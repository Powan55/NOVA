# Architecture decision records

The [decision log](../06-decision-log.md) is the full index, with status, alternatives, rationale,
cost, and revisit trigger for every decision.

An ADR lives here only where the reasoning needs more room than a table row: decisions likely to get
challenged, decisions that are expensive to reverse, or ones whose rationale needs to survive the
temptation to undo them later. Everything else stays in the log.

| ADR | Decision | Status |
|---|---|---|
| [001](001-postgres-pgvector-sole-datastore.md) | Postgres with pgvector as the only datastore | Accepted |
| [002](002-postgres-job-table-over-celery.md) | Postgres job table with a polling worker, not Celery | Accepted |
| [003](003-no-agent-framework.md) | No agent framework | Accepted |
| [004](004-mandatory-memory-confirmation.md) | Human confirmation on every memory write | Accepted |
| [005](005-embedding-model-and-dimension.md) | Embedding model and vector dimension | Open, blocking |

Written when the decision gets made, not after. Retroactive ADRs read as fiction and an experienced
reviewer can tell.
