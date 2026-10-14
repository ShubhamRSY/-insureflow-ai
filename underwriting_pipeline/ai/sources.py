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


def _ocr_score(image) -> tuple[str, float, int]:
    import pytesseract

    prepared = _prepare_image(_deskew(image))
    data = pytesseract.image_to_data(prepared, config="--psm 6", output_type=pytesseract.Output.DICT)
    words = []
    confs = []
    for conf, raw in zip(data["conf"], data["text"]):
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
    return text, mean, len(words)


def _read_scan(image) -> tuple[str, bool, float]:
    """Return text, whether a person must read the page, and Tesseract's mean word score (0–100)."""
    candidates = [image]
    turned = _osd_turn(image)
    if turned is not None:
        candidates.append(turned)
    best_text, best_mean, best_words = "", 0.0, 0
    for candidate in candidates:
        text, mean, words = _ocr_score(candidate)
        if mean > best_mean:
            best_text, best_mean, best_words = text, mean, words
    if best_words < 4 or best_mean < 40:
        return "", True, best_mean
    return best_text, False, best_mean


def _ocr_image(path: Path) -> tuple[str, bool, float]:
    from PIL import Image

    return _read_scan(Image.open(path))


def _pdf_text(path: Path) -> tuple[str, bool, float | None]:
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        parts = [(page.extract_text() or "") for page in pdf.pages]
    text = "\n".join(parts).strip()
    if len(text) >= 40:
        return text, False, None
    try:
        from pdf2image import convert_from_path

        pages = convert_from_path(str(path), dpi=200)
        chunks = []
        means = []
        for page in pages:
            page_text, _needs_human, mean = _read_scan(page)
            chunks.append(page_text)
            means.append(mean)
        ocr = "\n".join(chunks).strip()
        score = sum(means) / len(means) if means else 0.0
        if ocr:
            return ocr, False, score
        return "", True, score
    except Exception:
        return text, len(text) < 40, None


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
        if suffix in {".md", ".txt"}:
            text = path.read_text()
        elif suffix == ".csv":
            text = _csv_text(path)
        elif suffix == ".pdf":
            text, needs_human, ocr_confidence = _pdf_text(path)
        elif suffix == ".xlsx":
            text = _xlsx_text(path)
        elif suffix in IMAGE:
            text, needs_human, ocr_confidence = _ocr_image(path)
        else:
            continue
        doc = {"name": path.name, "text": text, "needs_human": needs_human, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
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
    text, human, mean = _read_scan(turned)
    assert not human and "Masonry" in text and mean >= 40
    blank, human_blank, _blank_mean = _read_scan(Image.new("RGB", (400, 200), "white"))
    assert human_blank and blank == ""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:  # B-206: a dotfile is neither read nor in the manifest
        (Path(tmp) / "a.md").write_text("x")
        (Path(tmp) / ".hidden.md").write_text("secret")
        assert [d["name"] for d in read_folder(Path(tmp))] == ["a.md"]
        from prepare import folder_manifest

        assert [m["name"] for m in folder_manifest(Path(tmp))] == ["a.md"]
    print("sources ok")
