# ADR-005: Embedding model and vector dimension

Status: Open, blocking. No decision yet
Raised: 2026-09-07

## Context

Memory retrieval is semantic. A requirement gets embedded, and stored rules are ranked partly by
cosine similarity against that vector. That needs an embedding model, and the dimension it produces
becomes a fixed column type in the database schema.

The dimension can't change without re-embedding every stored memory and rebuilding the index, which
makes this one of the few decisions here that's genuinely expensive to reverse. Recording it before
it's made rather than after.

## Why it's still open

The model spike answered the generation question and stopped. Embedding was never measured. Nothing
about the schema can be built until this is settled, because the dimension is part of the schema.

## Options

| Option | Consideration |
|---|---|
| A local embedding model through the same runtime as generation | Consistent with local-first. One more model pull. Dimension and quality vary by model |
| A hosted embedding API | Generally stronger, but breaks the local-only default and puts requirement-derived text on the network. Would have to be opt-in like the cloud generation provider |
| Lexical retrieval instead of vectors (BM25 or trigram) | Honest and simple, adequate at small memory volumes. Gives up paraphrase matching, which is central to the retrieval story, so a rule phrased differently from the requirement would never surface |

## What the decision needs

1. Candidate models pulled, output dimensions recorded
2. Embedding latency measured, since embedding happens synchronously on memory confirmation and
   again on every task
3. Retrieval quality measured on hand-labelled requirement-to-rule pairs. The 20 requirements from
   the model spike are a usable starting corpus
4. Resident memory cost, since the embedding model shares a 6 GB GPU with the generation model

About half a day.

## Interim position

None. This blocks schema work and should be settled before the first migration is written.

## Cost of getting it wrong

Picking a dimension and later changing the model means a re-embedding migration: read every memory,
re-embed, rewrite the column type, rebuild the HNSW index. That's a documented procedure rather than
a disaster, and it's entirely avoidable by spending half a day now.

Picking a model whose quality is poor is worse and less visible. Retrieval would underperform, the
applied-lessons panel would show weak matches, and the correction recurrence rate would look bad for
a reason that has nothing to do with the memory mechanism being wrong. That failure is easy to
misattribute.

## Related

- [ADR-001](001-postgres-pgvector-sole-datastore.md), why the dimension lives in the schema at all
- [Risk register, R-04](../07-risk-register.md)
- [Readiness, G1](../08-readiness-checklist.md)
