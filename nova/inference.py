"""Inference gateway: three operations over two providers (DL-010).

`generate_structured`, `generate_text`, `embed`. Nothing wider, because nothing wider is required.

The gateway does not retry. Repair retries belong to the orchestrator, which counts every attempt
against the validity metric (FR-2.2, FR-2.3); a retry hidden in here would be invisible to that.

It also never substitutes a provider. An unreachable local runtime is an error, not a reason to
reach for a hosted one (FR-11.1).

Usage:  py -3 nova/inference.py --selftest   exercise the fake, and the local runtime if it is up
        py -3 nova/inference.py --health     report readiness of the configured provider
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol

# ADR-0005. The column type is vector(768); a provider returning anything else corrupts the index
# silently, so it is checked rather than trusted.
EMBED_DIM = 768

Schema = dict[str, Any]  # a JSON Schema, passed through to constrained decoding

DEFAULT_URL = os.environ.get("NOVA_INFERENCE_URL", "http://127.0.0.1:11434")
DEFAULT_GEN_MODEL = os.environ.get("NOVA_GEN_MODEL", "gemma3:4b")
DEFAULT_EMBED_MODEL = os.environ.get("NOVA_EMBED_MODEL", "embeddinggemma")
DEFAULT_NUM_CTX = int(os.environ.get("NOVA_NUM_CTX", "8192"))
DEFAULT_TIMEOUT = int(os.environ.get("NOVA_INFERENCE_TIMEOUT", "300"))


class InferenceError(RuntimeError):
    """A gateway failure. `detail` is safe to show a user: it names the action required."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


@dataclass(frozen=True)
class Completion:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    data: dict[str, Any] | None = None  # parsed object, for generate_structured only


@dataclass(frozen=True)
class Embedding:
    vector: list[float]
    model: str
    latency_ms: int


@dataclass(frozen=True)
class Health:
    provider: str
    ready: bool
    detail: str  # actionable when not ready: names the model and how to obtain it (FR-11.4)
    models: list[str] = field(default_factory=list)


class InferenceGateway(Protocol):
    name: str

    def generate_structured(
        self, prompt: str, schema: Schema, *, system: str | None = None
    ) -> Completion: ...
    def generate_text(self, prompt: str, *, system: str | None = None) -> Completion: ...
    def embed(self, text: str) -> Embedding: ...
    def health(self) -> Health: ...


