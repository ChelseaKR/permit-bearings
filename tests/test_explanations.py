import copy
import json
import re
from dataclasses import replace
from pathlib import Path

import pytest
from demo.app import render_result_card, result_page

from permit_pathways.explanations import load_explanations, rule_fingerprint
from permit_pathways.screening import load_rules, screen

ROOT = Path(__file__).parent.parent
RULES_PATH = ROOT / "data" / "rules"
EXPLANATIONS_PATH = ROOT / "data" / "explanations" / "plain-language.json"


@pytest.fixture()
def rules():
    return load_rules(RULES_PATH)


@pytest.fixture()
def explanations(rules):
    return load_explanations(EXPLANATIONS_PATH, rules)


def _payload():
    return json.loads(EXPLANATIONS_PATH.read_text(encoding="utf-8"))


def _write_payload(tmp_path, payload):
    path = tmp_path / "plain-language.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_every_rule_has_one_versioned_explanation_with_source_date(rules, explanations):
    assert set(explanations) == {rule.rule_id for rule in rules}
    rules_by_id = {rule.rule_id: rule for rule in rules}
    for rule_id, explanation in explanations.items():
        assert re.fullmatch(r"\d+\.\d+\.\d+", explanation.version)
        assert explanation.source_verified_on == (
            rules_by_id[rule_id].citation.verified_on
        )
        assert explanation.rule_fingerprint == rule_fingerprint(rules_by_id[rule_id])
        assert explanation.review.status == "prototype_review_pending"
        assert explanation.review.reviewer is None


def test_spanish_copy_is_explicitly_an_unreviewed_machine_draft(explanations):
    for explanation in explanations.values():
        assert explanation.es is not None
        assert explanation.es.translation_status == "machine_draft"
        assert explanation.es.reviewer is None
        assert explanation.es.reviewed_on is None
        assert explanation.en.title
        assert explanation.es.title
        assert explanation.es.title != explanation.en.title
        assert explanation.es.summary != explanation.en.summary


def test_three_pilot_explanations_preserve_important_boundaries(explanations):
    ministerial = explanations["adu-ministerial-review"]
    assert ministerial.en.highlights is not None
    ministerial_text = " ".join(
        [
            ministerial.en.summary,
            ministerial.en.highlights.title,
            *(f"{item.label} {item.text}" for item in ministerial.en.highlights.items),
        ]
    )
    assert "15 business days" in ministerial_text
    assert "60 days" in ministerial_text
    assert "complete application" in ministerial_text
    assert "single-family home or multifamily building already exists" in (
        ministerial_text
    )
    assert "ministerial" not in ministerial.en.summary.lower()
    assert "discretionary" not in ministerial.en.summary.lower()
    assert all("?" in question for question in ministerial.en.confirm_with_staff)

    protected = explanations["adu-protected-minimum"]
    assert "do not have to build an 800-square-foot ADU" in (protected.en.summary)
    assert "every other applicable local development rule" in (protected.en.summary)

    height = explanations["adu-height-standards"]
    height_text = " ".join(
        [
            height.en.summary,
            *(f"{item.label} {item.text}" for item in height.en.highlights.items),
            *height.en.next_steps,
            *height.en.confirm_with_staff,
        ]
    ).lower()
    assert "attached or detached" in height_text
    assert "transit" in height_text
    assert "half-mile walking distance" in height_text
    assert "major transit stop" in height_text
    assert "high-quality transit corridor" in height_text
    assert "multistory multifamily" in height_text.replace("-", " ")
    assert "transit situation" in height_text
    assert "branch does not add" in height_text
    assert height.en.confirm_with_staff

    multifamily = explanations["adu-multifamily-66323"]
    multifamily_text = " ".join(
        [
            multifamily.en.summary,
            *(f"{item.label} {item.text}" for item in multifamily.en.highlights.items),
        ]
    )
    assert "At least one conversion ADU" in multifamily_text
    assert "blanket 16-foot cap" in multifamily_text

    proposed_multifamily = explanations["adu-multifamily-proposed-66323"]
    assert "no more than two detached ADUs" in (proposed_multifamily.en.summary)
    assert "conversion allowance does not apply yet" in (
        proposed_multifamily.en.summary
    )

    lot_split = explanations["sb9-urban-lot-split"]
    lot_split_text = " ".join(
        [
            lot_split.en.summary,
            *(f"{item.label} {item.text}" for item in lot_split.en.highlights.items),
            *lot_split.en.next_steps,
            *lot_split.en.confirm_with_staff,
        ]
    )
    assert "principal residence" in lot_split_text
    assert "at least three years" in lot_split_text
    assert "community land trust" in lot_split_text
    assert "nonprofit" in lot_split_text
    assert "1,200 square feet" in lot_split_text
    assert "verified current local ordinance" in lot_split_text
    assert "historic-landmark property" in lot_split_text
    assert "contributing structure" in lot_split_text


