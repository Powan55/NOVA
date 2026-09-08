# ADR-002: Postgres job table with a polling worker, not Celery

Status: Accepted
Date: 2026-09-07

## Context

Task execution takes tens of seconds. The model spike measured 9 to 26 s for generation alone,
before retrieval, critique, and persistence get added. Far too long for a synchronous HTTP request,
so execution has to be async and durable: a task survives a worker crash, exposes its status, and
retries within bounds.

The conventional answer in a Python stack is Celery with Redis.

## Decision

A `jobs` table in Postgres, claimed by a polling worker with `SELECT ... FOR UPDATE SKIP LOCKED`,
with a lease that expires so crashed jobs get reclaimed.

## Alternatives

Celery + Redis. The standard choice. Brings a broker, result backend, scheduling, fan-out, retries,
and a monitoring ecosystem.

FastAPI `BackgroundTasks`. Rejected outright: tasks die with the process, no durable status, no
retry. Fails the basic requirement.

## Why

Celery solves problems this project doesn't have. No multi-worker fan-out, no scheduling, no
backpressure, no throughput concern. One user, one task at a time, one machine. What it would add is
two more services in Compose for a local single-user app.

`SELECT ... FOR UPDATE SKIP LOCKED` is a well-established durable-queue pattern. It gives claim
semantics, and a lease column gives crash recovery. Because the job row lives in the same database
as the task record, enqueueing is transactional with task creation, so there's no window where a
task exists but its job doesn't.

It's also trivially inspectable. Debugging a stuck job is a `SELECT`, not a Redis CLI session.

Polling latency is about a second, against tasks that take tens of seconds. It doesn't register.

## Consequences

Easier: zero added infrastructure, transactional enqueue, status visible in SQL, straightforward
integration testing (kill a worker, assert the job gets reclaimed).

Harder: no scheduling, no fan-out, no monitoring ecosystem. Retry and backoff logic is hand-written,
which means it has to be tested, and it is, in the integration suite.

If challenged: on a production team with real throughput, scheduled work, or backpressure
requirements, Celery or a managed queue is the right call. None of that applies here, and adding it
to look conventional would be padding.

Revisit if multi-worker execution, scheduled evaluation runs, or backpressure become real
requirements.
