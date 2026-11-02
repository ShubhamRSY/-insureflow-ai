#!/usr/bin/env python3
"""P-073 (D-126): lint for scorer v12. Does not edit the frozen lint_holdout.py: it imports it, runs its whole scorer test with --scorer
eval_holdout_v12, and adds the cooking cases below as data (the frozen lint has no cooking-slot cases and its generic wrong operations answer,
"Unrelated widget assembly", is a hit on a card whose items are only business_type=other_class; no cooking, once v12 credits an omitted cooking
slot, so this wrapper swaps in a wrong answer that also claims a kitchen).

Usage: .venv/bin/python deliverables/senior-test-engineer/lint_holdout_v12.py PLAN.json [--run-date YYYY-MM-DD]   (HOLDOUT_INBOX / HOLDOUT_GOLD as the frozen lint)
       .venv/bin/python deliverables/senior-test-engineer/lint_holdout_v12.py --self-check
Read-only, no pipeline run, no model call, writes nothing. Exit 1 on any failure.
"""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lint_holdout as L  # noqa: E402  # frozen; imported, never edited
import eval_holdout_v12 as v12  # noqa: E402  # pyright: ignore[reportMissingImports]

L.WRONG["operations"] = ("operations", "Unrelated widget assembly; full commercial kitchen with fryers")

# (gold items, answer, must_hit, why). Gold "no cooking" = cooking none.
G = "no cooking; 48 seats"
CASES = [
    # (a) omission: nothing about cooking and no cooking word -> read as none
    (G, "48 seats", True, "a: cooking left out, no cooking word"),
    ("business_type=office; no cooking", "Office building, 12 suites", True, "a: class answer, cooking left out"),
    # (b) plain-words none
    (G, "48 seats; no cooking", True, "b: no cooking"), (G, "48 seats; no kitchen", True, "b: no kitchen"),
    (G, "48 seats; no food service", True, "b: no food service"), (G, "48 seats; does not cook", True, "b: does not cook"),
    (G, "48 seats; doesn't cook", True, "b: doesn't cook"), (G, "48 seats; no on-site cooking", True, "b: no on-site cooking"),
    (G, "48 seats; without a kitchen", True, "b: without a kitchen"), (G, "48 seats; cooking: none", True, "b: cooking: none"),
    (G, "48 seats; no hot food", True, "b: no hot food"), (G, "48 seats; no stove", True, "negated cooking word is not evidence"),
    (G, "48 seats; no cooking operations (tenant electric ranges only)", True, "rule file row 7: tenant ranges are not cooking"),
    ("no cooking; 48 seats", "Sin cocina, 48 asientos", True, "Spanish: sin cocina"),
    # near-miss negatives: cooking present or hidden -> must be a miss
    (G, "48 seats; we cook", False, "we cook"), (G, "48 seats; stove", False, "stove"), (G, "48 seats; fry chicken wings", False, "fry chicken wings"),
    (G, "48 seats; hot food", False, "hot food"), (G, "48 seats; hot plate", False, "hot plate"), (G, "48 seats; barbecue", False, "barbecue"),
    (G, "48 seats; range and hood", False, "range and hood"), (G, "48 seats; full kitchen", False, "full kitchen"),
    (G, "48 seats; microwave only", False, "microwave only (light)"), (G, "48 seats; pizza oven", False, "pizza oven"),
    (G, "48 seats; reheats meals", False, "reheats meals"), (G, "48 seats; soups cooked daily", False, "cooked daily"),
    (G, "48 seats; grill", False, "grill"), (G, "48 seats; bbq pit", False, "bbq pit"), (G, "48 seats; deep fryer", False, "deep fryer"),
    (G, "48 seats, no cooking; we fry wings", False, "no cooking said, then cooking stated"),
    (G, "no cooking. hot plate. 48 seats", False, "no cooking said, hot plate in another clause"),
    (G, "48 seats; no cooking operations (range and hood)", False, "no tenant qualifier: range and hood is evidence"),
    (G, "48 seats; no food service; grill", False, "plain none beaten by a stated grill"),
    (G, "40 seats", False, "other slot wrong"), (G, "", False, "empty answer"),
    ("business_type=restaurant; no cooking", "Office building", False, "class wrong, cooking left out"),
    # gold with cooking present: omission and "no cooking" are never credited
    ("full kitchen; 48 seats", "48 seats", False, "gold full, cooking left out"), ("full kitchen; 48 seats", "48 seats; no kitchen", False, "gold full, answer none"),
    ("full kitchen; 48 seats", "48 seats; stove", False, "gold full, stove is not a listed word"),
    ("microwave only; 48 seats", "48 seats", False, "gold light, cooking left out"), ("microwave only; 48 seats", "48 seats; no cooking", False, "gold light, answer none"),
    ("full kitchen; 48 seats", "48 seats; full kitchen", True, "gold full, answer full"),
]
# replacements for the "no cooking" item on a real card (each must be a miss), and plain-words none variants (each must hit)
CARD_WRONG = ["we cook", "stove", "fry chicken wings", "hot food", "hot plate", "barbecue", "range and hood", "full kitchen", "cooks on site", "pizza oven",
              "microwave only", "kitchen with fryers", "grill and hood"]
