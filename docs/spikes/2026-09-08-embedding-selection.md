# Spike Report: embedding model and vector dimension

| Field | Value |
|---|---|
| Document ID | NOVA-SPK-002 |
| Version | 1.0 |
| Status | Complete |
| Owner | Laxmi Poudel |
| Date | 2026-09-08 |
| Question | Which local embedding model, and which vector dimension, should the memory index be built on? |
| Answer | `embeddinggemma` at 768 dimensions. Best on every retrieval metric, 77 ms warm, 681 MB resident, co-resident with the generation model inside 6 GB |
| Decisions affected | ADR-0005, DL-026, DL-029, R-04 |

## Why this ran first

The dimension becomes a fixed column type the moment the first migration runs. Changing it later
means re-embedding every memory and rebuilding the index, so it is one of the few decisions here
that is expensive to reverse. ADR-0005 was recorded in proposed status specifically to stop the
choice being made implicitly by whichever migration got written first.

It blocks more than the schema. Retrieval quality is the substance of the memory capability: a weak
embedding model would make applied lessons look poor and the Correction Recurrence Rate look bad for
reasons unrelated to the memory mechanism, and that failure is easy to misattribute.

## Environment

| | |
|---|---|
| GPU | NVIDIA GeForce RTX 4050 Laptop |
| VRAM | 6141 MiB (6 GB) |
| OS | Windows 11 Home 10.0.26200 |
| Runtime | Ollama, host install, API on `127.0.0.1:11434` |
| Python | 3.12.10 |

## Method

### The corpus

Retrieval quality cannot be measured without labelled pairs, so the twenty synthetic requirements
from NOVA-SPK-001 were reused as queries and twenty-four memory rules were written against them,
each labelled with the requirements it should be retrieved for.

The rules are phrased the way a user's correction would be, not the way the requirement is. Mean
token overlap between a rule and a requirement it applies to is 0.06 Jaccard, with a maximum of
0.11, so a model ranking by shared vocabulary has little to work with. That is the point: matching a
rule to a requirement phrased differently is the capability being bought.

| | |
|---|---|
| Requirements (queries) | 20 |
| Memories (documents) | 24 |
| Labelled relevant pairs | 71 |
| Mean relevant memories per requirement | 3.55 |
| Narrow memories, labelled for at most two requirements | 17 |
| Universal memories, labelled for all twenty | 1 |

### Candidates

Five models, chosen to span the dimension range rather than to be exhaustive.

| Model | Dimension | Documented task prefixes |
|---|---|---|
| `all-minilm` | 384 | none |
| `nomic-embed-text` | 768 | `search_query:` / `search_document:` |
| `embeddinggemma` | 768 | task-prefixed query and document forms |
| `mxbai-embed-large` | 1024 | query prefix only |
| `bge-m3` | 1024 | none |

Documented prefixes are applied where the model specifies them. Omitting them would have measured
the harness rather than the model.

### What is measured

Per candidate: output dimension, cold load separated from warm per-call latency, resident size and
GPU/CPU split from `ollama ps`, and retrieval quality at the native dimension and at 256, 512, and
768 truncations with renormalization.

Retrieval is scored twice. **Typed** ranks only against memories whose scope matches the
requirement's playbook, which is what FR-4.1 specifies for production. **Open** ranks against all 24
and is the harder condition, included because the type filter would otherwise hide a weak model.

| Metric | Definition |
|---|---|
| recall@5 | Fraction of a requirement's relevant memories appearing in the top five |
| precision@5 | Fraction of the top five that are relevant |
| MRR | Reciprocal rank of the first relevant memory, averaged |
| narrow recall@5 | recall@5 counting only memories labelled for at most two requirements |
| scoped recall@5 | recall@5 excluding the one memory labelled for all twenty |

A BM25 baseline runs on the same corpus, because ADR-0005 lists lexical retrieval as a considered
option and it deserves closing with a measurement rather than an assertion. It is implemented in the
harness in about fifteen lines rather than pulled in as a dependency.

## Results

### Cost

