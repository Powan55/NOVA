---
status: accepted
date: 2026-09-07
decision-makers: Laxmi Poudel
consulted: none
informed: none
---

# Job table and polling worker rather than a message broker

## Context and problem statement

Task execution takes tens of seconds. The model selection spike measured 9 to 26 seconds for
generation alone, before retrieval, review, and persistence are added. This is far beyond an
acceptable synchronous request duration, so execution must be asynchronous and durable: a task must
survive worker termination, expose its status, and retry within bounds.

The conventional answer in this ecosystem is a distributed task queue with a message broker.

How should asynchronous execution be made durable without introducing infrastructure the project
does not otherwise require?

## Decision drivers

* A task must survive worker termination without loss of its execution trace
* Task status must be observable, and a stalled task must be diagnosable
* Enqueueing must not be able to succeed while task creation fails, or the reverse
* Operational surface must stay minimal under a constrained effort budget
* There is no fan-out, scheduling, or backpressure requirement

## Considered options

* A job table in PostgreSQL, claimed by a polling worker under row-level locking with lease expiry
* A distributed task queue with a message broker
* In-process background tasks provided by the web framework

## Decision outcome

Chosen option: **a job table in PostgreSQL**, claimed with `SELECT ... FOR UPDATE SKIP LOCKED` and a
lease that expires, because it satisfies every stated driver using infrastructure the project
already requires, and because it makes enqueueing transactional with task creation.

A distributed queue addresses problems this project does not have. There is no fan-out, no
scheduling, and no backpressure requirement: one user, one concurrent task, one machine. What it
would contribute is two further services in the deployment composition for a local single-user
application.

Because the job row shares a transaction with the task record, no window exists in which a task is
present without its job. Diagnosis of a stalled job is a query rather than an operational
investigation.

### Consequences

* Good, because no additional infrastructure
* Good, because enqueueing and task creation share a transaction
* Good, because job state is inspectable with ordinary queries
* Good, because recovery is straightforwardly testable: terminate a worker, assert reclamation
* Bad, because there is no scheduling and no fan-out capability
* Bad, because retry and backoff logic is written by hand, and therefore must also be tested
* Neutral, because polling introduces approximately one second of latency against tasks lasting tens
  of seconds

### Confirmation

Verified by integration tests covering claim under contention, lease expiry and reclamation after
worker termination, and bounded retry of a repeatedly failing job. Each asserts that the partial
execution trace survives.

Revisit if multi-worker execution, scheduled evaluation runs, or backpressure become genuine
requirements.

## Pros and cons of the options

### Job table with polling worker

* Good, because zero additional infrastructure
* Good, because transactional enqueue
* Good, because inspectable and testable without specialist tooling
* Bad, because no scheduling, fan-out, or monitoring ecosystem
* Bad, because retry semantics are hand-written

### Distributed task queue with a message broker

* Good, because mature retry, scheduling, and monitoring capability
* Good, because horizontal scaling is available when needed
* Bad, because two additional services for a single-user local application
* Bad, because enqueueing cannot share a transaction with task creation without additional patterns
* Neutral, because on a production team with real throughput requirements this would be the correct
  choice. Adopting it here to appear conventional would be unjustified

### Framework background tasks

* Good, because trivially simple
* Bad, because tasks are lost on process termination
* Bad, because there is no durable status and no retry
* Bad, because it fails the stated drivers outright

## More information

Depends on [ADR-0001](0001-postgres-pgvector-as-sole-datastore.md), which establishes PostgreSQL as
the sole datastore and therefore makes the transactional enqueue property available.
