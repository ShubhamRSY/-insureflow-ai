"""Steps 2–3 — cite fields, flag conflicts, write missing-info requests.

Extraction is an LLM call in llm_extract.py. Pattern labels are no longer the reader.
The API key is OPENAI_API_KEY in the environment. It is never written to a file.

Run: python underwriting_pipeline/ai/prepare.py
Inbox: python underwriting_pipeline/ai/prepare.py simulation/inbox simulation/pending-approval deliverables/data-engineer/conflicts
"""

import json
import re
import sys
import tempfile
from pathlib import Path

import llm_extract
import sources

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


_AMOUNT = re.compile(
    r"(?i)^(?:about|around|approximately|roughly)?\s*"
    r"\$?\s*(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*([kmb])?"
    r"(?:\s*(?:square\s+feet|sq\.?\s*ft\.?|sqft|sf))?\s*$"
)
_OPS_CLASS = (
    ("bar", ("nightclub", "night club", " bar", "bar ")),
    ("restaurant", ("restaurant", "taco", "kitchen")),
    ("habitational", ("habitational", "apartment", "flats")),
    ("contractor", ("contractor", "painting")),
    ("wholesale", ("wholesale",)),
    ("retail", ("retail",)),
    ("office", ("office",)),
)


def amount_value(value: str) -> int | None:
    """220k, $1.2M, 220,000, and 2,200 sq ft are numbers. A sentence is not."""
    if not value:
        return None
    match = _AMOUNT.match(value.strip())
    if not match:
        return None
    number = float(match.group(1).replace(",", ""))
    suffix = (match.group(2) or "").lower()
    factor = {"": 1, "k": 1_000, "m": 1_000_000, "b": 1_000_000_000}[suffix]
    return int(round(number * factor))


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
    if not kind_left or kind_left != kind_right:
        return False
    units_left = re.search(r"(\d+)\s*-?\s*units?", left.lower())
    units_right = re.search(r"(\d+)\s*-?\s*units?", right.lower())
    if units_left and units_right and units_left.group(1) != units_right.group(1):
        return False
    return not _ops_contradict(left, right)


def agrees(field: str, left: str, right: str) -> bool:
    if field in {"sales_or_payroll", "tiv_building", "square_feet"}:
        amount_left, amount_right = amount_value(left), amount_value(right)
        return amount_left is not None and amount_left == amount_right
    if field == "operations":
        return same_operations(left, right)
    return False


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
    """P-002. Flag a bad ZIP or a ZIP that does not match the city. Do not rewrite the city."""
    value = str(row.get("value") or "")
    found = re.search(r"\b(\d{5})\b", value)
    if not found:
        return
    cities = _zip_cities().get(found.group(1))
    city = re.search(r"([A-Za-z][A-Za-z .'-]{1,}),\s*(?:TX|Texas)\b", value)
    name = city.group(1).strip().casefold() if city else ""
    if not cities or not name or name not in cities:
        row["address_check"] = "address invalid"
        row["needs_review"] = True
    else:
        row["address_check"] = "ok"


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


def _set_cited(merged: dict, field: str, value: str, source: str, start: int, end: int) -> None:
    merged[field] = {
        "field_id": field,
        "value": value,
        "source": source,
        "start": start,
        "end": end,
        "confidence": 0.95,
        "needs_review": False,
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


def apply_locations(merged: dict, conflicts: list, texts: dict) -> list[dict]:
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
        )
    return locations


