# Project Case Schema 0.4.0

Schema 0.4.0 is the canonical safety boundary for importing additional public
GCC funding cases. It migrates all eight current records without connecting the
case database to Bot runtime answers or changing any review／AI eligibility.

## Record identity

`case_id` is the canonical, stable identity of a database record. Every record
also declares one `record_type`:

- `funding_program`: an umbrella programme or shared funding proposal, not an
  individual recipient;
- `grant_case`: one project, event, or award, optionally linked to one known
  `funding_track_id`;
- `placeholder`: an intentionally empty record reserved for later research.

This prevents a programme pool, funding track, and individual award from being
treated as the same thing.

`legacy_project_slug` is optional and has one purpose only: link a migrated case
to its exact slug in the frozen `projects.yaml` runtime catalog. It is not a
second canonical identity. `funding_track_id` is a foreign key from one
`grant_case` to a stable `track_id` declared by a funding programme.

## One source reference model

Every factual source reference uses `source_snapshot_ids`, even when there is
currently only one source. Each ID must refer to a snapshot registered inside
the same case. This prevents a claim from silently borrowing another case's
evidence and leaves room for corroborating sources later.

`snapshot_id` remains singular only where it identifies the snapshot record
itself, or where a public／redacted evidence pointer points to exactly one local
snapshot. `reference_urls` contains discovery or navigation links; a URL there
does not become citable evidence until it is captured as a registered snapshot.

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

Schema 0.3 removed the former `_usd` amount fields rather than keeping two
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
- one canonical case identity and a separately named legacy catalog slug;
- one case-local `source_snapshot_ids` model and rejection of former singular
  source-reference fields;
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

## Migration from 0.3.0

The 0.4 migration changes identity and source-reference structure, not the
meaning of known facts:

- `canonical_project_id` becomes the accurately named `legacy_project_slug`;
- `source_urls` becomes `reference_urls` so uncaptured links are not mistaken
  for evidence;
- claim-level `source_snapshot_id` values become `source_snapshot_ids` arrays;
- source references are restricted to snapshots registered in the same case;
- unknown and not-applicable values remain explicit;
- amounts, currencies, content, case review status, source review status,
  reconciliation status, and AI flags remain unchanged.
