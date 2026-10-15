"""D-083 B-305: dry check of eval_holdout_107.py with fake reports, no model call. Run: env -u LLM_API_KEY .venv/bin/python deliverables/ai-engineer/analysis/check_eval_holdout_107.py "$PWD" """
import sys, tempfile
from pathlib import Path
repo = Path(sys.argv[1]); sys.path.insert(0, str(repo / "underwriting_pipeline/ai"))
import eval_holdout_107 as e, prepare, regression_dev as r
tmp = Path(tempfile.mkdtemp())
(tmp / "SUB-107.md").write_text("- Status: complete\n- Named insured: A LLC\n- Premises: 1 Main St, Austin, TX 78701\n- Effective date: 2026-12-01\n- Operations: dental office\n- Sales: 100000\n- TIV: 500000\n- Construction: frame\n- Year built: 1990\n- Loss runs: valued through 2026-09-30\n- Claims: 0\n- Conflict: none\n- Expected carrier route: carrier_a\n")
e.GOLD = tmp
vals = {"named_insured": "A LLC", "premises_address": "1 Main St, Austin, TX 78701", "effective_date": "2026-12-01", "operations": "dental office",
        "sales_or_payroll": "100000", "tiv_building": "500000", "construction": "frame", "year_built": "1990", "loss_run_valued_through": "2026-09-30"}
def fake(folder, **k):
    return {"fields": [{"field_id": f, "value": v, "reason": "x"} for f, v in vals.items()], "conflicts": [], "complete": True, "error": None}
prepare.process_submission = fake
row = e.score_one("SUB-107"); assert set(row["checks"].values()) == {"hit"}, row; assert row["call"] == "not sent: no readable text", row
vals["effective_date"] = "12/01/2026"; assert e.score_one("SUB-107")["checks"]["effective_date"] == "miss"
vals["effective_date"] = None; assert e.score_one("SUB-107")["checks"]["effective_date"] == "miss"
prepare.process_submission = lambda f, **k: {**fake(f), "error": "rate_limit_429"}
row = e.score_one("SUB-107"); assert set(row["checks"].values()) == {"call_failed"} and row["call"] == "call failed: rate_limit_429", row
assert len(e.IDS) == 20 and e.IDS[0] == "SUB-107" and e.IDS[-1] == "SUB-126"
print("eval_holdout_107 base check ok", e.commit()[0][:8], e.LABEL)
vals["effective_date"]="2026-12-01"; vals["premises_address"]="1 Main St, Austin, TX 78701 (shop and yard)"
prepare.process_submission = fake
assert e.score_one("SUB-107")["checks"]["premises"] == "hit"
vals["premises_address"]="10 Main St, Austin, TX 78701 (shop)"; assert e.score_one("SUB-107")["checks"]["premises"] == "miss"
assert e.address("4102 Mesquite Bend Rd, Lubbock, TX 79424 (shop and yard)") == "4102 Mesquite Bend Rd, Lubbock, TX 79424"
print("eval_holdout_107 B-305 check ok")
