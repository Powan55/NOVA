# Project brief

| | |
|---|---|
| Project | NOVA |
| Built by | Solo Software Engineer |
| Status | Planning. Docs and one spike done, no app code |
| Decisions | [Decision log](06-decision-log.md) |
| Updated | 2026-09-07 |

## Background

I'm a Software Engineer building a portfolio project that has to show real depth in four areas at
once: test engineering, AI/LLM work, backend, and full-stack. Budget is roughly 130 to 180 hours
over about three months at 10 to 15 hours a week.

The concept, a developer agent with persistent memory, is easy to state and easy to fake. The space
is full of LLM wrappers with a thumbs-up button and a README claiming the thing learns. The only way
this is worth building is if the improvement is measured, the learning mechanism is bounded, and
both are inspectable. That constraint drives most of what follows: the scope stays narrow so the
depth is achievable, and every claim gets tied to a metric with a formula and a known weakness.

## The problem

Writing test cases from a requirement is high-volume, low-variance work that engineers do constantly
and don't enjoy. LLM assistants can produce test cases, but they fail the same way every time: they
don't know how your team writes tests.

So you re-supply the same context every session. Use Given/When/Then. Always add an unauthenticated
case for any endpoint. Tag priority P0 to P3. Don't generate UI cases for a backend-only story. The
correction lands, gets applied once, and is gone. Next requirement, same correction.

The generation isn't the cost. Re-explaining yourself forever is.

The usual answer is a long system prompt or a style guide. That's brittle, unversioned, unmeasured,
and gets quietly ignored as it grows. It also can't answer the question that matters: is this
actually getting better, and how would you know?

## Who it's for

**Primary: a test engineer on a feature team.** Two to six years in, embedded in a product team,
responsible for coverage on a stream of incoming stories. Writes test cases from tickets weekly. Has
strong opinions about case format, mandatory case types, and priority taxonomy, built from
experience. Has already tried an LLM assistant for this and gave up because re-explaining conventions
cost more than writing the cases.

They're skeptical of AI output by professional instinct and won't accept a black box. That's why the
execution trace viewer is a requirement and not a nice-to-have.

**Secondary, deferred: a developer who owns their own coverage.** No dedicated QA, writes tests
because they have to. Lower conventions bar, higher volume. I'm keeping this persona documented for
one reason only: it forces NOVA to be useful with an empty memory store. Not optimizing for it
otherwise.

## What success looks like

This is a portfolio project, so success is demonstrated capability rather than revenue.

| Outcome | How you'd know |
|---|---|
| Improvement is measured, not claimed | Correction recurrence rate tracked across two or more runs on a fixed dataset, reported honestly including any regression |
| Quality is enforced, not aspirational | A deliberately worsened prompt gets blocked by a CI gate |
| The mechanism is visible, not just its output | Open a memory row live, show where it came from, delete it, watch the behaviour revert |
| I can defend every design decision | Every significant call has a written record with the alternatives |
| It's genuinely useful to me | Case acceptance rate measured on my own real usage |

## Scope

In:

- One workflow: requirement to structured test plan and test cases
- Persistent memory extracted from corrections, with a confirmation step before anything is stored
- Scored retrieval, with the scores shown in the UI
- Outcome-scored selection across four fixed playbooks, with bounded exploration
- Full execution traces and a viewer
- An evaluation harness: versioned golden dataset, deterministic checks, adversarial suite, CI
  regression gate
- Local-first inference behind a provider abstraction
- Local deployment via Docker Compose
- Single user, tenant-ready schema, isolation enforced and tested from the start

Out:

| Not doing | Note |
|---|---|
| Fine-tuning or training of any kind | Deferred, not ruled out. See below |
| Auth and multi-user login | Schema is ready for it, auth comes later |
| Cloud deployment or a public URL | A recorded demo covers this |
| Repo or code ingestion | Would improve output and make evaluation much harder |
| Generating runnable test code (Playwright, pytest) | Best post-MVP addition, and roughly doubles the scope |
| Issue tracker integrations | |
| Running tests, or hooking into anyone's CI | |
| Real-time collaboration, mobile UI | |
| Fully autonomous learning | Every memory write and config change has a human or evaluation gate |

## Constraints

| ID | Constraint | Where it comes from |
|---|---|---|
| C1 | ~130 to 180 hours total | My availability |
| C2 | Solo, no external code review | Reality of the project |
| C3 | Local inference by default, 6 GB VRAM ceiling | Hardware, measured 2026-09-07 |
| C4 | Local deployment only | My call |
| C5 | Synthetic and open-source data only | My call |
| C6 | No fine-tuning in the MVP | Scope boundary |