CARD_OK = ["no kitchen", "no food service", "does not cook", "doesn't cook", "no on-site cooking", "without a kitchen", "cooking: none", "no hot food"]


def check_cases(scorer=v12) -> list[str]:
    bad = [f"case {why!r}: gold {g!r} answer {a!r} want {'hit' if want else 'miss'}" for g, a, want, why in CASES if scorer.ops_items_hit(a, g) != want]
    # the same cases end to end through score_report (the operations mark), on a synthetic card
    saved = scorer.route_used
    scorer.route_used = lambda report: report.get("_route") or "hold"
    try:
        card = ("- Status: complete\n- Scope: in scope\n- Named insured: Example LLC\n- Premises: 100 Main St, Austin, TX 78701\n- Effective date: 2027-01-01\n"
                "- Operations: x\n- Operations items: {items}\n- Sales: 742000\n- TIV: 2450000\n- Construction: Masonry\n- Year built: 2005\n"
                "- Loss runs: Carrier A format, valued as of 2026-08-15\n- Loss runs valued as of: 2026-08-15\n- Conflict: none\n"
                "- Expected loss run: Carrier A format recognised\n- Expected carrier route: carrier_a (R14)\n")
        for g, a, want, why in CASES:
            if not a or "business_type" in g or "kitchen" in g:  # "kitchen" reads as class restaurant; the class stage is v11's
                continue
            text = card.format(items=f"business_type=other_class; {g}")
            rep = L.perfect_report(scorer, "SUB-990", text)
            for r in rep["fields"]:
                if r["field_id"] == "operations":
                    r["value"], r["needs_review"] = f"Machine shop; {a}", False
            mark = scorer.score_report("SUB-990", text, rep)["checks"]["operations"]
            if (mark == "hit") != want:
                bad.append(f"end to end {why!r}: marked {mark}, want {'hit' if want else 'miss'}")
    finally:
        scorer.route_used = saved
    return bad


