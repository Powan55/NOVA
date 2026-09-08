# Readiness

Where the planning actually stands, and what's left before I start building.

Updated 2026-09-07.

## Checklist

| # | Item | Status | Where it is / what's missing |
|---|---|---|---|
| 1 | Problem is clearly defined | Done | [Brief](00-project-brief.md#the-problem). The re-instruction tax, with the specific failure mode named |
| 2 | Users and journeys documented | Done | [Requirements](01-prd.md). One primary persona, one deferred, the main journey plus ten alternate and failure journeys |
| 3 | Goals and measurable success metrics | Done | [Requirements](01-prd.md#success-metrics). Four separate scoreboards, every number labelled as a draft |
| 4 | Scope, assumptions, constraints, non-goals | Done | [Brief](00-project-brief.md#scope) |
| 5 | Functional requirements | Done | FR-1 to FR-18 with priorities |
| 6 | Non-functional requirements | Done | NFR-1 to NFR-11. Two now carry measured data |
| 7 | UX flows and designs | **Missing** | Journeys are written, but there are no wireframes and no screen inventory. The trace viewer and applied-lessons panel carry the whole project and neither has been designed |
| 8 | Architecture documented and reviewed | Partial | [Technical design](02-technical-design.md) is complete. Reviewed only by me, since I'm solo. Stating it rather than hiding it |
| 9 | Alternatives and tradeoffs documented | Done | [Technical design](02-technical-design.md#what-i-rejected) and the [decision log](06-decision-log.md) |
| 10 | Data model, ownership, retention, migration | **Blocked** | Entities, ownership, and retention are covered. The embedding dimension is unchosen and it goes into the schema. See G1 |
| 11 | API and integration contracts | Done | Operations, error model, idempotency, pagination |
| 12 | Auth, authorization, privacy, security identified | Done | [Security](04-security-privacy.md). Ten threats, layered defences, now-vs-production table |
| 13 | Dependencies, risks, open questions tracked | Done | [Risk register](07-risk-register.md), [brief](00-project-brief.md#dependencies) |
| 14 | Test strategy | Done | [Test strategy](03-test-strategy.md). Two layers, pyramid, dataset, twelve metrics with stated weaknesses, CI gates |
| 15 | Observability requirements | Done | [Technical design](02-technical-design.md#observability) |
| 16 | Deployment, rollout, rollback, support | Done | Deliberately thin, which is right for a local single-user app |
| 17 | Work decomposed into vertical slices | Done | [Delivery plan](05-delivery-plan.md#vertical-slices). S1 to S14, each demonstrable on its own |
| 18 | Acceptance criteria exist | Done | AC-1 to AC-13, plus a ready and done definition |

Fourteen done, two partial or blocked, two missing.

## What's missing, worst first

### G1 · Embedding model and dimension, blocking

The vector dimension is fixed when the schema is created. Choosing it afterwards means re-embedding
every memory and rebuilding the index, which is exactly the rework this planning is meant to avoid.

Fix: a short spike. Pull two or three candidate embedding models, measure dimension, embedding
latency, and retrieval quality on a handful of hand-labelled requirement-to-rule pairs drawn from
the 20 spike requirements. Half a day, then record the decision.

### G2 · Model spike is incomplete, do it first

Three of five candidates measured, at n=4 each. Enough to close the hardware risk, which was the
point, but not enough to pick a model. The lean toward a 4B-class model is provisional, and the two
8B candidates are on disk and unmeasured.

Fix: run the existing harness across all 20 requirements and all 5 candidates, then repeat once for
a first look at run-to-run variance. No new code, the harness exists and its self-test passes.
Mostly unattended machine time.

### G3 · No UX design, needed before UI work not before backend

Requirements say what the screens do. Nothing says what they look like or how they're laid out. The
trace viewer and applied-lessons panel are what make the agent internals readable, and they're the
two screenshots the whole presentation depends on.

Fix: a screen inventory and rough wireframes for four screens (task view, trace viewer, memory
manager, evaluation results). Doesn't block backend work, can run in parallel.

### G4 · Environment not fully verified, cheap

Docker Desktop is installed but the daemon isn't running, so nothing about the Compose path has been
exercised. Container-to-host Ollama reachability on Windows is unverified and is the likeliest early
time sink.

Fix: start Docker, stand up Postgres with pgvector, confirm a container reaches the host's Ollama
endpoint. An hour, and it de-risks the first milestone.

## What's actually established

The only part of this backed by evidence rather than reasoning.

| Established | Evidence |
|---|---|
| A local model holds the test-plan JSON schema | 12 of 12 valid first attempt across three models |
| 4B-class models fit this hardware with headroom | 2.9 to 3.9 GB resident at 8K context, 100% GPU offload on a 6 GB card |
| Generation latency is well inside the draft target | 9 to 26 s warm, against a p95 ≤90 s target for the whole pipeline |
| The Pydantic to schema to validation path works | Nested `$defs`/`$ref` accepted by the runtime's constrained decoding |
| Cold model load is a real cost and has to be measured separately | 115 s cold against 18 to 21 s warm for the same model |
| Hybrid reasoning models need thinking explicitly disabled | Required config, not an optimization |
| The 8 GB VRAM figure in planning was wrong | 6 GB. Found before writing any code |

Method, raw numbers, limitations: [model spike](spikes/2026-09-07-model-selection.md).

## Where I'm at

Two things are worth clearing before starting, and together they're about a day:

1. G1, the embedding spike. Blocking, and getting it wrong costs a data migration.
2. G4, environment verification. An hour, and it removes the most likely early time sink.

G2 is strongly recommended but not strictly blocking, since a provisional model choice can be
revised without rework, unlike the embedding dimension. G3 runs in parallel and is only needed
before UI work starts.

## What none of this covers

- No app code, scaffolding, database schema, or infrastructure exists
- No measured results beyond the one model spike
- Every performance and quality target is a draft, set from judgment rather than data
- The architecture is proposed, not validated. Parts of it may be wrong, which is what the first
  milestone is for
