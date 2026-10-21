from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

import package
import prepare
import scope

ROOT = Path(__file__).resolve().parents[2]
INBOX = ROOT / "simulation" / "inbox"


def saved_run(submission: str, status: str, scope_result: dict | None = None, manifest: list | None = None) -> dict:
    payload = {"submission": submission, "status": status, "scope": scope_result, "input_manifest": manifest or []}
    payload["hash_algorithm"] = prepare.HASH_ALGORITHM
    payload["saved_hash"] = prepare.hash_payload(payload)
    return payload


def write_run(folder: Path, submission: str, **kw) -> dict:
    payload = saved_run(submission, **kw)
    (folder / f"{submission}.json").write_text(json.dumps(payload))
    return payload


def test_refusal_reasons_cover_every_post_route():
    assert set(package.__dict__)  # module loaded
    expected = {"/confirm-market", "/decision", "/mark-code", "/cooking-call", "/close-subjectivity", "/send", "/approve-draft"}
    from workbench import REFUSED_AS

    assert set(REFUSED_AS) == expected
    assert all(isinstance(reason, str) and reason.strip() for reason in REFUSED_AS.values())


def test_a_send_with_no_saved_run_is_refused(tmp_path: Path):
    with pytest.raises(ValueError, match="no saved run"):
        package.send_to_carrier("SUB-999", "user", tmp_path, user_line="send to carrier SUB-999")


@pytest.mark.parametrize("status", prepare.REFUSED_STATUSES)
def test_agency_problem_refuses_every_refused_status(monkeypatch, status):
    report = saved_run("SUB-901", status, {"in_scope": False, "reasons": [{"code": "scanned_application", "text": "Manual intake: scanned application"}]})
    monkeypatch.setattr(prepare, "read_saved_run", lambda submission, extract_dir=None: report)
    problem = package.agency_problem("SUB-901")
    assert problem
    if status == prepare.MANUAL_INTAKE:
        assert "manual intake" in problem and "scanned application" in problem


def test_an_open_conflict_blocks_an_account_manager_send():
    problem = package.conflict_problem({"conflicts": [{"field": "operations", "resolution": "open"}]})
    assert "open conflict" in problem


def test_a_resolved_conflict_does_not_block():
    assert package.conflict_problem({"conflicts": [{"field": "operations", "resolution": "resolved"}]}) == ""


def test_scope_problem_refuses_a_file_the_detector_now_puts_out_of_scope(tmp_path: Path):
    run_dir, inbox = tmp_path / "extract", tmp_path / "inbox"
    run_dir.mkdir()
    shutil.copytree(INBOX / "SUB-233", inbox / "SUB-233")
    write_run(run_dir, "SUB-233", status="complete", scope_result={"version": scope.VERSION, "in_scope": True, "reasons": []})

    problem = prepare.scope_problem("SUB-233", extract_dir=run_dir, inbox=inbox)

    assert problem.startswith("out of pilot scope at send time (multiple locations")


def test_scope_problem_passes_an_in_scope_file(tmp_path: Path):
    run_dir, inbox = tmp_path / "extract", tmp_path / "inbox"
    run_dir.mkdir()
    (inbox / "SUB-900").mkdir(parents=True)
    (inbox / "SUB-900" / "application.md").write_text(
        "Named Insured: Example LLC\nPremises: 100 Main St\nEffective Date: 2026-01-01\nConstruction: masonry\nOperations: office\n"
    )
    write_run(run_dir, "SUB-900", status="complete", scope_result={"version": scope.VERSION, "in_scope": True, "reasons": []})

    assert prepare.scope_problem("SUB-900", extract_dir=run_dir, inbox=inbox) == ""


def test_manifest_problem_refuses_changed_documents(tmp_path: Path):
    run_dir, inbox = tmp_path / "extract", tmp_path / "inbox"
    run_dir.mkdir()
    (inbox / "SUB-901").mkdir(parents=True)
    (inbox / "SUB-901" / "application.md").write_text("before")
    write_run(run_dir, "SUB-901", status="complete", manifest=prepare.folder_manifest(inbox / "SUB-901"))
    assert prepare.manifest_problem("SUB-901", extract_dir=run_dir, inbox=inbox) == ""

    (inbox / "SUB-901" / "application.md").write_text("after")

    assert "changed since extraction" in prepare.manifest_problem("SUB-901", extract_dir=run_dir, inbox=inbox)


def test_needs_review_ids_lists_flagged_values_only():
    report = {
        "fields": [
            {"field_id": "operations", "value": "office", "needs_review": True},
            {"field_id": "premises", "value": "100 Main St", "needs_review": False},
            {"field_id": "sales", "value": None, "needs_review": True},
        ],
        "cooking": {"equipment": {"state": "needs_review"}},
    }
    assert package.needs_review_ids(report) == ["operations", "cooking_equipment"]
