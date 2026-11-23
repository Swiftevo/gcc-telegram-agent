# GCC Telegram Bot Operations Runbook

This runbook covers process, database, Telegram webhook, operations alerts, deploy,
and Machine incidents for `gcc-public-goods-bot`. It must not contain secret
values, user messages, email addresses, application content, or database rows.

## Application retirement release check

After the APP-001 / REVIEW-001 merge, verify in a private chat and in the configured
group that a funding application question gives only the current official external
form landing page. Test a Public Fund and a Special Fund question separately, and
check the website's current opening status before describing any round as open.
An old Telegram `intent_apply` or `intent_exit` button must return the external
handoff without asking for a project name or claiming submission. If a test account
has a legacy draft, confirm its next Q&A starts a clean session and does not quote
its draft. `/status` must not show a new-application count. Do not paste draft
contents into logs or a PR.

Rollback uses the previously verified image under the release procedure below;
this restores the old application flow, so disable public use and investigate
before any rollback. The release itself did not delete SQLite draft rows. A
2026-11-23 read-only production aggregate found no legacy application modes,
draft content, submission markers, or score markers. Recheck aggregate counts
before retention cleanup; if legacy data appears, skip those rows and investigate.
Backup and administrator Telegram copies are covered by `PRIV-001H`.

## Live SQLite retention cleanup (`PRIV-001F`)

The Bot defaults to `RETENTION_CLEANUP_MODE=off`. A production deploy alone does
not delete data. `dry-run` logs aggregate candidates without changing rows;
`apply` runs the same checks and then deletes eligible rows in one SQLite
transaction, starting 60 seconds after Bot startup and repeating every 24 hours.
Each run logs only counts and the mode, never IDs, addresses, or message text.
Failures raise `retention_cleanup_failed`; unexpected legacy drafts or invalid
timestamps raise `retention_cleanup_skipped_rows`; special-identity email data or
active agent credentials raise `retention_cleanup_manual_review`. These alerts
contain no user content.

Before enabling deletion after the merge:

1. Confirm the new image is deployed and `/readyz` and `/opsz` are healthy. Run
   `python -m gcc_agent.ops.retention` in the Fly Machine for a read-only preview;
   record aggregate counts only. Expected baseline on 2026-11-23: 42 sessions,
   33 older than 30 days, 6 users, no eligible inactive regular users, and no
   email or credential rows. Candidate counts may change with ongoing use.
2. Follow [`sqlite-backup-restore.md`](sqlite-backup-restore.md) to create and
   confirm an on-demand volume snapshot immediately before the first `apply`.
   If the preview shows legacy application rows, invalid timestamps, special
   email data, or active credentials, review the exception before proceeding.
3. Set `RETENTION_CLEANUP_MODE=apply` for the production app and let the Machine
   restart. Check the first aggregate `retention cleanup mode=apply` log line,
   `/readyz`, `/opsz`, and a normal private/group Q&A. Re-run the read-only
   preview to confirm eligible counts fell as expected. Do not paste user rows
   or message content into an issue or PR.

The cleanup removes both `sessions.messages_json` and related `messages` rows
after 30 days since session last activity. It removes unblocked human/regular
users after 90 days without activity only when they have no remaining sessions
or active credentials; the configured operator and blocked/managed identities
are protected. It removes dormant email challenges, clears email fields on
regular users, and removes already revoked credential hashes. Email fields on
managed identities and active credentials await operator review. Any unexpected
legacy application session is skipped, including its user; no application
content is printed or automatically deleted.

To stop future cleanup, set `RETENTION_CLEANUP_MODE=off`. If an incorrect
deletion occurred, stop cleanup first, preserve the current volume, and follow
the documented snapshot restore procedure; restoring a snapshot also rolls
back legitimate writes since that snapshot, so assess them before restoring.
Backups, logs, administrator Telegram copies, and third-party data remain under
`PRIV-001H` and are not deleted by this job.

## Ownership and alert paths

