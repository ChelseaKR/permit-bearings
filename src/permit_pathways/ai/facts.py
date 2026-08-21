"""The structured-fact vocabulary the deterministic matcher consumes.

This module is the single description of what a natural-language intake may
produce. Every field name, allowed value, and project-type applicability here
mirrors the browser form in ``assets/demo.js`` and the criteria in
``data/rules``; ``tests/test_ai_facts.py`` holds the three in agreement. The
model that extracts facts is constrained to this vocabulary by schema and
then by code, so nothing outside it can reach the matcher.

``UNKNOWN`` is the literal value the matcher and the browser already use for
"the applicant does not know". Extraction reuses it for "the text did not
say", so absence stays absence all the way through.
"""

from __future__ import annotations

from dataclasses import dataclass

PROJECT_TYPES: tuple[str, ...] = ("adu", "jadu", "two_unit", "lot_split")
TRI_STATE: tuple[str, ...] = ("yes", "no", "unknown")
UNKNOWN = "unknown"


@dataclass(frozen=True)
class FactField:
    """One structured fact: its name, allowed values, and scope."""

    name: str
    values: tuple[str, ...]
    applies_to: tuple[str, ...]
    meaning: str

    @property
    def concrete_values(self) -> tuple[str, ...]:
        return tuple(v for v in self.values if v != UNKNOWN)


PRIMARY_DWELLING_VALUES: tuple[str, ...] = (
    "existing_single_family",
    "existing_multifamily",
    "proposed_single_family",
    "proposed_multifamily",
    "none",
    UNKNOWN,
)

ADU_FORM_VALUES: tuple[str, ...] = (
    "new_detached",
    "new_attached",
    "conversion",
    "same_footprint_rebuild",
    UNKNOWN,
)

_SB9 = ("two_unit", "lot_split")

FACT_FIELDS: tuple[FactField, ...] = (
    FactField(
        "primary_dwelling_status",
        PRIMARY_DWELLING_VALUES,
        ("adu", "jadu"),
        "What dwelling exists on the lot now, or is only proposed. "
        "'existing_*' means it is there today; 'proposed_*' means none exists "
        "yet and one is being proposed; 'none' means neither.",
    ),
    FactField(
        "adu_project_form",
        ADU_FORM_VALUES,
        ("adu",),
        "The kind of ADU work: a new detached structure, a new attached "
        "addition, conversion of space inside an existing structure, or "
        "replacing a structure in the same location and dimensions.",
    ),
    FactField(
        "unpermitted_existing",
        TRI_STATE,
        ("adu", "jadu"),
        "Whether the applicant is trying to legalize a unit that was built "
        "without permits before January 1, 2020.",
    ),
    FactField(
        "in_urbanized_area",
        TRI_STATE,
        _SB9,
        "Whether the property is inside an incorporated city or another "
        "SB 9-qualifying urban area.",
    ),
    FactField(
        "sf_zone",
        TRI_STATE,
        _SB9,
        "Whether the property is zoned for single-family residential use.",
    ),
    FactField(
        "demolishes_protected_housing",
        TRI_STATE,
        _SB9,
        "Whether the project would demolish or alter rent-restricted, "
        "price-controlled, or deed-restricted affordable housing.",
    ),
    FactField(
        "tenant_occupied_last_3_years",
        TRI_STATE,
        _SB9,
        "Whether a tenant lived in housing the project would demolish or "
        "alter during the last three years.",
    ),
    FactField(
        "ellis_withdrawal_last_15_years",
        TRI_STATE,
        _SB9,
        "Whether housing on the property was withdrawn from rental use under "
        "the Ellis Act during the last 15 years.",
    ),
    FactField(
        "on_protected_site",
        TRI_STATE,
        _SB9,
        "Whether the property has a wetland, hazardous-land, conservation, "
        "habitat, or other protected-site condition named in SB 9.",
    ),
    FactField(
        "two_unit_contributing_historic_location",
        TRI_STATE,
        ("two_unit",),
        "Whether the two-home project would be in a contributing structure in "
        "a state-listed historic district, or in a historic property or "
        "district protected by a city or county ordinance.",
    ),
    FactField(
        "two_unit_individually_listed_historic_property",
        TRI_STATE,
        ("two_unit",),
        "Whether the parcel is individually listed in the State Historic "
        "Resources Inventory or individually designated as a city or county "
        "landmark.",
    ),
    FactField(
        "lot_split_on_historic_landmark_site",
        TRI_STATE,
        ("lot_split",),
        "Whether the parcel is within a historical landmark property in the "
        "State Historic Resources Inventory or on a site designated or listed "
        "as a city or county landmark.",
    ),
    FactField(
        "lot_split_alters_historic_district_resource",
        TRI_STATE,
        ("lot_split",),
        "Whether the lot split would require demolition or alteration of a "
        "contributing structure or an existing exterior structural wall in a "
        "historic district listed by California or designated locally.",
    ),
    FactField(
        "parcel_created_by_sb9_split",
        TRI_STATE,
        ("lot_split",),
        "Whether this parcel was itself created by an earlier SB 9 lot split.",
    ),
    FactField(
        "adjacent_sb9_split_same_actor",
        TRI_STATE,
        ("lot_split",),
        "Whether the same owner, or someone acting with that owner, used SB 9 "
        "to split an adjacent parcel.",
    ),
    FactField(
        "proposed_lot_ratio_compliant",
        TRI_STATE,
        ("lot_split",),
        "Whether each proposed parcel would contain at least 40 percent of "
        "the original lot area.",
    ),
    FactField(
        "proposed_lot_size_compliant",
        TRI_STATE,
        ("lot_split",),
        "Whether both new lots would be at least 1,200 square feet, or meet a "
        "smaller minimum verified in a current local ordinance.",
    ),
)

FIELDS_BY_NAME: dict[str, FactField] = {f.name: f for f in FACT_FIELDS}
FACT_NAMES: tuple[str, ...] = tuple(f.name for f in FACT_FIELDS)


def material_fields(project_type: str) -> tuple[str, ...]:
    """The fields the browser form asks for a project type, in form order."""
    if project_type not in PROJECT_TYPES:
        return ()
    return tuple(f.name for f in FACT_FIELDS if project_type in f.applies_to)


def allowed_values(name: str) -> tuple[str, ...]:
    if name == "project_type":
        return PROJECT_TYPES
    field = FIELDS_BY_NAME.get(name)
    return field.values if field else ()
