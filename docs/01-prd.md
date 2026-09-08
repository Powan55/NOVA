# Requirements

| | |
|---|---|
| Status | Planning |
| Updated | 2026-09-07 |

## Problem

Covered in the [project brief](00-project-brief.md). Short version: LLMs generate test cases fine,
but they don't retain your team's conventions across sessions, so you pay a re-instruction tax on
every one. And no existing tool can show you whether it's improving.

## Personas

### Test engineer on a feature team (primary)

| | |
|---|---|
| Experience | 2 to 6 years, fluent in test design, comfortable with CLI and APIs |
| Volume | 5 to 15 requirements a sprint needing coverage |
| Tools today | Issue tracker, a test management tool, an LLM assistant used inconsistently |
| Conventions | Specific and strongly held: case format, mandatory case types, priority taxonomy, house terminology |
| Good outcome | Full coverage of the acceptance criteria, no missed negative or boundary cases, output already in house format |
| Bad outcome | Re-explaining conventions every session, or silently missing an edge case that ships as a bug |
| Attitude | Skeptical of AI output. Won't accept a black box |

### Developer owning their own coverage (deferred)

Documented only to justify one requirement: NOVA has to be useful with an empty memory store. Not
optimized for in the MVP.

## Pain points

| ID | Pain | Handled by |
|---|---|---|
| PP1 | Re-explaining conventions every session | FR-4, FR-5, FR-6 |
| PP2 | Hand-reformatting output to house style | FR-2, FR-6 |
| PP3 | No way to tell if it's improving | FR-9, FR-10 |
| PP4 | No way to see why it produced what it did | FR-3 |
| PP5 | Missing negative, boundary, and auth cases | FR-2, FR-12 |
| PP6 | Can't send proprietary requirements to a cloud API | FR-11 |
| PP7 | A bad past correction poisons output with no way to undo it | FR-7, FR-8 |

## Goals

Cut the re-instruction tax measurably. Make the improvement mechanism visible and reversible. Make
quality enforceable in CI rather than aspirational.

