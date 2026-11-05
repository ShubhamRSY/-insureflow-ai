#!/usr/bin/env python3
"""T-082 fairness checks, items 1, 3 and 6 (D-169). Synthetic text only, no model call, no file read or written except the output.

1. EN<->ES same-match test: each Spanish class word and its English twin in the same operations text give the same
   route, rule ids, suggested market and overridable flag from workbench.match().
3. B-197 mapping check: every Spanish entry in the carrier-match lists maps one-to-one to an English entry of the same list.
6. Route by housing class: matched pairs (same TIV, same sprinkler answer), route split with n per class and the rule that set it.

The rules are not changed here. A difference is reported, not fixed (a fix is a rule change: a P-### for @user).
Run: python deliverables/data-scientist/t082_fairness_checks.py <out.md>
"""
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for sub in ("app", "ai", "models"):
    sys.path.insert(0, str(ROOT / "underwriting_pipeline" / sub))

import workbench  # noqa: E402

# Spanish entry -> English twin, and the list both must be in. Read from workbench.py (PROHIBITED, REFERRAL, ALLOW_A, CLASSES, EQUIP, VACANT).
LISTS = {
    "PROHIBITED": workbench.PROHIBITED,
    "REFERRAL": tuple(w for words, _ in workbench.REFERRAL for w in words),
    "ALLOW_A": tuple(w for words in workbench.ALLOW_A.values() for w in words),
    "CLASS_B": workbench.CLASSES["b"],
    "CONTRACTOR": workbench.CLASSES["contractor"],
    "HABITATIONAL": workbench.CLASSES["habitational"],
    "EQUIP": workbench.EQUIP,
}
PAIRS = [  # (list, spanish, english)
    ("PROHIBITED", "cantina", "bar"), ("PROHIBITED", "taberna", "tavern"), ("PROHIBITED", "antro", "nightclub"), ("PROHIBITED", "discoteca", "nightclub"),
    ("PROHIBITED", "marihuana", "marijuana"), ("PROHIBITED", "dispensario", "dispensary"), ("PROHIBITED", "fuegos artificiales", "fireworks"),
    ("PROHIBITED", "explosivos", "explosives"), ("PROHIBITED", "seguridad armada", "armed security"), ("PROHIBITED", "guardia armado", "armed guard"),
    ("PROHIBITED", "alojamiento estudiantil", "student housing"), ("PROHIBITED", "vivienda subsidiada", "subsidized housing"),
    ("REFERRAL", "fertilizante", "fertilizer"), ("REFERRAL", "pesticida", "pesticide"), ("REFERRAL", "químico", "chemical"), ("REFERRAL", "químicos", "chemicals"),
    ("REFERRAL", "médico", "medical"), ("REFERRAL", "clínica", "clinic"), ("REFERRAL", "terapia", "therapy"), ("REFERRAL", "pediátrico", "pediatric"),
    ("REFERRAL", "almacenamiento en frío", "cold storage"), ("REFERRAL", "refrigerado", "refrigerated"), ("REFERRAL", "licor", "liquor"),
    ("REFERRAL", "sin servicios", "no utilities"), ("REFERRAL", "sin luz", "no power"), ("REFERRAL", "sin ocupar", "not occupied"),
    ("REFERRAL", "vacante", "vacant"), ("REFERRAL", "vacío", "vacant"), ("REFERRAL", "vacio", "vacant"), ("REFERRAL", "vacía", "vacant"), ("REFERRAL", "vacia", "vacant"),
    ("REFERRAL", "desocupado", "unoccupied"), ("REFERRAL", "desocupada", "unoccupied"), ("REFERRAL", "deshabitado", "unoccupied"), ("REFERRAL", "deshabitada", "unoccupied"),
    ("REFERRAL", "abandonado", "abandoned"), ("REFERRAL", "abandonada", "abandoned"),
    ("ALLOW_A", "oficina", "office"), ("ALLOW_A", "oficinas", "offices"), ("ALLOW_A", "comercio minorista", "retail"), ("ALLOW_A", "tienda minorista", "retail store"),
    ("ALLOW_A", "tienda de ropa", "clothing store"), ("ALLOW_A", "ropa", "clothing"), ("ALLOW_A", "mayoreo", "wholesale"), ("ALLOW_A", "mayorista", "wholesale"),
    ("CLASS_B", "restaurante", "restaurant"), ("CLASS_B", "restaurantes", "restaurants"), ("CLASS_B", "servicio de alimentos", "food service"),
    ("CLASS_B", "cocina", "kitchen"), ("CLASS_B", "comedor", "eatery"), ("CLASS_B", "café", "cafe"), ("CLASS_B", "cafetería", "cafeteria"), ("CLASS_B", "banquetes", "catering"),
    ("CONTRACTOR", "contratista", "contractor"), ("CONTRACTOR", "techado", "roofing"), ("CONTRACTOR", "techador", "roofer"), ("CONTRACTOR", "pintor", "painter"),
    ("CONTRACTOR", "pintura", "painting"), ("CONTRACTOR", "carpintero", "carpenter"), ("CONTRACTOR", "carpintería", "carpentry"),
    ("HABITATIONAL", "habitacional", "habitational"), ("HABITATIONAL", "apartamento", "apartment"), ("HABITATIONAL", "apartamentos", "apartments"),
    ("HABITATIONAL", "multifamiliar", "multifamily"),
    ("EQUIP", "freidora", "fryer"), ("EQUIP", "freidoras", "fryers"), ("EQUIP", "horno", "oven"), ("EQUIP", "comal", "griddle"),
]
# Item 1b: Spanish plurals of listed words, against the English plural (the lists hold Spanish singulars only).
PLURALS = [("cantinas", "bars"), ("tabernas", "taverns"), ("antros", "nightclubs"), ("discotecas", "nightclubs"), ("clínicas", "clinics"),
           ("laboratorios", "laboratories"), ("contratistas", "contractors"), ("cocinas", "kitchens"), ("comedores", "eateries"), ("hornos", "ovens"),
           ("freidoras", "fryers"), ("multifamiliares", "multifamily"), ("tiendas minoristas", "retail stores"), ("restaurantes con cantinas", "restaurants with bars"),
           ("pintores", "painters"), ("carpinteros", "carpenters"), ("cafés", "cafes"), ("dispensarios", "dispensaries")]
