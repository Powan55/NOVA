# NOVA

A local agent that turns a requirement into a structured test plan, then uses your corrections so it
stops making the same mistakes. Corrections become memory rows you can read, edit, and delete.

Everything runs on a local model by default, so nothing leaves the machine.

**Status: planning.** Docs and one research spike. No app code yet.

## Docs

| Doc | What's in it |
|---|---|
| [Project brief](docs/00-project-brief.md) | The problem, who it's for, scope and non-goals |
| [Requirements](docs/01-prd.md) | Personas, journeys, functional and non-functional requirements, acceptance criteria |
| [Technical design](docs/02-technical-design.md) | Architecture, components, data flow, contracts, failure modes |
| [Test strategy](docs/03-test-strategy.md) | Test pyramid, evaluation dataset, metrics, CI gates |
| [Security and privacy](docs/04-security-privacy.md) | Threat model, trust boundaries, controls |
| [Delivery plan](docs/05-delivery-plan.md) | Milestones, vertical slices, cut order |
| [Decision log](docs/06-decision-log.md) | What was decided, what was rejected, why |
| [Risk register](docs/07-risk-register.md) | Open risks and what closes them |
| [Readiness](docs/08-readiness-checklist.md) | What's done and what's still missing before I start building |
| [ADRs](docs/adr/) | The decisions that needed more than a table row |
| [Spikes](docs/spikes/) | Research spikes with real numbers |

Short version for anyone skimming: [project brief](docs/00-project-brief.md), then the
[model spike](docs/spikes/2026-09-07-model-selection.md).

## The idea

Generating test cases from a requirement is something LLMs already do fine. Remembering how *your
team* writes tests is what they don't do.

You tell an assistant "always add an unauthenticated case for any endpoint". It does. Next session
you tell it again. And again. The generation was never the expensive part. Re-explaining yourself
every time is.

The usual fix is a long system prompt, which is unversioned, unmeasured, and quietly ignored as it
grows. Nobody can answer whether it's actually getting better.

NOVA's answer: pull each correction out as a rule with provenance and a confidence score, retrieve
the relevant ones per task, show which ones got applied and at what score, and track a metric for
whether corrections stop recurring. Prompt and config changes have to pass a regression suite before
they go live.

## What's actually been measured

One spike so far. Everything else in these docs is reasoning, not evidence.

- 4B-class local models held the test-plan JSON schema on 12 of 12 generations, fully on GPU inside
  6 GB of VRAM, at 9 to 26 seconds warm.
- The 8 GB VRAM figure I'd written down in planning was wrong. The card is 6 GB. Caught it before
  writing any code, which cost an afternoon instead of a rewrite later.

Method, raw numbers, and limitations: [model spike](docs/spikes/2026-09-07-model-selection.md).

## On claims

No performance or quality number goes in these docs, a README, or a resume until it's been measured
and can be reproduced. Anything unmeasured stays as a bracketed placeholder like
`[measured p95 latency]`. If a placeholder can't be filled, the claim gets deleted rather than
softened.

NOVA does not fine-tune or retrain anything. The [project brief](docs/00-project-brief.md) spells
out exactly what "learning" covers here and where it stops.
