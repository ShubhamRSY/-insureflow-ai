"""P-055 (D-105): the pilot scope detector. A file it puts out of scope goes to manual intake as a whole file.

Deterministic rules only. No model call, no OCR of its own: it reads the documents sources.read_folder() already returned.
Any change to a rule below is a change under D-017 (`approve change P-###`) and must be revalidated.
Fail closed: an error, an unsure language count, an unknown text layer, or no identifiable application is manual intake.
"""

import re

import llm_extract

VERSION = "scope-v2"  # model-inventory.md; bump with every rule change
IMAGE = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
REASONS = {
    "scanned_application": "Manual intake: scanned application",
    "multiple_locations": "Manual intake: multiple locations",
    "non_english": "Manual intake: non-English documents (Spanish)",
    "language_unsure": "Manual intake: document language not clear",
    "not_identified": "Manual intake: application not identified",
    "text_layer_unknown": "Manual intake: application text layer not known",
    "unidentified_scan": "Manual intake: a scanned document could not be identified",
    "detector_error": "Manual intake: scope check failed (detector error)",
}
MIN_WORDS = 5  # fewer common English + Spanish words than this: the language count is unsure
UNSURE_RATIO = 0.5  # Spanish words above this share of the English words (but not more than them): unsure

# Common words that belong to one language only (no "a", "no", "me": they are words in both).
# Field labels are words of the document: an English form's labels count as English, a Spanish form's as Spanish.
ENGLISH = frozenset("the and of to in for with is are on at by from or not this that yes none per as be all if any it we our your has have was were will "
                    "named insured premises effective date construction years business operations employees sales building year built mailing entity type line "
                    "stories sprinklers cooking loss runs expiring carrier claims bankruptcy submission application description address payroll personal property "
                    "square feet occupancy hours".split())
SPANISH = frozenset(
    "el la los las de del y en con para por que un una sin es se su al mi como pero tiene tienen hay son este esta lo les "
    "fecha anos años numero número ventas tipo linea línea entidad asegurado direccion dirección empleados negocio operaciones propiedad edificio "
    "construccion construcción pisos aspersores cocina solicitud gracias hola quiero tengo soy duena dueña tienda mando documentos despues después "
    "seguro cotizacion cotización cerveza vino asientos servicio llevar mesa".split()
)
NAME_LINE = re.compile(r"(?im)^([^\n:]{0,40}\b(?:name|insured|address|premises|location|contact|producer|agency|dba|asegurado|direccion|dirección|domicilio|riesgo)\b[^\n:]*:)[^\n]*$")
NAME_VALUE = re.compile(r"(?im)^\W*(?:named insured|insured name|business name|dba|asegurado|nombre del asegurado)\s*:\s*(.+?)\s*$")
LOSS_RUN = re.compile(r"loss|siniestr", re.I)
LABELS = (r"named insured|insured\s*:|asegurado", r"premises|location|direcci[oó]n", r"effective date|fecha efectiva", r"years in business|a[nñ]os en el negocio",
          r"construction|construcci[oó]n", r"year built", r"operations|operaciones", r"employees|empleados", r"\bacord\b")
LOC_LABELS = (re.compile(r"(?i)\(\s*(?:loc(?:ation)?|ubicaci[oó]n)\.?\s*#?\s*(\d+)\s*\)"),
              re.compile(r"(?im)^\W*(?:loc(?:ation)?|ubicaci[oó]n)\.?\s*#?\s*(\d+)\s*[:\-–—.)]"))  # "(loc 2)", "Location 2:", "Location #2:", "Location 2 -"
LOC_ORDINAL = re.compile(r"(?im)^\W*(?:second|third|fourth|fifth|additional|other|another)\s+(?:location|premises)\b")
LOC_HEADING = re.compile(r"(?im)^\W*(?:locations|premises|properties)\b[^\n]*:\s*$")
LIST_ITEM = re.compile(r"^\s*(?:\d+[.)]|[-*])\s+\S")
PREMISES_LINE = re.compile(r"(?im)^\W*premises(?:\s+address)?\s*\d*\s*:\s*(.+?)\s*$")
STREET = re.compile(r"\b\d{1,6}\s+[A-Za-z0-9 .]+?\s(?:st|street|rd|road|ave|avenue|blvd|dr|drive|ln|lane|hwy|way|pkwy|ct|court|pl|place|fwy|trl)\b\.?", re.I)


