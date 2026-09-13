# GCC Telegram Agent minimum data notice

Status: `PRIV-001B` implementation specification  
Last reviewed: 2026-09-13  
Evidence baseline: [`privacy-data-map.md`](privacy-data-map.md)

## Purpose and boundary

The Telegram `/privacy` response is a short, current-state operational notice. It
helps a person understand what happens before deciding what to send to the Bot. It
is not a complete privacy policy or legal opinion, and it does not invent a lawful
basis, controller identity, retention period, deletion deadline, or data-subject
request procedure that GCC has not yet approved.

The notice must remain consistent with the verified data inventory. Policy and
implementation decisions remain separated as follows:

- conversation and session retention: `PRIV-001C`;
- identity and email lifecycle: `PRIV-001D`;
- legacy application and scoring records: `PRIV-001E`;
- automated cleanup: `PRIV-001F`;
- access, export, and deletion requests: `PRIV-001G`;
- provider, backup, log, and production-access governance: `PRIV-001H`.

## Published surfaces

| Surface | Behaviour |
|---|---|
| Private chat `/privacy` | Available without email verification, membership, or Q&A access; does not create a user, session, or message row and does not consume the daily limit |
| Configured GCC group | Responds only after an explicit mention, such as `@GCCpublicgoods_bot /privacy`; does not run the group access guard or persist the request |
| `/start` welcome | Links to `/privacy` in Traditional Chinese, Simplified Chinese, and English |
| Repository README | Lists the public command and links to this specification and the detailed data map |

The response language follows the Telegram account locale: `zh-TW` includes Hong
Kong and Macau, `zh-CN` includes Simplified Chinese locales, and English locales
receive English. Other locales fall back to Traditional Chinese, matching the Bot's
existing language behaviour.

## Required disclosure

All three versions disclose the same current facts:

1. Telegram identity, group/topic identifiers, public profile/language, access
   state, questions, and answers can be processed; email verification and current
   application flows add their respective data.
2. Telegram transports interactions. Fly.io hosts the application, operational
   logs, SQLite volume, and scheduled snapshots; an operator can also create a
   manual SQLite backup in a separately chosen location.
3. OpenAI receives the current question and up to 20 recent messages from the same
   session only when deterministic official-link or established-fact handling does
   not answer it.
4. An SMTP service receives an address and one-time code only when email delivery
   is enabled; a completed current application may be copied to a GCC
   administrator's Telegram.
5. Some records do not currently expire automatically. Copies held by providers or
   in an administrator's Telegram are outside a live SQLite deletion.
6. Users should not send passwords, private keys, or unnecessary sensitive data.
   Retention and data-request procedures remain under design and are not promised
   by this notice.
7. The public channel for privacy questions and corrections is
   <https://www.gccofficial.org/contact>.

## Ownership and change control

The GCC bot operator owns technical accuracy and publication of this notice; the
current operations runbooks identify `Swiftevo` as that operator. This operational
role is not a claim that the operator is GCC's legal data controller or a formally
appointed privacy contact. Those governance roles remain for `PRIV-001H`.

The notice must be reviewed whenever a change affects collected fields, persistence,
model context, providers, application notifications, the contact URL, or any
retention/deletion behaviour. A user-visible claim must not be changed without a
matching code/data-flow check and tests in all three languages.

## Verification and rollback

Before release:

```bash
python -m tests
```

After deployment, verify `/privacy` in one private chat and one explicit-mention
request in the configured group, using no sensitive content. Confirm the reply
locale and ensure the group request did not consume the user's daily count or create
a conversation row.

Rollback is the normal application-image rollback. Reverting the change removes the
command and welcome link but does not alter or delete existing database records.
