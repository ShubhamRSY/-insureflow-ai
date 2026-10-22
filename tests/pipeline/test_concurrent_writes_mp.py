import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# The worker runs in its own process and imports the pipeline from this checkout, the same way
# tests/pipeline/conftest.py does. It used to live in /tmp outside the repo, so CI could not find it.
WORKER = """
import sys
from pathlib import Path
root = Path(sys.argv[1])
for folder in ("underwriting_pipeline/ai", "underwriting_pipeline/models", "underwriting_pipeline/app"):
    sys.path.insert(0, str(root / folder))
import package, prepare, workbench
dlog, uw, ext, start, count = Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6])
package.UNDERWRITERS = uw
prepare.EXTRACT_DIR = ext
for i in range(start, start + count):
    workbench.record_decision({"underwriter_id": "user", "submission": "SUB-901", "action": "edit", "reason": f"e{i}",
                               "field_id": "named_insured", "new_value": f"x{i}"}, dlog)
"""


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
    total = 32
    per = 8
    for p in range(4):
        proc = subprocess.Popen([sys.executable, "-c", WORKER, str(ROOT), str(dlog), str(uw), str(ext), str(p*per), str(per)], cwd=str(tmp_path))
        procs.append(proc)
    for pr in procs:
        assert pr.wait() == 0
    lines = dlog.read_text().splitlines()
    assert len(lines) == total
    seqs = [json.loads(l)["seq"] for l in lines]
    assert sorted(seqs) == list(range(1, total + 1))
