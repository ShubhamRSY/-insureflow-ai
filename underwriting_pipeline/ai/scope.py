"""P-055 (D-105): the pilot scope detector. A file it puts out of scope goes to manual intake as a whole file.

Deterministic rules only. No model call, no OCR of its own: it reads the documents sources.read_folder() already returned.
Any change to a rule below is a change under D-017 (`approve change P-###`) and must be revalidated.
Fail closed: an error, an unsure language count, an unknown text layer, or no identifiable application is manual intake.
"""

import re

import llm_extract

VERSION = "scope-v5"  # model-inventory.md; bump with every rule change. v5: P-077 part A (D-145, D-146)
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
    "location_count_unclear": "Manual intake: number of locations not clear",  # P-077 part B: set after the model call, never by detect()
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
# P-058 (D-108): a numbered location, building or premises used as a LABEL: at the start of a line, a list item or a schedule cell
# ("Location No. 2", "Location #2", "Loc #2", "Loc. 2", "Building 2:", "Bldg 2", "Bldg. #2", "Premises 2", "Location: 2", "Locations 1 and 2",
# "Bldgs 1-2", "Building 1 of 2"). Never mid-line, so "500 Oak Park Dr, Building 2, Austin" (one premises address) is not a second location.
# "Premises 12 Main St" (the number starts a street address), "Building 2 stories" and "Number of buildings: 2" are not labels;
# "Suite 2", "Floor 2", "Unit 2" and "2 buildings" are not in the word list.
_LABEL = (r"(?:locations?|loc|buildings?|bldgs?|premises)\b\.?\s*(?:(?:no|nos|num|number)\b\.?)?\s*:?\s*#?\s*"
          r"(\d{1,2}(?!\d)(?:\s*(?:,|and|&|-|–|to|of)\s*(?:(?:locations?|loc|buildings?|bldgs?)\b\.?\s*(?:no\b\.?)?\s*#?\s*)?\d{1,2}(?!\d))*)(?!\s*[-\u2013]?\s*(?:stor|floor|level|unit|year|ft|feet|sq))")
NUMBERED = re.compile(r"(?i)^\s*(?:(?:[-*\u2022]|\d{1,2}[.)])\s+)?" + _LABEL)
# P-063 (B-432): the same label anywhere in an application line, e.g. inside a premises value ("Loc 1: …; Loc #2: …", SUB-233).
# "Number of buildings: 2" and "2 of 3 buildings" style counts are not labels.
NUMBERED_ANY = re.compile(r"(?i)(?<!\bof\s)\b" + _LABEL)
NOT_A_LOCATION = re.compile(r"(?i)\b(?:mail(?:ing)?\s+(?:address|to)|(?:prior|former|previous)\s+(?:address|location|premises))\b")  # the label, not a substring: "email" and "former bank" are not it
# P-077 part A (D-145): a second place stated in words, read in every document (application, email, attachments, letters, loss runs).
# A1: a count, ordinal or quantifier next to a place noun ("two stores", "both locations", "another store"). Parts of one building
# ("two floors", "2nd floor", "two entrances", "Suite 200") and counts of other things ("two fryers", "second shift") have no place noun.
# D-146: a sold or closed place counts too ("sold our second store", "closed on our second store"); a person reads the file.
_QTY = r"(?:two|three|four|five|six|seven|eight|nine|ten|[2-9]|10|both|multiple|several|second|2nd|third|3rd|other|another|additional|each\s+of\s+our)"
PART_LABEL = re.compile(r"(?i)(?:suite|ste|unit|apt|apartment|bldg|building|space|room|rm|floor|fl|level|no|number|#)\.?\s*#?\s*$")  # "Ste. 2 shop", "Bldg 2 store"
_PLACE = r"(?:stores?|shops?|locations?|sites?|branch(?:es)?|outlets?|premises|restaurants?|storefronts?)"
_NOT_BETWEEN = (r"(?:floors?|levels?|stor(?:y|ies|eys?)|suites?|units?|entrances?|shifts?|of|the|a|an|in|at|on|for|to|and|or"
                r"|hand|job|jobs|work|construction|client|clients|customer|customers|electrical|power)")  # "second hand store", "several job sites"
