#!/usr/bin/env python3
"""Generate the per-LOB underwriting knowledge base from the live catalogs.

Reads the product catalogs in ``src/insureflow/insurance/*.py`` and the
category-level underwriting content in ``rag_knowledge_base.py`` and writes
full-depth underwriting guide entries (one per product) plus a per-LOB index
under ``docs/rag/``. Designed to be re-run whenever the catalogs change:

    .venv/bin/python scripts/generate_rag_corpus.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from rag_knowledge_base import (  # noqa: E402
    DEFAULT_STATE_NOTE,
    LOB_META,
    doc_purpose,
    get_category_rules,
)

GUIDE_VERSION = "3.0"
EFFECTIVE_DATE = "2026-01-01"

LOB_SPECS = [
    ("commercial", "Commercial Insurance (P&C)", "COMMERCIAL_LINES", "COMMERCIAL_CATEGORIES"),
    ("life", "Life Insurance", "LIFE_LINES", "LIFE_CATEGORIES"),
    ("health", "Health Insurance", "HEALTH_LINES", "HEALTH_CATEGORIES"),
    ("general", "General / Non-Life", "GENERAL_LINES", "GENERAL_CATEGORIES"),
]

PERSONAL_SPECS = [
    ("personal_auto", "Personal Auto", "AUTO_CATALOG"),
    ("personal_homeowners", "Personal Homeowners", "HOME_CATALOG"),
]


def load_mod(modname: str):
    import importlib

    return importlib.import_module(modname)


_ACRONYMS = {
    "acord": "ACORD",
    "xml": "XML",
    "mvr": "MVR",
    "clue": "CLUE",
    "dob": "DOB",
    "ssn": "SSN",
    "id": "ID",
    "kyp": "KYP",
    "kyc": "KYC",
    "puc": "PUC",
    "ncb": "NCB",
    "idv": "IDV",
    "rc": "RC",
}


def fmt_title(name: str) -> str:
    return name.replace("/", " / ").replace("_", " ").title()


def humanize(value: str) -> str:
    words = str(value).replace("_", " ").split()
    return " ".join(_ACRONYMS.get(w.lower(), w.capitalize()) for w in words)


def get_product_id(p: Any) -> str:
    return str(p.get("id") or p.get("slug") or p.get("name") or "unknown")


def get_product_name(p: Any) -> str:
    return str(p.get("name") or p.get("short_name") or get_product_id(p))


def get_category(p: Any) -> str:
    cat = p.get("category_id") or p.get("category") or p.get("insurance_line") or ""
    return str(cat)


def get_documents(p: Any) -> List[str]:
    docs = p.get("documents")
    if not docs:
        docs = p.get("additional_documents") or []
    return [str(d).strip() for d in docs if str(d).strip()]


def get_acord_forms(p: Any) -> List[str]:
    forms = p.get("acord_forms") or []
    return [str(f).strip() for f in forms if str(f).strip()]


def get_coverages(p: Any) -> List[dict[str, Any]]:
    out: List[dict[str, Any]] = []
    for c in p.get("coverages") or []:
        if isinstance(c, dict):
            out.append(
                {
                    "name": str(c.get("name") or c.get("id") or "Coverage"),
                    "documents": [str(d).strip() for d in (c.get("documents") or []) if str(d).strip()],
                }
            )
        else:
            out.append({"name": str(c), "documents": []})
    return out


def get_checklist_lob(p: Any) -> str:
    return str(p.get("checklist_lob") or "")


def get_status(p: Any) -> str:
    return str(p.get("status") or "filed")


def _clean(text: str) -> str:
    return " ".join(str(text).split())


def _bullets(items: List[str], indent: str = "") -> List[str]:
    return [f"{indent}- {_clean(i)}" for i in items if str(i).strip()]


def _table(headers: List[str], rows: List[List[str]]) -> List[str]:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        cells = [_clean(c).replace("|", "\\|") for c in row]
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def collect_personal(cat_name: str, catalog_list: List[Any]) -> List[dict]:
    products = []
    for idx, item in enumerate(catalog_list):
        if isinstance(item, tuple) and len(item) >= 2:
            name = item[0]
            doctype_names = []
            for dt in item[1]:
                val = getattr(dt, "value", dt)
                doctype_names.append(humanize(str(val)))
            products.append(
                {
                    "id": f"{cat_name}_{idx}",
                    "name": str(name),
                    "category_id": cat_name,
                    "documents": doctype_names,
                    "acord_forms": [],
                    "coverages": [],
                    "status": "filed",
                    "checklist_lob": cat_name,
                }
            )
        else:
            products.append(
                {
                    "id": f"{cat_name}_{idx}",
                    "name": str(item),
                    "category_id": cat_name,
                    "documents": [],
                    "acord_forms": [],
                    "coverages": [],
                    "status": "filed",
                    "checklist_lob": cat_name,
                }
            )
    return products


def render_product(
    lob_slug: str,
    product: dict[str, Any],
    base_packet: List[str],
) -> str:
    meta = LOB_META.get(lob_slug, {"title": lob_slug, "guide": "Underwriting Guide"})
    lob_title = str(meta["title"])
    pid = get_product_id(product)
    pname = get_product_name(product)
    category = get_category(product)
    description = _clean(product.get("description") or f"{pname} underwriting program.")
    uw_focus = _clean(product.get("uw_focus") or "Standard underwriting review for the line.")
    rules = get_category_rules(lob_slug, category, pid)
    status = get_status(product)
    checklist_lob = get_checklist_lob(product)
    docs = get_documents(product)
    forms = get_acord_forms(product)
    coverages = get_coverages(product)
    packet = list(dict.fromkeys(list(base_packet) + list(product.get("base_packet") or [])))

    out: List[str] = []
    out.append(f"# {pname}")
    out.append("")
    out.append(f"**Line of business:** {lob_title} › {fmt_title(category) or category}")
    out.append(f"**Document ID:** {lob_slug}/{pid}")
    out.append(f"**Guide:** {meta.get('guide', 'Underwriting Guide')} · Version {GUIDE_VERSION}")
    out.append(f"**Effective:** {EFFECTIVE_DATE}")
    if checklist_lob:
        out.append(f"**Package checklist key:** `{checklist_lob}`")
    out.append(f"**Program status:** {status}")
    out.append("")

    section = {"n": 0}

    def add(title: str) -> None:
        section["n"] += 1
        out.append(f"## {section['n']}. {title}")
        out.append("")

    add("Product overview")
    out.append(description)
    out.append("")

    add("Target market, appetite & eligibility")
    out.append(f"- **Market:** {_clean(rules['market'])}")
    out.extend(_bullets(list(rules["eligible"])))
    out.append("")

    add("Ineligible / decline criteria")
    out.extend(_bullets(list(rules["decline"])))
    out.append("")

    if packet:
        add("Core submission packet (all products in this line)")
        out.extend(_bullets(packet))
        out.append("")

    add("Submission requirements")
    if docs:
        rows = [[d, doc_purpose(d)] for d in docs]
        out.extend(_table(["Document", "Why it is required"], rows))
    else:
        out.append("_No additional documents beyond the core packet and application._")
    out.append("")

    add("Applications & forms")
    if forms:
        out.extend(_bullets(forms))
    else:
        out.append("- Filed application/proposal form for this product (plus any state-mandated disclosures).")
    out.append("")

    add("Coverage schedule")
    if coverages:
        rows = [[c["name"], "; ".join(c["documents"]) if c["documents"] else "—"] for c in coverages]
        out.extend(_table(["Coverage / option", "Supporting information"], rows))
    else:
        out.append("_Coverages per the filed product schedule._")
    out.append("")

    add("Policy exclusions")
    out.extend(_bullets(list(rules["exclusions"])))
    out.append("")

    add("Endorsements & optional covers")
    out.extend(_bullets(list(rules["endorsements"])))
    out.append("")

    add("Limits, deductibles & retention guidance")
    out.extend(_bullets(list(rules["limits"])))
    out.append("")

    add("Rating & pricing factors")
    out.extend(_bullets(list(rules["rating"])))
    out.append("")

    add("Underwriting focus")
    out.append(uw_focus)
    out.append("")

    add("Decline / refer authority")
    out.extend(_bullets(list(rules["refer"])))
    out.append("")
    out.append(f"- **Authority:** {_clean(meta.get('authority', ''))}")
    out.append("")

    add("Regulatory & filing notes")
    out.append(f"- **Standards:** {_clean(meta.get('standards', ''))}")
    out.append(f"- {DEFAULT_STATE_NOTE}")
    out.append("")

    add("Underwriting file checklist")
    checklist_items = list(dict.fromkeys(packet + docs + forms))
    if checklist_items:
        out.extend(_bullets(checklist_items))
    else:
        out.append("- Application and identity verification on file.")
    out.append("")

    return "\n".join(out) + "\n"


def render_program(
    lob_slug: str,
    entries: List[dict[str, Any]],
    category_key: str,
) -> str:
    meta = LOB_META.get(lob_slug, {"title": lob_slug, "guide": "Underwriting Guide"})
    lob_title = str(meta["title"])
    rules = get_category_rules(lob_slug, category_key)

    out: List[str] = []
    out.append(f"# {lob_title} Underwriting Program")
    out.append("")
    out.append(f"**Line of business:** {lob_title}")
    out.append(f"**Document ID:** {lob_slug}/program")
    out.append(f"**Guide:** {meta.get('guide', 'Underwriting Guide')} · Version {GUIDE_VERSION}")
    out.append(f"**Effective:** {EFFECTIVE_DATE}")
    out.append("**Program status:** filed")
    out.append("")

    section = {"n": 0}

    def add(title: str) -> None:
        section["n"] += 1
        out.append(f"## {section['n']}. {title}")
        out.append("")

    add("Program overview")
    out.append(f"{lob_title} program for standard eligible risks within filed program limits.")
    out.append("")

    add("Target market, appetite & eligibility")
    out.append(f"- **Market:** {_clean(rules['market'])}")
    out.extend(_bullets(list(rules["eligible"])))
    out.append("")

    add("Ineligible / decline criteria")
    out.extend(_bullets(list(rules["decline"])))
    out.append("")

    add("Submission requirements")
    rows = []
    all_docs: List[str] = []
    for e in entries:
        label = get_product_name(e)
        types = [humanize(t) for t in get_documents(e)]
        all_docs.extend(types)
        rows.append([label, "; ".join(types) if types else "—", doc_purpose(f"{label} {' '.join(types)}")])
    out.extend(_table(["Requirement", "Document types", "Why it is required"], rows))
    out.append("")

    add("Applications & forms")
    out.append("- Filed program application (ACORD or carrier-specific) plus state-mandated disclosures.")
    out.append("")

    add("Coverage schedule")
    out.append("_Coverages per the filed program forms (see Policy exclusions and Endorsements below)._")
    out.append("")

    add("Policy exclusions")
    out.extend(_bullets(list(rules["exclusions"])))
    out.append("")

    add("Endorsements & optional covers")
    out.extend(_bullets(list(rules["endorsements"])))
    out.append("")

    add("Limits, deductibles & retention guidance")
    out.extend(_bullets(list(rules["limits"])))
    out.append("")

    add("Rating & pricing factors")
    out.extend(_bullets(list(rules["rating"])))
    out.append("")

    add("Underwriting focus")
    out.append(f"Confirm eligibility, condition, and rating factors for the risk per the {lob_title} program before binding.")
    out.append("")

    add("Decline / refer authority")
    out.extend(_bullets(list(rules["refer"])))
    out.append("")
    out.append(f"- **Authority:** {_clean(meta.get('authority', ''))}")
    out.append("")

    add("Regulatory & filing notes")
    out.append(f"- **Standards:** {_clean(meta.get('standards', ''))}")
    out.append(f"- {DEFAULT_STATE_NOTE}")
    out.append("")

    add("Underwriting file checklist")
    out.extend(_bullets(list(dict.fromkeys(all_docs))))
    out.append("")

    return "\n".join(out) + "\n"


def render_index(
    lob_slug: str,
    categories: List[dict[str, str]],
    products: List[dict[str, Any]],
    extra_notes: List[str] | None = None,
) -> str:
    meta = LOB_META.get(lob_slug, {"title": lob_slug, "guide": "Underwriting Guide"})
    lob_title = str(meta["title"])
    out: List[str] = []
    out.append(f"# RAG Corpus: {lob_title}")
    out.append("")
    out.append(f"{meta.get('guide', 'Underwriting Guide')} · Version {GUIDE_VERSION} · Effective {EFFECTIVE_DATE}")
    out.append("")
    out.append("## LOB metadata")
    out.append(f"- LOB slug: {lob_slug}")
    out.append(f"- Products: {len(products)}")
    out.append(f"- Categories: {len(categories)}")
    out.append(f"- Standards: {_clean(meta.get('standards', ''))}")
    out.append(f"- Underwriting authority: {_clean(meta.get('authority', ''))}")
    out.append("")
    out.append("## How to use for RAG")
    out.append("- Index each `documents/<product>.md` as one or more chunks (split on the `##` sections).")
    out.append("- Bias retrieval to this LOB (or category) when the submission's line is known.")
    out.append("- The sections map to likely underwriter questions: eligibility, decline, documents, coverages, exclusions, limits, rating, authority.")
    out.append("")
    if categories:
        out.append("## Categories")
        out.append("")
        out.extend(_table(["id", "name", "summary"], [[c.get("id", ""), c.get("name", ""), c.get("summary", "")] for c in categories]))
        out.append("")
    out.append("## Product catalog")
    out.append("")
    rows = []
    for p in products:
        rows.append(
            [
                get_product_id(p),
                get_product_name(p),
                get_category(p),
                get_status(p),
                str(len(get_documents(p))),
                str(len(get_coverages(p))),
                str(len(get_acord_forms(p))),
            ]
        )
    out.extend(_table(["product_id", "name", "category", "status", "docs", "coverages", "forms"], rows))
    out.append("")
    out.append("## Product summaries")
    out.append("")
    for p in products:
        pid = get_product_id(p)
        pname = get_product_name(p)
        desc = _clean(p.get("description") or "")
        out.append(f"### {pid} — {pname}")
        if desc:
            out.append(f"{desc}")
        out.append(f"- Full guide entry: `documents/{pid}.md`")
        out.append("")
    if extra_notes:
        out.append("## Notes")
        out.extend(_bullets(extra_notes))
        out.append("")
    return "\n".join(out)


def main() -> None:
    rag_root = ROOT / "docs" / "rag"
    rag_root.mkdir(parents=True, exist_ok=True)
    written = 0

    for lob_slug, lob_title, lines_name, cats_name in LOB_SPECS:
        mod = load_mod(f"insureflow.insurance.{lob_slug}_lobs")
        lines = getattr(mod, lines_name)
        cats = getattr(mod, cats_name)
        base_packet = list(getattr(mod, "BASE_PACKET", []))
        if not base_packet:
            base_packet = list(getattr(mod, f"{lob_slug.upper()}_BASE_PACKET", []))

        lob_dir = rag_root / lob_slug
        docs_dir = lob_dir / "documents"
        docs_dir.mkdir(parents=True, exist_ok=True)
        for stale in docs_dir.glob("*.md"):
            stale.unlink()

        for p in lines:
            pid = get_product_id(p)
            (docs_dir / f"{pid}.md").write_text(render_product(lob_slug, p, base_packet), encoding="utf-8")
            written += 1

        (lob_dir / "RAG_CORPUS.md").write_text(render_index(lob_slug, cats, lines), encoding="utf-8")

    for pl_slug, pl_title, catalog_name in PERSONAL_SPECS:
        mod_pc = load_mod("insureflow.insurance.package_checklist")
        catalog_list = getattr(mod_pc, catalog_name)
        products = collect_personal(pl_slug, catalog_list)

        lob_dir = rag_root / pl_slug
        docs_dir = lob_dir / "documents"
        docs_dir.mkdir(parents=True, exist_ok=True)
        for stale in docs_dir.glob("*.md"):
            stale.unlink()

        category_key = "auto" if pl_slug == "personal_auto" else "home"
        (docs_dir / "program.md").write_text(render_program(pl_slug, products, category_key), encoding="utf-8")
        written += 1

        (lob_dir / "RAG_CORPUS.md").write_text(
            render_index(pl_slug, [], products, extra_notes=["Personal-lines program limits apply; refer non-standard risks."]),
            encoding="utf-8",
        )

    print(f"Wrote {written} underwriting guide entries under {rag_root}")


if __name__ == "__main__":
    main()
