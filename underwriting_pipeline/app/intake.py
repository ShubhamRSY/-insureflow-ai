"""Step 1 — store a submission pack. Synthetic documents only.

Run: python underwriting_pipeline/app/intake.py
Inbox: python underwriting_pipeline/app/intake.py simulation/inbox
"""

import hashlib
import io
import sys
import zipfile
from email import message_from_bytes, policy
from email.message import EmailMessage
from pathlib import Path
from typing import cast
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))  # T-122 (D-138): this worktree's main-app helpers
from insureflow.ingestion.intake import MAX_EXPANDED_BYTES, _email_attachments, _zip_members  # noqa: E402

ARCHIVES = {".zip", ".eml", ".msg"}


def _unsafe(name: str) -> bool:
    parts = name.replace("\\", "/").split("/")
    return name.startswith(("/", "\\")) or ".." in parts or ":" in parts[0] or "\0" in name


def _email_body(name: str, blob: bytes) -> tuple[str, bytes]:
    msg = cast(EmailMessage, message_from_bytes(blob, policy=policy.default))  # type: ignore[arg-type]
    body = msg.get_body(preferencelist=("plain", "html"))
    head = "".join(f"{k}: {msg[k]}\n" for k in ("From", "To", "Subject", "Date") if msg[k])
    return Path(name).with_suffix(".txt").name, (head + "\n" + (body.get_content() if body else "")).encode()


def _declared_size(blob: bytes) -> int:
    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            return sum(i.file_size for i in zf.infolist())
    except zipfile.BadZipFile:
        return 0


def unpack(files: list[tuple[str, bytes]]) -> tuple[list[tuple[str, bytes]], list[dict]]:
    """D-138 C: a .zip or .eml is replaced by what is inside it (one level). The main app's ZIP and email readers do the unpacking.

    Refused with a reason: password-protected or oversize zip, an unsafe file name (.., absolute path), an archive inside an archive.
    A container with any refusal is also kept whole, so the reader lists it as not read.
    """
    out: list[tuple[str, bytes]] = []
    refused: list[dict] = []
    taken: set[str] = set()

    def add(name: str, blob: bytes) -> None:
        while name in taken:
            name = "dup-" + name
        taken.add(name)
        out.append((name, blob))

    for name, blob in files:
        ext = Path(name).suffix.lower()
        if ext not in ARCHIVES:
            add(name, blob)
            continue
        if len(blob) > MAX_EXPANDED_BYTES or (ext == ".zip" and _declared_size(blob) > MAX_EXPANDED_BYTES):  # Q4: refused before any member is read into memory
            refused.append({"file": name, "reason": "too large (over 500 MB unpacked): not opened"})
            add(name, blob)
            continue
        if ext == ".zip":
            members = _zip_members(blob, [MAX_EXPANDED_BYTES])
            if members is None:
                refused.append({"file": name, "reason": "zip is password-protected, damaged, or too large: not opened"})
                add(name, blob)
                continue
            inner = members
        else:
            body_name, body_blob = _email_body(name, blob)
            add(f"{name}/{body_name}", body_blob)
            inner = _email_attachments(blob, name)
        bad = False
        for member, body in inner:
            if _unsafe(member):
                refused.append({"file": f"{name}/{member}", "reason": "unsafe file name (path outside the submission): not opened"})
                bad = True
            elif Path(member).suffix.lower() in ARCHIVES:
                refused.append({"file": f"{name}/{member}", "reason": "archive inside an archive: not opened"})
                bad = True
            elif len(body) > MAX_EXPANDED_BYTES:
                refused.append({"file": f"{name}/{member}", "reason": "too large (over 500 MB): not opened"})
                bad = True
            else:
                add(f"{name}/{member}", body)
        if bad:
            add(name, blob)
    return out, refused


def intake(files: list[tuple[str, bytes]]) -> dict:
    if not files:
        raise ValueError("submission has no documents")
    files, refused = unpack(files)
    docs = []
    for name, blob in files:
        if not name or blob is None:
            raise ValueError("document needs a name and bytes")
        docs.append(
            {
                "filename": name,
                "sha256": hashlib.sha256(blob).hexdigest(),
                "size": len(blob),
            }
        )
    return {
        "submission_id": str(uuid4()),
        "documents": docs,
        "refused": refused,
        "synthetic": True,
    }


