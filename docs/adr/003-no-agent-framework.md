# ADR-003: No agent framework

Status: Accepted
Date: 2026-09-07

## Context

LangChain, LlamaIndex, CrewAI and similar provide memory abstractions, retrievers, chains, and agent
loops out of the box. NOVA needs memory, retrieval, and a strategy layer. On the surface that's
exactly what those frameworks are for.

## Decision

Build the orchestration layer directly. No agent framework. The only third-party pieces in the agent
path are an HTTP client to the model runtime and Pydantic for schema definition and validation.

## Alternatives

LangChain or LlamaIndex, which would supply retrievers, memory classes, and chain composition, and
would probably save real hours in the first milestone.

A thin framework used only for retrieval. Rejected as the worst of both: a dependency and its
upgrade treadmill, for the one part of the system that most needs to be inspectable.

## Why

This is the decision most likely to get questioned, so here it is plainly.

The orchestration layer is the artifact. Memory extraction with validation checks, retrieval scored
on three explainable components with the non-selected candidates written into the trace,
outcome-scored playbook selection with bounded updates. Those are the things this project is meant
to show. Handing them to a framework means showing configuration instead of engineering, and the
interesting parts end up behind an abstraction I didn't write.

There's a practical reason too. The whole system depends on the execution trace being complete and
truthful: every retrieval score, every prompt hash, every retry. Frameworks own the call path, and
getting that level of introspection back out of one is usually more work than writing the call path
yourself.

The code being avoided isn't large. A scored retrieval query, a prompt assembler, and a bounded
selection function are tens of lines each.

## Consequences

Easier: total control over the trace, no upgrade treadmill on a fast-moving dependency, smaller
attack surface, and I can explain every line in the agent path.

Harder: more code by hand, so more code to test. Ecosystem integrations that come free with a
framework would have to be written if I ever needed them.

If challenged: on a production team a framework would probably be right, since the maintenance
burden is shared and the integrations are real value. Here the orchestration layer is the thing
being shown, so wrapping it would hide it.

Revisit if the project needs integrations a framework provides and the orchestration layer stops
being the point.