COUNT_PHRASE = re.compile(rf"(?i)\b{_QTY}(?:\s+of\s+(?:our|the|their|its))?\s+(?:(?!{_NOT_BETWEEN}\b)[a-z'-]+\s+)?{_PLACE}\b")
# A2: one line gives two figures, each labelled with a different place name: "Square footage: 3,000 (Corpus), 1,800 (Rockport)".
PLACE_VALUE = re.compile(r"\d[\d,.]*\s*(?:sq\.?\s*ft\.?|sf|square feet)?\s*\(\s*([A-Z][A-Za-z.' -]{1,30}?)\s*\)")
NOT_PLACE_NAME = frozenset("approx approximately est estimated actual annual gross net total building buildings contents bpp tiv owned leased rented "
                           "sales payroll new old current prior projected monthly yearly usd retail warehouse office storage kitchen dining patio "
                           "mezzanine basement floor first second ground main interior exterior heated unheated each general per aggregate occurrence "
                           "products completed personal medical online owner owners staff employee employees officer officers clerical full part "
                           "seasonal deductible limit limits premium property liability auto umbrella".split())
# A3: a street address on a line that names a role other than the premises is not a second place.
ROLE_LINE = re.compile(r"(?i)\b(?:mail(?:ing)?|billing|prior|former|previous|home|residence|residential|owner'?s|agency|agent|producer|broker(?:age)?"
                       r"|carrier|insurer|insurance\s+(?:company|co)|underwriter|supplier|vendor|landlord)\b")
STREET_WORDS = re.compile(r"\b\d{1,6}\s+(?:[NSEW]\.?\s+)?(?:[A-Z0-9][A-Za-z0-9.'-]*\s+){1,4}"
                          r"(?:St|Street|Rd|Road|Ave|Avenue|Blvd|Dr|Drive|Ln|Lane|Hwy|Highway|Way|Pkwy|Parkway|Ct|Court|Pl|Place|Fwy|Trl|Loop|Cir)\b\.?")
STREET = re.compile(r"\b\d{1,6}\s+[A-Za-z0-9 .]+?\s(?:st|street|rd|road|ave|avenue|blvd|dr|drive|ln|lane|hwy|way|pkwy|ct|court|pl|place|fwy|trl)\b\.?", re.I)


LOSS_TERMS = (r"date of loss", r"claim\s*(?:no|number|#|id)", r"incurred", r"valuation date|valued (?:as of|through|at)", r"paid (?:loss|indemnity)|reserve", r"loss run")


def _is_loss_sheet(doc: dict) -> bool:
    """A csv or xlsx that is a loss run by name or by content (two or more loss-run column terms, and not an application). Only the P-058 numbered-label check skips it; address rows are counted for every sheet exactly as in scope-v2."""
    name = doc["name"].lower()
    if not name.endswith((".csv", ".xlsx")):
        return False
    text = (doc.get("text") or "").lower()
    return bool(LOSS_RUN.search(name)) or (sum(bool(re.search(t, text)) for t in LOSS_TERMS) >= 2 and _label_count(doc) < 3)


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
            heads = [i for i, c in enumerate(cells) if "address" in c.lower() and not re.search(r"mail|prior|previous|former", c, re.I)]  # scope-v2 header test kept (check-P-057-P-058 H2)
            col = heads[0] if heads else None
        elif col is not None and col < len(cells) and cells[col].strip():
            raw.append(cells[col])
        elif col is None and not NOT_A_LOCATION.search(line):
            raw += [m.group(0) for m in STREET.finditer(line)]
    for address in raw:
        address = UNIT.sub("", address.strip())
        if address and not any(llm_extract.same_address(address, other) for other in found):
            found.append(address)
    return found


def _numbered(text: str, cells: bool = False, anywhere: bool = False) -> bool:
    """P-058: two or more premises named by number as a label: a number of 2 or more, or two distinct numbers ("Building 1" twice is one place;
    "Locations 1 and 2", "Bldgs 1-2" and "Building 1 of 2" name two). cells=True reads a schedule one tab-separated cell at a time.
    A line about a mailing or prior address is skipped; a number that starts a street address ("Premises 12 Main St") is not a label.
    anywhere=True (P-063, application text) reads every label in a line, not only one at its start."""
    found: set[int] = set()
    for line in text.splitlines():
        if NOT_A_LOCATION.search(line):
            continue
        pieces = line.split("\t") if cells else [line]
        for piece, m in ((p, m) for p in pieces for m in (NUMBERED_ANY.finditer(p) if anywhere else [NUMBERED.match(p)]) if m):
            street = STREET.match(piece[m.start(1):])
            if street and not re.search(r"\d", street.group(0)[len(m.group(1)):]) and not re.match(r"\d+\s+(?:on|at|in|is|near|behind|by)\b", street.group(0), re.I):
                continue  # "12 Main St" is an address; "2 Warehouse 50 Elm St" and "2 on Bell St" (P-063) are labels
            found |= {int(n) for n in re.findall(r"\d+", m.group(1))}
    return len(found) >= 2 or any(n >= 2 for n in found)


