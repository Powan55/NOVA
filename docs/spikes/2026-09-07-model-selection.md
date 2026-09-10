# Spike Report: local model selection under a 6 GB VRAM ceiling

| Field | Value |
|---|---|
| Document ID | NOVA-SPK-001 |
| Version | 1.1 |
| Status | Complete |
| Owner | Laxmi Poudel |
| Date | 2026-09-07, completed 2026-09-08 |
| Question | Can a local model hold NOVA's test plan JSON schema, on this hardware, at usable latency? |
| Answer | Yes for the 4B-parameter class. 100 of 100 schema-conformant across five candidates. `gemma3:4b` selected: 2.9 GB resident, fully GPU-offloaded, 17.3 s median. The 8B class needs 6.6 GB, spills a third onto the CPU, and buys no quality |
| Decisions affected | DL-021, DL-022, DL-023, DL-024, DL-025, R-08 |

## Why this ran first

Planning had "discrete GPU, 8 GB+ VRAM" written down as a confirmed input, and the candidate model
list was built around 9B models. If no local model could hold the schema at tolerable latency, the
whole workflow decision would have had to reopen. So this was the cheapest way to test the
assumption everything else rests on.

Good instinct, because the assumption was wrong.

## Environment

| | |
|---|---|
| GPU | NVIDIA GeForce RTX 4050 Laptop |
| VRAM | 6141 MiB (6 GB), not 8 GB+ |
| Driver | 610.62 |
| OS | Windows 11 Home 10.0.26200 |
| Runtime | Ollama 0.33.3, host install, API on `127.0.0.1:11434` |
| Python | 3.12.10 |

Norton Security Suite holds three `model_host.exe` processes on the GPU, so usable VRAM is below the
nominal 6141 MiB. Recorded so measurements taken here are comparable elsewhere.

## Method

Twenty synthetic requirements, five per playbook type (API/CRUD endpoint, auth/permission flow, UI
form, data migration), each with four acceptance criteria written to be machine-checkable. All
synthetic, so it's committable, and it doubles as the seed for the evaluation golden dataset.

A Pydantic `TestPlan` model defines the test-plan v1 schema. `TestPlan.model_json_schema()` goes
straight into Ollama's `format` parameter, which applies constrained decoding, and the same model
validates the response. That's deliberate: it tests whether one Pydantic definition can serve as
request validation, generation schema, and persistence type at once.

Settings: `temperature=0`, `seed=42`, `num_ctx=8192`, thinking disabled.

The prompt uses the intended production shape. Trusted system template carrying the playbook and its
required case types, requirement wrapped in `<requirement>` tags and explicitly labelled as untrusted
data that must not be followed as instructions.

Deterministic scoring per generation:

- Schema validity, first attempt
- AC coverage: fraction of the requirement's ACs referenced by at least one case
- Hallucinated ACs: references to AC ids that don't exist
- Required case-type presence: fraction of the playbook's mandated types that appear

The scoring functions have an assertion-based self-test, which passes.

## Results: smoke run, n=4

This was a smoke run at n=4 per model, one requirement per playbook type. The numbers are
directionally useful and statistically weak. Percentile latency at n=4 is basically min/max and
shouldn't be quoted as p50/p95. It is retained here because the full run below was designed against
what it showed.

| Model | Resident @ 8K ctx | Processor | Schema valid | AC coverage | Required types | Warm latency | Cases/plan |
|---|---|---|---|---|---|---|---|
| `qwen3:4b` | 3.9 GB | 100% GPU | 4/4 | 0.875 | 1.000 | 12.6 to 17.4 s | 4 to 6 |
| `gemma3:4b` | 2.9 GB | 100% GPU | 4/4 | 1.000 | 1.000 | 18.0 to 21.0 s | 5 to 6 |
| `phi4-mini` | 3.6 GB | 100% GPU | 4/4 | 1.000 | 0.917 | 9.4 to 25.7 s | 3 to 5 |
| `qwen3:8b` | | | not measured | | | | |
| `granite3.3:8b` | | | not measured | | | | |

