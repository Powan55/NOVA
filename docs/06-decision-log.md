# Decision log

Updated 2026-09-07.

Status values: **Accepted**, **Provisional** (evidence exists but it's thin), **Open** (waiting on
measurement, with a named trigger).

A decision log that stops getting updated is worse than none, because it misrepresents where the
project actually is.

## Product and scope

| ID | Decision | Status | Rejected | Why | Cost | Revisit when |
|---|---|---|---|---|---|---|
| D-001 | Workflow: requirement to structured test plan | Accepted | Bug-report structuring, debug-plan generation | Only option with objectively gradeable output, which the whole thesis needs. Feasible on small local models. Dense feedback signal | Crowded space, so differentiation has to come from the loop, not the generation | The model spike shows the schema can't be held |
| D-002 | Local-first inference, pluggable cloud | Accepted | Local only, cloud primary | Privacy story, zero marginal cost, and a harder engineering problem. The abstraction keeps a demo fallback | Output quality ceiling | Hardware proves inadequate |
| D-003 | Local deployment, Compose as the artifact | Accepted | Cloud-hosted demo | Recorded demo covers it | No live URL, less infrastructure surface | A live URL becomes worth it |
| D-004 | Synthetic and open-source data only | Accepted | Real work artifacts, mixed | Repo is publishable, and PII controls become designed-and-tested rather than compliance-bound | Less realistic inputs | Real data enters, at which point PII detection becomes a requirement |
| D-005 | Single user, tenant-ready schema, auth later | Accepted | Full auth, no tenancy | Most isolation-testing signal per hour. Auth changes the resolution point, not the data model | No real auth to demo | Post-MVP |
| D-006 | Fine-tuning later, not never | Accepted | Hard non-goal, or include it now | The MVP is the data-collection and baseline phase a fine-tune needs. Doing it first would be unmeasurable | Have to keep saying "does not fine-tune" in present tense until it exists | Dataset volume and a measured baseline both exist |
| D-007 | Uneven effort across the four role targets | Accepted | Even split | Even effort makes all four shallow | Frontend won't be visually impressive | I narrow to one role |
| D-008 | Four playbooks | Accepted | Two or three | Enough spread for selection to visibly matter, and it stratifies the dataset naturally | Four prompt fragments and four dataset strata to maintain | Hour pressure triggers the cut order |
| D-009 | Cut order decided up front | Accepted | Decide under pressure later | Decisions made calmly beat decisions made in week 10 | Might cut something I later regret | |

## Architecture

| ID | Decision | Status | Rejected | Why | Cost | Revisit when |
|---|---|---|---|---|---|---|
| D-010 | Postgres + pgvector as the only datastore | Accepted | Qdrant, Chroma, Pinecone, or SQLite plus brute-force scan | Transactional consistency between a memory row and its embedding is a correctness property, not a convenience. pgvector's ceiling is orders of magnitude above this scale | Not the fastest vector search at large scale | Past ~1M vectors |
| D-011 | Postgres job table with a polling worker | Accepted | Celery + Redis, FastAPI background tasks | Durable, observable, transactional with the task record, zero extra infrastructure | No fan-out or scheduling | Multi-worker or scheduled evaluations needed |
| D-012 | No agent framework | Accepted | LangChain, LlamaIndex, CrewAI | The orchestration layer is the thing being shown. A framework means showing configuration instead | More code by hand | |
| D-013 | Three-method provider interface | Accepted | A general LLM abstraction layer | `generate_structured`, `generate_text`, `embed` covers everything. Wider is speculative | Provider-specific features unreachable | A real need shows up |
| D-014 | Vite + React + TypeScript SPA | Accepted | Next.js, server-rendered templates with HTMX | SSR buys nothing for a local single-user app. Query caching solves the one genuinely non-trivial frontend problem, which is polling a running task | No SSR | Cloud deployment |
| D-015 | Human confirmation on every memory write | Accepted | Auto-promote above a confidence threshold | Memory is a persistent injection vector. Two imperfect controls in series | Feels less automatic | Confirmation data shows a defensible threshold |
| D-016 | Outcome scores derived, never authoritative | Accepted | Store scores as truth | Recoverable after poisoning, corruption, or a weighting change | Recomputation cost | |
| D-017 | Bounded exploration over a fixed playbook set | Accepted | Pure greedy, UCB or Thompson sampling, static mapping | Simplest mechanism that's real, scoreable, and explainable | Modest. It isn't reinforcement learning and I won't call it that | Action space grows |
| D-018 | The agent has no tool surface | Accepted | A tool-using agent | Strongest injection mitigation available, and it's architectural rather than a filter | Less capable agent | Any tool addition invalidates the security model and forces a rewrite of that doc |
| D-019 | Content-free logging by default | Accepted | Log prompts for debuggability | The privacy story can't leak through logs | Harder debugging, offset by an opt-in debug mode | |
| D-020 | RFC 9457 problem-details errors | Accepted | Ad-hoc error shapes | One shape, one frontend component | Slightly verbose | |
| D-021 | Cursor pagination | Accepted | Offset | Correct for append-heavy tables | Opaque cursors | |

