# GCC QA Fact Boundaries

This runbook defines which funding-policy claims the bot may present as official,
how those claims are sourced, and how to update or roll back the deterministic
answers introduced by `QA-FACT-001`.

## Purpose

General Q&A must not convert an internal bot heuristic into GCC policy. Questions
about funding process, review criteria, scoring, timing, and governance execution
are high-risk because a plausible but unsupported answer can mislead applicants.
For these intents, the bot uses reviewed deterministic answers before considering
the language model.

## Reviewed public sources

Verified on 2026-09-12:

| Claim scope | Canonical source | Permitted statement |
|---|---|---|
| Overall funding process | <https://www.gccofficial.org/about> | Initial screening, full review, due diligence, voting-committee decision, then agreement and milestone/progress management; the page says decisions usually require at least two-thirds support |
| Public Fund | <https://www.gccofficial.org/application/public> | Published considerations, application forms, exclusions, and an 8–12 week round cycle |
| Special Funds | <https://www.gccofficial.org/application/special> | Theme-specific, small, rolling applications described as faster; use the listed fund-specific forms |

GCC content owner confirmed on 2026-10-22 that the public
[Cohort 4 announcement](https://x.com/GCCofCommons/status/2103414364414079142?s=20)
is approved and takes precedence over the website's older four priority
categories **for this round**. The owner supplied the announcement text and
source URL; the X post could not be independently fetched from this environment.
The [Public Fund page](https://www.gccofficial.org/application/public) and its
project form were checked separately. The form identifies Cohort 4; a separate
personal-basic-income form on that page contains older cohort wording and must
not be presented as the Cohort 4 application form.

The general public pages do not publish 40/30/20/10 weights or 70/40
thresholds. They do not specify a duration for every review stage; Cohort 4's
announcement adds planned dates for some stages. The bot must not infer
unpublished durations or turn planned dates into actual execution claims.

## University Builder plan 2026

On 2026-10-22, the GCC content owner approved the supplied public announcement
and 23-page appendix for Bot Q&A. The external application is
<https://survey.gccofficial.org/552158?lang=zh-Hans>; the owner-supplied
[appendix](https://docs.google.com/document/d/1kxkpeluBX7k4sAi_uV7aAO0TFOw8BTvSLmkd7XhEWiI/edit?usp=sharing)
contains category details. `data/university-builder-2026.yaml` is the small,
reviewed runtime projection; the whole PDF and its fast-changing Appendix B
topic list are not placed in the model prompt.

This is an independent 2026 university programme, not the historical 2025
university Web3 line, ETH City or Cohort 4 Public Fund. Its 30/25/20/15/10
review weights belong **only** to this plan. Announced grant caps, cadence and
milestone payment rules do not prove any award, accepted milestone or payment.
The external form handles applications and private executor identity; the Bot
must not solicit those details or show its legacy internal application button.

Two public-source discrepancies remain. The form currently says alumni linkage
is 200 USD/event, while the owner approved the appendix's **150 USD/event**.
The appendix says daily operations are applied for by semester, while the owner
approved the form's **annual application**. Bot answers use those owner-approved
values and explicitly flag the mismatches. GCC must synchronize the form and
appendix; until then, applicants should confirm the final amount with GCC.

The approved Chinese text is Simplified Chinese. Traditional Chinese and
English prompts receive an explicit language fallback, pending human-reviewed
translations. `gcc_agent.qa.university_builder` fails closed without approval
or source metadata and takes precedence over generic special-fund links only
for current university-plan questions. Historical and ETH City questions retain
their own routes. After merging, verify private/group answers and rollback by
reverting the release or disabling this reviewed projection if a material fact
is withdrawn.

## Required distinctions

- The official website describes GCC's public process and considerations.
- The bot's `screening_rubric` remains a legacy internal triage heuristic until
  `REVIEW-001`; it is not an official score, cannot be cited in general Q&A, and
  cannot make a final approval or rejection.
- A community-call invitation is an optional next step, not a numbered review
  stage.
- A signed Snapshot proposal or vote records a governance proposal or decision.
  It does not by itself prove actual disbursement, milestone acceptance, or an
  unlock. Unreconciled execution claims remain unknown and are handled under
  `GRANT-RECON-001`.
- Public Fund details must not automatically be generalized to every Special
  Fund.
- Cohort 4's OPS focus, five unweighted criteria and 2026-09-25 through
  2026-10-31 23:59 (UTC+8) application window are round-scoped facts from the
  approved announcement, not permanent GCC policy. Its November/December
  screening, Demo Day, results and M0 dates are **plans**, not proof of events,
  grant agreements or payment. After the deadline, the bot must not claim the
  round is still accepting applications without a fresh owner-approved update.
- The announcement's 50+ projects, 100+ builders and >USD 1.6m cumulative
  donation claim has a different period/scope from the 2023–2025 report's
  aggregates. Do not use it to answer a current historical-total question
  until the accounting scope is reconciled. Cohort 3's ~USD 260,000 is
  described as *planned* support, not disbursement.

## Runtime behavior

`gcc_agent.qa.facts` handles reviewed policy intents in Traditional Chinese,
Simplified Chinese, and English. It covers:

- funding and review process;
- review criteria;
- whether an official numeric score exists;
- published timing and unknown per-stage timing;
- direct or contextual requests for sources;
- Snapshot decision versus actual execution.

These answers include direct sources and bypass the language model. Other
questions may use the model, but its system prompt excludes the internal rubric
and instructs it to identify unpublished information rather than guess.

`gcc_agent.qa.cohort4` loads the approved, public, round-scoped facts from
`data/cohort4.yaml` and answers explicit Cohort 4/current OPS intents before
the older general facts. It fails closed if approval/source metadata is missing.
The approved text is Simplified Chinese; Traditional Chinese and English
queries receive an explicitly labelled language fallback pending human-reviewed
translations. General historical projections retain their historical scope.

## Updating the facts

1. Re-read all three canonical pages and record the review date.
2. Update the localized answer in `gcc_agent/qa/facts.py` and the concise fallback
   policy in `values.yaml` together.
3. Preserve the distinction between Public and Special Funds.
4. Add or update exact Traditional Chinese, Simplified Chinese, and English
   regression cases.
5. Run `python -m tests` before opening a pull request.
6. After deployment, test the process, source, score, timing, and Snapshot prompts
   through an allowed Telegram path without submitting personal data.

For Cohort 4 updates, confirm with the content owner, update `data/cohort4.yaml`
and `values.yaml` together, preserve the time and planned-versus-actual boundaries,
then test private and group replies in addition to the automated suite. A website
copy change alone does not override the reviewed round-specific record.

## Rollback

If a published fact is found to be wrong, revert the affected release or replace
that deterministic answer with a source-only response stating that the detail is
under review. Do not restore the old numeric rubric to the general Q&A prompt.
If the website is temporarily unavailable, keep the last reviewed wording with
its direct URL and avoid adding new claims until a human content owner verifies
them.
