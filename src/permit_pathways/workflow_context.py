"""Load one registry entry as a source-review context.

This shared boundary keeps the review-worklist and source-release CLIs on the
same registry traversal and artifact-binding semantics. It validates portable
registry paths and IDs; it does not activate, approve, or publish a workflow.
"""

from __future__ import annotations

from pathlib import Path

from .journey import load_journey_config
from .program_availability import load_program_availability
from .readiness import (
    load_readiness_packet,
    load_readiness_remedies,
    load_readiness_workflow,
)
from .review_queue import ReadinessReviewContext
from .workflow_registry import FingerprintedArtifact, WorkflowRegistryEntry


def _assert_registered_path(
    root: Path,
    artifact: FingerprintedArtifact,
    override: Path | None,
    option: str,
) -> Path:
    selected = artifact.resolve(root)
    if override is not None and override.resolve() != selected:
        raise ValueError(f"--{option}: path does not match the registered workflow")
    return selected


def load_registered_review_context(
    entry: WorkflowRegistryEntry,
    root: Path,
    sources_path: Path,
    *,
    workflow_override: Path | None = None,
    packet_override: Path | None = None,
    remedies_override: Path | None = None,
    journey_override: Path | None = None,
) -> ReadinessReviewContext:
    """Load one exact registered workflow, packet, remedy, and journey set."""

    workflow = load_readiness_workflow(
        _assert_registered_path(
            root,
            entry.artifacts.readiness_workflow,
            workflow_override,
            "workflow",
        ),
        sources_path,
    )
    packet = load_readiness_packet(
        _assert_registered_path(
            root,
            entry.artifacts.readiness_packet,
            packet_override,
            "packet",
        ),
        workflow,
    )
    remedies = load_readiness_remedies(
        _assert_registered_path(
            root,
            entry.artifacts.readiness_remedies,
            remedies_override,
            "remedies",
        ),
        workflow,
    )
    journey = load_journey_config(
        _assert_registered_path(
            root,
            entry.artifacts.journey,
            journey_override,
            "journey",
        )
    )
    availability = load_program_availability(
        entry.artifacts.program_availability.resolve(root),
        policy=entry.availability_policy,
    )
    if workflow.workflow_id != entry.workflow_id:
        raise ValueError("registered workflow ID does not match its artifact")
    if packet.workflow_id != entry.workflow_id or packet.packet_id != entry.packet_id:
        raise ValueError("registered packet IDs do not match its artifact")
    if journey.journey_id != entry.journey_id:
        raise ValueError("registered journey ID does not match its artifact")
    if (
        journey.readiness_workflow_id != entry.workflow_id
        or journey.readiness_packet_id != entry.packet_id
    ):
        raise ValueError("registered journey references do not match its workflow")
    if (
        availability.workflow_id != entry.workflow_id
        or availability.program_id != entry.program_id
    ):
        raise ValueError("registered availability IDs do not match its artifact")
    if (
        workflow.jurisdiction != entry.jurisdiction
        or packet.jurisdiction != entry.jurisdiction
        or availability.jurisdiction != entry.jurisdiction
    ):
        raise ValueError("registered jurisdiction does not match its artifacts")
    return ReadinessReviewContext(
        workflow=workflow,
        packet=packet,
        remedies=remedies,
        journeys=(journey,),
    )
