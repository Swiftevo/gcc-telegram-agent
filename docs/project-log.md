# GCC Telegram Agent Project Log

這份日記記錄已核實的產品、技術、營運與 public-goods 決策。它不是待辦清單；
尚未完成的工作及其唯一執行順序，以 [`docs/todo.md`](todo.md) 為準。

## 2026-09-16：建立兩條獨立資助線的後續案例入口

- GCC owner 確認 ETH City 與高校 Web3 興趣小組是兩條獨立資助線；現有 2025
  Snapshot 是共同提案來源，並非單一個別受助案例，也不證明實際撥款。
- 兩條線各有固定識別碼；日後每個已核實個別案例以 `funding_track_id` 指向其中一條，
  金額、日期、成果和來源留在該案例，不混合兩個資助池。入口及所需資料見
  [`funding-track-case-intake.md`](funding-track-case-intake.md)。
- ETH Beijing 2025、Devconnect 機票 2025 暫無 owner 可補的詳細資料；不補猜測。
  現有 ETH Beijing 案例不因名稱而自動歸入 ETH City 資助線。
- 共同提案不再標作可供 AI review 使用；本次只建立資料入口及測試，沒有新增個別資助案例、
  改 Bot runtime 或開放 AI 評分。87 項本地回歸測試通過；
  證據、私隱及撥款核對工作仍按 [`docs/todo.md`](todo.md) 跟進。

## 2026-09-15：`GROUP-ACCESS-002` 完成，群組成員可使用私人一般問答

- GCC owner 指出 email verification 收起後，普通私人訊息只餘 welcome，明確決定讓
  `GCC_GROUP_ID` 指定群組的現任 Telegram 成員同時取得私人一般問答能力。
- Production 預查使用 owner 提供的 Telegram user ID，只輸出 membership status；Bot API
  成功從指定群組回傳 `creator`，沒有讀 token、profile、訊息或其他成員資料，證明現有 Bot
  權限可支援 live `getChatMember` 判斷。
- 邊界定為只接受 human `member`／`administrator`／`creator`，每次私人一般訊息即時查核；
  不依賴舊 cache，不永久升級 `gcc_member`。離群、kicked、blocked、Agent、群組未設定或
  Telegram API error 一律 fail closed。
- 私人 membership QA 沿用每日 20 條限制和私人 session；一般問答不開申請按鈕、不進
  application session，也不新增管理能力；既有專用命令治理仍留在 `ACCESS-002`。`/start`、`/privacy`、已暫停的 `/email`／`/verify` 專用路徑
  不變；`/whoami` 將以 live membership 準確反映 QA 資格。
- PR #33 已 merge（`7df1325f3c4d0972a00e02874d41ba732abaf2d5`）；Actions run
  `34895178387` 完整測試及 Fly deploy 成功，production machine v65、Fly check passing。
- GCC owner 真實私訊 `/whoami` 得到 `qa: yes`；私人一般問題正常回答，資助問題使用官方
  link-first 回覆且沒有申請按鈕。指定群組英文 explicit mention 亦正常回覆。互動後
  `/readyz`、`/opsz` 均為 HTTP 200，webhook pending `0`，沒有 recent incident。
- 群組英文問題的正文為英文，但固定例會提醒依 Telegram locale 顯示中文；不影響本項
  存取、session 或安全驗收，已另列低優先、非阻塞 `I18N-001`，不在收尾 PR 順手改行為。
- `GROUP-ACCESS-002` 已移入 Done；`PRIV-001C` 至 `PRIV-001H` 沒有因此自動開始。驗收及
  rollback 邊界見 [`group-member-private-qa.md`](group-member-private-qa.md)。

## 2026-09-14：`ACCESS-001` 完成，email verification 已收起

- GCC owner 在 `PRIV-001B` production 驗收後明確決定先收起整個 email verification；
  這次只停止入口及新資料處理，不刪 schema、implementation 或任何 production／backup
  歷史資料，也不自動開始 `PRIV-001C` 至 `PRIV-001H`。
