-- Task, job, and trace. The substrate for asynchronous execution (ADR-0002).
--
-- One state machine, not two: the task's, per NOVA-SRS-001 §3.6. The job row carries lease
-- bookkeeping only, so a claim can never disagree with the state the user is shown. A job is
-- claimable when its task is queued, or running under an expired lease.

CREATE TABLE task (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        uuid NOT NULL REFERENCES tenant (id),
    requirement_text text NOT NULL CHECK (requirement_text <> ''),
    -- Four types, because there are four playbooks. A fifth arrives with its playbook, and with
    -- the migration that widens this.
    requirement_type text NOT NULL CHECK (requirement_type IN
        ('api_crud_endpoint', 'auth_permission_flow', 'ui_form', 'data_migration')),
    context          text,
    state            text NOT NULL DEFAULT 'queued' CHECK (state IN
        ('queued', 'running', 'completed', 'failed', 'cancelled')),
    idempotency_key  text,
    failure_detail   text,
    created_at       timestamptz NOT NULL DEFAULT now(),
    started_at       timestamptz,
    finished_at      timestamptz
);

-- NFR-12. A replayed submission returns the original identifier rather than a second task.
CREATE UNIQUE INDEX task_idempotency ON task (tenant_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE INDEX task_tenant_created ON task (tenant_id, created_at DESC);

CREATE TABLE job (
    task_id      uuid PRIMARY KEY REFERENCES task (id) ON DELETE CASCADE,
    attempts     integer NOT NULL DEFAULT 0,
    max_attempts integer NOT NULL DEFAULT 3,
    lease_until  timestamptz,
    claimed_by   text,
    last_error   text,
    updated_at   timestamptz NOT NULL DEFAULT now()
);

-- Steps are appended as they complete, so a task that fails at generation still exposes what ran
-- before it (NOVA-SAD-001 §8.6). Ordering is by id: within one task there is one writer, the
-- worker holding the claim. `attempt` groups the steps of a reclaimed execution against those of
-- the execution it replaced, rather than interleaving them.
CREATE TABLE trace_step (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    task_id     uuid NOT NULL REFERENCES task (id) ON DELETE CASCADE,
    attempt     integer NOT NULL,
    step        text NOT NULL,
    detail      jsonb NOT NULL DEFAULT '{}'::jsonb,
    duration_ms integer,
    recorded_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX trace_step_task ON trace_step (task_id, id);