| Model | Dim | Resident | Processor | Cold load | Warm mean | Warm range |
|---|---|---|---|---|---|---|
| `all-minilm` | 384 | 26 MB | 100% GPU | 1.0 s | 58 ms | 43 to 126 ms |
| `nomic-embed-text` | 768 | 323 MB | 100% GPU | 5.9 s | 57 ms | 44 to 127 ms |
| `embeddinggemma` | 768 | 681 MB | 100% GPU | 7.1 s | 77 ms | 60 to 200 ms |
| `mxbai-embed-large` | 1024 | 618 MB | 100% GPU | 6.0 s | 72 ms | 48 to 192 ms |
| `bge-m3` | 1024 | 664 MB | 100% GPU | 8.3 s | 99 ms | 78 to 207 ms |

n = 44 warm calls per model, one per corpus item.

### Retrieval, typed (the production configuration)

| Model | recall@5 | precision@5 | MRR | narrow | scoped |
|---|---|---|---|---|---|
| `embeddinggemma` | 0.701 | 0.50 | **0.900** | **1.000** | **0.967** |
| `bge-m3` | 0.695 | 0.49 | 0.863 | 0.850 | 0.887 |
| `nomic-embed-text` | 0.674 | 0.48 | 0.850 | 0.900 | 0.954 |
| `all-minilm` | 0.772 | 0.55 | 0.842 | 0.950 | 0.967 |
| `mxbai-embed-large` | 0.672 | 0.48 | 0.825 | 0.900 | 0.950 |
| BM25 baseline | 0.695 | 0.49 | 0.771 | 0.700 | 0.725 |

### Retrieval, open (no type filter)

| Model | recall@5 | precision@5 | MRR | narrow | scoped |
|---|---|---|---|---|---|
| `embeddinggemma` | **0.569** | **0.39** | **0.860** | **0.775** | **0.817** |
| `nomic-embed-text` | 0.488 | 0.33 | 0.728 | 0.650 | 0.704 |
| `mxbai-embed-large` | 0.482 | 0.33 | 0.629 | 0.750 | 0.692 |
| `all-minilm` | 0.477 | 0.32 | 0.724 | 0.700 | 0.692 |
| `bge-m3` | 0.401 | 0.27 | 0.651 | 0.650 | 0.579 |
| BM25 baseline | 0.389 | 0.27 | 0.571 | 0.425 | 0.454 |

### Truncation, `embeddinggemma`

| Dimension | Typed MRR | Typed scoped | Open MRR | Open scoped |
|---|---|---|---|---|
| 768 | 0.900 | 0.967 | 0.860 | 0.817 |
| 512 | 0.892 | 0.967 | 0.799 | 0.800 |
| 256 | 0.892 | 0.983 | 0.800 | 0.758 |

### Co-residency

`gemma3:4b` and `embeddinggemma` loaded together: 2.9 GB + 681 MB, both reported at 100% GPU on a
6141 MiB card.

Raw per-model output: [`artifacts/run-log-embed-2026-09-08.txt`](artifacts/run-log-embed-2026-09-08.txt).
Full result JSON including per-requirement rankings:
[`artifacts/embed-results.json`](artifacts/embed-results.json).

## Findings

**A rule that applies to everything is not retrievable by similarity, and that is correct
behaviour.** One memory in the corpus is a formatting convention with no topical content, labelled
relevant to all twenty requirements. Every model ranked it 6th to 8th for every single requirement,
so it never entered a top five. That one memory is the whole gap between recall@5 of 0.701 and
scoped recall of 0.967 for the winning model. Semantic ranking has nothing to rank a content-free
rule by, and no amount of model quality fixes it.

The design consequence is that always-apply rules must not go through the vector index at all. They
belong in an always-included prompt fragment, with the index reserved for rules that have something
to match on. Recorded as DL-029 and to be resolved before the memory entity is defined in M3.

**`embeddinggemma` leads on every metric that discriminates.** It is first on typed MRR (0.900),
first on narrow recall (1.000, meaning every narrowly-scoped rule reached the top five for every
requirement it was labelled against), and first by a wide margin on every open-mode figure. The
open-mode gap is the more trustworthy of the two, since the type filter reduces the candidate pool
to seven or eight and compresses the differences between models.

**Embeddings beat lexical retrieval, but only clearly once the type filter is removed.** With the
filter applied, BM25 matches the field on recall@5 (0.695) and is beaten mainly on ranking quality.
Without it, BM25 collapses to 0.425 narrow recall against 0.775 for `embeddinggemma`. At 0.06 mean
token overlap, that is the expected shape, and it settles the lexical-retrieval option in ADR-0005
on evidence. It also suggests that a hybrid of the two is worth measuring later rather than
assumed away.

