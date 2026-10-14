"""Read submission files into text. PDFs, Excel, images, and plain text.

Unreadable scans are returned empty and marked needs_human. Nothing is guessed from them.

# ponytail: one text blob per file. A layout model can replace this when citations need boxes.
"""

import csv
import hashlib
import re
from io import StringIO
from pathlib import Path

IMAGE = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
# Part of the extraction cache key. Change this line whenever the OCR steps below change.
OCR_SETTINGS = "tesseract psm6; osd turn; deskew +-12; rule lift; x2 lanczos; pdf 200dpi"


def _fill(image):
    rgb = image.convert("RGB")
    return rgb.getpixel((0, 0))


def _osd_turn(image):
    """Clockwise correction from Tesseract OSD. Low confidence is ignored."""
    import pytesseract

    try:
        osd = pytesseract.image_to_osd(image)
    except Exception:
        return None
    rotate = re.search(r"Rotate:\s*(\d+)", osd)
    conf = re.search(r"Orientation confidence:\s*([0-9.]+)", osd)
    if not rotate or not conf:
        return None
    degrees = int(rotate.group(1))
    if degrees == 0 or float(conf.group(1)) < 1:
        return None
    # PIL rotates counter-clockwise. OSD's Rotate is clockwise.
    return image.rotate(-degrees, expand=True, fillcolor=_fill(image))


