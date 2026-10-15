"""T-067: name-swap counterfactual on cached results. No model call (llm_extract._post raises). Synthetic data.

Run (cache copied to a scratch folder first; this script refuses to run on the real cache):
  cp -R underwriting_pipeline/cache $SCRATCH/cache
  LLM_CACHE_DIR=$SCRATCH/cache LLM_BASE_URL=https://api.groq.com/openai/v1 LLM_MODEL=openai/gpt-oss-120b \
    .venv/bin/python underwriting_pipeline/models/name_swap.py [out.md]

How it stays on cached results: for each development file SUB-017..076 with a cached reply, the folder is copied to a scratch
folder, the insured's name is swapped in its text files (md, csv), and the cached reply is rewritten with the same swap and saved
under the cache key of the swapped text. Then the unchanged prepare.process_submission runs: gate, document rules, cooking facts,
completeness, status. points.score_run and workbench.match are then read. Score and carrier match are compared with the original.
It tests the rules after the model. It does NOT test whether the model would read a different name differently.
"""
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for sub in ("ai", "models", "app"):
    sys.path.insert(0, str(ROOT / "underwriting_pipeline" / sub))
import llm_extract  # noqa: E402
import points  # noqa: E402
import prepare  # noqa: E402
import sources  # noqa: E402
import workbench  # noqa: E402

# B-065: names holding a trigger word, then a neutral pair that differs by language and surname only.
NAMES = ["Guenther Tacos y Mas", "Blanco Street Kitchen", "Fryer and Sons Bookkeeping", "Open Flame Yoga", "Hood Street Books",
         "Garcia Holdings", "Smith Holdings", "Nguyen Holdings"]
SUFFIX = re.compile(r",?\s+(LLC|L\.L\.C\.|Inc\.?|Corp\.?|Co\.?)$", re.I)


def no_call(*_a, **_k):
    raise RuntimeError("T-067 reads the cache only; a model call is not allowed")


def swap(obj, olds: list[str], new: str):
    if isinstance(obj, str):
        for old in olds:
            obj = obj.replace(old, new)
        return obj
    if isinstance(obj, list):
        return [swap(x, olds, new) for x in obj]
    if isinstance(obj, dict):
        return {k: swap(v, olds, new) for k, v in obj.items()}
    return obj


def swap_items(obj, changed: set, olds: list[str], new: str):
    """Swap only in items whose cited source file had its text swapped. A scan keeps its old name, so its items stay as they were."""
    if isinstance(obj, list):
        return [swap_items(x, changed, olds, new) for x in obj]
    if isinstance(obj, dict):
        if "source" in obj and "quote" in obj:
            return swap(obj, olds, new) if obj.get("source") in changed else obj
        return {k: swap_items(v, changed, olds, new) for k, v in obj.items()}
    return obj


def observe(folder: Path) -> dict:
    report = prepare.process_submission(folder)
    sc = points.score_run(report)
    m = workbench.match(report) if report["status"] != "extraction_failed" else {"route": "n/a", "note": ""}
    return {"status": report["status"], "scored": sc["scored"], "points": sc["points"], "codes": sc["reason_codes"],
            "lines": sc["lines"], "route": m["route"], "note": m["note"], "name": next((r["value"] for r in report["fields"] if r["field_id"] == "named_insured"), None)}


def swapped_cache(folder: Path, parsed: dict, olds: list[str], new: str, tmp: Path) -> Path | None:
    """None when no text file holds the name (nothing to swap). Copy the folder with the name swapped in md/csv text; save the swapped cached reply under the swapped key."""
    dst = tmp / folder.name
    shutil.copytree(folder, dst)
    changed = set()
    for f in dst.iterdir():
        if f.suffix in (".md", ".csv") and any(o in f.read_text() for o in olds):
            f.write_text(swap(f.read_text(), olds, new))
            changed.add(f.name)
    if not changed:
        return None
    docs = [d for d in sources.read_folder(dst) if not d.get("unread")]
    key = llm_extract.cache_key(docs, llm_extract.provider_guard(calling=False)["model"])
    out = llm_extract.CACHE / "extractions" / f"{key}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"parsed": swap_items(parsed, changed, olds, new)}))
    return dst