def _is_sheet(doc: dict) -> bool:
    name = doc["name"].lower()
    return name.endswith((".csv", ".xlsx")) or any(w in name for w in ("schedule", "sov", "locations")) and not any(w in name for w in ("email", "loss"))


def _kind(doc: dict) -> str:
    """email, loss_run, schedule, reply or other (a possible application), from the file name and type only."""
    name = doc["name"].lower()
    if "email" in name:
        return "email"
    if LOSS_RUN.search(name):
        return "loss_run"
    if any(w in name for w in ("application", "solicitud", "acord")):
        return "other"  # a csv or xlsx called application is the application, not a schedule
    if _is_sheet(doc):
        return "other" if _label_count(doc) >= 3 else "schedule"  # a sheet that holds application labels is the application
    if name.startswith("reply"):
        return "reply"
    return "other"


def _label_count(doc: dict) -> int:
    text = (doc.get("text") or "").lower()
    return sum(bool(re.search(label, text)) for label in LABELS)


def _is_application(doc: dict) -> bool:
    name = doc["name"].lower()
    return any(w in name for w in ("application", "solicitud", "acord")) or _label_count(doc) >= 3


def _unreadable(doc: dict) -> bool:
    return bool(doc.get("needs_human") or doc.get("unread") or doc.get("unread_pages"))


def _scan_layer(doc: dict) -> str:
    """scan, typed or unknown for one document. A scanned page anywhere counts."""
    suffix = "." + doc["name"].rsplit(".", 1)[-1].lower() if "." in doc["name"] else ""
    if suffix in IMAGE or doc.get("ocr_words") or doc.get("ocr_confidence") is not None:
        return "scan"
    if any("scan" in (p.get("reason") or "") for p in doc.get("unread_pages") or []):
        return "scan"
    if _unreadable(doc) or not (doc.get("text") or "").strip():
        return "unknown"
    return "typed"


UNIT = re.compile(r"(?i)[,\s]+(?:suite|ste|unit|apt|apartment|floor|fl|room|rm|#)\.?\s*\w+")


def _addresses(doc: dict) -> list[str]:
    """Premises addresses of a schedule document (csv, xlsx or a file named schedule), one per place: "100 Main St" and
    "100 Main Street, Ste 2" are the same place (the pipeline's own address comparison, after a unit is dropped)."""
    found, col = [], None
    raw: list[str] = []
    for line in (doc.get("text") or "").splitlines():
        cells = line.split("\t")
        if line.startswith("sheet:"):
            col = None
        elif len(cells) > 1 and any("address" in c.lower() for c in cells) and not any(STREET.search(c) for c in cells):
            heads = [i for i, c in enumerate(cells) if "address" in c.lower() and not re.search(r"mail|prior|previous|former", c, re.I)]
            col = heads[0] if heads else None
        elif col is not None and col < len(cells) and cells[col].strip():
            raw.append(cells[col])
        elif col is None and not re.search(r"mail|prior|previous|former", line, re.I):
            raw += [m.group(0) for m in STREET.finditer(line)]
    for address in raw:
        address = UNIT.sub("", address.strip())
        if address and not any(llm_extract.same_address(address, other) for other in found):
            found.append(address)
    return found


def _multi_in_application(app: dict) -> bool:
    """Two or more premises named in the application: "(loc 2)", "Location 2:" and its forms, a numbered or bulleted list under a
    Locations heading, "Second location:", or two distinct premises addresses. A mailing or prior address is not a location."""
    text = app.get("text") or ""
    numbers = {n for rx in LOC_LABELS for n in rx.findall(text)}
    if len(numbers) >= 2 or any(int(n) >= 2 for n in numbers) or LOC_ORDINAL.search(text):
        return True
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if LOC_HEADING.match(line):
            items = 0
            for nxt in lines[i + 1 :]:
                if not nxt.strip():
                    break
                items += bool(LIST_ITEM.match(nxt))
            if items >= 2:
                return True
    places: list[str] = []
    for value in PREMISES_LINE.findall(text):
        for part in llm_extract.address_list(value) or [value]:
            part = UNIT.sub("", re.sub(r"\(\s*loc[^)]*\)", "", part, flags=re.I).strip())
            if part and not any(llm_extract.same_address(part, o) for o in places):
                places.append(part)
    return len(places) >= 2