- 動手前以唯讀 aggregate 查核 production：`users=2`、已驗證用戶 `0`、已驗證用戶的
  private messages `0`、已驗證用戶的 application drafts `0`、pending email challenges
  `0`；沒有讀取身份、email、訊息或申請內容。因此無須為現行已驗證用戶設過渡路徑。
- 實作邊界定為：公開 onboarding／README／設定範例移除 email 入口；legacy `/email`、
  `/verify` 只回三語暫停訊息，且不讀指令參數、不建立 user／challenge、不呼叫 SMTP；
  `/whoami` 不再顯示 email 欄位。群組 mention-only QA、`/privacy` 及既有 session 隔離
  不變。
- SQLite email 欄位、challenge table、persistence 及 sender 程式暫時保留為 dormant
  compatibility surface，避免在 retention／deletion 政策前破壞歷史資料；後續由
  `PRIV-001D/F/G` 決定 legacy data 的保存、清理及用戶權利流程。
- PR #31 已 merge（`5f0ae989242c1a9b4276732412cbde9a9a80149a`）；Actions run
  `34787021266` 完整測試及部署成功，production machine v63、四項 readiness passing。
  GCC owner 真實驗收 `/start`、`/email`、`/verify` 均符合預期。
- 首次真實 `/whoami` 暴露本輪移除 `email_verified` 行後留下奇數 Markdown underscore，
  Telegram 以 HTTP 400 拒絕訊息並觸發 `unhandled_update_error` 告警。PR #32 隨即改用純文字
  並加入回歸測試；merge `efe2ddb5efbb6277e1a255870b1d2bd03cbebb6e`、Actions run
  `34790480003` 成功部署 production v64，owner 重測得到正確 identity／`qa: no`，沒有 email
  或新告警。這項真實失敗及修復均保留在完成證據，不以原本綠燈測試掩蓋。
- 驗收後再次唯讀查核，aggregate 與變更前相同：`users=2`、verified users `0`、pending
  email challenges `0`、verified private messages `0`、verified application drafts `0`；
  `/email`／`/verify` 沒有新增驗證資料。沒有讀 identity、email、訊息或 draft 內容。
- 群組路徑沒有被本項修改，production container 的 email／privacy／group routing tests
  通過；schema、legacy data、volume、snapshots 亦沒有刪改。Container 缺少可直接核對的
  `GH_SHA` 是既有 release traceability 缺口，留在 `RELEASE-001`，不虛構已核對。
- `ACCESS-001` 已移入 Done；legacy data 仍由 `PRIV-001D/F/G` 跟進。詳細行為及回復邊界
  見 [`email-verification-shelving.md`](email-verification-shelving.md)。

## 2026-09-14：`PRIV-001B` 最低限度資料告知完成

- GCC owner 在 `PRIV-001A` 完成後明確選定 `PRIV-001B` 為下一項；這項授權不自動延伸
  至 `PRIV-001C` 至 `PRIV-001H`。
- 依已核實的 data map 建立繁中、簡中及英文 current-state notice，涵蓋實際處理資料、
  Telegram／Fly.io／OpenAI／SMTP／管理員 Telegram 接收、現況保存缺口及 GCC 官方
  contact 頁；不宣稱尚未批准的法律基礎、controller、保存日數或資料要求程序。
- 私訊 `/privacy` 不要求 email、member 或 QA access；指定 GCC 群組只回應 explicit
  mention 的 privacy request。兩條路徑均不建立 Bot SQLite user／session／message row，
  也不消耗每日限額。`/start` 及三份 README 提供入口。
- [`docs/privacy-notice.md`](privacy-notice.md) 定義文案必備事實、語言 fallback、變更觸發、
  技術 owner、production smoke test 及 rollback。技術 owner 沿用 GCC bot operator；這不
  等同指定法律 data controller 或正式 privacy contact，後者仍由 `PRIV-001H` 決定。