def apply_document_rules(merged: dict, conflicts: list, texts: dict) -> None:
    """Cited document rules. They do not call the model and do not invent a date."""
    run = carrier_run_date(texts)
    if run:
        name, value, start, end = run
        _set_cited(merged, "loss_run_valued_through", value, name, start, end)
    for name, text in texts.items():
        low = text.lower()
        at = low.find("joisted masonry")
        if at < 0:
            continue
        current = (merged["construction"]["value"] or "").lower()
        if current in {"", "masonry"}:
            _set_cited(merged, "construction", text[at : at + len("joisted masonry")], name, at, at + len("joisted masonry"))
        break
    for name, text in texts.items():
        match = re.search(r"\bcook\s+([A-Za-z]+)", text)
        if not match:
            continue
        food = match.group(1).lower()
        current = (merged["operations"]["value"] or "").lower()
        if food in current and "restaurant" in current:
            break
        _set_cited(merged, "operations", f"{food} restaurant", name, match.start(), match.end())
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
    readable = [doc for doc in docs if doc.get("text") and not doc.get("needs_human")]
    if not readable:
        extracted = {"fields": [], "conflicts": []}
    else:
        try:
            extracted = llm_extract.llm_extract(docs)
        except Exception as exc:
            extracted = {"fields": [], "conflicts": []}
            error = llm_extract._safe(str(exc))
    for row in extracted["fields"]:
        field_id = row.get("field_id")
        if field_id not in merged or not row.get("value"):
            continue
        cur = merged[field_id]
        if cur["value"] is None:
            row["value"] = _canonical(field_id, row["value"])
            merged[field_id] = row
        elif agrees(field_id, cur["value"], row["value"]):
            cur["value"] = _canonical(field_id, cur["value"])
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
        sides = [side.get("value") or "" for side in item.get("values") or [] if side.get("value")]
        if len(sides) >= 2 and all(agrees(item.get("field"), sides[0], side) for side in sides[1:]):
            field_id = item.get("field")
            if field_id in merged and merged[field_id]["value"] is None:
                merged[field_id]["value"] = _canonical(field_id, sides[0])
                merged[field_id]["needs_review"] = False
            continue
        if item["field"] in merged:
            merged[item["field"]]["value"] = None
            merged[item["field"]]["needs_review"] = True
        conflicts.append(item)
    _apply_reply(conflicts, texts.get("reply.md", ""))
    apply_document_rules(merged, conflicts, texts)
    locations = apply_locations(merged, conflicts, texts)
    blob = "\n".join(texts.values()).lower()
    extra = []
    if any(word in blob for word in ("restaurant", "fryer", "taco", "kitchen")):
        for label, cues in (
            ("cooking equipment", ("cooking equipment", "fryer")),
            ("hood and fire suppression", ("hood", "suppression")),
            ("sprinklers", ("sprinkler",)),
            ("liquor sales", ("liquor",)),
            ("hours", ("hours", " open ")),
        ):
            if not any(cue in blob for cue in cues):
                extra.append(label)
    needs_human = [doc["name"] for doc in docs if doc.get("needs_human")]
    drop_premises_without_zip(merged, needs_human)
    if merged["premises_address"].get("value"):
        flag_invalid_address(merged["premises_address"])
    open_conflicts = [c for c in conflicts if c.get("resolution") != "resolved"]
    rows = [merged[field] for field in FIELDS]
    report = completeness(rows)
    if open_conflicts or extra:
        report["complete"] = False
    report["conflicts"] = conflicts
    report["extra"] = extra
    report["fields"] = rows
    report["folder"] = folder.name
    report["sprinklers"] = "yes" if sprinklers_yes(texts) else "no"
    report["needs_human"] = needs_human
    report["locations"] = locations
    report["error"] = error
    if report["complete"]:
        report["request"] = None
    else:
        text = _request(folder.name, report["missing"], [c["field"] for c in open_conflicts])
        if extra:
            text += "\nAlso send:\n" + "\n".join(f"- {item}" for item in extra) + "\n"
        report["request"] = text
    return report


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
        report = process_submission(folder)
        reports.append(report)
        dest = draft_dir / f"{folder.name}.md"
        side = conflict_dir / f"{folder.name}.json"
        if report["request"]:
            dest.write_text(report["request"])
        conflicts_out = report["conflicts"]
        if conflicts_out:
            side.write_text(
                json.dumps({"submission": folder.name, "conflicts": conflicts_out}, indent=2) + "\n"
            )
        elif side.exists():
            prior = json.loads(side.read_text())
            kept = prior.get("conflicts") or []
            if kept and all(c.get("resolution") == "resolved" for c in kept):
                conflicts_out = kept
            else:
                side.unlink()
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
                }
            )
        (extract_dir / f"{folder.name}.json").write_text(
            json.dumps(
                {"submission": folder.name, "fields": fields, "conflicts": conflicts_out},
                indent=2,
            )
            + "\n"
        )
    return reports


def approve(
    draft: Path,
    actor: str,
    out_dir: Path,
    reason: str = "",
    report: dict | None = None,
) -> Path:
    """The user may override. The account manager may approve when the agency rules pass."""
    import sys

    app = Path(__file__).resolve().parents[1] / "app"
    if str(app) not in sys.path:
        sys.path.insert(0, str(app))
    from package import agency_problem

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
        problem = agency_problem(report)
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
        assert amount_value("2,200 sq ft") == 2200
        assert amount_value("2200 sf") == 2200
        assert amount_value("8 units") is None
        assert agrees("sales_or_payroll", "220000", "about 220k")
        assert same_operations(
            "habitational, 8 units, no commercial cooking",
            "Small apartments, 8 units, sprinklers throughout.",
        )
        assert not same_operations("accounting office", "restaurant, tacos, fryer")
        same_area = _square_feet({"a.md": "Shop is 2,200 sq ft.", "b.md": "2200 sf"})
        assert {row[0] for row in same_area} == {"2200"}
        try:
            approve(Path("underwriting_pipeline/ai/prepare.py"), "", Path("simulation/to-producer"))
            raise SystemExit("empty approver should fail")
        except ValueError:
            pass
        with tempfile.TemporaryDirectory() as tmp:
            draft = Path(tmp) / "SUB-000.md"
            draft.write_text("Nothing has been declined.\n")
            out = Path(tmp) / "to-producer"
            out.mkdir()
            try:
                approve(draft, "account-manager", out, reason="ready")
                raise SystemExit("manager without a report should fail")
            except ValueError:
                pass
            try:
                approve(draft, "ai-engineer-assistant", out)
                raise SystemExit("assistant approve should fail")
            except ValueError:
                pass
            sent = approve(draft, "user", out)
            assert "Approved-by: user (override)" in sent.read_text()
        print("prepare ok")
