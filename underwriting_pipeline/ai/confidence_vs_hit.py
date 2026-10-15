"""B-222: confidence versus hit, from cached model results only. A report, not a UI change.

Run (cache copied first, so nothing real is written):
  cp -R underwriting_pipeline/cache $SCRATCH/cache
  LLM_CACHE_DIR=$SCRATCH/cache LLM_BASE_URL=https://api.groq.com/openai/v1 LLM_MODEL=qwen/qwen3.8-27b \
    .venv/bin/python underwriting_pipeline/ai/confidence_vs_hit.py

Reads the cached model reply for each of SUB-017..076 that has one, runs the unchanged gate (llm_extract.accept_field)
on every item (and on both sides of every conflict), and judges each value against gold with eval_holdout's hit_*
functions (read-only; no scorer or score file is edited). _post raises, so no model call is possible.
A value is "stored" if the gate kept it, "dropped" if the gate removed it (the raw model value is judged either way).
Correct: the value passes the scorer's comparison to the gold line. A null is never counted. Gold "both" premises
and fields with no gold line (effective_date) are not judged.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import eval_holdout as sc  # noqa: E402  (read-only: parse_gold and hit_*)
import llm_extract  # noqa: E402
import sources  # noqa: E402

OUT = ROOT / "deliverables" / "ai-engineer"
BINS = ("<0.50", "0.50-0.74", "0.75-0.89", "0.90-1.00")
# stored field id -> (gold key, comparison)
JUDGE = {
    "named_insured": ("named insured", sc.hit_named),
    "premises_address": ("premises", lambda g, v: sc.hit_named(g, v)),
    "operations": ("operations", sc.hit_ops),
    "sales_or_payroll": ("sales", sc.hit_number),
    "tiv_building": ("tiv", sc.hit_number),
    "construction": ("construction", sc.hit_text),
    "year_built": ("year built", sc.hit_number),
    "loss_run_valued_through": ("loss runs", sc.hit_loss),
}


def bin_of(c: float) -> str:
    return BINS[0] if c < 0.5 else BINS[1] if c < 0.75 else BINS[2] if c < 0.9 else BINS[3]


def no_call(*_a, **_k):
    raise RuntimeError("B-222 reads the cache only; a model call is not allowed")


def cached_items(folder: Path):
    """Returns (docs, parsed) when the cache has this folder's reply, else None. Same key as llm_extract."""
    docs = [d for d in sources.read_folder(folder) if not d.get("unread")]
    packed_ok = [d for d in docs]
    key = llm_extract.cache_key(packed_ok, llm_extract.provider_guard(calling=False)["model"])
    saved = llm_extract.CACHE / "extractions" / f"{key}.json"
    if not saved.exists():
        return None
    return docs, json.loads(saved.read_text())["parsed"]


def collect() -> tuple[dict, list]:
    llm_extract._post = no_call
    rows, hit_subs, no_gold, skipped_lines = [], [], [], []
    for n in range(1, 77):  # D-077: every cached file up to SUB-076; nothing past it (hold-outs)
        sid = f"SUB-{n:03d}"
        got = cached_items(ROOT / "simulation" / "inbox" / sid)
        if not got:
            continue
        docs, parsed = got
        try:
            gold = sc.parse_gold((sc.GOLD / f"{sid}.md").read_text())
        except (OSError, KeyError, ValueError) as exc:
            no_gold.append(f"{sid} ({type(exc).__name__})")
            continue
        hit_subs.append(sid)
        by_name = {d["name"]: d["text"] for d in docs}
        ocr_conf = {d["name"]: d["ocr_confidence"] for d in docs if d.get("ocr_confidence") is not None}
        ocr_words = {d["name"]: d["ocr_words"] for d in docs if d.get("ocr_words")}
        items = list(parsed.get("fields") or [])
        for c in parsed.get("conflicts") or []:
            items += [{**s, "field_id": c.get("field")} for s in c.get("values") or []]
        for it in items:
            fid = it.get("field_id") or it.get("field")
            raw = it.get("value")
            if fid not in JUDGE or raw is None or str(raw).strip().lower() in ("", "null"):
                continue
            gkey, fn = JUDGE[fid]
            if gkey not in gold:  # D-077: an older gold file (SUB-007..016) has no line for this field; not judged
                skipped_lines.append(f"{sid}:{fid}")
                continue
            if fid == "premises_address" and gold["premises"].lower().startswith("both"):
                continue
            acc = llm_extract.accept_field(dict(it, field_id=fid), by_name, ocr_conf, ocr_words)
            rows.append({
                "sub": sid, "field": fid, "source": "scan" if it.get("source") in ocr_conf else "typed",
                "kept": "stored" if acc["value"] else "dropped", "bin": bin_of(acc["confidence"]),
                "correct": bool(fn(gold[gkey], str(raw).strip())),
            })
    return {"files_hit": hit_subs, "cached_without_gold": no_gold, "values_without_gold_line": skipped_lines}, rows