- PR #29 已 merge（`74d39f09a3f6d3288af590d7b84e65097cf90b4c`）；Actions run
  `34760585478` 的完整測試及 Fly deploy 成功。Production v61 的 `GH_SHA` 與 merge
  commit 相符，NRT machine started、encrypted `/data` volume 保持掛載，application、
  webhook、database 及 Telegram readiness 全部 passing。
- Production container 內六項 notice tests 及群組 non-persistence routing test 全部通過；
  GCC owner 隨後在真實 Telegram 確認私訊 `/privacy` 及指定群組 explicit-mention
  `/privacy` 均正常。`PRIV-001B` 已移入 Done；`PRIV-001C` 至 `PRIV-001H` 沒有因此開始。

## 2026-09-13：`PRIV-001` 拆分並開始現況資料盤點

- 原本把資料盤點、用戶告知、對話／身份／申請保存政策、自動清理、匯出／刪除、
  backups／logs／第三方和 production 存取放在一起的 `PRIV-001` 太大，現拆為
  `PRIV-001A` 至 `PRIV-001H`，各自有獨立出口條件。
- 本輪只批准 `PRIV-001A`。B–H 的排列仍待 GCC owner 看完盤點後重新確認，不因列入
  TODO 而自動授權下一項工作。
- `PRIV-001A` 以 main `d4be4206b1113146b4d6aa49c802a6030917c9c2` 為基準，建立
  [`docs/privacy-data-map.md`](privacy-data-map.md)，盤點六個 SQLite tables、重複 session
  storage、Telegram／OpenAI／SMTP／Fly／GitHub 接收、logs、管理員通知、volume／snapshot／
  manual backup 及 public repository content。
- 核對 production 時只讀取 secret 名稱及非敏感 metadata，沒有讀 secret value、SQLite
  row、Telegram 對話或管理員 chat，也沒有更改 runtime／Fly／用戶資料。Production secret
  名稱目前沒有 SMTP 或 `EMAIL_VERIFICATION_SECRET`，所以 email path 現時 fail closed；
  這不代表 database 沒有歷史 email。
- 關鍵發現：30 分鐘只令舊 session 不再被選取，最近 20 條只限制 AI context；兩者均不會
  刪除 `sessions.messages_json` 或獨立 `messages` rows。現行申請 draft 完成後仍在 session，
  並另有管理員 Telegram notification 副本。
- 這次只建立 verified current-state inventory 及重整 TODO，沒有新增 privacy notice、
  retention 承諾、cleanup、export／delete 或 access policy。PR #27 已 merge
  （`7148b17012fd3fa4593bd93ad1a2063e989a0fc2`）；Actions run `34753531218` 的完整
  測試及 Fly deploy 成功。Production v59 的 `GH_SHA` 與 merge commit 相符，NRT machine
  started、encrypted `/data` volume 保持掛載且 readiness passing，故 `PRIV-001A` 已移入
  Done；其後 GCC owner 已另行選定 B，C–H 仍待逐項排序及授權。

## 2026-09-12：採用 trunk-based，長期 `dev` branch 已移除

- GCC 決定現階段採用 `main` 為唯一長期 release branch；每項工作由最新 `main` 建立
  短期 `feat/`、`fix/`、`docs/` 或 `chore/` branch，經 PR、required checks 及適用的
  review 後合併到 `main`，再由既有 workflow 部署 production。
- 決策前核對顯示 `dev` 比 `main` 落後 33 commits、沒有任何只存在於 `dev` 的 commit，
  亦沒有以 `dev` 為來源或目標的 open PR。PR #25 先把三份 README、`CONTRIBUTING.md`
  及 label sync workflow 改為 trunk-based；`Verify release` 及 main Actions run
  `34685910481` 的完整測試／Fly deploy 均成功。
- PR #25 合併後再次核對：default branch 是 `main`；`dev` 落後 35 commits、仍為 0 個
  獨有 commit，且沒有 open PR。其 remote ref 隨後刪除，`ls-remote` 查詢為空，GitHub
  branch API 回傳預期 404；沒有刪除任何獨有程式碼或本機工作分支。
