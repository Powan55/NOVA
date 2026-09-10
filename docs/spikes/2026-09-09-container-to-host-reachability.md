# Spike Report: container-to-host inference reachability and datastore provisioning

| Field | Value |
|---|---|
| Document ID | NOVA-SPK-003 |
| Version | 1.0 |
| Status | Complete |
| Owner | Laxmi Poudel |
| Date | 2026-09-09 |
| Question | Can a container reach the host inference runtime on this platform, and does the datastore hold a 768-dimension vector with a working index? |
| Answer | Both, without configuration. Docker Desktop reaches a loopback-bound Ollama through its own host proxy, so the anticipated impediment does not occur here. `pgvector` 0.8.6 accepts `vector(768)`, builds an HNSW cosine index over it, and answers a nearest-neighbour query |
| Decisions affected | DL-030, R-09, G4, NOVA-SAD-001 §7 |

## Why this ran

R-09 recorded container-to-host inference reachability as the most probable early impediment, on the
reasoning that Ollama binds loopback by default and a container is not on the host's loopback. It was
the last open entry condition for implementation, and it gates the deployment composition: if the
path needed a host-side binding change, that change would have to appear in the deployment
documentation, in the threat model, and in the first-run instructions for anyone cloning the
repository.

The datastore half was folded into the same run because it answers a question of the same shape and
against the same runtime. ADR-0005 fixed the vector dimension at 768 on retrieval evidence, but that
figure had never been put through a column definition or an index build. A dimension that cannot be
indexed is not a decision.

## Environment

| | |
|---|---|
| OS | Windows 11 Home 10.0.26200 |
| Container runtime | Docker Desktop, Linux engine, server 29.7.2 (linux/amd64), Compose 5.5.1 |
| Datastore image | `pgvector/pgvector:pg17`, digest `sha256:cf134a767f474095eeba57e0117be8e568e011a63f33fbf252f14c9b760f8e6f`, pgvector 0.8.6 |
| Inference runtime | Ollama 0.33.3, host install, default binding `127.0.0.1:11434` |

## Method

One script, [`artifacts/reachability_check.sh`](artifacts/reachability_check.sh), covering both
questions and removing the container it starts on exit.

**Question 1.** A throwaway `alpine/curl` container issues `GET /api/tags` against
`host.docker.internal:11434` and the HTTP status is recorded. The probe was run twice, once with
Ollama on its default loopback binding and once with `OLLAMA_HOST=0.0.0.0:11434`, so that the
default configuration is measured rather than assumed. Where `host.docker.internal` resolved to was
recorded in both cases.

**Question 2.** A `pgvector/pgvector:pg17` container is started, then, in order: the extension is
created and its version read; a table with a `vector(768)` column is created; an HNSW index with
`vector_cosine_ops` is built over it; two rows are inserted, one a constant vector and one random,
and a nearest-neighbour query is issued against the first; and the on-disk size of one vector is
read with `pg_column_size`.

The second row exists so the ordering means something. A nearest-neighbour query against a
single-row table returns that row whether or not the operator works.

## Results

```
--- 1. container to host inference
  PASS  container reached host.docker.internal:11434 (HTTP 200)

--- 2. datastore with a 768-dimension vector
  PASS  pgvector 0.8.6 available
  PASS  vector(768) column accepted
  PASS  HNSW cosine index built over 768 dimensions
  PASS  nearest-neighbour query returns the expected row
  storage: 3076 bytes per 768-dimension vector

5 passed, 0 failed
```

Five of five, with Ollama on its default binding. Raw log:
[`artifacts/run-log-g4-2026-09-09.txt`](artifacts/run-log-g4-2026-09-09.txt).

| Configuration | Host listener | Container to `host.docker.internal:11434` |
|---|---|---|
| Ollama default | `127.0.0.1:11434` | HTTP 200 |
| `OLLAMA_HOST=0.0.0.0:11434` | `0.0.0.0:11434` | HTTP 200 |

## Findings

