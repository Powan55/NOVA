---
status: accepted
date: 2026-09-07
decision-makers: Laxmi Poudel
consulted: none
informed: none
---

# Mandatory human confirmation for memory writes

## Context and problem statement

When a user corrects NOVA, the correction is extracted into a candidate rule. Once stored, that rule
is retrieved and injected into every subsequent prompt for which it is in scope.

The convenient design promotes candidates automatically above a confidence threshold, so that the
system feels autonomous and the user is not asked to approve items repeatedly.

Under what conditions may a derived rule become durable and retrievable?

## Decision drivers

* A stored memory is replayed into every future prompt that retrieves it, so a compromise is
  persistent rather than transient
* The mechanical screen protecting the extraction path is a denylist against an open-ended attack
  surface, and is therefore known to be incomplete
* Extraction quality is bounded by a 4B-parameter model and will produce overbroad or trivial
  candidates
* The learning mechanism must be demonstrable to a skeptical reader

## Considered options

* Mandatory user confirmation before any memory becomes retrievable
* Automatic promotion above a confidence threshold
* Automatic promotion with retrospective review in the memory management interface

## Decision outcome

Chosen option: **mandatory user confirmation**, with no confidence threshold that bypasses it and no
batch approval that conceals individual rules, because the memory path is a persistent injection
vector and no single mechanical control over it can be treated as complete.

A single injected requirement affects one task and is then gone. An injection that survives
extraction and reaches storage is replayed into every subsequent prompt that retrieves it, which is
structurally equivalent to stored cross-site scripting: written once, served repeatedly.

Retrospective review does not address this. The harm occurs on every retrieval between storage and
discovery, and the user has no signal prompting them to look.

The design is therefore two independent controls in series, neither relied upon alone: a mechanical
screen that catches the obvious, and a human who sees the exact text before it becomes durable.

A second consideration is unrelated to security. Automatic promotion would populate the memory store
with low-quality rules that degrade retrieval precision, and the user would experience that as the
system inexplicably deteriorating.

### Consequences

* Good, because no path exists by which an injected or incorrect rule becomes durable without a
  human having seen it
* Good, because extraction quality problems surface immediately rather than accumulating
* Good, because the mechanism is directly demonstrable: a candidate, its provenance, and the moment
  of acceptance
* Bad, because the system feels less autonomous and requires more interaction
* Bad, because at high correction volume the confirmation step would become an obstacle. This does
  not bind at single-user scale, but it is a genuine limitation

### Confirmation

Verified by adversarial scenarios that submit instruction-shaped corrections, oversized rules, and
rules crafted to suppress required case types, each asserting that the candidate is either rejected
by the screen or surfaced at the confirmation step, and in no case stored silently.

Revisit only once sufficient confirmation data exists to characterize a genuinely safe automatic
promotion threshold, and then only for candidates clearing the mechanical screen by a wide margin.

**This decision should not be reversed casually.** The pressure to automate the step will return once
the confirmation flow becomes repetitive. It does not exist for convenience, and removing it would
silently reopen the highest-impact threat in the system.

## Pros and cons of the options

### Mandatory confirmation

* Good, because no unreviewed rule becomes durable
* Good, because extraction defects surface at once
* Good, because it is demonstrable rather than merely described
* Bad, because more interaction is required
* Bad, because it does not scale to high correction volume

### Automatic promotion above a threshold

* Good, because the system feels autonomous
* Good, because fewer interruptions
* Bad, because it relies on a mechanical screen known to be incomplete
* Bad, because low-quality rules accumulate and degrade retrieval silently
* Bad, because no confidence data yet exists from which to derive a safe threshold

### Automatic promotion with retrospective review

* Good, because it preserves an eventual human check
* Bad, because harm occurs on every retrieval before discovery
* Bad, because nothing prompts the user to review

## More information

Mitigates threat T3 in [NOVA-TM-001](../threat-model.md). The layered control set is described in
section 6.1 of that document.
