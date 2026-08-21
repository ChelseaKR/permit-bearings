"""Optional runtime AI layer (ADR 0004): intake extraction, grounded explanation,
and staff-question drafting around the unchanged deterministic matcher.

Nothing in this package is imported by :mod:`permit_pathways.screening`, the
readiness evaluator, the build, or the static bundle. The model providers
are reached only through :mod:`permit_pathways.ai.provider`.
"""
