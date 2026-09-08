# NOVA

A locally hosted agent that converts software requirements into structured test plans, and retains
your corrections as inspectable memory so it stops repeating the same mistakes.

Inference runs on a local model by default. No requirement or test data leaves the machine.

**Status: planning.** Document set and one research spike. No application code yet.

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
| [Architecture Decision Records](docs/adr/) | The decisions that needed more than a table row |
| [Spike Reports](docs/spikes/) | Investigations with raw data |

Full index and conventions: [docs/README.md](docs/README.md).

Distributable DOCX and PDF are generated from these sources into [`docs/dist/`](docs/dist/).

## What has been measured

One spike. Everything else in the document set is reasoning, not evidence.

| Finding | Detail |
|---|---|
| A local model holds the test plan schema | 12 of 12 valid on first attempt across three candidates |
| The 4B-parameter class fits the hardware | 2.9 to 3.9 GB resident at 8K context, fully GPU-offloaded on a 6 GB card |
| Latency has substantial headroom | 9 to 26 s warm generation, against a 90 s provisional target for the whole pipeline |
| Cold model load is a separate cost | 115 s cold against 18 to 21 s warm for the same model |
| The recorded hardware assumption was wrong | 6 GB, not 8 GB. Found before any code was written |

Sample size is four requirements per model, which is enough to close the hardware question and not
enough to select a model. Method, raw output, and limitations:
[NOVA-SPK-001](docs/spikes/2026-09-07-model-selection.md).

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
