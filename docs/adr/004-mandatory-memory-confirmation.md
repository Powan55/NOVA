# ADR-004: Human confirmation on every memory write

Status: Accepted
Date: 2026-09-07

## Context

When a user corrects NOVA, the correction gets extracted into a candidate rule. Once stored, that
rule is retrieved and injected into future prompts whenever it's relevant.

The tempting design is to auto-promote candidates above some confidence threshold, so the system
feels automatic and nobody has to approve things constantly.

## Decision

No memory gets stored without explicit confirmation. No confidence threshold bypasses it, and no
batch approval hides individual rules.

## Alternatives

Auto-promote above a confidence threshold. Feels more automatic, fewer interruptions.

Auto-promote with retrospective review. Store first, prune later in the memory manager.

## Why

Stored memory is a persistent prompt-injection vector, and that changes the whole calculation.

A one-off injection in a requirement hits one task and is gone. An injection that survives extraction
and reaches storage gets replayed into every future prompt that retrieves it. Same shape as stored
XSS: written once, served repeatedly. Retrospective review doesn't help, because the damage happens
on every retrieval between storage and discovery, and there's no reason anyone would go looking.

There's a mechanical control in front of the gate: the validation checks screen for
instruction-shaped text, enforce a length bound, and reject rules that aren't general or actionable.
That screen is a denylist against an open-ended attack surface. It will miss things. Treating it as
sufficient means trusting a filter to be complete, which filters aren't.

So it's two imperfect controls in series, neither trusted alone. A mechanical screen that catches the
obvious, and a human who sees the exact text before it becomes durable.

There's a second reason that isn't about security. Extraction quality is bounded by a small local
model, and it will produce overbroad or trivial candidates. The gate is where those get caught.
Auto-promotion would quietly fill the memory store with noise that degrades retrieval precision, and
that would show up as the system mysteriously getting worse.

It's also demonstrable. Showing a candidate, its provenance, and the moment someone accepts it
explains how the system works far better than describing a threshold.

## Consequences

Easier: no path exists for an injected or wrong rule to become durable without a human seeing it.
Extraction quality problems surface immediately instead of accumulating. The mechanism is visible.

Harder: more clicks, and it feels less automatic. At high correction volume the gate would get
tedious, which is a real limitation, though not one that binds at single-user scale.

Don't undo this casually. The urge to automate it will come back once the confirmation flow feels
repetitive. It doesn't exist for convenience, and removing it silently reopens the highest-impact
threat in the system.

Revisit only once there's enough confirmation data to show what a genuinely safe auto-promotion
threshold looks like, and even then only for rules that clear the mechanical screen by a wide
margin.
