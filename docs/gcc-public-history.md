# GCC public-history evidence layer

Decision dates: 2026-10-20, 2026-10-22
Tasks: `REPORT-KB-001A`, `REPORT-KB-001B`, `REPORT-KB-RUNTIME-001`

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
deterministic link-first selector
        ↓
fixed answer + public report citation
```

The source and seven projections are content-owner approved and connected through a fail-closed
runtime gate. The runtime reads only the explicit projection allowlist; it never reads the cleaned
extract or original PDF into the AI prompt. Matching answers are returned without an OpenAI call.
The history layer remains separate from `values.yaml`, onboarding, canonical case retrieval and
application review.

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

On 2026-10-22 the content owner directed the Bot to use the report-stated 50.4% overall selection
rate as the historical answer. Its denominator and calculation remain `pending_reconciliation`.
The approved answer therefore repeats 50.4%, says that the report does not define the denominator
or method, and forbids deriving the percentage from 297 applications and 132 supported
person-times. The report also does not establish a deduplicated unique-person count.

The source is now:

- `sanitization_status: human_reviewed`;
- `review_status: approved`;
- `allowed_uses: [evidence_only, bot_qa]`;
- `runtime.connected: true`, restricted to eligible approved projections.

## Approved projection boundary

The seven approved projections cover only:

1. GCC historical development from 2022-10 through the 2023–2025 report period;
2. historical fund structure and funding directions;
3. project names grouped by the report's historical categories;
4. Builder flight history, using 132 person-times and the bounded report-stated 50.4% rate;
5. the historical governance, funding process and cooperation methods;
6. two-year donation, category, milestone-rate, regional and operating-expense aggregates;
7. historical Builder／ETH City／university Web3 programme reach.

Each projection carries its question examples, fixed Traditional-Chinese answer, exact source and
section references, citation URL, excluded claims and content-owner review metadata. Projections
cannot cite an `excluded_from_bot` section.

The runtime selector uses explicit historical intent and topic rules. Present-tense policy or
application questions do not use the history layer; existing current official fact routes keep
precedence. Builder questions may use the fixed historical answer unless they ask about current
availability or applying. Simplified-Chinese and English users receive an explicit note that the
approved answer remains in Traditional Chinese rather than an unreviewed translation.

Every deterministic reply includes the public report citation. A source follow-up can reuse the
projection from the recent assistant answer. Private and configured-group mention routes share the
same selector while retaining their existing access and session boundaries.

## Rollback

Revert the runtime integration commit or set `runtime.connected: false` together with the matching
schema／test rollback. The production loader then returns zero history records and existing current
policy, canonical case, link-first and AI routes continue independently. Do not remove or weaken
source review metadata as a runtime switch.

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
historical wording, excluded sections and the requirement that any 50.4% answer explicitly state
the undefined denominator／calculation boundary. Runtime tests independently fail closed on schema,
connection, review, source, section and citation regressions; verify seven minimal projections,
current-versus-historical routing, locale fallback, private／group replies and AI-prompt isolation.
The case validator also recognizes history extracts as registered files so they are not mistaken
for orphan case evidence.