- 日後若建立真正 staging／integration 需要，可從當時的 `main` 重新建立 `dev`；必須先
  配置 ruleset、完整 PR gate、owner 及 promotion 規則，才接受 contributor 變更。
- 這項只落實 branch model 決定；敏感路徑 CODEOWNERS、選擇性非作者批准、AI Agent
  onboarding、backup operator 訓練及最小權限仍由 `REPO-GOV-001` 後續完成。

## 2026-09-12：拆分 release tooling、rollback 演練與 contributor governance

- Repository 最近新增三位 collaborators；電郵功能亦由其中一位 contributor 提交，
  而非由 `Swiftevo` 單獨開發。預期往後會有多人增減功能，因此 release 流程除了技術
  gate，也需要明確的 ownership、review、merge、hotfix 及權限邊界。
- 多人協作不自動代表必須採用 `dev`。目前 `main` 有 required PR／`Verify release` 及
  no-bypass ruleset，但 required approval count 為 0；`dev` 存在卻沒有 ruleset，PR
  targeting `dev` 也不會執行 release gate。是否採 trunk-based、保留真正 integration
  branch、要求獨立 approval，以及是否設 CODEOWNERS，集中交由新項目
  `REPO-GOV-001` 決定和落實，列為最高的 P2 工作。
- `REPO-GOV-001` 同時必須補回跨 AI Agent onboarding：建立單一 canonical
  `docs/ai-agent-guide.md`，涵蓋開工前必讀順序、scope／TODO 約束、架構邊界、敏感資料、
  production 操作授權、事實來源、完整測試及完成記錄；再按實際使用工具提供薄入口檔
  （例如根目錄 `AGENTS.md`、`CLAUDE.md` 或 `.github/copilot-instructions.md`），只引用
  canonical guide，避免多份規則漂移。另以 PR template 要求 scope、測試、私隱／資料、
  production 驗收及 rollback 說明。
- `RELEASE-001` 收窄為已確認的 supply-chain／reproducibility 修復：把所有 GitHub
  Actions 及 Fly deployment tooling 從可浮動 tag／`master` 鎖到不可變版本，建立受
  review 的更新政策，並驗證 main release 可追溯至同一 tested commit。它不再以未完成
  的 branch-model 決策或 rollback 演練作為同一 PR 的出口條件。
- 實際 image rollback rehearsal 拆為 `RELEASE-DRILL-001`：先在不使用 production
  Telegram token、production SQLite volume 或真實用戶流量的隔離環境完成向前／向後
  切換；任何 production drill 必須另有 maintenance window 及授權。這項列為 P2，
  依賴 `RELEASE-001`、既有 OPS runbook 及 DATA restore 邊界。
- 這次只調整 scope 與 canonical TODO，沒有更改 GitHub permissions／rulesets、workflow、
  Fly、runtime 或 production data。在 `REPO-GOV-001` 完成前，現有 protected-main gate
  繼續生效，但不能把「有 PR」等同「已有獨立人類批准」。

## 2026-09-12：`OPS-001` production 健康檢查、告警與 runbook 完成

- 公開 ingress 現提供三個不含敏感資料的 operational endpoints：`/healthz` 只反映
  process liveness；`/readyz` 檢查 application、webhook、Telegram 初始化及 SQLite
  schema／write-lock readiness；`/opsz` 再涵蓋 Telegram webhook、積壓量及近期 incident。
  DB probe 在背景定時執行並由 endpoint 讀取 cache，避免公網請求直接放大 DB 負載。
- Telegram webhook handler 移到 `127.0.0.1:8081`，由 `0.0.0.0:8080` 的薄 ingress
  只代理 `/webhook`；secret header 驗證仍由 Telegram application handler 執行。
- machine／DB readiness 由 Fly 每 15 秒檢查；Telegram webhook error／backlog 及
  admin notification failure 會發送不含用戶內容的去重 admin 告警。main deploy failure
  及外部 `/opsz` 失敗會開立單一 durable GitHub issue，恢復後自動關閉。
