# Risk register

Updated 2026-09-07.

Severity is about impact on the core claim, not just schedule.

## Open

| ID | Risk | Severity | Milestone | Mitigation |
|---|---|---|---|---|
| R-01 | Corrections don't extract into reusable rules well enough. A local model may produce candidates that are overbroad, trivial, or wrong often enough that the confirmation step becomes tedious instead of reassuring | High | M3 | Measure precision on ~15 hand-labelled real corrections at the mid-milestone checkpoint, before building the UI around it. Fallback is user-authored rules with model assistance. Biggest unknown in the project |
| R-02 | Dataset construction is underestimated. ~50 stratified cases with precise expected properties is 15 to 25 hours of authoring on the critical path | High | M5 | Start seeding from M2. The 20 spike requirements already exist and drop straight in, which removes roughly a third of the effort |
| R-03 | Model nondeterminism exceeds gate margins and the evaluation gate flaps. A flapping gate gets disabled, and a disabled gate is worse than none because it looks like protection | High | M5 | Measure run-to-run variance before setting any threshold. If variance is too high, grow the dataset rather than loosening thresholds |
| R-04 | Embedding model and dimension are unchosen, and the dimension goes into the schema. Changing it later means re-embedding everything | High | M1 | Dedicated spike before any schema work. Treat as a blocking prerequisite |
| R-05 | Correction recurrence rate depends on a "structurally similar" threshold that's genuinely hard to defend. The headline metric is only as good as that choice | Medium | M5 | Fix it from measured distributions, document it, freeze it, and always report it next to retrieval precision so "retrieved and ignored" is distinguishable from "never retrieved" |
| R-06 | At 10 hrs/week the plan is over budget | Medium | Week 6 | Cut order is decided. Decide in week 6, not week 12 |
| R-07 | Pressure to fill placeholders with optimistic numbers peaks in the last milestone, when the work is nearly done | Medium | M7 | Claim rules are written down. Re-read them at the start of M7. A placeholder that can't be filled becomes a removed claim, not a softened one |
| R-08 | The 8B class may not fit on 6 GB at all, and it was never measured | Medium | M1 | Both candidates are on disk. Measure residency and offload split. If 8B needs CPU offload, the latency cost decides it |
| R-09 | Container-to-host Ollama networking on Windows is unverified and is the likeliest early time sink. Anyone cloning the repo hits it too | Medium | M1 | Budget half a day, document the fix in the README. Docker daemon isn't currently running |
| R-10 | Local model quality misses the 60% acceptance target | Medium | M5 | Revise the target openly. Targets are drafts and moving them is expected, but it gets recorded rather than quietly edited |
| R-11 | Persistent-injection defences are unproven. The threat is novel enough that the adversarial suite is the only evidence | Medium | M5 | Treat the suite as a floor, not a guarantee, and say so. The no-tool-surface property carries most of the real protection |
| R-12 | Deterministic checks may not capture enough quality to gate on. Both AC coverage and required case-type presence rely on the model's own labelling | Medium | M5 | Hand-audit a sample of plans and report the agreement rate. If the checks are weak, increase the LLM-judge share and document the caveat |
| R-13 | The critic pass may not earn its latency. It adds a second model call to every task | Low | M5 | Built to be removable. Measure before and after on the golden set, cut it if it doesn't help |
| R-14 | Exploratory runs look like random degradation to someone who doesn't know exploration happened | Low | M4 | Label exploration in the UI |
| R-15 | Entity count is high for the hour budget. Several entities are thin, but each still needs a migration, a repository, and tests | Low | M2 to M3 | Budgeted honestly rather than assumed free |
| R-16 | Adding tools later invalidates the security model. The no-tool-surface property is load-bearing for the whole security story | Low | Future | Written down now so it isn't forgotten. Any tool addition means rewriting the security doc, not amending it |
| R-17 | No external code review. Every design and security decision has exactly one reviewer | Low | Throughout | Accepted. CI gates substitute where they can, and the limitation gets stated rather than hidden |
| R-18 | GPU contention on this machine. Norton holds GPU memory, so usable VRAM is under 6 GB | Low | Throughout | Recorded so measurements taken here make sense elsewhere. Not actioned |

## Closed

| ID | Risk | Outcome |
|---|---|---|
| R-C1 | Hardware can't sustain a local model at usable latency and schema fidelity. This was the one that could have invalidated the workflow decision | Closed by measurement, 2026-09-07. 4B-class models: 12 of 12 schema-valid first attempt, 2.9 to 3.9 GB resident, 100% GPU offload, 9 to 26 s warm generation. Well inside the draft latency target |
| R-C2 | The 8 GB+ VRAM figure in planning was wrong | Closed. Actual card is 6 GB. Found before writing any code, so it cost an afternoon instead of a rewrite in week 9. Candidate list rewritten and the constraint corrected across the docs |

## How this gets used

Risks get reviewed at milestone boundaries, not continuously. A risk closes when evidence closes it.
A planned mitigation doesn't close a risk, and neither does time passing.

R-01 and R-04 are prerequisites rather than ordinary risks. Work that depends on them shouldn't start
until they're resolved, because being wrong costs rework rather than delay.
