"""What happens to a raw upload before any parser sees it.

Shared by the insurance, mortgage and lending loaders: unpack ZIPs and email
attachments, drop duplicate uploads, fix wrong extensions, block files that
can't or mustn't be read (password-protected, malware, unreadable), note
active content, convert iPhone photos, and split multi-document PDF packets.
"""

from __future__ import annotations

import base64
import hashlib
import io
import logging
import os
import re
import socket
import struct
import zipfile
from pathlib import Path
from typing import Any, Callable, TypeVar

from insureflow.ingestion.locked_docs import LOCKED_ENGINE, LOCKED_TEXT, is_locked

logger = logging.getLogger(__name__)

INFECTED_ENGINE = "malware_detected"
UNREADABLE_ENGINE = "unreadable"
# A blocked file keeps no extracted text — only this marker — and refers the submission.
BLOCKED_TEXT = {
    LOCKED_ENGINE: LOCKED_TEXT,
    INFECTED_ENGINE: "[Blocked: an antivirus scan flagged this file — it was not opened. Ask for a clean copy]",
    UNREADABLE_ENGINE: "[Unreadable: no text could be extracted — the file may be corrupt, empty, or an unsupported format. Ask for a new copy]",
}
BLOCKED_FINDINGS = {
    LOCKED_ENGINE: ("Password-protected document", "are encrypted and no content was extracted. Re-upload them with their password, or ask for an unlocked copy."),
    INFECTED_ENGINE: ("Malware detected in document", "were flagged by the antivirus scan and not opened. Do not download them; ask for a clean copy."),
    UNREADABLE_ENGINE: ("Unreadable document", "produced no usable text — they may be corrupt, empty, or an unsupported format. Ask for a new copy."),
}
ACTIVE_CONTENT_FIELD = "active_content"

HEIC_EXTS = frozenset({".heic", ".heif"})
IMAGE_EXTS = frozenset({".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif"})
_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


# ── Malware ──────────────────────────────────────────────────────────


def malware_scanning_enabled() -> bool:
    return bool(os.getenv("CLAMAV_HOST", "").strip())


def scan_for_malware(data: bytes) -> str | None:
    """Signature name if ClamAV flags the file, else None.

    Off unless CLAMAV_HOST is set (clamd's INSTREAM protocol, port 3310 by
    default). If clamd is configured but unreachable this fails closed: the
    file is treated as flagged rather than let through unscanned.
    """
    if not malware_scanning_enabled():
        return None
    try:
        with socket.create_connection((os.environ["CLAMAV_HOST"].strip(), int(os.getenv("CLAMAV_PORT", "3310"))), timeout=30) as sock:
            sock.sendall(b"zINSTREAM\0")
            for i in range(0, len(data), 1 << 20):
                chunk = data[i : i + (1 << 20)]
                sock.sendall(struct.pack(">I", len(chunk)) + chunk)
            sock.sendall(struct.pack(">I", 0))
            reply = sock.recv(4096).decode(errors="replace").strip("\0\n ")
    except OSError as exc:
        logger.error("ClamAV scan failed, blocking file: %s", exc)
        return "scan-unavailable"
    if reply.endswith("FOUND"):
        return reply.removeprefix("stream:").removesuffix("FOUND").strip()
    if not reply.endswith("OK"):
        logger.error("Unexpected ClamAV reply, blocking file: %s", reply)
        return "scan-error"
    return None


# ── Active content (never executed here, but risky for whoever downloads the file) ──

_PDF_ACTIVE = {b"/JavaScript": "JavaScript", b"/JS": "JavaScript", b"/Launch": "launch action", b"/EmbeddedFile": "embedded file"}