Raw per-requirement output: [`artifacts/run-log-2026-09-07.txt`](artifacts/run-log-2026-09-07.txt).

Three individual results:

- `gemma3:4b` took 115.1 s on its first call. That's cold model load, not generation. Warm calls for
  the same model ran 18 to 21 s. Cold load is a real UX and evaluation-runtime cost and has to be
  excluded from latency metrics or reported separately.
- `qwen3:4b` covered only 2 of 4 acceptance criteria on the delete-user requirement, its one weak
  result. Every other generation across all three models covered all four.
- `phi4-mini` missed a required case type once, on the auth flow, at 2 of 3 types present.

## Results: full run, n=20

All twenty requirements against all five candidates, run 2026-09-08. Same harness, same settings.
Latency excludes the first call of each model, which carries the load.

| Model | Resident @ 8K ctx | Processor | Schema valid | AC coverage | Required types | Hallucinated ACs | Median | Slowest | Cases/plan |
|---|---|---|---|---|---|---|---|---|---|
| `gemma3:4b` | 2.9 GB | 100% GPU | 20/20 | **0.988** | **0.988** | 0 | 17.3 s | 24.7 s | 5.5 |
| `phi4-mini` | 3.6 GB | 100% GPU | 20/20 | 0.975 | 0.867 | 0 | 10.4 s | 16.6 s | 4.8 |
| `qwen3:4b` | 3.9 GB | 100% GPU | 20/20 | 0.900 | 0.983 | 2 | 11.2 s | 17.6 s | 4.2 |
| `qwen3:8b` | 6.6 GB | 36% CPU / 64% GPU | 20/20 | 0.988 | 0.983 | 0 | 43.6 s | 93.2 s | 4.7 |
| `granite3.3:8b` | 6.6 GB | 38% CPU / 62% GPU | 20/20 | 0.975 | 0.942 | 0 | 40.3 s | 68.8 s | 3.5 |

Cold first calls, excluded from the latency columns: 24.4 s, 14.5 s, 14.1 s, 75.1 s, 43.0 s
respectively.

Raw per-requirement output:
[`artifacts/run-log-2026-09-08-full.txt`](artifacts/run-log-2026-09-08-full.txt), with the
machine-readable form in `artifacts/results-full.json` and `artifacts/summary-full.json`.

## Findings

**The hardware assumption was wrong.** 6 GB, not 8 GB+. The original 9B candidate list isn't viable,
since a 9B at Q4 leaves effectively no KV-cache headroom on this card.

**Constrained decoding held everywhere.** 100 of 100 generations valid on first attempt, across five
models and twenty requirements, no repair retry needed anywhere. Ollama accepted the
Pydantic-generated JSON Schema including its nested `$defs`/`$ref` structure, so the
single-source-of-truth property the design leans on is real.

**4B-class fits comfortably.** 2.9 to 3.9 GB resident at 8K context with 100% GPU offload, leaving
headroom on a 6 GB card. Context budget isn't the binding constraint I expected it to be at this
model size.

**Warm latency is much better than the target, for the 4B class only.** The draft NFR was p95
≤90 s end to end. `gemma3:4b` generation alone runs at a 17.3 s median, 24.7 s slowest of nineteen.
Even adding retrieval, a critic pass, and persistence, there's a lot of margin. That target should be
tightened once the full pipeline exists, because one with this much slack doesn't constrain anything.
The 8B candidates do not share that margin: `qwen3:8b` took 93.2 s on one requirement, which is over
the whole-pipeline target on generation alone.

**The 8B class fits only by spilling onto the CPU, and gains nothing for it.** Both 8B candidates
load at 6.6 GB against 6141 MiB of VRAM, so roughly a third of each runs on the CPU. That costs 2.4
times the median latency of `gemma3:4b` and buys no quality: `qwen3:8b` ties it on AC coverage at
0.988 and is marginally behind on required case types. Paying 2.4 times for a tie settles R-08.