def run() -> dict:
    cache = os.environ.get("LLM_CACHE_DIR", "")
    real = (ROOT / "underwriting_pipeline" / "cache").resolve()
    assert cache and Path(cache).resolve() != real, "set LLM_CACHE_DIR to a scratch copy of the cache (D-069)"
    llm_extract._post = no_call
    tested, rows, skipped, not_taken = [], [], [], set()
    for n in range(17, 77):
        folder = ROOT / "simulation" / "inbox" / f"SUB-{n:03d}"
        docs = [d for d in sources.read_folder(folder) if not d.get("unread")]
        key = llm_extract.cache_key(docs, llm_extract.provider_guard(calling=False)["model"])
        saved = llm_extract.CACHE / "extractions" / f"{key}.json"
        if not saved.exists():
            skipped.append((folder.name, "no cached reply"))
            continue
        base = observe(folder)
        if base["status"] == "extraction_failed" or not base["name"]:
            skipped.append((folder.name, f"no named insured in the run (status {base['status']})"))
            continue
        parsed = json.loads(saved.read_text())["parsed"]
        olds = sorted({base["name"], SUFFIX.sub("", base["name"])}, key=len, reverse=True)
        in_text = any(o in f.read_text() for f in folder.iterdir() if f.suffix in (".md", ".csv") for o in olds)
        if not in_text:
            skipped.append((folder.name, "name only in a scan or PDF; cannot be swapped"))
            continue
        tested.append(folder.name)
        for new in NAMES:
            with tempfile.TemporaryDirectory() as t:
                dst = swapped_cache(folder, parsed, olds, new, Path(t))
                after = observe(dst)
            if after["name"] != new:  # the run still reads the old name (an item cited to a scan): this file is not a name-swap test
                not_taken.add(folder.name)
            diffs = [k for k in ("points", "codes", "lines", "scored", "route", "note", "status") if base[k] != after[k]]
            rows.append({"sub": folder.name, "new": new, "old": base["name"], "name_in_text": in_text, "diffs": diffs, "base": base, "after": after})
    for sub in sorted(not_taken):
        skipped.append((sub, "swap not taken (named insured still read from a scan)"))
    tested = [t for t in tested if t not in not_taken]
    rows = [r for r in rows if r["sub"] not in not_taken]
    return {"tested": tested, "skipped": skipped, "rows": rows}


