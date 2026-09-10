"""Task lifecycle: submission, durable claim, and execution trace (S1, S2, S3).

Submission writes the task and its job in one transaction, so no task can exist without the job
that will run it (ADR-0002). A worker claims under `FOR UPDATE SKIP LOCKED` with a lease: a
terminated worker's job is reclaimed once its lease expires, and the trace of the attempt it did
not finish stays where it was written.

The state machine is the task's alone (NOVA-SRS-001 §3.6). The job row holds lease bookkeeping
only, so a claim cannot disagree with the state a user is shown.

Usage:  py -3 nova/tasks.py --selftest   exercise the lifecycle against a scratch database
"""
from __future__ import annotations

import os
import subprocess
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

DSN = os.environ.get("DATABASE_URL", "postgresql://nova:nova@127.0.0.1:5432/nova")

# The single tenant of a single-user deployment, created by migration 0001. Authentication is
# deferred; the tenant is not, because retrofitting it is the expensive version (CON-7).
DEFAULT_TENANT = uuid.UUID("00000000-0000-0000-0000-000000000001")

# Mirrored by the CHECK constraint in migration 0002, which is the authority. Repeated here so a
# submission is refused with a message naming the constraint rather than a database error (FR-1.1).
REQUIREMENT_TYPES = ("api_crud_endpoint", "auth_permission_flow", "ui_form", "data_migration")

# NOVA-SRS-001 §3.6. `queued -> running` is the claim itself; every transition made through
# `_terminate` is to a terminal state.
TRANSITIONS: dict[str, set[str]] = {
    "queued": {"running", "cancelled"},
    "running": {"completed", "failed", "cancelled"},
}

MAX_TEXT = 20_000  # FR-1.1

# Generation alone measured 17.3 s median and 26 s worst (NOVA-SPK-001), before retrieval and
# review are added. A lease shorter than the work it covers reclaims a task that is still running.
LEASE_SECONDS = 300


class TaskError(RuntimeError):
    """A lifecycle failure. `detail` is safe to show a user: it names what was refused and why."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


@dataclass(frozen=True)
class Claim:
    """One worker's exclusive hold on a task, valid until the lease expires."""

    task_id: uuid.UUID
    tenant_id: uuid.UUID
    requirement_text: str
    requirement_type: str
    context: str | None
    attempt: int


def submit(
    conn: psycopg.Connection[Any],
    tenant_id: uuid.UUID,
    requirement_text: str,
    requirement_type: str,
    *,
    context: str | None = None,
    idempotency_key: str | None = None,
) -> uuid.UUID:
    """Accept a requirement and queue it. Returns the task identifier (FR-1, NFR-12)."""
    text = requirement_text.strip()
    if not text:
        raise TaskError("requirement text is empty")
    if len(text) > MAX_TEXT:
        raise TaskError(f"requirement text is {len(text)} characters; the limit is {MAX_TEXT}")
    if requirement_type not in REQUIREMENT_TYPES:
        raise TaskError(
            f"unknown requirement type '{requirement_type}'. One of: {', '.join(REQUIREMENT_TYPES)}"
        )

    try:
        with conn.transaction():
            if idempotency_key is not None:
                replayed = _by_key(conn, tenant_id, idempotency_key)
                if replayed is not None:
                    return replayed
            row = conn.execute(
                "INSERT INTO task (tenant_id, requirement_text, requirement_type, context,"
                " idempotency_key) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (tenant_id, text, requirement_type, context, idempotency_key),
            ).fetchone()
            assert row is not None
            task_id = uuid.UUID(str(row[0]))
            conn.execute("INSERT INTO job (task_id) VALUES (%s)", (task_id,))
            return task_id
    except psycopg.errors.UniqueViolation:
        # Two submissions raced on one key. The one that landed is the answer (NFR-12).
        assert idempotency_key is not None
        replayed = _by_key(conn, tenant_id, idempotency_key)
        if replayed is None:
            raise
        return replayed


def _by_key(conn: psycopg.Connection[Any], tenant_id: uuid.UUID, key: str) -> uuid.UUID | None:
    row = conn.execute(
        "SELECT id FROM task WHERE tenant_id = %s AND idempotency_key = %s", (tenant_id, key)
    ).fetchone()
    return None if row is None else uuid.UUID(str(row[0]))


