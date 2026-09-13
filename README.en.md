<div align="center">

<img src="docs/assets/banner.jpg" alt="GCC Telegram AI Assistant" width="100%">

# GCC Telegram AI Assistant

A Telegram AI assistant for public goods: it answers questions, collects grant applications, and runs preliminary screening.

[![Telegram](https://img.shields.io/badge/Telegram-@GCCpublicgoods__bot-2CA5E0?logo=telegram&logoColor=white)](https://t.me/GCCpublicgoods_bot)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Website](https://img.shields.io/badge/Website-gccofficial.org-1a1a1a)](https://www.gccofficial.org)
[![Contributing](https://img.shields.io/badge/Contributing-guide-orange.svg)](CONTRIBUTING.md)

[简体中文](README.md) · [繁體中文](README.zh-TW.md) · **English**

[Contributing](CONTRIBUTING.md) · [Code of Conduct](CODE_OF_CONDUCT.md) · [Project log](docs/project-log.md) · [Prioritized TODO](docs/todo.md) · [How to contribute](#contributing)

</div>

---

## Try it now

The assistant is already deployed. Open **[@GCCpublicgoods_bot](https://t.me/GCCpublicgoods_bot)** in Telegram and send `/start`.

Regular users receive a welcome message in private chat. GCC members can use private Q&A and grant applications after verifying their email. When group Q&A is enabled for the configured GCC group, users there may ask by explicitly mentioning the bot without providing an email.

To change code or open an Issue, start with the [contributing guide](CONTRIBUTING.md). Create a short-lived branch from the latest `main`, then open a Pull Request against `main`; never push directly to `main`.

## What this project solves

Newcomers ask the same questions: what GCC does, how to apply for funding, and whether a project is a fit. Those threads used to land in the group over and over.

This assistant takes that first layer: it answers with official links when it can, collects materials and scores them against GCC values when judgment is needed, then hands the case to members.

## Features

| Feature | Description |
|---|---|
| Tiered access | Regular users and unauthorized agents get a welcome message only |
| Email verification | GCC members unlock Q&A and applications after verifying email |
| Link-first answers | Questions that match official pages skip the model |
| Languages | Simplified Chinese, Traditional Chinese, or English from the user locale |
| Application flow | Four steps: project name, fund type, proposal link, executive summary |
| Screening | 0–100 score from `values.yaml`, then notify an administrator |
| Group Q&A | When enabled, only explicit mentions in the `GCC_GROUP_ID` chat are answered; email, applications, and admin capabilities are excluded |
| Rate limit | 20 messages per user per day, including group Q&A |

## Commands

For everyone (no email verification required):

```text
/privacy                    Show the Bot's current data-processing notice
```

For members:

```text
/email you@example.com      Bind email and receive a verification code
/verify 123456              Submit the code
/whoami                     Show current identity
```

For administrators:

```text
/grant <user_id or @username> regular|gcc_member|ai
/status                     Show statistics
/update_values              Reload values
```

Telegram group users with `member`, `administrator`, or `creator` status, plus `ADMIN_USER_ID`, may assign identities to others.

## Data notice

`/privacy` explains the data the Bot currently processes, recipients including Fly.io, Telegram, OpenAI, and SMTP, the parts that do not yet expire automatically, and GCC's public contact channel. The command creates no user or conversation record in the Bot's SQLite database and does not consume the daily limit; an explicit bot mention is still required in the configured group. See the [data-flow inventory](docs/privacy-data-map.md) for technical detail and the [minimum data notice](docs/privacy-notice.md) for scope and maintenance rules.

## Identity model

Identity uses two independent fields instead of RBAC:

- `actor_type`: `human` or `agent`
- `access_level`: `regular` or `gcc_member`

Human GCC members must verify email with `/email` and `/verify` to use private Q&A and applications. Email-free group Q&A is a request-scoped `group_qa` capability and never promotes the user to `gcc_member`. Legacy `user_kind` rows are migrated automatically at startup without deleting existing data.

## Quick start

Python 3.12 is required.

```bash
git clone https://github.com/Swiftevo/gcc-telegram-agent.git
cd gcc-telegram-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:

```env
BOT_TOKEN=Telegram Bot Token
ADMIN_USER_ID=Administrator Telegram User ID
ADMIN_NOTIFY_ID=Application notification Telegram User ID
GCC_GROUP_ID=GCC Telegram group ID
GROUP_QA_ENABLED=false

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

> [!WARNING]
> Never commit `.env`, tokens, passwords, or secret keys.

Run:

```bash
python main.py
```

Telegram polling is used when `WEBHOOK_URL` is unset.

Tests:

```bash
python -m tests
```

## Project structure

The codebase is a feature-oriented modular monolith:

```text
gcc_agent/
├── access/                  # Identity, authorization, email verification, guard
├── admin/                   # Administrator operations
├── applications/            # Workflow, copy, screening, notifications
├── common/
│   └── persistence/         # SQLite migrations and repositories
├── knowledge/               # GCC values, projects, and cases
├── qa/                      # Prompts, link-first answers, and AI Q&A
├── telegram/                # Telegram routing and app composition
└── config.py                # Environment settings

migrations/                  # Initial schema and versioned migrations
tests/                       # Feature-oriented tests
main.py                      # Entry point
```

Root-level `db.py`, `models.py`, `core/`, and `handlers/` are compatibility facades. Add new code under `gcc_agent/`.

Stack: Python 3.12, python-telegram-bot, OpenAI API, SQLite, Fly.io.

## Values and screening

`values.yaml` stores GCC's mission, funding priorities, rejection criteria, tone, and scoring weights. Redeploy after edits, or send `/update_values` in a private chat with the bot.

Default weights:

| Dimension | Weight |
|---|---|
| Mission fit | 40 |
| Public-goods nature | 30 |
| Chinese-speaking community impact | 20 |
| Feasibility | 10 |

Scores are preliminary only and are not a final decision:

- **≥ 70**: recommend administrator follow-up
- **40–69**: recommend discussion at a community call
- **< 40**: may not fit the current direction

## Data and conversation memory

- Users, sessions, messages, and application drafts live in SQLite
- GCC projects and cases live in YAML/Markdown
- The latest 20 messages are kept per user
- A new session starts after 30 minutes of inactivity
- Private chats, groups, group users, and Telegram topics use isolated sessions
- The values system prompt always precedes user conversation context

## Deploy

Example on Fly.io:

```bash
flyctl auth login
flyctl launch --no-deploy --name your-app
flyctl volumes create gcc_agent_data --region nrt --size 1
flyctl secrets set \
  BOT_TOKEN="..." \
  ADMIN_USER_ID="..." \
  ADMIN_NOTIFY_ID="..." \
  GCC_GROUP_ID="..." \
  GROUP_QA_ENABLED="true" \
  OPENAI_API_KEY="..." \
  WEBHOOK_URL="https://your-app.fly.dev/webhook" \
  WEBHOOK_LISTEN="0.0.0.0" \
  WEBHOOK_SECRET_TOKEN="random-secret-with-at-least-32-characters"
flyctl deploy
```

> [!IMPORTANT]
> On Fly.io, the webhook must listen on `0.0.0.0` and the `internal_port` from `fly.toml`; otherwise Fly cannot forward Telegram webhook requests to the app. `WEBHOOK_SECRET_TOKEN` must contain 32–256 letters, numbers, underscores, or hyphens. The app registers the webhook and secret with Telegram during startup; do not manually call `setWebhook` without the secret. For local debugging, set `WEBHOOK_LISTEN=127.0.0.1` if you only want localhost.

Set `GROUP_QA_ENABLED=false` to immediately disable email-free group Q&A without deleting or changing existing user identities or session data.

## Contributing

Issues and Pull Requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full process and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for community standards.

Short path:

1. Branch `feat/`, `fix/`, `docs/`, or `chore/` from the latest `main`
2. Keep the change focused and add tests
3. Run `python -m tests` before you push
4. Open the Pull Request against **`main`**; merge only after required checks pass, and never push directly to `main`

Put type words such as `enhancement`, `bug`, or `docs` in the Issue title so Actions can label it. Reference issues with `Refs #n` or `Fixes #n` in the commit message.

## About GCC

GCC (Global Chinese Community of Universal Digital Commons) supports people and projects reshaping public goods for the future, rooted in Chinese-speaking communities and connected globally.

- Website: [gccofficial.org](https://www.gccofficial.org)
- Grant application: [gccofficial.org/application](https://www.gccofficial.org/application)

## License

This project is licensed under the [MIT License](LICENSE).