def _language(text: str, names: list[str] | tuple = ()) -> str:
    """english, spanish or unsure. Names and addresses do not count: the value of a name or address line is left out, and the
    insured's name is left out wherever it recurs. Field labels count in their own language."""
    text = NAME_LINE.sub(r"\1", text)
    for name in sorted(names, key=len, reverse=True):
        text = re.sub(re.escape(name), " ", text, flags=re.I)
    words = re.findall(r"[a-záéíóúñü]+", text.lower())
    en, es = sum(w in ENGLISH for w in words), sum(w in SPANISH for w in words)
    if en + es < MIN_WORDS or (es <= en and es > UNSURE_RATIO * en):
        return "unsure"
    return "spanish" if es > en else "english"


def detect(docs: list[dict]) -> dict:
    """{"version", "in_scope", "reasons": [{"code", "text"}]}: every matched reason. Never raises: an error is manual intake."""
    try:
        codes = _codes(docs)
    except Exception:  # fail closed: whatever went wrong, a person reads this file
        codes = ["detector_error"]
    return {"version": VERSION, "in_scope": not codes, "reasons": [{"code": c, "text": REASONS[c]} for c in codes]}


def _codes(docs: list[dict]) -> list[str]:
    codes: list[str] = []

    def add(code):
        if code not in codes:
            codes.append(code)

    apps = [d for d in docs if _kind(d) == "other" and _is_application(d)]
    if not apps:
        add("not_identified")
    layers = [_scan_layer(d) for d in apps]
    if "scan" in layers:
        add("scanned_application")
    if "unknown" in layers:
        add("text_layer_unknown")
    for d in docs:  # a document no name identifies as email, loss run, schedule or reply is part of the application when it is a scan
        if _kind(d) == "other" and d not in apps:
            if _unreadable(d) and _scan_layer(d) != "typed":
                add("unidentified_scan")
            elif _scan_layer(d) == "scan":
                add("scanned_application")
    places: list[str] = []
    for d in docs:  # every csv, xlsx or schedule file is counted for address rows, even when it also holds application labels
        if _is_sheet(d):
            places += [a for a in _addresses(d) if not any(llm_extract.same_address(a, o) for o in places)]
    if len(places) >= 2 or any(_multi_in_application(d) for d in apps):
        add("multiple_locations")
    names = [m for d in docs for m in NAME_VALUE.findall(d.get("text") or "")]
    # The language rule is for the application. With no application to read, the other documents are checked instead (stricter only).
    for d in apps or [d for d in docs if _kind(d) in ("email", "other") and (d.get("text") or "").strip()]:
        lang = _language(d.get("text") or "", names)
        if lang == "spanish":
            add("non_english")
        elif lang == "unsure" and d in apps:
            add("language_unsure")
    return codes


def reasons_text(scope: dict | None) -> list[str]:
    """The card's lines, e.g. ["Manual intake: scanned application"]. Empty for an in-scope file or a run saved before P-055."""
    return [r["text"] for r in (scope or {}).get("reasons") or []] if scope and scope.get("in_scope") is False else []


