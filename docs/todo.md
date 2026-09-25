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

原本單一 `PRIV-001` 已於 2026-09-13 拆成 `PRIV-001A` 至 `PRIV-001H`；A、B 已完成。
`ACCESS-001` 已收起 email verification；`GROUP-ACCESS-002` 亦已讓指定群組現任成員
使用私人一般問答並完成 production 驗收。C–H 的表內次序仍只是方便檢視的暫定排列，
不會自動開始。

| 次序 | ID | 優先級 | 工作 | 完成定義／出口條件 | 依賴 |
|---:|---|---|---|---|---|
| 1* | PRIV-001C | P1 | **決定對話與 session 保存政策** | 分開決定 private／group、link-first／AI、`messages_json`／messages 的必要性、保存期、匿名統計及模型傳送邊界 | PRIV-001A；GCC retention 決定 |
| 2* | PRIV-001D | P1 | **決定身份與 email 資料政策** | 定義 Telegram identity、membership、legacy email、challenge、credential 的用途、revoke、inactive user 及保存期；不在本項重啟 email verification 或重做 authentication | PRIV-001A；ACCESS-001；部分依賴 ACCESS-002 決定 |
| 3* | PRIV-001E | P1 | **處理舊申請 draft、評分及 admin notification 資料** | 停止新流程後定義舊 session draft／score 的兼容、保存、通知副本及安全清理；政策前不得直接刪 production 歷史資料 | APP-001、REVIEW-001；GCC retention 決定 |
| 4* | PRIV-001F | P1 | **實作自動過期及 retention cleanup** | 按已批准期限清理／匿名化 user、session、message、challenge、credential、legacy draft；transaction 可重跑、有測試、metric、告警及 rollback | PRIV-001C、PRIV-001D、PRIV-001E |
| 5* | PRIV-001G | P1 | **提供用戶資料查閱、匯出及刪除流程** | 驗證 requestor，只處理自己的資料；完整涵蓋重複儲存及關聯 row，記錄最小 audit，清楚說明 backup／Telegram 外部副本延遲 | PRIV-001C 至 PRIV-001F；ACCESS-002 |
| 6* | PRIV-001H | P1 | **治理 backup、logs、第三方及 production 存取** | 定義 data owner、access register、provider／admin chat 邊界、logs review、snapshot／manual backup retention、離站儲存及 incident／撤權 runbook | PRIV-001A；GCC owner 決定；REPO-GOV-001 |
| 7 | ACCESS-002 | P1 | **補完現有管理命令與身份生命週期** | 實作或移除 router 中已宣告但不可用的 `/block`、`/unblock`；所有管理動作有 actor、target、timestamp、result audit trail；補 group membership 退出後政策與測試；不在本項重啟 email verification | TEST-001；ACCESS-001；部分依賴 PRIV-001D |
| 8 | RELEASE-001 | P1 | **鎖定 release workflow 與部署工具供應鏈** | 所有 GitHub Actions 固定到已核實的完整 commit SHA；移除 `setup-flyctl@master` 並固定 Fly deployment tooling；建立由 PR／完整 gate 審核的定期更新政策；main test／deploy 可追溯至同一 commit，production image SHA 相符 | TEST-001、OPS-001 |
| 9 | REVIEW-001 | P1 | **移除 Bot 現有的假精確申請分數** | 停止計算／通知 40/30/20/10 百分制及 70/40 建議；Bot 不作自動通過、拒絕或排序；一般 QA 繼續使用官方事實邊界；外置表格及人類流程是正式申請／決策來源；舊 scoring code、tests、文件及資料使用有清理／兼容方案 | 外置表格決定已確認；PRIV-001E 跟進歷史資料 |
| 10 | REPO-GOV-001 | P2 | **確立多人 contributor／AI Agent 的 repository 與 release 治理** | Trunk-based model、main-only 文件／workflow 及移除無獨有 commit 的 `dev` 已完成；剩餘：盤點三位 collaborators 並採最小權限；以 CODEOWNERS 只為敏感路徑要求非作者 approval，定義 owner、emergency hotfix 及 backup operator 訓練；建立單一 `docs/ai-agent-guide.md`，規定開工必讀、TODO／scope、架構、敏感資料、production 授權、事實來源、測試與完成記錄；按實際工具加入薄入口檔並建立 PR template | 敏感 owner／backup operator 最終確認；TEST-001；PRIV-001H 共享 access register |
| 11 | RELEASE-DRILL-001 | P2 | **在隔離環境完成 image rollback／roll-forward 演練** | 使用不含 production token、volume 或真實流量的隔離環境，選定可追溯的 current／known-good images，實際 rollback 再 roll-forward；驗證 endpoints、logs、image SHA、schema compatibility 及恢復時間；留下 operator、時間、證據和失敗處理；production 演練另需 maintenance window | RELEASE-001、OPS-001、DATA-001 |
| 12 | APP-001 | P2 | **把 Bot 申請入口收窄至官方外置表格** | 申請 CTA 直接導向正確公共／專項基金表格並清楚說明正式提交在外部完成；停止本機四步資料收集、管理員通知及提交成功暗示；安全退出舊 draft；不在本項刪除歷史資料 | 外置表格 URL owner；PRIV-001E 隨後處理歷史資料 |
| 13 | ONBOARDING-RUNTIME-001 | P2 | **把核准的新手內容接入輕量、問題驅動問答** | 僅讓 `GCC_GROUP_ID` 現任 human 成員使用；以 `data/onboarding.yaml` approved topics 作 deterministic-first 回答，每次最多一個自然延伸提示、不建立按鈕選單；不自動抓飛書、不新增永久興趣 profile、不改申請／管理能力；先解決 2026 H2 OPS 與 `values.yaml` 舊五項優先方向的內容優先順序，避免同一 Bot 給出矛盾答案；完整 private／group、rate-limit、session、fallback、fact-boundary、production E2E 及 rollback 驗收 | `ONBOARDING-CONTENT-001` baseline；GCC owner 決定 OPS／舊方向的 canonical priority；P1 scope freeze；多語另見 `ONBOARDING-I18N-001` |
| 14 | PGDATA-002 | P1 | **收斂 canonical case database、legacy migration、清理及審核閘門** | Schema 0.2.1 全量遷移現有 8 case；`projects.yaml` 以 digest 鎖定為 legacy runtime catalog，63 筆有 mapping／`legacy_only` 狀態；所有 local evidence 有 checksum、處理 profile、清理／review／allowed-use 狀態；CI 阻止孤立檔、逐票身份／wallet／存取憑證、重複 amount、未有付款證據的 `funded`、未審核來源進 Bot；提供可重用 intake／sanitized evidence template；不改 runtime | PGDATA-001 已完成的 schema 0.2 基礎；本項完成前暫停新增案例 |
| 15 | PGDATA-001 | P2 | **讓非衝突、已審核的 public-goods cases 成為 QA 資料來源** | Schema 0.2、完整 Draft 2020-12／跨紀錄驗證、現有 seed migration、OSKey／OpenRPC 首批無已知金額衝突的 draft 匯入，以及不含 voter identity／wallet／會議密碼的 sanitized application evidence 已完成；剩餘：內容 owner review、定義 QA 可用欄位、runtime 不再只靠 `projects.yaml`、回應帶 provenance／日期、private/internal 及 `pending_reconciliation` claims 不進 prompt；review/scoring 接入另由 REVIEW-001 控制 | QA-FACT-001、PRIV-001A／PRIV-001H；PGDATA-002 |
| 16 | CONTENT-001 | P2 | **修正非衝突 seed case 的證據與私隱缺口** | 完成 evidence 子清單可獨立核實的 Tier A 項目；每個公開 claim 有來源或明確 unknown；由內容 owner review；撥款／milestone 衝突移交 `GRANT-RECON-001`，不得猜測或阻塞其他 case | PGDATA-001 可平行設計，發佈受 PRIV-001H 約束 |
| 17 | GRANT-RECON-001 | P2 | **由專人核對治理決定、實際撥款及 milestone 解鎖差異** | 對每個爭議 case 分開記錄 snapshot decision、實際 disbursement、milestone acceptance／unlock；保留衝突來源；由獲授權 owner 確認後才解除 `pending_reconciliation`；未確認資料不進 bot 事實回答或 review | GCC 指定跟進人及會計／交易／驗收證據；不阻塞其他修復 |
| 18 | GOVERNANCE-001 | P2 | **確定 public-goods database 的授權與貢獻治理** | 決定資料 license（不只程式 MIT）；定義 provenance、版本、更正、撤回、敏感資料及 reviewer policy；提供 public contribution template | PRIV-001A、PRIV-001H |
| 19 | PRODUCT-001 | P2 | **建立產品成效指標與回饋迴路** | 指標能區分 onboarding、verified activation、link-first、AI、application started/submitted/followed-up；不以收集更多 PII 為代價；管理員可查看準確 funnel 與失敗率 | Scope freeze；APP-001、PRIV-001C／PRIV-001H |
| 20 | I18N-001 | P3 | **避免問答正文與固定尾句混用不同語言** | 重現英文問題正文配中文例會提醒；決定以 Telegram locale、問題語言或答案語言為準並統一整則回覆；繁／簡／英的 link-first、AI、private、group 路徑有測試；不改事實內容或存取規則 | 2026-09-15 `GROUP-ACCESS-002` production 群組 E2E 發現；非阻塞 |
| 21 | ONBOARDING-I18N-001 | P3 | **為新手 onboarding 內容建立多語審核與 fallback** | 以 `data/onboarding.yaml` 的 GCC owner 核准簡中 baseline 為來源，分別建立繁中／英文版本及 locale-specific `draft`／`published` 狀態；每個版本經人工核對後才發佈，未翻譯內容不得由 AI 臨時翻譯後冒充官方文字；定義缺少語言時的安全 fallback；內部、持續修改的飛書文件不直接成為 runtime 依賴，亦不把其 URL 寫入公開 production content | GCC owner 稍後提供翻譯／review 時間；內容 baseline 不代表已接入 runtime；非阻塞 |
| 22 | CONTENT-002 | P3 | **擴充案例覆蓋與 outcome evidence** | 完成 evidence 子清單 Tier B/C；按類別逐批 import、review、release；不以「67 個全部匯入」取代品質門檻 | Scope freeze；CONTENT-001、GOVERNANCE-001 |
| 23 | SEARCH-001 | P3 | **在 schema 穩定後評估 semantic search** | 先用 deterministic retrieval 建 baseline；量度準確率、引用率、成本及隱私；只有明顯優於 baseline 才引入 embeddings/vector store | Scope freeze；PGDATA-001、代表性 eval set |

