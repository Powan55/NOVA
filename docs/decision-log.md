# Decision Log

| Field | Value |
|---|---|
| Document ID | NOVA-DL-001 |
| Version | 0.3 |
| Status | Draft |
| Owner | Laxmi Poudel |
| Date | 2026-09-08 |

---

## 1. Purpose

This log records project and technical decisions that do not warrant a full Architecture Decision
Record. Architecturally significant decisions are recorded as ADRs in [`adr/`](adr/) using MADR 4.0
and are indexed in section 6 below.

A decision log that is not maintained is worse than none, because it misrepresents the current state
of the project.

## 2. Status values

| Status | Meaning |
|---|---|
| `Accepted` | Decided. Change requires a superseding entry |
| `Provisional` | Decided on limited evidence. Confirmation pending |
| `Open` | Awaiting measurement, with a stated trigger |
| `Superseded` | Replaced. Retained for history |

## 3. Product and scope decisions

| ID | Decision | Status | Rejected alternatives | Rationale | Accepted cost | Revisit trigger |
|---|---|---|---|---|---|---|
| DL-001 | Primary workflow is requirement to structured test plan | Accepted | Defect report structuring; diagnostic plan generation | The only candidate whose output is objectively gradeable, which the central claim requires. Feasible within the inference constraint. Dense feedback signal from ordinary use | The problem space is crowded, so differentiation must come from the feedback loop rather than the generation | The model spike demonstrating that schema conformance is unattainable |
| DL-002 | Local-first inference with a pluggable hosted provider | Accepted | Local only; hosted primary | Confidentiality position, zero marginal cost, and a materially harder engineering problem. The abstraction preserves a demonstration fallback | A lower output quality ceiling | Hardware proving inadequate |
| DL-003 | Local deployment only, container composition as the artifact | Accepted | Hosted demonstration instance | A recorded demonstration substitutes at lower cost | No publicly reachable instance | A publicly reachable instance becoming worthwhile |
| DL-004 | Synthetic and open-source data only | Accepted | Authentic work artifacts; mixed | The repository becomes publishable, and privacy controls become designed and tested rather than compliance-bound | Less realistic inputs | Authentic data entering the system, at which point PII detection becomes a requirement |
| DL-005 | Single user with a multi-tenant-capable schema, authentication deferred | Accepted | Full authentication; no tenancy model | Maximum isolation-testing value per hour invested. Authentication changes the resolution point, not the data model | No authentication capability to demonstrate | Post-release |
| DL-006 | Model fine-tuning deferred rather than excluded | Accepted | Permanent exclusion; inclusion in the initial release | The initial release produces the labelled dataset and the baseline that a fine-tune requires. Training first would be unmeasurable | Requires present-tense discipline in all material until a trained model exists | Sufficient dataset volume and a measured baseline both present |
| DL-007 | Effort weighted unevenly across capability areas | Accepted | Even distribution | Even distribution yields uniformly shallow work in every area | The user interface will not be visually distinguished | Narrowing to a single capability area |
| DL-008 | Four playbooks | Accepted | Two; three | Sufficient spread for selection to visibly matter, and it stratifies the evaluation dataset naturally | Four prompt fragments and four dataset strata to maintain | Effort pressure triggering the scope reduction order |
| DL-009 | Scope reduction order committed in advance | Accepted | Deciding under pressure | Decisions taken calmly are better than decisions taken in the tenth week | A capability may be removed that is later regretted | None |

## 4. Technical decisions

