---
status: proposed
date: 2026-09-07
decision-makers: Laxmi Poudel
consulted: none
informed: none
---

# Embedding model and vector dimension

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

**Not yet taken.** This ADR is recorded in proposed status to prevent the decision being made
implicitly by whichever schema migration is written first.

Deciding requires:

1. Candidate models retrieved, with their output dimensions recorded
2. Embedding duration measured, since it occurs on the synchronous path
3. Retrieval quality measured against hand-labelled requirement-to-rule pairs. The twenty
   requirements produced for the model selection spike are a usable starting corpus
4. Resident memory cost measured, since the embedding model shares the GPU with generation

Estimated effort: approximately four hours.

### Consequences of deferring correctly

Selecting a dimension and subsequently changing the model requires reading every memory, re-embedding
it, altering the column type, and rebuilding the index. That is a documented procedure rather than a
catastrophe, but it is entirely avoidable at the cost of half a day now.

Selecting a model of poor quality is worse and less visible. Retrieval would underperform, applied
lessons would show weak matches, and the Correction Recurrence Rate would appear poor for reasons
unrelated to the memory mechanism. That failure is straightforward to misattribute, which makes it
more dangerous than the migration cost.

### Confirmation

The decision is confirmed by a committed spike report following the same form as the model selection
spike: stated method, raw output, sample size, and limitations.

## Pros and cons of the options

### Local embedding model

* Good, because consistent with local-first operation and the confidentiality position
* Good, because no marginal cost and no network dependency
* Neutral, because one further model to provision
* Bad, because quality is generally below hosted alternatives
* Bad, because it consumes part of a constrained VRAM budget

### Hosted embedding service

* Good, because generally stronger retrieval quality
* Good, because no local resource consumption
* Bad, because it defeats local-first operation and transmits requirement-derived text off-host
* Bad, because it would have to be opt-in, matching the hosted generation provider, which
  complicates the retrieval path

### Lexical retrieval

* Good, because simple, transparent, and adequate at low memory volumes
* Good, because no dimension is fixed in the schema and no model is required
* Bad, because it cannot match a rule phrased differently from the requirement, which is the
  substance of the memory capability
* Bad, because it does not demonstrate the retrieval engineering the project intends to show

## More information

Related: [ADR-0001](0001-postgres-pgvector-as-sole-datastore.md) establishes why the dimension
resides in the schema. Tracked as R-04 in [NOVA-RR-001](../risk-register.md) and as G1 in
[NOVA-SDP-001 section 5.6](../sdp.md#56-entry-criteria-for-implementation).
