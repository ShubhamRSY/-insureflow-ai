"""Password-protected uploads (bank statements, payroll, APS, some loss runs).

A locked file can't be parsed, and every extractor used to fall through to
reading the raw encrypted bytes as "text". Loaders call ``is_locked`` to mark
the document instead, and the API calls ``unlock`` when the uploader supplies
the password so everything downstream sees an ordinary file.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

LOCKED_ENGINE = "password_protected"
LOCKED_TEXT = "[Password protected: this file is encrypted and could not be read — re-upload it with its password]"

# Encrypted OOXML (.xlsx/.docx/.pptx) is wrapped in an OLE container instead of a zip;
# legacy .xls/.doc are always OLE, so those need msoffcrypto to tell.
_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_OFFICE_EXTS = frozenset({".xlsx", ".xlsm", ".xls", ".docx", ".doc", ".pptx", ".ppt"})


class WrongPasswordError(ValueError):
    pass


def is_locked(data: bytes, filename: str) -> bool:
    """True when the file can't be opened without a password. A PDF with only
    an owner (permissions) password opens fine, so it doesn't count."""
    ext = Path(filename).suffix.lower()
    try:
        if ext == ".pdf":
            if b"/Encrypt" not in data:
                return False
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            return reader.is_encrypted and not reader.decrypt("")
        if ext in _OFFICE_EXTS and data.startswith(_OLE_MAGIC):
            import msoffcrypto

            return bool(msoffcrypto.OfficeFile(io.BytesIO(data)).is_encrypted())
        if ext == ".zip":
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                return any(info.flag_bits & 0x1 for info in zf.infolist())
    except Exception:
        return False  # unreadable for some other reason — let the normal parsers report it
    return False


def unlock(data: bytes, filename: str, password: str) -> bytes:
    """Return the decrypted file, or ``data`` unchanged if it isn't locked."""
    if not is_locked(data, filename):
        return data
    out = io.BytesIO()
    if Path(filename).suffix.lower() == ".zip":
        with zipfile.ZipFile(io.BytesIO(data)) as zf, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as plain:
            for info in zf.infolist():
                try:
                    plain.writestr(info.filename, zf.read(info, pwd=password.encode()))
                except RuntimeError as exc:  # "Bad password for file"
                    raise WrongPasswordError(f"Wrong password for '{filename}'") from exc
                except NotImplementedError as exc:  # AES-encrypted members
                    raise WrongPasswordError(f"'{filename}' uses AES encryption, which can't be opened here — ask for the files unzipped") from exc
        return out.getvalue()
    if Path(filename).suffix.lower() == ".pdf":
        from pypdf import PdfReader, PdfWriter

        reader = PdfReader(io.BytesIO(data))
        if not reader.decrypt(password):
            raise WrongPasswordError(f"Wrong password for '{filename}'")
        PdfWriter(clone_from=reader).write(out)
        return out.getvalue()

    import msoffcrypto
    from msoffcrypto.exceptions import DecryptionError, InvalidKeyError

    office = msoffcrypto.OfficeFile(io.BytesIO(data))
    try:
        office.load_key(password=password)
        office.decrypt(out)
    except (DecryptionError, InvalidKeyError) as exc:
        raise WrongPasswordError(f"Wrong password for '{filename}'") from exc
    return out.getvalue()
