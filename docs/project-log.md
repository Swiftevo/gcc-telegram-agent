# GCC Telegram Agent Project Log

這份日記記錄已核實的產品、技術、營運與 public-goods 決策。它不是待辦清單；
尚未完成的工作及其唯一執行順序，以 [`docs/todo.md`](todo.md) 為準。

## 2026-09-10：`DATA-001` SQLite 備份與還原閉環完成

- Production volume `vol_vde858w7nwx75564` 的 scheduled snapshots 已實際產生：
  盤點時最近兩日有 3 個 `created` snapshots；設定顯示 scheduled snapshots 為 true。
- 每日 snapshot retention 已由 5 日提高至 14 日；production machine、volume mount
  和 DB 內容沒有因此重啟或改動。
- 第一輪從當日較早的 automatic snapshot `vs_ZywDkqVwkgYszlxYjN8k77P` 建立隔離
  volume；DB `integrity_check=ok`、外鍵違規 0、migration 1–4 齊全，但 users／sessions／
  messages 為 0／0／0。同期 production 唯讀檢查為 1／1／6，實證每日 snapshot 最多
  可落後約 24 小時，不能當作即時複本。
- 隨後建立 on-demand snapshot `vs_7q940ZM90DyT9QKjyGbgwRk`；從它建立位於不同
  zone 的獨立 restore volume，並以不啟動 bot 或 HTTP service 的一次性 machine
  `83d105ec746ed8` 驗證。結果為 `integrity_check=ok`、外鍵違規 0、migration 1–4、
  users／sessions／messages 1／1／6，與 snapshot 前 production 計數一致；machine
  exit code 0 並自動銷毀。
- 兩個演練 restore volumes 均在核對未 attached 後刪除；production volume 未被替換。
- 已建立 `gcc_agent.ops.sqlite_backup`：以 SQLite online backup API 建立一致副本，
  驗證完整性／外鍵／必要 tables／migration，並輸出不含實際個人資料的 SHA-256、
  row counts 和 manifest。Windows 首輪測試發現 connection 未明確 close 會鎖檔，
  修正後相關測試全數通過。
- Runbook 訂明 owner 為 GCC bot operator（目前 `Swiftevo`）、RPO 24 小時、RTO 2 小時、
  migration 前 on-demand snapshot、每季 restore drill，以及 rollback／清理界線。
- 離站備份評估結論：只用 Fly snapshots 仍有同 account／平台風險；建議獨立
  S3-compatible storage、上傳前加密、14 個 daily 加 3 個 monthly。正式啟用仍待
  GCC 指定 storage account owner 及 `PRIV-001` 確定含個人資料備份的保留／刪除政策。
- PR #15 已 merge（`15932a4`）；GitHub Actions run `34418412224` 的 compile、既有
  regression suites、新增 SQLite backup tests 及 Fly deploy 全部成功。
- Production machine `7813de2bdd3638` 已更新至 version 48，原 `nrt` volume 保持掛載；
  新 image 內的 `sqlite_backup verify` 直接檢查 `/data/gcc_agent.db` 成功：
  `integrity_check=ok`、外鍵違規 0、migration 1–4。部署後 bot 繼續成功處理 Telegram
  和 OpenAI 回覆，logs 沒有新 traceback，token 保持 redacted。
- 驗收完成後 `DATA-001` 移入 Done。現存 snapshots 在 retention 更新前建立，仍顯示
  5 日；volume 現行設定為 14 日，下一個 scheduled snapshot 應再核對其個別 retention。
  離站 object storage 未啟用的風險保留至 `PRIV-001` 和 storage owner 決定。

## 2026-09-10：`GROUP-ACCESS-001` production 驗收完成

- PR #13 已 merge（`f60825e`）；GitHub Actions run `34169493168` 的 verify 和
  Fly deploy 均成功。
- Production `GCC_GROUP_ID` 已由舊測試群組更新為 GCC 2026H2 內部工作群組
  `-1003962128595`；`GROUP_QA_ENABLED=true`。
- Machine `7813de2bdd3638` 在 `nrt` 為 `started`／host `ok`；重啟後 `getMe`、
  `setWebhook` 均為 200。Webhook pending updates 為 0，沒有 last error。
- 未驗證 email、`access_level=regular` 的真實群組用戶 mention bot 後，成功取得
  GCC about 的 link-first 回覆；沒有 email gate 或申請按鈕。
- SQLite 建立一個 `scope_type=group`、正確 group ID、`mode=general` 的 session；
  一問一答同時產生 2 條 context 及 2 條 message records。儲存內容已移除 bot mention，
  application draft 為空，沒有建立或觸碰 private session。
- Production logs 記錄 `link served type=about`，沒有新 error／traceback。由此確認
  mention-only、免 email、窄權限及 session 隔離閉環均成立，任務移到 Done。

## 2026-09-08：關閉 Telegram 安全缺口及確定群組 QA 路徑

