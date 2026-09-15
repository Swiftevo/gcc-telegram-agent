# GCC newcomer onboarding content foundation

Status: owner-approved Simplified Chinese content; not connected to Bot runtime  
Decision date: 2026-09-16

## Product boundary

- The first onboarding audience is limited to current human members of the configured
  `GCC_GROUP_ID`. People outside that group continue to rely on public outreach and
  events; this work does not create a public pre-membership Q&A route.
- Onboarding is question-led and lightweight. The baseline defines no navigation
  buttons, progress tracker, permanent interest profile, or new application flow.
- This change stores and validates content only. It does not change `/start`, access
  rules, routing, prompts, replies, SQLite, secrets, or production behaviour.

## Source and update boundary

- The Simplified Chinese baseline in [`../data/onboarding.yaml`](../data/onboarding.yaml)
  is the text supplied and approved by the GCC owner in this repository workflow.
- The four Feishu pages remain changing internal working documents. Their URLs are not
  stored, the Bot does not fetch them, and no automatic sync is introduced.
- Future updates use the same explicit process: the owner provides revised text, the
  repository version is reviewed through a PR, and only then may a later runtime
  integration use it.
- The owner confirmed that the website, X account, Telegram volunteer-group invite,
  and `admin@gccofficial.org` are public channels. A read-only check also found the
  Telegram and email contacts on the live GCC homepage and contact page.
- Per owner decision, the baseline does not yet implement expiry or automatic stale
  content handling. `2026 H2` remains an explicit context label, and recruitment wording
  tells users that the latest announcement controls.

## Language boundary

Only `zh-CN` is present. Traditional Chinese and English review, per-locale publication
state, and safe fallback remain deferred to `ONBOARDING-I18N-001`. The Bot must not use
unreviewed machine translation as official GCC wording.

## Content structure

The four-part contributor journey is represented by nine question-sized topics:

1. GCC overview;
2. GCC beliefs about public goods;
3. the owner-supplied `2026 H2` OPS focus;
4. reasons to participate;
5. official channels;
6. joining the volunteer community;
7. activities and tasks;
8. volunteer versus builder;
9. becoming a GCC builder.

Each topic contains suggested questions, a short answer, optional paragraphs and bullets,
a single lightweight next prompt, and public links where relevant. The file deliberately
contains no internal Feishu URL.

## Later runtime decision

Connecting this file to answers requires a separate owner-approved task. That task must
decide deterministic matching, answer selection, how one follow-up prompt is appended,
and how existing session retention applies. It must retain current group membership,
rate-limit, privacy, application, and session-isolation boundaries.

There is also a known source-priority conflict to resolve before activation:
`data/onboarding.yaml` says the owner-supplied `2026 H2` focus has converged on OPS,
while the current `values.yaml` still lists five older priority themes and its GCC summary
describes four of them. Runtime integration must not blend both as simultaneously current.
The GCC owner must decide whether onboarding takes precedence for newcomer questions or
whether the canonical values content should be updated in the same reviewed change.

## Verification and rollback

`gcc_agent.knowledge.onboarding` validates the content contract and fails on duplicate or
unreferenced topics, unexpected locale/status, enabled automatic sync, runtime activation,
or an internal Feishu hostname. The complete test entry point includes these checks.

Because the dataset is not imported by the Telegram application, rollback of this content
foundation is a normal image rollback or file reversion. No database, user record, secret,
session, message, volume, or snapshot migration is required.