def test_woodland_copy_reports_adoption_without_claiming_conformance(
    explanations,
):
    woodland = explanations["woodland-adu-ordinance-2026"]
    text = " ".join(
        [
            woodland.en.title,
            woodland.en.summary,
            *woodland.en.next_steps,
            *woodland.en.confirm_with_staff,
        ]
    ).lower()
    assert "adopted" in text
    assert "does not establish actual conformance" in text
    assert "comparable-jurisdiction precedent" not in text


def test_high_priority_plain_language_records_avoid_policy_memo_phrasing(
    explanations,
):
    high_priority = (
        "adu-ministerial-review",
        "adu-height-standards",
        "adu-parking-limits",
        "adu-multifamily-66323",
        "adu-multifamily-proposed-66323",
        "sb9-urban-lot-split",
    )
    policy_phrases = (
        "candidate route",
        "completeness notice",
        "discretionary hearing",
        "state framework",
        "this screen identifies",
        "this rule points to",
        "in conjunction with",
    )
    for rule_id in high_priority:
        explanation = explanations[rule_id]
        assert not any(
            phrase in explanation.en.summary.lower() for phrase in policy_phrases
        )
        assert all("?" in question for question in explanation.en.confirm_with_staff)


def test_every_staff_prompt_is_a_direct_question_in_each_language(explanations):
    for rule_id, explanation in explanations.items():
        assert all(
            question.rstrip().endswith("?")
            for question in explanation.en.confirm_with_staff
        ), rule_id
        assert explanation.es is not None
        assert all(
            question.lstrip().startswith("¿") and question.rstrip().endswith("?")
            for question in explanation.es.confirm_with_staff
        ), rule_id


def test_every_locale_has_an_applicant_facing_title(explanations):
    for rule_id, explanation in explanations.items():
        assert explanation.en.title.strip(), rule_id
        assert explanation.es is not None
        assert explanation.es.title.strip(), rule_id
        assert "ministerial" not in explanation.en.title.lower(), rule_id
        assert "ministerial" not in explanation.es.title.lower(), rule_id


def test_copy_avoids_final_eligibility_approval_and_completeness_claims(explanations):
    def localized_text(localized):
        highlight_text = ()
        if localized.highlights is not None:
            highlight_text = (
                localized.highlights.title,
                *(
                    text
                    for item in localized.highlights.items
                    for text in (item.label, item.text)
                ),
            )
        return (
            localized.title,
            localized.summary,
            *highlight_text,
            *localized.next_steps,
            *localized.confirm_with_staff,
        )

    copy_text = " ".join(
        text
        for explanation in explanations.values()
        for text in (
            *localized_text(explanation.en),
            *localized_text(explanation.es),
        )
    ).lower()
    for prohibited in (
        "you qualify",
        "you are eligible",
        "your project is compliant",
        "your project complies",
        "will be approved",
        "guaranteed approval",
        "complete permit packet",
        "lista completa de documentos",
        "su proyecto cumple",
        "será aprobado",
    ):
        assert prohibited not in copy_text


def test_duplicate_or_orphaned_explanation_is_rejected(tmp_path, rules):
    duplicate = _payload()
    duplicate["entries"].append(copy.deepcopy(duplicate["entries"][0]))
    with pytest.raises(ValueError, match="duplicate"):
        load_explanations(_write_payload(tmp_path, duplicate), rules)

    orphan = _payload()
    orphan["entries"][0]["source_rule_id"] = "unknown-rule"
    with pytest.raises(ValueError, match="unknown rule"):
        load_explanations(_write_payload(tmp_path, orphan), rules)


def test_missing_explanation_and_source_date_drift_are_rejected(tmp_path, rules):
    missing = _payload()
    missing["entries"].pop()
    with pytest.raises(ValueError, match="missing rule IDs"):
        load_explanations(_write_payload(tmp_path, missing), rules)

    drifted = _payload()
    drifted["entries"][0]["source_verified_on"] = "2026-07-26"
    with pytest.raises(ValueError, match="does not match rule source date"):
        load_explanations(_write_payload(tmp_path, drifted), rules)

    predates_source = _payload()
    predates_source["entries"][0]["updated_on"] = "2026-07-26"
    with pytest.raises(ValueError, match="predates linked source date"):
        load_explanations(_write_payload(tmp_path, predates_source), rules)