def claim(
    conn: psycopg.Connection[Any], worker: str, *, lease_seconds: int = LEASE_SECONDS
) -> Claim | None:
    """Take the oldest claimable job: queued, or running under an expired lease.

    A job locked by another worker is skipped rather than waited on. Returns None when there is
    nothing to run, which includes the case where the only candidate had exhausted its attempts and
    was failed by this call.
    """
    with conn.transaction():
        row = conn.execute(
            """
            SELECT j.task_id, t.tenant_id, t.requirement_text, t.requirement_type, t.context,
                   j.attempts, j.max_attempts
            FROM job j JOIN task t ON t.id = j.task_id
            WHERE t.state = 'queued' OR (t.state = 'running' AND j.lease_until < now())
            ORDER BY t.created_at
            FOR UPDATE OF j SKIP LOCKED
            LIMIT 1
            """
        ).fetchone()
        if row is None:
            return None
        task_id, tenant_id, text, requirement_type, context, attempts, max_attempts = row

        if attempts >= max_attempts:
            detail = f"abandoned after {attempts} attempts"
            conn.execute(
                "UPDATE task SET state = 'failed', failure_detail = %s, finished_at = now()"
                " WHERE id = %s",
                (detail, task_id),
            )
            conn.execute(
                "UPDATE job SET lease_until = NULL, last_error = %s, updated_at = now()"
                " WHERE task_id = %s",
                (detail, task_id),
            )
            return None

        conn.execute(
            "UPDATE job SET attempts = attempts + 1, claimed_by = %s,"
            " lease_until = now() + make_interval(secs => %s), updated_at = now()"
            " WHERE task_id = %s",
            (worker, lease_seconds, task_id),
        )
        conn.execute(
            "UPDATE task SET state = 'running', started_at = coalesce(started_at, now())"
            " WHERE id = %s",
            (task_id,),
        )
    return Claim(
        task_id=uuid.UUID(str(task_id)),
        tenant_id=uuid.UUID(str(tenant_id)),
        requirement_text=text,
        requirement_type=requirement_type,
        context=context,
        attempt=attempts + 1,
    )


def complete(conn: psycopg.Connection[Any], task_id: uuid.UUID) -> None:
    _terminate(conn, task_id, "completed")


def fail(conn: psycopg.Connection[Any], task_id: uuid.UUID, detail: str) -> None:
    _terminate(conn, task_id, "failed", detail=detail)


def cancel(conn: psycopg.Connection[Any], tenant_id: uuid.UUID, task_id: uuid.UUID) -> None:
    """Cancel a queued or running task, retaining its partial trace (NFR-8).

    User-initiated, so tenant-scoped. Completion and failure are the worker's and are not.
    """
    _terminate(conn, task_id, "cancelled", tenant_id=tenant_id)


def _terminate(
    conn: psycopg.Connection[Any],
    task_id: uuid.UUID,
    to: str,
    *,
    detail: str | None = None,
    tenant_id: uuid.UUID | None = None,
) -> None:
    sources = [state for state, allowed in TRANSITIONS.items() if to in allowed]
    sql = (
        "UPDATE task SET state = %s, failure_detail = %s, finished_at = now()"
        " WHERE id = %s AND state = ANY(%s)"
    )
    params: list[Any] = [to, detail, task_id, sources]
    if tenant_id is not None:
        sql += " AND tenant_id = %s"
        params.append(tenant_id)

    with conn.transaction():
        if conn.execute(sql, params).rowcount != 1:
            raise TaskError(_refusal(conn, task_id, to, tenant_id))
        conn.execute(
            "UPDATE job SET lease_until = NULL, last_error = coalesce(%s, last_error),"
            " updated_at = now() WHERE task_id = %s",
            (detail, task_id),
        )


def _refusal(
    conn: psycopg.Connection[Any], task_id: uuid.UUID, to: str, tenant_id: uuid.UUID | None
) -> str:
    """Distinguish the two reasons: the task is not visible, or the move is not permitted."""
    sql = "SELECT state FROM task WHERE id = %s"
    params: list[Any] = [task_id]
    if tenant_id is not None:
        sql += " AND tenant_id = %s"
        params.append(tenant_id)
    row = conn.execute(sql, params).fetchone()
    if row is None:
        return f"no task {task_id}"
    return f"task {task_id} is {row[0]}; {to} is not a permitted transition from it"


