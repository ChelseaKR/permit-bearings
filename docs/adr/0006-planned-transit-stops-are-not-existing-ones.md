# Planned transit stops are not existing ones

- Status: Accepted
- Date: 2026-08-27
- Decider: Chelsea Kelly-Reif

## Context

`src/permit_pathways/transit.py` screens two State ADU Law standards that turn
on transit proximity: the § 66322(a)(1) parking exemption and the
§ 66321(b)(4)(B) 18-foot height allowance. Alongside a local GTFS feed it reads
the statewide Caltrans/Cal-ITP High Quality Transit Stops dataset, which
supplies the operators, rail, and ferry a single local bus feed does not carry.
That was the point of adding it: the Davis Amtrak platform is absent from the
Unitrans feed and present in the statewide dataset.

Each dataset row has six fields. The screen read `hqta_type` and decided:

```python
@property
def is_major(self) -> bool:
    return self.hqta_type.startswith("major_stop")
```

`hqta_details` was parsed into `HQStop.details` and never read again. Nothing
in `src/`, `tests/`, `scripts/`, or `assets/` referenced it. It was a field
carried into the model for decoration.

`hqta_details` is the field that separates two different things wearing one
type. Cal-ITP's published methodology for the dataset
(https://github.com/cal-itp/data-analyses/tree/main/high_quality_transit_areas,
`README.md` and `technical_notes.md`, both read 2026-08-27) lists planned stops
in their own workflow section, "Planned Major Stops (future service, provided
by MPOs)", and describes their handling:

> Metropolitan Planning Organizations are encouraged to submit geospatial data
> of planned major transit stops for inclusion in our datasets. Per PRC 21155,
> these must be included in the _currently adopted_ regional transportation
> plan. ... Since the only statutory criteria for including these stops is that
> they are included in the RTP, Caltrans does not validate or further process
> them. We will add them to our map as-is.

The same README quotes the two statutory definitions the dataset spans:

> PRC 21155. Major transit stop definition: _A major transit stop is as defined
> in Section 21064.3, except that, for purposes of this section, it also
> includes major transit stops that are included in the applicable regional
> transportation plan_

> PRC 21064.3. _Major transit stop means a site containing any of the
> following: (a) An existing rail or bus rapid transit station. ..._

So one column, `hqta_type`, holds rows qualifying under two definitions that do
not agree, and `hqta_details` is the only thing that tells them apart. In the
committed 2026-07-27 snapshot, 3,120 of the 13,446 distinct `major_stop_*` rows
the loader returns are `mpo_rtp_planned_major_stop`, close to one row in four.

The consequence was visible on this repository's own documented example. The
command printed in `README.md`,

```sh
PYTHONPATH=src python3 -m permit_pathways.transit --gtfs corpus/gtfs/unitrans.zip --lat 38.5449 --lon -121.7442
```

produced:

```
18-ft height allowance (Gov. Code § 66321(b)(4)(B)): CANDIDATE — Yolo TD
(major_stop_bus) (0.12 mi) is a major transit stop (Caltrans HQ Transit Stops
dataset: major_stop_bus); confirm walking distance.
```

Seven planned Yolo TD rows sit between that coordinate and the two operating
rail platforms at 0.36 mi. The tool selected the nearest row, which was
planned, and said in the present tense that it "is a major transit stop". Both
the planned rows and the rail platforms are inside the half mile, so the
verdict survived either way. The reason given for it did not. Issue #44
reported this with the measurement.

## Decision

The screen reads `hqta_details`.

- `HQStop.is_planned` is true exactly when `details` is
  `mpo_rtp_planned_major_stop`. `HQStop.is_existing_major` is a major-stop row
  that is not planned. `is_major` keeps its meaning, the dataset's own type
  classification, planned rows included.
