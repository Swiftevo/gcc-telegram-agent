# GCC Telegram Agent 個人資料現況與 Data Flow

狀態：`PRIV-001A` 現況盤點  
盤點日期：2026-09-13  
基準：GitHub `main` commit `d4be4206b1113146b4d6aa49c802a6030917c9c2`

## 目的與邊界

本文件只記錄 Bot **目前實際**收集、產生、傳送、保存及刪除的資料。它不是私隱政策、
法律意見或未來設計，也不為 GCC 決定資料用途、合法基礎、保存期限或資料主體權利。

盤點以 repository 程式、migration、設定、runbook 及不含 secret value／用戶 row 的
production metadata 為證據。本次沒有讀取 production SQLite 內容、Telegram 對話、
管理員 chat、SMTP 帳戶或任何 secret value，也沒有更改 runtime、Fly 或用戶資料。

後續決定及實作分別由 `PRIV-001B` 至 `PRIV-001H` 跟進；`APP-001`／`REVIEW-001`
仍決定 Bot 申請收集及評分的產品去向。

## 資料主體與處理角色

| 類別 | 現況 |
|---|---|
| 私訊用戶 | `/start`、身份／email 指令、一般問答及現行申請流程的使用者 |
| 群組用戶 | 在指定 `GCC_GROUP_ID` 群組明確 mention Bot 的使用者 |
| 申請人 | 在私訊四步流程提供項目資料的已授權用戶 |
| 管理員／grantor | 接收通知、查看統計或執行身份操作的人；其 Telegram ID 及操作會部分留在 logs |
| Agent 身份 | Schema 支援 agent credential；runtime authentication path 尚未完成，但 credential row 可存在 |
| 公開案例中的人物 | 公開項目頁、Snapshot、活動或社交貼文可能包含公開姓名／團隊資料 |

GCC 的正式 data owner、可存取 production 的人員名單、SMTP operator、backup owner 及
資料要求聯絡人尚未有一份 canonical register；這是 `PRIV-001H` 的決定，不在本盤點假設。

## 系統資料流

```text
Telegram 用戶／群組
        │ inbound update、身份及訊息
        ▼
Telegram Bot API ───────► Fly.io ingress／Bot process
                                 │
             ┌───────────────────┼───────────────────┐
             ▼                   ▼                   ▼
     SQLite /data         OpenAI API          SMTP provider
  身份、session、訊息   一般 AI prompt       收件 email、驗證碼
     及申請 draft       與最近 context
             │
             ├──────────────► 管理員 Telegram chat
             │                現行申請通知／非敏感 ops 告警
             ▼
       Fly volume snapshots
       及 operator 手動 backup
```

官方 GCC／Tally 連結只作為回覆 URL。Bot 現時沒有 server-side 呼叫這些表格，也沒有把
Telegram identity 自動附加到連結；用戶點擊後的資料處理由目的網站另行發生。

## SQLite 資料清冊

Production `DB_PATH` 是 `/data/gcc_agent.db`，位於 NRT 單一 encrypted Fly volume。
SQLite 沒有欄位級加密；任何完整 database 或 backup 均包含以下資料。

### `users`

| 欄位／資料 | 來源 | 現行用途 | 現行刪除／保存行為 |
|---|---|---|---|
| `user_id` | Telegram | 主鍵、身份、rate limit、session／message 關聯 | 沒有 user delete；無限期保留 |
| `username`、`first_name` | Telegram profile | 顯示、`@username` 查找、申請通知 | 每次互動更新；沒有自動刪除 |
| `detected_lang` | Telegram language code | 選擇繁中／簡中／英文 | 語言改變時更新；沒有自動刪除 |
| `is_group_member` | Telegram `getChatMember` | 記錄最近一次 explicit membership check | 不是持續同步；沒有 expiry |
| `actor_type`、`access_level`、legacy `user_kind` | 管理操作／migration | QA 與身份授權 | 沒有 revoke lifecycle／自動刪除 |
| `is_blocked` | persistence primitive | access guard | `/block`／`/unblock` 尚未完成；沒有 audit table |
| `email`、`email_verified_at` | email verification | human GCC-member access | 明文 email；沒有 revoke 或 retention cleanup |
| `daily_count`、`count_reset_date`、`total_messages` | Bot 使用 | 每日 20 次限制及累計統計 | 日期轉換時重設 daily count；累計不刪除 |
| `created_at`、`last_seen_at` | Bot | 帳戶建立／最近互動 | 每次互動更新 last seen；沒有 inactive cleanup |

建立 user row 不只發生於完整 QA：普通私訊、群組 mention、身份指令及以 numeric ID 執行
`/grant` 均可建立或更新 user row。

### `sessions`

