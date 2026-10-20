import json
import subprocess
import sys
from pathlib import Path


def test_multiprocess_concurrent_appends(tmp_path):
    dlog = tmp_path / "decisions.jsonl"
    uw = tmp_path / "underwriters.json"
    uw.write_text(json.dumps({"underwriters": [{"id": "user"}]}))
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
    procs = []
    worker = '/tmp/concurrent_append_worker2.py'
    total = 32
    per = 8
    for p in range(4):
        proc = subprocess.Popen([sys.executable, worker, str(dlog), str(uw), str(ext), str(p*per), str(per)], cwd=str(tmp_path))
        procs.append(proc)
    for pr in procs:
        assert pr.wait() == 0
    lines = dlog.read_text().splitlines()
    assert len(lines) == total
    seqs = [json.loads(l)["seq"] for l in lines]
    assert sorted(seqs) == list(range(1, total + 1))
