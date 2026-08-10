# Provenance record

- **Conceived:** 2026-07-27 in response to the public California AI
  Permitting Innovation Showcase announcement.
- **Authorship context:** personal project, personal equipment and accounts,
  begun after 2026-07-21. Original application code, rule encodings,
  explanation drafts, tests, and project prose were created for this
  repository.
- **Public-source inputs:** official California statutes; HCD handbooks, fact
  sheets, and enforcement or technical-assistance records; official municipal
  code and CEQA pages; California and federal open data; and official transit
  schedules. These materials are evidence inputs, not project-authored work.
- **California Design System reference:** all five static pages use a
  project-maintained version-0 preview compatibility layer informed by the
  successor California Design System at pinned commit
  `f8775cfac090de08b9e0083eb3008bd585f33e91` (2026-01-27). That repository
  describes the system as pre-Alpha and not production-ready. Its package and
  repository license declarations are not unambiguous, so no successor source,
  compiled bundle, or package is redistributed. The local `ca-*` selectors and
  markup are project-authored compatibility structures, not a fork or
  certified implementation. The optional Python-rendered reference flow loads
  the same project-authored layer; it does not introduce another upstream
  dependency.
- **Legacy design assets:** the interface adapts published `cagov` theme
  tokens and redistributes Public Sans regular, semibold, and bold WOFF2 font
  files from the archived MIT-licensed `cagov/design-system` snapshot
  `4a2ba27967580cbfb10b94b0e1b3193dbcea7c22`. The font files remain subject
  to the SIL Open Font License 1.1; both notices are retained in
  `THIRD_PARTY_NOTICES.md`. The product-specific service header intentionally
  omits State branding, and no California affiliation, endorsement, or
  official-site status is implied.
- **Source-state receipt:** `data/source-status/current.json` records the
  completed August 3, 2026 GitHub Actions source-currency run
  `30835371749` against commit
  `8d841409dc5fd16fe56b52a8b57c826c07f176a6`: 19 unchanged, zero changed,
  and zero unverifiable watched sources. Its `reviewed` status means the exact
  completed-run receipt was deliberately selected for the public repository
  build. It is not a claim of named-human, legal, jurisdiction, counsel, or
  substantive content review.
- **Woodland program availability:** the official
  [City of Woodland Preapproved ADU Plan Program page](https://www.cityofwoodland.gov/1616/Preapproved-ADU-Plan-Program)
  was checked on 2026-08-09 and said **“Preapproved ADU List: Coming soon!”**
  No listed City plan was identified. The exact excerpt fingerprint,
  `plans_not_listed` status, future-state boundary, and recheck deadline are
  recorded in `data/availability/woodland-preapproved-adu-program.json`. The
  retained checklist was separately source checked 2026-07-29; it is not
  described as inherently dated. These records support only a source-bound
  future-state simulation, not a currently usable preapproved plan or
  applicant-ready workflow.
- **Rule-review provenance:** schema version 2 in
  `data/validation/rule-verification.json` binds any promoted review claim to
  both citation and full-rule fingerprints. Source change, source age, review
  age, or fingerprint drift demotes the effective claim. All 19 current rules
  remain `machine_linked`; the public evidence page records zero named human
  reviews and zero jurisdiction approvals. Bundle format 6 carries this claim
  separately from source state and program availability.
- **HCD HAU letter refresh:** the public HCD Housing Accountability Unit
  dashboard was re-read on August 3, 2026. The committed derived dataset now
  contains 1,314 letter records: 1,312 mapped across 470 jurisdictions and two
  statewide records, with zero unmatched rows.
- **Statewide coverage index:** `jurisdictions.py` derives a portable profile
  index from the committed jurisdiction registry, scoped rule records, and
  HCD-letter snapshot. It validates the snapshot's non-future ISO retrieval
  date and records rule IDs and HCD counts rather than interpreting
  correspondence. The browser applies the separately adopted source-state
  receipt to hold changed statewide/local inventory records for re-verification.
  It supports orientation only: no linked HCD record is not a compliance or
  no-activity finding, and an absent local layer is not a claim that local
  requirements do not exist.
- **AI assistance:** rule and readiness encoding, explanation, remedy and
  translation drafts, code, prose, and the two decorative editorial
  illustrations have been machine-assisted. The illustrations were generated
  for this repository with OpenAI's image-generation tool from
  project-specific prompts, then converted locally to compressed WebP assets;
  they are not copied from California Design System or agency artwork and do not
  represent an official mark, workflow, source, or decision. No current
  rule interpretation, checklist mapping, action draft, plain-language
  explanation, or Spanish translation is represented as
  jurisdiction-approved, counsel-approved, or human-reviewed unless its own
  record contains that exact review metadata.
- **Relationship to prior work:** no proprietary or non-public work product is
  represented as imported. Public documents and datasets retained in
  `corpus/` and generated source registries remain attributable to their
  publishers and are excluded from claims of original authorship.

Source URLs, retrieval or check dates, content hashes, and rule dependencies
are recorded in `data/sources.json`, the program-availability record, rule
citations, dataset metadata, and `corpus/ordinances/SOURCES.json`. See
`THIRD_PARTY_NOTICES.md` for attribution and licensing boundaries.

This file records project provenance. It does not make legal conclusions about
copyright, public-record status, or permission to redistribute any specific
source artifact.