def check_cards(ids: list[str], scorer=v12) -> list[str]:
    """Every in-scope card of the set whose items hold a bare "no cooking" item: swap it for each wrong and each plain-words variant, drop it."""
    import importlib
    bad, n = [], 0
    saved = scorer.route_used
    scorer.route_used = lambda report: report.get("_route") or "hold"
    try:
        for sid in ids:
            text = (L.GOLD / f"{sid}.md").read_text()
            gold = scorer.parse_gold(text)
            items = [i.strip() for i in (gold.get("operations items") or "").split(";") if i.strip()]
            idx = [k for k, i in enumerate(items) if i.lower() == "no cooking"]
            if not idx or scorer.gold_scope(text)["out"]:
                continue
            n += 1
            perfect = L.perfect_report(scorer, sid, text)

            def mark(answer: str) -> str:
                rep = copy.deepcopy(perfect)
                for r in rep["fields"]:
                    if r["field_id"] == "operations":
                        r["value"], r["needs_review"] = answer, False
                return scorer.score_report(sid, text, rep)["checks"]["operations"]
            k = idx[0]
            swap = lambda new: "; ".join(items[:k] + ([new] if new else []) + items[k + 1:])
            for w in CARD_WRONG:
                if mark(swap(w)) == "hit":
                    bad.append(f"{sid}/scorer: 'no cooking' -> {w!r} is not caught")
            for w in CARD_OK:
                if mark(swap(w)) != "hit":
                    bad.append(f"{sid}/scorer: 'no cooking' -> {w!r} is wrongly a miss")
            rest_has_evidence = scorer.cooking_evidence(swap(""))
            if mark(swap("")) == "hit" and rest_has_evidence:
                bad.append(f"{sid}/scorer: cooking left out is credited although the rest of the answer states cooking")
            if mark(swap("")) != ("miss" if rest_has_evidence else "hit"):
                bad.append(f"{sid}/scorer: cooking left out is not read as v12 item 20 says (marked {mark(swap(''))})")
    finally:
        scorer.route_used = saved
    print(f"cooking stage: {n} real card(s) with a bare 'no cooking' item, {len(CARD_WRONG)} wrong + {len(CARD_OK)} plain-words variants + omission each; {len(CASES)} synthetic cases")
    return bad


def self_check() -> int:
    r = [not check_cases()]
    print(("ok   " if r[-1] else "BAD  ") + "v12: every synthetic cooking case reads as written")
    real = v12.cooking_evidence
    v12.cooking_evidence = lambda t: False  # a scorer blind to cooking words
    blind = check_cases()
    v12.cooking_evidence = real
    r.append(len(blind) >= 15)
    print(("ok   " if r[-1] else "BAD  ") + f"a scorer blind to cooking words is caught ({len(blind)} findings)")
    real_hit = v12.ops_items_hit
    v12.ops_items_hit = lambda *a: True
    blind2 = check_cases()
    v12.ops_items_hit = real_hit
    r.append(len(blind2) >= 15)
    print(("ok   " if r[-1] else "BAD  ") + f"a scorer that hits everything is caught ({len(blind2)} findings)")
    import eval_holdout_v11 as v11  # noqa: E402  # pyright: ignore[reportMissingImports]
    v11_bad = check_cases(v11) if hasattr(v11, "cooking_evidence") else [x for x in (g for g, a, want, why in CASES if v11.ops_items_hit(a, g) != want)]
    r.append(bool(v11_bad))
    print(("ok   " if r[-1] else "BAD  ") + f"frozen v11 fails the omission/plain-words hits as expected ({len(v11_bad)} of {len(CASES)} cases differ)")
    return 0 if all(r) else 1


def main(argv: list[str]) -> int:
    if "--self-check" in argv:
        return self_check()
    argv = [*argv, "--scorer", "eval_holdout_v12"] if "--scorer" not in argv else argv
    code = L.main(argv)
    plan = L.json.loads(Path([a for a in argv if not a.startswith("--") and a != argv[argv.index("--run-date") + 1 if "--run-date" in argv else 0]][0]).read_text())
    a, b = (int(n) for n in plan["ids"].split("-"))
    fails = check_cases() + check_cards([f"SUB-{n:03d}" for n in range(a, b + 1)])
    for f in fails:
        print("FAIL ", f)
    print(f"{'FAIL' if fails or code else 'PASS'} (v12 cooking stage): {len(fails)} failure(s)")
    return 1 if fails or code else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
