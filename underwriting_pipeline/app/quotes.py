"""T-087 / D-035 — quote tracking: a status per submission and carrier, read from the carrier replies.

Reads simulation/from-carrier/ and simulation/to-carrier/ only; writes neither. Nothing binds.
A subjectivity is open until a listed underwriter logs a closure with a reason (subjectivity_closures.jsonl).
A carrier reply that says "satisfied" is shown as a note; it does not close anything by itself.

# ponytail: line-based parse of the simulated replies; a real carrier feed needs its own parser.

Run: python underwriting_pipeline/app/quotes.py
"""

import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "underwriting_pipeline" / "app"))
import package

FROM_CARRIER = ROOT / "simulation" / "from-carrier"
TO_CARRIER = ROOT / "simulation" / "to-carrier"
CLOSURES = ROOT / "deliverables" / "software-engineer" / "subjectivity_closures.jsonl"
STOP = {"the", "and", "on", "of", "a", "to", "confirm", "fire", "is", "in"}


def _words(text: str) -> set:
    return set(re.findall(r"[a-z]+", text.lower())) - STOP


def _closures(path: Path) -> dict:
    out = {}
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if isinstance(row, dict) and row.get("submission") and row.get("subjectivity"):
                out[(row["submission"], row["carrier"], row["subjectivity"])] = row
    return out


def close_subjectivity(submission: str, carrier: str, subjectivity: str, underwriter_id: str, reason: str, path: Path = None) -> dict:
    """Only a listed underwriter, with a written reason. Appends one row; never edits a reply."""
    path = path or CLOSURES
    if (underwriter_id or "").strip() not in package.underwriters():
        raise ValueError("only an underwriter on the list may close a subjectivity")
    if not (reason or "").strip():
        raise ValueError("closing a subjectivity needs a written reason")
    row = {"submission": submission, "carrier": carrier, "subjectivity": subjectivity, "underwriter_id": underwriter_id.strip(),
           "reason": reason.strip(), "date": date.today().isoformat()}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(row) + "\n")
    return row


def track(from_dir: Path = None, to_dir: Path = None, closures: Path = None) -> list[dict]:
    """One row per (submission, carrier): sent_date, status, premium, deductible, subjectivities [{text, state}], notes."""
    from_dir, to_dir = from_dir or FROM_CARRIER, to_dir or TO_CARRIER
    closed = _closures(closures or CLOSURES)
    rows: dict = {}
    # quotes (they carry a Subjectivities line) first, then follow-ups, each in name order
    files = sorted(from_dir.glob("*.md"), key=lambda p: ("Subjectivities:" not in p.read_text(), p.name)) if from_dir.exists() else []
    for f in files:
        text = f.read_text()
        sub = (re.search(r"^Submission:\s*(\S+)", text, re.M) or [None, ""])[1]
        car = (re.search(r"^Carrier:\s*(\S+)", text, re.M) or [None, ""])[1]
        if not sub or not car:
            continue
        key = (sub, "carrier_" + car.lower())
        row = rows.setdefault(key, {"submission": sub, "carrier": key[1], "status": "", "premium": None, "deductible": None, "subjectivities": [], "notes": [], "replies": []})
        row["replies"].append(f.name)
        for name in ("premium", "deductible"):
            m = re.search(rf"^{name}:\s*(\d+)", text, re.I | re.M)
            if m:
                row[name] = int(m[1])
        first = text.strip().splitlines()[0].strip().upper() if text.strip() else ""
        kind = {"QUOTE": "quoted", "DECLINE": "declined by carrier"}.get(first, "reply needs human reading")  # D-035: read from the reply, never assumed
        if kind != "quoted" or not row["status"]:
            row["status"] = kind
        m = re.search(r"^Subjectivities:\s*(.+)$", text, re.M)
        # only these two exact lines mean none; anything else is shown open (T-020 item e)
        if m and m[1].strip().lower() not in ("none.", "none beyond the file as sent."):
            for item in re.split(r"[;]", m[1].strip().rstrip(".")):
                row["subjectivities"].append({"text": item.strip(), "state": "open"})
        for sentence in re.findall(r"[^.\n]*\bsatisfied\b[^.\n]*\.?", text):
            row["notes"].append(f"{f.name}: carrier reply says \"{sentence.strip()}\"; stays open until an underwriter logs the closure")
    for (sub, car), row in rows.items():
        for s in row["subjectivities"]:
            c = closed.get((sub, car, s["text"]))
            if c:
                s["state"] = "closed"
                s["closed_by"], s["closed_reason"] = c["underwriter_id"], c["reason"]
        open_n = sum(s["state"] == "open" for s in row["subjectivities"])
        if row["status"] == "quoted" and open_n:
            row["status"] = "quoted, subjectivities open"
        pkg = to_dir / f"{sub}.md"
        row["sent_date"] = date.fromtimestamp(pkg.stat().st_mtime).isoformat() if pkg.exists() else "not recorded"
        row["bound"] = False
    return sorted(rows.values(), key=lambda r: (r["submission"], r["carrier"]))