**Model size does not predict retrieval quality on this corpus.** `all-minilm` at 23M parameters and
26 MB resident scores 0.967 typed scoped recall, matching the winner, and `bge-m3` at 567M is last
in open mode. Absent the open-mode results there would have been no defensible reason to prefer
anything larger than the smallest candidate.

**Truncation costs almost nothing in the typed configuration and something real in open mode.**
`embeddinggemma` at 256 dimensions holds typed scoped recall (0.983) but loses open-mode scoped
recall (0.758 against 0.817). Since 768 stores at 3 KB per memory and the model supports truncation,
storing the full vector keeps the shorter one available later without re-embedding, whereas storing
256 forecloses it.

**Retrieval metrics reproduce exactly.** The harness was run twice, and every retrieval figure was
identical to three decimal places both times. Embedding under a fixed model is deterministic, so
unlike generation, retrieval measurements need no variance allowance. Latency did vary between runs,
particularly cold load.

**Embedding latency is not a design constraint.** At 77 ms warm on the synchronous path, embedding
is roughly 0.5% of the 9 to 26 s generation time measured in NOVA-SPK-001.

**Where the winner still fails.** Excluding the universal rule, `embeddinggemma` left a relevant
memory outside the top five for 2 of 20 requirements, both the same rule: the field-level error
message convention, ranked 6th for the CSV upload and profile settings requirements, displaced by
the file-attachment and uniqueness rules. Both are plausible confusions rather than nonsense, which
is the failure mode to expect.

## Limitations

1. n = 20 requirements against 24 memories. Differences smaller than roughly 0.1 on any metric are
   not separable at this sample size, and several rankings here are inside that band. `bge-m3`
   scoring 1.000 narrow recall at 256 dimensions but 0.850 at its native 1024 is noise, not a
   finding.
2. The labels are one person's judgement about which rule ought to apply to which requirement, and
   that person also wrote both sides. Shared idiom between the two inflates every model's score
   equally, but there is no second labeller and no measured agreement.
3. Requirements and rules are synthetic. Authentic corrections are messier, longer, and frequently
   ambiguous about their own scope.
4. recall@5 in the typed configuration is close to meaningless: the candidate pool is seven or eight
   memories, so a top five covers most of it by construction. MRR, narrow recall, and the open-mode
   figures carry the signal.
5. The corpus contains no adversarial or poisoned memories, no near-duplicate rules, and no
   cross-tenant candidates. Retrieval under those conditions is unmeasured.
6. `all-minilm` reports a 256-token context and `mxbai-embed-large` 512. Query texts were not token
   counted, so truncation of the longer queries cannot be excluded for those two.
7. Prefix handling follows each model's documentation. Unprefixed performance was not measured, and
   for the asymmetric models it would be materially worse.
8. Cold load was measured once per model and moved substantially between the two runs (1.0 s against
   4.6 s for the same model), which reflects operating-system file caching rather than the model.
9. Retrieval was measured by cosine similarity alone. Production ranking also carries a confidence
   score and recency, so these figures are the ceiling that ranking starts from, not what the system
   will show.

## Follow-up

| # | Action | Why |
|---|---|---|
| 1 | Separate always-apply rules from retrievable ones in the memory entity | DL-029. The universal-rule finding above. Must land before the M3 schema |
| 2 | Re-measure retrieval against authentic corrections once M3 produces them | The current corpus is synthetic and self-labelled |
| 3 | Measure hybrid lexical-plus-vector ranking | BM25 matched on typed recall; the two fail differently and may combine |
| 4 | Add near-duplicate and adversarial memories to the corpus | Needed for the M5 adversarial suite regardless |
| 5 | Token-count the query texts against each model's context limit | Closes the truncation question for the two short-context candidates |
| 6 | Fold this corpus into the evaluation dataset | It is 20 requirements and 71 labelled pairs already written |

## Reproducing it

Everything is in [`artifacts/`](artifacts/): the requirement set, the labelled memory set, the
harness, the raw log, and the full result JSON.

```bash
ollama pull all-minilm && ollama pull nomic-embed-text && ollama pull embeddinggemma && ollama pull mxbai-embed-large && ollama pull bge-m3
```

```bash
py -3 artifacts/embed_spike.py all-minilm nomic-embed-text embeddinggemma mxbai-embed-large bge-m3
```

`py -3 artifacts/embed_spike.py --selftest` runs the ranking-metric and corpus-integrity self-test.