def find_active_content(data: bytes, filename: str) -> list[str]:
    """Macros, scripts, launch actions or embedded files inside a document."""
    ext = Path(filename).suffix.lower()
    found: set[str] = set()
    try:
        if ext == ".pdf":
            found.update(label for token, label in _PDF_ACTIVE.items() if re.search(re.escape(token) + rb"(?![A-Za-z])", data))
            if b"/ObjStm" in data:  # names can hide inside compressed object streams
                from pypdf import PdfReader

                root: Any = PdfReader(io.BytesIO(data)).trailer["/Root"].get_object()
                names: Any = root["/Names"].get_object() if "/Names" in root else {}
                action: Any = root["/OpenAction"].get_object() if "/OpenAction" in root else {}
                kind = action.get("/S") if hasattr(action, "get") else None  # an array here is just "open at page N"
                if "/JavaScript" in names or "/AA" in root or kind == "/JavaScript":
                    found.add("JavaScript")
                if kind == "/Launch":
                    found.add("launch action")
                if "/EmbeddedFiles" in names:
                    found.add("embedded file")
        elif data[:4] == b"PK\x03\x04":
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                if any(n.lower().endswith("vbaproject.bin") for n in zf.namelist()):
                    found.add("macros")
        elif data.startswith(_OLE_MAGIC):
            import olefile

            with olefile.OleFileIO(io.BytesIO(data)) as ole:
                if any(ole.exists(s) for s in ("Macros", "_VBA_PROJECT_CUR", "VBA")):
                    found.add("macros")
    except Exception as exc:
        logger.debug("active-content check skipped for %s: %s", filename, exc)
    return sorted(found)


# ── Format normalisation ─────────────────────────────────────────────


def heic_to_jpeg(data: bytes) -> bytes:
    import pillow_heif
    from PIL import Image

    pillow_heif.register_heif_opener()
    out = io.BytesIO()
    Image.open(io.BytesIO(data)).convert("RGB").save(out, format="JPEG", quality=92)
    return out.getvalue()


# (magic bytes, offset, extension) — only signatures that can't occur in text
_MAGIC = [
    (b"\x89PNG\r\n\x1a\n", 0, ".png"),
    (b"\xff\xd8\xff", 0, ".jpg"),
    (b"II*\x00", 0, ".tif"),
    (b"MM\x00*", 0, ".tif"),
    (b"ftypheic", 4, ".heic"),
    (b"ftypheix", 4, ".heic"),
    (b"ftypmif1", 4, ".heic"),
]
_SAME_TYPE = {".jpg": {".jpg", ".jpeg"}, ".tif": {".tif", ".tiff"}, ".heic": {".heic", ".heif"}}


def sniff_extension(data: bytes) -> str | None:
    """The file's real type from its first bytes, when that's certain."""
    if b"%PDF-" in data[:1024]:  # PDFs may carry a little junk before the header
        return ".pdf"
    return next((ext for magic, offset, ext in _MAGIC if data[offset : offset + len(magic)] == magic), None)


def decode_text(data: bytes) -> str:
    """Bytes as text when they are text; "" for binary (archives, unknown
    formats), which is never worth decoding — callers then flag it unreadable."""
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16", errors="replace")
    if b"\0" in data[:8192]:
        return ""
    return data.decode("utf-8", errors="replace")


def is_unreadable(text: str) -> bool:
    """Extraction produced nothing usable: empty, a failure marker, raw PDF
    syntax, or binary junk decoded as text."""
    sample = text.strip()[:4000]
    if not sample or sample.startswith(("[OCR: No text", "%PDF-")):
        return True
    junk = sum(1 for c in sample if c == "\ufffd" or (ord(c) < 32 and c not in "\n\r\t\f"))
    return junk / len(sample) > 0.05


def prepare(data: bytes, filename: str) -> tuple[bytes, str, str | None, list[str]]:
    """Run every pre-parse check on one upload.

    Returns ``(data, filename, blocked_engine, active_content)``. When
    ``blocked_engine`` is set the file must not be parsed — use
    ``BLOCKED_TEXT[blocked_engine]`` as its text. A wrong extension is
    corrected (a PNG named .pdf comes back as .png), and HEIC photos come
    back as JPEG, with the filename changed to match.
    """
    real = sniff_extension(data)
    if real and Path(filename).suffix.lower() not in _SAME_TYPE.get(real, {real}):
        logger.info("%s is really a %s file — treating it as one", filename, real)
        filename = str(Path(filename).with_suffix(real))
    if is_locked(data, filename):
        return data, filename, LOCKED_ENGINE, []
    signature = scan_for_malware(data)
    if signature:
        logger.warning("Blocked %s: antivirus flagged %s", filename, signature)
        return data, filename, INFECTED_ENGINE, []
    if Path(filename).suffix.lower() in HEIC_EXTS:
        try:
            data, filename = heic_to_jpeg(data), str(Path(filename).with_suffix(".jpg"))
        except Exception as exc:
            logger.warning("HEIC conversion failed for %s: %s", filename, exc)
    return data, filename, None, find_active_content(data, filename)


