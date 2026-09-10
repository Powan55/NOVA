-- Baseline: the vector extension, and the tenant that every later table is scoped to.
--
-- CON-7 puts the tenant identifier in from the first migration. Authentication is deferred, but
-- retrofitting a tenant column across a populated schema is the expensive version of this decision.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE tenant (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name       text NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- The single tenant of a single-user deployment. Fixed identifier so configuration and fixtures can
-- name it without a lookup.
INSERT INTO tenant (id, name) VALUES ('00000000-0000-0000-0000-000000000001', 'default');