### Production 安全驗證

- PR #12（merge `4760b24`）已把長隨機 `WEBHOOK_SECRET_TOKEN` 同時傳給
  Telegram `setWebhook` 和本機 webhook server。
- 缺少或錯誤 `X-Telegram-Bot-Api-Secret-Token` 的 POST 會被拒絕；正確 header
  能到達 Telegram update parser。
- 曾在歷史 logs 出現的 bot token 已由 BotFather revoke；新 token 只經 Fly secret
  更新。Machine `7813de2bdd3638` version 44 在 `nrt` 正常啟動。
- 新 token 的 `getMe` 和 `setWebhook` 均回傳 200；webhook URL 正確，pending updates
  為 0，沒有 last error，logs 只顯示 `bot[REDACTED]`。
- Fly CLI 的 DNS warning 來自操作端向 `8.8.8.8` 查詢逾時；production webhook
  實際可達且 Telegram 狀態正常。

### 群組存取產品決定

- 電郵驗證暫時不作為指定 GCC 群組一般問答的先決條件；它繼續保護私訊問答、
  申請和成員級功能。
- 群組能力是 request-scoped `group_qa`，不會寫入或升級用戶的 `access_level`，
  亦不會偽造 email 驗證狀態。
- 只有 `GCC_GROUP_ID` 指定群組內的明確 bot mention 才處理；其他群組及未 mention
  訊息保持靜默。群組只開一般 QA，不開申請、callback 或管理功能。
- Private、group、user 及 Telegram topic 的 session 必須隔離，避免私訊歷史或
  申請草稿進入公開群組回答。
- Block list 和每日 20 條限制繼續適用。`GROUP_QA_ENABLED` 是 rollout／rollback
  開關；`fly.toml` 的 release 設定會啟用它，但只有 merge、deploy 和群組 E2E
  完成後才可把 `GROUP-ACCESS-001` 移到 Done。

## 2026-09-07：由零開始的全系統重新審視

### 審視範圍與基線

- Repository：`main`，PR #10 merge commit `e1e4a63`。
- Production：Fly.io app `gcc-public-goods-bot`。
- 檢查面向：產品閉環、身份與安全、Telegram 體驗、申請流程、AI 預審、
  public-goods 資料、內容證據、測試、部署、資料保存及維運。
- 原則：以實際程式碼、production 設定、CI 和 HTTP 行為為準；README 的描述
  不當作功能已可用的證據。

### 總結

Bot 已有清楚的模組化基礎：default-deny 身份守門、三語介面、link-first 問答、
四步申請收集、確定性預審、管理員通知，以及結構化 public-goods 案例資料。
Fly webhook／資料卷事故亦已修復。

目前最大的產品阻塞不是「缺少更多功能」，而是已承諾的核心閉環尚未全部在
production 成立：電郵驗證沒有寄送設定，普通用戶因此無法成為可使用問答／申請的
成員；申請完成後也沒有獨立、耐久、可追蹤的申請紀錄。安全方面仍需輪替曾出現在
歷史 logs 的 Telegram token，並為 webhook 加上來源驗證。

### 產品檢查

| 範圍 | 已有能力 | 已核實缺口 |
|---|---|---|
| Onboarding／身份 | human/agent 與 regular/gcc_member 分開；未授權預設拒絕；有 `/email`、`/verify`、`/whoami`、`/grant` | Production 沒有 SMTP／verification secret；歡迎訊息要求所有人驗證，但只有 Telegram GCC 群成員才會升級，資格與下一步不夠清楚 |
| 問答 | 官網連結優先；其餘問題使用 OpenAI；三語回應；每日限額 | 連結為硬編碼，缺少定期失效檢查；沒有一組產品級回答品質／幻覺回歸評估 |
| 申請 | 四步收集項目名稱、基金、連結、摘要；產生預審分數並通知管理員 | 沒有 `applications` 主表、狀態或 stable ID；通知失敗仍向申請人顯示「已收到」；連結與 Markdown 輸入未完整驗證／轉義；統計以 session draft 推算，不可靠 |
| 管理 | `/status`、`/update_values` 可用；身份授權會再次檢查群組身份 | Router 宣告 `/block`、`/unblock`，handler 沒有實作；缺少可稽核的管理操作紀錄與身份撤銷流程 |
| 群組 | 只處理指定 GCC 群內明確 mention bot 的訊息 | 尚未有群組噪音、重複回覆、權限及 rate-limit 的端到端測試 |

### 技術與維運檢查