- 新增 operations runbook，記錄 owner、endpoint contract、告警矩陣、incident triage、
  webhook／DB 處理、image rollback 及季度演練要求。PR #22 已合併至 main（merge
  `389322c`）；Actions run `34651675306` 的 compile、完整測試及 Fly deploy 均成功。
- Production release v54／machine `7813de2bdd3638` 在 `nrt` 為 started，image label
  `GH_SHA=389322ccbf619c75a4ddff9c6f1f783914be9ed5`，`/data` encrypted volume 仍掛載，
  Fly `/readyz` check 為 passing。公開 `/healthz`、`/readyz`、`/opsz` 均回 200；
  `/webhook` GET 為 405，缺少 secret 的 POST 為 403。
- Telegram `getWebhookInfo` 指向 production host、pending updates 為 0、無 last error；
  手動 workflow_dispatch 的 Production Readiness Monitor run `34656207494` 成功，沒有
  open incident issue。驗收沒有向真實群組發訊息、注入假 update 或故意製造 outage；
  故障分支由自動測試覆蓋，首次季度演練仍須按 runbook 執行及留下證據。

## 2026-09-12：正式申請改用外置表格，降低 `APP-001` 優先級

- GCC 決定正式申請由外置表格收集，不再優先建設 Bot 內的 application database、
  status model、通知重試及提交追蹤系統。
- `APP-001` 降為 P2 scope-reduction：其後只需把 Bot 申請入口清楚導向官方外置表格，
  移除本機四步收集、管理員通知及舊百分制的正式提交暗示；現存資料的保留／刪除由
  `PRIV-001E` 決定。
- `REVIEW-001` 相應收窄為移除 Bot 的假精確評分，而不是建立新的申請決策系統。
- 下一個優先項改為 `OPS-001`，其後依次為私隱、管理身份生命週期、release 治理及
  移除舊評分。

## 2026-09-12：`QA-FACT-001` 官方事實邊界完成

- 資助／評審流程、公開準則、評選時間、正式評分、來源追問，以及
  Snapshot 決定與實際執行，現先經繁／簡／英 deterministic link-first 路由；這些
  高風險答案不再交由語言模型推斷。
- 公開流程只引用 GCC 官網已核實內容；明確說明官網沒有公布 40/30/20/10 權重、
  70/40 門檻或各階段分別需時。公共基金與專項基金不再混為同一套細節。
- 一般 QA system prompt 已移除舊百分制。現有 application heuristic 暫時只供管理員
  初步整理，通知明確標成「非 GCC 正式評分」；完整 evidence triage 仍由
  `REVIEW-001` 處理。
- Snapshot 簽署／投票不再被描述成實際撥款、milestone 驗收或款項解鎖；未核實
  執行狀態保留為 unknown，交由 `GRANT-RECON-001` 核對。
- PR #20 合併至 main（merge `96ca785`）。PR `Verify release` 及 main Actions run
  `34644006225` 的 compile、13 個完整 test files 與 Fly deploy 全部成功。
- Production release v52／machine `7813de2bdd3638` 在 `nrt` 為 started；image label
  `GH_SHA=96ca785e399bd442127f084126efd368c8534e3f`。啟動 logs 顯示 database
  `/data/gcc_agent.db`、webhook `0.0.0.0:8080`、Telegram `getMe`／`setWebhook` 均正常。
- v52 容器內唯讀 smoke probe 確認六類代表問法命中預期 fact route，官方連結及
  unknown 邊界正確；Telegram webhook 指向 production host、pending updates 為 0、
  無 last error。驗證沒有向真實群組發訊息或注入假 update。

## 2026-09-11：`TEST-001` 完整跨平台 release gate 完成

- 新增唯一完整測試入口 `python -m tests`，自動找出所有 test files，並把舊 executable
  suites 與 unittest modules 放在獨立 processes 執行；由此隔離各測試的 SQLite 路徑、
  environment mutation 及殘留 connection。