# ── Duplicates ───────────────────────────────────────────────────────


def content_hash(content: Any) -> str:
    raw = content if isinstance(content, bytes) else str(content or "").encode()
    return hashlib.sha256(raw).hexdigest()


def dedupe_documents(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop repeat uploads of the same file (same bytes, any filename) so a
    loss run sent twice isn't counted twice. Keeps the first copy."""
    seen: dict[tuple[str, str], str] = {}
    unique: list[dict[str, Any]] = []
    for doc in documents:
        # an s3_ref is keyed by its storage key here; repeat large uploads are caught by ETag in the draft store
        key = (str(doc.get("encoding") or "utf-8"), content_hash(doc.get("content")))
        if key in seen:
            logger.info("Skipping %s: duplicate of %s", doc.get("filename"), seen[key])
            continue
        seen[key] = str(doc.get("filename") or "")
        unique.append(doc)
    return unique


# ── Containers: ZIP archives and emails become the documents inside them ──

MAX_EXPANDED_FILES = 200
MAX_EXPANDED_BYTES = 500 * 1024 * 1024  # zip-bomb guard: total unpacked size across one upload
_MAX_DEPTH = 3  # a ZIP inside an email inside a ZIP
_OFFICE_ZIP_EXTS = frozenset({".docx", ".docm", ".xlsx", ".xlsm", ".xltx", ".xltm", ".pptx", ".pptm"})


def _zip_members(data: bytes, budget: list[int]) -> list[tuple[str, bytes]] | None:
    """Files inside a ZIP, or None to leave it whole (password-protected —
    flagged as locked later — or over the size limits, flagged unreadable)."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        return None
    with zf:
        infos = [i for i in zf.infolist() if not i.is_dir() and "__MACOSX" not in i.filename and not Path(i.filename).name.startswith(".")]
        if any(i.flag_bits & 0x1 for i in infos) or len(infos) > MAX_EXPANDED_FILES:
            return None
        members: list[tuple[str, bytes]] = []
        for info in infos:
            with zf.open(info) as f:
                content = f.read(budget[0] + 1)  # declared sizes can lie; cap what is actually read
            budget[0] -= len(content)
            if budget[0] < 0:
                logger.warning("ZIP unpacks past %d bytes — left whole", MAX_EXPANDED_BYTES)
                return None
            members.append((info.filename, content))
        return members


def _email_attachments(data: bytes, filename: str) -> list[tuple[str, bytes]]:
    if Path(filename).suffix.lower() == ".msg":
        from insureflow.ingestion.structured_docs import read_msg

        try:
            return read_msg(data)[1]
        except Exception as exc:
            logger.warning("Could not read attachments from %s: %s", filename, exc)
            return []
    from email import message_from_bytes, policy

    attachments = []
    for part in message_from_bytes(data, policy=policy.default).walk():
        name = part.get_filename()
        # inline images are signature logos, not documents
        if not name or (part.get_content_disposition() == "inline" and part.get_content_maintype() == "image"):
            continue
        payload = part.get_payload(decode=True)
        if isinstance(payload, bytes):
            attachments.append((name, payload))
    return attachments


def expand_documents(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Replace each ZIP with the files inside it, and add each email's
    attachments after the email itself (whose body stays a document)."""
    out: list[dict[str, Any]] = []
    budget = [MAX_EXPANDED_BYTES]
    queue = [(doc, 0) for doc in documents]
    while queue:
        doc, depth = queue.pop(0)
        filename = str(doc.get("filename") or "")
        ext = Path(filename).suffix.lower()
        if doc.get("encoding") != "base64" or depth >= _MAX_DEPTH or ext not in {".zip", ".eml", ".msg"} | {""}:
            out.append(doc)
            continue
        data = base64.b64decode(str(doc.get("content") or ""))
        if ext in (".zip", "") and data[:4] == b"PK\x03\x04":
            members = _zip_members(data, budget)
            if members is not None:
                queue[:0] = [({"filename": f"{filename}/{name}", "content": base64.b64encode(body).decode(), "encoding": "base64"}, depth + 1) for name, body in members]
                continue
            out.append(doc)
            continue
        out.append(doc)
        if ext in (".eml", ".msg"):
            attachments = [(f"{filename}/{name}", body) for name, body in _email_attachments(data, filename)]
            queue[:0] = [({"filename": name, "content": base64.b64encode(body).decode(), "encoding": "base64"}, depth + 1) for name, body in attachments]
    return out


def intake_documents(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Every loader's first step: unpack containers, then drop duplicates."""
    return dedupe_documents(expand_documents(documents))


# ── Multi-document packets ───────────────────────────────────────────

T = TypeVar("T")


_SECTION_NUMBER = re.compile(r"^\(?(\d+|[IVX]+|[A-Z])[.)]\s")  # "8. SURVEYOR'S CERTIFICATION" is part of a document


def _is_title(line: str) -> bool:
    """Short, in capitals or Title Case; not a sentence, field row or numbered section."""
    words = line.split()
    letters = [c for c in line if c.isalpha()]
    if not 1 <= len(words) <= 10 or len(letters) < 4 or line[-1] in ".;" or any(c in line for c in ",:$") or _SECTION_NUMBER.match(line):
        return False
    capitals = sum(c.isupper() for c in letters) / len(letters)
    return capitals >= 0.6 or all(w[0].isupper() for w in words if len(w) > 3 and w[0].isalpha())


def page_heading(text: str) -> str:
    """A page's title lines among its first three, skipping rule lines (═══)."""
    lines = [stripped for line in text.splitlines() if (stripped := line.strip(" \t═=─-_*#|"))][:3]
    return "\n".join(line for line in lines if _is_title(line))


def split_sections(pages: list[str], classify: Callable[[str], T], fallback: T, classify_page: Callable[[str], T] | None = None) -> list[tuple[T, int, int]]:
    """Group pages into ``(type, first_page, last_page)`` sections (1-based).

    A page starts a new document only when its title names a different type
    *and* the page as a whole classifies the same way. Titles alone misfire on
    sub-sections ("SCHEDULE B - EXCEPTIONS" inside a title commitment), and
    whole pages alone on passing mentions ("attach loss runs"). Any other
    page continues the current section. ``classify_page`` (default:
    ``classify``) judges the whole page when titles need a different rule.
    A section typed ``fallback`` had no recognisable title — callers classify
    its full text the usual way.
    """
    classify_page = classify_page or classify
    sections: list[tuple[T, int, int]] = []
    for n, text in enumerate(pages, start=1):
        heading = page_heading(text)
        kind = classify(heading) if heading else fallback
        if not sections:
            sections.append((kind, n, n))
            continue
        current, first, _ = sections[-1]
        # an untitled section that already reads as this type is the same document
        same_untitled = current == fallback and classify_page("\n".join(pages[first - 1 : n - 1])) == kind
        if kind not in (fallback, current) and not same_untitled and classify_page(text) == kind:
            sections.append((kind, n, n))
        else:
            sections[-1] = (sections[-1][0], sections[-1][1], n)
    return sections


def pdf_page_texts(data: bytes) -> list[str]:
    try:
        import pdfplumber

        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return [page.extract_text() or "" for page in pdf.pages]
    except Exception:
        return []


def pdf_packet_sections(
    data: bytes,
    filename: str,
    classify: Callable[[str], T],
    fallback: T,
    classify_page: Callable[[str], T] | None = None,
    ocr_text: str = "",
) -> list[tuple[T, int, int, str]]:
    """``(type, first_page, last_page, text)`` per document in a multi-document
    PDF, or ``[]`` when it holds just one. Pages come from the text layer, or
    for a scan from ``ocr_text`` (pages separated by form feeds)."""
    if Path(filename).suffix.lower() != ".pdf":
        return []
    pages = pdf_page_texts(data)
    if not any(p.strip() for p in pages) and "\f" in ocr_text:
        pages = ocr_text.split("\f")
    if len(pages) < 2 or not any(p.strip() for p in pages):
        return []
    sections = split_sections(pages, classify, fallback, classify_page)
    if len(sections) < 2:
        return []
    return [(kind, first, last, "\n".join(pages[first - 1 : last])) for kind, first, last in sections]
