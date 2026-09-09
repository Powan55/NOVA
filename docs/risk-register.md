# Risk Register

| Field | Value |
|---|---|
| Document ID | NOVA-RR-001 |
| Version | 0.3 |
| Status | Draft |
| Owner | Laxmi Poudel |
| Date | 2026-09-08 |
| Review cadence | Milestone boundaries |

---

## 1. Method

Risks are assessed on likelihood and impact, with impact measured against the project's central
claim rather than against schedule alone. A risk that delays delivery is less severe than one that
undermines the evidence for the claim.

| Likelihood | Definition |
|---|---|
| High | More likely than not on current evidence |
| Medium | Plausible, with no evidence either way |
| Low | Contradicted by evidence or by design, but not eliminated |

| Impact | Definition |
|---|---|
| Critical | The central claim cannot be evidenced, or data is disclosed |
| High | A primary capability is lost or substantially degraded |
| Medium | Rework, or a metric loses meaning |
| Low | Inconvenience, or a secondary capability is affected |

Response strategies follow ISO 31000: **avoid**, **reduce**, **transfer**, **accept**.

A risk closes only when evidence closes it. A planned mitigation does not close a risk, and neither
does elapsed time. A closed risk keeps the identifier it was tracked under and moves to section 3;
the `R-Cn` identifiers belong to risks that were identified and closed without ever being active.

## 2. Active risks

| ID | Risk | L | I | Response | Mitigation | Trigger or indicator | Milestone |
|---|---|---|---|---|---|---|---|
| R-01 | Correction extraction does not reach usable precision on a 4B-parameter model. Candidates prove overbroad, trivial, or incorrect often enough that confirmation becomes an obstacle rather than a safeguard | High | High | Reduce | Precision measured against approximately 15 hand-labelled authentic corrections at a defined checkpoint, before dependent interface work. Fallback is user-authored rules with model assistance | Precision below a usable threshold at the M3 checkpoint | M3 |
| R-02 | Evaluation dataset construction is underestimated. Approximately 50 stratified cases with precisely stated expected properties represents 15 to 25 hours of authoring on the critical path | High | High | Reduce | Authoring begins two milestones early. Twenty cases already exist from the model selection spike and transfer directly, removing approximately one third of the effort | Fewer than 30 cases authored by the start of M5 | M5 |
| R-03 | Inference nondeterminism exceeds gate margins and the regression gate becomes unstable. An unstable gate is disabled in practice, and a disabled gate is worse than none because it presents as protection | High | High | Reduce | Run-over-run variance measured before any threshold is set. Where variance is excessive, the dataset is enlarged rather than thresholds loosened | Identical inputs producing divergent gate verdicts across runs | M5 |
| R-05 | The Correction Recurrence Rate depends on a structural similarity threshold that is difficult to defend, and the primary metric is only as sound as that choice | Medium | High | Reduce | Threshold derived from measured distributions, documented, held constant across runs, and always reported alongside retrieval precision so that a memory retrieved and disregarded is distinguishable from one never retrieved | The metric moving materially under small threshold perturbation | M5 |
| R-06 | Available effort falls to the lower bound and the plan exceeds budget | Medium | Medium | Accept | Scope reduction order pre-committed. Decision point at week 6, not week 12 | Cumulative hours tracking below plan at week 6 | Week 6 |
| R-07 | Provisional values are replaced with optimistic figures under presentation pressure | Medium | Critical | Avoid | Claim discipline recorded in NOVA-SDP-001 §7.6 and reviewed at the start of the final milestone rather than at its end. A placeholder that cannot be filled becomes a removed claim | Any figure appearing without a stated method, sample size, and reference configuration | M7 |
| R-09 | Container-to-host inference reachability is unverified on this platform, and is the most probable early impediment. Anyone reproducing the deployment encounters it | Medium | Medium | Reduce | Half a day allocated. Resolution documented in the repository README | Container unable to reach the host inference endpoint | M1 |
| R-10 | Output quality on a local model does not reach the acceptance rate target | Medium | Medium | Accept | Target revised openly. Targets are provisional and revision is expected, but is recorded rather than applied silently | Measured acceptance rate materially below target across authentic usage | M5 |
| R-11 | Persistent injection defences are unproven. The threat is sufficiently novel that the adversarial suite constitutes the only evidence | Medium | High | Reduce | The suite establishes a floor, not a guarantee, and is described as such. The absence of a tool surface carries the substantive protection | Any adversarial scenario reaching stored memory | M5 |
| R-12 | Deterministic checks do not capture sufficient quality signal to gate on. Both acceptance criteria coverage and required case type presence rely on the model's own labelling | Medium | Medium | Reduce | A sample of plans is manually audited and the agreement rate reported. Where the checks prove weak, the share of model-based review increases and the caveat is documented | Manual audit disagreeing materially with automated verdicts | M5 |
| R-13 | The model review stage does not justify its latency cost, having added a second inference call to every task | Low | Low | Reduce | Designed to be removable. Measured before and after against the dataset, and removed where it does not demonstrably help | No measurable quality difference with the stage disabled | M5 |
| R-14 | Exploratory selections present as unexplained degradation to a user unaware that exploration occurred | Low | Low | Reduce | Exploration labelled explicitly in the interface | User report of inconsistent quality without apparent cause | M4 |
| R-15 | Entity count is high relative to the effort budget. Several entities are thin, but each still requires a migration, a data access implementation, and tests | Low | Medium | Accept | Estimated explicitly rather than assumed cost-free | Persistence work exceeding estimate by a material margin | M2, M3 |
| R-16 | Introducing any tool capability invalidates the threat model. The absence of a tool surface is load-bearing for the entire security position | Low | High | Avoid | Recorded so the consequence is not overlooked. Such a change requires rewriting NOVA-TM-001, not amending it | Any proposal introducing file, command, or network capability for the model | Future |
| R-17 | No independent code review. Every design and security decision has a single reviewer | Low | Medium | Accept | Automated gates substitute where they can. The limitation is stated in the document set rather than concealed | Not applicable. A standing condition | Throughout |
| R-18 | Endpoint protection software on the development workstation holds GPU memory, reducing available VRAM below nominal | Low | Low | Accept | Recorded so that measurements taken on this host remain interpretable elsewhere | Not applicable. A standing condition | Throughout |

