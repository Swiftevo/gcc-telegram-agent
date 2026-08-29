<div align="center">

<img src="docs/assets/banner.jpg" alt="GCC Telegram AI 助手" width="100%">

# GCC Telegram AI 助手

面向公共物品的 Telegram AI 助手：回答问题、收集资助申请、完成初步筛选。

[![Telegram](https://img.shields.io/badge/Telegram-@GCCpublicgoods__bot-2CA5E0?logo=telegram&logoColor=white)](https://t.me/GCCpublicgoods_bot)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Website](https://img.shields.io/badge/Website-gccofficial.org-1a1a1a)](https://www.gccofficial.org)
[![Contributing](https://img.shields.io/badge/Contributing-guide-orange.svg)](CONTRIBUTING.md)

**简体中文** · [繁體中文](README.zh-TW.md) · [English](README.en.md)

[贡献指南](CONTRIBUTING.md) · [行为准则](CODE_OF_CONDUCT.md) · [参与贡献](#参与贡献)

</div>

---

## 立即试用

助手已经部署上线，在 Telegram 里打开 **[@GCCpublicgoods_bot](https://t.me/GCCpublicgoods_bot)** 发送 `/start` 即可开始。

普通用户会收到欢迎信息；GCC 成员通过邮箱验证后，可以使用问答和资助申请功能。

想改代码或提 Issue，请先看 [贡献指南](CONTRIBUTING.md)。Pull Request 请开向 `dev`，不要直接推 `main`。

## 这个项目解决什么问题

新成员的问题大多重复：GCC 在做什么、资助怎么申请、我的项目合不合适。这些问题过去要在群里反复回答。

这个助手把这部分工作接过来：能用官网链接回答的直接给链接，需要判断的先收集材料并按 GCC 价值观打分，再交给成员跟进。

## 核心功能

| 功能 | 说明 |
|---|---|
| 分级访问 | 普通用户和未授权 Agent 只收到欢迎信息 |
| 邮箱验证 | GCC 成员验证邮箱后解锁问答与申请 |
| 链接优先 | 能用官网链接回答的问题不调用模型 |
| 多语言 | 按用户语言使用简体中文、繁体中文或英文 |
| 申请流程 | 四步收集：项目名称、基金类型、提案链接、执行摘要 |
| 初步筛选 | 依据 `values.yaml` 给出 0–100 分并通知管理员 |
| 用量限制 | 每位成员每天最多 20 条消息 |

## 命令

面向成员：

```text
/email you@example.com      绑定邮箱并接收验证码
/verify 123456              提交验证码
/whoami                     查看当前身份
```

面向管理员：

```text
/grant <user_id 或 @username> regular|gcc_member|ai
/status                     查看统计
/update_values              重新载入价值观
```

GCC Telegram 群的 `member`、`administrator`、`creator` 以及 `ADMIN_USER_ID` 可以为其他用户设置身份。

## 身份模型

身份由两个独立字段组成，不使用 RBAC：

- `actor_type`：`human` 或 `agent`
- `access_level`：`regular` 或 `gcc_member`

人类 GCC 成员必须通过 `/email` 和 `/verify` 验证邮箱。旧数据库中的 `user_kind` 会在启动时自动迁移，不会删除原有数据。

## 快速开始

需要 Python 3.12。

```bash
git clone https://github.com/Swiftevo/gcc-telegram-agent.git
cd gcc-telegram-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

在 `.env` 中填入配置：

```env
BOT_TOKEN=Telegram Bot Token
ADMIN_USER_ID=管理员 Telegram User ID
ADMIN_NOTIFY_ID=接收申请通知的 Telegram User ID
GCC_GROUP_ID=GCC Telegram 群组 ID

OPENAI_API_KEY=OpenAI API Key
AI_MODEL=gpt-4o-mini
AI_MAX_TOKENS=800

DB_PATH=gcc_agent.db

# 邮箱验证；未完整配置时会安全拒绝发送
EMAIL_VERIFICATION_SECRET=至少32字符的随机秘密
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=SMTP账号
SMTP_PASSWORD=SMTP密码
SMTP_FROM=bot@example.com
SMTP_USE_TLS=true
```

> [!WARNING]
> 不要把 `.env`、Token、密码或密钥提交到 Git。

启动：

```bash
python main.py
```

没有配置 `WEBHOOK_URL` 时使用 Telegram polling。

运行测试：

```bash
python -m unittest discover -s tests -v
```

## 项目结构

项目采用按功能组织的模块化单体：

```text
gcc_agent/
├── access/                  # 身份、授权、邮箱验证和 Guard
├── admin/                   # 管理员操作
├── applications/            # 申请流程、文案、筛选和通知
├── common/
│   └── persistence/         # SQLite 迁移和 repositories
├── knowledge/               # GCC 价值观、项目和案例
├── qa/                      # Prompt、链接优先和 AI 问答
├── telegram/                # Telegram 路由和应用装配
└── config.py                # 环境变量

migrations/                  # 数据库初始结构及版本迁移
tests/                       # 按功能组织的测试
main.py                      # 启动入口
```

根目录的 `db.py`、`models.py`、`core/` 和 `handlers/` 是旧 import 的兼容入口。新代码应放在 `gcc_agent/` 对应模块。

技术栈：Python 3.12、python-telegram-bot、OpenAI API、SQLite、Fly.io。

## 价值观与预审

`values.yaml` 保存 GCC 使命、资助方向、拒绝条件、语气和评分权重。修改后重新部署，或私聊 Bot 发送 `/update_values` 生效。

默认评分权重：

| 维度 | 权重 |
|---|---|
| 使命契合度 | 40 |
| 公共物品属性 | 30 |
| 华语社区影响 | 20 |
| 可行性 | 10 |

结果仅用于初步筛选，不代表最终决定：

- **≥ 70**：建议管理员跟进
- **40–69**：建议参加例会进一步了解
- **< 40**：可能不符合当前方向

## 数据与对话记忆

- 用户、会话、消息和申请草稿保存在 SQLite
- GCC 项目和案例保存在 YAML/Markdown
- 每位用户保留最近 20 条对话
- 30 分钟无活动后建立新 Session
- 价值观 system prompt 始终位于用户对话之前

## 公共物品案例资料库

第一批案例种子保存在 `data/project-case-seeds.yaml`，目前覆盖 6 个代表类别：开源项目、社区资助、单次活动、ETH City 系列、机票支持计划和 Gitcoin 类别占位。

v0.1 schema 分成两层：

- `schema/project-case-database.schema.json`：定义整个资料库文件，包括 `schema_version`、`updated_at`、`purpose` 和 `cases`
- `schema/project.schema.json`：定义单个案例，包括公开记录、资金结构、公共物品维度、影响证据、原始资料指针、投票记录和 AI 初审引用方式

这批资料是可追溯的 seed database，不等同于完整 GCC 历史资助库。新增案例时应保留原始申请书、Snapshot 或投票记录的指针，并明确标记资料质量、隐私和是否可用于 AI 初审。

## 部署

以 Fly.io 为例：

```bash
flyctl auth login
flyctl launch --no-deploy --name 你的应用名称
flyctl volumes create gcc_agent_data --region nrt --size 1
flyctl secrets set \
  BOT_TOKEN="..." \
  ADMIN_USER_ID="..." \
  ADMIN_NOTIFY_ID="..." \
  GCC_GROUP_ID="..." \
  OPENAI_API_KEY="..." \
  WEBHOOK_URL="https://你的应用名称.fly.dev/webhook"
flyctl deploy
```

设置 Telegram Webhook：

```text
https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=https://<应用名>.fly.dev/webhook
```

> [!IMPORTANT]
> Webhook 只监听 `127.0.0.1`，需要由同一实例中的反向代理转发，不能直接把本地监听地址暴露到公网。

## 参与贡献

欢迎提交 Issue 和 Pull Request。完整流程和约定见 [CONTRIBUTING.md](CONTRIBUTING.md)，参与时请遵守 [行为准则](CODE_OF_CONDUCT.md)。

简要流程：

1. 从 `dev` 拉出 `feat/` 或 `fix/` 分支
2. 改动保持聚焦，并补上对应测试
3. 提交前运行 `python -m unittest discover -s tests -v`
4. 向 **`dev`** 开 Pull Request，不要直接推 `main`

Issue 标题带上 `新功能`、`缺陷`、`文档` 等类型词，GitHub Actions 会按内容和改动路径自动打标签。提交说明请写 `Refs #编号` 或 `Fixes #编号` 以关联 Issue。

## 关于 GCC

GCC（Global Chinese Community of Universal Digital Commons）支持以未来方式重塑公共物品的人与项目，立足华语，共连全球。

- 官网：[gccofficial.org](https://www.gccofficial.org)
- 资助申请：[gccofficial.org/application](https://www.gccofficial.org/application)

## 许可证

本项目采用 [MIT License](LICENSE)。