- A planned row inside the half mile produces no candidate. It does not
  establish a § 21064.3 major transit stop for the height allowance, and it
  does not establish public transit near the site for the parking exemption. A
  facility that does not exist yet is not transit an applicant can walk to.
- A planned row inside the half mile is never silently dropped. It is carried
  on `Determination.planned_major_stops` and reported in `summary()` by count,
  agency, type, and distance, with what Caltrans says about these rows, the two
  statutory definitions, and the instruction to ask the transit agency or
  planning staff whether the facility is in service.
- Every reason string for a dataset-derived stop now names both `hqta_type` and
  `hqta_details`, so a reader can see which classification produced it rather
  than inferring one.
- `hqta_details` now decides whether a row can support a candidate, so
  `load_hq_stops` requires it to be text and raises on anything else, instead
  of defaulting to `""` and reading as an operating facility. The
  de-duplication key gained the same field: it was `(lat, lon, hqta_type)`, so
  a planned row and an operating row at one coordinate with one type collapsed
  into whichever came first. That fix alone recovers 898 rows the loader had
  been discarding.

The module does not decide which statutory definition a given standard
incorporates. It refuses to collapse the two.

## Alternatives considered

- **Decide whether § 66321(b)(4)(B) incorporates § 21155's expanded
  definition.** Rejected. That is a legal reading, this repository does not
  make legal readings, and no published source retrieved here settles it.
  Withholding the candidate and naming the row is the answer that does not
  require the reading.
- **Report the planned row as a candidate with a warning attached.** Rejected.
  `docs/PRODUCT-CONTEXT.md` risk 5 already directs the opposite: "Return
  `unknown` unless data completeness supports a narrower conclusion." A
  candidate the reader must then discount is the confident wrong answer this
  project exists to avoid.
- **Drop planned rows at load time.** Rejected. It would make the tool silent
  about a fact the source publishes, and a planned stop near a site is
  genuinely useful to an applicant who can then ask when it opens. Withholding
  a finding without saying so is the failure mode, not the fix.
- **Widen the exclusion to any row whose `hqta_details` is unfamiliar.**
  Not done. `mpo_rtp_planned_major_stop` is the one value the publisher
  documents as planned. Excluding values on the ground that this repository has
  not read their definition would be guessing in the conservative direction,
  which is still guessing. An unreadable, non-text `hqta_details` is a
  different case and does fail the load.
- **Also carry the distinction into the applicant-facing pages.** Not
  applicable. `transit.py` is a CLI. Nothing in `screening.py`, `assets/demo.js`,
  `demo/app.py`, the rule base, or the bundle imports it, so there is no second
  runtime to keep in agreement here.

## Consequences

The documented Davis example now names the operating Capitol Corridor rail
platform at 0.36 mi as the reason for the 18-foot allowance and lists the twelve
planned rows inside the radius separately. The verdict is unchanged; the
evidence for it is now true.

Three of the four transit corrections `docs/PRODUCT-CONTEXT.md` risk 5 names
remain open: service effective dates and calendar exceptions, multi-operator
completeness, and walking-network confirmation. This decision closes one of
them and does not change the capability status, which stays Prototype and not
applicant-facing.

Attribution for the Cal-ITP methodology lives in the module docstring and in
this record rather than in `THIRD_PARTY_NOTICES.md`, which would otherwise be
its natural home. Both evidence export profiles pin that file by raw SHA-256,
and the schema-v1 profile is frozen for archive compatibility, so adding a
line to it fails `make evidence-export-check` and would require a new export
profile version. `docs/EXPORT-RESTORE.md` makes that a separately reviewed
decision, and it is not one this change should make on the way past. Nothing
is redistributed here in any case: short passages are quoted with their URL
and read date, and neither document is vendored.

A dataset column that is parsed and never read is the shape of defect this was.
The value looked present in the model and in every debugger, and no test could
have failed on its absence, because nothing consumed it. `hqta_details` is now
consumed, and eight regression tests fail if it stops being.
