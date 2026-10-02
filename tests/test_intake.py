"""Upload intake: packet splitting, duplicates, HEIC, active content, malware, scan rotation."""

import base64
import io
import shutil
import socket
import zipfile
from typing import Any

import pytest
from fastapi import HTTPException

from insureflow.api.main import InsuranceDocumentPayload
from insureflow.e2e.documents import LOSS_RUN, LOSS_RUN_CONT, SOV
from insureflow.e2e.documents import fake_clamd as _fake_clamd
from insureflow.e2e.documents import pdf as _pdf
from insureflow.e2e.documents import zip_of as _zip
from insureflow.ingestion.insurance.classifier import InsuranceDocumentType
from insureflow.ingestion.insurance.loader import InsuranceDocumentLoader
from insureflow.ingestion.intake import ACTIVE_CONTENT_FIELD, INFECTED_ENGINE, find_active_content, prepare, split_sections
from insureflow.ingestion.lending.loader import load_lending_documents_from_payloads
from insureflow.ingestion.mortgage.loader import MortgageDocumentParser
from insureflow.lending.models import LendingDocumentType
from insureflow.models.mortgage import MortgageDocumentType
from insureflow.storage.draft_bundle_store import DraftBundleStore
from insureflow.storage.job_store import MemoryJobStore


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


# ── Packet splitting ─────────────────────────────────────────────────


def test_split_sections_uses_headings_and_continuations():
    pages = ["LOSS RUN\n...", "continued claims", "SCHEDULE OF VALUES\n...", "more locations"]
    kinds = {"LOSS RUN": "loss", "SCHEDULE OF VALUES": "sov"}

    def classify(heading):
        return next((v for k, v in kinds.items() if k in heading), "other")

    assert split_sections(pages, classify, "other") == [("loss", 1, 2), ("sov", 3, 4)]
    # body text past the heading never starts a section
    assert split_sections(["LOSS RUN\n" + "x" * 400 + "SCHEDULE OF VALUES"], classify, "other") == [("loss", 1, 1)]


def test_insurance_packet_is_split_into_documents():
    packet = _pdf(pages=[LOSS_RUN, LOSS_RUN_CONT, SOV])
    bundle = InsuranceDocumentLoader().load_from_documents([{"filename": "broker_package.pdf", "content": _b64(packet), "encoding": "base64"}])

    assert [d.document_type for d in bundle.unstructured] == [InsuranceDocumentType.LOSS_RUN.value, InsuranceDocumentType.SCHEDULE_OF_VALUES.value]
    loss_run, sov = bundle.unstructured
    assert "10518" in loss_run.raw_text and "Main St" not in loss_run.raw_text  # page 2 stayed with the loss run
    assert "Main St" in sov.raw_text


def test_single_document_pdf_is_not_split():
    application = _pdf(pages=[["COMMERCIAL INSURANCE APPLICATION", "Please attach 5 years of loss runs"], ["Annual revenue $12,000,000", "Prior inspection: yes"]])
    bundle = InsuranceDocumentLoader().load_from_documents([{"filename": "application.pdf", "content": _b64(application), "encoding": "base64"}])
    assert len(bundle.unstructured) == 1


def test_mortgage_and_lending_packets_are_split():
    packet = _pdf(pages=[["Form W-2 Wage and Tax Statement 2025", "Wages $84,000"], ["PAY STUB", "Pay period 09/01-09/15  Gross $3,500"]])
    docs = MortgageDocumentParser(use_llm=False).parse_upload(packet, "income_docs.pdf", "m-1")
    assert [d.document_type for d in docs] == [MortgageDocumentType.W2, MortgageDocumentType.PAY_STUB]

    packet = _pdf(pages=[["Business Bank Statement - Checking", "Ending balance $41,200"], ["Profit and Loss Statement", "Revenue $1,200,000"]])
    lending = load_lending_documents_from_payloads([{"filename": "financials.pdf", "content": _b64(packet), "encoding": "base64"}], use_llm=False)
    assert [d.document_type for d in lending] == [LendingDocumentType.BANK_STATEMENT, LendingDocumentType.PROFIT_LOSS]


# ── Duplicates ───────────────────────────────────────────────────────


