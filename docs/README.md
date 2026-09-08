# NOVA documentation

Document set for the NOVA project. Authored in Markdown, versioned in git, reviewed through pull
requests. Distributable DOCX and PDF are generated from these sources.

## Documents

| ID | Document | Standard followed | Status |
|---|---|---|---|
| NOVA-VS-001 | [Vision and Scope](vision-and-scope.md) | Wiegers vision and scope template | Draft |
| NOVA-SRS-001 | [Software Requirements Specification](srs.md) | ISO/IEC/IEEE 29148:2018 | Draft |
| NOVA-SAD-001 | [Software Architecture Document](architecture.md) | arc42 v9, C4 model, ISO/IEC/IEEE 42010 | Draft |
| NOVA-STP-001 | [Software Test Plan](test-plan.md) | ISO/IEC/IEEE 29119-3:2021 | Draft |
| NOVA-TM-001 | [Threat Model](threat-model.md) | STRIDE, OWASP ASVS references | Draft |
| NOVA-SDP-001 | [Software Development Plan](sdp.md) | ISO/IEC/IEEE 16326:2019 | Draft |
| NOVA-RR-001 | [Risk Register](risk-register.md) | ISO 31000 risk register practice | Draft |
| NOVA-DL-001 | [Decision Log](decision-log.md) | Project decision log | Draft |
| | [Architecture Decision Records](adr/) | MADR 4.0 | Various |
| | [Spikes](spikes/) | Project convention | Various |

## Reading order

New reader with limited time: [Vision and Scope](vision-and-scope.md), then
[section 1 of the SAD](architecture.md#1-introduction-and-goals), then the
[model selection spike](spikes/2026-09-07-model-selection.md).

Evaluating the engineering: [SAD](architecture.md) sections 4, 8, and 9, then the
[Test Plan](test-plan.md) section 5, then the [ADRs](adr/).

## Document control

Every document carries a control block: document ID, version, status, owner, and date, followed by
a revision history at the end.

Status values, one word, in lifecycle order:

| Status | Meaning |
|---|---|
| `Draft` | Being written. Content may change without notice |
| `Review` | Complete and awaiting review |
| `Approved` | Reviewed and accepted. Changes require a version bump |
| `Active` | Approved and describing the system as built |
| `Superseded` | Replaced by a later document, retained for history |

Versions follow `MAJOR.MINOR`. Minor for edits within a status, major on approval.

## Building DOCX and PDF

Sources are Markdown. Deliverables are generated with [Pandoc](https://pandoc.org) into
[`dist/`](dist/).

```powershell
powershell -File tools/build-docs.ps1
```

Requires Pandoc. PDF export additionally requires Microsoft Word, which the script drives through
COM automation. Run with `-Format docx` to skip PDF.

## Conventions

- Diagrams are [Mermaid](https://mermaid.js.org) fenced blocks, which GitHub renders natively. C4
  levels 1 and 2 (context and container) are used for structural views
- Requirement identifiers are stable: `FR-n` functional, `NFR-n` non-functional, `CON-n` constraint,
  `ASM-n` assumption
- Architecture decisions use [MADR 4.0](https://adr.github.io/madr/) and are numbered sequentially
  from `0001`. Superseded ADRs are never deleted
- Measured values are stated with the method and sample size. Unmeasured values appear as bracketed
  placeholders and are removed rather than softened if they cannot be filled
