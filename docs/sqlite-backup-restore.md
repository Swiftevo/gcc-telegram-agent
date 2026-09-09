# SQLite 備份與還原 Runbook

這份文件處理 production `/data/gcc_agent.db` 的資料事故。程式部署 rollback、
Telegram token 或其他 Fly secrets 不屬於 SQLite 還原；它們需要另外處理。

## 保護目標與責任

| 項目 | 現行決定 |
|---|---|
| Production app | `gcc-public-goods-bot` |
| Production volume | `vol_vde858w7nwx75564`／`gcc_agent_data`，`nrt` |
| 資料庫 | `/data/gcc_agent.db` |
| Owner | GCC bot operator（目前由 `Swiftevo` 負責 Fly 操作及演練） |
| RPO | 最多 24 小時；任何 DB migration 前另做 on-demand snapshot |
| RTO | 事故確認後 2 小時內恢復；這是演練後的操作目標，不是平台 SLA |
| Fly snapshot retention | 14 日 |
| Restore drill | 每季一次，及 schema／storage 流程重大改動後一次 |

RPO 是事故時最多可接受遺失多少時間的資料；RTO 是確認事故後恢復服務的
目標時間。現時每日 snapshot 不能保證保存事故前最後 24 小時內的寫入。

## 三道保護

1. Fly 每日 scheduled snapshot：處理 volume／host 故障和短期誤刪。
2. DB migration 前的 on-demand snapshot：縮短高風險改動的回復點距離。
3. SQLite application-consistent 備份：使用 SQLite backup API 建立經驗證的副本，
   作為日後傳到獨立 object storage 的來源；不可用普通 `cp` 複製運行中的 DB。

Snapshot 及 SQLite 備份均包含 Telegram identity、email、對話和申請草稿。只可讓
指定 operator 存取，不得放入 Git、一般 CI artifact、公開連結或未加密儲存。

## 每日檢查及 migration 前 snapshot

列出 volume 與 snapshot：

```powershell
flyctl volumes show vol_vde858w7nwx75564 -a gcc-public-goods-bot
flyctl volumes snapshots list vol_vde858w7nwx75564 -a gcc-public-goods-bot
```

正常條件：`Scheduled snapshots: true`；最近約 24 小時內至少一個 snapshot 為
`created`。`waiting`／`running` 只代表尚未完成，不能作還原點。

任何會改 schema 或大量修改資料的 deploy 前：

```powershell
flyctl volumes snapshots create vol_vde858w7nwx75564 -a gcc-public-goods-bot
flyctl volumes snapshots list vol_vde858w7nwx75564 -a gcc-public-goods-bot
```

必須等待新 snapshot 變成 `created` 才開始 migration。

## 建立一致的 SQLite 備份

部署本 repository 的工具後，可在 machine 內執行：

```text
python -m gcc_agent.ops.sqlite_backup create \
  --source /data/gcc_agent.db \
  --output-dir /data/backups
```

工具會：

- 對 source 執行 `PRAGMA quick_check`；
- 使用 SQLite online backup API，而不是直接複製 live file；
- 對輸出執行完整 `integrity_check` 及 `foreign_key_check`；
- 核對必要 tables 與 migration version；
- 產生 SHA-256、row counts 和 JSON manifest，但不輸出實際個人資料；
- 以 atomic rename 發佈已驗證檔案，權限設為 owner-only。

`/data/backups` 仍在同一個 production volume，只是安全的中間檔，不算離站備份。
它必須由已核准流程加密並傳送到獨立 object storage，成功核對 checksum 後再從
production volume 移除。

驗證任何已下載／還原的副本：

```text
python -m gcc_agent.ops.sqlite_backup verify \
  --database <RESTORED_DB_PATH> \
  --manifest <MANIFEST_PATH>
```

成功條件是 exit code 0、`integrity_check: ok`、外鍵違規 0、migration 齊全，而且
`manifest_match: true`。沒有 manifest 的 Fly snapshot 演練，則以 snapshot 前記錄的
row counts 核對事故時間點；checksum 只用來識別該次還原結果。

## Snapshot 還原程序

### 1. 控制事故

