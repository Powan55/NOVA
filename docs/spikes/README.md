# Spike reports

Time-boxed investigations run to resolve a specific uncertainty before it can affect design or
implementation. Each produces a report with a stated method, raw output, and limitations.

| ID | Spike | Date | Status | Outcome |
|---|---|---|---|---|
| NOVA-SPK-001 | [Local model selection under a 6 GB VRAM ceiling](2026-09-07-model-selection.md) | 2026-09-07, completed 2026-09-08 | Complete | `gemma3:4b`. 100 of 100 schema-conformant across five candidates, 17.3 s median, 2.9 GB fully GPU-resident. The 8B class spills a third onto the CPU for no quality gain |
| NOVA-SPK-002 | [Embedding model and vector dimension](2026-09-08-embedding-selection.md) | 2026-09-08 | Complete | `embeddinggemma` at 768 dimensions. Leads every discriminating retrieval metric across five candidates, 77 ms warm, co-resident with the generation model inside 6 GB |
| NOVA-SPK-003 | [Container-to-host inference reachability and datastore provisioning](2026-09-09-container-to-host-reachability.md) | 2026-09-09 | Complete | Both reachable without configuration. Docker Desktop's host proxy reaches a loopback-bound Ollama, so the anticipated binding change is unnecessary. `vector(768)` indexes under HNSW and answers correctly |

## Planned

| Spike | Resolves | Blocking |
|---|---|---|
| Hybrid lexical and vector ranking | NOVA-SPK-002 follow-up 3 | No. Deferred until authentic corrections exist |

## Conventions

- A spike is time-boxed before it starts. Exceeding the box is itself a finding
- Every report states its method, its sample size, and its limitations. A measurement without a
  stated sample size is not a result
- Harnesses and raw output are committed under `artifacts/` so that any figure can be reproduced
- A partial spike is reported as partial. Unmeasured candidates are listed as unmeasured rather than
  omitted
- Recommendations arising from a small sample are marked provisional and do not become decisions
  until confirmed
