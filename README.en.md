# GCC Telegram AI Assistant

[简体中文](README.md) · [繁體中文](README.zh-TW.md) · **English**

A Telegram AI assistant for GCC (Global Chinese Community of Universal Digital
Commons). It answers basic questions, collects grant application information,
performs preliminary screening, and hands cases requiring judgment to GCC
members.

## Features

- Regular users and unauthorized agents receive a welcome message only
- GCC members can use Q&A and applications after verifying their email
- Daily limit of 20 messages per member
- Official links are preferred over unnecessary model calls
- Simplified Chinese, Traditional Chinese, and English responses
- Four-step application flow: project name, fund type, proposal link, summary
- 0–100 preliminary screening based on `values.yaml`
- Administrator notification after an application is completed
- `/status` statistics and `/update_values` value reload commands

## Identity and access

Identity uses two independent fields instead of RBAC:

- `actor_type`: `human` or `agent`
- `access_level`: `regular` or `gcc_member`

Human GCC members must verify their email with `/email` and `/verify`. Regular
users and regular agents receive the welcome message only. Legacy `user_kind`
data is migrated automatically at startup without deleting existing records.

Common commands:

```text
/email you@example.com
/verify 123456
/whoami
/grant <user_id or @username> regular|gcc_member|ai
```

Current Telegram group members with `member`, `administrator`, or `creator`
status, plus `ADMIN_USER_ID`, may assign identities to other users.

## Architecture

The project is a feature-oriented modular monolith:

```text
gcc_agent/
├── access/                  # Identity, authorization, email verification, guard
├── admin/                   # Administrator operations
├── applications/            # Workflow, messages, screening, notifications
├── common/
│   └── persistence/         # SQLite migrations and repositories
├── knowledge/               # GCC values, projects, and cases
├── qa/                      # Prompts, link-first answers, and AI Q&A
├── telegram/                # Telegram routing and application composition
└── config.py                # Environment-backed settings

migrations/                  # Initial schema and versioned migrations
tests/                       # Feature-oriented tests
main.py                      # Thin entry point
```

Root-level `db.py`, `models.py`, `core/`, and `handlers/` are compatibility
facades for legacy imports. New code should be added under `gcc_agent/`.

Stack: Python 3.12, python-telegram-bot, OpenAI API, SQLite, and Fly.io.

## Local setup

### 1. Install

```bash
git clone https://github.com/your-account/gcc-telegram-agent.git
cd gcc-telegram-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Configure

```env
BOT_TOKEN=Telegram Bot Token
ADMIN_USER_ID=Administrator Telegram User ID
ADMIN_NOTIFY_ID=Application notification Telegram User ID
GCC_GROUP_ID=GCC Telegram group ID

OPENAI_API_KEY=OpenAI API Key
AI_MODEL=gpt-4o-mini
AI_MAX_TOKENS=800

DB_PATH=gcc_agent.db

# Email delivery fails closed unless fully configured
EMAIL_VERIFICATION_SECRET=random secret with at least 32 characters
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=SMTP username
SMTP_PASSWORD=SMTP password
SMTP_FROM=bot@example.com
SMTP_USE_TLS=true
```

Never commit `.env`, tokens, passwords, or secret keys.

### 3. Run

```bash
python main.py
```

Telegram polling is used when `WEBHOOK_URL` is not configured.

### 4. Test

```bash
python -m unittest discover -s tests -v
```

Tests are grouped under `tests/access`, `tests/applications`,
`tests/knowledge`, `tests/persistence`, and `tests/qa`.

## Fly.io deployment

```bash
flyctl auth login
flyctl launch --no-deploy --name your-app
flyctl volumes create gcc_agent_data --region nrt --size 1
flyctl secrets set \
  BOT_TOKEN="..." \
  ADMIN_USER_ID="..." \
  ADMIN_NOTIFY_ID="..." \
  GCC_GROUP_ID="..." \
  OPENAI_API_KEY="..." \
  WEBHOOK_URL="https://your-app.fly.dev/webhook"
flyctl deploy
```

The webhook currently listens on `127.0.0.1` only. Deployment therefore
requires a reverse proxy in the same instance; the local listener must not be
exposed directly to the public internet.

Configure the Telegram webhook:

```text
https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=https://<app>.fly.dev/webhook
```

## Values and screening

`values.yaml` stores GCC's mission, priorities, rejection criteria, tone, and
screening weights. Administrators can redeploy or send `/update_values` to the
bot after editing it.

Default weights:

- Mission fit: 40
- Public-goods nature: 30
- Chinese-speaking community impact: 20
- Feasibility: 10

Results are preliminary only:

- ≥ 70: recommend administrator follow-up
- 40–69: recommend further discussion at a community call
- < 40: may not fit the current direction

## Data and conversation memory

- Users, sessions, messages, and application drafts are stored in SQLite
- GCC projects and cases are stored as YAML/Markdown
- The latest 20 conversation messages are retained per user
- A new session starts after 30 minutes of inactivity
- The values system prompt always precedes user conversation context

## About GCC

GCC supports people and projects reshaping public goods for the future, rooted
in Chinese-speaking communities and connected globally.

- Website: [gccofficial.org](https://www.gccofficial.org)
- Grant application: [gccofficial.org/application](https://www.gccofficial.org/application)

## License

This project is licensed under the [MIT License](LICENSE).