def test_duplicate_uploads_are_dropped():
    doc = {"filename": "loss_run.pdf", "content": _b64(_pdf(pages=[LOSS_RUN])), "encoding": "base64"}
    bundle = InsuranceDocumentLoader().load_from_documents([doc, {**doc, "filename": "loss_run (1).pdf"}])
    assert len(bundle.unstructured) == 1

    store = DraftBundleStore(MemoryJobStore())
    draft = store.create(org_id="test")
    store.add_documents(draft["bundle_id"], [doc], org_id="test")
    again = store.add_documents(draft["bundle_id"], [{**doc, "filename": "copy.pdf"}], org_id="test")
    assert again is not None
    assert len(again["documents"]) == 1
    assert again["last_skipped_oversized"][0]["reason"].startswith("duplicate of loss_run.pdf")


# ── HEIC ─────────────────────────────────────────────────────────────


def test_heic_photos_become_jpeg():
    import pillow_heif
    from PIL import Image

    heic = io.BytesIO()
    pillow_heif.from_pillow(Image.new("RGB", (64, 64), "white")).save(heic, format="HEIF")
    data, filename, blocked, _ = prepare(heic.getvalue(), "IMG_0042.HEIC")
    assert blocked is None and filename == "IMG_0042.jpg" and data[:3] == b"\xff\xd8\xff"


# ── Active content ───────────────────────────────────────────────────


def test_active_content_is_detected_and_flagged():
    js_pdf = _pdf(extra_catalog="/OpenAction<</S/JavaScript/JS(app.alert(1))>>")
    assert find_active_content(js_pdf, "a.pdf") == ["JavaScript"]
    assert find_active_content(_pdf(), "a.pdf") == []

    xlsm = io.BytesIO()
    with zipfile.ZipFile(xlsm, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("xl/vbaProject.bin", b"\0")
    assert find_active_content(xlsm.getvalue(), "sov.xlsm") == ["macros"]

    _, _, fields, *_ = InsuranceDocumentLoader()._process_binary(js_pdf, "a.pdf")
    assert fields[ACTIVE_CONTENT_FIELD][0].value == "JavaScript"


# ── Malware ──────────────────────────────────────────────────────────


def test_malware_is_blocked_and_refers(monkeypatch):
    monkeypatch.setenv("CLAMAV_HOST", "127.0.0.1")

    monkeypatch.setenv("CLAMAV_PORT", str(_fake_clamd(b"stream: Win.Test.EICAR_HDB-1 FOUND\0")))
    text, engine, *_ = InsuranceDocumentLoader()._process_binary(_pdf(), "loss_run.pdf")
    assert engine == INFECTED_ENGINE and "Acme" not in text

    monkeypatch.setenv("CLAMAV_PORT", str(_fake_clamd(b"stream: OK\0")))
    assert prepare(_pdf(), "a.pdf")[2] is None

    monkeypatch.setenv("CLAMAV_PORT", str(_fake_clamd(b"stream: Win.Test.EICAR_HDB-1 FOUND\0")))
    with pytest.raises(HTTPException, match="antivirus"):
        InsuranceDocumentPayload(filename="a.pdf", content=_b64(_pdf()), encoding="base64")

    # clamd configured but down: fail closed
    with socket.create_server(("127.0.0.1", 0)) as s:
        dead_port = s.getsockname()[1]
    monkeypatch.setenv("CLAMAV_PORT", str(dead_port))
    assert prepare(_pdf(), "a.pdf")[2] == INFECTED_ENGINE


def test_insurance_pipeline_refers_blocked_documents(monkeypatch):
    from insureflow.insurance.pipeline import InsurancePipeline

    monkeypatch.setenv("CLAMAV_HOST", "127.0.0.1")
    monkeypatch.setenv("CLAMAV_PORT", str(_fake_clamd(b"stream: Win.Test.EICAR_HDB-1 FOUND\0")))
    with open("examples/insurance/sample_acord.xml") as f:
        acord = f.read()
    result = InsurancePipeline(use_llm=False).run(
        documents=[{"filename": "acord.xml", "content": acord, "encoding": "utf-8"}, {"filename": "loss_run.pdf", "content": _b64(_pdf()), "encoding": "base64"}]
    )
    memo = result["memo"] if isinstance(result["memo"], dict) else result["memo"].model_dump()
    assert memo["decision"] == "refer"
    assert any(f["title"] == "Malware detected in document" for f in memo["key_findings"])


# ── Rotated scans ────────────────────────────────────────────────────


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="needs the tesseract binary")
def test_sideways_scans_are_turned_upright_before_ocr():
    pytesseract = pytest.importorskip("pytesseract")
    import glob

    from PIL import Image, ImageDraw, ImageFont

    from insureflow.ingestion.ocr import _upright

    fonts = glob.glob("/System/Library/Fonts/Supplemental/Arial.ttf") + glob.glob("/usr/share/fonts/**/DejaVuSans.ttf", recursive=True)
    if not fonts:
        pytest.skip("no TrueType font available")
    font = ImageFont.truetype(fonts[0], 28)
    page = Image.new("L", (1200, 900), 255)
    draw = ImageDraw.Draw(page)
    for i, line in enumerate(LOSS_RUN + LOSS_RUN_CONT):
        draw.text((60, 60 + i * 60), line, fill=0, font=font)

    for angle in (90, 180):
        sideways = page.rotate(angle, expand=True)
        assert "Acme Widgets" in pytesseract.image_to_string(_upright(sideways))