def _deskew(image):
    """Small tilt. Pick the angle whose text rows are the most solid."""
    gray = image.convert("L")
    small = gray.resize((max(1, gray.width // 4), max(1, gray.height // 4)))
    best_angle, best_score = 0, -1
    for angle in range(-12, 13):
        rotated = small.rotate(angle, fillcolor=255)
        pixels = rotated.load()
        width, height = rotated.size
        score = 0
        for y in range(0, height, 2):
            dark = 0
            for x in range(0, width, 3):
                if pixels[x, y] < 140:
                    dark += 1
            score += dark * dark
        if score > best_score:
            best_score, best_angle = score, angle
    if best_angle == 0:
        return image
    return image.rotate(best_angle, expand=True, fillcolor=_fill(image))


def _prepare_image(image):
    """Lift light horizontal scanner rules, then enlarge.

    # ponytail: rules are rows that are mostly gray.
    """
    from PIL import Image

    gray = image.convert("L")
    pixels = gray.load()
    width, height = gray.size
    for y in range(1, height - 1):
        samples = 0
        line = 0
        for x in range(0, width, 2):
            samples += 1
            here = pixels[x, y]
            if 140 < here < 245 and here + 25 < pixels[x, y - 1] and here + 25 < pixels[x, y + 1]:
                line += 1
        if line <= samples * 0.45:
            continue
        for x in range(width):
            here = pixels[x, y]
            if 140 < here < 245 and here + 25 < pixels[x, y - 1] and here + 25 < pixels[x, y + 1]:
                pixels[x, y] = min(pixels[x, y - 1], pixels[x, y + 1])
    return gray.resize((width * 2, height * 2), Image.Resampling.LANCZOS)


def _ocr_score(image) -> tuple[str, float, int, list]:
    import pytesseract

    prepared = _prepare_image(_deskew(image))
    data = pytesseract.image_to_data(prepared, config="--psm 6", output_type=pytesseract.Output.DICT)
    words = []
    confs = []
    scored = []  # P-016 (b): every word with its own score (0-1), no letters-only filter and no four-letter minimum
    for conf, raw in zip(data["conf"], data["text"]):
        if (raw or "").strip():
            try:
                scored.append([raw.strip(), max(0.0, float(conf)) / 100])
            except (TypeError, ValueError):
                pass
        word = re.sub(r"[^A-Za-z]", "", raw or "")
        if len(word) < 4:
            continue
        words.append(word)
        try:
            confs.append(float(conf))
        except (TypeError, ValueError):
            continue
    text = pytesseract.image_to_string(prepared, config="--psm 6")
    mean = sum(confs) / len(confs) if confs else 0
    return text, mean, len(words), scored


def _read_scan(image) -> tuple[str, bool, float, list]:
    """Return text, whether a person must read the page, Tesseract's mean word score (0–100), and every word with its score (0–1)."""
    candidates = [image]
    turned = _osd_turn(image)
    if turned is not None:
        candidates.append(turned)
    best_text, best_mean, best_words, best_scored = "", 0.0, 0, []
    for candidate in candidates:
        text, mean, words, scored = _ocr_score(candidate)
        if mean > best_mean:
            best_text, best_mean, best_words, best_scored = text, mean, words, scored
    if best_words < 4 or best_mean < 40:
        return "", True, best_mean, []
    return best_text, False, best_mean, best_scored


def _ocr_image(path: Path) -> tuple[str, bool, float, list]:
    from PIL import Image

    return _read_scan(Image.open(path))


def _covered(page) -> bool:
    """P-016 (c3). A page whose images cover more than half of it is read as a scan, whatever typed text it has."""
    area = float(page.width * page.height) or 1.0
    return sum(max(0.0, min(i["x1"], page.width) - max(i["x0"], 0)) * max(0.0, min(i["bottom"], page.height) - max(i["top"], 0)) for i in page.images) / area > 0.5


def _pdf_text(path: Path) -> tuple[str, bool, float | None, list, list]:
    """P-016 (c). Each page is typed (40 or more typed characters, not mostly an image), read by OCR, or listed as not read.

    Returns text, needs_human (no text at all), the mean OCR score of the scanned pages (None if none), the pages not read
    as [{"page", "reason"}], and every OCR'd word with its score. Typed pages of a file with a scanned page add their words at score 1.
    """
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        pages = [((page.extract_text() or ""), _covered(page)) for page in pdf.pages]
    texts, means, unread, words = [], [], [], []
    for number, (typed, covered) in enumerate(pages, 1):
        if len(typed.strip()) >= 40 and not covered:
            texts.append(typed)
            words += [[w, 1.0] for w in typed.split()]
            continue
        try:
            from pdf2image import convert_from_path

            image = convert_from_path(str(path), dpi=200, first_page=number, last_page=number)[0]
        except Exception:
            texts.append(typed)
            unread.append({"page": number, "reason": "OCR for PDF pages is not available"})
            continue
        page_text, human, mean, scored = _read_scan(image)
        if human:
            texts.append("")
            unread.append({"page": number, "reason": f"scan not readable, OCR score {round(mean)}"})
        else:
            texts.append(page_text)
            means.append(mean)
            words += scored
    text = "\n".join(texts).strip()
    score = sum(means) / len(means) if means else None
    if score is None:  # no page was scanned: typed words need no list
        words = []
    return text, not text or (bool(unread) and len(text) < 40), score, unread, words


def _xlsx_text(path: Path) -> str:
    import openpyxl

    book = openpyxl.load_workbook(path, data_only=True, read_only=True)
    lines = []
    for sheet in book.worksheets:
        lines.append(f"sheet: {sheet.title}")
        for row in sheet.iter_rows(values_only=True):
            cells = ["" if cell is None else str(cell) for cell in row]
            if any(cells):
                lines.append("\t".join(cells))
    book.close()
    return "\n".join(lines)


def _csv_text(path: Path) -> str:
    raw = path.read_text()
    rows = list(csv.reader(StringIO(raw)))
    return "\n".join("\t".join(row) for row in rows)


def read_folder(folder: Path) -> list[dict]:
    docs = []
    for path in sorted(p for p in folder.iterdir() if p.is_file() and not p.name.startswith(".")):  # B-206 (P-022): same rule as folder_manifest
        suffix = path.suffix.lower()
        needs_human = False
        ocr_confidence = None
        unread, words, why = [], [], None
        try:
            if suffix in {".md", ".txt"}:
                text = path.read_text()
            elif suffix == ".csv":
                text = _csv_text(path)
            elif suffix == ".pdf":
                text, needs_human, ocr_confidence, unread, words = _pdf_text(path)
            elif suffix == ".xlsx":
                text = _xlsx_text(path)
            elif suffix in IMAGE:
                text, needs_human, ocr_confidence, words = _ocr_image(path)
                if needs_human:
                    unread = [{"page": None, "reason": f"scan not readable, OCR score {round(ocr_confidence)}"}]
            else:
                text, needs_human, why = "", True, f"file type {suffix or path.name} is not read"  # P-016 (c1)
        except Exception:  # P-016 E1: a damaged or locked file is listed; the other files are read
            text, needs_human, why, ocr_confidence, unread, words = "", True, "could not be opened", None, [], []
        try:
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            sha = None
        doc = {"name": path.name, "text": text, "needs_human": needs_human, "sha256": sha}
        if why:
            doc["unread"] = why  # the whole file is not read: it never reaches the model or the cache key
        if unread:
            doc["unread_pages"] = unread
        if words:
            doc["ocr_words"] = words
        if ocr_confidence is not None:
            doc["ocr_confidence"] = round(ocr_confidence / 100, 3)
        if suffix == ".pdf" or suffix in IMAGE:
            doc["ocr"] = OCR_SETTINGS
        docs.append(doc)
    return docs


if __name__ == "__main__":
    from PIL import Image, ImageDraw, ImageFont

    page = Image.new("RGB", (900, 240), "white")
    draw = ImageDraw.Draw(page)
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Courier New.ttf", 36)
    draw.text((40, 80), "Named insured: Masonry Office LLC", fill="black", font=font)
    turned = page.rotate(180, expand=True, fillcolor="white")
    text, human, mean, scored = _read_scan(turned)
    assert any(w == "Masonry" or w.startswith("Masonry") for w, _ in scored) and all(0 <= c <= 1 for _, c in scored), "every OCR word has its own score (P-016 b)"
    assert not human and "Masonry" in text and mean >= 40
    blank, human_blank, _blank_mean, _ = _read_scan(Image.new("RGB", (400, 200), "white"))
    assert human_blank and blank == ""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:  # B-206: a dotfile is neither read nor in the manifest
        (Path(tmp) / "a.md").write_text("x")
        (Path(tmp) / ".hidden.md").write_text("secret")
        assert [d["name"] for d in read_folder(Path(tmp))] == ["a.md"]
        from prepare import folder_manifest

        assert [m["name"] for m in folder_manifest(Path(tmp))] == ["a.md"]
    # P-016 (c). A page that is not read is listed with its number; an unsupported or unopenable file is listed; nothing stops the others.
    def pdf(path, *pages):  # a tiny PDF by hand: each page is its text, or None for a blank page
        objs = ["<< /Type /Catalog /Pages 2 0 R >>", f"<< /Type /Pages /Kids [{' '.join(f'{3 + 2 * i} 0 R' for i in range(len(pages)))}] /Count {len(pages)} >>"]
        for i, text in enumerate(pages):
            body = f"BT /F1 12 Tf 20 100 Td ({text}) Tj ET" if text else ""
            objs += [f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 200] /Contents {4 + 2 * i} 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>", f"<< /Length {len(body)} >>\nstream\n{body}\nendstream"]
        out, offsets = "%PDF-1.4\n", []
        for n, obj in enumerate(objs, 1):
            offsets.append(len(out))
            out += f"{n} 0 obj\n{obj}\nendobj\n"
        xref = len(out)
        out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n" + "".join(f"{o:010d} 00000 n \n" for o in offsets)
        path.write_text(out + f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n")

    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        typed = "Named insured: Example Roofing LLC, 100 Main St, Austin"
        pdf(folder / "two.pdf", typed, None)
        (folder / "note.docx").write_text("not read")
        (folder / "bad.txt").write_bytes(b"\xff\xfe\x00bad")
        (folder / "bad.pdf").write_text("not a pdf")
        (folder / "ok.md").write_text("Named insured: Example LLC")
        by = {d["name"]: d for d in read_folder(folder)}
        assert by["two.pdf"]["text"] == typed and not by["two.pdf"]["needs_human"], "page 1 is kept when page 2 cannot be read"
        assert by["two.pdf"]["unread_pages"] == [{"page": 2, "reason": "OCR for PDF pages is not available"}] or by["two.pdf"]["unread_pages"][0]["page"] == 2, "page 2 is listed with its number and a reason"
        assert by["note.docx"]["unread"] == "file type .docx is not read" and by["note.docx"]["needs_human"] and by["note.docx"]["text"] == ""
        assert by["bad.txt"]["unread"] == "could not be opened" and by["bad.pdf"]["unread"] == "could not be opened", "a file that cannot be opened is listed, not raised"
        assert by["ok.md"]["text"] == "Named insured: Example LLC" and "unread" not in by["ok.md"], "the other files are still read"
        assert "ocr_words" not in by["two.pdf"], "a PDF with no scanned page keeps no word list"
        from prepare import unread_rows

        rows = unread_rows(list(by.values()), ["big.md"])
        assert {(r["file"], r["page"]) for r in rows} == {("two.pdf", 2), ("note.docx", None), ("bad.txt", None), ("bad.pdf", None), ("big.md", None)}
        assert [r["reason"] for r in rows if r["file"] == "big.md"] == ["not sent: text past 120,000 characters"]
    print("sources ok")