def _multi_in_application(app: dict) -> bool:
    """Two or more premises named in the application: "(loc 2)", "Location 2:" and its forms, a numbered or bulleted list under a
    Locations heading, "Second location:", or two distinct premises addresses. A mailing or prior address is not a location."""
    text = app.get("text") or ""
    numbers = {n for rx in LOC_LABELS for n in rx.findall(text)}
    if len(numbers) >= 2 or any(int(n) >= 2 for n in numbers) or LOC_ORDINAL.search(text) or _numbered(text, anywhere=True):
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


def _place_words(docs: list[dict]) -> tuple[str, str] | None:
    """P-077 part A: (quoted words, file name) for the first second-place signal in any document, or None. A1, then A2, then A3."""
    for d in docs:
        text = d.get("text") or ""
        for m in COUNT_PHRASE.finditer(text):
            if m.group(0)[0].isdigit() and PART_LABEL.search(text[max(0, m.start() - 12) : m.start()]):
                continue  # "Suite 2 shop", "Bldg 2 store": a part of one place
            return m.group(0), d["name"]
    for d in docs:
        for line in (d.get("text") or "").splitlines():
            names = {n.lower() for n in PLACE_VALUE.findall(line) if n.split()[0].lower().rstrip(".") not in NOT_PLACE_NAME}
            if len(names) >= 2:
                return line.strip()[:120], d["name"]
    places: list[str] = []
    for d in docs:
        prev = ""
        for line in (d.get("text") or "").splitlines():
            label_above = len(prev.strip()) <= 60 and (ROLE_LINE.search(prev) or NOT_A_LOCATION.search(prev))  # a short "Mailing address:" or "ABC Insurance Agency" line above
            prev = line if line.strip() else prev
            if ROLE_LINE.search(line) or NOT_A_LOCATION.search(line) or label_above:
                continue
            for m in (m for cell in line.split("\t") for m in STREET_WORDS.finditer(cell)):  # one schedule cell at a time: "1<tab>12 Main St" is not an address
                address = UNIT.sub("", m.group(0).strip())
                if not any(llm_extract.same_address(address, o) for o in places):
                    places.append(address)
                    if len(places) >= 2:
                        return m.group(0).strip(), d["name"]
    return None


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
    evidence: dict[str, str] = {}
    try:
        codes = _codes(docs)
        words = _place_words(docs)  # P-077 part A: stricter only, it can only add a reason
        if words and "multiple_locations" not in codes:  # the quote is shown only when these words alone sent the file
            evidence["multiple_locations"] = f' — "{words[0]}" ({words[1]})'
            codes.append("multiple_locations")
    except Exception:  # fail closed: whatever went wrong, a person reads this file
        codes = ["detector_error"]
    return {"version": VERSION, "in_scope": not codes, "reasons": [{"code": c, "text": REASONS[c] + evidence.get(c, "")} for c in codes]}


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
    numbered = any(_numbered(d.get("text") or "", cells=True) for d in docs if _is_sheet(d) and not _is_loss_sheet(d))  # P-058: "Location 2", "Bldg 2" in a schedule
    if len(places) >= 2 or numbered or any(_multi_in_application(d) for d in apps):
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
    # P-058: numbered locations, buildings and premises as labels; dev-style probes (application lines, then a schedule's cells)
    def multi(extra, name="application.md"):
        base = APP.replace("Premises address: 100 Main St, Austin, TX 78701\n", "") if extra.startswith("Premises") else APP  # one premises line only
        return "multiple_locations" in [r["code"] for r in detect([doc(name, base + extra + "\n")])["reasons"]]

    for form in ("Location No. 2: 200 Oak Ave", "Location #2", "Loc #2 is the warehouse", "Loc. 2", "Building 2", "Bldg 2", "Bldg. #2", "Premises 2", "Premises No. 2",
                 "Building 2: warehouse", "Location No. 2 - yard", "- Bldg 3 (storage)", "2) Building 2", "Locations 1 and 2", "Buildings 1 and 2", "Bldgs 1-2", "Building 1 of 2",
                 "Location 2 Warehouse 50 Elm St", "Location: 2", "Location 1 and Location 2", "location no 2 - yard", "Location 2: former bank, 50 Elm St", "Loc 2 (email for details)"):
        assert multi(form), form
    for form in ("Suite 2", "Floor 2", "Unit 2", "Apt 2", "Number of buildings: 2", "2 buildings", "Building 2 stories", "Building 2-story masonry", "Premises 12 Main St",
                 "Location 1", "Building 1", "Loc #1 and Loc #1", "Building 1 of 1", "Mailing address: Building 2, PO Box 5", "Prior location 2: 7 Elm St, Waco, TX", "Same as Location 1",
                 "Locations: 1", "Premises address: 100 Main Street, Ste 2, Austin, TX", "Building 2020", "Former address: Location 2, 5 Elm", "Mail to: Loc 2, PO Box 4",
                 "Previous location 2: 9 Elm", "Operations: we lease 1 of 2 buildings", "Premises address: Loc 1: 100 Main St, Austin, TX"):
        assert not multi(form), form
    # P-063 (B-432): a label anywhere in a field or body line counts, not only at line start. SUB-233 wrote both inside the premises value.
    # Fail closed: "Building 2" inside one premises address (P-058 kept it in scope) is now manual intake; a person reads it.
    for form in ("Premises address: Loc 1: 3412 S Georgia St, Amarillo, TX 79109; Loc #2: 6901 Bell St, Amarillo, TX 79106", "Premises: Location 1 at 1 A St and Location 2 at 9 B Rd",
                 "Operations: retail; we also run Location 2 on Bell St", "Premises address: 500 Oak Park Dr, Building 2, Austin, TX", "Premises: 500 Oak Park Dr, Bldg 2, Austin",
                 "The shop is in Building 2 of the plaza", "Description: storage in Bldg #3 behind the shop"):
        assert multi(form), form
    assert codes_of("SUB-233") == ["multiple_locations"], codes_of("SUB-233")
    sched_cells = "loc\tname\nLocation No. 2\tWarehouse\nLocation 1\tShop"
    assert [r["code"] for r in detect([doc("application.md", APP), doc("schedule.csv", sched_cells)])["reasons"]] == ["multiple_locations"], "numbered cells in a schedule"
    assert [r["code"] for r in detect([doc("application.md", APP), doc("schedule.csv", "loc\tname\nBldg 1\tShop\nBldg 2\tYard")])["reasons"]] == ["multiple_locations"]
    assert detect([doc("application.md", APP), doc("schedule.csv", "loc\tname\nBuilding 1\tShop\nBuilding 1\tShop again")])["in_scope"], "one number twice is one place"
    assert detect([doc("application.md", APP), doc("schedule.csv", "loc\taddress\n1\t100 Main St\n1\t100 Main Street")])["in_scope"], "a bare loc column is not a numbered entry"
    assert detect([doc("application.md", APP), doc("email.md", EMAIL + "\nBuilding 2 is the one we want covered.")])["in_scope"], "an email is not read for locations"
    # loss-run sheets (name or content) skip only the numbered-label check; address rows are counted as in scope-v2 for every sheet
    lr = "Date of loss\tClaim number\tTotal incurred\nBldg 1\t100\t5\nBldg 2\t200\t6"
    for name in ("loss-runs.xlsx", "carrier-a.csv", "currently_valued.csv"):
        assert detect([doc("application.md", APP), doc(name, lr)])["in_scope"], name  # numbered claim rows are not locations
    sov = "address\tReserve\tIncurred\tClaim number\tValued as of\n100 Main St\t1\t2\tC1\t2026-01-01\n200 Oak Ave\t1\t2\tC2\t2026-01-01"
    lr_addr = "Date of loss\tClaim number\tTotal incurred\nLocation 1\t12 Oak St\t100\nLocation 2\t99 Elm Ave\t200"
    for name in ("sov.csv", "schedule.xlsx", "locations.csv", "carrier-a.csv", "loss-runs.xlsx"):
        assert [r["code"] for r in detect([doc("application.md", APP), doc(name, sov)])["reasons"]] == ["multiple_locations"], name  # as scope-v2
        assert [r["code"] for r in detect([doc("application.md", APP), doc(name, lr_addr)])["reasons"]] == ["multiple_locations"], name  # as scope-v2: two addresses
    assert not detect([doc("application.md", APP), doc("schedule.csv", "Location 1\t12 Oak St\nLocation 2\t99 Elm Ave")])["in_scope"], "a real schedule still counts"
    for head in ("Address (mailing)", "Prior-address", "Address - previous"):  # check-P-057-P-058 H2: the premises column is still found
        sheet = f"Loc,{head},Premises address\n1,PO Box 9 Waco TX 76701,100 Main St Waco TX 76701\n2,PO Box 9 Waco TX 76701,200 Elm St Waco TX 76702\n"
        got = [r["code"] for r in detect([{"name": "schedule.csv", "text": sheet}])["reasons"]]
        assert "multiple_locations" in got, (head, got)
    # P-077 part A (D-145, D-146): a second place in words, in any document; the card quotes the words and the file
    def words(text, name="email.md"):
        got = detect([doc("application.md", APP), doc(name, EMAIL + "\n" + text)])
        return [r["text"] for r in got["reasons"]]

    for phrase in ("We run two stores.", "Cover both locations.", "Our second shop opens in May.", "The other branch is in Waco.", "our 2 sites",
                   "another store in Rockport", "each of our locations", "both of our stores", "three retail outlets",
                   "Square footage: 3,000 (Corpus), 1,800 (Rockport)", "Please also cover 9 Oak Ave, Waco, TX 76701.",
                   "We sold our second store in 2019.", "We closed on our second store last year.", "We closed the other shop.",  # D-146: fail closed
                   "No other locations."):  # a negation is not read; a person reads it (fail closed)
        got = words(phrase)
        assert got and got[0].startswith("Manual intake: multiple locations — \"") and got[0].endswith("(email.md)"), (phrase, got)
    assert 'multiple locations — "two stores" (application.md)' in detect([doc("application.md", APP + "We run two stores in Corpus.\n")])["reasons"][0]["text"]
    assert words("We run two stores.", "loss-runs.md") and words("We run two stores.", "reply.md"), "every document is read"
    for phrase in ("The shop has two floors.", "The office is on the 2nd floor.", "Second floor storage.", "The store has two entrances.",
                   "two buildings at one address", "Suite 200", "Unit 2 storefront", "Ste 2 shop", "We have two fryers.", "A second shift runs at night.",
                   "Both owners work in the store.", "two employees", "Mailing address: 9 Oak Ave, Waco, TX", "Billing address: 9 Oak Ave, Waco, TX",
                   "Prior address: 9 Oak Ave, Waco, TX", "Owner's home: 9 Oak Ave, Waco, TX", "ABC Insurance Agency, 55 Elm St, Austin TX",
                   "Producer: Jane Roe, 55 Elm St, Austin", "Landlord: Oak Holdings, 9 Oak Ave, Waco", "Square footage: 3,000 (Building), 500 (Contents)",
                   "Sales: 500,000 (2025), 450,000 (2024)", "The premises at 100 Main St, Austin, TX 78701 is our only store.", "Building 2 is the one we want covered.",
                   # code review 2026-11-02: one-place wordings that must not fire
                   "We are a second hand store.", "The roofer works 2-3 job sites a day.", "several job sites", "Ste. 2 shop", "Bldg 2 store", "Space 3 storefront",
                   "Suite  2 shop", "Limits: 1,000,000 (Each Occurrence), 2,000,000 (General Aggregate)", "Sales: 500,000 (Retail), 200,000 (Online)",
                   "Payroll: 80,000 (Owner), 40,000 (Staff)", "ABC Insurance Agency\n55 Elm St, Austin TX", "Mailing address:\n9 Oak Ave, Waco, TX",
                   "We run 2 delivery drivers all the way to Waco.", "Dr. Smith signed it."):
        assert not words(phrase), (phrase, words(phrase))
    numbered_too = detect([doc("application.md", APP), doc("schedule.csv", "loc\tname\nLocation 2\tYard"), doc("email.md", EMAIL + "\nanother store")])
    assert [r["text"] for r in numbered_too["reasons"]] == ["Manual intake: multiple locations"], "no quote when other rules sent the file"
    print("scope ok", VERSION)