Non-goals are in the [project brief](00-project-brief.md#scope). The three tempting ones worth
repeating: generating runnable test code, multi-user auth, and repo/code ingestion are all out.

## Main journey

1. Paste a requirement (user story plus acceptance criteria), pick a requirement type.
2. NOVA acknowledges immediately, task goes to `running`, UI shows progress.
3. It retrieves relevant memories, picks a playbook, generates a schema-constrained plan, runs an
   evaluator pass, and stores the full trace.
4. UI shows the plan next to an "Applied lessons" panel listing each retrieved memory and its score.
5. You go case by case: accept, edit, reject. Optionally add a freeform correction.
6. NOVA proposes candidate memories from those corrections. You confirm or discard each one.
7. Next structurally similar requirement, the confirmed memories get retrieved and applied, and the
   panel shows them.

Step 7 is the point of the whole thing. Everything else exists to make it observable and measurable.

## Alternate and failure journeys

| ID | Situation | What should happen |
|---|---|---|
| AJ-1 | Cold start, no memories | Produce a usable plan from playbook defaults. Panel says "no prior lessons" instead of hiding the absence |
| AJ-2 | Model returns invalid JSON | Constrained decoding should prevent it. If it happens: bounded repair-retry, then fail with a readable error. Every attempt recorded |
| AJ-3 | Provider unavailable | Task marked `failed` with a clear cause. Never a silent hang. Existing results still accessible |
| AJ-4 | Conflicting memories retrieved | Surface the conflict instead of silently picking one |
| AJ-5 | Requirement contains a prompt injection | Requirement text is untrusted data. Attempt is neutralized and logged. Covered by the adversarial suite |
| AJ-6 | User rejects every case | Recorded as a strong negative outcome, feeds playbook scoring, prompts for a correction |
| AJ-7 | Retrieval finds nothing relevant | Proceed on defaults. Low scores get recorded, not hidden |
| AJ-8 | User deletes a memory that was being used | Deletion is immediate and complete. Old traces keep a tombstone reference, not the content |
| AJ-9 | Task runs past its latency budget | Stays cancellable, partial trace kept |
| AJ-10 | Contradictory feedback over time | Recency and confidence weighting. Older rule gets superseded, never silently averaged |

## User stories

| ID | Story | Priority |
|---|---|---|
| US-1 | Submit a requirement, get a structured test plan back, so I'm not starting from a blank page | Must |
| US-2 | See which prior lessons got applied, so I can judge whether to trust the output | Must |
| US-3 | Accept, edit, or reject individual cases, so feedback is specific rather than a blanket rating | Must |
| US-4 | Add a freeform correction for a rule the UI can't infer | Must |
| US-5 | See a correction applied on a later similar task without restating it | Must |
| US-6 | Browse, edit, and delete stored memories so a wrong lesson doesn't stick around | Must |
| US-7 | Inspect a full execution trace so I can debug a bad result | Must |
| US-8 | Run an evaluation suite and see pass rates and trends | Must |
| US-9 | Have CI block a prompt or config change that regresses the suite | Must |
| US-10 | Switch model provider, trading privacy for quality | Should |
| US-11 | Pin a memory as always-apply | Should |
| US-12 | See cost and latency per task | Should |
| US-13 | Export a plan to Markdown or CSV | Could |
| US-14 | Compare two runs of the same requirement side by side | Could |
| US-15 | Share memories across a team | Won't. Needs auth first |

## Functional requirements

| ID | Requirement | Priority | Serves |
|---|---|---|---|
| FR-1 | Accept a requirement with type and optional context, validate and store it | Must | US-1 |
| FR-2 | Generate a plan conforming to a versioned JSON schema via constrained decoding | Must | US-1, PP2, PP5 |
| FR-3 | Store a complete execution trace: playbook, retrieved memories with scores, model calls, tokens, latency, retries | Must | US-7, PP4 |
| FR-4 | Capture per-case accept/edit/reject plus optional freeform correction | Must | US-3, US-4 |
| FR-5 | Extract candidate memories from corrections, require explicit confirmation before storing | Must | US-4, PP1 |
| FR-6 | Retrieve memories by similarity, recency, and confidence, and show the scores | Must | US-2, US-5 |
| FR-7 | Memory browse, edit, delete, pin | Must | US-6, US-11, PP7 |
| FR-8 | Detect conflicting memories and surface them | Must | AJ-4, AJ-10 |
| FR-9 | Compute and store metrics per task and per evaluation run | Must | US-8, PP3 |
| FR-10 | Run an evaluation suite against a versioned golden dataset, report pass rates and trends | Must | US-8 |
| FR-11 | Pluggable model providers with a local default | Must | US-10, PP6 |
| FR-12 | Select among at least two playbooks using outcome scores with bounded exploration | Must | PP5 |
| FR-13 | Version prompts and config, promote only on evaluation pass | Must | US-9 |
| FR-14 | Scope every data access by `tenant_id` | Must | Isolation |
| FR-15 | Run tasks async with observable status | Must | AJ-9, C3 |
| FR-16 | Show cost and latency per task | Should | US-12 |
| FR-17 | Export a plan to Markdown and CSV | Could | US-13 |
| FR-18 | Side-by-side run comparison | Could | US-14 |

## Non-functional requirements

Targets are drafts until measured. Where something has been measured, it's noted.

| ID | Requirement | Draft target | Measured | Note |
|---|---|---|---|---|
| NFR-1 | Structured-output validity, first attempt | ≥98% | 12 of 12 | Sample far too small to call it a rate |
| NFR-2 | End-to-end task latency | p95 ≤90 s | Generation alone 9 to 26 s warm | Target has way too much slack. Tighten it once the full pipeline exists |
| NFR-3 | Retrieval latency | p95 ≤200 ms | | pgvector at this scale should be well under |
| NFR-4 | UI stays responsive during a running task | No blocking interaction | | Async-first |
| NFR-5 | Cross-tenant data leakage | Zero, enforced and tested | | Not negotiable |
| NFR-6 | Memory deletion completeness | Content gone, tombstone kept | | AJ-8 |
| NFR-7 | Startup | One command via Compose | | |
| NFR-8 | Trace completeness | Every model call and retrieval recorded | | Including on failed tasks |
| NFR-9 | Evaluation suite runtime | ≤15 min | | Has to be tolerable as a CI gate. Cold model load is a real contributor |
| NFR-10 | Core logic test coverage | ≥80% | | Memory, retrieval, scoring, validation. Excludes UI and glue |
| NFR-11 | Reproducibility | Fixed seed plus pinned model and prompt version reproduces a run | | Regression testing means nothing without it |

## MoSCoW

Must: FR-1 to FR-15, NFR-1 to NFR-11. Should: FR-16, US-11. Could: FR-17, FR-18. Won't: US-15,
multi-user auth, cloud deployment, code ingestion, runnable test generation, tool integrations.

## Acceptance criteria

Done when all of these work end to end.

| ID | Criterion |
|---|---|
| AC-1 | A requirement submitted through the UI returns a schema-valid plan |
| AC-2 | The trace viewer shows retrieved memories with scores, model calls, tokens, latency |
| AC-3 | A rejection plus a freeform correction produces a candidate memory I can confirm |
| AC-4 | A later similar requirement retrieves and applies that memory, visibly, with no restating |
| AC-5 | Memory browse, edit, delete, pin all work. Deletion stops future retrieval |
| AC-6 | Two conflicting memories get detected and surfaced, not silently resolved |
| AC-7 | The evaluation suite runs against the committed golden dataset and reports every metric |
| AC-8 | A deliberately worsened prompt gets blocked by the CI regression gate |
| AC-9 | Playbook selection shifts after recorded outcomes, and exploration stays inside its bound |
| AC-10 | Adversarial suite passes: injection, feedback poisoning, cross-tenant isolation |
| AC-11 | `docker compose up` gives a working system from a clean checkout |
| AC-12 | Provider swap between local and cloud works without code changes |
| AC-13 | Correction recurrence rate measured and reported across two or more runs, including any regression |

AC-8 is the one that matters most. A CI gate that actually blocks a bad change is the difference
between a real quality system and a decorative one.

## Success metrics

Four separate scoreboards. Mixing them is how portfolio projects end up claiming things they haven't
shown. Every number below is a draft target, not a result.

### Is it useful?

| Metric | Draft target | Note |
|---|---|---|
| Case acceptance rate, unedited | ≥60% | Measured on my own real usage |
| Time to usable plan vs writing by hand | ≥40% reduction | Needs a manual baseline. No baseline, no claim |
| Would I use it again | Yes/No | Subjective, and reported as subjective |

### Is it built properly?

| Gate | Target |
|---|---|
| Core logic test coverage | ≥80% |
| CI green on every merge to main | Required |
| Zero cross-tenant leakage | Required |
| Regression gate blocks a worsened prompt | Required (AC-8) |
| Clean `docker compose up` from a fresh clone | Required |
| An ADR for every significant decision | Required |

### Is the output good?

| Metric | Draft target | How it's collected |
|---|---|---|
| Structured-output validity | ≥98% | Automatic, every generation |
| Acceptance-criteria coverage | ≥90% | Deterministic, against parsed ACs |
| Required case-type presence | ≥85% | Deterministic, per playbook rules |
| Duplicate case rate | ≤10% | Embedding similarity within a plan |
| Correction recurrence rate | ≤20% | Headline metric, see below |
| Retrieval precision @5 | ≥70% | Against a hand-labelled relevance set |
| Evaluation pass rate | ≥85% | Golden dataset |

Correction recurrence rate:

```
CRR = corrections that reappear as errors on later structurally similar tasks
      ──────────────────────────────────────────────────────────────────────
      total distinct corrections previously given and confirmed
```

This is whether NOVA actually stops repeating mistakes. Directly observable, no LLM judge needed,
and it maps straight onto PP1. It's the thesis made falsifiable, so it gets reported honestly
including any run where it gets worse.

Two known weaknesses, and they go wherever the number goes. "Structurally similar" needs a
similarity threshold and the metric is sensitive to it, so the threshold gets fixed, documented, and
held constant or the number is meaningless. And it can't tell "memory retrieved and ignored" from
"memory never retrieved" without the trace, so it always gets reported next to retrieval precision.

### Does it land?

| Goal | Evidence |
|---|---|
| README explains the loop in under two minutes | One external reader |
| Architecture doc and five or more ADRs | Committed |
| Demo showing correction, later application, deletion, reversion | Recorded |
| Screenshots: trace viewer, memory manager, evaluation results, failing CI gate | Captured |
| Resume claims carry measured numbers | Every placeholder filled or the claim cut |

## Analytics

No telemetry, nothing leaves the machine. All measurement is local and inspectable.

| Signal | What it's for | Stored in |
|---|---|---|
| Task status transitions with timestamps | Success rate, latency | `tasks` |
| Per-case accept/edit/reject/add | Acceptance rate, outcome scoring, memory extraction | `feedback_events` |
| Freeform corrections | Memory extraction | `feedback_events` |
| Retrieval scores including non-selected candidates | Retrieval precision, debugging | `trace_steps` |
| Model call tokens, latency, attempts, validity | Validity rate, latency, cost proxy | `model_calls` |
| Playbook selection and exploration flag | Strategy layer behaviour | `tasks`, `trace_steps` |
| Evaluation run aggregates | Trends, gate verdicts | `eval_runs` |

Implicit signals (time to first action, abandonment, export) get collected but weighted well below
explicit feedback, and never on their own create or change a memory. Abandonment is ambiguous by
nature: someone might close the tab because the plan was bad, or because they got coffee. That's a
stated limit, not an oversight.

## Rollout

Local, single user. No staged rollout, no feature flags, no user migration. A release is a tagged
commit that starts cleanly from a fresh clone.

| Requirement | Detail |
|---|---|
| Install | `docker compose up` from a clean checkout, Ollama running on the host |
| First run | Health endpoint reports provider reachability. A missing model gives a message naming the pull command, not a generic error |
| Migrations | Alembic, forward-only. Embedding dimension is fixed at schema creation, so changing the embedding model needs a documented re-embedding migration |
| Rollback | Git revert plus a documented `pg_dump` restore, drilled at least once. An untested backup isn't a backup |
| Support | Just me. Issues in the repo |

## Risks

Full list in the [risk register](07-risk-register.md). The product-level ones:

- Corrections might not extract into reusable rules well enough, which drops the loop back to
  user-authored rules. Smaller feature, still honest.
- Local model quality might miss the 60% acceptance target, in which case the target gets revised
  openly.
- The recurrence-rate similarity threshold might not be defensible, in which case a weaker per-case
  regression metric replaces it.
- Scope might exceed the hour budget, which is why the cut order is decided up front.

## Open questions

| ID | Question | Blocking? | Going with |
|---|---|---|---|
| Q-04 | Test case schema fixed or user-configurable? | Blocks schema freeze | Fixed v1. Format preferences get expressed through memory |
| Q-05 | Memory confirmation mandatory, or auto-promote above a confidence threshold? | No | Mandatory. It's the control that mitigates persistent injection |
| Q-06 | Golden dataset hand-written, derived, or both? | Blocks dataset work | Both. Roughly 30 hand-written, 20 derived |
| Q-07 | Duplicate and structural similarity thresholds? | Blocks two metrics | Set from measured distributions, then freeze |