1. 記錄事故開始、最後一次已知正常寫入及操作人。
2. 如仍有錯誤寫入，先停止 production machine；不要先刪除原 volume。
3. 記錄當前 image、machine、volume 及 snapshot 清單。
4. 選擇事故發生前、狀態為 `created` 的 snapshot。

### 2. 建立隔離 volume

還原會建立新 volume，不會倒帶或覆寫 production volume：

```powershell
flyctl volumes create <SHORT_DRILL_NAME> `
  --app gcc-public-goods-bot `
  --region nrt `
  --size 1 `
  --snapshot-id <SNAPSHOT_ID> `
  --scheduled-snapshots=false `
  --yes
```

從 `flyctl volumes list -a gcc-public-goods-bot` 記下新 volume ID，並再次確認它不是
`vol_vde858w7nwx75564`。

### 3. 在不啟動 bot 的 machine 驗證

先由 `flyctl machine status <PRODUCTION_MACHINE_ID> -a gcc-public-goods-bot
--display-config` 取得現行 image。以下 machine 沒有 HTTP service，command 只會讀取
SQLite，完成後以 `--rm` 自動刪除：

```powershell
flyctl machine run <CURRENT_IMAGE> `
  --app gcc-public-goods-bot `
  --region nrt `
  --volume <RESTORE_VOLUME_ID>:/data `
  --name gcc-restore-drill `
  --restart no `
  --rm `
  --skip-dns-registration `
  --vm-memory 256 `
  --file-local /tmp/sqlite_backup.py=gcc_agent/ops/sqlite_backup.py `
  -- python /tmp/sqlite_backup.py verify --database /data/gcc_agent.db
```

再以 `flyctl machine status <DRILL_MACHINE_ID>` 核對 `exit_code=0`，並查看該 machine
logs。不得只以 machine 能啟動當作資料已還原。

### 4. Production 切換（只在真實事故執行）

1. 保持舊 volume 不變並記錄其 ID。
2. 以已驗證 volume 取代 machine 的 `/data` mount；一次只可有一部 SQLite writer。
3. 啟動後核對 machine status、webhook、DB counts 及一個不寫入敏感資料的 smoke test。
4. 如驗證失敗，停止新 machine，重新掛回原 volume 或選另一個 restore point。
5. 問題 volume 至少保留到事故分析及資料補回決定完成，不要即時 destroy。

Fly secrets、`fly.toml` 和 container image 不在 volume snapshot 內。DB 恢復後仍要核對
secret 名稱、image release 和 webhook 設定，但不得把 secret values 寫入 runbook。

## 演練後清理

確認 drill machine 已 `destroyed`，然後列出 volumes，逐字核對臨時 volume 的 ID、名稱、
未 attached，才執行：

```powershell
flyctl volumes destroy <RESTORE_VOLUME_ID> -a gcc-public-goods-bot --yes
```

永遠不可把 production volume ID 放入演練清理指令。

## 離站備份評估

Fly snapshot 仍依賴同一個 Fly account／平台，不能覆蓋 account lockout 或平台級事故。
因此離站備份是下一層必要保護，但啟用前要完成以下決定：

| 選項 | 優點 | 主要風險／條件 |
|---|---|---|
| 獨立 S3-compatible object storage | 與 Fly 分開、容易做 versioning/lifecycle | 要管理獨立 credential、client-side encryption 和 restore download |
| 由 operator 加密下載到受控儲存 | 最少自動化、容易先試行 | 依賴人工執行，容易漏做，不適合作長期每日方案 |
| 只使用 Fly snapshots | 現時最簡單 | 不是離站，不能作唯一長期方案 |

建議採用獨立 S3-compatible storage、每日一份、保留 14 個 daily 及 3 個 monthly；
上傳前 client-side encryption，credential 只容許指定 bucket/prefix。正式啟用前由
`PRIV-001` 確認資料保留及刪除政策，並由 GCC 指定 storage account owner。

## 驗收紀錄

每次演練要在 `docs/project-log.md` 記錄：日期、snapshot ID、restore volume（清理後）、
machine exit code、integrity/foreign-key 結果、migration、row counts、耗時及殘餘風險。
只記數量與 checksum，不記錄 Telegram ID、email、訊息內容或其他備份資料。
