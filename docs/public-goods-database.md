# Public Goods Database Design

This document describes the implementation track. Teaching notes and unresolved
discussion live in `docs/learning-room.md`.

## Direction

The database should become reusable public infrastructure for Chinese-language
public goods knowledge. The Telegram agent is one consumer, not the owner of the
data model.

Initial scope:

- Seed one representative case from each existing GCC project category.
- Preserve compatibility with the existing `projects.yaml` knowledge base.
- Define schema fields for future detailed application imports.
- Define schema fields for future committee voting record imports.
- Define snapshot metadata so each project can later point to immutable source
  material.

The 2025 ETH City / university Web3 seed is a shared governance-proposal record,
not one downstream award. GCC owner confirmed its two funding tracks are
independent. Each has a stable `track_id`; a future verified individual case
uses `funding_track_id` to identify exactly one track. See
[`funding-track-case-intake.md`](funding-track-case-intake.md) for the intake
fields and privacy boundary. The proposal's two funding pools do not prove
individual approval, disbursement, or current operating status.

Out of scope for this first step:

- Importing all 67 projects.
- Publishing private applications or committee records.
- Fully automating grant review.
- Replacing the current `pre_screen()` scoring logic.

## Data Layers

### 1. Public Case Record

This is the stable public-facing database record: name, category, amount,
summary, why funded, region, tags, links, and source URLs.

### 2. Source Snapshots

Snapshots are point-in-time references to source material. A snapshot can point
to a public web page, a private application, an exported PDF, a vote record, or a
future content-addressed archive.

The schema reserves fields for:

- `snapshot_id`
- `captured_at`
- `source_type`
- `storage_uri`
- `source_url`
- `checksum`
- `access_level`

A signed governance Snapshot proves the proposal or decision captured at that time;
it does not prove actual disbursement, milestone acceptance, or fund unlock. Those
execution events require separate transaction／accounting／operator evidence. When
sources conflict, preserve the alternatives, mark the execution fact
`pending_reconciliation`, and exclude it from AI factual answers and review until
an authorized GCC owner confirms it.

### 3. Grant Application

Applications are modeled as linked evidence, not copied into the public database
by default. A case can say that an application exists, whether it is public,
private, or redacted, and where an authorized system can find it later.

For an owner-approved public application, a local sanitized evidence layer may
preserve the public problem, source-reported state, funding plan, deliverables,
milestones, sustainability claims, anonymized governance risks and applicant
responses. It excludes voter identity data, per-voter metadata, meeting
credentials, unnecessary biographies and private material. The structured case
points to this evidence but remains unavailable to Bot／AI use until human review.
See [`sanitized-application-evidence.md`](sanitized-application-evidence.md).

### 4. Voting Record

Voting records are also modeled as linked evidence. The schema supports public
aggregate records now and can later support committee-level records if GCC
chooses to publish or internally expose them.

### 5. AI Screening Context

The bot should retrieve only the fields that are allowed for screening. This
prevents private applications and voting notes from accidentally becoming prompt
material.

## Design Principle

Each case should separate four things:

- What happened: public factual record.
- Why it was funded: GCC's reason and public goods interpretation.
- What evidence supports it: source URLs, snapshots, applications, votes.
- What AI may use: concise retrieval text and allowed screening dimensions.

## Schema 0.2

Schema 0.2 migrates all existing seed records and provides the validation boundary
for the next small import batch. It distinguishes a funding programme, an
individual grant case, and a placeholder; separates requested, governance-approved,
and disbursed amounts; and reserves independently sourced execution events for
governance decisions, payments, milestone acceptance／unlock, activity completion,
and reports. Full field and validation rules are documented in
[`project-case-schema-v0.2.md`](project-case-schema-v0.2.md).

New public record fields:

- `grant_year`: when GCC approved or recorded the grant.
- `activity_year`: when the activity or project work mainly happens.
- `language_community`: language or cultural communities served.
- `funding`: requested, governance-approved, and disbursed facts with original
  currency, evidence references, and uncertainty status; legacy USD fields are
  temporarily retained for compatibility.
- `execution_events`: separately sourced governance and real-world execution
  events; an empty list does not imply that no event occurred.
- `program_details`: dates, location, application deadline, eligibility,
  selection criteria, deliverables, and milestones.
- `public_goods_dimensions`: flexible assessments for open source,
  accessibility, knowledge transfer, community impact, and classical public
  goods dimensions when relevant.
- `impact_evidence`: concrete evidence such as participation, deliverables,
  adoption, education, community outcomes, open-source outputs, or funding
  access.
- `lifecycle_status`: grant, delivery, and reporting status.

New evidence fields:

- `vote_summary`: structured vote choices, scores, proposal id, platform, and
  state.
- `raw_data_status`: whether raw data is captured by API, official site, manual
  user supply, pending, unavailable, or not applicable.

Fields deliberately not duplicated:

- GitHub links stay under `links.repository_url`.
- Source records stay under `evidence.snapshots` instead of a parallel
  top-level `sources` block.
- Database licensing should be handled at the database or repository level
  before making per-case licensing mandatory.

## Delivery Status

Completed foundations:

- The six existing seeds are migrated to schema 0.2; this migration imports no
  additional cases.
- Draft 2020-12 and cross-record validation run locally and in the release gate.
- A loader exposes all cases and the subset explicitly allowed for AI review.
- Source snapshots preserve raw material separately from interpreted summaries.
- The first post-migration batch adds OSKey and OpenRPC as `draft` grant cases.
  For both records, the public proposal amount, closed governance vote and GCC
  project-page amount agree. Actual disbursement, milestone acceptance, unlock
  and delivery remain `unknown`; neither case is available to Bot QA or AI review.

The first batch also exposed a deliberate compatibility limitation: proposed
milestone amounts are denominated in USDC, while the legacy milestone field is
named `unlock_amount_usd`. The import therefore preserves the original USDC
amount in the milestone description and leaves `unlock_amount_usd` empty rather
than silently converting currencies. A future schema revision may replace that
legacy field with the same amount／currency fact shape used by `funding` and
`execution_events`.

The remaining work is governed by `PGDATA-001`, `CONTENT-001`,
`GOVERNANCE-001`, `CONTENT-002`, and `SEARCH-001` in the canonical
[`docs/todo.md`](todo.md). That ordering is intentional: privacy, screening
guardrails, provenance, and licensing must be stable before importing private
applications or adding semantic search.

This design document must not be used as a parallel backlog. Detailed evidence
gaps remain in [`docs/project-evidence-todo.md`](project-evidence-todo.md).
