# Canonical Project Data Pipeline

Decision date: 2026-09-25  
Task: `PGDATA-002`

## One canonical destination

`data/project-case-seeds.yaml` is the only destination for new structured case
data. Despite the historical filename, it is the canonical case database.
Schema upgrades migrate this file in place; old schema copies live only in Git
history and must not be kept as parallel databases.

`projects.yaml` is a frozen legacy runtime catalog. The Bot still reads it for
compatibility, but contributors must not add new cases there. Its normalized
content digest and migration counts are locked by
`data/project-case-migration.yaml`. An intentional correction must update the
digest and reconcile every mapped canonical case in the same PR.

Current inventory:

- 63 legacy runtime records;
- 8 mapped canonical cases;
- 55 records explicitly remaining `legacy_only`;
- 14 referenced local evidence files;
- zero cases or sources approved for Bot／AI use.

## Intake flow

```text
public source supplied
        ↓
cleaned local evidence extract
        ↓ automated privacy + checksum gate
canonical draft case (AI disabled)
        ↓ source/fact/privacy/content-owner review
reviewed or published case
        ↓ separate explicit allowed-use decision
eligible for a later Bot runtime integration
```

Use `data/templates/project-case-template.yaml` for a new case and
`data/templates/sanitized-public-application.md` when a full public application
needs a cleaned evidence layer.

## Source processing states

Every local source has a `processing` object:

- `handling_profile`: ordinary cleaned public extract or sanitized public
  application;
- `sanitization_status`: `pending`, `automated_checked`, or `human_reviewed`;
- `review_status`: `pending`, `approved`, or `rejected`;
- `allowed_uses`: starts as `[evidence_only]`;
- `policy_version`: identifies the cleaning rule used.

Automated checks are not human approval. A pending or rejected source cannot be
used for Bot QA or application review. A case cannot become `reviewed` or
`published` until all linked sources are approved. AI use additionally requires
an explicit `bot_qa` allowed use and no unresolved reconciliation status.

## Reusable cleaning policy v1.0

Preserve substantive project, funding, deliverable, milestone, sustainability,
risk, response, aggregate vote, and evidence-limit information.

Exclude:

- voter names, wallets, ENS identifiers and row-level vote metadata;
- meeting, recording, document, or system access credentials;
- named reviewer attribution when an anonymized concern is sufficient;
- unnecessary biographies or employment histories;
- private applications, internal notes, or non-public committee material;
- claims that a proposal or website label proves payment, milestone acceptance,
  unlock, delivery, or impact.

The validator scans every referenced local evidence file, verifies its
normalized SHA-256 checksum, rejects orphan source files, and blocks known
row-level vote, wallet, and recording-access patterns.

## Human review checklist

Before approving a source:

1. Confirm the source is public or publication is authorized.
2. Confirm the extract accurately represents the source and distinguishes
   applicant claims from independently verified facts.
3. Confirm requested, approved, and disbursed amounts are separated.
4. Confirm governance decisions are not used as payment or milestone evidence.
5. Confirm vote data is aggregate-only and no access credential remains.
6. Confirm unresolved contradictions are marked `pending_reconciliation`.
7. Recalculate the checksum after any evidence edit.
8. Record only a reviewer role and date, not private reviewer notes.

Before approving a case:

1. All linked source reviews are approved.
2. The case has no deprecated duplicate amount fields.
3. `funded` is used only with separate disbursement evidence.
4. Links, dates, categories, record type, and funding-track relationships are
   correct.
5. Retrieval text and allowed uses disclose no fact that exceeds the evidence.
6. Enabling Bot／AI use is an explicit separate decision.

## Validation

Run:

```powershell
python -m gcc_agent.knowledge.validate_cases
python -m tests
```

Both commands are part of the release gate. Do not bypass a failure by copying
data into a second file or lowering the review status.

## Existing public-history note

The current branch removes previously copied row-level Snapshot identities and
an unnecessary recording credential from the working tree. Git history may
still contain earlier versions. Rewriting public repository history is a
separate destructive governance decision and is not part of this task.