def test_same_day_citation_drift_is_rejected(rules):
    changed_rules = [
        replace(
            rule,
            citation=replace(
                rule.citation,
                excerpt=(rule.citation.excerpt or "") + " changed",
            ),
        )
        if rule.rule_id == "adu-ministerial-review"
        else rule
        for rule in rules
    ]
    with pytest.raises(ValueError, match="citation fingerprint"):
        load_explanations(EXPLANATIONS_PATH, changed_rules)


@pytest.mark.parametrize(
    "changed_field,new_value",
    [
        ("criteria", [{"field": "project_type", "op": "eq", "value": "jadu"}]),
        ("notes", "Changed interpretation."),
        ("required_documents", ["Changed document hint"]),
        ("pathway", "Changed pathway title"),
    ],
)
def test_non_citation_rule_drift_is_rejected(changed_field, new_value, rules):
    target = next(rule for rule in rules if rule.rule_id == "adu-ministerial-review")
    changed_rules = [
        replace(rule, **{changed_field: new_value})
        if rule.rule_id == target.rule_id
        else rule
        for rule in rules
    ]
    with pytest.raises(ValueError, match="rule fingerprint"):
        load_explanations(EXPLANATIONS_PATH, changed_rules)


def test_review_claims_require_reviewer_date_and_method(tmp_path, rules):
    payload = _payload()
    payload["entries"][0]["review"]["status"] = "human_reviewed"
    with pytest.raises(ValueError, match="requires reviewer, date, method"):
        load_explanations(_write_payload(tmp_path, payload), rules)

    translation = _payload()
    translation["entries"][0]["es"]["translation_status"] = "human_reviewed"
    with pytest.raises(ValueError, match="requires reviewer, date, method"):
        load_explanations(_write_payload(tmp_path, translation), rules)

    wrong_version = _payload()
    review = wrong_version["entries"][0]["review"]
    review.update(
        {
            "status": "human_reviewed",
            "reviewer": "Named reviewer",
            "reviewed_on": "2026-07-28",
            "method": "Compared line by line",
            "reviewed_version": "0.9.0",
        }
    )
    with pytest.raises(ValueError, match="reviewed_version must match"):
        load_explanations(_write_payload(tmp_path, wrong_version), rules)


def test_tolerant_display_load_is_per_record_and_falls_back_to_english(tmp_path, rules):
    payload = _payload()
    missing_spanish_id = payload["entries"][0]["source_rule_id"]
    payload["entries"][0].pop("es")
    invalid_record_id = payload["entries"][1]["source_rule_id"]
    payload["entries"][1]["review"]["status"] = "invented_status"
    path = _write_payload(tmp_path, payload)

    with pytest.raises(ValueError):
        load_explanations(path, rules)

    display = load_explanations(path, rules, strict=False)
    assert display[missing_spanish_id].es is None
    assert display[missing_spanish_id].localized("es") == (
        display[missing_spanish_id].en
    )
    assert invalid_record_id not in display
    assert len(display) == len(rules) - 1


def test_malformed_highlights_are_rejected_or_dropped_with_the_record(tmp_path, rules):
    payload = _payload()
    rule_id = payload["entries"][0]["source_rule_id"]
    payload["entries"][0]["en"]["highlights"]["items"][0]["text"] = ""
    path = _write_payload(tmp_path, payload)

    with pytest.raises(ValueError, match="highlights"):
        load_explanations(path, rules)
    assert rule_id not in load_explanations(path, rules, strict=False)


