"""D-082 item 4: reader smoke test before any hold-out. One uncached run per file type; prints "read / not read" per file.

Each type gets its own fictional one-file folder, made in a temp directory. The cache and token log are a fresh temp folder
(D-069), so every folder is one real model call and nothing real is written. A missing reader stops the run (P-034).
Exit 1 if any file is not read or any call fails.

Run: .venv/bin/python underwriting_pipeline/ai/smoke_readers.py
"""

import os
import subprocess
import sys
import tempfile
from importlib import metadata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import llm_extract  # noqa: E402
import prepare  # noqa: E402

FACTS = ("SMOKE TEST - FICTIONAL. Named insured: Juniper Lane Supply LLC. Premises address: 410 Elm Fork Rd, Denton, TX 76201. "
         "Effective date: 2027-01-01. Operations: dry goods retail. Sales: 650000. Building TIV: 900000. Construction: masonry. Year built: 1999.")
ES = ("PRUEBA - FICTICIO. Asegurado: Juniper Lane Supply LLC. Dirección del local: 410 Elm Fork Rd, Denton, TX 76201. "
      "Fecha de vigencia: 2027-01-01. Operaciones: venta al por menor de abarrotes secos. Ventas: 650000. Valor del edificio: 900000. "
      "Construcción: mampostería. Año de construcción: 1999.")


def _typed_pdf(path: Path, lines: list[str]) -> None:
    """A one-page PDF with a typed text layer, built by hand (no extra library)."""
    body = "BT /F1 11 Tf 20 760 Td 14 TL " + " ".join(f"({line}) Tj T*" for line in lines) + " ET"
    objs = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>",
            f"<< /Length {len(body)} >>\nstream\n{body}\nendstream"]
    out, offsets = "%PDF-1.4\n", []
    for n, obj in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{n} 0 obj\n{obj}\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n" + "".join(f"{o:010d} 00000 n \n" for o in offsets)
    path.write_text(out + f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n")


def _scan(lines: list[str], mode: str = "RGB", turn: int = 0):
    from PIL import Image, ImageDraw, ImageFont

    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Courier New.ttf", 30)
    page = Image.new("RGB", (1500, 60 + 50 * len(lines)), "white")
    draw = ImageDraw.Draw(page)
    for i, line in enumerate(lines):
        draw.text((30, 30 + 50 * i), line, fill="black", font=font)
    return page.rotate(turn, expand=True, fillcolor="white").convert(mode) if turn else page.convert(mode)


def build(root: Path) -> dict[str, Path]:
    import openpyxl

    lines = [part.strip() + "." for part in FACTS.split(". ") if part.strip()]
    lines = [line.rstrip(".") + "." for line in lines]
    folders = {}

    def folder(kind: str) -> Path:
        path = root / kind
        path.mkdir()
        folders[kind] = path
        return path

    _typed_pdf(folder("typed PDF") / "application.pdf", lines)
    _scan(lines, "L").save(folder("image-only PDF") / "application.pdf", "PDF", resolution=150)
    _scan(lines, "RGB").save(folder("colour scan") / "scan.jpg")
    _scan(lines, "L").save(folder("greyscale scan") / "scan.jpg")
    _scan(lines, "L", 90).save(folder("rotated scan") / "scan.jpg")
    book = openpyxl.Workbook()
    for line in lines:
        label, _, value = line.rstrip(".").partition(": ")
        book.active.append([label, value])
    book.save(folder("Excel") / "schedule.xlsx")
    (folder("email-only") / "email.md").write_text("From: producer (fictional)\nSubject: new submission\n\n" + FACTS + "\n")
    (folder("Spanish") / "solicitud.md").write_text(ES + "\n")
    return folders


def environment() -> list[str]:
    import pytesseract

    versions = [f"{name} {metadata.version(name)}" for name in ("pdfplumber", "openpyxl", "pytesseract", "pdf2image", "pillow")]
    poppler = subprocess.run(["pdftoppm", "-v"], capture_output=True, text=True).stderr.splitlines()[:1]
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True).stdout.strip()
    return [f"python {sys.executable} {sys.version.split()[0]}", ", ".join(versions),
            f"tesseract {pytesseract.get_tesseract_version()}", f"poppler {poppler[0] if poppler else 'missing'}", f"commit {head}"]


def run() -> int:
    for line in environment():
        print(line)
    bad = 0
    with tempfile.TemporaryDirectory() as tmp:
        llm_extract.CACHE = Path(tmp) / "cache"  # fresh: every folder is an uncached call, and the real token log is never touched
        llm_extract.CACHE.mkdir()
        for kind, folder in build(Path(tmp)).items():
            report = prepare.process_submission(folder)  # a missing reader raises sources.ReaderMissing here and stops the run
            unread = {row["file"]: row["reason"] for row in report.get("unread") or []}
            values = sum(1 for row in report["fields"] if row.get("value"))
            for path in sorted(folder.iterdir()):
                ok = path.name not in unread and path.name not in (report.get("needs_human") or [])
                call = f"call failed: {report['error']}" if report.get("error") else f"{values} of {len(report['fields'])} fields"
                print(f"{kind:15} {path.name:16} {'read' if ok else 'NOT READ: ' + unread.get(path.name, 'needs a person')} · {call}")
                bad += (not ok) or bool(report.get("error"))
    print("smoke ok" if not bad else f"smoke FAILED: {bad} file(s) not read or call failed")
    return 1 if bad else 0


if __name__ == "__main__":
    llm_extract.provider_guard(calling=False)
    sys.exit(run())
