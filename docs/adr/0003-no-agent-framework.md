---
status: accepted
date: 2026-09-07
decision-makers: Laxmi Poudel
consulted: none
informed: none
---

# No agent framework

## Context and problem statement

Established agent frameworks supply memory abstractions, retrievers, chain composition, and
execution loops. NOVA requires memory, retrieval, and a strategy layer. On the surface this is
precisely the problem those frameworks address.

Should the orchestration layer be built on a framework, or written directly?

## Decision drivers

* The execution trace must be complete and truthful: every retrieval score including non-selected
  candidates, every prompt digest, every retry attempt
* Memory extraction, scored retrieval, and outcome-based selection are the capabilities the project
  exists to demonstrate
* The effort budget is constrained, so avoidable work matters
* Dependency count is deliberately minimized, both for security surface and for maintenance

## Considered options

* Write the orchestration layer directly, using only an HTTP client and a schema validation library
* Adopt an established agent framework
* Adopt a framework for retrieval alone, writing the remainder directly

## Decision outcome

Chosen option: **write the orchestration layer directly**, because the orchestration layer is the
artifact the project is intended to demonstrate, and because frameworks own the call path in a way
that makes complete trace capture harder to obtain than to write.

Delegating memory extraction, scored retrieval, and bounded selection to a framework would mean
demonstrating configuration rather than engineering, with the substantive parts behind an
abstraction the author did not write.

The second consideration is practical. The entire system depends on trace completeness. Frameworks
control the call path, and extracting that level of introspection from one is generally more work
than writing the call path directly.

The volume of code avoided is not large. A scored retrieval query, a prompt assembler, and a bounded
selection function are on the order of tens of lines each.

### Consequences

* Good, because complete control over trace content and granularity
* Good, because no upgrade treadmill on a rapidly changing dependency
* Good, because a smaller dependency surface
* Good, because every line in the execution path can be explained
* Bad, because more code is written by hand and therefore more code requires tests
* Bad, because ecosystem integrations available without cost from a framework would have to be
  written if they were ever required

### Confirmation

Verified by trace completeness tests, including against a deliberately failed task, and by the
absence of framework dependencies in the manifest.

Revisit if the project requires integrations that a framework supplies and the orchestration layer
is no longer the capability being demonstrated.

## Pros and cons of the options

### Direct implementation

* Good, because complete trace control
* Good, because minimal dependency surface
* Good, because the demonstrated capability is not obscured
* Bad, because more hand-written code and tests

### Established agent framework

* Good, because retrievers, memory abstractions, and composition are supplied
* Good, because maintenance burden is shared across a community
* Bad, because trace introspection must be recovered from a framework that owns the call path
* Bad, because it obscures the capability the project exists to demonstrate
* Neutral, because on a production team this would likely be the correct choice

### Framework for retrieval only

* Bad, because it incurs a dependency and its upgrade cost for the single component most requiring
  inspectability
* Bad, because it combines the disadvantages of both alternatives without the advantages of either

## More information

This is the decision most likely to be challenged. The defensible position is that context
determines the answer: on a production team a framework is usually correct, whereas here the
orchestration layer is the deliverable and wrapping it would conceal it.
