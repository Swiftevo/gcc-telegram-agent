# Email verification shelving boundary

Status: `ACCESS-001` implementation specification  
Decision date: 2026-09-14  
Owner decision: stop the public email-verification path without deleting historical data

## Current product behaviour

- Private `/start` explains that private-member onboarding is paused and directs users to
  mention the Bot in the configured GCC group.
- Legacy private `/email` and `/verify` commands return a localized paused response. The
  handler does not inspect command arguments, load or create a user, create a challenge,
  or call the SMTP sender.
- `/whoami` reports identity and Q&A access without showing legacy email or verification
  state.
- The configured GCC group's explicit-mention, email-free Q&A route is unchanged.
- `/privacy` remains available without authentication or persistence and discloses that
  email verification is paused while legacy fields or records may remain.

## Deliberately retained

This change does not delete or migrate:

- `users.email` or `users.email_verified_at`;
- the `email_verifications` table;
- repository, service, persistence, migration, and SMTP compatibility code;
- SQLite volume data, scheduled snapshots, or manual backups.

These remain dormant until `PRIV-001D`, `PRIV-001F`, and `PRIV-001G` establish identity
retention, cleanup, and user-data request policy. They must not be treated as an active or
documented onboarding API.

## Verified production baseline

The pre-change read-only aggregate check found two users, zero verified users, zero private
messages or application drafts belonging to verified users, and zero pending email
challenges. No identity, address, message, or application content was read.

## Acceptance checks

Before merge:

1. the full test entry point passes;
2. tests prove both legacy commands use only the non-persisting paused handler;
3. all three welcome and privacy languages describe the paused state;
4. public READMEs and `.env.example` no longer offer email or SMTP onboarding;
5. group mention routing and privacy non-persistence tests remain green.

After deploy, verify without submitting a real address or code:

1. `/start` shows no email-verification instruction;
2. `/email` and `/verify` return the paused response;
3. `/whoami` shows no email field;
4. an explicit mention in the configured GCC group still receives a normal answer;
5. aggregate user and challenge counts do not increase during the legacy-command probes.

## Rollback and reactivation

An application-image rollback restores the old handlers but does not change the SQLite
schema or rows. Production previously had no SMTP or email-verification secret, so delivery
was fail-closed; nevertheless, rollback must not be used as an informal reactivation path.
Reactivation requires a reviewed PR plus an approved eligibility policy, privacy-notice
update, SMTP owner/provider, abuse limits, and three-language end-to-end verification.