def unpack_folder(folder: Path, dest: Path) -> tuple[list[dict], dict[str, str]]:
    """D-138 C: copy a submission folder into dest (a temp dir, never the inbox) with zips and emails unpacked, so read_folder(dest) reads
    the inner files. Returns the refusals and {file name in dest: name to show, e.g. "pack.zip/loss-runs.pdf"}."""
    files, refused = unpack([(p.name, p.read_bytes()) for p in sorted(folder.iterdir()) if p.is_file() and not p.name.startswith(".")])
    dest.mkdir(parents=True, exist_ok=True)
    shown = {}
    for name, blob in files:
        safe = name.replace("/", "__")
        (dest / safe).write_bytes(blob)
        shown[safe] = name
    return refused, shown


def scan_inbox(root: str) -> list[dict]:
    inbox = Path(root)
    found = []
    for folder in sorted(p for p in inbox.iterdir() if p.is_dir() and p.name.startswith("SUB-")):
        files = [
            (path.name, path.read_bytes())
            for path in sorted(folder.iterdir())
            if path.is_file()
        ]
        record = intake(files)
        record["folder"] = folder.name
        found.append(record)
    return found


if __name__ == "__main__":
    if len(sys.argv) == 2:
        for record in scan_inbox(sys.argv[1]):
            names = ", ".join(doc["filename"] for doc in record["documents"])
            print(f"{record['folder']} {record['submission_id']} files={names}")
        raise SystemExit(0)
    try:
        intake([])
        raise SystemExit("empty pack should fail")
    except ValueError:
        pass
    rec = intake([("acord.txt", b"named_insured: Example LLC\n")])
    assert rec["synthetic"] is True
    assert len(rec["submission_id"]) > 0
    assert rec["documents"][0]["sha256"] == hashlib.sha256(
        b"named_insured: Example LLC\n"
    ).hexdigest()
    # D-138 C
    import io
    import zipfile

    def zipped(**members):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            for member, body in members.items():
                zf.writestr(member.replace("__", "/"), body)
        return buf.getvalue()

    inner = zipped(**{"a.txt": b"A", "dir__b.md": b"B"})
    got = intake([("pack.zip", inner)])
    assert [d["filename"] for d in got["documents"]] == ["pack.zip/a.txt", "pack.zip/dir/b.md"] and got["refused"] == [], got
    bad = intake([("pack.zip", zipped(**{"__etc__passwd": b"x", "ok.txt": b"A"}))])
    assert "unsafe file name" in bad["refused"][0]["reason"] and "pack.zip/ok.txt" in [d["filename"] for d in bad["documents"]], bad
    assert "pack.zip" in [d["filename"] for d in bad["documents"]], "a container with a refusal is kept whole"
    nested = intake([("pack.zip", zipped(**{"in.zip": inner, "ok.txt": b"A"}))])
    assert nested["refused"][0]["reason"] == "archive inside an archive: not opened" and "pack.zip/in.zip/a.txt" not in [d["filename"] for d in nested["documents"]], nested
    eml = (b"From: a@x.com\nTo: b@x.com\nSubject: Quote\nMIME-Version: 1.0\nContent-Type: multipart/mixed; boundary=B\n\n--B\nContent-Type: text/plain\n\nHello body\n"
           b"--B\nContent-Type: text/plain; name=\"loss.txt\"\nContent-Disposition: attachment; filename=\"loss.txt\"\n\nlosses\n--B--\n")
    mail = intake([("mail.eml", eml)])
    assert [d["filename"] for d in mail["documents"]] == ["mail.eml/mail.txt", "mail.eml/loss.txt"] and mail["refused"] == [], mail
    locked = io.BytesIO()
    with zipfile.ZipFile(locked, "w") as zf:
        zf.writestr(zipfile.ZipInfo("s.txt"), b"x")
    raw = bytearray(locked.getvalue())
    raw[raw.index(b"PK\x03\x04") + 6] |= 1  # encrypted flag
    raw[raw.rindex(b"PK\x01\x02") + 8] |= 1
    assert intake([("lock.zip", bytes(raw))])["refused"][0]["reason"].startswith("zip is password-protected"), "locked zip is refused"
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        src, dst = Path(tmp) / "src", Path(tmp) / "dst"
        src.mkdir()
        (src / "pack.zip").write_bytes(inner)
        refused_, shown_ = unpack_folder(src, dst)
        assert refused_ == [] and sorted(shown_.values()) == ["pack.zip/a.txt", "pack.zip/dir/b.md"] and sorted(p.name for p in dst.iterdir()) == sorted(shown_), shown_
    big = zipped(**{"a.txt": b"A"})
    import intake as _self

    saved_cap = _self.MAX_EXPANDED_BYTES
    _self.MAX_EXPANDED_BYTES = 0  # Q4: declared size over the cap refuses before any member is read
    try:
        assert "too large" in _self.intake([("pack.zip", big)])["refused"][0]["reason"]
    finally:
        _self.MAX_EXPANDED_BYTES = saved_cap
    print("intake ok", rec["submission_id"])
