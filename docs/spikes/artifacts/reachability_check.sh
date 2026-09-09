#!/usr/bin/env bash
# G4: can a container reach the host inference runtime, and does the datastore hold a 768-dimension
# vector with a working index?
#
# Two questions, both of which have to be answered before any migration is written:
#   1. Container -> host Ollama over host.docker.internal. Known first-run friction; Ollama binds
#      loopback by default, so this fails until it is told otherwise.
#   2. pgvector holds vector(768) (ADR-0005), indexes it with HNSW, and answers a nearest-neighbour
#      query. A dimension that cannot be indexed is not a decision, it is a mistake.
#
# Usage: bash reachability_check.sh
# Leaves nothing running: the container is removed on exit.

set -uo pipefail

PG_IMAGE="${PG_IMAGE:-pgvector/pgvector:pg17}"
PG_NAME="${PG_NAME:-nova-g4-db}"
PG_PASS="g4check"
DIM=768
OLLAMA_PORT="${OLLAMA_PORT:-11434}"
pass=0 fail=0

step() { printf '\n--- %s\n' "$1"; }
ok()   { printf '  PASS  %s\n' "$1"; pass=$((pass + 1)); }
no()   { printf '  FAIL  %s\n' "$1"; fail=$((fail + 1)); }
cleanup() { docker rm -f "$PG_NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT

step "environment"
docker version --format '  docker {{.Server.Version}} ({{.Server.Os}}/{{.Server.Arch}})'
docker compose version --short | sed 's/^/  compose /'
printf '  host listener on %s: %s\n' "$OLLAMA_PORT" \
  "$(netstat -ano 2>/dev/null | grep -E "LISTENING" | grep ":$OLLAMA_PORT " | awk '{print $2}' | head -1)"

step "1. container to host inference"
# alpine/curl rather than installing curl into a shell image: one pull, no package manager.
probe() {
  docker run --rm --add-host=host.docker.internal:host-gateway alpine/curl:latest \
    -s -m 5 -o /dev/null -w '%{http_code}' \
    "http://host.docker.internal:$OLLAMA_PORT/api/tags" 2>/dev/null
}
code=$(probe)
if [ "$code" = "200" ]; then
  ok "container reached host.docker.internal:$OLLAMA_PORT (HTTP $code)"
else
  no "container could not reach host.docker.internal:$OLLAMA_PORT (got '${code:-no response}')"
  printf '        fix: set OLLAMA_HOST=0.0.0.0:%s on the host and restart Ollama,\n' "$OLLAMA_PORT"
  printf '        then restrict the port to the Docker subnet in the host firewall.\n'
fi

step "2. datastore with a $DIM-dimension vector"
docker rm -f "$PG_NAME" >/dev/null 2>&1
if ! docker run -d --name "$PG_NAME" -e POSTGRES_PASSWORD="$PG_PASS" "$PG_IMAGE" >/dev/null; then
  no "could not start $PG_IMAGE"
else
  printf '  image %s\n' "$(docker image inspect "$PG_IMAGE" --format '{{index .RepoDigests 0}}' 2>/dev/null)"
  for _ in $(seq 1 60); do
    docker exec "$PG_NAME" pg_isready -U postgres -q && break
    sleep 1
  done
  sql() { docker exec -i "$PG_NAME" psql -U postgres -v ON_ERROR_STOP=1 -t -A -q -c "$1" 2>&1; }

  out=$(sql "CREATE EXTENSION IF NOT EXISTS vector; SELECT extversion FROM pg_extension WHERE extname='vector';")
  [ -n "$out" ] && ok "pgvector $out available" || no "pgvector extension unavailable: $out"

  out=$(sql "CREATE TABLE m (id int primary key, tenant_id int not null, embedding vector($DIM)); SELECT 'created';")
  [ "$out" = "created" ] && ok "vector($DIM) column accepted" || no "vector($DIM) column rejected: $out"

  out=$(sql "CREATE INDEX ON m USING hnsw (embedding vector_cosine_ops); SELECT 'indexed';")
  [ "$out" = "indexed" ] && ok "HNSW cosine index built over $DIM dimensions" || no "HNSW index failed: $out"

  # Two rows, one near the probe and one far, so the ordering proves the operator is doing something.
  out=$(sql "INSERT INTO m SELECT g, 1, (SELECT array_agg(CASE WHEN g=1 THEN 1.0 ELSE random() END)::vector FROM generate_series(1,$DIM)) FROM generate_series(1,2) g;
             SELECT id FROM m ORDER BY embedding <=> (SELECT embedding FROM m WHERE id=1) LIMIT 1;")
  [ "$out" = "1" ] && ok "nearest-neighbour query returns the expected row" || no "ANN query wrong: $out"

  out=$(sql "SELECT pg_column_size(embedding) FROM m WHERE id=1;")
  printf '  storage: %s bytes per %s-dimension vector\n' "$out" "$DIM"
fi

printf '\n%s passed, %s failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
