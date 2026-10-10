"""Step 1 — store a submission pack. Synthetic documents only.

Run: python underwriting_pipeline/app/intake.py
Inbox: python underwriting_pipeline/app/intake.py simulation/inbox
"""

import hashlib
import sys
from pathlib import Path
from uuid import uuid4


def intake(files: list[tuple[str, bytes]]) -> dict:
    if not files:
        raise ValueError("submission has no documents")
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
        "synthetic": True,
    }


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
    print("intake ok", rec["submission_id"])