| 範圍 | 狀態 | 判斷 |
|---|---|---|
| Fly webhook | `WEBHOOK_LISTEN` 預設 `0.0.0.0`，傳給 `run_webhook()`；public `/webhook` 可由 Fly proxy 到達 | 已解決 |
| SQLite persistence | app 與 `gcc_agent_data` volume 同在 `nrt`；`/data/gcc_agent.db`；單一 writer machine | 已解決，但仍需 restore drill |
| Availability | 一部 machine、`min_machines_running = 1` | 避免 webhook cold start；接受單機／單區故障風險及常駐成本 |
| Logging | 已能遮罩 URL object 中的 Telegram token，production 抽查沒有 raw token | 新洩漏已堵塞；舊 token 仍必須輪替 |
| CI/CD | main push 先執行 compile、舊 regression suites 及 token-redaction test，再部署；deploy 有 concurrency lock | CI 只覆蓋部分 tests；README 的完整 discovery 指令在 Windows 仍有 import／temp SQLite 清理問題 |
| Health／monitoring | Fly smoke check 能確認 machine 進入 good state | 沒有專用 health/readiness endpoint、外部告警、錯誤率或通知失敗告警 |
| Backup | Fly volume 已啟用 scheduled snapshots，retention 為 5 | 尚未驗證 snapshot 產生、還原步驟、RPO/RTO 或離站備份 |

### Security 與資料治理檢查

- 歷史 Fly logs 曾包含完整 Telegram bot token。程式已修正 log redaction，但已出現過的
  token 不能靠遮罩補救，必須由 BotFather revoke／重發並更新 Fly secret。
- Webhook 現時依賴難以猜測的 Telegram update 內容，沒有使用 Telegram
  `secret_token`／`X-Telegram-Bot-Api-Secret-Token` 驗證來源。
- Email code 使用 HMAC、有效期和最多五次嘗試，方向正確；但沒有 resend cooldown、
  每日寄送上限或明確的合資格 domain／群組政策。
- SQLite 保存 Telegram identity、email、對話全文與申請草稿；尚未訂明告知、保留期、
  刪除／匯出流程及誰可存取。
- 管理員通知將申請人名稱、Telegram ID、摘要及提案連結傳至指定 chat；需要把這條
  資料流寫進 privacy／operations 文件。

### Public-goods 與內容檢查

已有的公共基礎建設方向是合理的：

- `values.yaml` 保存使命、資助方向、拒絕準則及評分權重。
- `projects.yaml` 是目前 bot 使用的舊知識來源。
- `data/project-case-seeds.yaml`、JSON Schema 和 source snapshots 開始把事實、來源、
  私隱等級與 AI 可用範圍分開。
- 六個 seed cases 已覆蓋不同資助類型，並保留不確定性，而非補寫猜測內容。

主要缺口：

- Runtime 問答與 `pre_screen()` 仍主要讀取 `projects.yaml`；結構化 case database 尚未
  真正成為可重用的公共資料層。
- 現行預審以關鍵詞、字數及固定加·判斷計分塊進行，容易被措辭操控；分數看似精確，
  但未經歷史決策或人工 rubric 校準。
- 資料庫級 license、貢獻／更正流程、版本與 provenance policy 尚未定案。
- ETH City、ETH Beijing、Devconnect 等案例仍有來源、結果和私隱邊界待補；詳見
  [`docs/project-evidence-todo.md`](project-evidence-todo.md)。

### Production 快照

截至 2026-09-07（Asia/Hong_Kong）：

- Machine：`7813de2bdd3638`，version 41，`nrt`，`started`，host `ok`。
- Volume：`vol_vde858w7nwx75564`／`gcc_agent_data`，1 GB encrypted，已附加。
- GitHub Actions run `34065609326`：`Verify release` 與 `Deploy app` 均成功。
- Logs：`listen=0.0.0.0 port=8080`、application started、database path 正確、沒有 raw token。
- HTTP：`/` 回傳 404（沒有 homepage route）；`/webhook` 對 GET 回傳 405（只接受 POST）。
- 已部署 secrets 只有：`ADMIN_NOTIFY_ID`、`ADMIN_USER_ID`、`BOT_TOKEN`、
  `GCC_GROUP_ID`、`OPENAI_API_KEY`、`WEBHOOK_URL`。SMTP、email verification 及 webhook
  secret 尚未設定。

### 來源與責任追蹤

- PR #2 `Refactor bot architecture and establish identity foundation`：由
  `China-Chris` 提出，2026-08-28 merge；加入目前的身份／電郵驗證基礎。
- PR #8 `Release dev updates to main`：由 `Swiftevo` 提出，將 dev 更新帶到 main。
- PR #10 `fix: make Fly deployment persistent and single-instance`：由 `Swiftevo` 提出，
  2026-09-07（香港時間）merge；修復 Fly listen host、volume、單機部署、CI gate 與 token
  redaction。

### 已完成決策

- SQLite 階段只運行一部 writer machine，不製造沒有同步機制的假高可用。
- Production 與現有 volume 統一放在 `nrt`。
- Webhook machine 保持常駐，優先可靠性而非 scale-to-zero 成本節省。
- 每次 production deploy 前至少執行現有 release regression 與安全 smoke test。
- 新工作按 [`docs/todo.md`](todo.md) 的單一順序處理；同一時間只開一個 active item。
