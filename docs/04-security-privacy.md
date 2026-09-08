# Security and privacy

| | |
|---|---|
| Status | Proposed |
| Scope | Local, single user, synthetic data |
| Updated | 2026-09-07 |

Controls are split into what gets built now and what a production version would need. Claiming
production-grade security for a local portfolio app would be its own credibility problem.

## Assets

| Asset | Sensitivity | Why |
|---|---|---|
| Requirement text | Medium, high with real data | May describe unreleased functionality |
| Stored memories | High | They shape all future output, and a compromised one persists |
| Execution traces | Medium | Contain prompt context and retrieved memory content |
| Feedback events | Medium | The learning substrate. Corrupt them and the derived scores go with them |
| Prompt and config versions | High | Control system behaviour directly |
| Cloud provider API keys | High | Financial and exfiltration exposure |
| Golden dataset | Low | Public by design |

## Threats

| ID | Threat | Vector | Mitigation |
|---|---|---|---|
| T1 | Prompt injection via requirement | Untrusted requirement text | Delimited and labelled untrusted blocks, constrained decoding bounding the output shape, output validation, adversarial suite |
| T2 | Persistent injection via memory | Correction text becomes a confirmed memory, replayed forever | Instruction-shape screen, length bound, mandatory human confirmation. Memory content delimited on injection. Tested explicitly |
| T3 | Feedback poisoning | Adversarial feedback bursts | Bounded step, clamped range, minimum observations, per-tenant scores, scores recomputable from events |
| T4 | Cross-tenant leakage | Missing scope filter, insecure direct object reference | Repository-layer scoping by construction, server-side `tenant_id` resolution, isolation tests as an unconditional CI gate |
| T5 | Exfiltration via provider switch | Silent switch to a cloud provider | Explicit user action only, never an automatic fallback, active provider visible in the UI |
| T6 | Secret leakage | Keys in code, logs, or the repo | `.env` git-ignored, never logged, secret scanning in CI |
| T7 | Content leaking through logs | Content written to logs | Ids and hashes by default. Content logging is opt-in debug only, asserted by test |
| T8 | Malicious dependency | Supply chain | Pinned versions with a lockfile, automated dependency updates, audit in CI |
| T9 | Resource exhaustion | Oversized requirement, runaway retries | Input length caps, bounded retries, job attempt limits, context budget guard |
| T10 | XSS via rendered model output | Output containing markup | Framework escaping by default, no unsanitized raw HTML. If Markdown rendering gets added it needs a sanitizer, and that's the likeliest place this rule gets broken later |

T2 and T4 matter most. T2 because it's architecturally novel and most projects in this space haven't
thought about it. T4 because the whole tenant-readiness claim evaporates if it fails once.

## Injection defences

Layered, none trusted alone:

1. Structural separation. Untrusted content in explicitly delimited, labelled blocks. System
   instructions never string-concatenated with user text
2. Constrained decoding. Output shape is fixed by schema, so injected free-text instructions have
   nowhere to land in the output
3. Output validation. Schema conformance plus semantic checks before anything is stored or rendered
4. Instruction-shape screening on memory candidates
5. Human confirmation on every memory write
6. No tool surface. No shell, no filesystem, no arbitrary network. A successful injection can produce
   bad test cases, but it can't take an action, because there are no actions. This is the strongest
   item on the list and it comes from the architecture, not a filter
7. Adversarial regression suite in CI

Prompt injection isn't solved by anyone. These layers reduce blast radius, they don't eliminate the
class. The meaningful claim is architectural: the agent has no capability to misuse. Not that the
filters are complete.

The intended prompt structure got exercised once already in the model spike, where the requirement
was wrapped in `<requirement>` tags with an explicit note that content inside is data and must not be
followed. That shows the shape works with constrained decoding. It doesn't show it resists attack,
which is what the adversarial suite is for.

## Permissions

| Principal | Can do |
|---|---|
| Web UI | Only what the API exposes. No direct database access |
| API service | Database read/write scoped to its tables, plus the LLM gateway |
| Worker | Same database scope, plus the gateway. No inbound network surface |
| The model | No tools. Generates text into a schema. Can't read files, run commands, or make network calls |
| Evaluation harness | Separate database. Never touches user data |

"The agent has no tools" is a posture, not a missing feature. Adding tools later (test execution,
repo reads) would need a permission model, sandboxing, and an approval flow, which is exactly why
those are post-MVP.

## Validation

| Boundary | Validation |
|---|---|
| API inbound | Pydantic models, length caps, enum constraints, unknown fields rejected |
| Requirement text | Length cap tied to the context budget, encoding normalization |
| Correction text | Length cap, instruction-shape screen |
| Model output | JSON Schema conformance, semantic checks, referential integrity of AC links |
| Memory content | Validation checks before proposal, human gate before storage |
| Rendered output | Framework escaping, no raw HTML injection |
| Database | Parameterized queries only, no string-built SQL |

## Privacy

The MVP uses synthetic and open-source data only, so this is designed and tested rather than
compliance-bound. Worth stating rather than implying a compliance posture that doesn't exist.

| Control | Now | Production would add |
|---|---|---|
| Content in logs | Ids and hashes only, asserted by test | Structured redaction pipeline |
| Local inference default | Yes, the strongest privacy control available | Same, plus egress policy enforcement |
| Data export | Full JSON memory export | Complete data-subject export |
| Deletion | Content purge plus tombstone | Verified cascade deletion with certification |
| PII detection | Not built. Documented gap | Detection with redaction before storage |
| Encryption at rest | Not implemented | Volume encryption plus column-level for sensitive fields |

The gap is named rather than hidden. "PII detection isn't implemented because this uses synthetic
data, and here's where it would go" beats a half-built detector giving false confidence.