**1. The anticipated impediment does not occur on Docker Desktop, and the reasoning behind it was
wrong.** Inside a container, `host.docker.internal` resolves to `fdc4:f303:9324::254`, an address
belonging to Docker Desktop's own host proxy rather than to the host's network interfaces. The proxy
terminates the connection and forwards it to the host, loopback included. The container is therefore
never a peer on the host's network in the way R-09 assumed, and a loopback-bound service is
reachable. It works without `--add-host=host.docker.internal:host-gateway`, which the script passes
anyway for portability.

**2. Ollama stays on loopback, which is the better security position.** The mitigation R-09
anticipated was `OLLAMA_HOST=0.0.0.0` plus a firewall rule scoping the port. That binding exposes an
unauthenticated API that can load models and run generation to every host the firewall permits, and
a firewall rule is the only thing standing in front of it. Not needing it removes a control that
would have had to be documented, justified in NOVA-TM-001, and correctly reproduced by anyone
cloning the repository. The deployment view's claim that services carry no inbound surface beyond
the host holds for the inference runtime as written.

**3. The finding is specific to Docker Desktop, and this is the part that will bite someone else.**
A Linux-native Docker Engine has no host proxy. There, `host.docker.internal` is undefined unless
declared, and `host-gateway` maps to the bridge address, which a loopback-bound service does not
answer on. The remediation R-09 described remains correct for that case, so the script retains it as
its failure message rather than dropping it. What was measured is this platform, not the general
case.

**4. 768 dimensions survives contact with the schema.** The column type is accepted, the HNSW cosine
index builds over it, and the ordering is correct. ADR-0005 can move from a retrieval argument to a
migration.

**5. A 768-dimension vector costs 3076 bytes.** Four bytes per dimension plus a four-byte header,
which is `pgvector`'s uncompressed `vector` type behaving exactly as documented. At the retention
volumes in NOVA-SRS-001 the embedding column is not a capacity concern, and the arithmetic is now
recorded rather than estimated.

**6. The check found one defect, in itself.** The nearest-neighbour insert used a correlated
reference inside `array_agg`, which PostgreSQL rejects as an aggregate over the outer query. The
first run failed there while the four checks around it passed. A verification script that has never
run is not evidence, which is the argument for running it before the deployment work rather than
alongside it.

## Limitations

1. One platform, one run. Docker Desktop on Windows 11 with the Linux engine. Neither Docker Engine
   on Linux nor Podman was tested, and finding 3 is reasoning about them, not measurement.
2. The reachability probe is `GET /api/tags`. It proves the HTTP path, not that a generation request
   under load behaves, and says nothing about latency across the proxy.
3. Docker Desktop updated itself from Compose 5.4.0 to 5.5.1 during the session, which is a reminder
   that the runtime version under this finding moves without being asked.
4. The datastore ran with default configuration and a throwaway container, no named volume, no
   tuning, no restart. Persistence across container replacement is the deployment composition's
   problem and is not evidence from this run.
5. The index was built over two rows. That exercises the type and the operator, not recall or build
   time at any realistic row count.
6. `pg_column_size` reports the stored attribute, not the index's own footprint.

## Follow-up

| # | Action | Why |
|---|---|---|
| 1 | Write the deployment composition against a loopback-bound inference runtime | The default configuration is now the verified one |
| 2 | Record the Linux-engine caveat in the deployment documentation | Finding 3. The first person to clone this on Linux hits it, and the script's failure message is the only place it currently lives |
| 3 | Pin the datastore image by digest in the composition | The digest is recorded here; drift is silent otherwise |
| 4 | Re-measure HNSW build time and recall at a realistic memory count | Finding limitation 5. Belongs with the M3 memory work, not here |

## Reproducing it

Requires a running container runtime and Ollama on the host. Nothing is left running.

```bash
bash docs/spikes/artifacts/reachability_check.sh
```

`PG_IMAGE` and `OLLAMA_PORT` are overridable. The script exits non-zero if any check fails.

---

## Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0 | 2026-09-09 | Laxmi Poudel | Initial report. G4 closed, R-09 closed |