## Done

| 日期 | ID | 原優先級 | 完成內容 | 證據 |
|---|---|---|---|---|
| 2026-09-15 | GROUP-ACCESS-002 | P1 | 指定 `GCC_GROUP_ID` 的現任 human `member`／`administrator`／`creator` 可使用私人一般問答；每次 live membership 查核、不升級帳戶；離群、blocked、Agent 或 API error fail closed；沿用每日限額及 private／group session 隔離；不開 Bot 內申請流程或新增管理能力；`/whoami` 反映有效資格 | PR #33／merge `7df1325`／Actions `34895178387` 完整測試及部署成功／production v65；owner 真實私訊 `/whoami` 得 `qa: yes`、一般及資助 link-first 問答正常且無申請按鈕；群組英文 explicit mention 正常；互動後 `/readyz`、`/opsz` 200、webhook pending 0、無 recent incident；英文正文配中文例會提醒另列 `I18N-001` |
| 2026-09-14 | ACCESS-001 | P1 | 正式收起 email verification：公開 onboarding／README／設定範例停止引導；legacy `/email`／`/verify` 只作三語 non-persisting 暫停回應；`/whoami` 隱藏 email；schema、dormant implementation 及 legacy data 保留待私隱政策；群組 mention-only QA 不變 | PR #31／merge `5f0ae98`／Actions `34787021266`／production v63；真實 `/start`、`/email`、`/verify` 通過；真實 `/whoami` 揭露 Markdown regression 後由 PR #32／merge `efe2ddb`／Actions `34790480003` 修復至 v64並通過；production aggregate 前後同為 users 2、verified 0、pending challenge 0、verified private message／draft 0；四項 readiness passing；容器 routing tests 通過；container 欠 `GH_SHA` 留待 RELEASE-001 |
| 2026-09-14 | PRIV-001B | P1 | 提供繁中／簡中／英文最低限度 current-state data notice；私訊 `/privacy` 毋須 email 或 member access，指定群組維持 explicit mention；兩者均不寫入 Bot SQLite 或消耗每日限額；`/start`、三份 README、維護／rollback 文件可找到；說明實際保存及 Telegram／Fly.io／OpenAI／SMTP／管理員 Telegram 接收，不虛構未批准的法律或 retention 承諾 | PR #29／merge `74d39f0`；Actions run `34760585478` 完整測試及 Fly deploy 成功；production v61／NRT machine started／encrypted `/data` mounted／四項 readiness passing／GH_SHA 相符；production container 7 項 notice／routing tests 通過；GCC owner 確認真實私訊及群組路徑均正常 |
| 2026-09-13 | PRIV-001A | P1 | 以 code、schema 及非敏感 production metadata 建立現行個人資料／data-flow 清冊；涵蓋六個 SQLite tables、session duplicate、Telegram／OpenAI／SMTP／Fly／GitHub、logs、admin notification、volume／snapshot／manual backup 及 public repo content；A–H 取代原本單一 PRIV-001，未決定或實作政策 | PR #27／merge `7148b17`；Actions run `34753531218` 完整測試及 Fly deploy 成功；production v59／NRT machine started／encrypted `/data` mounted／readiness passing／GH_SHA 相符；沒有讀 secret value、production row 或 Telegram 內容 |
| 2026-09-12 | OPS-001 | P1 | 補回不含敏感資料的 liveness／readiness／operations endpoints、Fly DB readiness check、Telegram webhook／backlog 監察、admin／deploy／machine 外部告警，以及完整 incident／rollback runbook | PR #22／merge `389322c`；Actions run `34651675306` 完整測試及 deploy 成功；production v54／machine started／Fly check passing／GH_SHA 相符；三個 endpoint 200、未授權 webhook 403；Telegram pending 0、無 last error；monitor run `34656207494` 成功、無 open incident |
| 2026-09-12 | QA-FACT-001 | P1 | 高風險資助政策問答改用繁／簡／英 deterministic link-first 與官方來源；一般 QA 移除內部百分制；明確區分公共／專項基金、Bot heuristic／人類決策，以及 Snapshot／實際執行 | PR #20／merge `96ca785`；Actions run `34644006225` compile、13 test files、Fly deploy 成功；production v52／machine started／GH_SHA 相符；容器內六類 route probe 正確；webhook pending 0、無 last error |
| 2026-09-11 | TEST-001 | P1 | 建立跨 Windows／Linux 的單一完整測試入口 `python -m tests`；逐檔隔離舊 executable suites 與 unittest，統一 UTF-8，消除 `tests/telegram` package shadowing；PR 與 main deploy 共用完整 gate；main ruleset 無 bypass 並要求 `Verify release` | PR #19／merge `38b747b`（PR #18 只合併至中間分支，故由 #19 正式帶入 main）；Windows 完整 suite 連續兩次通過、legacy discovery 33 tests；Actions run `34514061374` Linux gate／Fly deploy 成功；production machine v51；Node 20 action warning 留待 RELEASE-001 |
| 2026-09-10 | DATA-001 | P0 | Fly scheduled snapshots 已核實並保留 14 日；SQLite online backup／manifest 驗證工具、runbook、RPO 24h／RTO 2h、owner 及季度演練規則已建立；不同 zone restore drill 成功 | PR #15／merge `15932a4`；Actions run `34418412224`；production machine v48；on-demand snapshot 還原後 integrity OK、外鍵 0、migration 1–4、row counts 與 production 一致；臨時資源已清理；離站 object storage 待 `PRIV-001H` 與 owner 決定 |
| 2026-09-10 | GROUP-ACCESS-001 | P0 | 指定 GCC 群組已開放 mention-only、免 email 的一般 QA；不升級帳戶，不開放申請／管理；private／group／user／topic session 隔離 | PR #13／merge `f60825e`；Actions run `34169493168`；production `GCC_GROUP_ID=-1003962128595`；未驗證 regular user link-first E2E 成功；group session 為 general、2 messages、無 private session／draft 污染 |
| 2026-09-08 | SEC-001 | P0 | BotFather 舊 Telegram token 已 revoke；新 token 只透過 Fly secret 更新；machine v44 正常啟動 | 新 token `getMe` 200；`setWebhook` 200；webhook pending 0、無 last error；logs token 已 redacted |
| 2026-09-08 | SEC-002 | P0 | Telegram webhook 已設定長隨機 secret 並驗證來源 header；錯誤或缺少 secret 的 POST 被拒絕 | PR #12／merge `4760b24`；production `setWebhook` 200；secret header smoke test |
| 2026-09-07 | FLY-001 | P0 | Webhook 改為 `0.0.0.0:8080`；app/volume 統一 `nrt`；SQLite 掛載 `/data`；只保留一部常駐 machine；部署前有基本 test gate | PR #10／merge `e1e4a63`；Actions run `34065609326`；Fly machine v41 started/host ok；public webhook GET 405 |
| 2026-09-07 | LOG-001 | P0 | 修正非字串 URL logging argument 的 Telegram token redaction；production logs 抽查無 raw token | `tests/test_logging.py`；PR #10；production log assertion |
