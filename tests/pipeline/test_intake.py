from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

import intake


def test_intake_hashes_each_document():
    record = intake.intake([("application.md", b"named insured: Example LLC\n")])
    assert record["synthetic"] is True
    assert record["submission_id"]
    doc = record["documents"][0]
    assert doc["filename"] == "application.md"
    assert doc["sha256"] == hashlib.sha256(b"named insured: Example LLC\n").hexdigest()
    assert doc["size"] == len(b"named insured: Example LLC\n")


def test_intake_refuses_an_empty_pack():
    with pytest.raises(ValueError):
        intake.intake([])


def test_intake_refuses_a_document_without_bytes():
    with pytest.raises(ValueError):
        intake.intake([("application.md", None)])


def test_scan_inbox_reads_each_submission_folder_sorted(tmp_path: Path):
    (tmp_path / "SUB-002").mkdir()
    (tmp_path / "SUB-002" / "application.md").write_text("b")
    (tmp_path / "SUB-001").mkdir()
    (tmp_path / "SUB-001" / "email.md").write_text("a")
    (tmp_path / "notes").mkdir()

    found = intake.scan_inbox(str(tmp_path))

    assert [record["folder"] for record in found] == ["SUB-001", "SUB-002"]
    assert [d["filename"] for d in found[0]["documents"]] == ["email.md"]
    assert found[0]["submission_id"]