| ID | Decision | Status | Rejected alternatives | Rationale | Accepted cost | Revisit trigger |
|---|---|---|---|---|---|---|
| DL-010 | Three-operation inference gateway interface | Accepted | A general inference abstraction layer | Structured generation, text generation, and embedding cover every requirement. Anything wider is speculative | Provider-specific capabilities are unreachable | A concrete requirement arising |
| DL-011 | Client-rendered single-page application | Accepted | Server-side rendering framework; server-rendered templates with progressive enhancement | Server-side rendering yields nothing for a local single-user application. Query caching addresses the one non-trivial client concern, which is polling a running task | No server-side rendering | Hosted deployment |
| DL-012 | Outcome scores derived from the event log, never authoritative | Accepted | Storing scores as the record of truth | Recoverable following poisoning, corruption, or a change to the weighting scheme | Recomputation cost | None |
| DL-013 | Bounded exploration over a fixed action set | Accepted | Pure exploitation; upper-confidence-bound or Thompson sampling; static mapping | The simplest mechanism that is real, scoreable, and explainable | A modest mechanism. It is not reinforcement learning and is not described as such | The action set growing materially |
| DL-014 | Content-free logging by default | Accepted | Logging prompts for diagnostic value | The confidentiality position cannot be undermined through logs | More difficult diagnosis, offset by an explicit debug mode | None |
| DL-015 | RFC 9457 problem-detail error representation | Accepted | Ad hoc error shapes | One representation for every failure, and one rendering component | Slightly verbose | None |
| DL-016 | Cursor-based pagination | Accepted | Offset pagination | Correct behaviour on append-heavy relations | Opaque cursors | None |
| DL-017 | Deterministic checks first, model-based review confined to the residual | Accepted | Model-based evaluation as the primary mechanism | Avoids making every metric dependent on a component whose reliability must itself be established | Misses nuance that a model-based judge would detect | Deterministic checks proving insufficient |
| DL-018 | Correction Recurrence Rate as the primary metric | Accepted | Acceptance rate; evaluation pass rate | Directly falsifies the central claim and requires no model-based judge | Sensitive to a threshold choice, which must be stated wherever the metric is quoted | The threshold proving indefensible |
| DL-019 | Fake inference provider for integration testing | Accepted | Real models throughout | Integration tests must be fast and deterministic. Model behaviour belongs to the evaluation sub-process | Integration tests cannot detect model-specific defects | None |
| DL-020 | Evaluation thresholds derived from measured variance | Accepted | Thresholds set from intent | An unstable gate is disabled in practice, and a disabled gate is worse than none | Thresholds cannot be set until the harness exists and variance is measured | None |
| DL-030 | The inference runtime stays bound to loopback; containers reach it through Docker Desktop's host proxy | Accepted | Widening `OLLAMA_HOST` to `0.0.0.0` with the port firewalled to the Docker subnet; containerizing inference with GPU passthrough | Measured working on the default binding, so the alternative buys nothing and costs an unauthenticated inference API behind one firewall rule | The deployment is Docker Desktop-specific. A Linux-native engine has no host proxy and needs the widened binding | Deploying on a container runtime without a host proxy |

## 5. Decisions pending measurement

| ID | Decision | Status | Evidence to date | Next action |
|---|---|---|---|---|
| DL-021 | Hardware provides 6 GB VRAM, not 8 GB or greater | Accepted, corrected by measurement | RTX 4050 Laptop, 6141 MiB, measured 2026-09-07 | Planning had recorded 8 GB or greater. The candidate model list was revised throughout the document set |
| DL-022 | Model class fixed at 4B parameters rather than 8 to 9B | Accepted | Five candidates over twenty requirements. The 4B class is 2.9 to 3.9 GB and fully GPU-offloaded; both 8B candidates need 6.6 GB, run about a third on the CPU, and are 2.4 times slower for no quality gain | Settled by the full run on 2026-09-08 |
| DL-023 | Specific model and quantization | Accepted | `gemma3:4b` at its default quantization. Leads content quality at 0.988 AC coverage and 0.988 required case types over twenty requirements, no hallucinated criterion references, smallest footprint at 2.9 GB | Chosen over a 7 s median latency advantage elsewhere, because the faster candidates each carry a coverage or accuracy deficit |
| DL-024 | Single-stage constrained generation rather than reason-then-structure | Accepted | 100 of 100 valid on first attempt at single stage, across five models and twenty requirements | The complete run showed no structural weakness to justify a second inference call |
| DL-025 | Thinking disabled on hybrid reasoning models | Accepted | Required for one candidate family. Reasoning tokens dominate generation duration and interact poorly with constrained decoding | A configuration requirement, not an optimization |
| DL-026 | Embedding model and vector dimension | Accepted | `embeddinggemma` at 768 dimensions. Five candidates measured against 71 hand-labelled pairs: first on every discriminating metric, 77 ms warm, 681 MB resident, co-resident with the generation model inside 6 GB | Decided in [ADR-0005](adr/0005-select-an-embedding-model-and-vector-dimension.md) on the evidence in NOVA-SPK-002. Revisit when authentic corrections exist in volume |
| DL-027 | Whether the 8B class fits within the VRAM budget | Accepted | It does not. Both candidates load at 6.6 GB against 6141 MiB, running 36% and 38% on the CPU, at 40 to 44 s median against 17.3 s | R-08 closed on the measurement. Revisit only on different hardware |
| DL-028 | Duplicate similarity and structural similarity thresholds | Open | None | Derive from measured distributions, then fix |
| DL-029 | Always-apply memories are held outside the vector index rather than retrieved by similarity | Provisional | A rule labelled relevant to all twenty requirements was ranked 6th to 8th by every one of five candidates, for every requirement. It accounts for the entire gap between recall@5 of 0.701 and scoped recall of 0.967 | A content-free rule gives semantic ranking nothing to match on. Settle the memory entity's treatment of scope before the M3 schema |

