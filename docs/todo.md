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
6. 現階段凍結新功能；先修復已承諾但不可靠、不完整或可能誤導的現有功能。資料庫擴充、
   semantic search 和新指標不得越過 P1 修復項目。

優先級定義：

- **P0 Critical**：已存在的安全、資料保存或核心 production 閉環風險。
- **P1 High**：影響可靠性、申請處理、公平性或持續交付。
- **P2 Medium**：提升產品價值及 public-goods 資料可重用性。
- **P3 Later**：規模化、便利性或非阻塞改善。

## 資助資料衝突隔離規則

- Snapshot／投票簽署只證明當時的提案、治理授權或決定，不自動證明實際撥款、
  milestone 驗收或解鎖金額。
- 實際執行必須由交易、會計、付款、驗收紀錄或獲授權跟進人確認；各者要分開記錄，
  不得以 snapshot 欄位互相代替。
- 尚在專人核對的衝突保留所有來源及差異，標成 `unknown`／`pending_reconciliation`；
  bot 不得把它說成已核實事實，AI review／分數亦不得使用該爭議 claim。
- 衝突核對列入 `GRANT-RECON-001`，但不阻塞測試、QA 正確性、申請持久化、私隱、
  維運及其他非衝突案例資料的修復。

## Next up：嚴格執行順序

| 次序 | ID | 優先級 | 工作 | 完成定義／出口條件 | 依賴 |
|---:|---|---|---|---|---|
| 1 | PRIV-001 | P1 | **補回現有個人資料治理缺口** | 列出 email、Telegram identity、對話、申請及 admin chat 的資料流；決定告知、用途、保留期、刪除／匯出、存取權；實作 retention cleanup 與 user/admin 操作；公開文件不洩露私人申請或委員資料 | GCC governance 決定 |
| 2 | ACCESS-002 | P1 | **補完現有管理命令與身份生命週期** | 實作或移除 router 中已宣告但不可用的 `/block`、`/unblock`；所有管理動作有 actor、target、timestamp、result audit trail；補 group membership 退出後政策與測試；email revoke／重新驗證部分待 `ACCESS-001` | TEST-001；部分依賴 ACCESS-001 |
| 3 | RELEASE-001 | P1 | **修復 dev→main 發佈治理缺口** | PR checks 同時適用 dev/main；main 受保護且只接收經驗證 release PR；deploy workflow/action 版本固定或有更新政策；documented rollback 經演練 | TEST-001、OPS-001 |
| 4 | REVIEW-001 | P1 | **移除 Bot 現有的假精確申請分數** | 停止計算／通知 40/30/20/10 百分制及 70/40 建議；Bot 不作自動通過、拒絕或排序；一般 QA 繼續使用官方事實邊界；外置表格及人類流程是正式申請／決策來源；舊 scoring code、tests、文件及資料使用有清理／兼容方案 | 外置表格決定已確認 |
| 5 | ACCESS-001 | P1 | **完成或正式收窄私訊／電郵驗證功能** | 決定繼續、收窄或移除未完成的 private/member email path；若保留，決定合資格政策及 SMTP provider、加入 cooldown／每日上限並完成三語 E2E；不影響 `group_qa` 免 email 路徑 | 依先前決定暫緩；需要 GCC 資格政策及 SMTP owner |
| 6 | APP-001 | P2 | **把 Bot 申請入口收窄至官方外置表格** | 申請 CTA 直接導向正確公共／專項基金表格並清楚說明正式提交在外部完成；停止本機四步資料收集、管理員通知及提交成功暗示；安全退出舊 draft；既有資料依 `PRIV-001` 處理 | 外置表格 URL owner；PRIV-001 |
| 7 | PGDATA-001 | P2 | **讓非衝突、已審核的 public-goods cases 成為 QA 資料來源** | 定義 QA 可用欄位；runtime 不再只靠 `projects.yaml`；回應帶 provenance／日期；private/internal 及 `pending_reconciliation` claims 不進 prompt；完整 schema validation 及兼容測試；review/scoring 接入另由 REVIEW-001 控制 | QA-FACT-001、PRIV-001 |
| 8 | CONTENT-001 | P2 | **修正非衝突 seed case 的證據與私隱缺口** | 完成 evidence 子清單可獨立核實的 Tier A 項目；每個公開 claim 有來源或明確 unknown；由內容 owner review；撥款／milestone 衝突移交 `GRANT-RECON-001`，不得猜測或阻塞其他 case | PGDATA-001 可平行設計，發佈受 PRIV-001 約束 |
| 9 | GRANT-RECON-001 | P2 | **由專人核對治理決定、實際撥款及 milestone 解鎖差異** | 對每個爭議 case 分開記錄 snapshot decision、實際 disbursement、milestone acceptance／unlock；保留衝突來源；由獲授權 owner 確認後才解除 `pending_reconciliation`；未確認資料不進 bot 事實回答或 review | GCC 指定跟進人及會計／交易／驗收證據；不阻塞其他修復 |
| 10 | GOVERNANCE-001 | P2 | **確定 public-goods database 的授權與貢獻治理** | 決定資料 license（不只程式 MIT）；定義 provenance、版本、更正、撤回、敏感資料及 reviewer policy；提供 public contribution template | PRIV-001 |
| 11 | PRODUCT-001 | P2 | **建立產品成效指標與回饋迴路** | 指標能區分 onboarding、verified activation、link-first、AI、application started/submitted/followed-up；不以收集更多 PII 為代價；管理員可查看準確 funnel 與失敗率 | Scope freeze；APP-001、PRIV-001 |
| 12 | CONTENT-002 | P3 | **擴充案例覆蓋與 outcome evidence** | 完成 evidence 子清單 Tier B/C；按類別逐批 import、review、release；不以「67 個全部匯入」取代品質門檻 | Scope freeze；CONTENT-001、GOVERNANCE-001 |
| 13 | SEARCH-001 | P3 | **在 schema 穩定後評估 semantic search** | 先用 deterministic retrieval 建 baseline；量度準確率、引用率、成本及隱私；只有明顯優於 baseline 才引入 embeddings/vector store | Scope freeze；PGDATA-001、代表性 eval set |

