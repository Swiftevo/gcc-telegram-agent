# GCC Telegram Agent Project Log

這份日記記錄已核實的產品、技術、營運與 public-goods 決策。它不是待辦清單；
尚未完成的工作及其唯一執行順序，以 [`docs/todo.md`](todo.md) 為準。

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

