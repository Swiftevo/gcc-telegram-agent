# OSKey Sanitized Public Application Evidence

- Source: https://snapshot.org/#/s:gccofficial.eth/proposal/0x097e42fd59cf33b51ca2ecfbc230809e7597bf879b748dcf1f49950379e98a8d
- Prepared at: 2026-09-25
- Access level: public
- Evidence type: sanitized application evidence
- Proposal title: 关于捐赠OSKey的提案
- Requested amount: 30000u

## Sanitization Boundary

This evidence layer preserves facts needed to understand the application and its
governance risks. It deliberately excludes voter names, wallet addresses,
per-voter timestamps, per-voter voting power, named reviewer attribution,
unnecessary personal biographies, and meeting or recording credentials.

All statements below are applicant-, proposal-, or discussion-reported unless a
separate source is named. They are not independent technical validation and are
not evidence of payment, milestone acceptance, unlock, or completed delivery.

## Project and Public Problem

OSKey presents itself as a fully open-source, non-commercial hardware-wallet
project designed to run on general-purpose development boards. The application
frames proprietary hardware, vendor dependence, hardware cost, and difficulty
verifying closed or specialist devices as the public problems it addresses.

The proposed approach is to provide reusable firmware, embedded wallet
libraries, build guidance, reference designs, and a modular system that lets
users choose among different chips, boards, displays, connectivity options, and
security levels.

## Source-Reported State at Application

The application reported that a proof of concept could run on multiple platforms
and already covered a limited set of day-to-day wallet functions:

- BIP39 mnemonic creation and import;
- BIP32 and BIP44 hierarchical key derivation;
- secp256k1 signing;
- WalletConnect integration;
- embedded libraries intended for resource-constrained microcontrollers.

These are application claims. This import does not independently reproduce the
build, tests, supported-board count, security properties, or wallet integrations.

## Funding Use Plan

The application divides the requested total into three main uses. Line items use
`$`／`USD` notation even though the overall request is written as `30000u`; this
evidence preserves that notation without inferring a currency conversion.

### Product iteration and development or testing hardware — 21,000

- 6,000 for embedded firmware security, secure boot, encryption, upgrades,
  maintenance, displays, sound and buttons;
- 6,000 for desktop or application development and firmware management;
- 4,000 for core algorithms, embedded wallet libraries, chains and cryptographic
  support;
- 3,000 for platform adaptation, development boards and testing tools;
- 2,000 for one year of indexer, RPC and required backend services.

### Build guidance and hardware design — 4,000

- 1,500 for industrial, enclosure and structural design suitable for CNC or 3D
  printing;
- 2,500 for circuit and PCB design;
- deployment and development guidance intended to let users build devices
  independently.

### Open-source contributor support — 5,000

The application allocates half to retrospective contributor recognition and the
remainder to future contributors, development boards, and community support.

## Proposed Deliverables

- improve firmware, browser and application usability from a demonstration
  toward a more complete product experience;
- add safer on-device initialization and display-assisted confirmation;
- provide firmware management and improve the WalletConnect path;
- maintain reusable embedded wallet and cryptographic libraries;
- support more development boards, screens, chains and algorithms;
- publish build, hardware and security-level guidance;
- create reference enclosure, circuit and PCB designs;
- support contributors and distribute development kits;
- move toward a modular architecture for wallets and other physical devices.

## Proposed Milestones

| Milestone | Proposal share | Proposal amount | Target | Proposed scope |
| --- | ---: | ---: | --- | --- |
| M0 | 20% | 6,000 | vote approval | Initial unlock described by the proposal. |
| M1 | 30% | 9,000 | 2025 Q3-Q4 | Firmware, browser and application usability; display support; safer initialization and firmware management. |
| M2 | 30% | 9,000 | 2026 Q1 | Desktop and mobile applications, asset-management functions, WalletConnect improvement and broader chain support. |
| M3 | 20% | 6,000 | 2026 Q2 | Modular firmware and hardware design, configurable peripherals and easier physical-product integration. |

The milestone amounts and dates are planned terms. They are not recorded as
actual unlocks or completed work.

## Sustainability and Delivery Capacity

The application describes a lead developer, other technical contributors, and
support from an open developer community. In the governance discussion, the
applicant stated that the lead developer had other full-time work and that OSKey
was then an interest-driven open-source project.

The stated long-term model is to keep the core project open source while
potentially selling development kits or intermediary boards, and to encourage
multiple third parties to commercialize around and contribute back to the core.
This is a proposed sustainability path, not evidence that recurring revenue or a
commercial partner already exists.

## Proposed GCC Commitments

- cooperate with public communications and community activities;
- list GCC as a core supporter on project channels;
- provide some development kits to the GCC community;
- offer relevant embedded or hardware technical support to GCC when feasible.

## Anonymized Governance Concerns

The public application and discussion record raised the following substantive
questions without retaining reviewer identities:

- whether general-purpose hardware can provide an adequate threat model compared
  with specialist hardware wallets;
- how private keys are protected when a selected board lacks a secure element;
- whether supporting more transparent secure chips would be more valuable than
  broad device compatibility;
- whether users can safely verify and flash firmware;
- dependence on third-party wallet interfaces and future compatibility changes;
- whether project capacity is sufficient while the principal work is not
  presented as full time;
- how an open-source project would sustain maintenance and optional commercial
  activity;
- how milestones would be demonstrated and accepted before later funding stages.

## Applicant Responses Captured in the Public Record

The applicant described a plan to support multiple chips and optional secure
elements rather than bind the project to one vendor. The response proposed
documenting low, medium and high security tiers, supporting publicly usable
security components where possible, and allowing users to select stronger and
more expensive hardware when needed.

The applicant acknowledged risks in firmware flashing and recommended an
isolated environment for high-security use. The project intended to improve the
flashing experience, follow interface changes when necessary, keep the core open
source, and consider development-kit sales or third-party commercial partners as
future sustainability mechanisms.

For milestone review, the discussion described a quarterly product-experience
check before later releases. This is a proposed acceptance process; no acceptance
or unlock event is established by this evidence.

## Evidence Limits

- Security and compatibility claims require independent technical verification.
- Usage, board-support, test and contributor claims remain source-reported.
- The proposal's initial-unlock wording is not proof that funds moved.
- No actual disbursement, milestone acceptance, unlock, delivery report or impact
  outcome is present in this sanitized evidence.
