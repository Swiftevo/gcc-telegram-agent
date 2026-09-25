# Sanitized Public Application Evidence

Decision date: 2026-09-25  
Initial cases: OSKey and OpenRPC

## Purpose

The case database needs enough application evidence to explain what a project
proposed, how funds were intended to be used, and what risks governance raised.
It does not need to duplicate every identity, credential, discussion transcript,
or personal biography from a public source.

For an owner-approved public application, a sanitized evidence document may sit
between the original source and the structured case record:

```text
public Snapshot or application
        ↓
sanitized application evidence
        ↓
structured case record
        ↓
human review before any Bot or AI use
```

## Preserve

- project and application type;
- requested amount and original currency notation;
- public problem and proposed approach;
- source-reported current state and adoption;
- funding-use plan;
- proposed deliverables and milestones;
- sustainability and delivery-capacity claims;
- commitments made to GCC;
- anonymized governance risks and applicant responses;
- explicit evidence limits and unresolved execution facts.

## Exclude

- voter names, ENS names and wallet addresses;
- per-voter dates, voting power and other row-level vote metadata;
- named attribution for reviewer comments when the substantive concern can be
  preserved anonymously;
- meeting or recording passwords and other access credentials;
- unnecessary personal biographies and employment histories;
- private applications, internal notes or non-public committee material;
- claims that a proposal, vote or project-page label proves payment, acceptance,
  unlock, delivery or impact.

## Data Model

Each sanitized document receives its own stable `snapshot_id` with:

- `source_type: grant_application`;
- `access_level: public`;
- the original public source URL;
- a local `storage_uri` under `data/source-snapshots/`.

The case's `evidence.grant_application` points to that sanitized snapshot. Public
vote totals remain in `vote_summary`; individual vote rows are not copied. The
original proposal extract remains a separate `snapshot_proposal` source.

## Runtime and Review Boundary

Creating this evidence does not publish a case to the Bot. The case remains:

- `governance.review_status: draft`;
- `ai_review_usage.allowed: false`;
- unavailable to Bot QA and application scoring.

A GCC content owner must review the summary, evidence limits, public-goods
assessment, links and cautions before a later change may mark the record
`reviewed` or `published`. Actual disbursement and milestone events still require
their own transaction, accounting, acceptance or authorized-owner evidence.