# ── Containers: ZIP and email ────────────────────────────────────────


def test_zip_is_unpacked_into_its_documents():
    inner = _zip({"sov.pdf": _pdf(pages=[SOV])})
    package = _zip({"loss_run.pdf": _pdf(pages=[LOSS_RUN, LOSS_RUN_CONT]), "more/inner.zip": inner, "__MACOSX/._loss_run.pdf": b"junk"})
    bundle = InsuranceDocumentLoader().load_from_documents([{"filename": "package.zip", "content": _b64(package), "encoding": "base64"}])
    assert sorted(d.document_type for d in bundle.unstructured) == sorted([InsuranceDocumentType.LOSS_RUN.value, InsuranceDocumentType.SCHEDULE_OF_VALUES.value])


def test_zip_bomb_is_left_whole_and_flagged_unreadable(monkeypatch):
    from insureflow.ingestion import intake

    monkeypatch.setattr(intake, "MAX_EXPANDED_BYTES", 1000)
    package = _zip({"big.txt": b"A" * 5000})
    docs = intake.expand_documents([{"filename": "package.zip", "content": _b64(package), "encoding": "base64"}])
    assert [d["filename"] for d in docs] == ["package.zip"]
    _, engine, *_ = InsuranceDocumentLoader()._process_binary(package, "package.zip")
    assert engine == intake.UNREADABLE_ENGINE


@pytest.mark.skipif(shutil.which("zip") is None, reason="needs the zip CLI to make an encrypted archive")
def test_password_protected_zip(tmp_path):
    import subprocess

    from insureflow.ingestion.intake import expand_documents
    from insureflow.ingestion.locked_docs import WrongPasswordError, is_locked, unlock

    (tmp_path / "loss_run.pdf").write_bytes(_pdf(pages=[LOSS_RUN]))
    subprocess.run(["zip", "-q", "-P", "secret", "locked.zip", "loss_run.pdf"], cwd=tmp_path, check=True)
    locked = (tmp_path / "locked.zip").read_bytes()

    assert is_locked(locked, "locked.zip")
    with pytest.raises(WrongPasswordError):
        unlock(locked, "locked.zip", "nope")
    opened = unlock(locked, "locked.zip", "secret")
    assert [d["filename"] for d in expand_documents([{"filename": "locked.zip", "content": _b64(opened), "encoding": "base64"}])] == ["locked.zip/loss_run.pdf"]


def test_email_attachments_become_documents():
    from email.message import EmailMessage

    msg = EmailMessage()
    msg["Subject"] = "New submission - Acme Widgets"
    msg.set_content("Loss runs attached.")
    msg.add_alternative('<p>Loss runs attached.<img src="cid:logo"></p>', subtype="html")
    html_part = msg.get_payload()[1]  # type: ignore[index, unused-ignore]
    assert isinstance(html_part, EmailMessage)
    html_part.add_related(b"\x89PNG\r\n\x1a\n" + b"\0" * 50, maintype="image", subtype="png", cid="logo", filename="logo.png", disposition="inline")
    msg.add_attachment(_pdf(pages=[LOSS_RUN]), maintype="application", subtype="pdf", filename="loss_run.pdf")

    bundle = InsuranceDocumentLoader().load_from_documents([{"filename": "broker.eml", "content": _b64(msg.as_bytes()), "encoding": "base64"}])
    texts = [d.raw_text for d in bundle.unstructured]
    assert len(texts) == 2  # the email body and the PDF — not the signature logo
    assert any("Loss runs attached" in t for t in texts) and any("10442" in t for t in texts)


