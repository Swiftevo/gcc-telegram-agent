# GCC Telegram AI 助手

[简体中文](README.md) · **繁體中文** · [English](README.en.md)

**Global Chinese Community of Universal Digital Commons**

一個專為 GCC 社區設計的 Telegram AI 助手，作為 GCC 的第一道過濾器——回答基本問題、收集申請資料、預審申請者，再交棒給 GCC 人類成員進行深入判斷。

---

## 設計理念

這個 Agent 不是通用問答機器。它的核心任務是：

1. **過濾** — 問答與申請只服務已授權且完成驗證的 GCC 成員
2. **引導** — 優先給出官網連結，節省 token，回應更準確
3. **收集** — 四步驟收集申請者的基本資料
4. **預審** — 根據 GCC 價值觀對申請進行初步評分
5. **交棒** — 把有潛力的申請者轉介給 GCC 人類成員

Agent 的價值觀與審查邏輯儲存在獨立的 `values.yaml`，完全不受用戶對話影響，可隨時由管理員更新。

---

## 功能

- 身份與存取分離（`human/agent` + `regular/gcc_member`）
- 人類 GCC 成員郵箱驗證
- 每日訊息上限（預設 20 條，防止濫用）
- 三層 Prompt 架構（價值觀 → GCC 摘要 → 對話記錄）
- 連結優先邏輯（問及已知內容直接給官網連結）
- 三語支援（繁體中文 / 簡體中文 / 英文，跟隨用戶語言）
- 申請資料四步收集（項目名稱 → 基金類型 → 提案連結 → 執行摘要）
- Values Engine 預審評分（0-100 分）
- 管理員私訊通知（申請完成後自動發送摘要）
- `/status` 管理員統計指令
- `/update_values` 即時更新價值觀設定

---

## 技術架構

程式採用按功能組織的模組化單體。根目錄的 `db.py`、`models.py`、
`core/` 和 `handlers/` 只保留舊 import 相容入口；新功能應直接寫入
`gcc_agent/` 對應模組。

```text
gcc_agent/
├── access/                  # 身份、授權、郵箱驗證、請求 Guard
├── admin/                   # 管理員操作
├── applications/            # 申請流程、文案、預審和通知
├── common/
│   └── persistence/         # SQLite migrations 和 repositories
├── knowledge/               # GCC values、項目與案例載入
├── qa/                      # Prompt、連結優先和 AI 問答
├── telegram/                # Telegram 路由和 Application 裝配
└── config.py                # 環境變數設定

migrations/                  # 資料庫初始 schema
tests/                       # 新模組測試
main.py                      # 薄啟動入口
```

**技術棧：** Python 3.12 · python-telegram-bot · OpenAI API · SQLite · Fly.io

---

## 快速開始

### 前置要求

