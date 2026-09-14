# Group-member private Q&A boundary

Status: `GROUP-ACCESS-002` implementation specification
Decision date: 2026-09-15
Owner decision: align human private-Q&A eligibility with current membership of `GCC_GROUP_ID`

## Eligibility

For every private general message, the Bot requests the sender's current
`getChatMember` status from the configured GCC group.

| Condition | Private general Q&A |
|---|---|
| human `member`, `administrator`, or `creator` | allowed |
| `left`, `kicked`, `restricted`, or unknown status | denied |
| blocked Bot user | denied before a membership request |
| actor stored as `agent` | denied unless the separate existing agent-credential rule allows it |
| missing `GCC_GROUP_ID` or Telegram API error | denied |
| legacy verified email but no current group membership | denied |

The successful human decision is request-scoped. It updates the existing
`users.is_group_member` access-state field but does not change `actor_type`,
`access_level`, or any email field.

## Capability boundary

A group-qualified private request:

- uses the existing private session, separate from all group, user, and topic sessions;
- consumes the existing shared daily limit of 20 messages;
- can receive deterministic official-link or general AI answers;
- never receives the application button and cannot enter an old application session;
- does not add an administrator or identity-grant capability; existing dedicated command
  eligibility is unchanged and remains under `ACCESS-002` governance.

Dedicated `/start`, `/privacy`, `/email`, `/verify`, `/grant`, and `/whoami` command
handlers remain ahead of the general private-message guard. `/whoami` performs the same
live membership check and reports the effective QA result without exposing email data.

## Data and operational boundary

The membership request sends Telegram the configured group ID and requesting user ID.
The returned status is reduced to an allowed boolean and stored in the existing access
field. No group member list, email, profile, question, or other member data is requested.
The `/privacy` notice and data map describe this current processing.

Live checks add one Telegram API dependency to each private general message. Failure is
closed to a welcome-only response and is logged without message content. Existing
operations monitoring continues to cover Telegram API availability.

## Acceptance

Before merge:

1. the complete repository test entry point passes;
2. all accepted and rejected membership statuses are covered;
3. API error, blocked user, Agent, legacy email, and rate-limit boundaries are covered;
4. tests prove an application-mode session is not entered and no application button is
   enabled for this capability;
5. the three welcome, README, and privacy languages describe the same eligibility.

After deployment:

1. a current group member receives `qa: yes` from private `/whoami`;
2. the same member receives a normal answer to one safe private question;
3. no application button is shown on a funding-related answer;
4. an explicit group mention still works and uses a separate group session;
5. readiness, webhook backlog, alerts, and non-sensitive aggregate counts remain healthy.

Testing a real nonmember or removed member is optional only if it can be done without
changing production membership. The fail-closed paths must always be covered by automated
tests.

## Rollback

Rollback uses the previous application image. There is no schema or secret change. The
old image ignores the newly refreshed `is_group_member` value for private QA, so rollback
returns non-email private users to welcome-only behaviour without a data migration. Do not
delete identity, session, message, volume, or snapshot data as part of rollback.
