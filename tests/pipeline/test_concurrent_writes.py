import json
from concurrent.futures import ThreadPoolExecutor

import package
import prepare
import workbench


def test_concurrent_decision_appends(tmp_path, monkeypatch):
    dlog = tmp_path / "decisions.jsonl"
    uw = tmp_path / "underwriters.json"
    uw.write_text(json.dumps({"underwriters": [{"id": "user"}]}))
    monkeypatch.setattr(package, "UNDERWRITERS", uw)
    ext = tmp_path / "extractions"
    ext.mkdir(parents=True)
    report = {
        "submission": "SUB-901",
        "saved_hash": "abc123",
        "fields": [{"field_id": "named_insured", "value": "x"}],
        "conflicts": [],
        "status": "complete",
        "system_status": "ok",
        "status_safety": "ok",
        "status_automation": "ok",
        "scope": {"in_scope": True},
        "manual_intake": False,
        "reason_codes": [],
        "points": {"total": 10},
        "points_version": "p",
        "model_version": "m",
        "prompt_version": "p",
        "cache_key": None,
    }
    (ext / "SUB-901.json").write_text(json.dumps(report))
    monkeypatch.setattr(prepare, "EXTRACT_DIR", ext)

    def do_edit(i):
        return workbench.record_decision({"underwriter_id": "user", "submission": "SUB-901", "action": "edit", "reason": f"e{i}", "field_id": "named_insured", "new_value": f"x{i}"}, dlog)

    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(do_edit, range(16)))
    assert len(results) == 16
    lines = dlog.read_text().splitlines()
    assert len(lines) == 16
    seqs = [json.loads(l)["seq"] for l in lines]
    assert sorted(seqs) == list(range(1, 17))
