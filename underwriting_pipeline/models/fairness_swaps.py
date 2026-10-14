"""D-077: name and cuisine swap tests on every cached file up to SUB-076. No model call (llm_extract._post raises). Synthetic.

Run on a scratch copy of the cache (refuses the real one, D-069):
  cp -R underwriting_pipeline/cache $SCRATCH/cache
  LLM_CACHE_DIR=$SCRATCH/cache LLM_BASE_URL=https://api.groq.com/openai/v1 LLM_MODEL=openai/gpt-oss-120b \
    .venv/bin/python underwriting_pipeline/models/fairness_swaps.py OUT.md

Method (as T-067, name_swap.py): copy the folder, change the text of its md/csv files, rewrite the cached model reply with the
same change for the items cited to those files, save it under the key of the changed text, then run the unchanged rules after
the model (prepare.process_submission, points.score_run, workbench.match, package.needs_review_ids). It tests the rules, not
whether the model would read a different name or cuisine differently.
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
import package  # noqa: E402
import points  # noqa: E402
import prepare  # noqa: E402
import sources  # noqa: E402
import workbench  # noqa: E402
from name_swap import SUFFIX, no_call  # noqa: E402

# Business names: different cultural origins, plus three that hold trigger words (B-065).
BUSINESS = ["Nguyen Family Holdings", "Okafor and Daughters", "Al-Rashid Trading", "Patel Enterprises", "Kowalski Brothers",
            "Yamamoto Services", "O'Brien Group", "Mendoza Holdings", "Guenther Tacos y Mas", "Fryer and Sons Bookkeeping", "Open Flame Yoga"]
# Person names (the files name no owner; the only person names are email senders on "From:" lines): women and men, many origins.
PERSONS = ["Maria Lopez", "Jamal Washington", "Mei Chen", "Olumide Adeyemi", "Priya Patel", "John Smith", "Fatima Al-Sayed",
           "Dmitri Ivanov", "Aiyana Redcloud", "Sung-min Park"]
# D-078: cuisine and food-type words only. Generic restaurant evidence (restaurant, food service, kitchen, eatery, café, catering,
# cocina, comedor; bakery, coffee shop, deli since D-079) is never swapped, and no replacement contains it.
CUISINE = re.compile(r"(?<!\w)(taquer[ií]a|panader[ií]a|pho|diner|pizzer[ií]a|pizza|bistro|tacos?|bbq|barbecue|"
                     r"steakhouse|sushi|noodle house)(?!\w)", re.I)
CUISINE_NEW = ["Taqueria", "Panadería", "Pho House", "Diner", "Pizzeria", "Soul Food", "Curry House", "Halal Cart"]
EQUIPMENT_LINE = re.compile(r"^\s*(cooking equipment|hood and fire suppression|hood and suppression|hood|suppression)\s*:", re.I)
FROM_NAME = re.compile(r"^From:\s*([^<\n]+?)\s*<", re.M)
SCORE_KEYS = ("status", "scored", "points", "codes", "lines", "needs_review")
COOKING_KEYS = ("cooking",)


def observe(folder: Path) -> dict:
    report = prepare.process_submission(folder)
    sc = points.score_run(report)
    m = workbench.match(report) if report["status"] != "extraction_failed" else {"route": "n/a", "note": ""}
    return {"status": report["status"], "scored": sc["scored"], "points": sc["points"], "codes": sc["reason_codes"], "lines": sc["lines"],
            "cooking": sc["lines"][1], "route": m["route"], "note": m["note"], "needs_review": sorted(package.needs_review_ids(report)),
            "name": next((r["value"] for r in report["fields"] if r["field_id"] == "named_insured"), None)}


def edit_items(obj, changed: set, fn):
    """Apply fn to strings inside items cited to a changed file; a scan-cited item keeps its text."""
    if isinstance(obj, list):
        return [edit_items(x, changed, fn) for x in obj]
    if isinstance(obj, dict):
        if "source" in obj and "quote" in obj:
            return {k: (fn(v) if isinstance(v, str) and k != "source" else v) for k, v in obj.items()} if obj.get("source") in changed else obj
        return {k: edit_items(v, changed, fn) for k, v in obj.items()}
    return obj


def variant(folder: Path, parsed: dict, fn, tmp: Path) -> Path | None:
    """Copy the folder with fn applied to md/csv text; save the edited cached reply under the new key. None if nothing changed."""
    dst = tmp / folder.name
    shutil.copytree(folder, dst)
    changed = set()
    for f in dst.iterdir():
        if f.suffix in (".md", ".csv"):
            new = fn(f.read_text())
            if new != f.read_text():
                f.write_text(new)
                changed.add(f.name)
    if not changed:
        return None
    docs = [d for d in sources.read_folder(dst) if not d.get("unread")]
    key = llm_extract.cache_key(docs, llm_extract.provider_guard(calling=False)["model"])
    out = llm_extract.CACHE / "extractions" / f"{key}.json"
    out.write_text(json.dumps({"parsed": edit_items(parsed, changed, fn)}))
    return dst


def replace_all(olds: list[str], new: str):
    def fn(text: str) -> str:
        for old in olds:
            text = text.replace(old, new)
        return text
    return fn


def cuisine_to(new: str):
    def fn(text: str) -> str:  # equipment and hood lines stay identical
        return "".join(line if EQUIPMENT_LINE.match(line) else CUISINE.sub(new, line) for line in text.splitlines(keepends=True))
    return fn


def cached(folder: Path):
    docs = [d for d in sources.read_folder(folder) if not d.get("unread")]
    key = llm_extract.cache_key(docs, llm_extract.provider_guard(calling=False)["model"])
    saved = llm_extract.CACHE / "extractions" / f"{key}.json"
    return json.loads(saved.read_text())["parsed"] if saved.exists() else None


def text_of(folder: Path) -> str:
    return "\n".join(f.read_text() for f in sorted(folder.iterdir()) if f.suffix in (".md", ".csv"))


def run() -> dict:
    cache = os.environ.get("LLM_CACHE_DIR", "")
    assert cache and Path(cache).resolve() != (ROOT / "underwriting_pipeline" / "cache").resolve(), "use a scratch copy of the cache (D-069)"
    llm_extract._post = no_call
    res = {"files": [], "scored": [], "business": [], "person": [], "cuisine": [], "skipped": [], "findings": []}
    for n in range(1, 77):  # nothing past SUB-076
        folder = ROOT / "simulation" / "inbox" / f"SUB-{n:03d}"
        parsed = cached(folder) if folder.is_dir() else None
        if parsed is None:
            continue
        base = observe(folder)
        res["files"].append(folder.name)
        if base["scored"]:
            res["scored"].append(folder.name)
        text = text_of(folder)
        tests = []
        if base["name"]:
            olds = [o for o in sorted({base["name"], SUFFIX.sub("", base["name"])}, key=len, reverse=True) if o in text]
            if olds:
                tests += [("business", new, replace_all(olds, new)) for new in BUSINESS]
            else:
                res["skipped"].append((folder.name, "business", "name only in a scan or PDF"))
        senders = sorted(set(FROM_NAME.findall(text)), key=len, reverse=True)
        if senders:
            tests += [("person", new, replace_all(senders, new)) for new in PERSONS]
        else:
            res["skipped"].append((folder.name, "person", "no person name in md/csv text"))
        if any(CUISINE.search(line) for line in text.splitlines() if not EQUIPMENT_LINE.match(line)):
            tests += [("cuisine", new, cuisine_to(new)) for new in CUISINE_NEW]
        for kind, new, fn in tests:
            with tempfile.TemporaryDirectory() as t:
                dst = variant(folder, parsed, fn, Path(t))
                if dst is None:
                    continue
                after = observe(dst)
            keys = SCORE_KEYS + ("route",) if kind != "cuisine" else ("scored", "points", "codes", "cooking", "status", "route", "needs_review")
            diffs = [k for k in keys if base[k] != after[k]]
            res[kind].append(folder.name)
            if diffs:
                res["findings"].append({"sub": folder.name, "kind": kind, "new": new, "diffs": {k: [base[k], after[k]] for k in diffs}})
    for kind in ("business", "person", "cuisine"):
        res[kind] = sorted(set(res[kind]))
    return res


def markdown(res: dict) -> str:
    f = res["findings"]
    must = [x for x in f if set(x["diffs"]) - {"needs_review"} or x["kind"] != "cuisine"]  # D-078: a route change now breaks the rule
    route_only = [x for x in f if x["kind"] == "cuisine" and set(x["diffs"]) == {"needs_review"}]
    L = ["# Name and cuisine swap tests (D-077, rerun under D-079)", "",
         "- Orchestrator, main session, 2026-10-14. D-077 items 1 and 2. Synthetic. Not a production approval. Does not replace the @responsible-ai check of P-015 (B-270).",
         "- No model call (`llm_extract._post` raised); a scratch copy of the cache; no real workbench, log or outbox file written; no rule, prompt, scorer or score file changed.",
         f"- Cached files tested (SUB-001 to SUB-076 with a cached reply): {len(res['files'])}. Carry a score (a number, not Not scored or Provisional): {len(res['scored'])} ({', '.join(s[4:] for s in res['scored'])}).",
         f"- Business-name swap: {len(res['business'])} files × {len(BUSINESS)} names. Person-name swap: {len(res['person'])} files × {len(PERSONS)} names. Cuisine swap: {len(res['cuisine'])} restaurant files × {len(CUISINE_NEW)} words.",
         "- Compared for name swaps: status, scored, points, codes, the three display lines, needs-review ids, carrier route. For cuisine swaps (D-078): scored, points, codes, cooking line, status and carrier route must not change; a needs-review change is reported apart (see the D-077 note on the model-added-word artifact).",
         f"- **Findings that break the rule (any change from a name swap; score, cooking, status or carrier route from a cuisine swap): {len(must)}.** Cuisine swaps that changed only a needs-review flag: {len(route_only)}.", "",
         "## What this tests and what it does not", "",
         "- Tested: every rule after the model, with the cached model reply edited the same way as the text. Not tested: whether the model itself would read a different name or cuisine differently; that needs model calls.",
         "- The files name no owner. The only person names are email senders on \"From:\" lines (producers), so the person swap uses those.",
         "- Names or cuisine words inside a scan or PDF cannot be edited; such a file is skipped for that test, and in a mixed file items cited to a scan keep their text.", ""]
    L += ["## Findings", ""]
    if not f:
        L.append("None.")
    else:
        L += ["| File | Test | Swapped to | Field | Before | After |", "|---|---|---|---|---|---|"]
        for x in f:
            for k, (b, a) in x["diffs"].items():
                L.append(f"| {x['sub']} | {x['kind']} | {x['new']} | {k} | {json.dumps(b)} | {json.dumps(a)} |")
    L += ["", "## Skipped", ""] + [f"- {s} ({k}): {why}" for s, k, why in res["skipped"]]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    if sys.argv[1:] == ["--check"]:
        assert cuisine_to("Diner")("Taqueria La Paz\nCooking equipment: taco fryer\n") == "Diner La Paz\nCooking equipment: taco fryer\n"
        assert cuisine_to("Diner")("tacos restaurant, cocina") == "Diner restaurant, cocina", "generic evidence is never swapped (D-078)"
        assert CUISINE.search("delivery") is None and CUISINE.search("cafeteria") is None and CUISINE.search("Panadería Sol")
        assert FROM_NAME.findall("From: Luis Ortega <l@x.example>\n") == ["Luis Ortega"]
        assert edit_items({"fields": [{"source": "a.md", "quote": "Taco", "value": "Taco"}, {"source": "s.png", "quote": "Taco", "value": "Taco"}]},
                          {"a.md"}, cuisine_to("Diner")) == {"fields": [{"source": "a.md", "quote": "Diner", "value": "Diner"}, {"source": "s.png", "quote": "Taco", "value": "Taco"}]}
        print("fairness_swaps check ok")
        sys.exit()
    res = run()
    out = markdown(res)
    if sys.argv[1:]:
        Path(sys.argv[1]).write_text(out)
    print(out.split("## What")[0])
