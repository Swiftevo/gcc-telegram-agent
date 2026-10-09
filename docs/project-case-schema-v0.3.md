# Project Case Schema 0.3.0

Schema 0.3.0 is the canonical safety boundary for importing additional public
GCC funding cases. It migrates all eight current records without connecting the
case database to Bot runtime answers or changing any review／AI eligibility.

## Record identity

Every record declares one `record_type`:

- `funding_program`: an umbrella programme or shared funding proposal, not an
  individual recipient;
- `grant_case`: one project, event, or award, optionally linked to one known
  `funding_track_id`;
- `placeholder`: an intentionally empty record reserved for later research.

This prevents a programme pool, funding track, and individual award from being
treated as the same thing.

## One amount model

Every structured amount now uses the same `amountFact` shape:

```yaml
amount: 12500
currency: USDC
status: source_reported
source_snapshot_ids: [snap-example]
notes: Proposal schedule only; not evidence of payment or unlock.
```

The shape is used by:

- `funding.requested`, `governance_approved`, and `disbursed`;
- `funding.total_budget` and `per_person_cap`;
- funding-track `total_pool`, `min_grant`, and `max_grant`;
- milestone `unlock_amount`.

Allowed fact statuses are `source_reported`, `owner_confirmed`, `verified`,
`pending_reconciliation`, `unknown`, and `not_applicable`. A numeric amount must
carry its original currency. Unknown or disputed execution must not be converted
to USD merely to fill a field.

Schema 0.3 removes the former `_usd` amount fields rather than keeping two
representations. Runtime legacy conversion still derives its compatibility
amount from the structured requested／governance-approved facts.

## Execution events

`public_record.execution_events` independently records governance decisions,
disbursements, milestone acceptance, milestone unlocks, activity completion,
and report submission. Every event has its own date, amount/currency when
applicable, fact status, source references, and notes.

A proposed milestone and its source-reported unlock amount are not evidence that
the milestone was accepted, paid, or unlocked. Those outcomes require separate
execution events and evidence.

## Review, privacy, and AI boundary

All current cases have `ai_review_usage.allowed: false`. AI review is permitted
only for a public case whose governance status is `reviewed` or `published`, with
review date and reviewer role recorded. Reconciliation conflicts continue to
block AI use.

Every local source declares a handling profile, sanitization status, review
status, allowed uses, policy version, and normalized SHA-256 checksum. Automated
checking is not human approval; all current sources remain `pending` and
`evidence_only`.

Repository-local evidence must be `public`, or `redacted` with human-reviewed
sanitization and approved source review. `internal`／`private` application and
voting pointers are metadata-only; their document reference, snapshot id,
content summary, and URL remain empty.

## Validation

Run:

```powershell
python -m gcc_agent.knowledge.validate_cases
python -m tests
```

Validation covers JSON Schema Draft 2020-12 plus database-wide rules:

- unique case, funding-track, and source-snapshot IDs;
- valid funding-track and source references;
- one structured amount model and rejection of `_usd` fields;
- source-file existence, checksum, and orphan detection;
- row-level voter, wallet, and recording-access data scanning;
- public-repository evidence boundaries;
- review and allowed-use gates before AI use;
- canonical-to-legacy migration mappings and frozen legacy digest;
- no unsupported `funded` claims.

The validator does not decide whether a source is truthful, reconcile accounting
records, or approve private material for publication. Those remain human review
tasks.

## Migration from 0.2.1

The migration changes structure, not the meaning of known facts:

- existing budget, track, cap, and milestone values retain their recorded
  number, original currency, status, and source;
- OSKey and OpenRPC proposal milestone amounts can now be structured in USDC
  instead of being trapped in prose by an incorrectly named USD field;
- unknown and not-applicable values remain explicit;
- case review status, source review status, reconciliation status, and AI flags
  remain unchanged.
