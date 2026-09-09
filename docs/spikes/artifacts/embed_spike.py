"""Embedding spike: which local embedding model, and which vector dimension, for memory retrieval?

The dimension becomes a fixed column type at schema creation (ADR-0005), so this measures, per
candidate:
  - output dimension
  - embed latency, cold load separated from warm calls, because it sits on the synchronous path
  - resident size and GPU/CPU split reported by `ollama ps` (shares 6 GB with the generation model)
  - retrieval quality against hand-labelled requirement-to-memory pairs, unfiltered and with the
    production type filter (FR-4.1) applied
  - the same quality at truncated dimensions, since a shorter vector is a cheaper column

A BM25 baseline runs alongside, because ADR-0005 lists lexical retrieval as a considered option and
it should be closed with a measurement rather than an assertion.

Usage:  py -3 embed_spike.py nomic-embed-text bge-m3 ...
        py -3 embed_spike.py --selftest
"""
from __future__ import annotations

import json, math, os, re, subprocess, sys, time
from collections import Counter
from pathlib import Path

import requests

HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
HERE = Path(__file__).parent
TIMEOUT = 300
TRUNC_DIMS = [256, 512, 768]
GEN_MODEL = os.environ.get("NOVA_GEN_MODEL", "gemma3:4b")  # for the co-residency check

# Documented task prefixes. Asymmetric retrieval models score materially worse without them, so
# omitting them would measure the harness rather than the model.
PREFIX: dict[str, tuple[str, str]] = {  # model -> (query prefix, document prefix)
    "nomic-embed-text": ("search_query: ", "search_document: "),
    "embeddinggemma": ("task: search result | query: ", "title: none | text: "),
    "mxbai-embed-large": ("Represent this sentence for searching relevant passages: ", ""),
}


def prefixes(model: str) -> tuple[str, str]:
    return PREFIX.get(model.split(":")[0], ("", ""))