## 3. Closed risks

| ID | Risk | Closure |
|---|---|---|
| R-C1 | Available hardware cannot sustain a local model at acceptable latency and schema fidelity. This was the risk capable of invalidating the primary workflow decision | **Closed by measurement, 2026-09-07.** 4B-parameter class: 12 of 12 schema-conformant on first attempt, 2.9 to 3.9 GB resident, fully GPU-offloaded, 9 to 26 s warm generation. Substantially inside the provisional latency target |
| R-C2 | The recorded hardware assumption of 8 GB or greater VRAM was incorrect | **Closed, 2026-09-07.** The device provides 6 GB. Identified before any implementation, at a cost of one afternoon rather than a rewrite in the ninth week. The candidate model list was revised and the constraint corrected throughout the document set |
| R-04 | The embedding model and vector dimension remained unselected, and the dimension is fixed at schema creation | **Closed by measurement, 2026-09-08.** `embeddinggemma` at 768 dimensions, selected in [ADR-0005](adr/0005-select-an-embedding-model-and-vector-dimension.md) on the evidence in NOVA-SPK-002. Five candidates measured against 71 hand-labelled requirement-to-rule pairs. Schema definition is unblocked |
| R-08 | The 8B parameter class might not fit the 6 GB budget, and was unmeasured | **Closed by measurement, 2026-09-08.** It does not fit. Both candidates load at 6.6 GB and run 36% to 38% on the CPU, at 40 to 44 s median against 17.3 s for `gemma3:4b`, with no quality gain. The 4B class is confirmed rather than merely assumed |

## 4. Prerequisites

Two entries are prerequisites rather than ordinary risks. Dependent work does not commence until
they are resolved, because proceeding while wrong incurs rework rather than delay. They are retained
here once resolved so that the sequencing remains legible.

| ID | Prerequisite | Blocks | State |
|---|---|---|---|
| R-04 | Embedding model and vector dimension selected | Schema definition, and therefore all persistence work | Resolved 2026-09-08. Closed as R-C3 |
| R-01 | Extraction precision measured | Memory management interface and applied-lessons presentation | Outstanding |

---

## Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-09-08 | Laxmi Poudel | Initial draft |
| 0.2 | 2026-09-08 | Laxmi Poudel | R-04 closed by measurement as R-C3 |
| 0.3 | 2026-09-08 | Laxmi Poudel | R-08 closed by measurement as R-C4 |
