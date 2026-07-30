# Data card — public permitting reference sources

- Tier: L1 public, non-sensitive reference data
- Publishers: California Legislature, California HCD, California and federal
  open-data publishers, and the named local jurisdictions
- Registry: `data/sources.json`
- Lineage: retained source copies under `corpus/`, stable source IDs, SHA-256
  digests, retrieval dates, rule dependency IDs, and generated-bundle hashes
- Retention: indefinite while useful and redistribution remains permitted;
  remove or relicense within 30 days of confirmed publisher notice

## Purpose

The sources support deterministic candidate-rule screening, source currency
checks, a bounded ordinance screen, transit-proximity candidates, and the
synthetic Woodland readiness workflow.

## Refresh and staleness

Watched sources use the cadence and recorded digest in `data/sources.json`.
The weekly watcher reports changed or unreachable records. Rule and
explanation runtimes separately enforce dated review windows. Newly enacted
law discovery and a durable human re-verification queue are not implemented.

## License and provenance

Official statutes, guidance, forms, GIS, transit data, and municipal materials
retain their publisher attribution and any separate terms. Repository code is
MIT; that license is not asserted over third-party source content. See
`PROVENANCE.md`, `THIRD_PARTY_NOTICES.md`, and per-source metadata.

## Known limitations

The registry is not a claim of comprehensive state or local coverage. A
statewide baseline is not locally encoded law. Source-linked mappings and
machine-assisted explanations remain review-pending unless their own metadata
records a completed review.

Last reviewed: 2026-07-29. Recheck on any new source, publisher term, source
schema, retention, or data-flow change.
