---
status: accepted
date: 2026-09-08
decision-makers: Laxmi Poudel
consulted: none
informed: none
---

# Select an embedding model and vector dimension

## Context and problem statement

Memory retrieval is semantic. A requirement is embedded and stored rules are ranked partly by cosine
similarity against that vector. This requires an embedding model, and the dimension that model
produces becomes a fixed column type in the schema.

The dimension cannot change without re-embedding every stored memory and rebuilding the index. It is
one of the few decisions in this project that is expensive to reverse, which is why it is recorded
before it is taken rather than afterwards.

The model selection spike addressed generation and concluded there. Embedding was never measured.

## Decision drivers

* The dimension is fixed at schema creation, so this decision blocks all persistence work
* Embedding occurs synchronously on memory confirmation and again on every task, so its duration is
  user-visible
* The embedding model shares a 6 GB VRAM budget with the generation model
* Local-first operation is a confidentiality property, not a preference
* Retrieval must match a rule to a requirement phrased differently, since that is the substance of
  the memory capability

## Considered options

* A local embedding model served through the same runtime as generation
* A hosted embedding service
* Lexical retrieval using term-frequency ranking, with no embedding

## Decision outcome

Chosen option: **a local embedding model, `embeddinggemma`, at its native 768 dimensions**, because
it led every discriminating retrieval metric on the labelled corpus while costing 77 ms per call and
681 MB of VRAM, which leaves the generation model comfortably resident on the same 6 GB card.

Measured in [NOVA-SPK-002](../spikes/2026-09-08-embedding-selection.md) across five candidates, 20
requirements, and 24 hand-labelled memory rules at 0.06 mean token overlap:

| | `embeddinggemma` | Best other candidate | BM25 |
|---|---|---|---|
| MRR, production type filter applied | **0.900** | 0.863 | 0.771 |
| MRR, no type filter | **0.860** | 0.728 | 0.571 |
| Narrow-rule recall@5, no type filter | **0.775** | 0.750 | 0.425 |
| Warm latency, n=44 | 77 ms | 57 ms | not applicable |
| Resident | 681 MB | 26 MB | none |

The dimension is fixed at **768**. Truncation to 256 held quality under the type filter but lost
open-mode recall, and since the model supports truncation, storing 768 keeps the shorter vector
derivable later without re-embedding, whereas storing 256 would foreclose it. 768 is well inside
pgvector's index limits.

### Consequences

* Good, because retrieval quality on the corpus is high enough that a weak applied-lessons
  presentation in M3 can be attributed to extraction or ranking rather than to embedding
* Good, because the schema is unblocked and persistence work can begin
* Good, because embedding adds under 1% to task duration, so it needs no asynchronous handling
* Neutral, because a second model must be provisioned, documented, and pulled at setup
* Bad, because 681 MB of a 6 GB budget is now committed to embedding, narrowing the headroom for any
  later move to a larger generation model
* Bad, because the choice rests on a synthetic corpus labelled by one person, so it is a defensible
  starting point rather than a settled one

A consequence discovered during the spike, recorded as DL-029: a rule that applies universally has
no topical content to match on and was ranked outside the top five by every candidate for every
requirement. Always-apply rules therefore must not be routed through the vector index at all. This
has to be settled before the memory entity is defined in M3.

### Confirmation

Confirmed by [NOVA-SPK-002](../spikes/2026-09-08-embedding-selection.md), which states its method,
sample size, and limitations, and commits its harness and raw output. Retrieval figures reproduced
exactly across two runs.

Revisited when authentic corrections exist in volume, which is the first point at which the
synthetic-corpus limitation can be removed.

## Pros and cons of the options

### Local embedding model

* Good, because consistent with local-first operation and the confidentiality position
* Good, because no marginal cost and no network dependency
* Neutral, because one further model to provision
* Neutral, because quality is generally below hosted alternatives, though it proved sufficient on
  the labelled corpus
* Bad, because it consumes part of a constrained VRAM budget, measured at 681 MB

### Hosted embedding service

* Good, because generally stronger retrieval quality
* Good, because no local resource consumption
* Bad, because it defeats local-first operation and transmits requirement-derived text off-host
* Bad, because it would have to be opt-in, matching the hosted generation provider, which
  complicates the retrieval path

### Lexical retrieval

* Good, because simple, transparent, and adequate at low memory volumes
* Good, because no dimension is fixed in the schema and no model is required
* Neutral, because with the production type filter applied it matched the field on recall@5 (0.695),
  which was closer than expected and makes a hybrid worth measuring later
* Bad, because without the type filter it reached 0.425 narrow recall against 0.775, confirming by
  measurement that it cannot match a rule phrased differently from the requirement
* Bad, because it does not demonstrate the retrieval engineering the project intends to show

## More information

Related: [ADR-0001](0001-use-postgres-with-pgvector-as-sole-datastore.md) establishes why the dimension
resides in the schema. Evidence: [NOVA-SPK-002](../spikes/2026-09-08-embedding-selection.md). Closed
R-04 in [NOVA-RR-001](../risk-register.md) and G1 in
[NOVA-SDP-001 section 5.6](../sdp.md#56-entry-criteria-for-implementation).