# --- retrieval maths -------------------------------------------------------------------------
def normalize(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def truncate(v: list[float], d: int) -> list[float]:
    return normalize(v[:d])


_WORD = re.compile(r"[a-z0-9]+")


def tokens(s: str) -> list[str]:
    return _WORD.findall(s.lower())


def bm25_scores(query: str, docs: list[str], k1: float = 1.5, b: float = 0.75) -> list[float]:
    """Okapi BM25 over a corpus this small needs no dependency."""
    toks = [tokens(d) for d in docs]
    n, avgdl = len(docs), (sum(len(t) for t in toks) / len(docs) if docs else 0.0)
    df = Counter(w for t in toks for w in set(t))
    out = []
    for t in toks:
        tf, dl, s = Counter(t), len(t), 0.0
        for w in tokens(query):
            if w not in tf:
                continue
            idf = math.log(1 + (n - df[w] + 0.5) / (df[w] + 0.5))
            s += idf * tf[w] * (k1 + 1) / (tf[w] + k1 * (1 - b + b * dl / (avgdl or 1)))
        out.append(s)
    return out


def rank_metrics(ranked: list[str], relevant: set[str], k: int = 5) -> dict:
    """ranked: candidate ids best-first. Recall is capped at k by construction, so it is reported
    beside precision and reciprocal rank rather than alone."""
    top = ranked[:k]
    hits = [i for i, c in enumerate(ranked) if c in relevant]
    return {
        "recall_at_k": len(set(top) & relevant) / len(relevant) if relevant else 0.0,
        "precision_at_k": len(set(top) & relevant) / k if k else 0.0,
        "rr": 1.0 / (hits[0] + 1) if hits else 0.0,
        "hit_ranks": [i + 1 for i in hits],
    }


def mean(xs: list[float]) -> float | None:
    return round(sum(xs) / len(xs), 3) if xs else None


# --- corpus ----------------------------------------------------------------------------------
def query_text(req: dict) -> str:
    """What production embeds for a task: the requirement as the user submitted it."""
    return (f"{req['title']}\n{req['text']}\n"
            + "\n".join(f"{k}: {v}" for k, v in req["acs"].items()))


def load() -> tuple[list[dict], list[dict]]:
    reqs = json.loads((HERE / "requirements.json").read_text(encoding="utf-8"))
    mems = json.loads((HERE / "memories.json").read_text(encoding="utf-8"))
    known = {r["id"] for r in reqs}
    for m in mems:  # a label naming a requirement that does not exist would silently deflate recall
        unknown = set(m["applies_to"]) - known
        assert not unknown, f"{m['id']} labels unknown requirements: {sorted(unknown)}"
    return reqs, mems


def candidates(req: dict, mems: list[dict], type_filter: bool) -> list[dict]:
    if not type_filter:
        return mems
    return [m for m in mems if m["scope"] in (req["type"], "any")]


def narrow(m: dict) -> bool:
    """A memory labelled for at most two requirements. These are the discriminating pairs; a rule
    that applies to everything is retrieved correctly by accident."""
    return len(m["applies_to"]) <= 2


def universal(m: dict, reqs: list[dict]) -> bool:
    """A rule labelled for every requirement. It carries no topical hook, so semantic ranking has
    nothing to rank it by. Counted separately rather than allowed to depress every recall figure."""
    return len(m["applies_to"]) == len(reqs)


def lexical_overlap(req: dict, mem: dict) -> float:
    a, b = set(tokens(query_text(req))), set(tokens(mem["text"]))
    return len(a & b) / len(a | b) if a | b else 0.0


# --- ollama ----------------------------------------------------------------------------------
def embed(model: str, text: str) -> tuple[float, list[float]]:
    t0 = time.perf_counter()
    r = requests.post(f"{HOST}/api/embed", json={"model": model, "input": text}, timeout=TIMEOUT)
    wall = (time.perf_counter() - t0) * 1000
    r.raise_for_status()
    return wall, r.json()["embeddings"][0]


def ollama(*args: str) -> str:
    try:
        return subprocess.run(["ollama", *args], capture_output=True, text=True,
                              timeout=60).stdout.strip()
    except Exception as e:  # noqa: BLE001
        return f"(ollama {' '.join(args)} unavailable: {e})"


def run_model(model: str, reqs: list[dict], mems: list[dict]) -> dict:
    qp, dp = prefixes(model)
    ollama("stop", model)  # so the first call below is an honest cold load
    time.sleep(1)
    cold_ms, _ = embed(model, dp + "warm-up")
    ps_line = ollama("ps")

    doc_vecs, doc_ms = {}, []
    for m in mems:
        ms, v = embed(model, dp + m["text"])
        doc_ms.append(ms)
        doc_vecs[m["id"]] = normalize(v)
    q_vecs, q_ms = {}, []
    for r in reqs:
        ms, v = embed(model, qp + query_text(r))
        q_ms.append(ms)
        q_vecs[r["id"]] = normalize(v)

    dim = len(next(iter(doc_vecs.values())))
    res = {
        "model": model, "dim": dim, "prefixed": bool(qp or dp),
        "cold_load_ms": round(cold_ms), "ollama_ps": ps_line,
        "warm_ms": {"n": len(doc_ms) + len(q_ms),
                    "min": round(min(doc_ms + q_ms)), "max": round(max(doc_ms + q_ms)),
                    "mean": round(sum(doc_ms + q_ms) / len(doc_ms + q_ms), 1),
                    "mean_doc": round(sum(doc_ms) / len(doc_ms), 1),
                    "mean_query": round(sum(q_ms) / len(q_ms), 1)},
        "retrieval": {}, "per_requirement": [],
    }

    for d in [dim] + [t for t in TRUNC_DIMS if t < dim]:
        dv = {k: (v if d == dim else truncate(v, d)) for k, v in doc_vecs.items()}
        qv = {k: (v if d == dim else truncate(v, d)) for k, v in q_vecs.items()}
        for tf in (True, False):
            agg: dict[str, list[float]] = {"recall_at_k": [], "precision_at_k": [], "rr": [],
                                           "narrow_recall": [], "scoped_recall": []}
            for r in reqs:
                cand = candidates(r, mems, tf)
                ranked = [c["id"] for c in sorted(
                    cand, key=lambda c: cosine(qv[r["id"]], dv[c["id"]]), reverse=True)]
                rel = {c["id"] for c in cand if r["id"] in c["applies_to"]}
                mets = rank_metrics(ranked, rel)
                for key in ("recall_at_k", "precision_at_k", "rr"):
                    agg[key].append(mets[key])
                for key, keep in (("narrow_recall", narrow),
                                  ("scoped_recall", lambda c: not universal(c, reqs))):
                    sub = {c["id"] for c in cand if r["id"] in c["applies_to"] and keep(c)}
                    if sub:
                        agg[key].append(rank_metrics(ranked, sub)["recall_at_k"])
                if d == dim and tf:
                    res["per_requirement"].append(
                        {"id": r["id"], "top5": ranked[:5], "relevant": sorted(rel),
                         "hit_ranks": mets["hit_ranks"]})
            res["retrieval"][f"dim{d}_{'typed' if tf else 'open'}"] = {
                k: mean(v) for k, v in agg.items()}
    return res


def baseline_bm25(reqs: list[dict], mems: list[dict]) -> dict:
    out = {}
    for tf in (True, False):
        agg: dict[str, list[float]] = {"recall_at_k": [], "precision_at_k": [], "rr": [],
                                       "narrow_recall": [], "scoped_recall": []}
        for r in reqs:
            cand = candidates(r, mems, tf)
            scores = bm25_scores(query_text(r), [c["text"] for c in cand])
            ranked = [c["id"] for _, c in sorted(zip(scores, cand),
                                                 key=lambda p: p[0], reverse=True)]
            rel = {c["id"] for c in cand if r["id"] in c["applies_to"]}
            mets = rank_metrics(ranked, rel)
            for key in ("recall_at_k", "precision_at_k", "rr"):
                agg[key].append(mets[key])
            for key, keep in (("narrow_recall", narrow),
                              ("scoped_recall", lambda c: not universal(c, reqs))):
                sub = {c["id"] for c in cand if r["id"] in c["applies_to"] and keep(c)}
                if sub:
                    agg[key].append(rank_metrics(ranked, sub)["recall_at_k"])
        out[f"{'typed' if tf else 'open'}"] = {k: mean(v) for k, v in agg.items()}
    return out


def coresidency(embed_model: str) -> str:
    """Both models have to be resident at once in production. 6 GB is the whole question."""
    requests.post(f"{HOST}/api/chat", timeout=TIMEOUT, json={
        "model": GEN_MODEL, "stream": False, "options": {"num_ctx": 8192, "num_predict": 8},
        "messages": [{"role": "user", "content": "ok"}]})
    embed(embed_model, "co-residency probe")
    return ollama("ps")


def corpus_stats(reqs: list[dict], mems: list[dict]) -> dict:
    pairs = [(r, m) for m in mems for r in reqs if r["id"] in m["applies_to"]]
    ov = [lexical_overlap(r, m) for r, m in pairs]
    return {
        "requirements": len(reqs), "memories": len(mems), "labelled_pairs": len(pairs),
        "narrow_memories": sum(1 for m in mems if narrow(m)),
        "universal_memories": sum(1 for m in mems if universal(m, reqs)),
        "mean_relevant_per_requirement": round(len(pairs) / len(reqs), 2),
        "lexical_overlap_jaccard": {"mean": mean(ov), "min": round(min(ov), 3),
                                    "max": round(max(ov), 3)},
    }


def selftest() -> None:
    assert abs(cosine(normalize([3.0, 4.0]), normalize([3.0, 4.0])) - 1.0) < 1e-9
    assert abs(cosine(normalize([1.0, 0.0]), normalize([0.0, 1.0]))) < 1e-9
    assert abs(sum(x * x for x in truncate([1.0, 1.0, 5.0], 2)) - 1.0) < 1e-9

    m = rank_metrics(["a", "b", "c", "d", "e", "f"], {"c", "f"}, k=5)
    assert m["recall_at_k"] == 0.5 and m["precision_at_k"] == 0.2, m
    assert m["rr"] == 1 / 3 and m["hit_ranks"] == [3, 6], m
    assert rank_metrics(["a"], set())["rr"] == 0.0

    s = bm25_scores("cascade related records", ["cascade related records", "postal code format"])
    assert s[0] > s[1] > 0 or (s[0] > 0 and s[1] == 0), s

    r2 = [{"id": "a"}, {"id": "b"}]
    assert universal({"applies_to": ["a", "b"]}, r2) and not universal({"applies_to": ["a"]}, r2)

    reqs, mems = load()  # also asserts every label names a real requirement
    assert all(m["scope"] in {"any", "api_crud_endpoint", "auth_permission_flow", "ui_form",
                              "data_migration"} for m in mems)
    for r in reqs:  # a requirement with no labelled memory would be dead weight in every metric
        assert any(r["id"] in m["applies_to"] for m in mems), r["id"]
    print("selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest(); raise SystemExit(0)
    models = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not models:
        raise SystemExit("usage: embed_spike.py <model> [<model>...]")
    reqs, mems = load()
    stats = corpus_stats(reqs, mems)
    print(json.dumps(stats, indent=1), flush=True)
    bm25 = baseline_bm25(reqs, mems)
    print(f"bm25 baseline: {json.dumps(bm25)}", flush=True)

    out = []
    for m in models:
        print(f"\n=== {m} ===", flush=True)
        res = run_model(m, reqs, mems)
        out.append(res)
        print(f"  dim={res['dim']} prefixed={res['prefixed']} cold={res['cold_load_ms']}ms "
              f"warm mean={res['warm_ms']['mean']}ms "
              f"({res['warm_ms']['min']}-{res['warm_ms']['max']})", flush=True)
        print(f"  {res['ollama_ps']}", flush=True)
        for k, v in res["retrieval"].items():
            print(f"  {k:14} {json.dumps(v)}", flush=True)

    best = max(out, key=lambda r: r["retrieval"][f"dim{r['dim']}_typed"]["narrow_recall"] or 0)
    ps_both = coresidency(best["model"])
    print(f"\nco-residency ({GEN_MODEL} + {best['model']}):\n{ps_both}", flush=True)

    (HERE / "embed-results.json").write_text(json.dumps(
        {"corpus": stats, "bm25": bm25, "models": out,
         "coresidency": {"generation": GEN_MODEL, "embedding": best["model"], "ps": ps_both}},
        indent=1), encoding="utf-8")
    print("\nwrote embed-results.json", flush=True)
