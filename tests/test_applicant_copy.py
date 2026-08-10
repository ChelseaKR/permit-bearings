import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check_applicant_copy.mjs"
APPLICATION = ROOT / "assets" / "demo.js"


def run_checker(source: Path = APPLICATION) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["node", str(CHECKER), "--source", str(source), "--json"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )


def changed_application(tmp_path: Path, before: str, after: str) -> Path:
    source = APPLICATION.read_text(encoding="utf-8")
    assert source.count(before) == 1
    changed = tmp_path / "demo.js"
    changed.write_text(source.replace(before, after), encoding="utf-8")
    return changed


def changed_application_many(
    tmp_path: Path,
    replacements: list[tuple[str, str]],
) -> Path:
    source = APPLICATION.read_text(encoding="utf-8")
    for before, after in replacements:
        assert source.count(before) == 1
        source = source.replace(before, after)
    changed = tmp_path / "demo.js"
    changed.write_text(source, encoding="utf-8")
    return changed


def result_for(
    source: Path = APPLICATION,
) -> tuple[subprocess.CompletedProcess[str], dict]:
    completed = run_checker(source)
    return completed, json.loads(completed.stdout)


def test_applicant_copy_catalog_passes_strict_contract() -> None:
    completed, result = result_for()

    assert completed.returncode == 0, completed.stderr
    assert result["status"] == "pass"
    assert result["locales"] == ["en", "es"]
    assert result["catalog_keys"] > 100
    assert result["placeholder_checks"] > 0
    assert result["option_identifier_checks"] > 0
    assert result["pseudolocalization"]["status"] == "pass"
    assert result["pseudolocalization"]["expansion_ratio"] >= 1.2
    assert result["pseudolocalization"]["mode"] == "copy_leaf_expansion_test"
    assert result["pseudolocalization"]["generated_catalog"] is False
    assert result["pseudolocalization"]["rendered_layout"] is False
    assert result["issues"] == []
    assert result["claim_boundary"] == {
        "semantic_translation_review": "not_evaluated",
        "spanish_applicant_readiness": "not_claimed",
        "layout_compatibility": "not_evaluated",
    }


def test_catalog_rejects_missing_spanish_key(tmp_path: Path) -> None:
    source = changed_application(tmp_path, '    langBtn: "English",\n', "")
    completed, result = result_for(source)

    assert completed.returncode == 1
    assert any(
        item["code"] == "missing_spanish_key" and item["path"] == "STRINGS.langBtn"
        for item in result["issues"]
    )


def test_catalog_rejects_formatter_arity_drift(tmp_path: Path) -> None:
    source = changed_application(
        tmp_path,
        "    profileIntro: jurisdiction => `Este perfil",
        "    profileIntro: (jurisdiction, unused) => `Este perfil",
    )
    completed, result = result_for(source)

    assert completed.returncode == 1
    assert any(
        item["code"] == "function_arity_mismatch"
        and item["path"] == "STRINGS.profileIntro"
        for item in result["issues"]
    )


def test_catalog_rejects_formatter_placeholder_loss(tmp_path: Path) -> None:
    source = changed_application(
        tmp_path,
        "    decisionBoundaryUnknownNext: jurisdiction => `Confirme esos datos con el personal de ${jurisdiction}.`,",
        '    decisionBoundaryUnknownNext: jurisdiction => "Confirme esos datos con el personal local.",',
    )
    completed, result = result_for(source)

    assert completed.returncode == 1
    assert any(
        item["code"] == "placeholder_mismatch"
        and item["path"] == "STRINGS.decisionBoundaryUnknownNext"
        for item in result["issues"]
    )


def test_catalog_rejects_blank_singular_formatter_branch(tmp_path: Path) -> None:
    source = changed_application_many(
        tmp_path,
        [
            (
                '    resultCount: count => count === 1 ? "1 result found." : `${count} results found.`,',
                '    resultCount: count => count === 1 ? "" : `${count} results found.`,',
            ),
            (
                '    resultCount: count => count === 1 ? "Se encontró 1 resultado." : `Se encontraron ${count} resultados.`,',
                '    resultCount: count => count === 1 ? "" : `Se encontraron ${count} resultados.`,',
            ),
        ],
    )
    completed, result = result_for(source)

    assert completed.returncode == 1
    assert any(
        item["code"] == "blank_function_output"
        and item["path"] == "STRINGS.resultCount"
        and "singular" in item["message"]
        for item in result["issues"]
    )


def test_catalog_rejects_static_placeholder_loss(tmp_path: Path) -> None:
    source = changed_application_many(
        tmp_path,
        [
            (
                '    tagline: "Find a candidate route. See the sources behind it. Take open questions to staff.",',
                '    tagline: "Open {record_id} and take questions to staff.",',
            ),
            (
                '    tagline: "Encuentre una posible ruta. Vea las fuentes que la respaldan. Consulte las preguntas pendientes con el personal de la agencia.",',
                '    tagline: "Abra el registro y consulte al personal.",',
            ),
        ],
    )
    completed, result = result_for(source)

    assert completed.returncode == 1
    assert any(
        item["code"] == "static_placeholder_mismatch"
        and item["path"] == "STRINGS.tagline"
        for item in result["issues"]
    )


def test_catalog_accepts_a_translated_two_string_copy_list(tmp_path: Path) -> None:
    source = changed_application_many(
        tmp_path,
        [
            (
                '    tagline: "Find a candidate route. See the sources behind it. Take open questions to staff.",',
                '    tagline: "Find a candidate route. See the sources behind it. Take open questions to staff.",\n    testTwoItemCopy: ["First", "Second"],',
            ),
            (
                '    tagline: "Encuentre una posible ruta. Vea las fuentes que la respaldan. Consulte las preguntas pendientes con el personal de la agencia.",',
                '    tagline: "Encuentre una posible ruta. Vea las fuentes que la respaldan. Consulte las preguntas pendientes con el personal de la agencia.",\n    testTwoItemCopy: ["Primero", "Segundo"],',
            ),
        ],
    )
    completed, result = result_for(source)

    assert completed.returncode == 0, completed.stderr
    assert result["status"] == "pass"


def test_catalog_rejects_option_identifier_drift(tmp_path: Path) -> None:
    source = changed_application(
        tmp_path,
        '    types: [["adu","Vivienda accesoria',
        '    types: [["adu_changed","Vivienda accesoria',
    )
    completed, result = result_for(source)

    assert completed.returncode == 1
    assert any(
        item["code"] == "option_identifier_mismatch"
        and item["path"] == "STRINGS.types[0][0]"
        for item in result["issues"]
    )


def test_catalog_rejects_load_marker_drift(tmp_path: Path) -> None:
    source = changed_application(
        tmp_path,
        "const STRINGS = {",
        "const APPLICANT_STRINGS = {",
    )
    completed, result = result_for(source)

    assert completed.returncode == 1
    assert result["issues"] == [
        {
            "code": "catalog_load_failed",
            "path": "STRINGS",
            "message": "expected exactly one applicant-copy catalog start marker",
        }
    ]