- Runner 強制 UTF-8，修正 Windows CP950 無法輸出測試符號而中止的問題；
  `tests/telegram` 改為 `tests/telegram_bot`，不再遮蔽安裝的 Telegram package。
- Windows 完整 suite 連續兩次通過；舊 discovery 亦由 6 個 import errors 變成 33 tests
  全過。Linux GitHub Actions 的 `Verify release` 執行完整 command 並成功。
- Pull requests targeting `main` 現在先通過相同 gate；Fly deploy 只在已測試的 main push
  執行，PR event 會明確 skip deployment。
- `Project main` ruleset 已 active：target default branch、無 bypass、禁止 delete／force
  push、必須經 PR、解決 review threads、branch up to date，並要求 GitHub Actions 的
  `Verify release`。
- PR #18 因 stacked base 已先合併，只進入中間分支；PR #19 將相同兩個 commits 正式
  合併至 main（merge `38b747b`）。Actions run `34514061374` 的 test 及 Fly deploy
  成功；production machine `7813de2bdd3638` 更新至 v51，在 `nrt` 為 started，webhook
  `0.0.0.0:8080`、database `/data/gcc_agent.db`、Telegram `getMe`／`setWebhook` 均正常。
- Actions 顯示 Node.js 20 deprecation warning，但由 GitHub 強制以 Node 24 成功執行；
  workflow action version／更新政策仍由 `RELEASE-001` 跟進。

## 2026-09-11：隔離 Snapshot／實際執行衝突，凍結新功能

- GCC 確認：Snapshot 簽署與真實資助執行、milestone 驗收／解鎖可能有出入，現正由
  專人跟進核對。往後資料模型及內容必須把 governance decision、actual disbursement、
  milestone acceptance 和 unlock 分開，不可由簽署結果推定實際執行。
- 未完成核對的金額、付款和 milestone claim 保留所有來源，標成
  `unknown`／`pending_reconciliation`，不進 bot 事實回答、案例比較或申請 review；
  相關工作集中到 `GRANT-RECON-001`，不阻塞其他非衝突內容及可靠性修復。
- 本輪 bot 實測顯示「GCC 評審流程」回答把 repository 內部 40/30/20/10 權重及
  70/40 門檻表述成正式政策，亦沒有準確交代盡調、投委決策與 milestone 管理。
  這是現有 QA 的 correctness bug，不是新增內容需求，新增 `QA-FACT-001` 優先修復。
- 現階段 scope freeze：除資助項目資料整理及申請評審修復外，不增加產品能力。
  順序先處理完整測試入口、QA 事實邊界、申請持久化／通知、假精確評分、私隱、
  health／告警、管理命令及 release gate；metrics、案例擴量及 semantic search 留後。
- 電郵驗證按先前決定繼續暫緩；其後應由 GCC 明確選擇完成、收窄或移除，不讓
  一個不可用的既有入口長期停留在模糊狀態。
- 這次只重整 canonical TODO、evidence 子清單及資料設計原則，沒有改動 runtime、
  production data 或 Fly 設定。

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
  GCC 指定 storage account owner 及 `PRIV-001H` 確定含個人資料備份的保留／刪除政策。
- PR #15 已 merge（`15932a4`）；GitHub Actions run `34418412224` 的 compile、既有
  regression suites、新增 SQLite backup tests 及 Fly deploy 全部成功。
- Production machine `7813de2bdd3638` 已更新至 version 48，原 `nrt` volume 保持掛載；
  新 image 內的 `sqlite_backup verify` 直接檢查 `/data/gcc_agent.db` 成功：
  `integrity_check=ok`、外鍵違規 0、migration 1–4。部署後 bot 繼續成功處理 Telegram
  和 OpenAI 回覆，logs 沒有新 traceback，token 保持 redacted。
- 驗收完成後 `DATA-001` 移入 Done。現存 snapshots 在 retention 更新前建立，仍顯示
  5 日；volume 現行設定為 14 日，下一個 scheduled snapshot 應再核對其個別 retention。
  離站 object storage 未啟用的風險保留至 `PRIV-001H` 和 storage owner 決定。

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
