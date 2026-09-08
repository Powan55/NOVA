# Architecture Decision Records

Records of architecturally significant decisions, in [MADR 4.0](https://adr.github.io/madr/) format.

A decision is recorded here when it is expensive to reverse, likely to be challenged, or when its
rationale must survive later pressure to undo it. Decisions not meeting that bar are recorded in
[NOVA-DL-001](../decision-log.md), which is the complete index.

| ADR | Decision | Status | Date |
|---|---|---|---|
| [0001](0001-use-postgres-with-pgvector-as-sole-datastore.md) | PostgreSQL with pgvector as the sole datastore | Accepted | 2026-09-07 |
| [0002](0002-use-a-postgres-job-table-for-async-execution.md) | Job table and polling worker rather than a message broker | Accepted | 2026-09-07 |
| [0003](0003-do-not-use-an-agent-framework.md) | No agent framework | Accepted | 2026-09-07 |
| [0004](0004-require-human-confirmation-for-memory-writes.md) | Mandatory human confirmation for memory writes | Accepted | 2026-09-07 |
| [0005](0005-select-an-embedding-model-and-vector-dimension.md) | Embedding model and vector dimension | Proposed | 2026-09-07 |

## Conventions

- Numbered sequentially from `0001`. Numbers are never reused
- Filename is the number followed by a kebab-case title
- Status is one of `proposed`, `rejected`, `accepted`, `deprecated`, `superseded by ADR-NNNN`
- A superseded record is never deleted. Its status is amended and the superseding record links back
- Written at the point of decision, not retrospectively. Retrospective records read as reconstruction
  and an experienced reviewer will recognize them

## Template

```markdown
---
status: proposed
date: YYYY-MM-DD
decision-makers: names
consulted: names
informed: names
---

# Short title stating the problem and the resolution

## Context and problem statement

## Decision drivers

## Considered options

## Decision outcome

Chosen option: "...", because ...

### Consequences

### Confirmation

## Pros and cons of the options

## More information
```
