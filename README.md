# NOVA

A locally hosted agent that converts software requirements into structured test plans, and retains
your corrections as inspectable memory so it stops repeating the same mistakes.

Inference runs on a local model by default. No requirement or test data leaves the machine.

**Status: planning.** Document set and two research spikes. No application code yet.

---

## The problem

Generating test cases from a requirement is something current models already do competently.
Retaining a team's conventions between sessions is not.

You tell an assistant to include an unauthenticated case for every endpoint. It does. Next session
you tell it again. The generation was never the expensive part; restating context indefinitely is.

The usual mitigation is a long system prompt, which is unversioned, unmeasured, and degrades quietly
as it grows. It also offers no way to answer whether output is actually improving.

## The approach

Each correction is extracted into a rule carrying provenance and a confidence score. Relevant rules
are retrieved per task and the applied ones are shown with their scores. Whether corrections stop
recurring is tracked as a metric, and prompt or configuration changes must pass a regression suite
before they take effect.

Adaptation happens through retrieval and configuration, not weights. NOVA does not fine-tune or
retrain any model. [What that covers and where it stops](docs/vision-and-scope.md#22-major-features).

## Documentation

| Document | Contents |
|---|---|
| [Vision and Scope](docs/vision-and-scope.md) | Problem, objectives, scope, exclusions |
| [Requirements](docs/srs.md) | Functional and non-functional requirements, verification matrix |
| [Architecture](docs/architecture.md) | Context, building blocks, runtime, deployment, crosscutting concerns |
| [Test Plan](docs/test-plan.md) | Strategy, dataset, metrics, gates |
| [Threat Model](docs/threat-model.md) | Assets, trust boundaries, threats, residual risk |
| [Development Plan](docs/sdp.md) | Milestones, slices, acceptance criteria |
| [Risk Register](docs/risk-register.md) | Active and closed risks |
| [Decision Log](docs/decision-log.md) | Decisions, alternatives, revisit triggers |
| [User Interface Design](docs/ui-design.md) | Screen inventory, wireframes, state coverage |
| [Architecture Decision Records](docs/adr/) | The decisions that needed more than a table row |
| [Spike Reports](docs/spikes/) | Investigations with raw data |

Full index and conventions: [docs/README.md](docs/README.md).

Distributable DOCX and PDF are generated from these sources into [`docs/dist/`](docs/dist/).

## What has been measured

Two spikes. Everything else in the document set is reasoning, not evidence.

| Finding | Detail | Source |
|---|---|---|
| A local model holds the test plan schema | 100 of 100 valid on first attempt, five candidates over twenty requirements | SPK-001 |
| The 4B-parameter class fits the hardware | 2.9 to 3.9 GB resident at 8K context, fully GPU-offloaded on a 6 GB card | SPK-001 |
| The 8B class does not, and gains nothing anyway | 6.6 GB, a third of it on the CPU, 2.4 times slower, and no better on coverage | SPK-001 |
| Latency has substantial headroom | 17.3 s median generation, against a 90 s provisional target for the whole pipeline | SPK-001 |
| Cold model load is a separate cost | 115 s cold against 18 to 21 s warm for the same model | SPK-001 |
| The recorded hardware assumption was wrong | 6 GB, not 8 GB. Found before any code was written | SPK-001 |
| Retrieval matches rules to differently-worded requirements | 0.900 MRR, 1.000 narrow recall@5 across 71 labelled pairs at 0.06 mean token overlap | SPK-002 |
| Embeddings beat lexical ranking, though not by default | BM25 matches on recall once a type filter is applied; it collapses without one | SPK-002 |
| Both models fit on the card together | 2.9 GB generation plus 681 MB embedding, both fully GPU-offloaded | SPK-002 |
| A rule that applies to everything cannot be retrieved by similarity | Ranked outside the top five by all five candidates, every time. It belongs outside the index | SPK-002 |

Sample sizes are 20 requirements per model across five models for SPK-001, and 20 requirements
against 24 labelled rules for SPK-002. Both are one run at a fixed seed, so run-to-run variance is
unmeasured, which is what the evaluation harness in M5 exists to fix. Method, raw output, and
limitations: [NOVA-SPK-001](docs/spikes/2026-09-07-model-selection.md),
[NOVA-SPK-002](docs/spikes/2026-09-08-embedding-selection.md).

## On claims

No performance or quality figure appears in this repository until it has been measured and can be
reproduced. Unmeasured values are bracketed placeholders. **A placeholder that cannot be filled
becomes a removed claim, not a softened one.**

Measured figures are stated with their method, sample size, and reference hardware. A figure without
that qualification is not reproducible and is therefore not a claim.

## Building the documents

```powershell
powershell -File tools/build-docs.ps1
```

Requires [Pandoc](https://pandoc.org). PDF output additionally requires Microsoft Word. Use
`-Format docx` to skip PDF generation.

## License

[MIT](LICENSE).