def _post(url: str, body: dict[str, Any], timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload: dict[str, Any] = json.loads(response.read())
    return payload


class OllamaGateway:
    """The local runtime, host-resident. Reached at loopback, or at host.docker.internal from a
    container (NOVA-SPK-003)."""

    name = "ollama"

    def __init__(
        self,
        url: str = DEFAULT_URL,
        gen_model: str = DEFAULT_GEN_MODEL,
        embed_model: str = DEFAULT_EMBED_MODEL,
        num_ctx: int = DEFAULT_NUM_CTX,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.url = url.rstrip("/")
        self.gen_model = gen_model
        self.embed_model = embed_model
        self.num_ctx = num_ctx
        self.timeout = timeout

    def _chat(self, prompt: str, system: str | None, schema: Schema | None) -> Completion:
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}
        ]
        body: dict[str, Any] = {
            "model": self.gen_model,
            "messages": messages,
            "stream": False,
            # Temperature and seed fixed: run-to-run variance is measured by the evaluation harness,
            # not introduced here (R-03).
            "options": {"temperature": 0, "seed": 42, "num_ctx": self.num_ctx},
        }
        if schema is not None:
            body["format"] = schema  # constrained decoding, FR-2

        started = time.perf_counter()
        try:
            payload = _post(f"{self.url}/api/chat", body, self.timeout)
        except urllib.error.HTTPError as exc:
            raise InferenceError(self._http_detail(exc, self.gen_model)) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise InferenceError(
                f"inference runtime at {self.url} is unreachable ({exc}). Start it, or set "
                f"NOVA_INFERENCE_URL to where it is running."
            ) from exc
        latency_ms = int((time.perf_counter() - started) * 1000)

        text = payload.get("message", {}).get("content", "")
        data = None
        if schema is not None:
            try:
                data = json.loads(text)
            except json.JSONDecodeError as exc:
                # Constrained decoding should make this impossible. If it happens the caller needs
                # to see it as a generation failure, not as an empty result.
                raise InferenceError(f"{self.gen_model} returned output that is not JSON: {exc}") from exc

        return Completion(
            text=text,
            model=self.gen_model,
            prompt_tokens=payload.get("prompt_eval_count", 0),
            completion_tokens=payload.get("eval_count", 0),
            latency_ms=latency_ms,
            data=data,
        )

    def generate_structured(self, prompt: str, schema: Schema, *, system: str | None = None) -> Completion:
        return self._chat(prompt, system, schema)

    def generate_text(self, prompt: str, *, system: str | None = None) -> Completion:
        return self._chat(prompt, system, None)

    def embed(self, text: str) -> Embedding:
        started = time.perf_counter()
        try:
            payload = _post(
                f"{self.url}/api/embed", {"model": self.embed_model, "input": text}, self.timeout
            )
        except urllib.error.HTTPError as exc:
            raise InferenceError(self._http_detail(exc, self.embed_model)) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise InferenceError(f"inference runtime at {self.url} is unreachable ({exc}).") from exc

        vector = (payload.get("embeddings") or [[]])[0]
        if len(vector) != EMBED_DIM:
            raise InferenceError(
                f"{self.embed_model} returned {len(vector)} dimensions, but the schema is "
                f"vector({EMBED_DIM}) per ADR-0005. Changing the embedding model requires a "
                f"migration and a re-embedding of every memory."
            )
        latency_ms = int((time.perf_counter() - started) * 1000)
        return Embedding(vector=vector, model=self.embed_model, latency_ms=latency_ms)

    def _http_detail(self, exc: urllib.error.HTTPError, model: str) -> str:
        if exc.code == 404:  # FR-11.4: name the model and the action required
            return f"model '{model}' is not installed on {self.url}. Run: ollama pull {model}"
        return f"inference runtime returned HTTP {exc.code} for model '{model}'"

    def health(self) -> Health:
        try:
            with urllib.request.urlopen(f"{self.url}/api/tags", timeout=5) as response:
                installed = [m["name"] for m in json.loads(response.read()).get("models", [])]
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return Health(self.name, False, f"inference runtime at {self.url} is unreachable ({exc}).")

        # Ollama reports names tagged; a bare name in configuration means the :latest tag.
        present = {n.removesuffix(":latest") for n in installed}
        missing = [m for m in (self.gen_model, self.embed_model) if m.removesuffix(":latest") not in present]
        if missing:
            pulls = "; ".join(f"ollama pull {m}" for m in missing)
            detail = f"model(s) not installed: {', '.join(missing)}. Run: {pulls}"
            return Health(self.name, False, detail, installed)
        ready = f"{self.url} ready with {self.gen_model} and {self.embed_model}"
        return Health(self.name, True, ready, installed)


class FakeGateway:
    """Deterministic, no network. Integration tests must be fast and repeatable (DL-019).

    Model behaviour is the evaluation sub-process's problem, not integration testing's, so this
    makes no attempt to be plausible. `queue` seeds an exact response, `fail_next` an error path;
    without either, structured generation returns the minimal instance of the supplied schema.
    """

    name = "fake"

    def __init__(self, gen_model: str = "fake-gen", embed_model: str = "fake-embed") -> None:
        self.gen_model = gen_model
        self.embed_model = embed_model
        self.calls: list[tuple[str, str]] = []  # (operation, prompt) in order, for assertions
        self._queued: list[Any] = []
        self._failure: str | None = None

    def queue(self, value: Any) -> None:
        """Seed the next generation result: a dict for structured, a string for text."""
        self._queued.append(value)

    def fail_next(self, detail: str = "seeded failure") -> None:
        self._failure = detail

    def _check_failure(self) -> None:
        if self._failure is not None:
            detail, self._failure = self._failure, None
            raise InferenceError(detail)

    def generate_structured(self, prompt: str, schema: Schema, *, system: str | None = None) -> Completion:
        self.calls.append(("generate_structured", prompt))
        self._check_failure()
        data = self._queued.pop(0) if self._queued else stub_from_schema(schema)
        text = json.dumps(data)
        return Completion(text, self.gen_model, _tokens(prompt), _tokens(text), 1, data)

    def generate_text(self, prompt: str, *, system: str | None = None) -> Completion:
        self.calls.append(("generate_text", prompt))
        self._check_failure()
        text = self._queued.pop(0) if self._queued else f"fake completion for {_tokens(prompt)} tokens"
        return Completion(text, self.gen_model, _tokens(prompt), _tokens(text), 1)

    def embed(self, text: str) -> Embedding:
        self.calls.append(("embed", text))
        self._check_failure()
        return Embedding(_pseudo_vector(text), self.embed_model, 1)

    def health(self) -> Health:
        return Health(self.name, True, "fake provider, no runtime required")