def record_step(
    conn: psycopg.Connection[Any],
    task_id: uuid.UUID,
    attempt: int,
    step: str,
    *,
    detail: dict[str, Any] | None = None,
    duration_ms: int | None = None,
) -> None:
    """Append one trace step, as the step completes rather than at the end of the task, so a task
    that fails partway still exposes what ran before it (FR-8)."""
    conn.execute(
        "INSERT INTO trace_step (task_id, attempt, step, detail, duration_ms)"
        " VALUES (%s, %s, %s, %s, %s)",
        (task_id, attempt, step, Jsonb(detail or {}), duration_ms),
    )


def get(
    conn: psycopg.Connection[Any], tenant_id: uuid.UUID, task_id: uuid.UUID
) -> dict[str, Any] | None:
    with conn.cursor(row_factory=dict_row) as cur:
        return cur.execute(
            "SELECT t.*, j.attempts, j.max_attempts, j.lease_until, j.claimed_by, j.last_error"
            " FROM task t JOIN job j ON j.task_id = t.id"
            " WHERE t.id = %s AND t.tenant_id = %s",
            (task_id, tenant_id),
        ).fetchone()


def trace(
    conn: psycopg.Connection[Any], tenant_id: uuid.UUID, task_id: uuid.UUID
) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        return cur.execute(
            "SELECT s.attempt, s.step, s.detail, s.duration_ms, s.recorded_at"
            " FROM trace_step s JOIN task t ON t.id = s.task_id"
            " WHERE s.task_id = %s AND t.tenant_id = %s ORDER BY s.id",
            (task_id, tenant_id),
        ).fetchall()


def selftest(dsn: str = DSN) -> None:
    """Exercise the lifecycle against a scratch database it creates and drops.

    A scratch database rather than the configured one: `claim` serves every tenant, as a worker
    does, so it must not be able to reach a real queued task.
    """
    scratch = "nova_tasks_selftest"
    with psycopg.connect(dsn, autocommit=True) as admin:
        admin.execute(f'DROP DATABASE IF EXISTS "{scratch}" WITH (FORCE)')
        admin.execute(f'CREATE DATABASE "{scratch}"')
    scratch_dsn = psycopg.conninfo.make_conninfo(dsn, dbname=scratch)
    try:
        subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parents[1] / "db" / "migrate.py")],
            env={**os.environ, "DATABASE_URL": scratch_dsn},
            check=True,
            capture_output=True,
        )
        with psycopg.connect(scratch_dsn, autocommit=True) as conn:
            _exercise(conn, scratch_dsn)
        print("selftest ok: submission, idempotency, contention, reclamation, limit, isolation")
    finally:
        with psycopg.connect(dsn, autocommit=True) as admin:
            admin.execute(f'DROP DATABASE IF EXISTS "{scratch}" WITH (FORCE)')


def _refused(call: Any, *args: Any, **kwargs: Any) -> str:
    """Call something expected to refuse, and return the detail it refused with."""
    try:
        call(*args, **kwargs)
    except TaskError as exc:
        return exc.detail
    raise AssertionError(f"{getattr(call, '__name__', call)} did not raise")


def _count(conn: psycopg.Connection[Any], sql: str) -> int:
    row = conn.execute(sql).fetchone()
    assert row is not None
    return int(row[0])


