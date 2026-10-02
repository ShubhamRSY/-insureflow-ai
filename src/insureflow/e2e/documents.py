"""Real files for intake tests and the E2E suite: text-layer PDFs (optionally
password-protected), encrypted Excel, ZIPs, emails, and a fake clamd.

Built in code so the suite needs no binary fixtures in the repo.
"""

from __future__ import annotations

import base64
import io
import socket
import threading
import zipfile
from email.message import EmailMessage

DEFAULT_TEXT = "COMMERCIAL INSURANCE APPLICATION Named Insured: Acme Widgets LLC Total Insured Value: $4,500,000 Annual Revenue: $12,000,000"

LOSS_RUN = ["Hartwell Mutual Insurance", "LOSS RUN REPORT", "Insured: Acme Widgets LLC", "Claim # 10442  DOL 03/14/2023  Slip and fall  Incurred $12,400", "Total Incurred: $12,400"]
LOSS_RUN_CONT = ["Page 2", "Claim # 10518  DOL 08/02/2024  Water damage  Incurred $48,000", "Total Incurred: $60,400"]
SOV = ["SCHEDULE OF VALUES", "Location 1: 100 Main St  Building value $3,200,000  Contents $800,000", "Total insurable value $4,000,000"]
BANK_STATEMENT = ["Business Bank Statement - Checking", "Account holder: Acme Widgets LLC", "Ending balance $41,200"]


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def pdf(user_password: str | None = None, pages: list[list[str]] | None = None, extra_catalog: str = "") -> bytes:
    """A real text-layer PDF, one page per list of lines. ``user_password``
    encrypts it (``""`` = permissions-only: opens without a password)."""
    from pypdf import PdfReader, PdfWriter
    from pypdf.constants import UserAccessPermissions

    pages = pages or [[DEFAULT_TEXT]]
    font = 3 + 2 * len(pages)
    objs = [f"<</Type/Catalog/Pages 2 0 R{extra_catalog}>>", f"<</Type/Pages/Kids[{' '.join(f'{3 + 2 * n} 0 R' for n in range(len(pages)))}]/Count {len(pages)}>>"]
    for n, lines in enumerate(pages):
        stream = "BT /F1 10 Tf 14 TL 40 800 Td " + " T* ".join(f"({line}) Tj" for line in lines) + " ET"
        objs.append(f"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 842]/Contents {4 + 2 * n} 0 R/Resources<</Font<</F1 {font} 0 R>>>>>>")
        objs.append(f"<</Length {len(stream)}>>stream\n{stream}\nendstream")
    objs.append("<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>")
    raw, offsets = "%PDF-1.4\n", []
    for i, body in enumerate(objs, 1):
        offsets.append(len(raw))
        raw += f"{i} 0 obj{body}endobj\n"
    xref = len(raw)
    raw += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n" + "".join(f"{o:010d} 00000 n \n" for o in offsets)
    raw += f"trailer<</Size {len(objs) + 1}/Root 1 0 R>>\nstartxref\n{xref}\n%%EOF"
    writer = PdfWriter(clone_from=PdfReader(io.BytesIO(raw.encode())))
    if user_password is not None:
        writer.encrypt(user_password=user_password, owner_password="owner", permissions_flag=UserAccessPermissions.PRINT, algorithm="AES-128")
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def xlsx(password: str | None = None) -> bytes:
    import msoffcrypto.format.ooxml
    import openpyxl

    wb = openpyxl.Workbook()
    sheet = wb.active
    assert sheet is not None
    sheet.append(["Location", "TIV"])
    sheet.append(["1 Main St", 4500000])
    plain = io.BytesIO()
    wb.save(plain)
    if password is None:
        return plain.getvalue()
    plain.seek(0)
    out = io.BytesIO()
    msoffcrypto.format.ooxml.OOXMLFile(plain).encrypt(password, out)
    return out.getvalue()


def zip_of(files: dict[str, bytes]) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as zf:
        for name, body in files.items():
            zf.writestr(name, body)
    return out.getvalue()


def email_with(attachments: dict[str, bytes], body: str = "Submission attached.") -> bytes:
    msg = EmailMessage()
    msg["Subject"] = "New submission - Acme Widgets"
    msg["From"] = "broker@example.com"
    msg.set_content(body)
    for name, data in attachments.items():
        msg.add_attachment(data, maintype="application", subtype="octet-stream", filename=name)
    return msg.as_bytes()


def fake_clamd(reply: bytes) -> int:
    """A one-shot clamd stand-in speaking INSTREAM; returns its port."""
    srv = socket.create_server(("127.0.0.1", 0))

    def serve() -> None:
        conn, _ = srv.accept()
        with conn:
            buf = b""
            while not buf.endswith(b"\0\0\0\0"):  # a zero-length chunk ends the stream
                chunk = conn.recv(65536)
                if not chunk:
                    break
                buf += chunk
            conn.sendall(reply)
        srv.close()

    threading.Thread(target=serve, daemon=True).start()
    return int(srv.getsockname()[1])
