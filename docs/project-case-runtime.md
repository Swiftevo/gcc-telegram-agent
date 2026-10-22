# Canonical Case Runtime Gate

Decision date: 2026-10-11  
Task: `PGDATA-001` step 6

## Purpose

The Bot may read the canonical case database only through a deny-by-default
runtime gate. This connects the data model to QA without treating schema-valid,
draft, private, disputed, or merely imported material as publishable facts.

The frozen `projects.yaml` catalog remains the compatibility source for existing
project links and the general project index. Canonical records supplement it
only after explicit content and source approval.

## Eligibility

A canonical record is eligible for Bot QA only when all of these conditions are
true:

1. It is not a placeholder and `ai_review_usage.allowed` is explicitly `true`.
2. Governance visibility is `public`; case status is `reviewed` or `published`;
   review date and reviewer role are present.
3. At least one local source is registered. Every source is `public` or an
   approved, human-reviewed `redacted` extract.
4. Every source review is `approved`, records reviewer role/date, and explicitly
   includes `bot_qa` in `allowed_uses`.
5. Every factual source ID used by the public record or aggregate vote resolves
   to that approved case-local source set.
6. No field anywhere in the case is `pending_reconciliation`.
7. The canonical database remains schema 0.4.0 and the public summary is not
   empty.

This gate runs again when the application loads data. Passing CI or JSON Schema
alone is not runtime authorization.

## Runtime allowlist

The prompt projection may contain only:

- stable case identity, record type, title, category and fund type;
- database update date and case review date;
- approved public-record facts: years, communities, regions, tags, summary,
  funding rationale, structured funding, independently recorded execution
  events, programme dates／eligibility／deliverables／tracks／milestones, public-
  goods dimensions, impact evidence, lifecycle state and public links;
- aggregate vote summary without voter-level data;
- minimal approved-source metadata: source ID, type, access level, capture date,
  and public source URL. A redacted source never exposes an original URL.

It never projects private／internal evidence pointers, raw-data locations,
repository-local paths, checksums, `reference_urls`, reviewer identity, private
notes, application-review retrieval text, screening dimensions or cautions.
Selection is deterministic and limited to a small set matching the question.

## Answer behavior and provenance

An explicit approved case-name question receives a deterministic overview before
the language model. Other matching questions may receive the selected allowlist
as a system data block marked as facts rather than instructions.
The deterministic overview is sent as plain text: source labels and fact-status
values contain underscores that Telegram's legacy Markdown parser can reject.

Case-backed answers include public source URLs and the canonical database update
date. Requested, governance-approved and disbursed values retain separate labels
and fact statuses. Unknown payment remains unknown; proposed milestones are not
described as accepted, unlocked or paid. The length limiter preserves the
provenance footer.

## Review state

At initial implementation, all eight canonical cases were `seed` or `draft`, all
14 sources were `pending`／`evidence_only`, and the runtime gate returned zero.
The 2026-10-23 OSKey content-owner decision approves its three public extracts
for historical `bot_qa` and moves that one case to `reviewed`; the gate now
selects only OSKey. Its USD figures are owner-confirmed public reporting units,
not transfer-token assertions. The Snapshot schedule and milestone review govern
releases, but actual payment stages, amounts and dates remain undisclosed.
The other seven records remain ineligible. Application-review use remains
separately denied, including for OSKey.

## Enabling one case

Use one case per review PR:

1. Content owner checks every public claim and resolves or removes conflicts.
2. Approve each source, add `bot_qa`, and record reviewer role/date. Redacted
   evidence must be human-reviewed.
3. Mark the case `reviewed` or `published`, record reviewer role/date, and set
   `ai_review_usage.allowed: true` only after deciding that the allowlist is safe.
4. Update `canonical_inventory`, run the canonical validator and full test suite,
   inspect the exact runtime projection, and review the generated deterministic
   answer and provenance in all supported languages.
5. Merge and perform private／group production E2E for the specific case.

Do not approve several cases merely to make the runtime count non-zero.

## Rollback

For one content problem, set `ai_review_usage.allowed: false` and redeploy; the
runtime fails closed immediately for that case. Removing `bot_qa` from any source
or returning the case to `draft` also makes it ineligible, but the boolean is the
clearest emergency switch.

For a connector regression, revert the runtime integration PR. The frozen legacy
catalog remains available, and no production SQLite migration or user-data
rollback is required.