# Templates: the same file in both languages. The joining word is translated too ("and" / "y"); "with" / "con" tests the neutral list.
TEMPLATES = [("{w}", "{w}"), ("{w} and office", "{w} y oficina"), ("restaurant with {w}", "restaurante con {w}")]
SPRINKLERS = ("yes", "no")


def report(ops: str, tiv: str = "$1,000,000", sprinklers: str = "yes") -> dict:
    return {"complete": True, "status": "complete", "sprinklers": sprinklers,
            "fields": [{"field_id": "operations", "value": ops}, {"field_id": "tiv_building", "value": tiv}]}


def ids(note: str) -> tuple:
    return tuple(sorted(set(re.findall(r"\b(?:R\d+|W\d+[a-z]?|P-\d+|D-\d+|KO \d+)\b", note))))


def outcome(ops: str, sprinklers: str = "yes", tiv: str = "$1,000,000") -> tuple:
    m = workbench.match(report(ops, tiv, sprinklers))
    return (m["route"], ids(m["note"]), m["suggested"], m["overridable"])


def item1() -> tuple[list[str], int, int]:
    rows, diffs, n = [], 0, 0
    for lst, es, en in PAIRS:
        for t_en, t_es in TEMPLATES:
            for spr in SPRINKLERS:
                n += 1
                a, b = outcome(t_en.format(w=en), spr), outcome(t_es.format(w=es), spr)
                if a != b:
                    diffs += 1
                    rows.append(f"| {lst} | `{t_es.format(w=es)}` | `{t_en.format(w=en)}` | {spr} | {b[0]} {'/'.join(b[1])} sugg={b[2] or '-'} ovr={b[3]} | {a[0]} {'/'.join(a[1])} sugg={a[2] or '-'} ovr={a[3]} |")
    return rows, diffs, n


def item3() -> list[str]:
    problems = []
    seen: dict[str, str] = {}
    for lst, es, en in PAIRS:
        if es not in LISTS[lst]:
            problems.append(f"`{es}` is not in {lst}")
        if en not in LISTS[lst]:
            problems.append(f"`{es}` -> `{en}`: the English twin is not in {lst}")
        if es in seen and seen[es] != en:
            problems.append(f"`{es}` maps to two English words")
        seen[es] = en
    return problems