## Done

| 日期 | ID | 原優先級 | 完成內容 | 證據 |
|---|---|---|---|---|
| 2026-09-12 | OPS-001 | P1 | 補回不含敏感資料的 liveness／readiness／operations endpoints、Fly DB readiness check、Telegram webhook／backlog 監察、admin／deploy／machine 外部告警，以及完整 incident／rollback runbook | PR #22／merge `389322c`；Actions run `34651675306` 完整測試及 deploy 成功；production v54／machine started／Fly check passing／GH_SHA 相符；三個 endpoint 200、未授權 webhook 403；Telegram pending 0、無 last error；monitor run `34656207494` 成功、無 open incident |
| 2026-09-12 | QA-FACT-001 | P1 | 高風險資助政策問答改用繁／簡／英 deterministic link-first 與官方來源；一般 QA 移除內部百分制；明確區分公共／專項基金、Bot heuristic／人類決策，以及 Snapshot／實際執行 | PR #20／merge `96ca785`；Actions run `34644006225` compile、13 test files、Fly deploy 成功；production v52／machine started／GH_SHA 相符；容器內六類 route probe 正確；webhook pending 0、無 last error |
| 2026-09-11 | TEST-001 | P1 | 建立跨 Windows／Linux 的單一完整測試入口 `python -m tests`；逐檔隔離舊 executable suites 與 unittest，統一 UTF-8，消除 `tests/telegram` package shadowing；PR 與 main deploy 共用完整 gate；main ruleset 無 bypass 並要求 `Verify release` | PR #19／merge `38b747b`（PR #18 只合併至中間分支，故由 #19 正式帶入 main）；Windows 完整 suite 連續兩次通過、legacy discovery 33 tests；Actions run `34514061374` Linux gate／Fly deploy 成功；production machine v51；Node 20 action warning 留待 RELEASE-001 |
| 2026-09-10 | DATA-001 | P0 | Fly scheduled snapshots 已核實並保留 14 日；SQLite online backup／manifest 驗證工具、runbook、RPO 24h／RTO 2h、owner 及季度演練規則已建立；不同 zone restore drill 成功 | PR #15／merge `15932a4`；Actions run `34418412224`；production machine v48；on-demand snapshot 還原後 integrity OK、外鍵 0、migration 1–4、row counts 與 production 一致；臨時資源已清理；離站 object storage 待 `PRIV-001` 與 owner 決定 |
| 2026-09-10 | GROUP-ACCESS-001 | P0 | 指定 GCC 群組已開放 mention-only、免 email 的一般 QA；不升級帳戶，不開放申請／管理；private／group／user／topic session 隔離 | PR #13／merge `f60825e`；Actions run `34169493168`；production `GCC_GROUP_ID=-1003962128595`；未驗證 regular user link-first E2E 成功；group session 為 general、2 messages、無 private session／draft 污染 |
| 2026-09-08 | SEC-001 | P0 | BotFather 舊 Telegram token 已 revoke；新 token 只透過 Fly secret 更新；machine v44 正常啟動 | 新 token `getMe` 200；`setWebhook` 200；webhook pending 0、無 last error；logs token 已 redacted |
| 2026-09-08 | SEC-002 | P0 | Telegram webhook 已設定長隨機 secret 並驗證來源 header；錯誤或缺少 secret 的 POST 被拒絕 | PR #12／merge `4760b24`；production `setWebhook` 200；secret header smoke test |
| 2026-09-07 | FLY-001 | P0 | Webhook 改為 `0.0.0.0:8080`；app/volume 統一 `nrt`；SQLite 掛載 `/data`；只保留一部常駐 machine；部署前有基本 test gate | PR #10／merge `e1e4a63`；Actions run `34065609326`；Fly machine v41 started/host ok；public webhook GET 405 |
| 2026-09-07 | LOG-001 | P0 | 修正非字串 URL logging argument 的 Telegram token redaction；production logs 抽查無 raw token | `tests/test_logging.py`；PR #10；production log assertion |
