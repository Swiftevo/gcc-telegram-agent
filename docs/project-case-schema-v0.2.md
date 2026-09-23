# Project Case Schema 0.2

Schema 0.2 is the safety boundary for importing additional public GCC funding
cases. It migrates the six existing seed records but does not add new projects or
connect the case database to Bot runtime answers.

## Record identity

Every record declares one `record_type`:

- `funding_program`: an umbrella programme or shared funding proposal, not an
  individual recipient.
- `grant_case`: one funded project, event, or award. It may reference exactly one
  known `funding_track_id`.
- `placeholder`: an intentionally empty record reserved for later research.

This prevents a programme pool, a funding track, and an individual grant from
being treated as the same thing.

## Funding facts

`public_record.funding` now requires three separate facts:

- `requested`
- `governance_approved`
- `disbursed`

Each fact stores the original amount and currency, a status, supporting
`source_snapshot_ids`, and a note. Allowed statuses are:

- `source_reported`
- `owner_confirmed`
- `verified`
- `pending_reconciliation`
- `unknown`
- `not_applicable`

The existing `*_amount_usd` fields remain temporarily for legacy compatibility;
new imports must not use them as a substitute for the structured facts. A signed
Snapshot can support `requested` or `governance_approved`, but cannot by itself
support `disbursed`.

## Execution events

`public_record.execution_events` can independently record:

- governance decisions
- disbursements
- milestone acceptance
- milestone unlocks
- activity completion
- report submission

Every event has its own date, amount/currency when applicable, fact status,
source references, and notes. An empty array means the event has not yet been
safely modelled; it does not mean that nothing happened.

## Review and AI boundary

All migrated seed cases have `ai_review_usage.allowed: false`. Schema 0.2 only
permits AI review for a public record whose status is `reviewed` or `published`,
with review date and reviewer role recorded. The cross-record validator also
rejects AI use when any part of the case is `pending_reconciliation`.

Changing a case to `reviewed`, `published`, or AI-allowed is a separate content
and governance decision. Schema migration alone never performs that approval.

## Validation

Run the same validator locally and in CI:

```powershell
python -m gcc_agent.knowledge.validate_cases
python -m tests
```

Validation covers JSON Schema Draft 2020-12 plus database-wide rules:

- unique case, funding-track, and source-snapshot IDs;
- every `funding_track_id` resolves to a known track;
- only `grant_case` records may link to a funding track;
- every source-snapshot reference resolves;
- reviewed/public requirements for AI use;
- no AI use while reconciliation is pending;
- date and amount/currency structure.

The validator reports all detectable issues and exits non-zero. It does not fetch
websites, decide whether a source is truthful, reconcile accounting records, or
approve private material for publication. Those remain human review tasks.

## First import after 0.2

Import only two or three non-conflicting public cases in the first batch. Keep
them as `draft`, leave AI disabled, preserve the official GCC page and Snapshot
as separate sources, and use `unknown` rather than inferring payments or
outcomes. The pilot should test whether 0.2 needs an additive 0.2.x adjustment
before a larger import.