def html_for(submission: str) -> str:
    import html

    mine = [r for r in track() if r["submission"] == submission]
    if not mine:
        return "<h3>Quote tracking</h3><p>No carrier reply on file. Nothing is bound.</p>"
    out = ["<h3>Quote tracking</h3>"]
    for r in mine:
        subs = "; ".join(f"{s['text']} [{s['state']}]" for s in r["subjectivities"]) or "none"
        out.append(f"<p>{html.escape(r['carrier'])}: {html.escape(r['status'])} · sent {html.escape(r['sent_date'])} · premium {r['premium']} · deductible {r['deductible']} · subjectivities: {html.escape(subs)} · not bound</p>")
        out += [f"<p>Note: {html.escape(n)}</p>" for n in r["notes"]]
        for s in r["subjectivities"]:  # D-058: a listed underwriter closes it, one logged action
            if s["state"] == "open":
                f = "".join(f'<input type="hidden" name="{k}" value="{html.escape(v, quote=True)}">' for k, v in (("submission", submission), ("carrier", r["carrier"]), ("subjectivity", s["text"])))
                out.append(f'<form method="post" action="/close-subjectivity">{f}<input name="underwriter_id" placeholder="underwriter id" required> <input name="reason" placeholder="reason" required> <button>Close: {html.escape(s["text"])}</button></form>')
    return "".join(out)


if __name__ == "__main__":
    import tempfile

    before = sorted((p.name, p.stat().st_mtime) for p in FROM_CARRIER.glob("*"))
    rows = {(r["submission"], r["carrier"]): r for r in track()}
    assert sum(len(r['replies']) for r in rows.values()) == 9 and len(rows) == 8 and all(r["bound"] is False for r in rows.values()), len(rows)  # nine replies, SUB-002 has two
    sub2 = rows[("SUB-002", "carrier_b")]
    assert sub2["status"] == "quoted, subjectivities open" and len(sub2["replies"]) == 2
    assert sub2["subjectivities"] == [{"text": "confirm hood and suppression on the inspection", "state": "open"}], sub2["subjectivities"]
    assert sub2["premium"] == 9800 and sub2["deductible"] == 2500 and sub2["notes"]
    assert rows[("SUB-001", "carrier_a")]["status"] == "quoted" and rows[("SUB-001", "carrier_a")]["subjectivities"] == []
    assert rows[("SUB-005", "carrier_c")]["premium"] == 10400
    assert "[open]" in html_for("SUB-002") and "No carrier reply" in html_for("SUB-999")
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "c.jsonl"
        for bad in (("nobody", "x"), ("user", "")):
            try:
                close_subjectivity("SUB-002", "carrier_b", sub2["subjectivities"][0]["text"], *bad, path=log)
                raise SystemExit(f"{bad} must be refused")
            except ValueError:
                pass
        assert not log.exists()
        close_subjectivity("SUB-002", "carrier_b", sub2["subjectivities"][0]["text"], "user", "inspection report seen", path=log)
        again = {(r["submission"], r["carrier"]): r for r in track(closures=log)}[("SUB-002", "carrier_b")]
        assert again["status"] == "quoted" and again["subjectivities"][0]["state"] == "closed"
    with tempfile.TemporaryDirectory() as tmp:  # T-020 item (e): status from the reply, "none" only when exact
        t = Path(tmp); (t / "f").mkdir()
        def reply(name, first, sub, extra=""):
            (t / "f" / name).write_text(f"{first}\nCarrier: A\nSubmission: {sub}\n{extra}\n")
        reply("1.md", "DECLINE", "SUB-777", "We decline; outside appetite.")
        reply("2.md", "MAYBE", "SUB-778", "Premium: 100\nSubjectivities: none.")
        reply("3.md", "QUOTE", "SUB-779", "Subjectivities: none.")
        reply("4.md", "QUOTE", "SUB-780", "Subjectivities: none beyond the file as sent.")
        reply("5.md", "QUOTE", "SUB-781", "Subjectivities: none, subject to inspection.")
        got = {r["submission"]: r for r in track(t / "f", t / "t", t / "none.jsonl")}
        assert got["SUB-777"]["status"] == "declined by carrier" and got["SUB-778"]["status"] == "reply needs human reading"
        assert got["SUB-779"]["status"] == got["SUB-780"]["status"] == "quoted" and not got["SUB-779"]["subjectivities"] and not got["SUB-780"]["subjectivities"]
        assert got["SUB-781"]["status"] == "quoted, subjectivities open" and got["SUB-781"]["subjectivities"][0]["state"] == "open"
    assert before == sorted((p.name, p.stat().st_mtime) for p in FROM_CARRIER.glob("*"))  # read only
    print("quotes ok")