HOUSING = {  # class text -> group; matched on TIV and sprinkler answer
    "student housing": "W1 housing (EN)", "subsidized housing": "W1 housing (EN)",
    "alojamiento estudiantil": "W1 housing (ES)", "vivienda subsidiada": "W1 housing (ES)",
    "affordable housing": "near-synonym, not listed", "low-income apartments": "near-synonym, not listed", "section 8 apartments": "near-synonym, not listed",
    "senior housing": "other housing", "apartments": "habitational", "multifamily": "habitational", "duplex": "habitational", "habitational": "habitational",
}
TIVS = ("$800,000", "$2,500,000", "$4,900,000")


def item6() -> tuple[list[str], int]:
    rows, n = [], 0
    for cls, group in HOUSING.items():
        split: Counter = Counter()
        for tiv in TIVS:
            for spr in SPRINKLERS:
                m = workbench.match(report(f"{cls}, 12 units", tiv, spr))
                split[(m["route"], "/".join(ids(m["note"])) or "-", m["overridable"])] += 1
                n += 1
        cells = "; ".join(f"{r} [{rule}] ovr={o}: {c}" for (r, rule, o), c in sorted(split.items()))
        rows.append(f"| `{cls}` | {group} | {sum(split.values())} | {cells} |")
    return rows, n


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    d1, diffs, n1 = item1()
    p3 = item3()
    r6, n6 = item6()
    md = ["# T-082 fairness checks — items 1, 3, 6 (synthetic, no model call)", "",
          f"Code: `underwriting_pipeline/app/workbench.py` `match()` as on branch `pilot-final`. Script: `deliverables/data-scientist/t082_fairness_checks.py`.", "",
          f"## Item 1 — EN↔ES same match: {n1 - diffs} of {n1} pairs equal, {diffs} differ", "",
          "Compared: route, rule ids in the note, suggested market, overridable. Each pair is the same text in both languages, sprinklers yes/no, TIV $1,000,000.", ""]
    if d1:
        md += ["| List | Spanish text | English text | Sprinklers | Spanish result | English result |", "|---|---|---|---|---|---|", *d1]
    plural = [(es, en, outcome(es), outcome(en)) for es, en in PLURALS]
    pd = [r for r in plural if r[2] != r[3]]
    md += ["", f"### Item 1b — Spanish plurals: {len(plural) - len(pd)} of {len(plural)} equal, {len(pd)} differ", "",
           "| Spanish | English | Spanish result | English result |", "|---|---|---|---|",
           *[f"| `{es}` | `{en}` | {a[0]} {'/'.join(a[1])} ovr={a[3]} | {b[0]} {'/'.join(b[1])} ovr={b[3]} |" for es, en, a, b in pd], "",
           "Reading: the lists hold Spanish singulars only, so a Spanish plural falls to R8 (overridable no_match). For the bar words that is looser than English"
           " (overridable where `bars` is never overridable); for clinics, contractors, kitchens and multifamily it skips the senior referral English gets."
           " `pintores`, `carpinteros`, `cafés`, `dispensarios` are equal only because the English plurals are missing too. Fix options are in P-087 part B."]
    md += ["", "Reading: Spanish bar words beside restaurant evidence are R1 (never overridable) where the English bar words are R2 (senior referral);"
           " `cantina`/`taberna` are in PROHIBITED but not in BAR_WORDS (`workbench.py`). Alone, both languages are R1. `antro`/`discoteca` match `nightclub` (R1 in both)."
           " This is T-082 item 2; the fix is P-087 (a rule change, not built)."]
    md += ["", f"## Item 3 — B-197 Spanish→English mapping: {len(PAIRS)} Spanish entries, {len(p3)} problems", ""]
    md += [f"- {p}" for p in p3] or ["- Every Spanish entry is in its list and its English twin is in the same list; no entry maps to two words."]
    md += ["", f"## Item 6 — route by housing class: {n6} matched files ({len(TIVS)} TIVs × 2 sprinkler answers per class)", "",
           "| Class text | Group | n | Route split [rule] |", "|---|---|---|---|", *r6, "",
           "Reading: the same occupancy gets three outcomes by wording. `student/subsidized housing` (EN or ES) is R1, never overridable;"
           " `affordable housing` and `senior housing` are R8, overridable; `low-income apartments` and `section 8 apartments` are R12 senior referrals."
           " No TIV or sprinkler answer changes any of them. Every difference traces to a named list (W1, R8, R12) and nothing else. This is T-082 item 5; P-088 drafts the route.", "",
           "Not measured: the impact on occupants' protected groups. That needs pilot data (or an approved inference method)."]
    text = "\n".join(md) + "\n"
    if out:
        out.write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