- The repository owner/on-call maintainer owns GitHub Actions and Fly incidents.
- `ADMIN_USER_ID` receives generic Telegram alerts without user content.
- `Production Readiness Monitor` probes production every 15 minutes. It opens one
  GitHub issue while `/opsz` is failing and closes it after recovery.
- A failed main test/deploy opens a separate GitHub issue linked to the failed run.
- Operators must enable GitHub notifications for this repository; an issue is the
  durable incident record, not proof that a particular person has acknowledged it.

## Identity and access operator

- The Telegram user ID in `ADMIN_USER_ID` is the sole designated operator for
  `/grant`, `/block`, and `/unblock`. Membership of `GCC_GROUP_ID`, including group
  administrator status, does not confer operator authority. If `ADMIN_USER_ID`
  is unset, these commands deny all callers. A backup operator requires a
  separately approved configuration change; do not share a Telegram account.
- These commands are accepted only in a private chat with the Bot. Targets must
  already have a Bot user row. Use `/whoami` with the target's cooperation to
  identify their numeric Telegram ID; avoid relying on a mutable username.
- `/grant <user_id> ai` marks an existing user as an agent with regular access;
  `/grant <user_id> regular` returns the identity to human/regular. A regular
  human who remains a member of the configured GCC group can still use Q&A.
  Use `/block <user_id>` to revoke Bot Q&A immediately in both private and
  group contexts; `/unblock <user_id>` restores eligibility subject to the
  normal group membership and rate-limit checks.
- Successful, unchanged, invalid, and not-found operator requests are recorded
  in SQLite `operator_actions` with actor, target where known, action, result,
  before/after state, and UTC timestamp. The change and audit insert share a
  transaction: an audit write failure rolls back the access change. Denied
  non-operator attempts go to redacted application logs without command text.
  Do not paste user IDs or audit rows into public GitHub issues.
- After a production merge, verify an ordinary group member cannot `/grant` or
  `/block`; verify the designated operator can block a consenting test account,
  that its group mention and private Q&A are refused, then unblock and verify
  normal eligibility returns. Check the audit results locally through approved
  production access. If any step fails, stop group expansion and follow the
  code rollback procedure below. Database migration 6 adds a table and index;
  code rollback leaves them in place and does not undo recorded changes.

Wallet and receiving-address questions use a fixed reply directing users to
GCC's official contact channel. No current wallet/network has been approved as
Bot answer data. A historical multisig address must never be treated as a
current payment instruction. Input routing covers wallet, deposit, and transfer
phrasing; if the language model nevertheless emits a full Ethereum address,
the Bot replaces that draft before sending or storing it. Test Chinese and
English variants in private and group chats after merge; the general AI must
not provide a destination.

## Endpoint contract

| Endpoint | Purpose | Success | Must not expose |
|---|---|---|---|
| `/healthz` | Process/event-loop liveness | HTTP 200 | config, IDs, paths, counters |
| `/readyz` | Routing readiness | Application and webhook running; startup Telegram call succeeded; cached SQLite schema/read/write-lock probe passed | secrets, DB path, rows, user data |
| `/opsz` | External incident monitor | `/readyz` passes; Telegram API monitor is healthy; no high webhook backlog or recent operational incident | exception text, Telegram error text, user content |
| `/webhook` | Telegram updates | Proxies only to the loopback PTB handler, which still enforces the webhook secret | health data |

Fly uses `/readyz` as a service-level check every 15 seconds. Database readiness
is probed in the background and cached, so public requests cannot repeatedly lock
or scan SQLite. Telegram is intentionally checked by `/opsz`, not Fly readiness:
a Telegram outage should alert operators without making Fly remove the only
Machine from routing.

## Alert matrix

| Failure | Signal and alert | First response |
|---|---|---|
| Machine/process/DB not ready | Fly `/readyz` check fails; external `/opsz` workflow opens an issue | Check Machine state, checks, events, logs, volume mount |
| Main test or deploy fails | `Fly Deploy` run fails and opens a run-specific issue | Inspect the first failed step; do not retry blindly |
| Telegram API unreachable three times | `/opsz` becomes 503; external monitor opens an issue | Check Telegram status, DNS/network, token validity and logs |
| Webhook URL mismatch, new Telegram delivery error, or backlog ≥20 | Generic Telegram admin alert; `/opsz` remains degraded for at least 30 minutes; GitHub issue follows | Inspect `getWebhookInfo`, public endpoint, secret and recent deploy |
| Unhandled update exception | Redacted traceback in Fly logs, generic admin alert, `/opsz` degradation | Identify exception type and affected feature; never paste user content into an issue |