def tabulate(rows: list) -> dict:
    out: dict = {}
    for r in rows:
        for fld in (r["field"], "ALL"):
            cell = out.setdefault(r["source"], {}).setdefault(fld, {}).setdefault(r["kept"], {}).setdefault(r["bin"], {"correct": 0, "incorrect": 0})
            cell["correct" if r["correct"] else "incorrect"] += 1
    return out


def markdown(meta: dict, table: dict, rows: list) -> str:
    L = ["# Confidence versus hit (B-222)", "",
         "- Author: @ai-engineer-assistant (rebuild: orchestrator, main session). 2026-10-14. D-070 item 3, D-077 item 3. Synthetic. Not a production approval.",
         "- A report, not a UI change. No model call (`_post` raised), no code, prompt, scorer, or score file changed. Cache read from a scratch copy.",
         "- Rebuilt 2026-10-14 under D-077 on every cached file up to SUB-076. The first version (15 files, 115 values) is in git at b77ffa9.",
         f"- Files judged: {len(meta['files_hit'])} (cached and with a gold file): {', '.join(s[4:] for s in meta['files_hit'])}.",
         f"- Cached but not judged (no usable gold file): {len(meta.get('cached_without_gold') or [])}" + (f": {', '.join(meta['cached_without_gold'])}." if meta.get('cached_without_gold') else "."),
         f"- Values not judged because the gold file has no line for that field: {len(meta.get('values_without_gold_line') or [])}.",
         f"- Values judged: {len(rows)} (stored {sum(r['kept']=='stored' for r in rows)}, dropped {sum(r['kept']=='dropped' for r in rows)}).",
         "- Confidence: the gate's own number: the model's, or for a scan the lower of the model's and the OCR score of the cited words.",
         "- Stored: the gate kept the value. Dropped: the gate removed it (low confidence, quote not found, or value not in the quote); the raw model value is judged anyway. Each side of a model-reported conflict counts as a value.",
         "- Correct: the value passes the existing scorer comparison (`eval_holdout.hit_named / hit_ops / hit_number / hit_text / hit_loss`, used read-only) against the gold line. Premises where gold says both addresses conflict, and effective_date (no gold line), are not judged. Operations is a word-overlap test, so it is lenient.",
         "- Cells are correct/incorrect counts. Small counts: read direction, not rates.", ""]
    for src in ("typed", "scan"):
        for kept in ("stored", "dropped"):
            L += [f"## {src.title()} sources, {kept}", "", "| Field | " + " | ".join(BINS) + " |", "|---|" + "---|" * len(BINS)]
            for fld in sorted(table.get(src, {}), key=lambda f: (f == "ALL", f)):
                cells = table[src][fld].get(kept, {})
                L.append(f"| {fld} | " + " | ".join(f"{c['correct']}/{c['incorrect']}" if (c := cells.get(b)) else "-" for b in BINS) + " |")
            L.append("")
    return "\n".join(L)


def _self_check() -> None:
    assert [bin_of(x) for x in (0.1, 0.5, 0.74, 0.75, 0.89, 0.9, 1.0)] == [BINS[0], BINS[1], BINS[1], BINS[2], BINS[2], BINS[3], BINS[3]]
    t = tabulate([{"sub": "S", "field": "tiv_building", "source": "scan", "kept": "stored", "bin": BINS[3], "correct": True},
                  {"sub": "S", "field": "tiv_building", "source": "scan", "kept": "stored", "bin": BINS[3], "correct": False}])
    assert t["scan"]["ALL"]["stored"][BINS[3]] == {"correct": 1, "incorrect": 1}
    try:
        no_call()
        raise SystemExit("no_call must raise")
    except RuntimeError:
        pass
    assert JUDGE["tiv_building"][1]("1,000", "$1000") and not JUDGE["tiv_building"][1]("1,000", "2000")


if __name__ == "__main__":
    _self_check()
    cache = os.environ.get("LLM_CACHE_DIR")
    assert cache and Path(cache).resolve() != (ROOT / "underwriting_pipeline" / "cache").resolve(), "point LLM_CACHE_DIR at a copy"
    meta, rows = collect()
    table = tabulate(rows)
    assert sum(c["correct"] + c["incorrect"] for s in table.values() for c in [x for k in s["ALL"].values() for x in k.values()]) == len(rows)
    (OUT / "confidence-vs-hit.json").write_text(json.dumps({**meta, "n_values": len(rows), "bins": BINS, "counts": table}, indent=2) + "\n")
    (OUT / "confidence-vs-hit.md").write_text(markdown(meta, table, rows) + "\n")
    print("files hit:", len(meta["files_hit"]), "values:", len(rows), "self-check ok")