**Hybrid reasoning models need thinking turned off.** `qwen3` is one. Left at default, thinking
tokens dominate generation time and interact badly with constrained decoding. Required config, not
an optimization.

**Content quality is the discriminator, not structure.** Since structural validity was 100%
everywhere, model selection comes down to AC coverage, required case-type adherence, and latency.
That's a much harder thing to measure, and it's what the evaluation harness is for.

## Limitations

These numbers will get quoted later, so:

1. n=20 per model on the full run. Enough to separate the models on content quality, still thin for
   latency: with nineteen warm observations the 95th percentile is the slowest observation, which is
   why the tables report the slowest rather than a percentile estimate.
2. One hardware configuration, one run, no repeats, fixed seed. Run-to-run variance is unmeasured,
   and variance is what evaluation thresholds eventually have to come from.
4. AC coverage trusts the model's own `covers_acceptance_criteria` labelling. A case can claim an AC
   without meaningfully covering it, so the metric is an upper bound.
5. Required case-type presence trusts the model's own `case_type` tagging, same problem.
6. No duplicate-case detection. That needs embeddings, which aren't chosen yet.
7. Cold-load latency contaminates any naive percentile, and I only caught it because one outlier was
   big enough to notice.

## Where this leaves the model choice

**`gemma3:4b`.** It leads content quality on both metrics, references no acceptance-criterion ids
that don't exist, produces the most cases per plan, and has the smallest footprint at 2.9 GB, which
matters because the embedding model shares the card.

It is not the fastest. `phi4-mini` is 7 s quicker at the median but misses a required case type on
roughly one requirement in seven, and `qwen3:4b` is quicker still with the weakest AC coverage and
the only hallucinated criterion references in the run. Seven seconds against a 90 s pipeline target
does not buy back a coverage deficit, so this is quality over latency. Recorded as DL-023.

What remains unsettled is run-to-run variance: this is one pass at a fixed seed. That belongs to M5,
where the thresholds are set, and it does not hold up the choice here, because the separation between
`gemma3:4b` and the alternatives is on content quality and the alternatives are not close enough on
that to be re-ordered by noise of a plausible size.

## Follow-up

| # | Action | State |
|---|---|---|
| 1 | Run all 20 requirements against all 5 models | **Done 2026-09-08.** 100 of 100 valid. `gemma3:4b` selected |
| 2 | Measure `qwen3:8b` and `granite3.3:8b` residency and offload split | **Done 2026-09-08.** 6.6 GB, roughly a third on CPU, 2.4 times the latency, no quality gain. R-08 closed |
| 3 | Repeat runs at fixed seed to measure variance | Outstanding. Belongs to M5, where the thresholds are set |
| 4 | Separate cold load from warm generation everywhere | **Done.** Cold first calls are reported separately above |
| 5 | Spike the embedding model and fix its dimension | **Done 2026-09-08.** [NOVA-SPK-002](2026-09-08-embedding-selection.md) |
| 6 | Hand-audit case-type and AC labels on a sample of plans | Outstanding. Both metrics remain upper bounds until then |
| 7 | Verify host Ollama is reachable from inside a container | Outstanding. G4, the last M1 entry criterion |

## Reproducing it

Everything is in [`artifacts/`](artifacts/): the requirement set, the harness, the raw log.

```bash
py -3 -m pip install pydantic requests
```

```bash
py -3 artifacts/spike.py gemma3:4b phi4-mini qwen3:4b qwen3:8b granite3.3:8b
```

Set `NOVA_LIMIT=4` for the smoke run, one requirement per playbook type. `py -3 artifacts/spike.py --selftest` runs the scoring
self-test.

---

## Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0 | 2026-09-07 | Laxmi Poudel | Smoke run, three of five candidates measured. Status partial |
| 1.1 | 2026-09-08 | Laxmi Poudel | Full run across all twenty requirements and all five candidates. `gemma3:4b` selected, R-08 closed. Status complete |
