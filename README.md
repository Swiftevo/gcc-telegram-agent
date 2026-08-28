# GCC Telegram AI 助手

**简体中文** · [繁體中文](README.zh-TW.md) · [English](README.en.md)

GCC（Global Chinese Community of Universal Digital Commons）的 Telegram AI
助手。它负责回答基础问题、收集资助申请资料、初步筛选，再把需要深入判断的
事项交给 GCC 成员。

## 核心功能

- 普通用户及未授权 Agent 只收到欢迎信息
- GCC 内部成员完成邮箱验证后可以使用问答和申请功能
- 每位成员每天最多发送 20 条消息
- 官网链接优先，减少不必要的模型调用
- 根据用户语言使用简体中文、繁体中文或英文
- 四步申请流程：项目名称、基金类型、提案链接、执行摘要
- 根据 `values.yaml` 做 0–100 分的初步筛选
- 完成申请后通知管理员
- `/status` 查看统计，`/update_values` 重新载入价值观

## 身份与访问

身份由两个独立字段组成，不使用 RBAC：

- `actor_type`：`human` 或 `agent`
- `access_level`：`regular` 或 `gcc_member`

人类 GCC 成员必须通过 `/email` 和 `/verify` 验证邮箱。普通用户和普通
Agent 只能看到欢迎信息。旧数据库中的 `user_kind` 会在启动时自动迁移，
不会删除原有数据。

常用命令：

```text
/email you@example.com
/verify 123456
/whoami
/grant <user_id 或 @username> regular|gcc_member|ai
```

当前 GCC Telegram 群的 `member`、`administrator`、`creator` 以及
`ADMIN_USER_ID` 可以为其他用户设置身份。

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

根目录的 `db.py`、`models.py`、`core/` 和 `handlers/` 是旧 import 的兼容
入口。新代码应放在 `gcc_agent/` 对应模块。

技术栈：Python 3.12、python-telegram-bot、OpenAI API、SQLite、Fly.io。

## 本地运行

### 1. 准备环境

```bash
git clone https://github.com/你的账号/gcc-telegram-agent.git
cd gcc-telegram-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. 配置环境变量

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

不要把 `.env`、Token、密码或密钥提交到 Git。

### 3. 启动

```bash
python main.py
```

没有配置 `WEBHOOK_URL` 时使用 Telegram polling。

### 4. 测试

```bash
python -m unittest discover -s tests -v
```

测试分别位于 `tests/access`、`tests/applications`、`tests/knowledge`、
`tests/persistence` 和 `tests/qa`。

## Fly.io 部署

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

当前 Webhook 只监听 `127.0.0.1`。部署时需要由同一实例中的反向代理转发，
不能直接把本地监听地址暴露到公网。

设置 Telegram Webhook：

```text
https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=https://<应用名>.fly.dev/webhook
```

## 价值观与预审

`values.yaml` 保存 GCC 使命、资助方向、拒绝条件、语气和评分权重。管理员
可以重新部署，或私聊 Bot 发送 `/update_values` 使修改生效。

默认评分：

- 使命契合度：40
- 公共物品属性：30
- 华语社区影响：20
- 可行性：10

结果仅用于初步筛选：

- ≥ 70：建议管理员跟进
- 40–69：建议参加例会进一步了解
- < 40：说明可能不符合当前方向

## 数据与对话记忆

- 用户、会话、消息和申请草稿保存在 SQLite
- GCC 项目和案例保存在 YAML/Markdown
- 每位用户保留最近 20 条对话
- 30 分钟无活动后建立新 Session
- 价值观 system prompt 始终位于用户对话之前

## 关于 GCC

GCC 支持以未来方式重塑公共物品的人与项目，立足华语，共连全球。

- 官网：[gccofficial.org](https://www.gccofficial.org)
- 资助申请：[gccofficial.org/application](https://www.gccofficial.org/application)

## 许可证

本项目采用 [MIT License](LICENSE)。
