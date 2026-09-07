# GCC Telegram Agent Prioritized TODO

這是整個專案唯一的排序工作佇列。完整審視依據見
[`docs/project-log.md`](project-log.md)。內容證據的細項只在
[`docs/project-evidence-todo.md`](project-evidence-todo.md) 展開。

## 執行規則

1. 同一時間只處理一個最前面的未完成項目；不得因較容易而跳級。
2. P0 未清完前，不主動擴大 production 用戶或收集更多個人／申請資料。
3. 每項完成必須同時具備：程式／設定、測試、production 驗證、文件和 rollback 說明。
4. 若項目需要產品或治理決定，先記錄決定與責任人，再寫程式。
5. 完成後將項目移到「Done」，並在 project log 加日期、PR、驗證證據和殘餘風險。

優先級定義：

- **P0 Critical**：已存在的安全、資料保存或核心 production 閉環風險。
- **P1 High**：影響可靠性、申請處理、公平性或持續交付。
- **P2 Medium**：提升產品價值及 public-goods 資料可重用性。
- **P3 Later**：規模化、便利性或非阻塞改善。

## Next up：嚴格執行順序

| 次序 | ID | 優先級 | 工作 | 完成定義／出口條件 | 依賴 |
|---:|---|---|---|---|---|
| 1 | GROUP-ACCESS-001 | P0 | **開放指定群組的 mention-only、免 email、隔離 session 問答** | 只有 `GCC_GROUP_ID` 指定群組的明確 mention 可進入一般 QA；不升級 `access_level`，不開放私訊、申請、callback 或管理能力；blocked 與每日限額繼續生效；private／group／user／topic session 隔離並有向後兼容 migration；feature flag 可即時關閉；三語及 production E2E 通過 | SEC-001、SEC-002 已完成；沿用現有 `GCC_GROUP_ID` |
| 2 | DATA-001 | P0 | **建立可實際還原的 SQLite 備份方案** | 確認 scheduled snapshot 正常產生；寫出備份與還原 runbook；在非 production volume 演練還原並核對資料；訂明 RPO/RTO、retention 和負責人；評估離站備份 | 現有 nrt volume |
| 3 | TEST-001 | P1 | **統一完整測試入口並把它設為 deploy gate** | 修正 `tests/telegram` package shadowing、Windows temp SQLite lock／編碼問題；一條 documented command 在 Windows/Linux 均通過；identity、email、group、migration、application、QA 和 logging tests 全部由 CI 執行；不能只跑舊 regression wrapper | P0 production 風險先清理 |
| 4 | ACCESS-001 | P1 | **把私訊／成員電郵驗證變成 production 閉環** | 決定合資格 email／群組政策；設定 verification 與 SMTP secrets；加入 resend cooldown／每日上限；完成 `/email`→收信→`/verify`→正確 access level 的三語 E2E；不影響 `group_qa` 的免 email 路徑 | 暫緩至 GCC 決定資格政策及 SMTP provider |
| 5 | APP-001 | P1 | **讓申請成為耐久、可追蹤的正式紀錄** | 新增 versioned migration 與 `applications`／status model；提交使用 stable ID 且具冪等性；通知成功／失敗分開記錄並可重試；通知失敗不可對用戶聲稱已送達；修正 `applications_today`；輸入 URL 驗證及 Telegram Markdown escaping 有測試 | TEST-001 |
| 6 | REVIEW-001 | P1 | **降低預審分數的錯誤精確度與偏見風險** | 明確標示 advisory、不得自動拒絕；將 rubric 拆成可解釋證據；建立由 GCC 審閱的代表性 eval cases；測試中英文同義內容不產生不合理差異；記錄人工 override 和模型／規則版本 | APP-001，GCC reviewer 參與 |
| 7 | OPS-001 | P1 | **加入健康檢查、告警與營運 runbook** | 不含敏感資料的 health/readiness endpoint；Fly health check 驗證 process、DB read/write readiness；machine down、deploy fail、webhook error、admin notification failure 有告警；runbook 包含 rollback、volume、token、incident 步驟 | TEST-001 |
| 8 | ACCESS-002 | P1 | **補完管理與身份生命週期** | 實作或移除 router 中的 `/block`、`/unblock`；加入 revoke／重新驗證規則；所有管理動作有 actor、target、timestamp、result audit trail；補 group membership 退出後的權限政策與測試 | ACCESS-001、TEST-001 |
| 9 | PRIV-001 | P1 | **制定及落實個人資料治理** | 列出 email、Telegram identity、對話、申請及 admin chat 的資料流；決定告知、用途、保留期、刪除／匯出、存取權；實作 retention cleanup 與 user/admin 操作；公開文件不洩露私人申請或委員資料 | APP-001，GCC governance 決定 |
| 10 | RELEASE-001 | P1 | **統一 dev→main 發佈治理** | PR checks 同時適用 dev/main；main 受保護且只接收經驗證 release PR；deploy workflow/action 版本固定或有更新政策；documented rollback 經演練 | TEST-001、OPS-001 |
| 11 | PGDATA-001 | P2 | **讓結構化 public-goods case database 成為 runtime 資料來源** | 定義從 case schema 到 QA／review 的 allowed fields；runtime 不再只靠 `projects.yaml`；回應能帶 provenance；private/internal snapshots 不進 prompt；兼容 migration 有測試 | REVIEW-001、PRIV-001 |
| 12 | CONTENT-001 | P2 | **修正現有 seed cases 的高風險證據缺口** | 依 evidence 子清單 Tier A 完成日期／金額／來源／私隱核實；每個 public claim 有可追溯來源或明確 unknown；由內容 owner review | PGDATA-001 可平行設計，但發佈受 PRIV-001 約束 |
| 13 | GOVERNANCE-001 | P2 | **確定 public-goods database 的授權與貢獻治理** | 決定資料 license（不只程式 MIT）；定義 provenance、版本、更正、撤回、敏感資料及 reviewer policy；提供 public contribution template | PRIV-001 |
| 14 | PRODUCT-001 | P2 | **建立產品成效指標與回饋迴路** | 指標能區分 onboarding、verified activation、link-first、AI、application started/submitted/followed-up；不以收集更多 PII 為代價；管理員可查看準確 funnel 與失敗率 | APP-001、PRIV-001 |
| 15 | CONTENT-002 | P3 | **擴充案例覆蓋與 outcome evidence** | 完成 evidence 子清單 Tier B/C；按類別逐批 import、review、release；不以「67 個全部匯入」取代品質門檻 | CONTENT-001、GOVERNANCE-001 |
| 16 | SEARCH-001 | P3 | **在 schema 穩定後評估 semantic search** | 先用 deterministic retrieval 建 baseline；量度準確率、引用率、成本及隱私；只有明顯優於 baseline 才引入 embeddings/vector store | PGDATA-001、代表性 eval set |

## Done

| 日期 | ID | 原優先級 | 完成內容 | 證據 |
|---|---|---|---|---|
| 2026-09-08 | SEC-001 | P0 | BotFather 舊 Telegram token 已 revoke；新 token 只透過 Fly secret 更新；machine v44 正常啟動 | 新 token `getMe` 200；`setWebhook` 200；webhook pending 0、無 last error；logs token 已 redacted |
| 2026-09-08 | SEC-002 | P0 | Telegram webhook 已設定長隨機 secret 並驗證來源 header；錯誤或缺少 secret 的 POST 被拒絕 | PR #12／merge `4760b24`；production `setWebhook` 200；secret header smoke test |
| 2026-09-07 | FLY-001 | P0 | Webhook 改為 `0.0.0.0:8080`；app/volume 統一 `nrt`；SQLite 掛載 `/data`；只保留一部常駐 machine；部署前有基本 test gate | PR #10／merge `e1e4a63`；Actions run `34065609326`；Fly machine v41 started/host ok；public webhook GET 405 |
| 2026-09-07 | LOG-001 | P0 | 修正非字串 URL logging argument 的 Telegram token redaction；production logs 抽查無 raw token | `tests/test_logging.py`；PR #10；production log assertion |
