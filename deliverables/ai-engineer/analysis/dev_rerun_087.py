"""D-083 item 3: development check, not a hold-out score. Re-extract SUB-087..106 (development data since D-082) with the
current code, scored by the frozen eval_holdout_087.py into dev file names; its published output paths are never written.
Uncached: run with LLM_CACHE_DIR pointing at a new empty folder. Failed calls are retried by regression_dev.score_retry.

Run: LLM_CACHE_DIR=<empty dir> .venv/bin/python deliverables/ai-engineer/analysis/dev_rerun_087.py
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("LLM_MAX_WAIT", "1800")
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "underwriting_pipeline" / "ai"))
import eval_holdout_087 as scorer  # noqa: E402
import llm_extract  # noqa: E402
import regression_dev  # noqa: E402

EVALS = ROOT / "deliverables" / "ai-engineer" / "evals"
scorer.OUT_JSON, scorer.OUT_MD = EVALS / "dev-SUB-087-106-D-083.json", EVALS / "dev-SUB-087-106-D-083.md"
plain = scorer.score_one
scorer.score_one = lambda sid: regression_dev.score_retry(scorer, sid, plain)
llm_extract.provider_guard(calling=False)
scorer.main()
regression_dev.report_failures()
md = scorer.OUT_MD.read_text().replace("# Hold-out extraction score — SUB-087 through SUB-106",
                                        "# DEVELOPMENT CHECK — SUB-087 through SUB-106 (D-083), not a hold-out score", 1)
scorer.OUT_MD.write_text(md.replace("- Scored by @model-risk with this file unchanged after the gold answers were written.",
                                    "- Development data since D-082: the gold was seen while the code changed (P-035, P-036). Not a hold-out.", 1))
