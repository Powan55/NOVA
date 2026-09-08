# ADR-001: Postgres with pgvector as the only datastore

Status: Accepted
Date: 2026-09-07

## Context

NOVA stores relational data (tasks, plans, cases, traces, feedback events, jobs, config versions)
and vectors (memory embeddings for retrieval). The modern instinct is to reach for a dedicated
vector database alongside a relational one.

Scale here is small. Thousands of memory vectors at most, single user, local. Dedicated vector
databases start to matter in the millions.

## Decision

PostgreSQL with pgvector, and nothing else. No separate vector database, no cache, no separate queue
backend.

## Alternatives

Qdrant, Chroma, or Pinecone alongside Postgres. Lower p99 at very large scale, GPU-accelerated
indexing, purpose-built filtering. All irrelevant at this scale, and each adds a service to Compose,
a client library, and an operational surface.

SQLite with a brute-force numpy scan. Genuinely adequate for thousands of vectors and honestly
simpler. Rejected because it gives up the async job pattern, and Postgres is the more useful thing
to have built against.

## Why

The deciding argument isn't performance, it's correctness.

With a separate vector store, writing a memory means two writes to two systems. A partial failure
leaves an embedding with no row, or a row with no embedding. The first is orphaned data. The second
is a memory that exists but can never be retrieved, which fails silently and looks exactly like a
system that stopped learning for no reason. Recovering from that needs reconciliation logic that
would be more code than the entire retrieval layer.

With pgvector, the memory row and its embedding are one transaction. The failure mode goes away
instead of getting handled.

Secondary: one service in Compose, one backup and restore path, and retrieval that can filter on
tenant, scope, and status in the same query as the similarity search, which is exactly the shape
NOVA's retrieval needs.

## Consequences

Easier: transactional consistency, one operational surface, relational filtering in the same query
as vector search, a single backup path.

Harder: the vector search ceiling is lower than a dedicated store, and HNSW rebuild time grows with
corpus size. Neither binds at this scale.

Sticky: the vector dimension is fixed in the schema. Changing the embedding model later means a
re-embedding migration. See [ADR-005](005-embedding-model-and-dimension.md).

Revisit if the memory corpus approaches a million vectors, or if retrieval latency becomes a
measured problem rather than an assumed one.
