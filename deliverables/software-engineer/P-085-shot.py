#!/usr/bin/env python3
"""Render the P-085/P-086 (D-169) workbench card for SUB-562 (T-128) to HTML for the screenshot.

D-069: nothing real is written. The model answer comes from a temp copy of the T-128 run cache, the model call is blocked,
the inbox folder is a temp copy, and the page goes to the folder you pass. No model call.

Run: python deliverables/software-engineer/P-085-shot.py <t128-cache-dir> <out-html-folder>
"""
import os
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for sub in ("app", "ai", "models"):
    sys.path.insert(0, str(ROOT / "underwriting_pipeline" / sub))


def main() -> int:
    cache, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="p085-"))
    shutil.copytree(cache, tmp / "cache")
    shutil.copytree(ROOT / "simulation" / "inbox" / "SUB-562", tmp / "SUB-562")
    os.environ.update(LLM_CACHE_DIR=str(tmp / "cache"), LLM_BASE_URL="https://api.groq.com/openai/v1", LLM_MODEL="qwen/qwen3.8-27b", LLM_API_KEY="blocked-not-a-key")

    def blocked(*_a, **_k):
        raise SystemExit("model call attempted; the cache must answer")

    urllib.request.urlopen = blocked
    import points  # noqa: E402
    import prepare  # noqa: E402
    import workbench  # noqa: E402

    report = prepare.process_submission(tmp / "SUB-562")
    report["saved_hash"] = "p085" + "0" * 60
    card = {"id": "SUB-562", "report": report, "files": sorted(p.name for p in (tmp / "SUB-562").iterdir()), "ignored": [],
            "route": "hold", "score": points.score_run(report), "snippets": {}}
    (out / "P-085-SUB-562.html").write_text(workbench.render([card], None))
    print(f"rendered to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