## Quality and evaluation

| ID | Decision | Status | Rejected | Why | Cost |
|---|---|---|---|---|---|
| D-022 | Deterministic checks first, LLM judge for the residual | Accepted | LLM-judge-first | Avoids making every metric depend on a component whose reliability I'd then have to prove | Misses nuance |
| D-023 | Correction recurrence rate as the headline metric | Accepted | Acceptance rate, evaluation pass rate | Directly falsifies the thesis, and needs no LLM judge | Threshold-sensitive, which has to be stated wherever it's quoted |
| D-024 | Fake provider for integration tests, real models only in evaluation | Accepted | Real models throughout | Integration tests have to be fast and deterministic. Model behaviour is the evaluation layer's job | Integration tests can't catch model-specific bugs |
| D-025 | Evaluation thresholds from measured variance | Accepted | Set from aspiration | A gate that flaps gets ignored, and an ignored gate is worse than none | Can't set thresholds until the harness exists and variance is measured |

## Measured, or waiting on measurement

| ID | Decision | Status | Evidence | Next |
|---|---|---|---|---|
| D-026 | Hardware is 6 GB VRAM, not 8 GB+ | Accepted, corrected by measurement | RTX 4050 Laptop, 6141 MiB, measured 2026-09-07 | Planning had 8 GB+ written down. Candidate list rewritten |
| D-027 | 4B model class rather than 8 to 9B | Provisional | 3 candidates measured, 12 of 12 schema-valid, 2.9 to 3.9 GB resident, 100% GPU, 9 to 26 s warm | Finish the run across all 20 requirements and all 5 candidates before this is settled |
| D-028 | Specific model and quantization | Open | `gemma3:4b` leads on content quality at n=4, `phi4-mini` on latency, `qwen3:4b` weakest on coverage | n=4 can't separate them. Decide after the full run |
| D-029 | Single-stage constrained generation | Provisional | Validity was 100% single-stage across every measured model | Only revisit if content quality is weak on the full run. Two-stage costs a second call and latency |
| D-030 | Thinking disabled on hybrid reasoning models | Accepted | Required for `qwen3`. Thinking tokens dominate latency and interact badly with constrained decoding | Config detail, not an optimization |
| D-031 | Embedding model and dimension | Open, blocking | None | Sticky. The dimension goes into the schema, and changing it later forces a re-embedding migration. Needs its own spike before schema work |
| D-032 | Does 8B fit on 6 GB at all? | Open | Both candidates pulled, neither measured | Measure residency and offload split |
| D-033 | Duplicate and structural similarity thresholds | Open | None | Set from measured distributions, then freeze |

## Still to settle

| ID | Question | Blocking? | Going with |
|---|---|---|---|
| D-034 | Publish the repo early, or only when polished? | No | Early. Commit history showing steady work is itself evidence, and a repo that appears fully formed in one commit looks worse |
| D-035 | Expand the name NOVA? | No | Leave it alone |
| D-036 | Test case schema fixed or configurable? | Blocks schema freeze | Fixed v1, format preferences through memory |
| D-037 | Golden dataset sourcing | Blocks dataset work | Hybrid, ~30 hand-written and ~20 derived |

## Traceability

| Pain point | Requirements | Components | Verified by |
|---|---|---|---|
| Re-explaining conventions | FR-4, FR-5, FR-6 | Feedback processor, memory store, retriever | Correction recurrence rate, extraction precision |
| Hand-reformatting | FR-2, FR-6 | Generator | Structured-output validity, schema conformance tests |
| Can't tell if it's improving | FR-9, FR-10, FR-13 | Evaluation harness | Recurrence rate, pass rate, regression rate |
| Can't see why | FR-3 | Orchestrator, observability | Trace completeness, trace-id propagation tests |
| Missing negative/boundary/auth cases | FR-2, FR-12 | Selector, generator, critic | AC coverage, required case-type presence |
| Can't send data to a cloud API | FR-11 | LLM gateway | Provider contract tests, explicit-switch test |
| Bad memory poisons output | FR-7, FR-8 | Memory store, feedback processor | Deletion completeness, conflict tests |

| Threat | Mitigated by | Verified by |
|---|---|---|
| Persistent injection via memory | Validation checks, human gate, no tool surface | Injection-into-memory scenarios |
| Cross-tenant leakage | Repository-layer scoping, server-side tenant resolution | Isolation tests as an unconditional CI gate |
| Feedback poisoning | Bounded updates, clamping, minimum observations, derived scores | Poisoning scenarios, score recomputation test |