def _ole(tree: dict[str, Any]) -> bytes:
    """Minimal OLE compound file writer (512-byte sectors, no mini stream) — enough to build a .msg for tests."""
    import struct

    end, free, fatsect, nostream = 0xFFFFFFFE, 0xFFFFFFFF, 0xFFFFFFFD, 0xFFFFFFFF
    entries: list[dict[str, Any]] = []

    def add(name, node):
        if isinstance(node, bytes):  # readers send anything under 4096 bytes to the mini stream, which this writer doesn't build
            node = node.ljust(4096, b"\0")
        entry = {"name": name, "node": node, "left": nostream, "right": nostream, "child": nostream}
        entries.append(entry)
        index = len(entries) - 1
        if isinstance(node, dict):
            kids = [add(k, v) for k, v in node.items()]
            if kids:
                entry["child"] = kids[0]
                for a, b in zip(kids, kids[1:]):
                    entries[a]["right"] = b
        return index

    add("Root Entry", tree)
    streams = [e for e in entries if isinstance(e["node"], bytes)]
    dir_sectors = -(-len(entries) // 4)
    data_sectors = sum(-(-len(e["node"]) // 512) for e in streams)
    fat_sectors = 1
    while fat_sectors * 128 < fat_sectors + dir_sectors + data_sectors:
        fat_sectors += 1
    fat = [fatsect] * fat_sectors + [n + 1 for n in range(fat_sectors, fat_sectors + dir_sectors - 1)] + [end]
    data = b""
    for e in streams:
        count = -(-len(e["node"]) // 512)
        e["start"] = len(fat) if count else end
        fat += [len(fat) + n + 1 for n in range(count - 1)] + ([end] if count else [])
        data += e["node"].ljust(count * 512, b"\0")
    fat += [free] * (fat_sectors * 128 - len(fat))

    directory = b""
    for i, e in enumerate(entries):
        name = e["name"].encode("utf-16-le") + b"\0\0"
        kind = 5 if i == 0 else 1 if isinstance(e["node"], dict) else 2
        size = len(e["node"]) if kind == 2 else 0
        directory += name.ljust(64, b"\0") + struct.pack("<HBBIII", len(name), kind, 1, e["left"], e["right"], e["child"]) + b"\0" * 36 + struct.pack("<II", e.get("start", end), size) + b"\0" * 4
    directory = directory.ljust(dir_sectors * 512, b"\0")

    header = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\0" * 16 + struct.pack("<HHHHH", 0x3E, 3, 0xFFFE, 9, 6) + b"\0" * 6
    header += struct.pack("<IIIIIIII", 0, fat_sectors, fat_sectors, 0, 0, end, 0, end) + struct.pack("<I", 0)
    header += struct.pack("<109I", *(list(range(fat_sectors)) + [free] * (109 - fat_sectors)))
    return header + struct.pack(f"<{len(fat)}I", *fat) + directory + data


def test_outlook_msg_body_and_attachments():
    from insureflow.ingestion.structured_docs import read_msg

    def utf16(text):
        return text.encode("utf-16-le")

    msg = _ole(
        {
            "__substg1.0_0037001F": utf16("Submission - Acme Widgets"),
            "__substg1.0_0C1A001F": utf16("Dana Broker"),
            "__substg1.0_1000001F": utf16("Please quote. Loss run attached."),
            "__attach_version1.0_#00000000": {"__substg1.0_3707001F": utf16("loss_run.pdf"), "__substg1.0_37010102": _pdf(pages=[LOSS_RUN])},
        }
    )
    text, attachments = read_msg(msg)
    assert "Subject: Submission - Acme Widgets" in text and "Please quote" in text
    assert [name for name, _ in attachments] == ["loss_run.pdf"]

    bundle = InsuranceDocumentLoader().load_from_documents([{"filename": "broker.msg", "content": _b64(msg), "encoding": "base64"}])
    assert len(bundle.unstructured) == 2 and any("10442" in d.raw_text for d in bundle.unstructured)


# ── Unreadable files and wrong extensions ────────────────────────────


def test_corrupt_pdf_is_flagged_unreadable_not_passed_on_as_bytes():
    from insureflow.ingestion.intake import UNREADABLE_ENGINE

    truncated = _pdf()[:300]
    text, engine, *_ = InsuranceDocumentLoader()._process_binary(truncated, "loss_run.pdf")
    assert engine == UNREADABLE_ENGINE and "%PDF" not in text

    [doc] = MortgageDocumentParser(use_llm=False).parse_upload(truncated, "w2.pdf", "m-1")
    assert any(f.value == UNREADABLE_ENGINE for f in doc.extracted_fields["ocr_engine"])

    [lend] = load_lending_documents_from_payloads([{"filename": "bank.pdf", "content": _b64(truncated), "encoding": "base64"}], use_llm=False)
    assert lend.ocr_engine == UNREADABLE_ENGINE


def test_wrong_extension_is_corrected():
    png = io.BytesIO()
    from PIL import Image

    Image.new("RGB", (8, 8), "white").save(png, format="PNG")
    assert prepare(png.getvalue(), "scan.pdf")[1] == "scan.png"
    assert prepare(_pdf(), "statement.txt")[1] == "statement.pdf"
    assert prepare(_pdf(), "statement.pdf")[1] == "statement.pdf"


def test_office_files_are_read_by_mortgage_and_lending():
    import openpyxl

    wb = openpyxl.Workbook()
    wb.active.append(["Account", "Ending balance"])
    wb.active.append(["Checking", 41200])
    xlsx = io.BytesIO()
    wb.save(xlsx)

    [doc] = MortgageDocumentParser(use_llm=False).parse_upload(xlsx.getvalue(), "assets.xlsx", "m-1")
    assert "41200" in doc.raw_text
    [lend] = load_lending_documents_from_payloads([{"filename": "assets.xlsx", "content": _b64(xlsx.getvalue()), "encoding": "base64"}], use_llm=False)
    assert "41200" in lend.content


# ── Scanned packets ──────────────────────────────────────────────────


def test_scanned_packet_is_split_on_ocr_pages():
    from insureflow.ingestion.intake import pdf_packet_sections

    loader = InsuranceDocumentLoader()
    blank_pages = _pdf(pages=[[""], [""], [""]])  # no text layer, like a scan
    ocr_text = "\f".join("\n".join(page) for page in (LOSS_RUN, LOSS_RUN_CONT, SOV))
    sections = pdf_packet_sections(blank_pages, "scan.pdf", loader._classify_heading, InsuranceDocumentType.SUPPLEMENTAL, loader.classifier.classify, ocr_text=ocr_text)
    assert [(kind, first, last) for kind, first, last, _ in sections] == [(InsuranceDocumentType.LOSS_RUN, 1, 2), (InsuranceDocumentType.SCHEDULE_OF_VALUES, 3, 3)]


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="needs the tesseract binary")
def test_scanned_packet_end_to_end(monkeypatch):
    """Image-only PDF → real Tesseract OCR (pdf2image stood in for, as poppler may be absent) → split."""
    import glob
    import sys
    import types

    pytest.importorskip("pytesseract")
    from PIL import Image, ImageDraw, ImageFont

    fonts = glob.glob("/System/Library/Fonts/Supplemental/Arial.ttf") + glob.glob("/usr/share/fonts/**/DejaVuSans.ttf", recursive=True)
    if not fonts:
        pytest.skip("no TrueType font available")
    font = ImageFont.truetype(fonts[0], 28)
    images = []
    for lines in (LOSS_RUN, LOSS_RUN_CONT, SOV):
        page = Image.new("RGB", (1300, 900), "white")
        draw = ImageDraw.Draw(page)
        for i, line in enumerate(lines):
            draw.text((50, 50 + i * 60), line, fill="black", font=font)
        images.append(page)
    scan = io.BytesIO()
    images[0].save(scan, format="PDF", save_all=True, append_images=images[1:])
    monkeypatch.setitem(sys.modules, "pdf2image", types.SimpleNamespace(convert_from_path=lambda *_a, **_k: images))
    monkeypatch.setenv("USE_DOC_ROUTER", "0")

    bundle = InsuranceDocumentLoader().load_from_documents([{"filename": "faxed_package.pdf", "content": _b64(scan.getvalue()), "encoding": "base64"}])
    assert [d.document_type for d in bundle.unstructured] == [InsuranceDocumentType.LOSS_RUN.value, InsuranceDocumentType.SCHEDULE_OF_VALUES.value]


# ── Duplicate large uploads ──────────────────────────────────────────


def test_duplicate_presigned_upload_is_skipped_by_etag():
    from unittest.mock import patch

    store = DraftBundleStore(MemoryJobStore())
    draft = store.create(org_id="test")
    store.add_object_reference(draft["bundle_id"], storage_key="k1", filename="sov.xlsx", size_bytes=10, etag="abc", org_id="test")
    with patch("insureflow.storage.object_storage.delete_object") as delete:
        again = store.add_object_reference(draft["bundle_id"], storage_key="k2", filename="sov (1).xlsx", size_bytes=10, etag="abc", org_id="test")
    assert again is not None
    assert len(again["documents"]) == 1
    delete.assert_called_once_with("k2")
    assert "duplicate of sov.xlsx" in again["last_skipped_oversized"][0]["reason"]
