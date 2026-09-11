# GCC Telegram Bot Operations Runbook

This runbook covers process, database, Telegram webhook, notification, deploy,
and Machine incidents for `gcc-public-goods-bot`. It must not contain secret
values, user messages, email addresses, application content, or database rows.

## Ownership and alert paths

- The repository owner/on-call maintainer owns GitHub Actions and Fly incidents.
- `ADMIN_USER_ID` receives generic Telegram alerts without user content.
- `Production Readiness Monitor` probes production every 15 minutes. It opens one
  GitHub issue while `/opsz` is failing and closes it after recovery.
- A failed main test/deploy opens a separate GitHub issue linked to the failed run.
- Operators must enable GitHub notifications for this repository; an issue is the
  durable incident record, not proof that a particular person has acknowledged it.

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
| Admin application notification fails | Generic fallback alert to `ADMIN_USER_ID`; `/opsz` degrades and external issue follows | Check bot permission and target chat without copying application content |
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
