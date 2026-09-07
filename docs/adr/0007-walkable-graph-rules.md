# ADR-0007: Which OpenStreetMap ways count as walkable, and what happens when the network cannot answer

**Status:** Accepted
**Date:** 2026-09-07
**Deciders:** Repository owner
**Relates to:** ADR-0006 (a planned stop is not an existing one) — the same
refusal to let a screen report a number the source does not support

## Context

Both transit standards this project screens are written in walking distance.
Gov. Code § 66322(a)(1) exempts an ADU from parking requirements when it is
"located within one-half mile **walking distance** of public transit", and
§ 66321(b)(4)(B) allows eighteen feet within a half-mile walking distance of a
major transit stop.

`transit.py` measured a straight line. The README said so, in terms: the
straight line "can eliminate a supplied stop, but cannot establish" one.
That is a correct statement of the asymmetry, and it is also an admission
that the tool answered a different question from the one the statute asks —
and answered it in the optimistic direction. A stop across a freeway, a
canal, a rail corridor or a creek is a quarter mile as the crow flies and a
mile and a half on foot. Every such stop was a straight-line candidate.

`docs/PRODUCT-CONTEXT.md` names walking-network confirmation as correction
risk 5, and `docs/EXPANSION-PLAN.md` Phase 1 lists it. The remaining question
was not whether to measure the walk but what to measure it over, and what to
say when the answer is not available.

## Decision

**Measure the walk offline, from a file the operator supplies, and never
substitute the straight line for it.**

### 1. The network is a file, not a service

An OSM XML extract (`.osm`, `.osm.gz`, `.osm.bz2`) or a pre-built graph
(`.json`). Nothing is fetched at screening time and no routing service is
called. The consequences that matter: the run is reproducible, it works in a
jurisdiction with no outbound network access, there is no third party in the
data path, and there is no per-query cost or rate limit to design around.

The extract's SHA-256 and its bounds travel with the result, so a metre count
can always be traced to the file it came from.

**PBF is not supported.** Reading it requires a compiled library, and adding
that dependency for an optional offline mode would cost every deployment that
never uses it. `osmium cat -o area.osm area.osm.pbf` converts in one command.
Because no third-party package is needed, there is also no optional extra to
install: the reader is `xml.etree.ElementTree.iterparse` and the search is
`heapq`.

### 2. Graph rules, written down rather than inferred

A way is walkable when:

* its `highway` value is in the **walkable set** — `footway`, `path`,
  `pedestrian`, `steps`, `living_street`, `residential`, `unclassified`,
  `service`, `track`, `tertiary`(`_link`), `secondary`(`_link`),
  `primary`(`_link`), `corridor`, `crossing`; **or**
* it carries `foot=yes`/`designated`/`permissive`/`destination`, which admits
  a way whose `highway` value is not in that set (a `cycleway` signed for
  pedestrians, say).

A way is **never** walkable when:

* its `highway` value is in the **excluded set** — `motorway`,
  `motorway_link`, `trunk`, `trunk_link`, `construction`, `proposed`,
  `raceway`, `bus_guideway — **whatever else it is tagged**. A `foot=yes` on
  a motorway is a tagging error or a mapped shoulder, and reading it as a
  footpath produces exactly the optimistic answer this work exists to remove;
* it carries `foot=no` or `foot=private`;
* it carries `access=no`/`private` and no `foot` tag that permits.

Every edge is undirected. `oneway` restricts vehicles; a one-way street is
walkable in both directions.

Two secondary classes are deliberately *not* modelled, and the omission is
recorded rather than hidden: crossing legality (an unsignalised crossing of a
`primary` is walkable in this graph, and may not be advisable) and grade
separation beyond what the tags say. Both would need data the extract does
not reliably carry.

### 3. Three withheld states, and no fourth that guesses

A walk is reported only when it was measured. Otherwise the result names the
reason and carries **no distance**:

| Status | Meaning |
|---|---|
| `measured` | a path was found; `walking_m` is its length, snap legs included |
| `not_in_extract` | the site or the stop lies outside the extract's bounds |
| `snap_too_far` | the nearest walkable node is beyond the snap limit (default 100 m) |
| `disconnected` | both points snapped and no walkable route joins them *in this extract* |

`disconnected` is a statement about the extract's coverage, not a proof that
no route exists, and a clipped extract makes it common near the edge. None of
the three is treated as evidence against a stop, and none of them is ever
filled in from the straight line. That substitution — a number that means "we
did not measure" published as if it were a measurement — is the defect class
this repository keeps finding, and this is the surface where it would have
been easiest to introduce.

### 4. The walking distance changes no verdict

Both distances are reported; the parking and height verdicts stay
straight-line. Which distance a jurisdiction applies to a given screen is a
legal judgement this tool does not make, and quietly switching the verdict to
the walking number would be making it. The summary says so where it prints
the numbers.

## Consequences

- A stop that is a straight-line candidate and a mile and a half on foot is
  now visible as such, which is the point.
- Results depend on the supplied extract, so the extract's digest and bounds
  are part of the result. Two runs over different extracts are two different
  measurements and are labelled as such.
- The graph is only as good as the mapping. An unmapped footpath reads as a
  longer walk, and this direction of error is the safe one: it never turns a
  long walk into a short one.
- A snap limit is a judgement. 100 m is roughly a city block — far enough to
  attach a stop set back from the kerb, near enough that attaching it does
  not invent a path across a parcel. Raising it does not improve the
  measurement; it widens what the tool is willing to assume.
- Nothing here validates that the operator's extract covers the area they
  think it covers. The bounds are reported so a reader can check.