| 資料 | 內容與用途 | 現行刪除／保存行為 |
|---|---|---|
| `session_id`、`user_id` | UUID 與 user 關聯 | 沒有自動刪除 |
| `scope_type`、`scope_id`、`thread_id` | 分隔 private、group chat 及 forum topic | 包含 Telegram chat／topic identifiers；沒有自動刪除 |
| `mode` | `general` 或 `application` routing state | 新 session 不會刪除舊 row |
| `messages_json` | 該 session 的 user／assistant 完整文字 context 副本 | 只在送入模型時取最後 20 條；儲存陣列本身不會截短或清理 |
| `draft_json` | 項目名稱、基金、提案連結、摘要、步驟、分數、notes、提交時間 | exit 只清空當前 draft；完成後 draft 仍保存在 row；沒有 retention cleanup |
| timestamps | 建立及最後活動時間 | 30 分鐘 timeout 只令查詢另建 session，不會刪除過期 row |

Group session 已按 user、chat 及 topic 隔離，且 group route 不開啟申請；但群組問題和回答
仍會持久化到 `messages_json` 及 `messages`。

### `messages`

每次已處理的 user／assistant exchange 分別建立一個 row，保存：

- `message_id`、`session_id`、`user_id`；
- `role` 及完整 `content`；
- assistant 回答的 `tokens_used`、`link_served`；
- `created_at`。

同一段對話因此同時存在 `sessions.messages_json` 和獨立 `messages` table。README 所說的
「最近 20 條」是 AI context 上限，不是 database retention；`messages` row 沒有上限或
自動 expiry。被 rate limit、被拒絕、空 mention 或被忽略的群組訊息一般不會進入此表。

### `email_verifications`

保存 `user_id`、等待驗證的明文 email、HMAC `code_hash`、10 分鐘 `expires_at`、剩餘
嘗試次數及建立時間。驗證碼本身不保存明文。

成功驗證或嘗試次數歸零會刪除 row；寄送失敗會耗盡嘗試並刪除 row。已過期 row 只有在
用戶再次確認時才會清除，沒有全域 scheduled cleanup。2026-09-13 production secret name
清單沒有 SMTP 或 `EMAIL_VERIFICATION_SECRET`，所以現時 production request 會 fail
closed、不能寄出新驗證信；這不證明 SQLite 沒有歷史 email 或 challenge。

### `agent_credentials`

保存 `user_id`、scrypt credential hash、建立及 revoke 時間；不保存 raw credential。
程式有建立／驗證 primitive，但沒有完整 Telegram runtime 登入或公開管理流程。沒有
自動 retention cleanup。

### 非個人資料表

`schema_migrations` 只保存 migration version 及套用時間。本 repo 沒有獨立
`applications`、admin audit、privacy request 或 Telegram update idempotency table。

## 暫時處理及外部接收者

| 接收者／位置 | 會接收甚麼 | 觸發條件 | Repo 可核實的保留狀態 |
|---|---|---|---|
| Telegram Bot API | inbound update；Bot 回覆；身份查詢；管理員訊息 | 所有 Telegram 互動 | Telegram 端保留由其服務決定；本 repo 沒有控制 |
| OpenAI API | system instructions、GCC summary、最多最近 20 條 session context、當前問題 | deterministic fact／link-first 沒命中而呼叫 AI | 本 repo 沒有記錄或控制 provider-side retention；待告知／設定決定 |
| SMTP provider | 收件 email、六位驗證碼、寄件資料及 SMTP credentials | email service 完整設定且用戶請求驗證 | provider 及 mail recipient mailbox 的保留不受 Bot DB deletion 控制；production 現未配置 |
| 管理員 Telegram chat | username／ID／first name／語言、項目名稱、基金、提案 URL、摘要、heuristic 分數及 notes | 私訊申請完成時 | Bot 沒有 message ID／刪除流程；notification 失敗仍向用戶顯示 submitted |
| 管理員 Telegram chat | event type、UTC 時間，不含 user content | 去重 ops incident | Telegram 端保留不受 SQLite cleanup 控制 |
| Fly.io | webhook request、process、volume、secrets、platform／application logs、snapshots | production 運作 | provider metadata retention 未在 repo 定義；SQLite snapshot 見下節 |
| GitHub | source、Actions metadata、無 user content 的 deploy／ops incident issue | build、deploy 或 external monitor failure | public repo；Actions／Issue retention 由 GitHub／repo 設定決定 |

OpenAI 呼叫的 `messages` 不只是當前問題：包含同一 session 最多 20 條先前 user／assistant
內容。程式沒有在傳送前識別或遮蔽 email、電話、地址、申請資料或其他敏感文字。

## Logs、監察及錯誤

Application logs 目前可包含：

- Telegram `user_id`、group `chat_id`、scope／thread ID；
- grant actor／target ID 及身份結果；
- application user ID、分數、是否有提案連結；
- AI token 數、link type、command name；
- exception traceback 及 service error type。