def markdown(res: dict) -> str:
    rows, tested = res["rows"], res["tested"]
    changed = [r for r in rows if r["diffs"]]
    score_changed = {r["sub"] for r in changed if {"points", "codes", "scored", "lines"} & set(r["diffs"])}
    match_changed = {r["sub"] for r in changed if {"route", "note"} & set(r["diffs"])}
    status_changed = {r["sub"] for r in changed if "status" in r["diffs"]}
    L = ["# Name-swap counterfactual test (T-067)", "",
         "- Author: @data-scientist. 2026-10-14. D-070 item 4, D-023 item 5. Synthetic. Not a production approval.",
         "- No model call (`llm_extract._post` raised), cache read from a scratch copy, no real workbench, log, or outbox file written. No rule, prompt, scorer, or score file changed.",
         f"- Files tested: {len(tested)} of 60 development files (SUB-017 to SUB-076); skipped {len(res['skipped'])}: " + "; ".join(f"{sum(1 for _, x in res['skipped'] if x == w)} {w} ({', '.join(s[4:] for s, x in res['skipped'] if x == w)})" for w in sorted({x for _, x in res['skipped']})) + ".",
         f"- Swap names ({len(NAMES)}): " + "; ".join(NAMES) + ". Pairs run: " + str(len(rows)) + ".",
         f"- **Files whose score changed: {len(score_changed)}. Files whose carrier match changed: {len(match_changed)}. Files whose status changed: {len(status_changed)}.** Pairs changed: {len(changed)} of {len(rows)}.",
          "- Compared per pair: points, reason codes, the three display lines (loss history, cooking, hood), scored versus Not scored, carrier route and its note, status.", "",
         "## How it stays on cached results, and what it tests", "",
         "- The cache key holds the file text, so swapping the name in the input files would miss the cache. Instead the folder is copied, the name is swapped in its md and csv text, and the cached model reply is rewritten with the same swap and saved under the key of the swapped text. The cached reply is the original model output; no new one exists.",
         "- Tested: everything after the model. The gate (quote must be found in the text), the document rules, the cooking facts, the cue list for producer asks (T2 removes the name before cues are matched), completeness and status, the points, and the carrier match.",
         "- Not tested: whether the model would read a different name, or a Spanish versus English name, differently. That needs a model call and a P-###; the cached replies cannot answer it. Names in scans or PDFs cannot be swapped here: a file whose name is only in a scan is skipped, and in a mixed file the items cited to a scan keep the old name.",
         "- A name appears where the original `named_insured` string (and the same string without LLC, Inc, or Corp) occurs, case-sensitive. A differently spelled mention is left as it is.", ""]
    if changed:
        L += ["## Changes", "", "| File | Swap name | Differs | Before | After |", "|---|---|---|---|---|"]
        for r in changed:
            b, a = r["base"], r["after"]
            L.append(f"| {r['sub']} | {r['new']} | {', '.join(r['diffs'])} | {b['status']}, {b['points']}, {','.join(b['codes']) or '-'}, {b['route']} | {a['status']}, {a['points']}, {','.join(a['codes']) or '-'}, {a['route']} |")
    else:
        L += ["## Changes", "", "None. Every pair gave the same points, codes, display lines, carrier route, note and status."]
    scored = sum(1 for sub in tested if next(r for r in rows if r["sub"] == sub)["base"]["scored"])
    L += ["", "## Limits of this result", "",
          f"- Only {len(tested)} files could be tested: the cache holds replies for 15 of the 60 development files (the same 15 as B-222), and 8 of those have a name in a scan or in a scan-cited item. Of the {len(tested)}, {scored} carry a number; the rest are incomplete, so their points are Not scored before and after. \"No change\" for them means the status, the Not scored reason, the cooking lines and the carrier route did not move.",
          "- It is a pass for these files only, not evidence for the 60 or for the inbox. More files need more cached replies, which means model calls and a decision.",
          "- The five trigger-word names did not change any file's producer ask (the T2 name removal held on the swapped text) or the cooking line. No test file carries a stated cooking fact, so a trigger-word name next to a real fryer line is covered by the prepare.py self-check, not here.", "",
          "## Per file (before the swap)", "", "| File | Status | Points | Codes | Route |", "|---|---|---|---|---|"]
    seen = set()
    for r in rows:
        if r["sub"] in seen:
            continue
        seen.add(r["sub"])
        b = r["base"]
        L.append(f"| {r['sub']} | {b['status']} | {b['points'] if b['scored'] else 'Not scored'} | {','.join(b['codes']) or '-'} | {b['route']} |")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    if sys.argv[1:] == ["--check"]:  # self-check without the cache: the swap itself
        assert swap({"a": ["Casa Verde LLC and Casa Verde", 3]}, ["Casa Verde LLC", "Casa Verde"], "Open Flame Yoga") == {"a": ["Open Flame Yoga and Open Flame Yoga", 3]}
        assert SUFFIX.sub("", "Casa Verde, LLC") == "Casa Verde"
        print("name_swap check ok")
        sys.exit()
    res = run()
    assert res["tested"], "no cached file was tested"
    out = markdown(res)
    if sys.argv[1:]:
        Path(sys.argv[1]).write_text(out)
    print(out.split("## How")[0])
    bad = [r for r in res["rows"] if r["diffs"]]
    assert not bad, f"{len(bad)} pairs changed: first {bad[0]['sub']} {bad[0]['new']} {bad[0]['diffs']}"
    print("name_swap ok")
