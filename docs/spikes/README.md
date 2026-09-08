# Spike reports

Time-boxed investigations run to resolve a specific uncertainty before it can affect design or
implementation. Each produces a report with a stated method, raw output, and limitations.

| ID | Spike | Date | Status | Outcome |
|---|---|---|---|---|
| NOVA-SPK-001 | [Local model selection under a 6 GB VRAM ceiling](2026-09-07-model-selection.md) | 2026-09-07 | Partial | The 4B-parameter class holds the test plan schema at 9 to 26 s warm, fully GPU-resident. The 8B class remains unmeasured |

## Planned

| Spike | Resolves | Blocking |
|---|---|---|
| Embedding model and vector dimension | [ADR-0005](../adr/0005-select-an-embedding-model-and-vector-dimension.md), R-04 | Yes. Blocks schema definition |
| Container-to-host inference reachability | R-09 | No, but it is the most probable early impediment |

## Conventions

- A spike is time-boxed before it starts. Exceeding the box is itself a finding
- Every report states its method, its sample size, and its limitations. A measurement without a
  stated sample size is not a result
- Harnesses and raw output are committed under `artifacts/` so that any figure can be reproduced
- A partial spike is reported as partial. Unmeasured candidates are listed as unmeasured rather than
  omitted
- Recommendations arising from a small sample are marked provisional and do not become decisions
  until confirmed
