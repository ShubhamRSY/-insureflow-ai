"""Steps 2–3 — cite fields, flag conflicts, write missing-info requests.

Extraction is an LLM call in llm_extract.py. Pattern labels are no longer the reader.
The API key is OPENAI_API_KEY in the environment. It is never written to a file.

Run: python underwriting_pipeline/ai/prepare.py
Inbox: python underwriting_pipeline/ai/prepare.py simulation/inbox simulation/pending-approval deliverables/data-engineer/conflicts
"""

import hashlib
import json
import os
import re
import sys
import tempfile
import unicodedata
from pathlib import Path

import llm_extract
import sources

ROOT = Path(__file__).resolve().parents[2]
# G2 (D-029): the send gate reads the last saved run at this path. It never calls process_submission and never trusts a passed-in report.
EXTRACT_DIR = ROOT / "deliverables" / "data-engineer" / "extractions"
HASH_ALGORITHM = "sha256"
INBOX_DIR = ROOT / "simulation" / "inbox"
# P-010 part 1: these two statuses are refused for every actor, including the user. There is no override.
REFUSED_STATUSES = ("extraction_failed", "all_values_rejected")
REJECT_REASON = "the model answered but every value was rejected by the gate"
# G2 (D-029): the reader accepts only this closed set. A missing, empty, or unknown status is refused, not allowed.
# P-041 (D-088): every field present, but a value needs review or a conflict is open. Not "complete".
REVIEW_PENDING = "complete — review pending"
STATUSES = ("complete", REVIEW_PENDING, "incomplete", "extraction_failed", "all_values_rejected")

FIELDS = (
    "named_insured",
    "premises_address",
    "effective_date",
    "operations",
    "sales_or_payroll",
    "tiv_building",
    "construction",
    "year_built",
    "loss_run_valued_through",
)

LABELS = {
    "named_insured": ("named insured:", "named_insured:"),
    "premises_address": ("premises address:", "premises_address:"),
    "effective_date": ("effective date:", "effective_date:"),
    "operations": ("description of operations:", "operations:"),
    "sales_or_payroll": ("sales or payroll:", "annual sales:", "sales_or_payroll:"),
    "tiv_building": ("building tiv:", "tiv_building:"),
    "construction": ("construction:",),
    "year_built": ("year built:", "year_built:"),
    "loss_run_valued_through": ("valued through:", "loss_run_valued_through:"),
}

NKL = "no known loss"

PLAIN = {
    "named_insured": "legal name of the insured",
    "premises_address": "premises address",
    "effective_date": "effective date",
    "operations": "description of operations",
    "sales_or_payroll": "sales or payroll",
    "tiv_building": "building limit",
    "construction": "construction type",
    "year_built": "year built",
    "loss_run_valued_through": "currently valued carrier loss runs (a no-known-loss letter does not count)",
}


def _conflict(field: str, values: list[dict]) -> dict:
    return {
        "field": field,
        "values": values,
        "resolution": "unresolved",
        "resolved_value": None,
        "resolved_by": None,
    }


