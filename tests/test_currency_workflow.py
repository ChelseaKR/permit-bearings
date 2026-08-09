from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "currency.yml"


def _workflow_step(workflow: str, name: str) -> str:
    marker = f"      - name: {name}\n"
    start = workflow.index(marker)
    end = workflow.find("\n      - name: ", start + len(marker))
    return workflow[start:] if end == -1 else workflow[start:end]


def test_review_package_requires_a_nonempty_changed_source_list():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    watch_step = _workflow_step(workflow, "Re-fetch watched sources and diff hashes")
    package_step = _workflow_step(
        workflow,
        "Build the exact re-verification review package",
    )
    upload_step = _workflow_step(
        workflow,
        "Retain the exact re-verification review package",
    )

    assert 'payload.get("changed_source_ids")' in watch_step
    assert 'echo "has_changed_sources=$has_changed_sources"' in watch_step
    assert "if: steps.watch.outputs.has_changed_sources == 'true'" in package_step
    assert "if: steps.watch.outputs.has_changed_sources == 'true'" in upload_step
    assert "steps.watch.outputs.exit_code == '1'" not in package_step
    assert "steps.watch.outputs.exit_code == '1'" not in upload_step


def test_stale_only_or_golden_regression_still_opens_currency_alert():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    alert_step = _workflow_step(
        workflow, "Open an issue when currency review is needed"
    )

    assert "always() && steps.watch.outputs.exit_code == '1'" in alert_step
    assert "changed watched sources, stale rules, or a golden regression" in alert_step
    assert "has_changed_sources" not in alert_step


def test_package_failure_cannot_suppress_the_currency_alert():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    package_step = _workflow_step(
        workflow,
        "Build the exact re-verification review package",
    )
    upload_step = _workflow_step(
        workflow,
        "Retain the exact re-verification review package",
    )
    alert_step = _workflow_step(
        workflow, "Open an issue when currency review is needed"
    )

    assert workflow.index(package_step) < workflow.index(alert_step)
    assert workflow.index(upload_step) < workflow.index(alert_step)
    assert "if: ${{ always() && steps.watch.outputs.exit_code == '1' }}" in alert_step