Alerts are deduplicated per event for 15 minutes. If Telegram itself is down, its
fallback message can also fail; the independent GitHub `/opsz` monitor is the
secondary path.

## Initial triage

Run these read-only commands first from PowerShell:

```powershell
flyctl status -a gcc-public-goods-bot
flyctl checks list -a gcc-public-goods-bot
flyctl logs -a gcc-public-goods-bot --no-tail
flyctl releases -a gcc-public-goods-bot --image
```

Then check:

1. Exactly one expected `nrt` Machine is `started` and the `/data` volume remains mounted.
2. `/healthz`, `/readyz`, and `/opsz` return HTTP 200. A 503 JSON body contains only booleans.
3. The image `GH_SHA` matches the intended main merge commit.
4. Logs show database initialization, bot startup, `getMe`, and `setWebhook`, with tokens redacted.
5. The latest main Actions run completed both `Verify release` and `Deploy app`.

Do not restart before collecting status, check, event, release, and redacted log
evidence. A restart can erase the timing needed to diagnose an intermittent issue.

## Webhook incident

1. Confirm `/readyz` and `/opsz` separately. If readiness passes but operations
   fails, the process and DB are available and the incident is probably external
   Telegram/webhook state.
2. Check startup and delivery logs for redacted `getMe`/`setWebhook` results.
3. Confirm the registered URL is `https://gcc-public-goods-bot.fly.dev/webhook`,
   pending updates are below 20, and no new last-error timestamp exists. Never
   print `BOT_TOKEN` or `WEBHOOK_SECRET_TOKEN`.
4. If URL or secret registration is wrong, correct the Fly secret/config and
   redeploy through a tested PR. Do not manually register a webhook without the secret.
5. After recovery, require `/opsz` 200 and pending updates to fall; inspect one
   allowed, non-personal-data Telegram question only if group disruption is acceptable.

## Database readiness incident

`/readyz` verifies access to `schema_migrations` and a SQLite write transaction
that is rolled back without changing data. If it fails:

1. Confirm `/data` is mounted and the configured DB file exists inside the intended Machine.
2. Check for lock contention, read-only filesystem errors, full volume, or failed migration.
3. Do not delete, replace, or copy the live SQLite file while the bot is writing.
4. Follow [`sqlite-backup-restore.md`](sqlite-backup-restore.md) for integrity,
   snapshot, backup, or restore work.

## Code rollback

Fly rollback means redeploying a known-good earlier image; it does not reverse
SQLite migrations or restore data.

1. Identify the last verified image:

   ```powershell
   flyctl releases -a gcc-public-goods-bot --image
   ```

2. Compare its timestamp and image with the project log and successful Actions run.
3. Redeploy that exact image using the normal rolling strategy:

   ```powershell
   flyctl deploy -a gcc-public-goods-bot --image registry.fly.io/gcc-public-goods-bot:KNOWN_GOOD_TAG
   ```

4. Verify Machine state, Fly checks, all three endpoints, redacted startup logs,
   webhook pending/error state, and a safe application-level smoke test.
5. Record the incident, selected image, reason, operator, timestamps, checks and
   follow-up fix in `docs/project-log.md`. Never record secret values.

If the faulty release changed data or schema, stop and use the SQLite restore
runbook. Redeploying an old image against an incompatible newer schema can worsen
the incident.

## Quarterly exercise

Once per quarter, the owner should use `workflow_dispatch` on the readiness
monitor, verify Fly checks, trace a simulated alert without exposing user data,
and rehearse image selection up to—but not including—the production redeploy.
Any actual rollback drill must use an approved maintenance window and record its
result in the project log.
