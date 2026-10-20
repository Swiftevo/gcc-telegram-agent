# GCC public-history evidence layer

Decision date: 2026-10-20
Task: `REPORT-KB-001A`

## Purpose and boundary

`data/gcc-public-history.yaml` registers public, time-bounded material about GCC as an organization.
It is separate from both runtime knowledge and the canonical project-case database:

```text
public historical report
        ↓
cleaned, page-scoped evidence extract
        ↓ automated schema / checksum / privacy gate
history registry: pending + evidence_only
        ↓ content-owner review and present-policy comparison
future approved projection (separate task)
        ↓
Bot runtime, only after an explicit implementation and release decision
```

The current registry is deliberately disconnected from runtime. It is not read by `values.yaml`,
the QA prompt, onboarding, case retrieval or application review. A valid file is not an approval.

## Why this is not a project case

The report combines organization history, programme-level aggregates, historical policies, project
catalogue pages, photographs, testimonials and partner lists. Treating the whole report as one
project case would blur different evidence types. Treating each named project as an approved case
would bypass the canonical case schema, source reconciliation and content-owner review.

Therefore:

- organization history and time-bounded programme claims stay in this registry;
- a project named in the report is only a discovery lead;
- per-project facts must enter `data/project-case-seeds.yaml` through the existing case pipeline;
- no report claim alone proves payment, milestone acceptance, unlock or present status.

## Authority precedence

When sources disagree, use this order:

1. approved current official policy or website source for present-tense questions;
2. separately verified execution, accounting or milestone evidence for implementation facts;
3. approved canonical project-case evidence for a particular case;
4. this historical report for statements explicitly bounded to its period.

Do not use an older report to override a newer policy. Do not silently convert a historical claim
into a current one.

## Source classifications

- `historical_context`: time-bounded organization description or timeline;
- `time_bounded_aggregate`: numerical roll-up requiring an explicit start and end;
- `historical_policy`: a policy or process described at the report's time, not current policy;
- `case_catalog`: project names that require separate case intake;
- `historical_programme`: programme-level history and outcomes;
- `excluded_from_bot`: public content intentionally omitted because it is unnecessary or unstable.

Public availability does not make every name, image, quotation, QR code or partner claim necessary
for a Bot answer. The cleaned extract applies data minimization even to public material.

## Known conflict and review state

The report's Builder flight page says both 122 supported person-times and 132 total supported
people. It also shows 297 applications and a 50.4% selection rate without definitions sufficient
to reconcile the figures. These values remain `pending_reconciliation` and are not approved for
Bot QA.

The entire first source is currently:

- `sanitization_status: pending`;
- `review_status: pending`;
- `allowed_uses: [evidence_only]`;
- runtime disconnected.

## Review and future release

Before any section is used by the Bot, a follow-up change must:

1. compare present-tense claims with current official sources;
2. reconcile or exclude contradictory aggregates;
3. have a GCC content owner review the cleaned extract and its page mapping;
4. define a small projection containing only approved claims and citations;
5. add deterministic questions and fact-boundary tests;
6. separately authorize and implement runtime loading, with rollback instructions.

Until all six steps are complete, the report remains research evidence only.

## Validation

Run:

```powershell
python -m gcc_agent.knowledge.validate_history
python -m gcc_agent.knowledge.validate_cases
python -m tests
```

The history validator checks schema, unique identifiers, page ranges, aggregate periods, storage
location, normalized checksum, public source URL, required warning／conflict markers, unsafe voter
or access data, and the evidence-only gate. The case validator also recognizes history extracts as
registered files so they are not mistaken for orphan case evidence.