What those force:

- C3 makes structured-output reliability a real engineering problem rather than an assumption. A
  4B to 8B model is much weaker at instruction adherence than a frontier model.
- C3 also means latency is in seconds, not milliseconds. Measured 9 to 26 seconds warm. The UI has
  to be async-first or it'll feel broken.
- C1 means the evaluation dataset gets budgeted explicitly. It's 15 to 25 hours of real work and
  it's on the critical path.
- C5 means the dataset can be committed and reviewed, which is a plus.

## What "learning" means here

This term gets thrown around and destroys credibility when it's loose. Here's the boundary.

| Level | What it is | In the MVP? |
|---|---|---|
| L0 | Working memory. Context built for one task, then dropped | Yes |
| L1 | Episodic memory. Stored records of past tasks, outputs, outcomes | Yes |
| L2 | Semantic memory. Durable rules from corrections, with provenance and confidence | Yes |
| L3 | Retrieval. Picking relevant past memories by similarity, recency, confidence | Yes |
| L4 | Strategy scoring. Outcome-weighted choice across a fixed playbook set, bounded exploration | Yes, narrow |
| L5 | Evaluation-gated config change. Prompt and config versions promoted only after passing the suite | Yes, with a human confirming |
| L6 | Fine-tuning, weight updates | No. Later |

What I'm willing to say about it:

> NOVA improves through persistent memory, retrieval of past outcomes, outcome-scored strategy
> selection, and evaluation-gated configuration changes. It does not retrain or fine-tune any model.

What I won't say: "learns continuously", "gets smarter with every interaction", "self-improving",
"trains on your feedback", "adapts automatically".

On L6 being later rather than never: the feedback loop the MVP builds is a training-data pipeline
whether or not I ever use it as one. Confirmed corrections are labelled preference pairs. Every
accept, edit, and reject is a graded output. The evaluation set is a held-out test set. Building the
data and the baseline first is the right order. Fine-tuning before you can measure whether it helped
is how people burn GPU hours and then claim improvements they can't show.

Three rules keep that honest. Until an L6 model exists and has been measured, the docs say "does not
fine-tune" in the present tense. The roadmap can say it's planned; a capability list can't. And if I
do it, it gets measured on the same golden dataset as the L0 to L5 baseline. A fine-tune that loses
to prompt-plus-memory is a result worth publishing, not one to bury.

## Assumptions

| ID | Assumption | Status |
|---|---|---|
| A1 | Compose is enough for the DevOps story, no live URL needed | Mine to decide, going with yes |
| A2 | Hardware sustains a local model at usable latency and schema fidelity | Confirmed. 4B-class, 100% GPU, 9 to 26 s warm, 12 of 12 schema-valid |
| A3 | Repo goes public, including evaluation data and screenshots | Going with yes |
| A4 | Solo, no external review | Confirmed |
| A5 | 8B would be nicer but isn't required | Untested. Both 8B candidates are on disk, neither measured |
| A6 | A local model can extract reusable rules from corrections at decent precision | Untested, and it's the biggest unknown in the project |

## Dependencies

| Thing | Status |
|---|---|
| Ollama runtime | Installed, v0.33.3, API on `:11434` |
| Local model weights | Pulled: qwen3:4b, gemma3:4b, phi4-mini, qwen3:8b, granite3.3:8b (~18 GB) |
| Postgres with pgvector | Not set up yet |
| Docker Desktop | Installed, daemon not running |
| Local embedding model | Not chosen. Blocking, because the dimension goes into the schema |
| Cloud LLM provider | Not configured. Opt-in only, never an automatic fallback |
| Norton security suite | Holds GPU memory on this machine, so usable VRAM is under 6 GB |

## Open questions

| ID | Question | Blocking? | Going with |
|---|---|---|---|
| Q-01 | Expand the name NOVA? | No | Leave it alone. Forced backronyms read badly |
| Q-02 | Four playbooks or start with two? | No | Four: API/CRUD endpoint, auth/permission flow, UI form, data migration |
| Q-03 | Finish the model spike on the two 8B candidates? | Recommended first | Yes, it's mostly unattended machine time |

## Where the hours go

Splitting effort evenly across four areas gives four shallow stories, so it isn't even.

| Area | Treatment | Share |
|---|---|---|
| Memory, retrieval, strategy scoring | Headline work | ~30% |
| Evaluation harness and quality gates | Headline work, over-invested on purpose | ~25% |
| API, data model, async execution, observability | Solid and conventional | ~25% |
| Trace viewer, feedback UI, memory manager | Functional and readable, not fancy | ~20% |
