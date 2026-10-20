# GCC public-history evidence layer

Decision date: 2026-10-20
Tasks: `REPORT-KB-001A`, `REPORT-KB-001B`

## Purpose and boundary

`data/gcc-public-history.yaml` registers public, time-bounded material about GCC as an organization.
It is separate from both runtime knowledge and the canonical project-case database:

```text
public historical report
        ↓
cleaned, page-scoped evidence extract
        ↓ automated schema / checksum / privacy gate
history registry: reviewed historical evidence
        ↓ content-owner approval + explicit fact boundaries
approved projections only
        ↓
Bot runtime, only after an explicit implementation and release decision
```

The source and five initial projections are content-owner approved, but the registry remains
deliberately disconnected from runtime. It is not read by `values.yaml`, the QA prompt, onboarding,
case retrieval or application review. Approval makes the projections eligible for a later runtime
change; it does not itself change Bot behaviour.

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

## Reconciliation and review state

The GCC content owner confirmed that Builder flight supported 132 person-times through the report
period. The value 122 in the report body is recorded as a typo, while the annual figures also total 132. The
approved projection uses 297 applications and 132 supported person-times.

The page's 50.4% selection rate still has no definition or denominator that reconciles with those
totals. It remains `pending_reconciliation` and is prohibited from approved answer text. The report
also does not establish a deduplicated unique-person count.

The source is now:

- `sanitization_status: human_reviewed`;
- `review_status: approved`;
- `allowed_uses: [evidence_only, bot_qa]`;
- runtime disconnected.

## Approved projection boundary

The five approved projections cover only:

1. GCC historical development from 2022-10 through the 2023–2025 report period;
2. historical fund structure and funding directions;
3. project names grouped by the report's historical categories;
4. Builder flight history, using 132 person-times and excluding 50.4%;
5. the historical governance and funding process.

Each projection carries its question examples, fixed Traditional-Chinese answer, exact source and
section references, citation URL, excluded claims and content-owner review metadata. Projections
cannot cite an `excluded_from_bot` section.

Before the Bot may answer from them, a separate runtime PR must implement deterministic projection
selection, current-versus-historical routing, source citation, private／group tests and rollback. It
must load only `approved_projections`, never the full extract. Until then, production behaviour is
unchanged.

## Validation

Run:

```powershell
python -m gcc_agent.knowledge.validate_history
python -m gcc_agent.knowledge.validate_cases
python -m tests
```

The history validator checks schema, unique source／section／projection identifiers, page ranges,
aggregate periods, storage location, normalized checksum, public source URL, warning／reconciliation
markers, unsafe voter or access data, source review gates, projection references and citations,
historical wording, excluded sections and the 50.4% block. The case validator also recognizes
history extracts as registered files so they are not mistaken for orphan case evidence.