- Python 3.12+
- Telegram Bot Token（從 [@BotFather](https://t.me/BotFather) 取得）
- OpenAI API Key
- [Fly.io](https://fly.io) 帳號（用於部署）

### 1. Repo

```bash
git clone https://github.com/你的帳號/gcc-telegram-agent.git
cd gcc-telegram-agent
```

### 2. 建立虛擬環境並安裝依賴

```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 建立 .env 檔案

```bash
cp .env.example .env
```

編輯 `.env`，填入以下變數：

```env
BOT_TOKEN=你從 BotFather 取得的 Token
ADMIN_USER_ID=你的 Telegram User ID（數字）
GCC_GROUP_ID=GCC Telegram 群組 ID（負數）
OPENAI_API_KEY=你的 OpenAI API Key
ADMIN_NOTIFY_ID=接收申請通知的 Telegram User ID

# 郵箱驗證（未設定時會安全拒絕寄送）
EMAIL_VERIFICATION_SECRET=至少32字元的隨機秘密
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=SMTP帳號
SMTP_PASSWORD=SMTP密碼
SMTP_FROM=bot@example.com
SMTP_USE_TLS=true
```

> 取得 Telegram User ID：在 Telegram 找 [@userinfobot](https://t.me/userinfobot) 發任意訊息

身份拆成兩個互不混用的欄位：

- `actor_type`: `human` / `agent`
- `access_level`: `regular` / `gcc_member`

人類 GCC 成員必須先以 `/email` 和 `/verify` 完成郵箱驗證。普通用戶及
未授權 Agent 只收到歡迎訊息。舊資料中的 `user_kind` 會在啟動時由
版本化 migration 自動映射，原資料不會刪除。

### 4. 設定 values.yaml

編輯 `values.yaml`，填入你的組織使命、優先資助方向、審查邏輯。

把 `ADMIN_USER_ID` 替換為你真實的 Telegram User ID（數字）。

### 5. 本地測試

```bash
python main.py
```

看到 `Polling 模式啟動（本地開發）` 表示正常。在 Telegram 找你的 Bot 測試。

### 6. 執行測試套件

```bash
python -m unittest discover -s tests -v
```

測試依功能放在 `tests/access`、`tests/applications`、`tests/knowledge`、
`tests/persistence` 和 `tests/qa`。

---

## 部署到 Fly.io

### 1. 安裝 flyctl

```bash
curl -L https://fly.io/install.sh | sh
export PATH="$HOME/.fly/bin:$PATH"
flyctl auth login
```

### 2. 建立 App 和持久化磁碟

```bash
flyctl launch --no-deploy --name 你的app名稱
flyctl volumes create gcc_agent_data --region nrt --size 1
```

### 3. 上傳環境變數

```bash
flyctl secrets set \
  BOT_TOKEN="你的token" \
  ADMIN_USER_ID="你的user_id" \
  GCC_GROUP_ID="你的群組id" \
  OPENAI_API_KEY="你的key" \
  ADMIN_NOTIFY_ID="你的user_id" \
  WEBHOOK_URL="https://你的app名稱.fly.dev/webhook"
```

### 4. 部署

```bash
flyctl deploy
```

### 5. 設定 Telegram Webhook

目前 Webhook 只監聽 `127.0.0.1`。Fly.io 部署需要由同一實例中的反向代理
轉發，不能直接把本機監聽位址暴露到公網。

在瀏覽器打開：

```
https://api.telegram.org/bot你的BOT_TOKEN/setWebhook?url=https://你的app名稱.fly.dev/webhook
```

看到 `{"ok":true}` 表示設定成功。

---

## 更新價值觀設定

編輯 `values.yaml` 後有兩種方式生效：

**方式 A：重新部署（推薦）**
```bash
flyctl deploy
```

**方式 B：Telegram 指令（即時生效）**

在 Telegram 私訊 Bot 發送：
```
/update_values
```

只有 `ADMIN_USER_ID` 對應的帳號可以執行此指令。

---

## 管理員指令

| 指令 | 功能 |
|------|------|
| `/status` | 查看今日統計（用戶數、訊息數、token 消耗、申請數） |
| `/update_values` | 重新載入 values.yaml |

---

## values.yaml 結構說明

```yaml
version: "1.0.0"
admin_telegram_user_id: ADMIN_USER_ID

mission_statement: |
  組織使命描述...

priority_themes:
  - 優先資助方向 1
  - 優先資助方向 2

rejection_criteria:
  - 明確不考慮的申請類型

screening_rubric:
  mission_fit: 40        # 使命契合度（滿分 40）
  public_goods_nature: 30  # 公共物品屬性（滿分 30）
  chinese_community: 20   # 華語社區影響（滿分 20）
  feasibility: 10         # 可行性（滿分 10）

tone_guidelines: |
  回應語氣指引...

gcc_summary: |
  組織背景摘要（用於初次對話）...
```

預審評分結果：
- **≥ 70 分** → 通知管理員，建議深入跟進
- **40–69 分** → 提供資料連結，建議參與例會
- **< 40 分** → 禮貌說明不符合方向

---

## 對話記憶設計

- 每個用戶保留最近 **20 條**對話記錄
- **30 分鐘**無活動後自動開新 Session
- 不使用 AI 壓縮摘要，改以例會提醒引導深入交流
- 價值觀層（Layer 1）永遠排在對話記錄之前，不可被用戶覆蓋

---

## 授權

本項目以 [MIT](LICENSE) 授權開源。

---

## 關於 GCC

**Global Chinese Community of Universal Digital Commons**

GCC 支持以未來方式重塑公共物品的人與項目，立足華語，共連全球。

- 官方網站：[gccofficial.org](https://www.gccofficial.org)
- 資助申請：[gccofficial.org/application](https://www.gccofficial.org/application)

