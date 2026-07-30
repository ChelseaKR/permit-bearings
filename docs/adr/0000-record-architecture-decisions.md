# Record architecture decisions

- Status: Accepted
- Date: 2026-07-29
- Decider: Chelsea Kelly-Reif

## Context

Permit Bearings makes public, source-linked permitting claims. Changes to its
matching boundary, evidence semantics, privacy posture, or delivery controls
need a durable explanation beyond a commit message.

## Decision

Number architecture decision records sequentially under `docs/adr/`. Each
record states its status, date, context, decision, and consequences. A new ADR
is required before weakening a fail-closed evidence boundary, adding a runtime
model or durable applicant-data flow, changing the release posture, or
accepting a material standards divergence.

## Consequences

The existing design documents remain the architecture reference. ADRs record
specific consequential choices and do not replace capability truth in
`docs/PRODUCT-CONTEXT.md`.
