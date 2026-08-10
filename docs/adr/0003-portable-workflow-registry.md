# ADR-0003: Use a strict portable registry for bounded workflows

**Status:** Accepted
**Date:** 2026-08-09
**Deciders:** Repository maintainer

## Context

The bounded Woodland readiness sample is linked across a workflow, packet,
remedy sidecar, journey, program-availability record, generated evidence, the
browser bundle, and two CLIs. Those paths were repeated as Woodland-specific
constants. Adding a second reviewed pilot workflow that way would make it easy
to omit an artifact from generation or source-change review, point one surface
at a different packet, or expose a workflow in the browser merely because a
file exists.

The current browser contract intentionally exposes one bounded future-state
simulation. The refactor must preserve that one-workflow public behavior. It
must not turn extensible infrastructure into a claim that another workflow is
active, reviewed, applicant-ready, or jurisdiction-approved. Review of the
first implementation found that format 5 did not bind the browser's parsed
registry to its raw generated input, so compatibility must yield to an
explicit format-version change rather than silently altering that contract.

## Decision

Use `data/workflows/registry.json` as the sole selector for readiness workflow,
packet, remedy, journey, program-availability, and generated evidence paths.
The schema is a list keyed by stable workflow ID and contains one explicit
`browser_default_workflow_id`.

Every canonical input path is repository-relative, restricted to a portable
lowercase ASCII JSON filename in its expected direct directory, and pinned to
the SHA-256 of bounded raw bytes. The loader requires a complete one-to-one
inventory of canonical inputs and generated JSON outputs. It rejects unknown
or duplicate JSON fields, non-finite or oversized data, symbolic and hard
links, duplicate/case-colliding workflow/packet/journey/program IDs, duplicate
or overlapping paths, orphan files or references, absolute/traversal/
wrong-directory paths, fingerprint drift, and declared IDs or jurisdictions
that do not match the referenced records. Generated destinations receive the
same linked-file boundary before the builder can write them.

Each entry declares an availability-validation policy. The Woodland policy
retains exact ID, URL, excerpt, and boundary checks. A conservative generic
prototype policy exists to prove that a distinct non-default workflow can
traverse the builder and review queue without adding another public workflow.

The builder validates and generates every registered entry. Bundle format 6
aliases only the explicit browser default to the existing singular
`readiness`, `program_availability`, and one-element `journeys` fields. It also
embeds the exact raw registry text. The browser hashes those bytes against the
bundle input receipt, checks the parsed copy agrees, validates every registered
input pin, and derives workflow-specific links from the Woodland default. It
cannot inventory files absent from the bundle; that remains a Python boundary.
The readiness CLI selects one registered ID. The review-queue CLI includes all
registered contexts by default. Legacy path flags remain only as exact
assertions against a selected entry.

## Options considered

### Option A: Keep per-module path constants

| Dimension | Assessment |
|---|---|
| Complexity | Low initially, rising for every workflow |
| Failure isolation | Weak; paths can drift independently |
| Portability | Weak; the artifact graph exists only in code |
| Browser compatibility | Unchanged |

**Pros:** Smallest immediate diff.

**Cons:** Repeats the existing coupling and makes complete inventory or
cross-workflow maintenance difficult to prove.

### Option B: Discover every JSON file by directory convention

| Dimension | Assessment |
|---|---|
| Complexity | Medium |
| Failure isolation | Weak; file presence can become activation |
| Portability | Medium |
| Browser compatibility | Requires ambiguous default selection |

**Pros:** Fewer authored references.

**Cons:** Cannot distinguish intentional publication from a stray file, cannot
bind related IDs safely, and makes browser exposure implicit.

### Option C: Strict registry with one explicit browser default

| Dimension | Assessment |
|---|---|
| Complexity | Medium |
| Failure isolation | Strong; invalid entries fail closed |
| Portability | Strong; graph and pins are plain JSON |
| Browser compatibility | Public behavior preserved; contract intentionally advances to format 6 |

**Pros:** Makes selection, inventory, and input drift testable while retaining
the current public shape.

**Cons:** Any canonical input edit requires an intentional fingerprint update,
and adding a registry entry does not by itself design a new workflow-specific
availability policy or browser experience.

## Consequences

- Build and CLI behavior no longer depends on Woodland-specific paths.
- An unregistered or repinned-but-ID-inconsistent artifact fails before it can
  enter the bundle or maintenance worklist.
- A future reviewed workflow can be added without another set of path
  constants, but it still needs authoritative sources, domain validation,
  review evidence, and an explicit browser product decision.
- Bundle format 6 makes raw-registry and generation-receipt binding explicit;
  the current one-workflow browser behavior remains stable.
- The registry and its pins are integrity and selection controls, not
  authenticity, approval, legal review, or external validation evidence.

## Action items

1. [x] Add the strict registry, linked-file and portable-path boundary,
   builder/CLI selection, raw browser receipt validation, and adversarial
   parity tests.
2. [ ] Register another workflow only after its active source package,
   workflow-specific validation policy, review authority, and publication
   decision exist.
3. [ ] Revisit the singular browser aliases only when a real multi-workflow
   applicant experience is designed and fully tested.
