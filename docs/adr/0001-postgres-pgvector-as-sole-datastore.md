---
status: accepted
date: 2026-09-07
decision-makers: Laxmi Poudel
consulted: none
informed: none
---

# PostgreSQL with pgvector as the sole datastore

## Context and problem statement

NOVA persists relational data (tasks, plans, cases, execution traces, feedback events, jobs,
configuration versions) and vector data (memory embeddings used for retrieval). The prevailing
instinct is to pair a relational database with a purpose-built vector database.

Expected scale is small: thousands of memory vectors, a single user, local deployment. Dedicated
vector databases become preferable at a scale several orders of magnitude larger.

How should relational and vector data be stored such that a memory and its embedding cannot diverge?

## Decision drivers

* A memory row and its embedding must never exist independently of one another
* Retrieval filters on tenant, scope, and status before ranking, so relational predicates and vector
  similarity are evaluated together
* Operational surface must stay minimal under a constrained effort budget
* Backup and restore must be a single documented procedure

## Considered options

* PostgreSQL with the pgvector extension, as the only datastore
* PostgreSQL for relational data with a dedicated vector database alongside
* SQLite with brute-force similarity computation in application code

## Decision outcome

Chosen option: **PostgreSQL with pgvector as the only datastore**, because it is the only option in
which a memory and its embedding are written within a single transaction, which converts a class of
silent data corruption into a condition that cannot arise.

The determining argument is correctness rather than performance. With separate stores, persisting a
memory requires two writes to two systems. A partial failure produces either orphaned vector data or
a memory row with no retrievable embedding. The second case fails silently: the memory exists, is
visible in the interface, and is never retrieved. To a user this is indistinguishable from a system
that has inexplicably stopped learning. Detecting and repairing it would require reconciliation
logic exceeding the size of the retrieval layer it protects.

### Consequences

* Good, because the divergence failure mode is eliminated by construction rather than handled
* Good, because tenant, scope, and status predicates are evaluated in the same query as the
  similarity search, which is precisely the shape retrieval requires
* Good, because one service, one backup procedure, one operational surface
* Bad, because vector search throughput has a lower ceiling than a purpose-built store, and index
  rebuild duration grows with corpus size. Neither binds at the expected scale
* Bad, because the vector dimension becomes a fixed column type. Changing the embedding model later
  requires re-embedding every memory and rebuilding the index. See
  [ADR-0005](0005-embedding-model-and-vector-dimension.md)

### Confirmation

Verified by the integration suite: a memory write that fails part way leaves no partial state.
Retrieval performance is measured against the evaluation dataset as the memory store grows from 10
to 100 to 500 records.

Revisit if the memory corpus approaches one million vectors, or if retrieval duration becomes a
measured problem rather than a presumed one.

## Pros and cons of the options

### PostgreSQL with pgvector

* Good, because transactional consistency between row and embedding
* Good, because relational filtering and vector ranking occur in one query
* Good, because a single service to deploy, back up, and restore
* Neutral, because performance is adequate at the expected scale and unremarkable beyond it
* Bad, because the vector dimension is fixed in the schema

### PostgreSQL plus a dedicated vector database

* Good, because lower tail latency at very large scale
* Good, because purpose-built indexing and filtering
* Bad, because a memory write spans two systems with no shared transaction
* Bad, because an additional service, client library, and operational surface
* Bad, because the failure mode it introduces is silent

### SQLite with brute-force similarity

* Good, because genuinely adequate for thousands of vectors
* Good, because the simplest possible deployment
* Bad, because it forfeits the durable job pattern that asynchronous execution depends on
* Bad, because it does not exercise the persistence concerns the project intends to demonstrate

## More information

Related: [ADR-0002](0002-postgres-job-table-for-async-execution.md) depends on this choice, since the
job table shares the same datastore and therefore the same transaction as task creation.
