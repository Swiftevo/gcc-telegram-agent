# Learning Room

This file is the teaching and discussion room for the public goods database work.
It is intentionally separate from implementation docs, schemas, and code.

## Why This Room Exists

We want to learn while building, but we do not want unfinished discussion to leak
into production design. Questions, doubts, trade-offs, and vocabulary notes should
live here first. Once a decision becomes stable, we can move the outcome into the
schema, API docs, or implementation.

## Current Learning Goals

- Understand the difference between a bot-specific knowledge file and a reusable
  public goods database.
- Learn how to design a project case schema that can support public summaries,
  grant applications, voting records, and historical snapshots.
- Keep a clear boundary between public facts, private committee material, and AI
  screening interpretation.
- Build in small steps so each design choice can be questioned before it hardens.

## Discussion Log

### 2026-05-27: Starting Direction

The first implementation step is not to automate all review decisions. It is to
define a data contract for funded project cases and seed one case from each GCC
project category.

Key design choice:

- Keep `projects.yaml` as the current bot-oriented knowledge source for now.
- Add a new `data/project-case-seeds.yaml` as a more explicit case database seed.
- Add `schema/project.schema.json` to document the target shape.
- Reserve extension points for project snapshots, detailed grant applications,
  and GCC committee voting records without requiring those private documents to
  be public today.

Open questions:

- Which parts of historical applications can be public by default?
- Should committee voting records expose individual votes, aggregate votes, or
  only the final decision?
- What license should the public database use?
- Should future snapshots be stored in Git, object storage, IPFS, or a mix?

### 2026-05-27: First Source Imports

The user provided source links for the six seed categories. We imported source
evidence conservatively:

- Open Source: Vyper Snapshot proposal imported.
- Community: annual ETH City and university Web3 funding Snapshot imported.
- Event: Wamotopia 2026 Snapshot proposal imported.
- ETH City Series: ETH Beijing official event site imported because this series
  does not use Snapshot for the case provided.
- Travel Scholarship: X source URL preserved, but automated capture did not
  retrieve the post body. The user later manually provided the post text, so the
  case now has raw data and can be used as a travel scholarship precedent with a
  caution that independent archive/screenshot verification is still desirable.
- Gitcoin: fields preserved but no data imported, per user instruction.

Teaching note:

Source import does not mean "AI can freely use everything." Each case still has
an `ai_review_usage` block. This lets us decide which extracted facts are safe
for initial screening and which evidence should remain private, internal, or
manual-review-only.

Data quality note:

The user-provided community Snapshot URL ended with one extra character. Snapshot
Hub returned the proposal under id
`0x407f8915291757db03ae1b19e30162bb785e0dc61a6ab5e9ad958b1911fe8476`, so both
the user-provided URL and the normalized id are recorded.

Follow-up correction:

The first source import only stored extracted notes. The raw proposal/application
body is now stored inside each source snapshot markdown file under `## Raw Data`.
This keeps the database auditable: future summaries can be regenerated from the
raw source instead of relying only on our interpretation.

### 2026-05-29: Schema Expansion From Real Cases

We reviewed the six seed cases before expanding the schema. The decision was not
to add every theoretical public goods field as a required field. Instead, we
added optional fields that the current cases actually need:

- `grant_year` and `activity_year` instead of a single ambiguous `year`.
- `language_community` for Chinese-speaking and other served communities.
- `funding` because amount data differs by case: requested grant, total budget,
  per-person cap, milestone unlocks, and reimbursement are different things.
- `program_details` for deadlines, dates, location, eligibility, selection
  criteria, deliverables, and milestones.
- `public_goods_dimensions` as flexible assessments, not hard true/false theory
  gates.
- `impact_evidence` for concrete evidence that can later support search and
  review.
- `lifecycle_status` to avoid overloading the existing `status` fields.
- `vote_summary` so Snapshot choices and scores are machine-readable.
- `raw_data_status` so a case can distinguish API-captured raw data from
  manually supplied, pending, unavailable, or not applicable raw data.

We intentionally did not add separate `github`, `sources`, or per-case `license`
fields at this stage. Existing `links.repository_url`, `evidence.snapshots`, and
future repository-level licensing cover those needs more cleanly for now.

### 2026-05-29: Seed Cases Populated With New Fields

The six seed cases now use the expanded schema fields. The rule for this pass:
structure what is visible in the current sources, and mark uncertainty instead
of guessing.

Examples:

- Vyper has milestone funding and education/community impact evidence.
- The annual ETH City / university Web3 case is marked as a bundled dual-track
  program so future search does not confuse it with one single project.
- Wamotopia is marked as retroactive activity funding because the event had
  already happened when the proposal requested confirmation.
- ETH Beijing was corrected after the user noticed the official website had
  updated to the 2026 edition. The 2025 case now uses a PKUBlockchain X recap as
  source evidence instead of the current ETH Beijing website.
- Devconnect is marked as reimbursement-based travel support with user-supplied
  raw X post data.
- Gitcoin remains a placeholder with unknown/not-applicable fields because the
  user asked not to import data yet.

## Terms

- `project`: The funded initiative itself.
- `case`: A structured database record about a funded project.
- `snapshot`: A point-in-time copy of public or private source material used to
  support the case record.
- `grant_application`: The detailed application submitted to GCC, possibly
  private or partially redacted.
- `voting_record`: The committee decision record, possibly public, aggregate, or
  private depending on governance policy.
- `AI screening context`: The subset of case data that the agent is allowed to
  retrieve and cite during initial review.
