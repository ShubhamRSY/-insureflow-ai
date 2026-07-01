from __future__ import annotations

import base64
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_ENCRYPTION_PREFIX = "ENC:v1:"


class EnvelopeEncryption:
    """Fernet envelope encryption for audit bundles and sensitive payloads at rest."""

    def __init__(self, key: str | None = None) -> None:
        self._fernet = None
        raw_key = key if key is not None else os.getenv("ENCRYPTION_KEY", "")
        if raw_key:
            self._fernet = self._build_fernet(raw_key)

    @property
    def enabled(self) -> bool:
        return self._fernet is not None

    @staticmethod
    def _build_fernet(key: str) -> Any:
        from cryptography.fernet import Fernet

        if len(key) == 44 and key.endswith("="):
            return Fernet(key.encode())
        # Derive a valid Fernet key from arbitrary secret
        padded = base64.urlsafe_b64encode(key.encode()[:32].ljust(32, b"0"))
        return Fernet(padded)

    @staticmethod
    def generate_key() -> str:
        from cryptography.fernet import Fernet

        return Fernet.generate_key().decode()

    def encrypt_text(self, plaintext: str) -> str:
        if not self._fernet:
            return plaintext
        token = self._fernet.encrypt(plaintext.encode("utf-8"))
        return _ENCRYPTION_PREFIX + token.decode("utf-8")

    def decrypt_text(self, ciphertext: str) -> str:
        if not ciphertext.startswith(_ENCRYPTION_PREFIX):
            return ciphertext
        if not self._fernet:
            raise ValueError("Encrypted data found but ENCRYPTION_KEY is not configured")
        token = ciphertext[len(_ENCRYPTION_PREFIX) :].encode("utf-8")
        return self._fernet.decrypt(token).decode("utf-8")

    def encrypt_json(self, data: dict[str, Any]) -> str:
        return self.encrypt_text(json.dumps(data, default=str, ensure_ascii=False))

    def decrypt_json(self, ciphertext: str) -> dict[str, Any]:
        return json.loads(self.decrypt_text(ciphertext))

    def write_encrypted_file(self, path: str, data: dict[str, Any]) -> None:
        from pathlib import Path

        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = self.encrypt_json(data) if self.enabled else json.dumps(data, indent=2, default=str)
        p.write_text(payload, encoding="utf-8")

    def read_encrypted_file(self, path: str) -> dict[str, Any] | None:
        from pathlib import Path

        p = Path(path)
        if not p.exists():
            return None
        raw = p.read_text(encoding="utf-8")
        if raw.startswith(_ENCRYPTION_PREFIX):
            return self.decrypt_json(raw)
        return json.loads(raw)
