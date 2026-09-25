# Project Evidence TODO

This is the content-evidence sub-list for `CONTENT-001` and `CONTENT-002` in the
canonical [`docs/todo.md`](todo.md). It does **not** override the project-wide
priority order. Do not publish private applications, votes, applicant identities,
or reimbursements merely to close a checkbox.

## Funding execution reconciliation — intentionally non-blocking

A signed Snapshot proposal or vote records a governance proposal／decision. It is
not by itself evidence that the approved amount was transferred, a milestone was
accepted, or an unlock happened exactly as proposed.

- [ ] Model and record `governance_decision`, actual `disbursement`, milestone
  `acceptance`, and milestone `unlock` as separate events with separate sources.
- [ ] Reconcile Vyper's conflicting `30,000`／`40,000` amount meanings: requested,
  approved, transferred, unlocked, or another accounting basis.
- [ ] Reconcile Wamotopia 2026's `8,000`／`8,800` amount meanings on the same basis.
- [ ] Check every signed grant Snapshot against available transaction, accounting,
  payment and milestone follow-up records; record partial execution rather than
  copying proposal milestones into actual outcomes.
- [ ] Assign an authorized GCC follow-up owner to confirm each resolution and its
  effective date without publishing private reviewer／recipient material.

Until the assigned owner finishes a check, preserve all conflicting values and mark
the operational fact `unknown`／`pending_reconciliation`. Exclude that disputed
claim from bot factual answers, comparison examples and application review. This
work is tracked as `GRANT-RECON-001` and does not block unrelated repairs or
non-conflicting case evidence.

## First schema 0.2 import batch — OSKey and OpenRPC

- [x] Match each Snapshot requested amount to the GCC project-page amount.
- [x] Preserve the closed public vote and amount ballot without treating either
  as payment or milestone evidence.
- [x] Store local public-source extracts and link every structured claim to a
  stable snapshot id.
- [x] Keep actual disbursement, milestone acceptance／unlock and delivery unknown.
- [x] Keep both cases `draft` and excluded from Bot QA／AI review.
- [x] Add owner-approved sanitized application evidence covering public problems,
  funding use, deliverables, milestones, sustainability, anonymized governance
  concerns and applicant responses. Exclude voter identity data, per-voter
  metadata, meeting credentials and unnecessary biographies.
- [ ] GCC content owner reviews the two public summaries, public-goods assessments,
  links and cautions before either record may move to `reviewed`／`published`.
- [ ] If milestone amounts need structured querying, revise the legacy
  `unlock_amount_usd` field in a future schema version; do not convert proposal
  USDC values into USD merely to fill it.

This batch has no identified amount conflict: OSKey is 30,000 in both its public
proposal and GCC page, while OpenRPC is 25,000 and its public amount ballot records
no adjustment. This does not establish that either amount was actually paid.

## Tier A — correctness and privacy blockers for existing seed cases

Complete these before describing the affected records as verified public cases.

### ETH Beijing 2025

- [ ] Verify the currency and accounting meaning of the GCC project-page amount `3000`.
- [ ] Resolve why the GCC project page shows `2022.04.04` for a 2025 case; record
  the explanation or mark the field as unresolved rather than choosing a date.
- [ ] Add a stable 2025 official archive or screenshot. The live event site may
  describe a later edition and is not sufficient historical evidence.
- [ ] Locate the detailed GCC grant application and committee decision, if they
  exist; classify each as public, redacted, internal, unavailable, or unknown.

### Devconnect Flight Scholarship 2025

- [ ] Add an independently verifiable archive or screenshot of the GCC X announcement.
- [ ] Archive the Tally form at `https://tally.so/r/w2025L` if it remains public
  and the form owner permits archival use.
- [ ] Decide and document which applicant, recipient, selection, reimbursement,
  and disbursement fields must remain private or internal before importing them.
- [ ] Locate selection and disbursement evidence; publish only aggregate or
  redacted facts allowed by the privacy decision.

### ETH City / University Web3 Funding Tracks 2025

- [x] GCC owner confirmed these are two independent funding tracks under one
  shared proposal. Stable track ids and the future individual-case intake route
  are documented in [`funding-track-case-intake.md`](funding-track-case-intake.md).
- [x] GCC owner confirmed on 2026-09-20 that the existing ETH Beijing 2025 case
  belongs to `gcc-eth-city-2025`; its case record now carries that link. This
  confirms track membership only, not the unresolved amount, date, payment, or
  outcome facts.
- [ ] Obtain verifiable individual award/activity details for further cases and
  link each to exactly one funding track; do not infer membership from a name.
- [ ] Define public/internal/redacted treatment for applications, reviewers,
  decisions, amounts and applicant identity.
- [ ] Link public or shareable approval decisions and approval dates to the
  correct funding track without exposing private reviewer data.

ETH Beijing 2025 and Devconnect Flight Scholarship 2025 currently have no
additional owner-supplied detailed records. Keep their unresolved fields
unknown and do not manufacture missing application, selection, or payment data.

## Tier B — outcome and impact evidence

Start only after the corresponding Tier A claims and privacy boundary are stable.

### ETH Beijing 2025

- [ ] Add post-event reports, photos, submissions, judging results and participant
  metrics, distinguishing organiser claims from independently verifiable evidence.

### Devconnect Flight Scholarship 2025

- [ ] Add recipient reports, community sharing notes or published reflections
  where recipients made them public for reuse.
- [ ] Add attributable outcomes such as sessions attended, projects launched,
  collaborations or public write-ups; avoid claiming causality from attendance alone.

### ETH City / University Web3 Funding Tracks 2025

- [ ] Link completed projects and activity reports to the correct track and award.
- [ ] Add public photos, videos, participation data, feedback, repositories and
  write-ups with source date and access level.

## Tier C — coverage expansion

- [ ] Import individual downstream applications only after the subgrant data
  model, privacy policy and review workflow are approved.
- [ ] Work category by category; every new case must pass schema validation,
  provenance review and AI-usage access checks.
- [ ] Keep unavailable evidence explicitly `unknown`／`unavailable`; completeness
  targets must never incentivise invented summaries or publication of private data.

## Definition of done for one evidence item

- The source URL or storage URI, capture date, source type and access level exist.
- Public facts can be regenerated from preserved source material.
- Uncertainty and conflicts are visible in the case record.
- Private/internal material is excluded from public output and AI prompt context.
- A human reviewer confirms the record before release.