def test_tolerant_display_load_degrades_missing_or_malformed_data_to_empty(
    tmp_path, rules
):
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{not valid JSON", encoding="utf-8")

    with pytest.raises(ValueError, match="could not be loaded"):
        load_explanations(malformed, rules)
    assert load_explanations(malformed, rules, strict=False) == {}
    assert load_explanations(tmp_path / "missing.json", rules, strict=False) == {}


def test_loading_explanations_cannot_change_deterministic_matches(rules):
    intake = {
        "project_type": "adu",
        "primary_dwelling_status": "existing_single_family",
        "adu_project_form": "new_detached",
        "unpermitted_existing": "no",
        "jurisdiction": "davis",
    }
    before = [result.rule.rule_id for result in screen(intake, rules)]
    load_explanations(EXPLANATIONS_PATH, rules)
    after = [result.rule.rule_id for result in screen(intake, rules)]
    assert after == before


def test_python_demo_groups_decision_records_and_keeps_source_visible():
    form = {
        "project_type": ["adu"],
        "jurisdiction": ["davis"],
        "primary_dwelling_status": ["existing_single_family"],
        "adu_project_form": ["new_detached"],
        "unpermitted_existing": ["no"],
    }
    page = result_page(form, "en")
    assert "Possible permit paths and rules" in page
    assert "Possible permit paths" in page
    assert "Rules that may apply" in page
    assert "Local process information" in page
    assert 'data-rule-id="davis-local-adu-process"' in page
    assert "About these explanations" in page
    assert "Deadlines in this rule" in page
    assert "<strong>15 business days:</strong>" in page
    assert "source has no date on file" in page
    assert "<b>Source:</b>" in page
    assert "<details>" in page


def test_python_demo_labels_spanish_draft_and_has_evidence_fallback(
    rules, explanations
):
    intake = {
        "project_type": "adu",
        "primary_dwelling_status": "existing_single_family",
        "adu_project_form": "new_detached",
        "unpermitted_existing": "no",
        "jurisdiction": "example-city",
    }
    result = screen(intake, rules)[0]
    spanish = render_result_card(result, explanations[result.rule.rule_id], "es")
    assert "Borrador en español · creado con IA" in spanish
    assert "Borrador de explicación · creado con IA" in spanish
    assert '<p lang="es">' in spanish
    assert "<b>Fuente:</b>" in spanish

    fallback = render_result_card(result, None, "en")
    assert "This explanation is not available" in fallback
    assert result.rule.citation.source in fallback

    english_fallback = replace(explanations[result.rule.rule_id], es=None)
    spanish_fallback = render_result_card(result, english_fallback, "es")
    assert "Se muestra la explicación en inglés" in spanish_fallback
    assert "Borrador de explicación · creado con IA" in spanish_fallback
    assert '<p lang="en">' in spanish_fallback

    reviewed_translation = replace(
        explanations[result.rule.rule_id].es,
        translation_status="human_reviewed",
        reviewer="Named translator",
        reviewed_on="2026-07-28",
        method="Compared line by line",
        reviewed_version="1.0.0",
    )
    mixed_status = render_result_card(
        result,
        replace(
            explanations[result.rule.rule_id],
            es=reviewed_translation,
        ),
        "es",
    )
    assert "Borrador de explicación · creado con IA" in mixed_status
    assert "Traducción revisada por una persona" in mixed_status


def test_python_demo_withholds_actions_for_unverified_and_stale_rules(
    rules, explanations
):
    davis = next(
        result
        for result in screen(
            {
                "project_type": "adu",
                "primary_dwelling_status": "existing_single_family",
                "adu_project_form": "new_detached",
                "unpermitted_existing": "no",
                "jurisdiction": "davis",
            },
            rules,
        )
        if result.rule.rule_id == "davis-local-adu-process"
    )
    unverified = render_result_card(davis, explanations[davis.rule.rule_id], "en")
    assert "We are not showing next steps" in unverified
    assert 'class="plain-layer"' not in unverified
    assert "<b>Source:</b>" in unverified
    assert "No supporting excerpt is recorded" in unverified
    assert "site plan and floor plan" not in unverified
    assert davis.rule.notes not in unverified

    current = screen(
        {
            "project_type": "adu",
            "primary_dwelling_status": "existing_single_family",
            "adu_project_form": "new_detached",
            "unpermitted_existing": "no",
            "jurisdiction": "example-city",
        },
        rules,
    )[0]
    stale_rule = replace(
        current.rule,
        citation=replace(current.rule.citation, verified_on="2020-01-01"),
    )
    stale = render_result_card(
        replace(current, rule=stale_rule),
        explanations[current.rule.rule_id],
        "en",
    )
    assert "We are not showing next steps" in stale
    assert 'class="plain-layer"' not in stale
    assert current.rule.required_documents[0] not in stale
    assert current.rule.notes not in stale


def test_python_demo_escapes_explanation_copy(rules, explanations):
    result = screen(
        {
            "project_type": "adu",
            "primary_dwelling_status": "existing_single_family",
            "adu_project_form": "new_detached",
            "unpermitted_existing": "no",
            "jurisdiction": "example-city",
        },
        rules,
    )[0]
    explanation = explanations[result.rule.rule_id]
    unsafe = replace(
        explanation,
        en=replace(explanation.en, summary="<script>alert('no')</script>"),
    )
    rendered = render_result_card(result, unsafe, "en")

    assert "<script>alert" not in rendered
    assert "&lt;script&gt;alert" in rendered
