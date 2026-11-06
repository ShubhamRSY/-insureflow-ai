#!/usr/bin/env python3
"""Render P-087/P-088 (D-170) workbench cards to HTML for the screenshot.

D-069: nothing real is written. SUB-550 (T-128) is read from a temp copy of the run cache with the model call blocked,
then its operations line is set to a housing-program class (P-088) and to a Spanish bar class (P-087). Synthetic cards.

Run: python deliverables/software-engineer/P-088-shot.py <t128-cache-dir> <out-html-folder>
"""
import copy
import os
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for sub in ("app", "ai", "models"):
    sys.path.insert(0, str(ROOT / "underwriting_pipeline" / sub))

CASES = (("SUB-550", "Student housing, 24 units, three stories", "yes"),
         ("SUB-551", "Vivienda subsidiada, 24 unidades", "no"),
         ("SUB-552", "Restaurante con cantina", "yes"))


def main() -> int:
    cache, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="p088-"))
    shutil.copytree(cache, tmp / "cache")
    shutil.copytree(ROOT / "simulation" / "inbox" / "SUB-550", tmp / "SUB-550")
    os.environ.update(LLM_CACHE_DIR=str(tmp / "cache"), LLM_BASE_URL="https://api.groq.com/openai/v1", LLM_MODEL="qwen/qwen3.8-27b", LLM_API_KEY="blocked-not-a-key")

    def blocked(*_a, **_k):
        raise SystemExit("model call attempted; the cache must answer")

    urllib.request.urlopen = blocked
    import points  # noqa: E402
    import prepare  # noqa: E402
    import workbench  # noqa: E402

    base = prepare.process_submission(tmp / "SUB-550")
    cards = []
    for sid, ops, spr in CASES:
        report = copy.deepcopy(base)
        report["sprinklers"] = spr
        for f in report["fields"]:
            if f["field_id"] == "operations":
                f.update(value=ops, quote=ops, context=ops)
        report["saved_hash"] = "p088" + "0" * 60
        m = workbench.match(report)
        cards.append({"id": sid, "report": report, "files": sorted(p.name for p in (tmp / "SUB-550").iterdir()), "ignored": [],
                      "route": m["route"], "note": m["note"], "suggested": m["suggested"], "provisional": m.get("provisional_label") and m,
                      "score": points.score_run(report), "snippets": {}})
        print(sid, m["route"], "|", m["note"])
    (out / "P-088-cards.html").write_text(workbench.render(cards, None))
    print(f"rendered to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