def _exercise(conn: psycopg.Connection[Any], dsn: str) -> None:
    row = conn.execute("INSERT INTO tenant (name) VALUES ('selftest-other') RETURNING id").fetchone()
    assert row is not None
    other = uuid.UUID(str(row[0]))

    # FR-1.1: every rejection names the constraint it violated.
    assert "empty" in _refused(submit, conn, DEFAULT_TENANT, "   ", "ui_form")
    assert "limit" in _refused(submit, conn, DEFAULT_TENANT, "x" * (MAX_TEXT + 1), "ui_form")
    assert "unknown requirement type" in _refused(submit, conn, DEFAULT_TENANT, "x", "nonsense")

    # NFR-12: a replay returns the original identifier and does not queue a second task.
    first = submit(conn, DEFAULT_TENANT, "requirement one", "api_crud_endpoint", idempotency_key="k1")
    replay = submit(conn, DEFAULT_TENANT, "requirement one", "api_crud_endpoint", idempotency_key="k1")
    assert replay == first
    assert _count(conn, "SELECT count(*) FROM task") == 1

    # ADR-0002: no task exists without its job.
    orphans = "SELECT count(*) FROM task t LEFT JOIN job j ON j.task_id = t.id WHERE j.task_id IS NULL"
    assert _count(conn, orphans) == 0

    second = submit(conn, DEFAULT_TENANT, "requirement two", "ui_form")

    # Claim under contention: a job row held by another transaction is skipped, not waited on.
    with psycopg.connect(dsn) as holder:
        holder.execute("SELECT 1 FROM job WHERE task_id = %s FOR UPDATE", (first,))
        skipped = claim(conn, "worker-a")
        assert skipped is not None and skipped.task_id == second, "a locked job was not skipped"
        holder.rollback()

    taken = claim(conn, "worker-b")
    assert taken is not None and taken.task_id == first and taken.attempt == 1
    assert taken.requirement_text == "requirement one"
    assert taken.requirement_type == "api_crud_endpoint"
    running = get(conn, DEFAULT_TENANT, first)
    assert running is not None and running["state"] == "running"
    assert running["claimed_by"] == "worker-b"

    record_step(conn, first, taken.attempt, "playbook_selected", detail={"playbook": "api_default"})
    record_step(conn, first, taken.attempt, "generated", duration_ms=17300)
    assert claim(conn, "worker-c") is None, "a leased job was claimed by a second worker"

    # Worker termination: the lease expires, the job is reclaimed, and the partial trace survives.
    conn.execute(
        "UPDATE job SET lease_until = now() - interval '1 second' WHERE task_id = %s", (first,)
    )
    reclaimed = claim(conn, "worker-c")
    assert reclaimed is not None and reclaimed.task_id == first and reclaimed.attempt == 2
    steps = trace(conn, DEFAULT_TENANT, first)
    assert [s["step"] for s in steps] == ["playbook_selected", "generated"], "partial trace lost"
    assert steps[0]["detail"] == {"playbook": "api_default"}
    assert steps[1]["duration_ms"] == 17300

    record_step(conn, first, reclaimed.attempt, "generated", duration_ms=16100)
    assert [s["attempt"] for s in trace(conn, DEFAULT_TENANT, first)] == [1, 1, 2]

    # Tenant isolation (CON-7). Every read and every user-initiated write is scoped.
    assert get(conn, other, first) is None
    assert trace(conn, other, first) == []
    assert _refused(cancel, conn, other, first) == f"no task {first}"

    complete(conn, first)
    done = get(conn, DEFAULT_TENANT, first)
    assert done is not None and done["state"] == "completed" and done["finished_at"] is not None
    assert done["lease_until"] is None, "a finished job kept its lease"
    assert "not a permitted transition" in _refused(complete, conn, first)
    assert "not a permitted transition" in _refused(cancel, conn, DEFAULT_TENANT, first)

    # Attempt limit: reclaiming a job past its limit fails the task rather than looping forever.
    record_step(conn, second, 1, "generated", duration_ms=900)
    conn.execute(
        "UPDATE job SET attempts = max_attempts, lease_until = now() - interval '1 second'"
        " WHERE task_id = %s",
        (second,),
    )
    assert claim(conn, "worker-d") is None
    abandoned = get(conn, DEFAULT_TENANT, second)
    assert abandoned is not None and abandoned["state"] == "failed"
    assert abandoned["failure_detail"] == "abandoned after 3 attempts"
    assert len(trace(conn, DEFAULT_TENANT, second)) == 1, "trace of a failed task lost"

    # A cancelled task is not claimable.
    third = submit(conn, DEFAULT_TENANT, "requirement three", "data_migration")
    cancel(conn, DEFAULT_TENANT, third)
    assert claim(conn, "worker-e") is None
    cancelled = get(conn, DEFAULT_TENANT, third)
    assert cancelled is not None and cancelled["state"] == "cancelled"


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "--selftest"
    if arg == "--selftest":
        try:
            selftest()
        except (TaskError, psycopg.Error) as exc:
            sys.exit(f"selftest failed: {exc}")
    else:
        sys.exit(f"unknown argument: {arg}")