if __name__ == "__main__":
    import sys
    import tempfile
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import sources

    inbox = Path(__file__).resolve().parents[2] / "simulation" / "inbox"  # read only

    def codes_of(sub):
        return [r["code"] for r in detect(sources.read_folder(inbox / sub))["reasons"]]

    def doc(name, text="", **extra):
        return {"name": name, "text": text, "needs_human": False, **extra}

    APP = ("Named insured: Example Roofing LLC\nPremises address: 100 Main St, Austin, TX 78701\nEffective date: 2027-01-01\nYears in business: 9\n"
           "Operations: General office work for the business, no public visits, and the staff are all on site.\nConstruction: masonry\n")
    EMAIL = "Subject: quote\n\nHi, please quote this for the business and send the loss runs to the producer. Thanks."
    SCHED2 = "source\tloc\taddress\tcity\nX\t1\t100 Main St\tAustin\nX\t2\t200 Oak Ave\tAustin"
    ok = detect([doc("application.md", APP), doc("email.md", EMAIL)])
    assert ok["in_scope"] and ok["reasons"] == [] and ok["version"] == VERSION, ok

    # criteria 4 and 3: email-only files (dev SUB-142 English, SUB-143 Spanish)
    assert codes_of("SUB-142") == ["not_identified"], codes_of("SUB-142")
    assert codes_of("SUB-143") == ["not_identified", "non_english"], codes_of("SUB-143")
    # criterion 1: a SUB-170-style scanned application (jpg); criterion 2 too, because its schedule lists several premises
    c170 = codes_of("SUB-170")
    assert "scanned_application" in c170, c170
    # criterion 2 and several criteria on one file: SUB-172 (application list and schedule); dev SUB-140/144/145 also match
    assert codes_of("SUB-172") == ["multiple_locations"], codes_of("SUB-172")
    for sub in ("SUB-140", "SUB-145"):
        assert "multiple_locations" in codes_of(sub), sub
    assert set(codes_of("SUB-144")) >= {"scanned_application", "multiple_locations"}, codes_of("SUB-144")  # a file that matches two criteria lists both
    # criterion 3: a Spanish application (SUB-163) and a Spanish email-only file (SUB-169)
    assert "non_english" in codes_of("SUB-163") and "non_english" in codes_of("SUB-169")
    # in scope: a scanned carrier loss run beside a typed application (SUB-159 kind)
    assert detect(sources.read_folder(inbox / "SUB-159"))["in_scope"], codes_of("SUB-159")
    # in scope: Spanish email and Spanish business name beside an English application, a one-row schedule, a mailing and a prior address
    spanish_email = "Hola, les escribo por la tienda. Quiero una cotizacion para el seguro de mi negocio. Gracias, el productor."
    names = APP.replace("Example Roofing LLC", "Cenaduria Los Abuelos de la Frontera LLC")
    mail = APP + "Mailing address: PO Box 5, 22 Oak Ave, Dallas, TX\nPrior address: 7 Elm St, Waco, TX\nLocation 1: 100 Main St\nSame as location 1\n"
    one_row = "source\tloc\taddress\tcity\nX\t1\t100 Main St\tAustin"
    for label, files in (
        ("spanish email", [doc("application.md", APP), doc("email.md", spanish_email)]),
        ("spanish business name", [doc("application.md", names), doc("email.md", EMAIL)]),
        ("one-row schedule", [doc("application.md", APP), doc("schedule.csv", one_row)]),
        ("mailing and prior address", [doc("application.md", mail), doc("email.md", EMAIL)]),
        ("same address on many rows", [doc("application.md", APP), doc("schedule.csv", one_row + "\nX\t1\t100 Main St\tAustin")]),
        ("scanned loss run", [doc("application.md", APP), doc("loss-runs.jpg", "Valued 2026-09-01", ocr_words=[["Valued", 0.9]])]),
        ("typed pdf application", [doc("application.pdf", APP, ocr="tesseract")]),
    ):
        assert detect(files)["in_scope"], (label, detect(files))
    # each criterion on its own, and several at once with every reason listed
    assert [r["code"] for r in detect([doc("application.md", APP), doc("schedule.csv", SCHED2)])["reasons"]] == ["multiple_locations"]
    assert [r["code"] for r in detect([doc("application.md", APP + "Premises: 1 Main St (loc 1); 2 Oak Rd (loc 2)\n")])["reasons"]] == ["multiple_locations"]
    assert [r["code"] for r in detect([doc("application.pdf", APP, ocr_words=[["Named", 0.9]], ocr_confidence=0.9)])["reasons"]] == ["scanned_application"], "a scanned page in a PDF counts"
    spanish_app = "Solicitud de seguro\nAsegurado: Example LLC\nFecha efectiva: 2027-01-01\nOperaciones: tienda de ropa con los empleados en el local, sin cocina, para la venta.\nConstruccion: ladrillo\n"
    allin = detect([doc("application.jpg", spanish_app), doc("schedule.csv", SCHED2)])
    assert [r["code"] for r in allin["reasons"]] == ["scanned_application", "multiple_locations", "non_english"], allin
    assert [r["text"] for r in allin["reasons"]][2] == "Manual intake: non-English documents (Spanish)"
    # fail closed: an unsure language count, an unknown text layer, an error, no documents, an unreadable unnamed scan
    assert [r["code"] for r in detect([doc("application.md", "Named insured: X LLC")])["reasons"]] == ["language_unsure"], "too few words to tell"
    assert [r["code"] for r in detect([doc("application.md", APP + "Hola, la casa y el local sin cocina, los empleados de la tienda.\n")])["reasons"]] == ["language_unsure"], "near-even counts"
    assert "text_layer_unknown" in [r["code"] for r in detect([doc("application.pdf", "", needs_human=True, unread="could not be opened")])["reasons"]]
    assert "unidentified_scan" in [r["code"] for r in detect([doc("application.md", APP), doc("scan.jpg", "", needs_human=True)])["reasons"]]
    broken = detect([{"name": "application.md"}])  # no "text" key is fine; a non-dict is an error
    assert broken["in_scope"] is False
    err = detect(None)  # type: ignore[arg-type]
    assert not err["in_scope"] and [r["code"] for r in err["reasons"]] == ["detector_error"] and "detector error" in err["reasons"][0]["text"]
    assert not detect([])["in_scope"] and detect([])["reasons"][0]["code"] == "not_identified"
    assert reasons_text(allin) == [r["text"] for r in allin["reasons"]] and reasons_text(ok) == [] and reasons_text(None) == []
    with tempfile.TemporaryDirectory() as tmp:  # an xlsx schedule with two address rows
        import openpyxl

        book = openpyxl.Workbook()
        sheet = book.active
        assert sheet is not None
        sheet.append(["loc", "address", "city"])
        sheet.append([1, "100 Main St", "Austin"])
        sheet.append([2, "200 Oak Ave", "Austin"])
        book.save(Path(tmp) / "schedule.xlsx")
        (Path(tmp) / "application.md").write_text(APP)
        assert [r["code"] for r in detect(sources.read_folder(Path(tmp)))["reasons"]] == ["multiple_locations"]
    # label:value application in English with few other words: not unsure (labels count as English)
    terse = "Named insured: Gulf Tacos LLC\nPremises address: 1 A St, Austin TX\nEffective date: 2027-01-01\nYears in business: 4\nConstruction: masonry\nOperations: office\nNumber of employees: 3\n"
    assert detect([doc("application.md", terse)])["in_scope"], detect([doc("application.md", terse)])
    # fairness: the same file under a Spanish name, with the name repeated in Operations, gets the same scope
    base = APP.replace("Operations: General", "Operations: Example Roofing LLC General")
    spanish_name = base.replace("Example Roofing LLC", "La Cocina de los Abuelos y las Tias SRL")
    assert detect([doc("application.md", base)]) ["reasons"] == detect([doc("application.md", spanish_name)])["reasons"] == [], (detect([doc("application.md", spanish_name)]))
    # one place written two ways is one location; two buildings at one street address are two rows (SUB-145)
    same = "loc\taddress\n1\t100 Main St\n2\t100 Main Street, Ste 2\n3\t100 MAIN ST."
    assert detect([doc("application.md", APP), doc("schedule.csv", same)])["in_scope"]
    bldgs = "loc\taddress\n1\t100 Main St\n2\t100 Main St Bldg B"
    assert [r["code"] for r in detect([doc("application.md", APP), doc("schedule.csv", bldgs)])["reasons"]] == ["multiple_locations"]
    # a csv or xlsx that is also the application (by name or labels) is still counted for address rows (@model-risk H1)
    sheet_app = "Named insured\tX LLC\nPremises address\t1 A St\nEffective date\t2027-01-01\nOperations\toffice work for the business\n"
    for name in ("application.csv", "acord.xlsx", "data.csv"):
        one = detect([doc(name, sheet_app + "Mailing address\t9 Oak Ave")])
        assert "not_identified" not in [r["code"] for r in one["reasons"]] and one["in_scope"], (name, one)  # mailing address is not a location
        got = detect([doc(name, sheet_app + "100 Main St\n200 Oak Ave")])
        assert [r["code"] for r in got["reasons"]] == ["multiple_locations"], (name, got)
    # H1: SUB-172 with its "(loc n)" lines removed and SOV-style headers (a schedule that holds application labels) is still multiple locations
    app172 = (inbox / "SUB-172" / "application.md").read_text()
    app172 = re.sub(r"\s*\(loc \d\)", "", app172).replace("; ", " and ")
    sched172 = (inbox / "SUB-172" / "schedule.csv").read_text().replace("year_built", "Year Built").replace("cooking", "Operations").replace("construction", "Construction").replace(",address,", ",Premises Address,")
    sched_txt = "\n".join("\t".join(r.split(",")) for r in sched172.splitlines())
    assert [r["code"] for r in detect([doc("application.md", app172), doc("schedule.csv", sched_txt)])["reasons"]] == ["multiple_locations"], "SUB-172 schedule-only variant"
    assert [r["code"] for r in detect([doc("application.md", app172), doc("sov.xlsx", sched_txt)])["reasons"]] == ["multiple_locations"]
    # every application location-list form, each on its own; the single-location forms stay in scope
    for label, extra in (
        ("Location #2", "Location #1: 1 Main St, Austin\nLocation #2: 2 Oak Rd, Waco\n"),
        ("Location n -", "Location 1 - 1 Main St\nLocation 2 - 2 Oak Rd\n"),
        ("numbered list", "Locations:\n1. 1 Main St, Austin\n2. 2 Oak Rd, Waco\n"),
        ("bulleted list", "Premises:\n- 1 Main St, Austin\n- 2 Oak Rd, Waco\n"),
        ("second location", "Second location: 2 Oak Rd, Waco\n"),
        ("two premises lines", "Premises address: 3 Elm St, Waco, TX\n"),
        ("semicolon list", "Premises: 1 Main St, Austin; 2 Oak Rd, Waco\n"),
    ):
        assert detect([doc("application.md", APP + extra)])["reasons"] and "multiple_locations" in [r["code"] for r in detect([doc("application.md", APP + extra)])["reasons"]], label
    for label, extra in (
        ("one location line", "Location 1: 100 Main St\n"),
        ("mailing and prior", "Mailing address: 5 PO Box, Dallas, TX\nPrior address: 7 Elm St, Waco, TX\nSame as location 1\n"),
        ("one-item list", "Locations:\n1. 100 Main St, Austin\n"),
        ("premises with unit", "Premises address: 100 Main Street, Ste 2, Austin, TX 78701\n"),
    ):
        assert detect([doc("application.md", APP + extra)])["in_scope"], (label, detect([doc("application.md", APP + extra)]))
    # H2: a readable scanned page with a neutral name beside a typed application is a scanned page of the application
    scan_text = "Sprinklers: no\nLoss history: none"
    for name, extra in (("IMG_0412.jpg", {}), ("page2.pdf", {"ocr_words": [["Sprinklers", 0.9]], "ocr_confidence": 0.9})):
        got = detect([doc("application.md", APP), doc(name, scan_text, **extra)])
        assert [r["code"] for r in got["reasons"]] == ["scanned_application"], (name, got)
    assert detect([doc("application.md", APP), doc("page2.pdf", scan_text)])["in_scope"], "a typed pdf is typed"
    assert detect([doc("application.md", APP), doc("reply.md", scan_text)])["in_scope"] and detect([doc("application.md", APP), doc("loss-runs.jpg", scan_text, ocr_words=[["a", 1]])])["in_scope"]
    print("scope ok", VERSION)