def _norm(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


_OPS_CLASS = (
    ("bar", ("nightclub", "night club", " bar", "bar ")),
    ("restaurant", ("restaurant", "taco", "kitchen")),
    ("habitational", ("habitational", "apartment", "flats")),
    ("contractor", ("contractor", "painting")),
    ("wholesale", ("wholesale",)),
    ("retail", ("retail",)),
    ("office", ("office",)),
)


amount_value = llm_extract.amount_value  # P-016 N2: one reader of "220k" and "$1.2M" for the gate and for the merge


def _ops_class(value: str) -> str | None:
    low = f" {value.lower()} "
    for name, words in _OPS_CLASS:
        if any(word in low for word in words):
            return name
    return None


def _ops_contradict(left: str, right: str) -> bool:
    pair = (left.lower(), right.lower())
    no_cook = ("no cooking", "no commercial cooking")
    yes_cook = ("fryer", " cook ")
    for a, b in (pair, (pair[1], pair[0])):
        if any(phrase in a for phrase in no_cook) and any(phrase in f" {b} " for phrase in yes_cook):
            return True
        if re.search(r"sprinklers?\s*:\s*no\b", a) and "sprinkler" in b and not re.search(r"sprinklers?\s*:\s*no\b", b):
            return True
    return False


def same_operations(left: str, right: str) -> bool:
    kind_left, kind_right = _ops_class(left), _ops_class(right)
    if kind_left != kind_right:
        return False
    if not kind_left:  # P-036: no listed class on either side: the same business when they share a main word ("tile")
        # H1: every business word of the shorter wording is in the fuller one ("tile, stone" in "tile, stone and marble")
        biz = sorted(({w for w in words(v) if len(w) >= 3 and w not in _GENERIC and not w.isdigit()} for v in (left, right)), key=len)
        if not biz[0] or not biz[0] <= biz[1]:
            return False
    units_left = re.search(r"(\d+)\s*-?\s*units?", left.lower())
    units_right = re.search(r"(\d+)\s*-?\s*units?", right.lower())
    if units_left and units_right and units_left.group(1) != units_right.group(1):
        return False
    return not _ops_contradict(left, right)


# Words that say how or where, not what business: they never make two operations the same business (P-036 H1)
_GENERIC = {"and", "the", "with", "for", "some", "also", "used", "we", "do", "our", "install", "installs", "installation", "installer",
            "repair", "repairs", "service", "services", "shop", "shops", "store", "stores", "company", "residential", "commercial",
            "light", "heavy", "work", "works", "subcontract", "labor", "small", "general", "business", "only", "both", "plus"}
words, address_list, same_address = llm_extract.words, llm_extract.address_list, llm_extract.same_address  # P-036: one rule for the gate and the merge


def agrees(field: str, left: str, right: str) -> bool:
    if field in {"sales_or_payroll", "tiv_building", "square_feet"}:
        amount_left, amount_right = amount_value(left), amount_value(right)
        return amount_left is not None and amount_left == amount_right
    if field == "operations":
        return words(left) == words(right) or same_operations(left, right)
    if field == "premises_address":
        return same_address(left, right)
    return words(left) == words(right)  # P-036: names and other text fields agree only when identical once normalized


def _same_row(a: dict, b: dict) -> bool:
    return a.get("value") == b.get("value") and a.get("quote") == b.get("quote") and a.get("source") == b.get("source")


def fuller(rows: list[dict]) -> dict:
    """P-036: of agreeing values keep the fuller one; the other quotes stay on it as also_quoted."""
    base = dict(max(rows, key=lambda row: len(words(row.get("value") or ""))))
    also = [{"quote": row["quote"], "source": row.get("source")} for row in rows if row.get("quote") and row.get("quote") != base.get("quote")]
    for item in also:  # each other quote with its file, so the card says which document said what
        if item not in (base.get("also_quoted") or []):
            base["also_quoted"] = (base.get("also_quoted") or []) + [item]
    return base


def _canonical(field: str, value: str) -> str:
    if field not in {"sales_or_payroll", "tiv_building", "square_feet"}:
        return value
    amount = amount_value(value)
    return str(amount) if amount is not None else value


def extract(text: str) -> list[dict]:
    found = {}
    offset = 0
    for line in text.splitlines(keepends=True):
        body = line.split("\n", 1)[0]
        stripped = body.lstrip()
        lead = len(body) - len(stripped)
        low = stripped.lower()
        for field, labs in LABELS.items():
            if found.get(field, {}).get("value"):
                continue
            for lab in labs:
                if not low.startswith(lab):
                    continue
                raw = stripped[len(lab) :]
                rel = len(lab)
                if raw.startswith(" "):
                    raw = raw[1:]
                    rel += 1
                value = raw.rstrip()
                if (field == "loss_run_valued_through" and NKL in value.lower()) or not value:
                    found[field] = {"field_id": field, "value": None, "start": None, "end": None}
                    break
                start = offset + lead + rel
                end = start + len(value)
                if text[start:end] != value:
                    raise RuntimeError(f"citation mismatch on {field}")
                found[field] = {"field_id": field, "value": value, "start": start, "end": end}
                break
        offset += len(line)
    return [
        found.get(field) or {"field_id": field, "value": None, "start": None, "end": None}
        for field in FIELDS
    ]


_ZIP = re.compile(r"\b\d{5}\b")


def flag_invalid_address(row: dict) -> None:
    """P-002. Flag a bad ZIP or a ZIP that does not match the city. Do not rewrite the city.
    P-042 (D-089): the city may be written "City TX" or "City, TX"; every flag says why."""
    value = str(row.get("value") or "")
    found = re.search(r"\b(\d{5})\b", value)
    if not found:
        return
    zip_code = found.group(1)
    cities = _zip_cities().get(zip_code)
    low = value.casefold()
    if cities and any(re.search(rf"(?<![a-z]){re.escape(city)},?\s+(?:tx|texas)\b", low) for city in cities):
        row["address_check"] = "ok"
        return
    why = f"address check: ZIP {zip_code} is not in the Texas ZIP list" if not cities else (
        f"address check: ZIP {zip_code} is listed for {', '.join(sorted(c.title() for c in cities))}, not the city written before TX")
    row["address_check"] = "address invalid"
    row["needs_review"] = True
    row["reason"] = "; ".join(x for x in (row.get("reason"), why) if x)


def _zip_cities() -> dict[str, set[str]]:
    table: dict[str, set[str]] = {}
    path = Path(__file__).with_name("texas_zip_city.tsv")
    for line in path.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        zip_code, city = line.split("\t", 1)
        table.setdefault(zip_code, set()).add(city.casefold())
    return table


def drop_premises_without_zip(merged: dict, needs_human: list[str]) -> None:
    """P-001. No five-digit ZIP means the premises value is dropped and the source page needs a person.

    The text is not rewritten. Loss-run dates are not touched.
    """
    row = merged.get("premises_address")
    if not row or not row.get("value") or _ZIP.search(str(row["value"])):
        return
    source = row.get("source")
    row["value"] = None
    row["needs_review"] = True
    row["reason"] = "address check: no five-digit ZIP; the page needs a person"  # P-042: every flag says why
    if source and source not in needs_human:
        needs_human.append(source)


def completeness(rows: list[dict]) -> dict:
    missing = [r["field_id"] for r in rows if not r["value"]]
    if not missing:
        return {"complete": True, "missing": [], "request": None}
    lines = "\n".join(f"- {field}" for field in missing)
    request = (
        "We are preparing your submission for the carrier panel. "
        "Please send the following. Nothing has been declined.\n" + lines
    )
    return {"complete": False, "missing": missing, "request": request}


def _request(folder: str, missing: list[str], conflicts: list[str]) -> str:
    parts = [
        f"Submission {folder}",
        "Nothing has been declined. Nothing has been bound.",
        "",
    ]
    if missing:
        parts.append("Missing:")
        parts.extend(f"- {PLAIN.get(field, field)}" for field in missing)
        parts.append("")
    if conflicts:
        parts.append("These fields disagree across documents. Both values are stored as data, not only in this email:")
        parts.extend(f"- {item}" for item in conflicts)
    return "\n".join(parts).rstrip() + "\n"


def _apply_reply(conflicts: list[dict], reply: str) -> None:
    """A producer reply can settle a conflict. Both original values stay on the row."""
    if not reply:
        return
    low = reply.lower()
    for item in conflicts:
        if item.get("resolution") == "resolved":
            continue
        sides = [v for v in item["values"] if v.get("value")]
        if "use the application" in low:
            app = next((v for v in sides if v.get("source") == "application.md"), None)
            if app:
                item["resolution"] = "resolved"
                item["resolved_value"] = app["value"]
                item["resolved_by"] = "reply.md says use the application"
                continue
        hits = [v for v in sides if v["value"] in reply]
        if len(hits) == 1:
            item["resolution"] = "resolved"
            item["resolved_value"] = hits[0]["value"]
            item["resolved_by"] = "reply.md states this value and not the other"


def _stated(texts: dict, label: str) -> bool:
    prefix = label.lower() + ":"
    for text in texts.values():
        for line in text.splitlines():
            if line.strip().lower().startswith(prefix):
                return True
    return False


def _digits(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def _sqft(text: str) -> str | None:
    for row in extract_labeled(text, ("square feet:", "sqft:")):
        if row["value"]:
            return row["value"]
    return None


def sprinklers_yes(texts: dict) -> bool:
    """The application's sprinkler line, not the operations sentence."""
    for text in texts.values():
        for line in text.splitlines():
            low = line.strip().lower()
            if low.startswith("sprinklers:") or low.startswith("sprinkler:"):
                return low.split(":", 1)[1].strip().startswith("yes")
        headers = None
        for line in text.splitlines():
            cells = [cell.strip().lower() for cell in line.split("\t")]
            if headers is None and "sprinklers" in cells:
                headers = cells
                continue
            if headers and "sprinklers" in headers and len(cells) == len(headers):
                return cells[headers.index("sprinklers")] == "yes"
    return False


# P-015 S3 (D-040/D-070): cooking facts from the labelled lines of the source text, with a citation, as sprinklers_yes does.
# Equipment and hood/suppression only. Class words, cuisine words and the insured's name are never read. No model call.
COOKING_LABELS = {"equipment": ("cooking equipment:",), "hood_suppression": ("hood and fire suppression:", "hood and suppression:", "hood:", "suppression:")}
HAZARD_TERMS = ("fryer", "fryers", "freidora", "freidoras", "open flame", "llama abierta", "charbroiler", "grill", "parrilla")
NO_WORDS = re.compile(r"^(none|no|not|without|sin|ninguno|ninguna|n/a)\b")
ITEM_SPLIT = re.compile(r"[;,/]|\b(?:and|or|y|o|with|con)\b")  # P-027: a negation covers only the item it directly precedes
NONE_AFTER = re.compile(r":\s*(none|no|not|n/a|ninguno|ninguna)\s*$")  # "fryer: none"


NEG_WORD = re.compile(r"(?<![\w/'’])(no|none|not|without|never|don't|don’t|dont|n/a|sin|nunca|ninguno|ninguna|ningún|nada|w/o|isn't|isn’t|removed|zero)(?![\w/'’])")  # P-031 (D-074), P-033 (D-079)
REASON_COOKING = "the cooking line contains a negation word (P-031): the underwriter records present or none"


def equipment_fact(value: str) -> tuple[str, list[str], list[str]]:
    """P-031 (D-074), replacing P-029/P-030. (state, present terms, negated terms). Two rules, one line at a time:
    (1) a line with no negation word: every hazard term is present ("yes"), or "other" if there is none;
    (2) a line with any negation word: "needs_review", no points until the underwriter records present or none (B-278).
    A newline ends a line: only the first line of the value is read."""
    v = (value.splitlines() or [""])[0].lower().strip()
    if NEG_WORD.search(v):
        return "needs_review", [], []
    hits = sorted((m.start(), m.end(), t) for t in HAZARD_TERMS for m in re.finditer(rf"\b{re.escape(t)}\b", v))
    hits = [h for h in hits if not any(o[0] <= h[0] and h[1] <= o[1] and o != h for o in hits)]
    return ("yes" if hits else "other"), [h[2] for h in hits], []


def _items(value: str) -> list[tuple[str, bool]]:
    """P-027 (D-071): split a cooking line into items; each item is (text, negated). Whole words only."""
    out = []
    for item in ITEM_SPLIT.split(value):
        item = item.strip(" .")
        if item:
            out.append((item, bool(NO_WORDS.match(item) or NONE_AFTER.search(item))))
    return out


def _without_name(blob: str, name: str | None, texts: dict) -> str:
    """P-015 T2: remove the named insured (the extracted value and any 'Named insured:' line) before cue words are looked for."""
    names = {name} if name else set()
    for text in texts.values():
        for row in extract_labeled(text, LABELS["named_insured"]):
            if row.get("value"):
                names.add(row["value"])
    for n in sorted(names, key=len, reverse=True):
        blob = re.sub(re.escape(n), " ", blob, flags=re.I)
    return blob


def cooking_facts(texts: dict) -> dict:
    """{"equipment": fact, "hood_suppression": fact}. fact = {"state", "terms", "source", "start", "end", "quote"}.

    equipment state: "yes" (a hazard term is stated, not negated), "none" (stated none), "other" (a line with no hazard term), "not_stated".
    hood_suppression state: "stated" (a system is named), "none" (stated none), "not_stated". Nothing here adds points (H1).
    """
    out = {}
    for key, labels in COOKING_LABELS.items():
        fact = {"state": "not_stated", "terms": [], "source": None, "start": None, "end": None, "quote": None}
        for name, text in texts.items():
            row = extract_labeled(text, labels)[0]
            if not row["value"]:
                continue
            found, denied = [], []
            if key == "equipment":
                state, found, denied = equipment_fact(row["value"])
            elif row["value"].lower().strip() in ("n/a", "na", "n.a."):
                state = "not_stated"  # B-273 (hood line; the equipment line follows P-030)
            else:
                state = "none" if all(neg for _, neg in _items(row["value"].lower())) else "stated"
            fact = {"state": state, "terms": found, "negated": denied, "source": name, "start": row["start"], "end": row["end"], "quote": row["value"]}
            if state == "needs_review":
                fact["reason"] = REASON_COOKING
            break
        out[key] = fact
    return out


def carrier_run_date(texts: dict) -> tuple[str, str, int, int] | None:
    """Use the carrier loss-run date when a no-known-loss letter is also in the folder."""
    if not any("no known loss" in text.lower() for text in texts.values()):
        return None
    hits = []
    for name, text in texts.items():
        if "no known loss" in text.lower():
            continue
        match = re.search(r"valued through:\s*(20\d\d-\d\d-\d\d)", text, re.I)
        if match:
            hits.append((name, match.group(1), match.start(1), match.end(1)))
    if len(hits) != 1:
        return None
    return hits[0]


# P-040 (D-088): a loss run shows a carrier, a policy period, a valued-as-of date, and a claims list or the carrier's no-claims line.
# A no-known-loss letter, in any language, is never one. Matched on lower-case text with accents removed.
NKL_LETTER = re.compile(r"no[\s-]+known[\s-]+loss|no[\s-]+loss[\s-]+letter|sin perdidas conocidas|no hay reclamaciones|carta de (?:no )?perdidas")
RUN_PARTS = (
    re.compile(r"\b(?:mutual|insurance|insurer|assurance|casualty|indemnity|specialty|surplus|underwriters|carrier|aseguradora|seguros)\b"),
    re.compile(r"20\d\d-\d\d-\d\d\s+(?:to|through|thru|-|a|al|hasta)\s+20\d\d-\d\d-\d\d|(?<![\d-])20\d\d[-/](?:20)?\d\d\b(?![-/]\d)"
               r"|policy (?:period|term|year)|periodo de (?:la )?poliza|vigencia"),
    re.compile(r"valued\s+(?:through|thru|as\s+of)|valuad[oa]\s+al|valorad[oa]\s+al|fecha de valuacion"),
    re.compile(r"\bclaims?\b|\blosses\b|\bpaid\b|\breserves?\b|reclam|siniestro"),
)
# @model-risk H1 (check of P-040): a no-claims statement that comes from an agent, the owner or a letter, in any wording, is a letter too.
NO_CLAIMS = re.compile(r"\bno (?:known )?(?:claims|losses)\b|\bzero claims\b|\b0 claims\b|claim count:? ?0\b|loss[- ]free|\bsin (?:reclam\w*|siniestros?|perdidas)"
                       r"|no se reportaron reclamaciones|ningun (?:reclamo|siniestro)|aucun sinistre|sans sinistre|sem sinistros?|nenhum sinistro")
LETTERISH = re.compile(r"\bletter\b|\blettre\b|\bagente?\b|\bowner\b|applicant (?:states|says|reports)|per (?:the )?applicant|\bsolicitante\b|to our knowledge|\bsegun\b"
                       r"|\bfirmad[oa]\b|\bsigned\b|\bdeclar\w*|\bstates\b|\bproprietaire\b|\bproprietario\b|\bdono\b")
# P-043 (D-089): a loss run is issued by the carrier. A summary written by the applicant, insured, owner, agent or broker, even one
# that names a carrier, a period and claims, is not one: needs review.
AUTHORED = re.compile(
    r"(?:applicant|insured|owner|agent|broker|producer|solicitante|asegurado|agente|dueno|propietario)\s+(?:states|says|reports|declares|certifies|confirms|"
    r"lists|declara|indica|afirma|certifica|reporta)\b|prepared by (?:the )?(?:applicant|insured|owner|agent|broker|producer|agency)"
    r"|preparad[oa] por (?:el |la )?(?:solicitante|asegurado|agente|agencia)|per (?:the )?(?:applicant|insured|owner|agent|broker)"
    r"|segun el (?:solicitante|asegurado|agente|dueno)|to our knowledge|our records|signed by (?:the )?(?:applicant|insured|owner|agent|broker)"
    r"|firmad[oa] por (?:el )?(?:solicitante|asegurado|agente)|self[- ]reported|loss summary from (?:the )?(?:applicant|insured|agent|broker)")
# @model-risk H1 (check of P-043, LOOK-AGAIN): naming a carrier is not issuing. The document's first line must start with a carrier's
# own name (words ending in a carrier word, no business suffix) followed by a loss-run title, or the text says "issued/prepared by
# <carrier name>" with only an article between. When the document states its carrier ("Carrier:"/"Aseguradora:"), that name must
# match. Subject lines, prior/my/our/client wording and people or roles as preparer never pass. Anything else goes to review.
_CARRIER_END = r"(?:mutual|insurance|assurance|casualty|indemnity|specialty|surplus|underwriters)"
_NAME = (r"(?P<name>(?:[a-z0-9&'.]+ ){0,3}?" + _CARRIER_END + r"(?: (?:insurance )?(?:company|co\.?|group|corp\.?))?"
         r"|(?:seguros|aseguradora)(?: [a-z]+){0,3}?)(?: \((?:fictional|ficticia)\))?")
_TITLE = r"\s*[-—–:|]?\s*(?:loss runs?(?: report)?|loss history(?: report)?|claims history|historial de (?:siniestros|perdidas|reclamaciones))\b"
HEADER_ISSUER = re.compile("^" + _NAME + _TITLE)
HEADER_TITLE_FIRST = re.compile("^" + _TITLE.replace(r"\s*[-—–:|]?\s*", "", 1) + r"\s*[-—–:|]\s*" + _NAME + r"\s*$")  # "Loss Run Report - <carrier>"
ISSUED_BY = re.compile(r"\b(?:issued|prepared|produced|generated|emitid[oa]|preparad[oa])\s+(?:by|por)\s+(?:the\s+|la\s+|el\s+)?" + _NAME + r"\s*(?:$|[.;\n])", re.M)
NOT_ISSUER = re.compile(r"\b(?:prior|previous|my|our|your|i|we|client|clients|company's|subject|re|from|llc|inc|ltd|loss|history|claims|with|for|to|by|was|had|agency|agent|broker|owner|insured|applicant)\b")
STATED_CARRIER = re.compile(r"(?:^|\n)\s*[-*]?\s*(?:carrier|insurer|aseguradora)\s*:\s*([^\n,(]+)")
OTHER_AUTHOR = re.compile(
    r"\b(?:provided|submitted|written|prepared|compiled|completed|signed|sent)\s+by\s+(?:the\s+|an?\s+)?(?:applicant|insured|owner|agent|broker|producer|agency)"
    r"|\b(?:applicant|agent|producer|broker|owner|insured)(?:'s|s'|-provided|-prepared)|^\s*from\s*:|\bwe\s+(?:had|have|did|were)\b"
    r"|\bour\s+(?:prior|previous|old|records|carrier|insurer)\b|per\s+(?:the\s+)?(?:insured|applicant|owner)|\breports\s*:", re.M)


def _issued_by_carrier(low: str) -> bool:
    """P-043: the carrier shows as the issuer (header or issued-by line), and it is the carrier the document names."""
    lines = [ln.strip(" #*_\t") for ln in low.splitlines()]
    head = next((ln for ln in lines if ln and "test data" not in ln and "no real applicant" not in ln), "")  # skip the synthetic-data banner
    found = [m.group("name") for m in (HEADER_ISSUER.match(head), HEADER_TITLE_FIRST.match(head), *ISSUED_BY.finditer(low)) if m]
    names = [n for n in found if not NOT_ISSUER.search(n)]
    if not names:
        return False
    stated = STATED_CARRIER.search(low)
    if not stated:
        return True
    core = lambda t: re.sub(r"\((?:fictional|ficticia)\)|\b(?:insurance|company|co|group|corp)\b|[.,]", " ", t).split()
    want = core(stated.group(1))
    return any(core(n)[:2] == want[:2] for n in names)


NKL_DROPPED = "not a loss run: {} is a no-known-loss letter; carrier loss runs are still needed"
RUN_UNCLEAR = "check this is a carrier loss run: {} does not show a carrier, a policy period, a valued-as-of date and a claims list"


def _fold(text: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(ch))


def loss_run_kind(text: str) -> str:
    """P-040: "loss_run", "letter" (a no-known-loss letter), or "unclear". A letter phrase beside every loss-run part is unclear."""
    low = _fold(text)
    full = all(part.search(low) for part in RUN_PARTS)
    if NKL_LETTER.search(low) or (NO_CLAIMS.search(low) and LETTERISH.search(low)):
        return "unclear" if full else "letter"
    if full and (AUTHORED.search(low) or OTHER_AUTHOR.search(low) or not _issued_by_carrier(low)):  # P-043: carrier-issued only
        return "unclear"
    return "loss_run" if full else "unclear"


def gate_loss_run(merged: dict, texts: dict) -> None:
    """P-040: keep the loss-run date only when a real loss run backs it. From a letter it is dropped (the field stays missing);
    from anything else it is kept and marked needs review."""
    row = merged["loss_run_valued_through"]
    if not row.get("value"):
        return
    kinds = {name: loss_run_kind(text) for name, text in texts.items()}
    seen = [x for x in (row["value"], row.get("quote")) if x]
    if kinds.get(row.get("source")) == "loss_run" or any(kinds[n] == "loss_run" and any(x in t for x in seen) for n, t in texts.items()):
        return
    source = row.get("source") or "no file named"
    in_letter = [n for n, t in texts.items() if kinds[n] == "letter" and any(x in t for x in seen)]
    if kinds.get(row.get("source")) == "letter" or in_letter:  # @model-risk H1: a date only letters show is dropped, whichever file is cited
        source = source if kinds.get(row.get("source")) == "letter" else in_letter[0]
        row.update(value=None, needs_review=True, reason=NKL_DROPPED.format(source))
        return
    row["needs_review"] = True
    row["reason"] = "; ".join(x for x in (row.get("reason"), RUN_UNCLEAR.format(source)) if x)


def ready_to_route(report: dict) -> bool:
    """P-041 (D-088): carrier match and sends stay gated as before P-041: every field present, no open conflict, nothing more to ask.
    "complete — review pending" with no open conflict passes; the approve step still makes the underwriter acknowledge each
    value that needs review (D-039)."""
    if report.get("complete"):
        return True
    return report.get("status") == REVIEW_PENDING and not any(c.get("resolution") != "resolved" for c in report.get("conflicts") or [])


def _set_cited(merged: dict, field: str, value: str, source: str, start: int, end: int, texts: dict | None = None, scans: dict | None = None) -> None:
    """Store a document-rule value, cited to its own match. P-016 G2: on a scan source it takes the cited-word score like any other value.
    P-037 (@model-risk H1): a value from a scan never replaces a typed value; it agrees silently or flags the typed value."""
    cur = merged.get(field) or {}
    if scans and source in scans and cur.get("value") and cur.get("source") not in scans:
        if not agrees(field, cur["value"], value):
            _flag_scan_differs(cur, [{"value": value, "source": source}])
        return
    confidence, flag, reason = 0.95, False, None
    quote = texts[source][start:end] if texts and source in texts else None
    if scans and source in scans:
        confidence = min(confidence, llm_extract.cited_ocr_score(quote or value, value, scans[source]))
        if confidence < llm_extract.SCAN_FLOOR:
            return
        if field == "loss_run_valued_through":  # S2
            flag, reason = True, llm_extract.REASON_SCAN
        if confidence < llm_extract.MIN_CONFIDENCE:  # P-025
            flag, reason = True, llm_extract.REASON_LOW_SCAN
    merged[field] = {
        "field_id": field,
        "value": value,
        "source": source,
        "start": start,
        "end": end,
        "confidence": confidence,
        "needs_review": flag,
        "reason": reason,
        "quote": quote,
    }


def _square_feet(texts: dict) -> list[tuple[str, str, str]]:
    found = []
    for name, text in texts.items():
        area = r"(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)[ \t]*([kmb])?[ \t]*(?:square[ \t]+feet|sq\.?[ \t]*ft\.?|sqft|sf)\b"
        for match in re.finditer(area, text, re.I):
            amount = amount_value(match.group(0))
            if amount is not None:
                found.append((str(amount), name, match.group(0)))
        labeled = r"(?im)^(?:square\s+feet|sq\.?\s*ft\.?|sqft|sf):\s*(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*([kmb])?"
        for match in re.finditer(labeled, text):
            amount = amount_value(match.group(0).split(":", 1)[1])
            if amount is not None:
                found.append((str(amount), name, match.group(0)))
        headers = None
        for line in text.splitlines():
            cells = [cell.strip() for cell in line.split("\t")]
            low = [cell.lower() for cell in cells]
            if headers is None and any(cell in {"sqft", "sf"} for cell in low):
                headers = low
                continue
            key = "sqft" if headers and "sqft" in headers else "sf" if headers and "sf" in headers else ""
            if key and len(cells) == len(headers):
                raw = cells[headers.index(key)]
                amount = amount_value(raw)
                if amount is not None:
                    found.append((str(amount), name, raw))
    return found


def labeled_locations(texts: dict) -> list[dict]:
    """Main and second premises are two locations. Two unlabeled addresses are not."""
    for name, text in texts.items():
        main = re.search(r"main premises\s+(.+?)(?:\.|$)", text, re.I)
        second = re.search(r"second premises\s+(.+?)(?:\.|$)", text, re.I)
        if main and second:
            return [
                {"address": main.group(1).strip(), "primary": True, "source": name},
                {"address": second.group(1).strip(), "primary": False, "source": name},
            ]
    for name, text in texts.items():
        headers = None
        rows = []
        for line in text.splitlines():
            cells = [cell.strip() for cell in line.split("\t")]
            low = [cell.lower() for cell in cells]
            if headers is None and "address" in low and "location" in low:
                headers = low
                continue
            if not headers or len(cells) != len(headers):
                continue
            role = cells[headers.index("location")].lower()
            address = cells[headers.index("address")]
            if role in {"main", "second"} and address:
                rows.append({"address": address, "primary": role == "main", "source": name})
        if any(row["primary"] for row in rows) and any(not row["primary"] for row in rows):
            return rows
    return []


def apply_locations(merged: dict, conflicts: list, texts: dict, scans: dict | None = None) -> list[dict]:
    """P-005. A labeled second location is stored, and it is not a premises conflict.

    The primary address stays in premises_address. Unlabeled disagreements stay conflicts.
    Loss-run dates are not touched.
    """
    locations = labeled_locations(texts)
    if len(locations) < 2:
        return []
    primary = next(row for row in locations if row["primary"])
    kept = [item for item in conflicts if item.get("field") not in {"premises_address", "premises"}]
    conflicts[:] = kept
    source_text = texts.get(primary["source"], "")
    at = source_text.find(primary["address"])
    if at >= 0:
        _set_cited(
            merged,
            "premises_address",
            primary["address"],
            primary["source"],
            at,
            at + len(primary["address"]),
            scans=scans,  # P-037: a scan's primary address never replaces a typed one
        )
    return locations


def apply_document_rules(merged: dict, conflicts: list, texts: dict, scans: dict | None = None) -> None:
    """Cited document rules. They do not call the model and do not invent a date."""
    run = carrier_run_date(texts)
    if run:
        name, value, start, end = run
        _set_cited(merged, "loss_run_valued_through", value, name, start, end, texts, scans)
    for name, text in texts.items():
        low = text.lower()
        at = low.find("joisted masonry")
        if at < 0:
            continue
        current = (merged["construction"]["value"] or "").lower()
        if current in {"", "masonry"}:
            _set_cited(merged, "construction", text[at : at + len("joisted masonry")], name, at, at + len("joisted masonry"), texts, scans)
        break
    for name, text in texts.items():
        match = re.search(r"\bcook\s+([A-Za-z]+)", text)
        if not match:
            continue
        food = match.group(1).lower()
        current = (merged["operations"]["value"] or "").lower()
        if food in current and "restaurant" in current:
            break
        _set_cited(merged, "operations", f"{food} restaurant", name, match.start(), match.end(), texts, scans)
        break
    areas = _square_feet(texts)
    distinct = []
    for item in areas:
        if item[0] not in {row[0] for row in distinct}:
            distinct.append(item)
    if len(distinct) < 2:
        return
    blob = json.dumps(conflicts)
    if all(item[0] in blob for item in distinct):
        return
    conflicts.append(
        {
            "field": "square_feet",
            "values": [{"value": item[0], "source": item[1], "quote": item[2]} for item in distinct],
            "resolution": "unresolved",
            "resolved_value": None,
            "resolved_by": None,
        }
    )


def extract_labeled(text: str, labels: tuple[str, ...]) -> list[dict]:
    offset = 0
    for line in text.splitlines(keepends=True):
        body = line.split("\n", 1)[0]
        stripped = body.lstrip()
        low = stripped.lower()
        lead = len(body) - len(stripped)
        for lab in labels:
            if not low.startswith(lab):
                continue
            after = stripped[len(lab) :]
            pad = len(after) - len(after.lstrip())
            value = after.lstrip().rstrip()
            if not value:
                break
            start = offset + lead + len(lab) + pad
            end = start + len(value)
            if text[start:end] != value:
                raise RuntimeError("citation mismatch on extra")
            return [{"field_id": "extra", "value": value, "start": start, "end": end}]
        offset += len(line)
    return [{"field_id": "extra", "value": None, "start": None, "end": None}]


def unread_rows(docs: list[dict], not_sent: list[str]) -> list[dict]:
    """P-016 (c). One row per file or page that was not read: {"file", "page" (None = the whole file), "reason"}."""
    rows = []
    for doc in docs:
        pages = doc.get("unread_pages") or []
        if doc.get("unread"):
            rows.append({"file": doc["name"], "page": None, "reason": doc["unread"]})
        elif doc.get("needs_human") and not pages:
            rows.append({"file": doc["name"], "page": None, "reason": "scan not readable"})
        rows += [{"file": doc["name"], "page": row["page"], "reason": row["reason"]} for row in pages]
    return rows + [{"file": name, "page": None, "reason": f"not sent: text past {llm_extract.MAX_CHARS:,} characters"} for name in not_sent]


def _carry_flag(cur: dict, other: dict) -> None:
    """P-024: two agreeing values merge into one; the saved row is needs_review if either side was, and keeps the reason and quote."""
    if other.get("needs_review") and not cur.get("needs_review"):
        cur["needs_review"] = True
        for k in ("reason", "quote", "source", "start", "end"):
            if other.get(k) is not None:
                cur[k] = other[k]
    else:
        for k in ("reason", "quote"):
            if cur.get(k) is None and other.get(k) is not None:
                cur[k] = other[k]


def _typed_first(field_id: str, rows: list[dict], scans: set) -> dict | None:
    """P-037 (D-084): a typed or structured value outranks a scan (OCR) value. When the typed rows agree, their fuller value is kept;
    a scan value that agrees adds its quote, one that differs makes the kept value needs review, never replaces it.
    None when there is no typed-vs-scan split or the typed rows disagree among themselves (a real conflict)."""
    typed = [row for row in rows if row.get("source") not in scans]
    scanned = [row for row in rows if row.get("source") in scans]
    if not typed or not scanned or not all(agrees(field_id, a["value"], b["value"]) for i, a in enumerate(typed) for b in typed[i + 1 :]):
        return None
    keep = fuller(typed)
    for row in typed:
        if not _same_row(row, keep):
            _carry_flag(keep, row)
    keep["field_id"], keep["value"] = field_id, _canonical(field_id, keep["value"])
    differ = [row for row in scanned if not agrees(field_id, keep["value"], row["value"])]
    for row in scanned:
        if row not in differ and row.get("quote"):
            keep["also_quoted"] = (keep.get("also_quoted") or []) + [{"quote": row["quote"], "source": row.get("source")}]
    if differ:
        _flag_scan_differs(keep, differ)
    return keep


def _flag_scan_differs(row: dict, differ: list[dict]) -> None:
    said = "; ".join(f"\"{item['value']}\" ({item.get('source')})" for item in differ)
    row["needs_review"] = True
    row["reason"] = (row["reason"] + "; " if row.get("reason") else "") + f"scan read differs: {said}; the typed value is kept — check against the page"


def process_submission(folder: Path) -> dict:
    docs = sources.read_folder(folder)
    texts = {doc["name"]: doc["text"] for doc in docs}
    merged = {
        field: {
            "field_id": field,
            "value": None,
            "start": None,
            "end": None,
            "source": None,
            "confidence": 0.0,
            "needs_review": True,
        }
        for field in FIELDS
    }
    conflicts = []
    error = None
    rejected = False
    readable = [doc for doc in docs if doc.get("text") and not doc.get("needs_human")]
    key = llm_extract.key_for(docs) if readable else None  # P-028 (D-075): the extraction cache key; None when no model call is made
    if not readable:
        extracted = {"fields": [], "conflicts": []}
    else:
        try:
            extracted = llm_extract.llm_extract(docs)
        except Exception as exc:
            extracted = {"fields": [], "conflicts": []}
            error = llm_extract._safe(str(exc))
        else:
            if not extracted["conflicts"] and not any(row.get("value") for row in extracted["fields"]):
                # D-024: llm_extract returns only after it has its own usable values, so an all-empty reply is
                # an answer the gate rejected, not a failed call. A raised call stays extraction_failed above.
                rejected = True
    scans = {doc["name"]: doc["ocr_words"] for doc in docs if doc.get("ocr_words")}  # P-037: files whose text came from OCR; one list for every rule
    for row in extracted["fields"]:
        field_id = row.get("field_id")
        if field_id not in merged or not row.get("value"):
            continue
        cur = merged[field_id]
        if cur["value"] is None:
            row["value"] = _canonical(field_id, row["value"])
            merged[field_id] = row
        elif first := _typed_first(field_id, [cur, row], scans):  # P-037: typed beats scan, agreeing or not; a differing scan read flags it
            merged[field_id] = first
        elif agrees(field_id, cur["value"], row["value"]):
            keep = fuller([cur, row])  # P-036: the fuller value, both quotes
            keep["value"] = _canonical(field_id, keep["value"])
            _carry_flag(keep, row if _same_row(keep, cur) else cur)
            merged[field_id] = keep
        elif cur["value"] != row["value"]:
            conflicts.append(
                _conflict(
                    field_id,
                    [
                        {"value": cur["value"], "source": cur["source"]},
                        {"value": row["value"], "source": row.get("source")},
                    ],
                )
            )
            merged[field_id] = {**cur, "value": None, "needs_review": True}
    for item in extracted["conflicts"]:
        field_id = item.get("field")
        kept = [{**side, "field_id": field_id} for side in item.get("values") or [] if side.get("value")]
        first = _typed_first(field_id, kept, scans) if field_id in merged and merged[field_id]["value"] is None else None
        if first:  # P-037: the typed sides agree; a scan side never makes this an open conflict
            merged[field_id] = {**merged[field_id], **first, "confidence": first.get("confidence") or 0.0}
            continue
        sides = [side.get("value") or "" for side in item.get("values") or [] if side.get("value")]
        if len(sides) >= 2 and all(agrees(item.get("field"), a, b) for i, a in enumerate(sides) for b in sides[i + 1 :]):  # H3: every pair
            field_id = item.get("field")
            if field_id in merged and merged[field_id]["value"] is None:
                kept = [side for side in item["values"] if side.get("value")]
                base = fuller(kept)  # P-036: keep the fuller value with both quotes
                merged[field_id].update({k: base.get(k) for k in ("source", "start", "end", "quote", "reason", "confidence", "also_quoted")})
                merged[field_id]["confidence"] = merged[field_id]["confidence"] or 0.0
                merged[field_id]["value"] = _canonical(field_id, base["value"])
                merged[field_id]["needs_review"] = bool(base.get("needs_review"))
                for side in kept:
                    if not _same_row(side, base):
                        _carry_flag(merged[field_id], side)
            continue
        if item["field"] in merged:
            merged[item["field"]]["value"] = None
            merged[item["field"]]["needs_review"] = True
        conflicts.append(item)
    _apply_reply(conflicts, texts.get("reply.md", ""))
    apply_document_rules(merged, conflicts, texts, scans)
    gate_loss_run(merged, texts)  # P-040, after every rule that can set the date
    locations = apply_locations(merged, conflicts, texts, scans)
    listed = extracted.get("schedule") or []  # P-036: several schedule addresses are locations, not a conflict
    if not locations and listed and merged["premises_address"].get("value"):
        primary = merged["premises_address"]
        locations = [{"address": primary["value"], "primary": True, "source": primary.get("source")}] + [
            {"address": row["address"], "primary": False, "source": row["source"]} for row in listed if not same_address(row["address"], primary["value"])
        ]
    blob = _without_name("\n".join(texts.values()), merged["named_insured"].get("value"), texts).lower()  # P-015 T2: the insured's name never starts an ask
    cooking = cooking_facts(texts)
    extra = []
    if any(word in blob for word in ("restaurant", "fryer", "kitchen")):  # P-015 T2: cuisine words ("taco") are not cues
        for label, cues in (
            ("cooking equipment", ("cooking equipment", "fryer")),
            ("hood and fire suppression", ("hood", "suppression")),  # matched as whole words below
            ("sprinklers", ("sprinkler",)),
            ("liquor sales", ("liquor",)),
            ("hours", ("hours", " open ")),
        ):
            if not any(re.search(rf"\b{re.escape(cue.strip())}", blob) for cue in cues):
                extra.append(label)
    needs_human = [doc["name"] for doc in docs if doc.get("needs_human")]
    unread = unread_rows(docs, extracted.get("not_sent") or [])
    needs_human += [row["file"] for row in unread if row["file"] not in needs_human]
    drop_premises_without_zip(merged, needs_human)
    if merged["premises_address"].get("value"):
        flag_invalid_address(merged["premises_address"])
    open_conflicts = [c for c in conflicts if c.get("resolution") != "resolved"]
    rows = [merged[field] for field in FIELDS]
    report = completeness(rows)
    review = [r["field_id"] for r in rows if r.get("value") and r.get("needs_review")]
    pending = report["complete"] and not extra and bool(open_conflicts or review)  # P-041: all present, something still to check
    if open_conflicts or extra or review:
        report["complete"] = False
    report["conflicts"] = conflicts
    report["extra"] = extra
    report["fields"] = rows
    report["folder"] = folder.name
    report["sprinklers"] = "yes" if sprinklers_yes(texts) else "no"
    report["cooking"] = cooking
    report["needs_human"] = needs_human
    report["unread"] = unread
    report["locations"] = locations
    report["error"] = error
    report.update(_run_metadata())
    report["cache_key"] = key  # P-028 (D-075)
    # D-024: an answered reply the gate rejected is not a failed call, and it gets no request and no draft.
    if error:
        report["status"] = "extraction_failed"
    elif rejected:
        report["status"] = "all_values_rejected"
    elif report["complete"]:
        report["status"] = "complete"
    elif pending:
        report["status"] = REVIEW_PENDING
    else:
        report["status"] = "incomplete"
    report["status_reason"] = REJECT_REASON if rejected else None
    # A failed call or an all-rejected answer is not "no data". Nothing is asked of the producer and nothing is sent.
    if error or rejected:
        report["complete"] = False
        report["request"] = None
    elif report["complete"] or (pending and not open_conflicts):  # P-041: a review is the underwriter's, nothing to ask the producer
        report["request"] = None
    else:
        text = _request(folder.name, report["missing"], [c["field"] for c in open_conflicts])
        if extra:
            text += "\nAlso send:\n" + "\n".join(f"- {item}" for item in extra) + "\n"
        report["request"] = text
    return report


def _run_metadata() -> dict:
    """Extraction-run metadata for the saved run (data-model.md). Best effort; null where a setting is unavailable."""
    try:
        model = llm_extract.endpoint_settings().get("model")
    except Exception:
        model = None
    return {
        "model_version": model,
        "prompt_version": getattr(llm_extract, "PROMPT_VERSION", None),
        "ocr_settings": getattr(sources, "OCR_SETTINGS", None),
        "host": llm_extract._host() if hasattr(llm_extract, "_host") else None,
        "temperature": getattr(llm_extract, "TEMPERATURE", None),
    }


def hash_payload(payload: dict, algorithm: str = HASH_ALGORITHM) -> str:
    """The saved_hash bytes (data-model.md): the payload without saved_hash/hash_algorithm, canonical JSON, UTF-8, lowercase hex."""
    if algorithm != HASH_ALGORITHM:
        raise ValueError(f"unsupported hash algorithm {algorithm!r}")
    body = {key: value for key, value in payload.items() if key not in {"saved_hash", "hash_algorithm"}}
    blob = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def read_saved_run(submission: str, extract_dir: Path | None = None) -> dict:
    """G2 (D-029). Read the last saved run, verify its hash, and refuse when anything is off.

    Fail closed: no file, no usable hash, an unknown algorithm, a digest that does not match, or a status
    outside the closed set (`complete`, `incomplete`, `extraction_failed`, `all_values_rejected`) all refuse.
    A status that is missing, empty, or unknown is refused, not allowed, so a caller that branches on it fails closed.
    The gate reads the file itself and never trusts a report a caller passes in.
    """
    directory = Path(extract_dir) if extract_dir is not None else EXTRACT_DIR
    path = directory / f"{submission}.json"
    try:
        payload = json.loads(path.read_text())
    except (OSError, ValueError):
        raise ValueError(f"no saved run for {submission}; refusing to gate on nothing") from None
    if not isinstance(payload, dict):
        raise ValueError(f"the saved run for {submission} is not an object; refusing")
    algorithm = payload.get("hash_algorithm")
    stored = payload.get("saved_hash")
    if algorithm != HASH_ALGORITHM or not isinstance(stored, str) or not stored:
        raise ValueError(f"the saved run for {submission} has no usable hash; refusing")
    if hash_payload(payload, algorithm) != stored:
        raise ValueError(f"the saved run for {submission} changed since it was saved; refusing")
    status = payload.get("status")
    if not isinstance(status, str) or status not in STATUSES:
        raise ValueError(f"the saved run for {submission} has status {status!r}, outside the closed set; refusing")
    return payload


def folder_manifest(folder: Path) -> list[dict]:
    """P-020 (D-060/D-062): file name and sha256 of every file in the submission folder (dotfiles skipped)."""
    return [
        {"name": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
        for p in sorted(folder.iterdir())
        if p.is_file() and not p.name.startswith(".")
    ]


def manifest_problem(submission: str, extract_dir: Path | None = None, inbox: Path | None = None) -> str:
    """P-020 send-gate check. Empty string = ok. Else the refusal reason. Fails closed: no manifest, no folder, any difference."""
    try:
        saved = read_saved_run(submission, extract_dir).get("input_manifest")
    except ValueError as exc:
        return str(exc)
    if not isinstance(saved, list) or not saved:
        return f"the saved run for {submission} has no input manifest; re-run extraction before sending"
    try:
        now = folder_manifest((Path(inbox) if inbox is not None else INBOX_DIR) / submission)
    except OSError:
        return f"the input folder for {submission} cannot be read; refusing"
    if now != saved:
        return f"the input documents for {submission} changed since extraction; re-run extraction before sending"
    return ""


def current_status(submission: str, extract_dir: Path | None = None) -> str:
    """The status of the last saved run, read, hash-checked, and validated by the gate itself (G2)."""
    return read_saved_run(submission, extract_dir)["status"]


def _saved_payload(report: dict) -> dict:
    """The ExtractionRun payload (data-model.md): the exact object the saved_hash is computed over."""
    fields = []
    for row in report.get("fields") or []:
        fields.append(
            {
                "field_id": row["field_id"],
                "value": row["value"],
                "source": row.get("source"),
                "confidence": row.get("confidence"),
                "needs_review": row.get("needs_review"),
                "start": row.get("start"),
                "end": row.get("end"),
                "quote": row.get("quote"),  # P-016 Q1: the exact cited text. The app shows it
                **({"also_quoted": row["also_quoted"]} if row.get("also_quoted") else {}),  # P-036: the agreeing values' other quotes
                "reason": row.get("reason"),  # P-016 R1: why the row is flagged or has no value
            }
        )
    return {
        "submission": report.get("folder"),
        "status": report.get("status"),
        "error": report.get("error"),
        "complete": bool(report.get("complete")),
        "conflicts": report.get("conflicts") or [],
        "needs_human": report.get("needs_human") or [],
        "unread": report.get("unread") or [],  # P-016 (c): file and page not read, with the reason
        "sprinklers": report.get("sprinklers"),
        "cooking": report.get("cooking"),  # P-015 S3: equipment and hood/suppression facts with their citation; an older run has none = not stated
        "model_version": report.get("model_version"),
        "prompt_version": report.get("prompt_version"),
        "ocr_settings": report.get("ocr_settings"),
        "host": report.get("host"),
        "temperature": report.get("temperature"),
        "cache_key": report.get("cache_key"),  # P-028 (D-075): the extraction cache key, under saved_hash
        "fields": fields,
    }


def write_drafts(inbox: Path, draft_dir: Path, conflict_dir: Path) -> list[dict]:
    """Drafts go to pending-approval. Conflicts go to a data file. Never to-producer."""
    if draft_dir.name == "to-producer":
        raise RuntimeError("drafts are not sent to the producer")
    draft_dir.mkdir(parents=True, exist_ok=True)
    conflict_dir.mkdir(parents=True, exist_ok=True)
    extract_dir = conflict_dir.parent / "extractions"
    extract_dir.mkdir(parents=True, exist_ok=True)
    reports = []
    for folder in sorted(p for p in inbox.iterdir() if p.is_dir() and p.name.startswith("SUB-")):
        manifest = folder_manifest(folder)  # B-205 (P-022): taken before extraction reads any file
        report = process_submission(folder)
        reports.append(report)
        refused = report.get("status") in REFUSED_STATUSES
        dest = draft_dir / f"{folder.name}.md"
        side = conflict_dir / f"{folder.name}.json"
        if report["request"]:
            dest.write_text(report["request"])
        elif refused and dest.exists():
            # D1: a failed call or an all-rejected answer removes the old draft. Nothing is sent to the producer.
            dest.unlink()
        conflicts_out = report["conflicts"]
        if conflicts_out:
            side.write_text(
                json.dumps({"submission": folder.name, "conflicts": conflicts_out}, indent=2) + "\n"
            )
        elif refused:
            # D1: the conflict file is kept as it is for the human.
            pass
        elif side.exists():
            prior = json.loads(side.read_text())
            kept = prior.get("conflicts") or []
            if kept and all(c.get("resolution") == "resolved" for c in kept):
                conflicts_out = kept
            else:
                side.unlink()
        payload = _saved_payload(report)
        payload["conflicts"] = conflicts_out
        payload["input_manifest"] = manifest
        payload["hash_algorithm"] = HASH_ALGORITHM
        payload["saved_hash"] = hash_payload(payload, HASH_ALGORITHM)
        (extract_dir / f"{folder.name}.json").write_text(json.dumps(payload, indent=2) + "\n")
    return reports


def approve(
    draft: Path,
    actor: str,
    out_dir: Path,
    reason: str = "",
    report: dict | None = None,
) -> Path:
    """The user may override every block except the two refused statuses (P-010). G2 reads the status itself.

    The passed-in report is not a source of truth: the gate reads the last saved run and checks its hash,
    so an untouched failed or all-rejected run can never be approved, by anyone.
    """
    app = Path(__file__).resolve().parents[1] / "app"
    if str(app) not in sys.path:
        sys.path.insert(0, str(app))
    from package import agency_problem

    current = read_saved_run(draft.stem)  # G2: the file's current status, read and hash-checked here
    status = current.get("status")
    if status in REFUSED_STATUSES:
        raise ValueError(f"this file's status is {status}; it cannot be approved or sent, for any actor")
    name = (actor or "").strip().lstrip("@").lower().replace(" ", "-")
    if name not in {"user", "account-manager"}:
        raise ValueError("only the user or the account manager may approve; no AI role can send")
    if out_dir.name != "to-producer":
        raise ValueError("approved requests go to to-producer")
    body = draft.read_text()
    if "Nothing has been declined" not in body:
        raise ValueError("refusing to send a request that does not say it is not a decline")
    if name == "account-manager":
        if not (reason or "").strip():
            raise ValueError("the account manager must write a reason")
        problem = agency_problem(current)
        if problem:
            raise ValueError(problem)
        header = f"Approved-by: account-manager\nReason: {reason.strip()}\n"
    else:
        header = "Approved-by: user (override)\n"
        if (reason or "").strip():
            header += f"Reason: {reason.strip()}\n"
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / draft.name
    dest.write_text(f"{header}\n{body}")
    return dest


def _raiser(exc: Exception):
    def boom(_docs):
        raise exc

    return boom


def _fake_report(submission: str, status: str, error: str | None) -> dict:
    """A minimal report shaped like process_submission output, for the self-check. No model call."""
    rows = [
        {
            "field_id": field,
            "value": None,
            "start": None,
            "end": None,
            "source": None,
            "confidence": 0.0,
            "needs_review": True,
        }
        for field in FIELDS
    ]
    return {
        "folder": submission,
        "status": status,
        "status_reason": None,
        "error": error,
        "complete": False,
        "missing": list(FIELDS),
        "request": None,
        "conflicts": [],
        "extra": [],
        "fields": rows,
        "sprinklers": "no",
        "needs_human": [],
        "locations": [],
        "model_version": "test",
        "prompt_version": "test",
        "ocr_settings": None,
        "host": None,
        "temperature": 0,
    }


def _save_run(directory: Path, submission: str, status: str, error: str | None = None) -> None:
    payload = _saved_payload(_fake_report(submission, status, error))
    payload["hash_algorithm"] = HASH_ALGORITHM
    payload["saved_hash"] = hash_payload(payload, HASH_ALGORITHM)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{submission}.json").write_text(json.dumps(payload, indent=2) + "\n")


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "--approve":
        approve(Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4]))
        print("approved", sys.argv[2])
    elif len(sys.argv) == 4:
        reports = write_drafts(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
        for report in reports:
            print(
                report["folder"],
                "complete" if report["complete"] else "draft",
                ",".join(report["missing"]),
                "; ".join(item["field"] for item in report["conflicts"]),
            )
    else:
        text = "\n".join(
            [
                "named_insured: Example LLC",
                "premises_address: 100 Main St, San Antonio, TX",
                "effective_date: 2026-11-01",
                "operations: accounting office",
                "sales_or_payroll: 900000",
                "tiv_building: 500000",
                "construction: masonry",
                "year_built: 1998",
                "loss_run_valued_through: no known loss letter",
            ]
        )
        rows = extract(text)
        by = {r["field_id"]: r for r in rows}
        assert by["named_insured"]["value"] == "Example LLC"
        assert text[by["named_insured"]["start"] : by["named_insured"]["end"]] == "Example LLC"
        assert by["loss_run_valued_through"]["value"] is None
        gap = completeness(rows)
        assert gap["complete"] is False
        assert "loss_run_valued_through" in gap["missing"]
        assert "declined" in gap["request"]
        full = extract(text.replace("no known loss letter", "2026-09-30"))
        assert completeness(full)["complete"] is True
        nkl = {"loss-runs.md": "No known loss letter\nValued through: no known loss letter\n"}
        both = dict(nkl)
        both["carrier-loss-runs.md"] = "Carrier loss runs\nValued through: 2026-08-15\nLosses: none in 5 years\n"
        assert carrier_run_date(nkl) is None
        assert carrier_run_date(both)[1] == "2026-08-15"
        application = {"application.md": "Description of operations: habitational, 8 units, no commercial cooking\nSprinklers: yes\n"}
        assert sprinklers_yes(application) is True
        assert sprinklers_yes({"application.md": "Sprinklers: no\n"}) is False
        merged = {
            field: {"field_id": field, "value": None, "source": None, "start": None, "end": None, "confidence": 0, "needs_review": True}
            for field in FIELDS
        }
        merged["construction"]["value"] = "masonry"
        merged["operations"]["value"] = "restaurant"
        conflicts = []
        apply_document_rules(
            merged,
            conflicts,
            {
                "email.md": "They cook tacos. Joisted masonry. My note says 2200 square feet.",
                "schedule.xlsx": "location\ttiv\tsqft\n600 Houston St\t380000\t5100",
                **both,
            },
        )
        assert merged["loss_run_valued_through"]["value"] == "2026-08-15"
        assert merged["construction"]["value"].lower() == "joisted masonry"
        assert merged["operations"]["value"] == "tacos restaurant"
        assert conflicts[0]["field"] == "square_feet"
        assert {row["value"] for row in conflicts[0]["values"]} == {"2200", "5100"}
        quiet = []
        apply_document_rules(
            merged,
            quiet,
            {
                "application.md": "Year built: 1984\nSquare feet: 7200\nSprinklers: yes\n",
                "schedule.csv": "location\tyear_built\tsqft\n1400 Perez St\t1984\t7200",
            },
        )
        assert quiet == []
        flagged: list[str] = []
        bad_premises = {
            "premises_address": {
                "field_id": "premises_address",
                "value": "220 Nogalitos St, Saw Antonio, TX F8204",
                "source": "scan.jpg",
                "needs_review": False,
            }
        }
        drop_premises_without_zip(bad_premises, flagged)
        assert bad_premises["premises_address"]["value"] is None
        assert flagged == ["scan.jpg"]
        kept_pages: list[str] = []
        kept_premises = {
            "premises_address": {
                "field_id": "premises_address",
                "value": "500 Huebner Rd, San Antonio, TX 78240",
                "source": "application.pdf",
                "needs_review": False,
            }
        }
        drop_premises_without_zip(kept_premises, kept_pages)
        assert kept_premises["premises_address"]["value"] == "500 Huebner Rd, San Antonio, TX 78240"
        assert kept_pages == []
        flag_invalid_address(kept_premises["premises_address"])
        assert kept_premises["premises_address"]["address_check"] == "ok"
        mismatch = {
            "field_id": "premises_address",
            "value": "220 Nogalitos St, Saw Antonio, TX 78204",
            "needs_review": False,
        }
        flag_invalid_address(mismatch)
        assert mismatch["address_check"] == "address invalid"
        assert mismatch["value"] == "220 Nogalitos St, Saw Antonio, TX 78204"
        unknown = {"field_id": "premises_address", "value": "1 Main St, San Antonio, TX 00000", "needs_review": False}
        flag_invalid_address(unknown)
        assert unknown["address_check"] == "address invalid"
        assert mismatch["reason"].startswith("address check: ZIP 78204 is listed for") and unknown["reason"] == "address check: ZIP 00000 is not in the Texas ZIP list"
        # P-042 (D-089): "City TX" and "City, TX" both pass; a wrong city or unknown ZIP is flagged with its reason.
        for form in ("7710 Shoal Creek Ct, Suite 210, Austin TX 78757", "7710 Shoal Creek Ct, Suite 210, Austin, TX 78757", "2210 Mesquite Bend Rd, San Antonio TX 78201",
                     "2210 Mesquite Bend Rd, San Antonio, Texas 78201", "1180 Harbor Vista Dr, Corpus Christi TX 78404"):
            row = {"field_id": "premises_address", "value": form, "needs_review": False}
            flag_invalid_address(row)
            assert row["address_check"] == "ok" and not row["needs_review"], form
        for form in ("2210 Mesquite Bend Rd, Dallas TX 78201", "2210 Mesquite Bend Rd, Dallas, TX 78201", "1 Main St Austin TX 00000"):
            row = {"field_id": "premises_address", "value": form, "needs_review": False}
            flag_invalid_address(row)
            assert row["needs_review"] and row["reason"].startswith("address check: ZIP"), form
        assert merged["loss_run_valued_through"]["value"] == "2026-08-15"
        schedule = {
            "email.md": (
                "Main premises 10 De Zavala Rd, San Antonio, TX 78249. "
                "Second premises 80 Prue Rd, San Antonio, TX 78240."
            )
        }
        places = labeled_locations(schedule)
        assert places[0]["primary"] is True
        assert places[0]["address"].startswith("10 De Zavala")
        assert places[1]["primary"] is False
        box = {
            field: {"field_id": field, "value": None, "source": None, "start": None, "end": None, "confidence": 0, "needs_review": True}
            for field in FIELDS
        }
        box["loss_run_valued_through"]["value"] = "2026-08-15"
        open_rows = [
            _conflict(
                "premises_address",
                [
                    {"value": "10 De Zavala Rd, San Antonio, TX 78249", "source": "email.md"},
                    {"value": "80 Prue Rd, San Antonio, TX 78240", "source": "email.md"},
                ],
            ),
            _conflict(
                "tiv_building",
                [
                    {"value": "900000", "source": "email.md"},
                    {"value": "600000", "source": "schedule.xlsx"},
                ],
            ),
        ]
        assert apply_locations(box, open_rows, schedule)[0]["primary"] is True
        assert box["premises_address"]["value"].startswith("10 De Zavala")
        assert [item["field"] for item in open_rows] == ["tiv_building"]
        assert box["loss_run_valued_through"]["value"] == "2026-08-15"
        disagree = {
            "email-1.md": "Mistletoe Retail LLC is at 4 Mistletoe Ave, San Antonio, TX 78212.",
            "email-2.md": "Mistletoe Retail LLC is at 40 Mistletoe Ave, San Antonio, TX 78212.",
        }
        assert labeled_locations(disagree) == []
        assert amount_value("220k") == 220000
        assert amount_value("220,000") == 220000
        assert amount_value("$1.2M") == 1200000
        assert amount_value("$1.2MM") == 1200000 and amount_value("750K") == 750000
        assert amount_value("2,200 sq ft") == 2200
        assert amount_value("2200 sf") == 2200
        assert amount_value("8 units") is None
        assert agrees("sales_or_payroll", "220000", "about 220k")
        # P-024: agreeing scan values "280,000" and "$280k" keep the flag, reason and quote (B-215)
        _side = lambda v, q, f: {"value": v, "source": "scan.png", "start": 0, "end": 5, "quote": q, "needs_review": f,
                                 "reason": "number or date read from a scan" if f else None, "confidence": 0.9}
        for flags, want in (((True, True), True), ((True, False), True), ((False, True), True), ((False, False), False)):
            with tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp) / "SUB-201"
                folder.mkdir()
                (folder / "scan.png").write_text("x")
                real_read, real_extract = sources.read_folder, llm_extract.llm_extract
                sources.read_folder = lambda f: [{"name": "scan.png", "text": "Building 280,000 or $280k", "ocr_words": None}]
                llm_extract.llm_extract = lambda docs: {"fields": [], "not_sent": [], "conflicts": [
                    {"field": "tiv_building", "resolution": "unresolved", "values": [_side("280,000", "280,000", flags[0]), _side("$280k", "$280k", flags[1])]}]}
                try:
                    out = process_submission(folder)
                finally:
                    sources.read_folder, llm_extract.llm_extract = real_read, real_extract
            row = next(r for r in out["fields"] if r["field_id"] == "tiv_building")
            assert row["value"] == "280000" and row["needs_review"] is want, (flags, row)
            assert (row["reason"], row["quote"]) == (("number or date read from a scan", "280,000" if flags[0] else "$280k") if want else (None, "280,000")), row
            assert out["conflicts"] == []
        assert same_operations(
            "habitational, 8 units, no commercial cooking",
            "Small apartments, 8 units, sprinklers throughout.",
        )
        assert not same_operations("accounting office", "restaurant, tacos, fryer")
        # P-036 (D-083): every case of the premises trace (SUB-089/092/098/099/103) and the earlier conflict cases.
        full = "9901 Industrial Park Rd, Laredo, TX 78045"
        for left, right in ((full, "9901 Industrial Park Rd"), ("2950 Rose Hill Rd, Tyler, TX 75703", "2950 Rose Hill Road"),
                            ("1800 Hewitt Dr, Waco, TX 76705", "1800 hewitt drive"), ("4102 Mesquite Bend Rd, Lubbock, TX 79424 (shop and yard)", "4102 Mesquite Bend Rd, Lubbock, TX 79424"),
                            ("100 Main St.", "100  MAIN STREET"), ("12 Oak Ave, Austin, TX 78701", "12 Oak Avenue")):
            assert agrees("premises_address", left, right) and agrees("premises_address", right, left), (left, right)
        for left, right in (("4 Mistletoe Ave, San Antonio, TX 78212", "40 Mistletoe Ave, San Antonio, TX 78212"), ("9 Main St", "90 Main St"),
                            (full, "9901 Industrial Park Rd, Laredo, TX 78046"), ("9901 Industrial Park Rd", "9910 Industrial Park Rd"),
                            ("2215 Bayou Crest Dr, Houston, TX 77063", "2215 Bayou Crest Dr, Houston, TX 77063; 880 Kirby Meadow Ln, Houston, TX 77098"),
                            ("Main St", "Main Street, Austin")):
            assert not agrees("premises_address", left, right), (left, right)
        assert agrees("named_insured", "Caprock Tile & Stone Inc", "Caprock Tile and Stone Inc")
        assert agrees("named_insured", "Pappa Sal's Pizza Co.", "pappa sal's pizza co")
        assert not agrees("named_insured", "Pappa Sal's Pizza Co LLC", "Pappa Sal's Pizza Co"), "a shorter name is not the same name"
        assert agrees("operations", "Tile, stone and marble installation, residential and light commercial, subcontract labor used",
                      "Tile and stone install, we do residential and some light commercial.")
        assert not agrees("operations", "accounting office", "restaurant, tacos, fryer") and not agrees("operations", "dental office", "dry cleaning")
        assert not agrees("operations", "apartments, 8 units", "apartments, 9 units") and not agrees("operations", "restaurant, no cooking", "restaurant with fryer")
        assert not agrees("operations", "tile installation", "auto repair"), "no listed class and no shared word stays a conflict"
        for left, right in (("auto body shop", "coffee shop"), ("roof repair", "auto repair"), ("tile installation", "roofing installation"),
                            ("auto body shop", "auto glass shop")):  # @model-risk H1
            assert not agrees("operations", left, right), (left, right)
        for left, right in (("12 Oak", "12 Oak Ridge Dr, Austin, TX 78701"), ("100 Main St Suite 5", "100 Main St"), ("100 Main St, Unit 2, Austin, TX 78701", "100 Main St"),
                            ("12 Court", "12 Court Plaza Dr"), ("100 Main St Apt B", "100 Main St"), ("100 Main St, Bldg B, Austin", "100 Main St")):
            assert not agrees("premises_address", left, right), (left, right)  # @model-risk H2, M1, M3
        keep = fuller([{"value": "9901 Industrial Park Rd", "quote": "9901 Industrial Park Rd"}, {"value": full, "quote": "Premises address " + full}])
        assert keep["value"] == full and keep["also_quoted"] == [{"quote": "9901 Industrial Park Rd", "source": None}]
        # through process_submission: a street-only side merges into the fuller value; a schedule list goes to locations
        def _through(conflicts, schedule=()):
            with tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp) / "SUB-202"
                folder.mkdir()
                (folder / "application.md").write_text("x")
                real_read, real_extract = sources.read_folder, llm_extract.llm_extract
                sources.read_folder = lambda f: [{"name": "application.md", "text": "Premises address " + full}]
                llm_extract.llm_extract = lambda docs: {"fields": [], "not_sent": [], "conflicts": conflicts, "schedule": list(schedule)}
                try:
                    return process_submission(folder)
                finally:
                    sources.read_folder, llm_extract.llm_extract = real_read, real_extract
        _p = lambda v, q, src="application.md": {"value": v, "quote": q, "source": src, "start": 0, "end": 1, "confidence": 0.9, "needs_review": False, "reason": None}
        out = _through([{"field": "premises_address", "values": [_p("9901 Industrial Park Rd", "9901 Industrial Park Rd", "schedule.xlsx"), _p(full, full)]}])
        row = next(r for r in out["fields"] if r["field_id"] == "premises_address")
        assert row["value"] == full and row["also_quoted"] == [{"quote": "9901 Industrial Park Rd", "source": "schedule.xlsx"}] and out["conflicts"] == [], row
        out = _through([{"field": "premises_address", "values": [_p("4 Mistletoe Ave, San Antonio, TX 78212", "4 Mistletoe"), _p("40 Mistletoe Ave, San Antonio, TX 78212", "40 Mistletoe")]}])
        assert [c["field"] for c in out["conflicts"]] == ["premises_address"], "4 vs 40 stays a conflict"
        out = _through([{"field": "premises_address", "values": [_p("100 Main St", "a"), _p("100 Main St, Austin, TX 78701", "b"), _p("100 Main St, Dallas, TX 75201", "c")]}])
        assert [c["field"] for c in out["conflicts"]] == ["premises_address"], "@model-risk H3: Austin vs Dallas is never merged away"
        # P-037 (D-084): the SUB-088, 097 and 101 shapes. Typed beats scan; a differing scan read flags, never replaces.
        def _scan_case(fields, conflicts, email_text="typed", scan_text="ocr", scan_words=(("ocr", 0.9),)):
            scan_words = [list(w) for w in scan_words]
            with tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp) / "SUB-203"
                folder.mkdir()
                (folder / "email.md").write_text("x")
                real_read, real_extract = sources.read_folder, llm_extract.llm_extract
                sources.read_folder = lambda f: [{"name": "email.md", "text": email_text}, {"name": "scan.jpg", "text": scan_text, "ocr_confidence": 0.75, "ocr_words": scan_words},
                                                 {"name": "loss-runs-scan.jpg", "text": "ocr", "ocr_confidence": 0.8, "ocr_words": [["ocr", 0.9]]}]
                llm_extract.llm_extract = lambda docs: {"fields": fields, "not_sent": [], "conflicts": conflicts}
                try:
                    out = process_submission(folder)
                finally:
                    sources.read_folder, llm_extract.llm_extract = real_read, real_extract
            return {r["field_id"]: r for r in out["fields"]}, out["conflicts"]
        _s = lambda f, v, src: {"field_id": f, "value": v, "source": src, "quote": v, "start": 0, "end": 1, "confidence": 0.9, "needs_review": False, "reason": None}
        rows, open_ = _scan_case([], [  # SUB-088: the email and the scan disagree on name, date and sales
            {"field": "named_insured", "values": [_s("named_insured", "Harvest Crumb Bakery LLC", "email.md"), _s("named_insured", "Harvest Crumb Bakery tic", "scan.jpg")]},
            {"field": "effective_date", "values": [_s("effective_date", "2027-03-15", "email.md"), _s("effective_date", "03/15/202%", "scan.jpg")]},
            {"field": "sales_or_payroll", "values": [_s("sales_or_payroll", "640k", "email.md"), _s("sales_or_payroll", "40K", "scan.jpg")]}])
        assert open_ == [] and rows["named_insured"]["value"] == "Harvest Crumb Bakery LLC" and rows["sales_or_payroll"]["value"] == "640000", rows
        assert all(rows[f]["needs_review"] and "scan read differs" in rows[f]["reason"] for f in ("named_insured", "effective_date", "sales_or_payroll"))
        rows, open_ = _scan_case([_s("tiv_building", "520k", "email.md"), _s("tiv_building", "s20000", "scan.jpg"),   # SUB-097: a typed field row beats a scan field row
                                  _s("construction", "Brick", "scan.jpg")], [])
        assert rows["tiv_building"]["value"] == "520000" and rows["tiv_building"]["needs_review"] and open_ == [], rows["tiv_building"]
        assert rows["construction"]["value"] == "Brick" and not rows["construction"]["needs_review"], "a scan value fills an empty field"
        rows, open_ = _scan_case([_s("tiv_building", "s20000", "scan.jpg"), _s("tiv_building", "520k", "email.md")], [])
        assert rows["tiv_building"]["value"] == "520000" and rows["tiv_building"]["needs_review"], "the typed value replaces a scan value that came first"
        rows, open_ = _scan_case([_s("loss_run_valued_through", "09/30/2026", "loss-runs-scan.jpg")], [   # SUB-101
            {"field": "named_insured", "values": [_s("named_insured", "Pappa Sal's Pizza Co LLC", "email.md"), _s("named_insured", "Pappa Sal's Pizza Co", "email.md")]}])
        assert rows["loss_run_valued_through"]["value"] and [c["field"] for c in open_] == ["named_insured"], "typed vs typed stays a real conflict"
        rows, open_ = _scan_case([], [{"field": "year_built", "values": [_s("year_built", "1984", "email.md"), _s("year_built", "1984", "scan.jpg")]}])
        assert rows["year_built"]["value"] == "1984" and not rows["year_built"]["needs_review"] and rows["year_built"]["also_quoted"] == [{"quote": "1984", "source": "scan.jpg"}]
        rows, _ = _scan_case([_s("named_insured", "HARVEST CRUMB BAKERY LLC.", "scan.jpg"), _s("named_insured", "Harvest Crumb Bakery LLC", "email.md")], [])
        assert rows["named_insured"]["value"] == "Harvest Crumb Bakery LLC" and rows["named_insured"]["source"] == "email.md", "an agreeing scan value never replaces the typed one"
        scan_text = "Operations: we cook burgers. Construction: Joisted masonry"  # @model-risk H1: the document rules obey P-037 too
        rows, _ = _scan_case([_s("operations", "wholesale bakery", "email.md"), _s("construction", "Masonry", "email.md")], [],
                             email_text="Operations: wholesale bakery. Construction: Masonry", scan_text=scan_text, scan_words=[(w, 0.95) for w in scan_text.split()])
        for f, typed in (("operations", "wholesale bakery"), ("construction", "Masonry")):
            assert rows[f]["value"] == typed and rows[f]["source"] == "email.md" and rows[f]["needs_review"] and "scan read differs" in rows[f]["reason"], rows[f]
        rows, _ = _scan_case([], [], scan_text=scan_text, scan_words=[(w, 0.95) for w in scan_text.split()])
        assert rows["construction"]["value"] == "Joisted masonry" and rows["construction"]["source"] == "scan.jpg", "a scan rule still fills an empty field"
        out = _through([], [{"address": full, "source": "schedule.xlsx"}, {"address": "880 Kirby Meadow Ln, Houston, TX 77098", "source": "schedule.xlsx"}])
        assert out["locations"] == [] and out["conflicts"] == [], "no premises value: the schedule alone is not stored as locations"
        same_area = _square_feet({"a.md": "Shop is 2,200 sq ft.", "b.md": "2200 sf"})
        assert {row[0] for row in same_area} == {"2200"}
        # D-024: a raised call stays extraction_failed; an answered reply the gate rejected is all_values_rejected.
        real_extract = llm_extract.llm_extract
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "SUB-200"
            folder.mkdir()
            (folder / "application.md").write_text("Named insured: Example LLC\n")
            try:
                llm_extract.llm_extract = _raiser(RuntimeError("model call failed: HTTP 429 rate limit"))
                failed = process_submission(folder)
                assert failed["status"] == "extraction_failed"
                assert failed["error"] and failed["request"] is None and failed["complete"] is False
                llm_extract.llm_extract = _raiser(RuntimeError("model call returned no fields"))
                empty = process_submission(folder)
                assert empty["status"] == "extraction_failed" and empty["request"] is None
                llm_extract.llm_extract = lambda docs: {
                    "fields": [
                        {
                            "field_id": "named_insured",
                            "value": None,
                            "source": "application.md",
                            "confidence": 0.0,
                            "needs_review": True,
                        }
                    ],
                    "conflicts": [],
                }
                rejected = process_submission(folder)
                assert rejected["status"] == "all_values_rejected"
                assert rejected["error"] is None and rejected["request"] is None
                assert rejected["complete"] is False and rejected["status_reason"] == REJECT_REASON
            finally:
                llm_extract.llm_extract = real_extract
        # D1: on either refused status the old draft goes and the conflict file stays, and the run is saved and hashed.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            inbox = tmp / "inbox"
            (inbox / "SUB-300").mkdir(parents=True)
            (inbox / "SUB-300" / "application.md").write_text("Named insured: Example LLC\n")
            pending = tmp / "pending-approval"
            pending.mkdir()
            conflicts = tmp / "conflicts"
            conflicts.mkdir()
            side = conflicts / "SUB-300.json"
            kept = {
                "submission": "SUB-300",
                "conflicts": [
                    {"field": "tiv_building", "values": [{"value": "1"}], "resolution": "unresolved"}
                ],
            }
            side.write_text(json.dumps(kept, indent=2) + "\n")
            real_ps = process_submission
            try:
                for status, err in (
                    ("extraction_failed", "model call failed: HTTP 429 rate limit"),
                    ("all_values_rejected", None),
                ):
                    (pending / "SUB-300.md").write_text("old draft\n")

                    def fake(folder, status=status, err=err):
                        return _fake_report("SUB-300", status, err)

                    globals()["process_submission"] = fake
                    write_drafts(inbox, pending, conflicts)
                    assert not (pending / "SUB-300.md").exists(), "the old draft must be removed"
                    assert json.loads(side.read_text()) == kept, "the conflict file must be kept"
                    saved = json.loads((tmp / "extractions" / "SUB-300.json").read_text())
                    assert saved["status"] == status and saved["error"] == err
                    assert saved["saved_hash"] == hash_payload(saved)
                    assert read_saved_run("SUB-300", tmp / "extractions")["status"] == status
            finally:
                globals()["process_submission"] = real_ps
        # G2: the gate reads the last saved run and checks its hash. The two refused statuses have no override.
        good = _fake_report("SUB-103", "incomplete", None)
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            ext = tmp / "extractions"
            saved_dir = EXTRACT_DIR
            globals()["EXTRACT_DIR"] = ext
            try:
                pending = tmp / "pending-approval"
                pending.mkdir()
                out = tmp / "to-producer"
                out.mkdir()

                def draft_for(sub: str) -> Path:
                    path = pending / f"{sub}.md"
                    path.write_text("Nothing has been declined.\n")
                    return path

                for sub, status, err in (
                    ("SUB-101", "extraction_failed", "model call failed: HTTP 429 rate limit"),
                    ("SUB-102", "all_values_rejected", None),
                ):
                    _save_run(ext, sub, status, err)
                    path = draft_for(sub)
                    for actor in ("user", "user (override)", "account-manager"):
                        try:
                            approve(path, actor, out, reason="ready", report=good)
                            raise SystemExit(f"{status} must be refused for {actor}")
                        except ValueError:
                            pass
                try:
                    approve(draft_for("SUB-190"), "user", out, report=good)
                    raise SystemExit("approving with no saved run must be refused")
                except ValueError:
                    pass
                _save_run(ext, "SUB-191", "incomplete", None)
                tampered = json.loads((ext / "SUB-191.json").read_text())
                tampered["status"] = "complete"
                (ext / "SUB-191.json").write_text(json.dumps(tampered, indent=2) + "\n")
                try:
                    approve(draft_for("SUB-191"), "user", out)
                    raise SystemExit("a changed saved run must be refused")
                except ValueError:
                    pass
                # Medium-1 fail-closed: a hash-valid run whose status is empty, unknown, or missing is refused by the reader,
                # so a caller that branches on the status fails closed instead of receiving "".
                for sub, label, bad in (
                    ("SUB-194", "empty", ""),
                    ("SUB-195", "unknown", "banana"),
                    ("SUB-196", "missing", None),
                ):
                    _save_run(ext, sub, "incomplete", None)
                    raw = json.loads((ext / f"{sub}.json").read_text())
                    if bad is None:
                        raw.pop("status")
                    else:
                        raw["status"] = bad
                    raw["saved_hash"] = hash_payload(raw)
                    (ext / f"{sub}.json").write_text(json.dumps(raw, indent=2) + "\n")
                    for reader in (read_saved_run, current_status):
                        try:
                            reader(sub)
                            raise SystemExit(f"a {label} status must be refused")
                        except ValueError:
                            pass
                _save_run(ext, "SUB-192", "incomplete", None)
                assert current_status("SUB-192") == "incomplete", "an in-set status still reads"
                sent = approve(draft_for("SUB-192"), "user", out)
                assert "Approved-by: user (override)" in sent.read_text()
                _save_run(ext, "SUB-193", "incomplete", None)
                try:
                    approve(draft_for("SUB-193"), "ai-engineer-assistant", out)
                    raise SystemExit("no AI role may approve")
                except ValueError:
                    pass
                try:
                    approve(draft_for("SUB-193"), "account-manager", out)
                    raise SystemExit("the account manager must write a reason")
                except ValueError:
                    pass
            finally:
                globals()["EXTRACT_DIR"] = saved_dir
        # P-020: manifest check on a real write_drafts() run in a temp folder.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sub = tmp / "inbox" / "SUB-400"
            sub.mkdir(parents=True)
            (sub / "application.md").write_text("Named insured: Example LLC\n")
            real_extract = llm_extract.llm_extract
            llm_extract.llm_extract = _raiser(RuntimeError("model call failed: stub"))  # the manifest is saved on any status
            try:
                write_drafts(tmp / "inbox", tmp / "pending", tmp / "data" / "conflicts")
            finally:
                llm_extract.llm_extract = real_extract
            args = ("SUB-400", tmp / "data" / "extractions", tmp / "inbox")
            assert manifest_problem(*args) == "", manifest_problem(*args)
            (sub / "extra.md").write_text("new doc")
            assert "changed" in manifest_problem(*args), "a new document must be refused"
            (sub / "extra.md").unlink()
            assert manifest_problem(*args) == ""
            (sub / "application.md").write_text("Named insured: Other LLC\n")
            assert "changed" in manifest_problem(*args), "changed bytes must be refused"
            (sub / "application.md").write_text("Named insured: Example LLC\n")
            _save_run(tmp / "data" / "extractions", "SUB-401", "incomplete")
            assert "no input manifest" in manifest_problem("SUB-401", tmp / "data" / "extractions", tmp / "inbox")
            assert manifest_problem("SUB-999", tmp / "data" / "extractions", tmp / "inbox")
        # P-022 B-205: a file added while extraction runs is not in the saved manifest, so the send is refused.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sub = tmp / "inbox" / "SUB-402"
            sub.mkdir(parents=True)
            (sub / "application.md").write_text("Named insured: Example LLC\n")

            def _writes_then_fails(*_a, **_k):
                (sub / "late.md").write_text("added during extraction")
                raise RuntimeError("model call failed: stub")

            real_extract = llm_extract.llm_extract
            llm_extract.llm_extract = _writes_then_fails
            try:
                write_drafts(tmp / "inbox", tmp / "pending", tmp / "data" / "conflicts")
            finally:
                llm_extract.llm_extract = real_extract
            assert (sub / "late.md").exists()
            assert "changed" in manifest_problem("SUB-402", tmp / "data" / "extractions", tmp / "inbox"), "late file must be refused"
        # P-016 Q1, R1, (c), G2, N2. No model call.
    saved = _saved_payload({"fields": [{"field_id": "year_built", "value": "1942", "quote": "Year built: 1942", "reason": "number or date read from a scan", "needs_review": True}], "unread": [{"file": "a.pdf", "page": 2, "reason": "x"}]})
    assert saved["fields"][0]["quote"] == "Year built: 1942" and saved["fields"][0]["reason"] and saved["unread"][0]["page"] == 2, "the saved file carries quote, reason, and unread"
    assert amount_value is llm_extract.amount_value and amount_value("$1.2M") == 1200000, "one reader for amounts (N2)"
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "a.md").write_text("Named insured: Example LLC")
        (Path(tmp) / "b.docx").write_text("x")
        real = llm_extract.llm_extract
        llm_extract.llm_extract = lambda docs: {"fields": [], "conflicts": [], "not_sent": ["a.md"]}
        try:
            report = process_submission(Path(tmp))
        finally:
            llm_extract.llm_extract = real
        assert {(r["file"], r["reason"]) for r in report["unread"]} == {("b.docx", "file type .docx is not read"), ("a.md", "not sent: text past 120,000 characters")}
        assert set(report["needs_human"]) >= {"a.md", "b.docx"}, "every unread file is also in needs_human, as a list of names"
    merged_g2 = {f: {"field_id": f, "value": None, "needs_review": True} for f in FIELDS}
    apply_document_rules(merged_g2, [], {"s.jpg": "Valued through: 2026-01-01", "n.md": "No known loss letter"}, {"s.jpg": [["Valued", 0.9], ["through:", 0.9], ["2026-01-01", 0.4]]})
    assert merged_g2["loss_run_valued_through"]["value"] is None, "G2: a document rule on a scan takes the cited-word score; under 0.50 it is dropped"
    apply_document_rules(merged_g2, [], {"s.jpg": "Valued through: 2026-01-01", "n.md": "No known loss letter"}, {"s.jpg": [["Valued", 0.9], ["through:", 0.9], ["2026-01-01", 0.6]]})
    assert merged_g2["loss_run_valued_through"]["reason"] == llm_extract.REASON_LOW_SCAN, "P-025: 0.6 is stored for review"
    merged_g2["loss_run_valued_through"]["value"] = None
    apply_document_rules(merged_g2, [], {"s.jpg": "Valued through: 2026-01-01", "n.md": "No known loss letter"}, {"s.jpg": [["Valued", 0.9], ["through:", 0.9], ["2026-01-01", 0.9]]})
    assert merged_g2["loss_run_valued_through"]["value"] == "2026-01-01" and merged_g2["loss_run_valued_through"]["needs_review"], "G2/S2: passes at 0.9, kept and flagged"
    # P-015 S3/T2. No model call.
    kitchen = "Cooking equipment: two floor fryers\nHood and fire suppression: wet chemical system, inspected 2026-05-12\n"
    cf = cooking_facts({"kitchen.md": "Notes\n" + kitchen})
    assert cf["equipment"]["state"] == "yes" and cf["equipment"]["terms"] == ["fryers"] and cf["hood_suppression"]["state"] == "stated"
    for key in cf:
        f = cf[key]
        assert ("Notes\n" + kitchen)[f["start"] : f["end"]] == f["quote"], "the citation points at the stated text"
    assert cooking_facts({"a.md": "Cooking equipment: none\n"})["equipment"]["state"] == "needs_review"  # P-030 rule 3
    assert cooking_facts({"a.md": "Cooking equipment: sin freidora\n"})["equipment"]["state"] == "needs_review", "negated hazard gives no yes (P-031)"
    assert cooking_facts({"a.md": "Cooking equipment: freidora y parrilla\n"})["equipment"]["terms"] == ["freidora", "parrilla"]
    assert cooking_facts({"a.md": "Cooking equipment: microwave\n"})["equipment"]["state"] == "other"
    # P-031 (D-074): (1) no negation word -> hazards present; (2) any negation word -> needs review, no points. Every line used so far.
    eq = lambda line: cooking_facts({"a.md": f"Cooking equipment: {line}\n"})["equipment"]
    for line in ("no hood and gas grill", "sin campana con parrilla", "fryer, none", "no hood with grill", "no hood y parrilla",
                 "no fryer but charbroiler", "no fryer. gas grill", "no fryer & grill", "no fryer - grill", "sin freidora pero parrilla",
                 "no fryer or grill", "no fryer; gas grill and charbroiler", "fryer: none", "fryer (none)", "fryer - none",
                 "fryer not used", "grill, no fryer", "none", "N/A", "no microwave, fryer", "no open flame", "no gas grill",
                 "not a fryer", "sin freidora", "no fryer, no grill", "dont use fryer", "don't use fryer", "never a fryer",
                 "no fryer plus grill", "no fryer only grill", "no fryer except grill", "sin freidora más parrilla",
                 "no microwave plus grill", "nunca freidora", "ninguna parrilla", "without fryer"):
        f = eq(line)
        assert f["state"] == "needs_review" and f["terms"] == [] and f["quote"] and f["reason"] == REASON_COOKING, (line, f)
    for line, terms in (("freidora y parrilla", ["freidora", "parrilla"]), ("gas grill and charbroiler", ["grill", "charbroiler"]),
                        ("notable grill", ["grill"]), ("two floor fryers", ["fryers"]), ("knot-free grill", ["grill"])):
        assert eq(line)["state"] == "yes" and eq(line)["terms"] == terms, (line, eq(line))
    assert eq("microwave")["state"] == "other" and eq("nonstick griddle")["state"] == "other"
    two = lambda text: cooking_facts({"a.md": text})["equipment"]
    assert two("Cooking equipment: fryer\nno grill on site\n")["state"] == "yes", "a newline ends the line: the next line is not read"
    assert two("Cooking equipment: no fryer\ngas grill\n")["state"] == "needs_review"
    assert equipment_fact("fryer\nno grill") == ("yes", ["fryer"], [])
    # P-033 (D-079): more negation words; whole words only.
    for line in ("ningún freidora", "nada de parrilla", "fryer w/o hood", "grill isn't used", "fryer removed", "zero fryers", "fryer isn’t used"):
        assert eq(line)["state"] == "needs_review", (line, eq(line))
    for line in ("nadal grill", "zeroed fryer", "removedly grill"):
        assert eq(line)["state"] == "yes", ("whole words only", line, eq(line))
    assert cooking_facts({"a.md": "Hood: N/A\n"})["hood_suppression"]["state"] == "not_stated"
    assert cooking_facts({"a.md": "Hood: without hood\n"})["hood_suppression"]["state"] == "none"
    assert cooking_facts({"a.md": "Hood: without hood; Ansul suppression\n"})["hood_suppression"]["state"] == "stated"
    for text in ("Taqueria Fryer and Sons\nDescription of operations: restaurant, tacos\n", "Hood Street Books\nOpen Flame Yoga LLC\n", ""):
        assert cooking_facts({"a.md": text})["equipment"]["state"] == "not_stated" and cooking_facts({"a.md": text})["hood_suppression"]["state"] == "not_stated", "names, class and cuisine words are not facts"
    with tempfile.TemporaryDirectory() as tmp:
        def ask(name: str, ops: str) -> list:
            sub = Path(tmp) / "x"
            sub.mkdir(exist_ok=True)
            (sub / "application.md").write_text(f"Named insured: {name}\nDescription of operations: {ops}\n")
            real = llm_extract.llm_extract
            llm_extract.llm_extract = lambda docs: {"fields": [], "conflicts": [], "not_sent": []}
            try:
                return process_submission(sub)["extra"]
            finally:
                llm_extract.llm_extract = real
        base = ask("Plain Holdings LLC", "bookkeeping office")
        assert base == [], base
        for nm in ("Guenther Tacos y Mas", "Blanco Street Kitchen", "Fryer and Sons Bookkeeping", "Open Flame Yoga", "Hood Street Books"):
            assert ask(nm, "bookkeeping office") == base, f"T2: the name {nm!r} must not start the cooking ask"
        assert ask("Plain Holdings LLC", "taqueria, tacos") == base, "T2: a cuisine word does not start the ask"
        assert "cooking equipment" in ask("Plain Holdings LLC", "restaurant"), "a class word still asks the producer"
    # P-028 (D-075): a saved run's stored cache key equals the key recomputed from its inputs; a changed file changes it.
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        sub = tmp / "inbox" / "SUB-403"
        sub.mkdir(parents=True)
        (sub / "application.md").write_text("Named insured: Example LLC\n")
        saved_env = {k: os.environ.get(k) for k in ("LLM_MODEL", "LLM_BASE_URL")}
        os.environ.update(LLM_MODEL="key-check-model", LLM_BASE_URL="http://localhost:11434/v1")
        real_extract = llm_extract.llm_extract
        llm_extract.llm_extract = lambda *_a, **_k: {"fields": [], "conflicts": []}  # no model call
        try:
            write_drafts(tmp / "inbox", tmp / "pending", tmp / "data" / "conflicts")
            run = read_saved_run("SUB-403", tmp / "data" / "extractions")
            again = llm_extract.key_for(sources.read_folder(sub))
            assert run["cache_key"] and run["cache_key"] == again, (run.get("cache_key"), again)
            assert again == llm_extract.cache_key(sources.read_folder(sub), "key-check-model")
            (sub / "application.md").write_text("Named insured: Other LLC\n")
            assert llm_extract.key_for(sources.read_folder(sub)) != run["cache_key"], "a changed file is another key"
            # B-284 (D-076): through the real llm_extract and a stubbed host, the stored key is the name of the cache file written.
            llm_extract.llm_extract = real_extract
            real_post, real_cache, real_key = llm_extract._post, llm_extract.CACHE, os.environ.get("LLM_API_KEY")
            reply = {"fields": [{"field_id": "named_insured", "value": "Other LLC", "source": "application.md", "quote": "Other LLC", "confidence": 0.95}]}
            llm_extract._post = lambda *_a, **_k: {"choices": [{"message": {"content": json.dumps(reply)}}], "usage": {"total_tokens": 10}}
            llm_extract.CACHE, os.environ["LLM_API_KEY"] = tmp / "cache", "stub-not-sent"
            try:
                write_drafts(tmp / "inbox", tmp / "pending", tmp / "data" / "conflicts")
                run = read_saved_run("SUB-403", tmp / "data" / "extractions")
                written = sorted(p.stem for p in (tmp / "cache" / "extractions").glob("*.json"))
                assert written == [run["cache_key"]], (written, run["cache_key"])
            finally:
                llm_extract._post, llm_extract.CACHE = real_post, real_cache
                os.environ.pop("LLM_API_KEY", None) if real_key is None else os.environ.__setitem__("LLM_API_KEY", real_key)
        finally:
            llm_extract.llm_extract = real_extract
            for k, v in saved_env.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
    # P-040 / P-041 (D-088): letters are never loss runs; a file is complete only with nothing left to review.
    run_107 = ("# Northline Mutual (fictional) - Loss Run Report\nValued through: 2026-09-30\n- Northline Mutual (fictional), policy 2023-03-01 to 2024-03-01: 0 claims, $0 paid\n"
               "- Policy 2024-03-01 to 2025-03-01: 0 claims, $0 paid\n")
    run_110 = "# Loss runs\nIssued by Lakeshore Specialty (fictional)\nValued through: 2026-09-30\n- Lakeshore Specialty (fictional), 2023-24: 0 claims\n- 2024-25: 0 claims\n- Open reserve: $0\n"
    run_es = "# Historial de siniestros - Seguros del Valle (ficticia)\nAseguradora: Seguros del Valle (ficticia)\nVigencia 2025-01-01 a 2026-01-01\nValuado al 2026-09-30\nSin reclamos en este periodo.\n"
    letter_112 = ("# Carta de pérdidas\nNamed insured: Hernandez Plumbing & Drain LLC\nValued through: 2026-09-30\n"
                  "- Sin reclamos reportados en los ultimos 3 anos (2024, 2025 y hasta 2026-09-30).\n- Carta firmada por el agente anterior (ficticio), 2026-09-22.\n")
    letter_123 = ("# Carta de pérdidas\nNamed insured: Tienda Luna Azul LLC\nValued through: 2026-09-30\n"
                  "- Sin reclamos reportados en los ultimos 5 anos segun el solicitante.\n- Carta de pérdidas sin reclamos, agente anterior, 2026-09-30.\n")
    letters = [letter_112, letter_123,
               "# No known loss letter\nValued through: 2026-08-31\n- No known loss letter from prior agent, dated 2026-08-20.\n- No claims in the last five years to our knowledge.\n",
               "# No known loss letter\nValued through: 2026-09-30\n- No known loss letter from prior carrier, 2026-09-30.\n- Owner states no claims in five years.\n",
               "Valued through 2026-09-30. Sin pérdidas conocidas en los últimos cinco años.", "Valued as of 2026-09-30: No hay reclamaciones. Carta de no pérdidas."]
    for text in letters:
        assert loss_run_kind(text) == "letter", text
    for text in (run_107, run_110, run_es):
        assert loss_run_kind(text) == "loss_run", text
    # @model-risk H1: the letters without their headings, and other wordings, are still letters.
    for text in (letter_112.replace("# Carta de pérdidas", "# Historial de pérdidas"), letter_123.replace("# Carta de pérdidas\n", "").replace("Carta de pérdidas sin reclamos", "Sin reclamos"),
                 "Valued through 2026-09-30. No claims letter: the owner states the account has been loss-free.",
                 "Valued through 2026-09-30. Sin siniestros en cinco años, declara el solicitante.",
                 "Valued through 2026-09-30. Aucun sinistre depuis 2021 selon le proprietaire.", "Valued through 2026-09-30. Sem sinistros, declara o dono."):
        assert loss_run_kind(text) == "letter", text
    assert loss_run_kind("Carta de historial de reclamaciones\nFecha de valuacion: 2026-10-01\nNo se reportaron reclamaciones en el periodo.") == "unclear", "no carrier: review, not dropped"
    assert loss_run_kind("Loss runs\nValued through: 2026-09-30\nNo claims reported in the period. Claim count: 0.\n_FICTIONAL. No real applicant, person or business._") == "unclear"
    assert loss_run_kind("Loss history: no claims to our knowledge. Valued through 2026-09-30.") == "letter", "@model-risk H1: a no-claims statement by hearsay is a letter"
    assert loss_run_kind("Loss runs valued through 2026-09-30. 1 claim, 2025-03-01, paid $4,000.") == "unclear", "no carrier or period: review"
    assert loss_run_kind(run_107 + "No known losses.") == "unclear", "a letter phrase beside a full loss run: review"
    # P-043 (D-089): an applicant's or agent's summary that names a carrier, a period and claims is not a carrier loss run.
    for text in ("Loss summary prepared by the agent\nCarrier: Northline Mutual (fictional), policy 2024-01-01 to 2025-01-01\nValued through 2026-09-30\n1 claim, $4,000 paid.",
                 "Applicant states: prior carrier Lakeshore Specialty (fictional), 2023-24 and 2024-25, valued through 2026-09-30, 1 claim paid $2,100.",
                 "Resumen preparado por el agente. Aseguradora: Seguros del Valle (ficticia), vigencia 2025-01-01 a 2026-01-01, valuado al 2026-09-30, 1 reclamo pagado $3,000."):
        assert loss_run_kind(text) == "unclear", text
    # @model-risk H1 (check of P-043): naming a carrier is not issuing; these 14 non-carrier preambles all go to review.
    body = "Carrier: Northline Mutual (fictional), policy 2024-01-01 to 2025-01-01. Valued through 2026-09-30. 1 claim, $4,000 paid."
    for pre in ("Loss history provided by the applicant.", "Submitted by the agent.", "Agent's loss summary.", "Producer summary of prior losses.",
                "Prepared by Smith Insurance Agency.", "From: Jane Doe, owner of Acme LLC.", "We had one claim with our prior carrier.", "Applicant-provided loss history.",
                "Summary from broker.", "Written by the applicant.", "Insured: Acme LLC. Applicant's own summary.", "self-reported", "Per insured:", "The insured reports:"):
        assert loss_run_kind(pre + "\n" + body) == "unclear", pre
    assert loss_run_kind("# Loss runs (typed)\nValued through: 2026-09-30\n- Northline Mutual (fictional), policy 2023-03-01 to 2024-03-01: 0 claims, $0 paid\n") == "unclear", \
        "a carrier named only in a row, with no issuer header or issued-by line: review"
    assert loss_run_kind("Northline Mutual Insurance Company - Loss Run Report\n" + body) == "loss_run"
    # @model-risk H1 (LOOK-AGAIN): business names with a carrier word, the author naming the carrier, and people as preparer all go to review.
    for head in ("# Specialty Plumbing LLC - Loss History", "Casualty Restoration Inc. loss history", "Surplus Supply Co - claims summary",
                 "Loss history - prior carrier Northline Mutual (fictional)", "My prior carrier was Northline Mutual (fictional).", "Re: loss history with Northline Mutual (fictional)",
                 "Subject: Northline Mutual loss history", "My company's claims with Northline Mutual (fictional)", "Client's loss history: Northline Mutual (fictional)",
                 "Northline Mutual - I had one claim", "Prepared by John Smith, owner, for Northline Mutual Insurance Company",
                 "Loss summary prepared by Jane Doe for submission to Northline Mutual", "Compiled by account manager. Northline Mutual (fictional)", "Prepared by Acme CPA firm",
                 "Lakeshore Specialty - Loss Run Report"):  # the last names another carrier than the one stated
        assert loss_run_kind(head + "\n" + body) == "unclear", head
    es_body = "Aseguradora: Seguros del Valle (ficticia), vigencia 2025-01-01 a 2026-01-01, valuado al 2026-09-30, 1 reclamo pagado $3,000."
    assert loss_run_kind("Specialty Tacos LLC - historial\n" + es_body) == "unclear"
    for good in ("Northline Mutual (fictional) - Loss Run Report\nAgent: Smith Insurance Agency\n" + body, "# Northline Mutual Insurance Company Loss Runs\n" + body,
                 "Loss runs\nIssued by Northline Mutual (fictional).\n" + body, "Seguros del Valle (ficticia) - Historial de siniestros\n" + es_body):
        assert loss_run_kind(good) == "loss_run", good
    box = {"loss_run_valued_through": {"field_id": "loss_run_valued_through", "value": "2026-09-30", "source": "loss-runs.md", "quote": "2026-09-30", "needs_review": False, "reason": None}}
    gate_loss_run(box, {"loss-runs.md": "Written by the applicant.\n" + body})
    assert box["loss_run_valued_through"]["needs_review"] and box["loss_run_valued_through"]["value"], "kept for review, never silently satisfied"
    box = {"loss_run_valued_through": {"field_id": "loss_run_valued_through", "value": "2026-09-30", "source": "loss-runs.md", "quote": "2026-09-30", "needs_review": False, "reason": None}}
    gate_loss_run(box, {"loss-runs.md": "Applicant states: prior carrier Lakeshore Specialty (fictional), 2023-24, valued through 2026-09-30, 1 claim paid $2,100."})
    row = box["loss_run_valued_through"]
    assert row["value"] == "2026-09-30" and row["needs_review"] and row["reason"] == RUN_UNCLEAR.format("loss-runs.md"), "P-043: kept, needs review"
    lr = lambda src, val="2026-09-30": {"loss_run_valued_through": {"field_id": "loss_run_valued_through", "value": val, "source": src, "quote": val, "needs_review": False, "reason": None}}
    for text in letters:
        box = lr("loss-runs.md")
        gate_loss_run(box, {"loss-runs.md": text})
        row = box["loss_run_valued_through"]
        assert row["value"] is None and row["needs_review"] and row["reason"] == NKL_DROPPED.format("loss-runs.md"), row
    box = lr("loss-runs.md")
    gate_loss_run(box, {"loss-runs.md": run_107})
    assert box["loss_run_valued_through"]["value"] == "2026-09-30" and not box["loss_run_valued_through"]["needs_review"]
    box = lr("email.md")
    gate_loss_run(box, {"email.md": "Loss runs valued 2026-09-30 attached.", "loss-runs.md": run_110})
    assert not box["loss_run_valued_through"]["needs_review"], "a date a real loss run shows is kept, whichever file the model cited"
    box = lr("email.md")
    gate_loss_run(box, {"email.md": "Loss runs valued 2026-09-30 per the letter.", "letter.md": letters[2].replace("2026-08-31", "2026-09-30")})
    assert box["loss_run_valued_through"]["value"] is None and box["loss_run_valued_through"]["reason"] == NKL_DROPPED.format("letter.md"), "@model-risk H1: a date only a letter shows is dropped, whichever file is cited"
    box = lr("email.md")
    gate_loss_run(box, {"email.md": "Loss runs valued through 2026-09-30, will send."})
    assert box["loss_run_valued_through"]["value"] and box["loss_run_valued_through"]["reason"] == RUN_UNCLEAR.format("email.md"), "unclear: kept, needs review"

    def run_case(rows: dict, files: dict, conflicts: list | None = None) -> dict:
        """process_submission with a stubbed model reply; no call is made."""
        good = {"named_insured": "Example LLC", "premises_address": "100 Main St, San Antonio, TX 78205", "effective_date": "2027-03-01",
                "operations": "accounting office", "sales_or_payroll": "900000", "tiv_building": "500000", "construction": "Masonry",
                "year_built": "1998", "loss_run_valued_through": "2026-09-30"}
        reply = []
        for field, value in good.items():
            row = {"field_id": field, "value": value, "source": "application.md", "quote": value, "confidence": 0.95, "needs_review": False, "reason": None}
            row.update(rows.get(field) or {})
            reply.append(row)
        with tempfile.TemporaryDirectory() as tmp:
            sub = Path(tmp) / "SUB-500"
            sub.mkdir()
            (sub / "application.md").write_text("\n".join(f"{k}: {v}" for k, v in good.items()) + "\n")
            for name, text in files.items():
                (sub / name).write_text(text)
            real = llm_extract.llm_extract
            llm_extract.llm_extract = lambda docs: {"fields": [dict(r) for r in reply], "conflicts": list(conflicts or []), "not_sent": []}
            try:
                return process_submission(sub)
            finally:
                llm_extract.llm_extract = real

    on_run = {"loss_run_valued_through": {"source": "loss-runs.md"}}
    clean = run_case(on_run, {"loss-runs.md": run_107})
    assert clean["status"] == "complete" and clean["complete"] and ready_to_route(clean) and clean["request"] is None, clean["status"]
    for letter in (letter_112, letter_123, letter_112.replace("# Carta de pérdidas", "# Historial de pérdidas")):  # SUB-112, SUB-123, 112 renamed
        rep_ = run_case(on_run, {"loss-runs.md": letter})
        row = {r["field_id"]: r for r in rep_["fields"]}["loss_run_valued_through"]
        assert rep_["status"] == "incomplete" and not rep_["complete"] and not ready_to_route(rep_), rep_["status"]
        assert row["value"] is None and "loss_run_valued_through" in rep_["missing"] and rep_["request"], row
    for field in ("sales_or_payroll", "effective_date"):  # SUB-111 (sales), SUB-125 (effective date): flagged, no conflict raised
        rep_ = run_case({**on_run, field: {"needs_review": True, "reason": "check against the email"}}, {"loss-runs.md": run_107})
        assert rep_["status"] == REVIEW_PENDING and rep_["complete"] is False and rep_["missing"] == [], rep_["status"]
        assert rep_["request"] is None, "nothing to ask the producer; the review is the underwriter's"
        assert ready_to_route(rep_), "sends stay gated as before: approve still lists the value for acknowledgement (D-039)"
    sq = {"field": "square_feet", "values": [{"value": "16800", "source": "email.md"}, {"value": "14200", "source": "application.md"}], "resolution": "unresolved"}
    rep_ = run_case(on_run, {"loss-runs.md": run_107}, [sq])
    assert rep_["status"] == REVIEW_PENDING and not ready_to_route(rep_) and rep_["request"], "an open conflict: review pending, held, producer asked"
    rep_ = run_case({**on_run, "year_built": {"value": None}}, {"loss-runs.md": run_107})
    assert rep_["status"] == "incomplete", "a missing field is incomplete, not review pending"
    print("prepare ok")