If real data ever enters, PII detection stops being a documented gap and becomes a requirement.

## Tenant isolation

The one guarantee I'm not willing to soften.

- `tenant_id` on every user-owned table
- The repository layer scopes every query, so isolation is structural rather than something each
  caller has to remember
- `tenant_id` resolved server-side, never read from a request body or header
- No endpoint returns an object without a scope check
- Isolation tests are an unconditional CI gate from the moment memory exists, before there's ever a
  second user, because the test is what keeps the guarantee true as the code grows
- With real auth later, add Postgres row-level security as defence in depth

## Secrets

`.env` git-ignored with a committed `.env.example` carrying placeholders. No secrets in Compose
files or CI logs. Secret scanning on. Local-first means the default config needs no secrets at all,
which is a nice property.

## Reliability

| Concern | Approach |
|---|---|
| Model call failure | Bounded retry with exponential backoff and jitter, every attempt recorded |
| Schema violation | Bounded repair-retry, counted against the validity metric |
| Job failure | Bounded attempts, then terminal failure with cause. Partial trace kept |
| Worker crash | Lease expiry, then reclaim by another worker |
| Task creation | Idempotency key, replay returns the original task |
| Feedback | Idempotent by client event id |
| Score updates | Derived from events, recomputable |
| Database unavailable | Fail fast with 503, no partial writes |

No infinite retries anywhere. Every retry loop has a bound and a terminal state.

## Degraded modes

| Failure | Behaviour |
|---|---|
| Ollama down | Task creation still accepted and queued, readiness reports unhealthy, existing results browsable, error names the fix rather than a generic 500 |
| Embedding model down | Retrieval fails loudly rather than silently returning nothing. A silent empty retrieval is the worst option available, because the system looks fine while quietly not learning |
| Critic model fails | Deterministic verdicts still returned, flagged partial |
| Memory extraction fails | Raw correction stored for later extraction, nothing lost |
| Worker down | Tasks queue, UI shows a queued state instead of a spinner implying progress |
| Postgres down | Whole system down. Fine for a local app, and documented |

## Audit

Append-only and immutable: feedback events, trace steps, task status transitions, memory lifecycle
(create, confirm, edit, supersede, delete with actor and timestamp), and config version promotions
with the linked evaluation run.

Memory tombstones are the interesting case. A deleted memory keeps its id, timestamps, and tenant so
old traces stay coherent, while the content is purged. That satisfies both auditability and
deletion.

## Human gates

| Gate | Blocks | Why |
|---|---|---|
| Memory confirmation | Anything entering long-term memory unconfirmed | Stops wrong or injected rules persisting and being replayed |
| Conflict resolution | A contradicting memory being stored silently | The user owns which rule wins, the system doesn't guess |
| Prompt/config promotion | Promotion without an evaluation pass and an explicit action | Stops silent degradation and makes the change auditable |
| Provider switch | Automatic switching | Switching providers changes where data goes. That's a decision, not a fallback |

Each exists because the alternative is silent, unreviewable change, which is the failure mode that
makes systems claiming to learn untrustworthy.

## Supply chain

Pinned versions with a lockfile, automated dependency alerts, dependency audit in CI, base images
pinned by digest. Minimal dependency count on purpose: every dependency not added is an attack
surface not acquired, which is the same argument as the engineering one.

## Backup and restore

`pg_dump` on demand, documented in the README, plus a restore drill run at least once. An untested
backup isn't a backup. Compose volumes are named and documented. Production would add scheduled
backups, offsite retention, and point-in-time recovery.

## Abuse cases

| Abuse | Handling |
|---|---|
| Generating test cases for malicious software | Out of scope for a local single-user tool. No content moderation is claimed |
| Flooding memory with junk | Per-tenant cap, archival, duplicate detection |
| Extracting another user's memories | T4 defences |
| Draining a cloud API budget | Cloud is opt-in and explicit, rate-limiting seam documented |
| Reconstructing deleted memories from traces | Tombstones purge content, traces store hashes not prompt text |

## Now vs production

| Control | Now | Production |
|---|---|---|
| Authentication | Stubbed single user | OIDC or session auth, MFA |
| Authorization | Repository scoping | Plus Postgres row-level security |
| Rate limiting | Documented, seam in place | Enforced per-tenant token bucket |
| PII | Not detected, documented gap | Detection and redaction pipeline |
| Encryption at rest | None | Volume and column-level |
| Secrets | `.env` | Vault or a cloud secret manager |
| Audit | App-level append-only | Plus tamper-evident storage |
| Backup | Manual, drilled once | Scheduled, offsite, point-in-time recovery |
| Monitoring | Local traces | Alerting, service objectives, on-call |

Knowing the difference between a portfolio MVP and a production system, and drawing the line
explicitly, is more useful than pretending the gap isn't there.

## Environment notes

| Note | Detail |
|---|---|
| Service binding | Bind to `127.0.0.1` only. No reason to expose a local single-user app to the LAN |
| Host inference | Ollama runs on the Windows host, not in a container. GPU passthrough on Windows adds friction that buys nothing here, and the container-to-host networking path needs verifying and documenting |
| GPU contention | Norton holds GPU memory on this machine, so usable VRAM is under 6 GB. Recorded so measurements taken here make sense elsewhere |

## Open questions

| ID | Question | Going with |
|---|---|---|
| S-01 | Is prompt hashing in traces enough for real debugging, or is an opt-in content mode needed? | Hash by default, add an explicit debug mode rather than loosening the default |
| S-02 | What's the per-tenant memory cap? | Set once memory growth over real usage is visible |
| S-03 | Should the instruction-shape screen be a denylist, a classifier, or both? | Denylist plus length bound to start. The human gate carries the residual risk |
