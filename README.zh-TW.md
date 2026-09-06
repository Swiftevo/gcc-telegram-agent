<div align="center">

<img src="docs/assets/banner.jpg" alt="GCC Telegram AI 助手" width="100%">

# GCC Telegram AI 助手

面向公共物品的 Telegram AI 助手：回答問題、收集資助申請、完成初步篩選。

[![Telegram](https://img.shields.io/badge/Telegram-@GCCpublicgoods__bot-2CA5E0?logo=telegram&logoColor=white)](https://t.me/GCCpublicgoods_bot)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Website](https://img.shields.io/badge/Website-gccofficial.org-1a1a1a)](https://www.gccofficial.org)
[![Contributing](https://img.shields.io/badge/Contributing-guide-orange.svg)](CONTRIBUTING.md)

[简体中文](README.md) · **繁體中文** · [English](README.en.md)

[貢獻指南](CONTRIBUTING.md) · [行為準則](CODE_OF_CONDUCT.md) · [參與貢獻](#參與貢獻)

</div>

---

## 立即試用

助手已經部署上線，在 Telegram 裡打開 **[@GCCpublicgoods_bot](https://t.me/GCCpublicgoods_bot)** 發送 `/start` 即可開始。

普通用戶會收到歡迎訊息；GCC 成員通過郵箱驗證後，可以使用問答和資助申請功能。

想改程式或提 Issue，請先看 [貢獻指南](CONTRIBUTING.md)。Pull Request 請開向 `dev`，不要直接推 `main`。

## 這個專案解決什麼問題

新成員的問題大多重複：GCC 在做什麼、資助怎麼申請、我的專案合不合適。這些問題過去要在群裡反覆回答。

這個助手把這部分工作接過來：能用官網連結回答的直接給連結，需要判斷的先收集材料並按 GCC 價值觀打分，再交給成員跟進。

## 核心功能

| 功能 | 說明 |
|---|---|
| 分級存取 | 普通用戶和未授權 Agent 只收到歡迎訊息 |
| 郵箱驗證 | GCC 成員驗證郵箱後解鎖問答與申請 |
| 連結優先 | 能用官網連結回答的問題不呼叫模型 |
| 多語言 | 依用戶語言使用簡體中文、繁體中文或英文 |
| 申請流程 | 四步收集：專案名稱、基金類型、提案連結、執行摘要 |
| 初步篩選 | 依據 `values.yaml` 給出 0–100 分並通知管理員 |
| 用量限制 | 每位成員每天最多 20 條訊息 |

## 指令

面向成員：

```text
/email you@example.com      綁定郵箱並接收驗證碼
/verify 123456              提交驗證碼
/whoami                     查看目前身份
```

面向管理員：

```text
/grant <user_id 或 @username> regular|gcc_member|ai
/status                     查看統計
/update_values              重新載入價值觀
```

GCC Telegram 群的 `member`、`administrator`、`creator` 以及 `ADMIN_USER_ID` 可以為其他用戶設定身份。

## 身份模型

身份由兩個獨立欄位組成，不使用 RBAC：

- `actor_type`：`human` 或 `agent`
- `access_level`：`regular` 或 `gcc_member`

人類 GCC 成員必須通過 `/email` 和 `/verify` 驗證郵箱。舊資料庫中的 `user_kind` 會在啟動時自動遷移，不會刪除原有資料。

## 快速開始

需要 Python 3.12。

```bash
git clone https://github.com/Swiftevo/gcc-telegram-agent.git
cd gcc-telegram-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

在 `.env` 中填入設定：

```env
BOT_TOKEN=Telegram Bot Token
ADMIN_USER_ID=管理員 Telegram User ID
ADMIN_NOTIFY_ID=接收申請通知的 Telegram User ID
GCC_GROUP_ID=GCC Telegram 群組 ID

OPENAI_API_KEY=OpenAI API Key
AI_MODEL=gpt-4o-mini
AI_MAX_TOKENS=800

DB_PATH=gcc_agent.db

# 郵箱驗證；未完整設定時會安全拒絕發送
EMAIL_VERIFICATION_SECRET=至少32字元的隨機秘密
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=SMTP帳號
SMTP_PASSWORD=SMTP密碼
SMTP_FROM=bot@example.com
SMTP_USE_TLS=true
```

> [!WARNING]
> 不要把 `.env`、Token、密碼或金鑰提交到 Git。

啟動：

```bash
python main.py
```

沒有設定 `WEBHOOK_URL` 時使用 Telegram polling。

執行測試：

```bash
python -m unittest discover -s tests -v
```

## 專案結構

專案採用按功能組織的模組化單體：

```text
gcc_agent/
├── access/                  # 身份、授權、郵箱驗證和 Guard
├── admin/                   # 管理員操作
├── applications/            # 申請流程、文案、篩選和通知
├── common/
│   └── persistence/         # SQLite 遷移和 repositories
├── knowledge/               # GCC 價值觀、專案和案例
├── qa/                      # Prompt、連結優先和 AI 問答
├── telegram/                # Telegram 路由和應用裝配
└── config.py                # 環境變數

migrations/                  # 資料庫初始結構及版本遷移
tests/                       # 按功能組織的測試
main.py                      # 啟動入口
```

根目錄的 `db.py`、`models.py`、`core/` 和 `handlers/` 是舊 import 的相容入口。新程式應放在 `gcc_agent/` 對應模組。

技術棧：Python 3.12、python-telegram-bot、OpenAI API、SQLite、Fly.io。

## 價值觀與預審

`values.yaml` 保存 GCC 使命、資助方向、拒絕條件、語氣和評分權重。修改後重新部署，或私訊 Bot 發送 `/update_values` 生效。

預設評分權重：

| 維度 | 權重 |
|---|---|
| 使命契合度 | 40 |
| 公共物品屬性 | 30 |
| 華語社區影響 | 20 |
| 可行性 | 10 |

結果僅用於初步篩選，不代表最終決定：

- **≥ 70**：建議管理員跟進
- **40–69**：建議參加例會進一步了解
- **< 40**：可能不符合目前方向

## 資料與對話記憶

- 用戶、會話、訊息和申請草稿保存在 SQLite
- GCC 專案和案例保存在 YAML/Markdown
- 每位用戶保留最近 20 條對話
- 30 分鐘無活動後建立新 Session
- 價值觀 system prompt 始終位於用戶對話之前

## 部署

以 Fly.io 為例：

```bash
flyctl auth login
flyctl launch --no-deploy --name 你的應用名稱
flyctl volumes create gcc_agent_data --region nrt --size 1
flyctl secrets set \
  BOT_TOKEN="..." \
  ADMIN_USER_ID="..." \
  ADMIN_NOTIFY_ID="..." \
  GCC_GROUP_ID="..." \
  OPENAI_API_KEY="..." \
  WEBHOOK_URL="https://你的應用名稱.fly.dev/webhook" \
  WEBHOOK_LISTEN="0.0.0.0"
flyctl deploy
```

設定 Telegram Webhook：

```text
https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=https://<應用名>.fly.dev/webhook
```

> [!IMPORTANT]
> 在 Fly.io 上，Webhook 必須監聽 `0.0.0.0` 和 `fly.toml` 的 `internal_port`，否則 Fly 無法把 Telegram webhook 請求轉發給應用。本地調試如需只監聽 localhost，可設定 `WEBHOOK_LISTEN=127.0.0.1`。

## 參與貢獻

歡迎提交 Issue 和 Pull Request。完整流程和約定見 [CONTRIBUTING.md](CONTRIBUTING.md)，參與時請遵守 [行為準則](CODE_OF_CONDUCT.md)。

簡要流程：

1. 從 `dev` 拉出 `feat/` 或 `fix/` 分支
2. 改動保持聚焦，並補上對應測試
3. 提交前執行 `python -m unittest discover -s tests -v`
4. 向 **`dev`** 開 Pull Request，不要直接推 `main`

Issue 標題帶上 `新功能`、`缺陷`、`文檔` 等類型詞，GitHub Actions 會按內容和改動路徑自動打標籤。提交說明請寫 `Refs #編號` 或 `Fixes #編號` 以關聯 Issue。

## 關於 GCC

GCC（Global Chinese Community of Universal Digital Commons）支持以未來方式重塑公共物品的人與專案，立足華語，共連全球。

- 官網：[gccofficial.org](https://www.gccofficial.org)
- 資助申請：[gccofficial.org/application](https://www.gccofficial.org/application)

## 授權

本專案採用 [MIT License](LICENSE)。