## 6. Architecture Decision Records

| ADR | Decision | Status |
|---|---|---|
| [0001](adr/0001-use-postgres-with-pgvector-as-sole-datastore.md) | PostgreSQL with pgvector as the sole datastore | Accepted |
| [0002](adr/0002-use-a-postgres-job-table-for-async-execution.md) | Job table and polling worker rather than a message broker | Accepted |
| [0003](adr/0003-do-not-use-an-agent-framework.md) | No agent framework | Accepted |
| [0004](adr/0004-require-human-confirmation-for-memory-writes.md) | Mandatory human confirmation for memory writes | Accepted |
| [0005](adr/0005-select-an-embedding-model-and-vector-dimension.md) | Embedding model and vector dimension | Proposed |

## 7. Traceability

### 7.1 User need to verification

| Need | Requirements | Components | Verification |
|---|---|---|---|
| UN-1 Retain conventions across sessions | FR-5, FR-6, FR-4 | Feedback processor, memory store, retriever | Correction Recurrence Rate; extraction precision measurement |
| UN-2 Output in the team's format | FR-2, FR-4 | Generator | Structured output validity; schema conformance tests |
| UN-3 Determine whether it is improving | FR-9, FR-10 | Evaluation harness | Correction Recurrence Rate; evaluation pass rate; regression rate |
| UN-4 Understand why an output was produced | FR-8 | Orchestrator, observability | Trace completeness; trace correlation tests |
| UN-5 Complete negative and authorization coverage | FR-2, FR-3 | Selector, generator, reviewer | Acceptance criteria coverage; required case type presence |
| UN-6 Avoid third-party transmission | FR-11 | Inference gateway | Provider contract suite; explicit switch test |
| UN-7 Correct or remove a poor rule | FR-7, FR-6.5 | Memory store, feedback processor | Deletion completeness; conflict detection tests |

### 7.2 Threat to verification

| Threat | Mitigation | Verification |
|---|---|---|
| T3 Persistent injection through memory | Validation screen, human confirmation, absence of tool surface | Adversarial scenarios targeting extraction and confirmation |
| T10 Cross-tenant disclosure | Data-layer scoping, server-side tenant resolution | Isolation suite as an unconditional gate |
| T5 Feedback poisoning | Bounded updates, clamping, minimum observations, derived scores | Poisoning scenarios; score recomputation test |
| T19 Elevation through injected instruction | No tool surface | Architecture inspection; adversarial suite |

---

## Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-09-08 | Laxmi Poudel | Initial draft |
| 0.2 | 2026-09-08 | Laxmi Poudel | DL-026 accepted. DL-029 added: always-apply memories held outside the vector index |
| 0.3 | 2026-09-08 | Laxmi Poudel | DL-022, DL-023, DL-024 and DL-027 accepted on the full model run |
| 0.4 | 2026-09-09 | Laxmi Poudel | DL-030 added and accepted on the evidence in NOVA-SPK-003 |
