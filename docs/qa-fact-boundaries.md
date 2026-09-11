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

The public pages do not publish 40/30/20/10 weights, 70/40 thresholds, or a
duration for each individual review stage. The bot must say that these details
are not published instead of inferring them.

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

## Rollback

If a published fact is found to be wrong, revert the affected release or replace
that deterministic answer with a source-only response stating that the detail is
under review. Do not restore the old numeric rubric to the general Q&A prompt.
If the website is temporarily unavailable, keep the last reviewed wording with
its direct URL and avoid adding new claims until a human content owner verifies
them.