def _tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _pseudo_vector(text: str) -> list[float]:
    """A stable unit vector per input. Deterministic, not semantic: nearest-neighbour ordering
    under this provider is meaningless by design, so no test can accidentally assert on it."""
    seed = hashlib.sha256(text.encode()).digest()
    raw = [(seed[i % len(seed)] ^ (i * 31 % 256)) / 255.0 - 0.5 for i in range(EMBED_DIM)]
    norm = math.sqrt(sum(v * v for v in raw)) or 1.0
    return [v / norm for v in raw]


def stub_from_schema(schema: Schema) -> Any:
    """The minimal instance satisfying a JSON Schema: required properties, minItems, first enum."""
    if "enum" in schema:
        return schema["enum"][0]
    kind = schema.get("type")
    if kind == "object":
        properties = schema.get("properties", {})
        required = schema.get("required") or list(properties)
        return {name: stub_from_schema(properties[name]) for name in required if name in properties}
    if kind == "array":
        return [stub_from_schema(schema.get("items", {})) for _ in range(max(1, schema.get("minItems", 1)))]
    return {"string": "stub", "integer": 0, "number": 0.0, "boolean": False}.get(str(kind))


def gateway_from_env() -> InferenceGateway:
    """Local by default (FR-11). Selecting anything else is an explicit act, never a fallback."""
    provider = os.environ.get("NOVA_INFERENCE_PROVIDER", "ollama").lower()
    if provider == "ollama":
        return OllamaGateway()
    if provider == "fake":
        return FakeGateway()
    raise InferenceError(
        f"unknown inference provider '{provider}'. Set NOVA_INFERENCE_PROVIDER to ollama or fake."
    )


def selftest() -> None:
    fake = FakeGateway()

    schema = {
        "type": "object",
        "required": ["summary", "cases"],
        "properties": {
            "summary": {"type": "string"},
            "count": {"type": "integer"},
            "cases": {
                "type": "array",
                "minItems": 2,
                "items": {
                    "type": "object",
                    "properties": {"title": {"type": "string"}, "priority": {"enum": ["P0", "P1"]}},
                },
            },
        },
    }
    result = fake.generate_structured("a requirement", schema)
    assert result.data == {
        "summary": "stub",
        "cases": [{"title": "stub", "priority": "P0"}, {"title": "stub", "priority": "P0"}],
    }, result.data
    assert "count" not in result.data, "optional property should not appear in the minimal instance"
    assert result.data["cases"][0] is not result.data["cases"][1], "array items must not be aliased"
    assert json.loads(result.text) == result.data
    assert result.prompt_tokens > 0 and result.completion_tokens > 0

    fake.queue({"summary": "seeded", "cases": []})
    assert fake.generate_structured("x", schema).data == {"summary": "seeded", "cases": []}

    fake.fail_next("runtime down")
    try:
        fake.generate_text("x")
    except InferenceError as exc:
        assert exc.detail == "runtime down"
    else:
        raise AssertionError("fail_next did not raise")
    assert fake.generate_text("x").text, "failure should be consumed, not sticky"

    first = fake.embed("boundary cases are P0")
    assert len(first.vector) == EMBED_DIM
    assert first.vector == fake.embed("boundary cases are P0").vector, "embedding is not deterministic"
    assert first.vector != fake.embed("something else").vector
    assert abs(math.sqrt(sum(v * v for v in first.vector)) - 1.0) < 1e-9, "not a unit vector"

    assert [c[0] for c in fake.calls].count("embed") == 3
    assert fake.health().ready

    # No automatic substitution: an unreachable runtime raises rather than degrading to the fake.
    unreachable = OllamaGateway(url="http://127.0.0.1:1")
    assert not unreachable.health().ready
    try:
        unreachable.generate_text("x")
    except InferenceError as exc:
        assert "unreachable" in exc.detail
    else:
        raise AssertionError("an unreachable runtime did not raise")

    print("selftest ok: fake provider, schema stub, determinism, no silent substitution")

    live = OllamaGateway().health()
    if live.ready:
        gateway = OllamaGateway()
        plan = gateway.generate_structured("Write a test plan for a password reset endpoint.", schema)
        assert isinstance(plan.data, dict) and plan.data.get("summary")
        vector = gateway.embed("boundary cases are P0")
        print(
            f"live ok: {plan.model} {plan.prompt_tokens}+{plan.completion_tokens} tokens in "
            f"{plan.latency_ms} ms, {vector.model} {len(vector.vector)} dims in {vector.latency_ms} ms"
        )
    else:
        print(f"live skipped: {live.detail}")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "--selftest"
    if arg == "--selftest":
        selftest()
    elif arg == "--health":
        health = gateway_from_env().health()
        print(f"{health.provider}: {'ready' if health.ready else 'NOT READY'} - {health.detail}")
        sys.exit(0 if health.ready else 1)
    else:
        sys.exit(f"unknown argument: {arg}")