明確控制包括 Telegram Bot token redaction filter；ops alert 只發 event type 和時間，error
handler 不記錄 raw update，GitHub incident issue 文案也不含用戶內容。程式一般不主動把
問題、摘要、email 或驗證碼寫入 application log；但第三方 library traceback／platform
request metadata 的完整內容未有可核實的 retention 或定期敏感資料檢查。

## 備份、複本與刪除邊界

| 複本 | 內容 | 現況 |
|---|---|---|
| Fly encrypted volume | 完整 live SQLite | `/data`，單一 NRT Machine 掛載 |
| Fly scheduled snapshots | 完整 SQLite volume block data | volume 設定 retention 14 日；舊 snapshot 可沿用建立時的 5 日設定 |
| 手動 SQLite backup | 完整 SQLite，包括 email、對話、draft、credential hash | 工具由 operator 指定輸出位置；manifest 含 checksum、size、migration version、各 table row counts，不含 row content |
| Restore drill copy | snapshot／backup 的完整臨時副本 | runbook 要求隔離、核對 target 後清理；沒有 application-level deletion propagation |
| Session duplication | `messages_json` 與 `messages` | 刪除其中一處不會自動清除另一處，需明確 transaction |
| Telegram admin notification | 申請資料的外部複本 | 不隨 SQLite row 刪除；目前沒有追蹤 message ID |

`.gitignore` 排除 `.env`、`gcc_agent.db`、`*.sqlite3`、manifest 及 `backups/`，目前沒有
database／backup 被 Git 追蹤。離站 object storage 尚未啟用；如日後啟用，必須先由
`PRIV-001H` 定義 owner、access、retention 及 deletion boundary。

## Public-goods repository 資料

GitHub repository 現時是 public。`projects.yaml`、`data/project-case-seeds.yaml`、schema
及九份 `data/source-snapshots/*.md` 均被 Git 追蹤，所以其中任何內容實際上都是公開資料。

詳細案例 schema 容許 `public`、`internal`、`private`、`redacted` evidence pointer；現行
seed 亦有標成 internal／private 的 pointer 或缺失資料說明。盤點未發現 raw private
application document 被 Git 追蹤，但 classification label 不能為 public repository 內的
文字提供存取控制。現行 runtime 只測試／載入案例 loader，尚未把詳細案例接入 QA；
`PGDATA-001`／`CONTENT-001` 在接入前必須按 `PRIV-001H` 的公開邊界審核。

公開來源也可能包含姓名、團隊或社交帳戶。公開可見不等於可以不設用途、來源、更正及
撤回規則；這部分同時屬於 `GOVERNANCE-001`。

## 現有保護

- Telegram webhook 使用 secret header，錯誤或缺失會被拒絕。
- Bot token 有 logging redaction；secret value 不進 repo。
- `/email`、`/verify`、`/grant`、`/whoami` 只在 private chat 註冊。
- Group QA 只在指定 chat、explicit mention 下運作，且 session 按 group／user／topic 隔離。
- email code 只保存 HMAC hash，agent credential 只保存 scrypt hash。
- Production SQLite volume encrypted，backup 有 integrity、foreign-key、checksum validation。
- 公開 health／readiness／ops endpoints 不輸出 user content、row count、secret 或錯誤細節。

## 已確認缺口與後續路由

| 缺口 | 後續任務 |
|---|---|
| 沒有 Bot 內最低限度資料告知或 `/privacy` | `PRIV-001B` |
| 對話、session、group identifiers 沒有保存期限；20-message／30-minute 並非刪除 | `PRIV-001C` |
| user identity、email、membership、credential 沒有完整 revoke／inactive policy | `PRIV-001D`、`ACCESS-001`／`ACCESS-002` |
| 現行申請 draft、評分及 admin notification 的去向未定 | `APP-001`、`REVIEW-001`、`PRIV-001E` |
| 沒有 scheduled retention cleanup | `PRIV-001F` |
| 沒有 user export／delete 或 privacy request record | `PRIV-001G` |
| Fly／SMTP／OpenAI／Telegram 的 owner、access register、provider retention 及 incident 流程未定 | `PRIV-001H` |
| SQLite 刪除不會同步刪除 snapshots、manual backups 或 Telegram admin messages | `PRIV-001G`／`PRIV-001H` |
| public repo 的 internal／private classification 不能形成存取控制 | `PRIV-001H`、`GOVERNANCE-001` |

## `PRIV-001A` 出口證據

- 已逐一核對六個 SQLite tables、session duplicate、logs、AI／SMTP／Telegram 傳送、
  Fly volume／snapshot／manual backup 及 public repository content。
- 已把「現行行為」與「待 GCC 決定」分開；沒有把 20-message context 或 30-minute
  session timeout 誤寫成 retention cleanup。
- 已核對 production secret **名稱**；沒有讀取值或 production user rows。
- 本任務沒有新增 notice、保存期限、cleanup、export、delete 或 access policy。

