"""Step 6 — one page of the queue. Does not bind and does not send to a carrier.

The React workbench in frontend/ is a different app and is not modified.

# ponytail: stdlib HTML plus one JSONL log. Split the page when a second screen exists.

Run: python underwriting_pipeline/app/workbench.py
Serve: python underwriting_pipeline/app/workbench.py --serve
"""

import html
import json
import os
import sys
import threading
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "underwriting_pipeline" / "ai"))
sys.path.insert(0, str(ROOT / "underwriting_pipeline" / "models"))
sys.path.insert(0, str(ROOT / "underwriting_pipeline" / "app"))
import package
import points
import prepare

INBOX = ROOT / "simulation" / "inbox"
PAGE = Path(__file__).resolve().parent / "workbench.html"
LOG = package.DECISIONS_LOG
_LOG_LOCK = threading.Lock()  # ponytail: one process writes the log; a file lock if a second writer appears


def _ops(report: dict) -> str:
    for row in report["fields"]:
        if row["field_id"] == "operations" and row["value"]:
            return row["value"].lower()
    return ""


def route(report: dict) -> str:
    ops = _ops(report)
    if any(word in ops for word in ("bar", "nightclub", "firework", "explosive")):
        return "no_match"
    if not report["complete"]:
        return "hold"
    if any(word in ops for word in ("habitational", "apartment", "flats")):
        if report.get("sprinklers") == "yes" or "sprinklers yes" in ops or "sprinklered" in ops:
            return "carrier_c"
        return "hold"
    if any(word in ops for word in ("restaurant", "taco", "kitchen", "contractor", "painting")):
        return "carrier_b"
    if any(word in ops for word in ("office", "retail", "wholesale")):
        return "carrier_a"
    return "hold"


def facts(report: dict) -> dict:
    by = {row["field_id"]: (row["value"] or "") for row in report["fields"]}
    ops = by.get("operations", "").lower()
    tiv = "".join(ch for ch in by.get("tiv_building", "") if ch.isdigit())
    return {
        "restaurant": any(word in ops for word in ("restaurant", "taco", "kitchen")),
        "cooking": any(word in ops for word in ("fryer", "restaurant", "taco", "kitchen")),
        "habitational": any(word in ops for word in ("habitational", "apartment", "flats")),
        "contracting": "contractor" in ops or "painting" in ops,
        "construction": by.get("construction", "").lower(),
        "tiv": int(tiv) if tiv else 0,
    }


def snippet(folder: Path, row: dict) -> str:
    source = row.get("source")
    if not source or row.get("start") is None:
        return ""
    path = folder / source
    if not path.is_file():
        return ""
    text = path.read_text()
    return text[row["start"] : row["end"]]


def load_queue(only: str | None = None) -> list[dict]:
    folders = sorted(p for p in INBOX.iterdir() if p.is_dir() and p.name.startswith("SUB-"))
    if only:
        folders = [folder for folder in folders if folder.name == only]
    rows = []
    for folder in folders:
        report = prepare.process_submission(folder)
        files = sorted(p.name for p in folder.iterdir() if p.is_file())
        ignored = [name for name in files if not name.endswith((".md", ".csv"))]
        rows.append(
            {
                "id": folder.name,
                "report": report,
                "files": files,
                "ignored": ignored,
                "route": route(report),
                "score": points.score(facts(report)),
                "snippets": {row["field_id"]: snippet(folder, row) for row in report["fields"]},
            }
        )
    return rows


def ai_version() -> str:
    model = os.environ.get("LLM_MODEL") or "local-default"
    return model + "+rules-d015"


def correction_counts(log_path: Path) -> dict:
    counts = {"approve": 0, "edit": 0, "decline": 0}
    if not log_path.exists():
        return counts
    for line in log_path.read_text().splitlines():
        if not line.strip():
            continue
        action = json.loads(line).get("action")
        if action in counts:
            counts[action] += 1
    return counts


def record_decision(payload: dict, log_path: Path) -> dict:
    actor = (payload.get("underwriter_id") or "").strip()
    action = (payload.get("action") or "").strip()
    reason = (payload.get("reason") or "").strip()
    if not actor:
        raise ValueError("underwriter id required")
    if actor not in package.underwriters():
        raise ValueError("only an id on underwriters.json may log a decision (D-055); AI roles never count")
    if action not in {"approve", "edit", "decline"}:
        raise ValueError("action must be approve, edit, or decline")
    if action in {"edit", "decline"} and not reason:
        raise ValueError("edit and decline require a reason")
    if action == "approve":
        submission = (payload.get("submission") or "").strip()
        # T-071: read the file's status from the last saved run itself. An approve is refused on either
        # refused status, and when nothing is saved or the run cannot be read (current_status raises).
        status = prepare.current_status(submission)
        if status in prepare.REFUSED_STATUSES:
            raise ValueError(f"this file's status is {status}; an approve is refused for it")
    with _LOG_LOCK:
        if action == "approve" and not reason:
            # D-053: an approve after a decline needs a written reason; refused here, not only at the send.
            if any(r.get("action") == "decline" for r in package.decisions(submission, log_path)):
                raise ValueError("an approve after a decline needs a written reason")
        return _append(payload, action, actor, reason, log_path)


def _append(payload: dict, action: str, actor: str, reason: str, log_path: Path) -> dict:
    """D-055: every entry gets the next sequence number in the log; the highest seq is the latest decision."""
    last = 0
    if log_path.exists():
        for line in log_path.read_text().splitlines():
            try:
                seq = json.loads(line).get("seq")
            except (ValueError, AttributeError):
                continue
            if isinstance(seq, int) and not isinstance(seq, bool):
                last = max(last, seq)
    row = {
        "seq": last + 1,
        "submission": payload.get("submission"),
        "action": action,
        "underwriter_id": actor,
        "reason": reason,
        "date": date.today().isoformat(),
        "ai_version": ai_version(),
        "bound": False,
        "sent_to_carrier": False,
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a") as handle:
        handle.write(json.dumps(row) + "\n")
    return row


def _confidence(row: dict) -> str:
    used = row.get("confidence", "")
    model = row.get("model_confidence")
    if model is None or model == used:
        return str(used)
    return f"{used} ocr / {model} model"


def render(queue: list[dict], counts: dict | None = None) -> str:
    counts = counts or {"approve": 0, "edit": 0, "decline": 0}
    corrections = counts["edit"] + counts["decline"]
    blocks = []
    for item in queue:
        report = item["report"]
        refused = report.get("status") in prepare.REFUSED_STATUSES
        field_rows = []
        for row in report["fields"]:
            field_rows.append(
                "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                    html.escape(row["field_id"]),
                    html.escape(row["value"] or "—"),
                    html.escape(_confidence(row)),
                    html.escape(row.get("source") or "—"),
                    html.escape(item["snippets"].get(row["field_id"]) or "—"),
                )
            )
        conflicts = report["conflicts"] or []
        conflict_html = "<p>No stored conflict.</p>"
        if conflicts:
            conflict_html = "<ul>" + "".join(
                "<li>{}: {}</li>".format(
                    html.escape(item_c["field"]),
                    html.escape(json.dumps(item_c["values"])),
                )
                for item_c in conflicts
            ) + "</ul>"
        address_check = "—"
        for row in report["fields"]:
            if row["field_id"] == "premises_address":
                address_check = row.get("address_check") or "—"
        extraction = "ok"
        if report.get("status") == "extraction_failed":
            extraction = f"FAILED — {report['error']}. No field was read. This is not a missing-data file. Sends are blocked."
        elif report.get("status") == "all_values_rejected":
            reason = report.get("status_reason") or "every value was rejected by the gate"
            extraction = f"REJECTED — {reason}. No field was accepted. This is not a missing-data file. Sends are blocked."
        lines = [
            f"<h2>{html.escape(item['id'])}</h2>",
            f"<p>Files: {html.escape(', '.join(item['files']) or 'none')}</p>",
            f"<p>Not read by extraction: {html.escape(', '.join(item['ignored']) or 'none')}</p>",
        ]
        if not refused:
            lines += [
                f"<p>Score: {item['score']['points']} · {html.escape(', '.join(item['score']['reason_codes']) or 'none')} · not a price</p>",
                f"<p>Carrier match: {html.escape(item['route'])} · recommendation only</p>",
            ]
        lines += [
            f"<p>Extraction: {html.escape(extraction)}</p>",
            f"<p>Needs human read: {html.escape(', '.join(report.get('needs_human') or []) or 'none')}</p>",
            f"<p>Address check: {html.escape(address_check)}</p>",
            f"<p>Locations: {html.escape('; '.join(('primary ' if row.get('primary') else 'other ') + row['address'] for row in report.get('locations') or []) or 'one premises')}</p>",
            "<h3>Extracted fields</h3>",
            f"<table><tr><th>Field</th><th>Value</th><th>Confidence</th><th>Source</th><th>Cited text</th></tr>{''.join(field_rows)}</table>",
            f"<h3>Conflicts</h3>{conflict_html}",
        ]
        if not refused:
            missing = report["missing"] + report.get("extra", [])
            lines += ["<h3>Missing</h3>", f"<p>{html.escape(', '.join(missing) or 'none')}</p>"]
        # T-071: on a refused card there is no approve option. Edit and decline stay so a person decides.
        options = "<option>edit</option><option>decline</option>" if refused else "<option>approve</option><option>edit</option><option>decline</option>"
        lines.append(
            f"""<form method="post" action="/decision">
<input type="hidden" name="submission" value="{html.escape(item['id'])}">
<label>Underwriter id <input name="underwriter_id" required></label>
<label>Action
<select name="action">{options}</select>
</label>
<label>Reason <input name="reason"></label>
<button type="submit">Record decision</button>
</form>"""
        )
        blocks.append(
            f'<article id="{html.escape(item["id"])}">\n' + "\n".join(lines) + "\n</article>"
        )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Underwriter workbench</title>
<style>
body {{ font: 15px/1.4 sans-serif; margin: 2rem; }}
article {{ border-top: 1px solid #ccc; padding: 1rem 0; }}
table {{ border-collapse: collapse; }}
td, th {{ border: 1px solid #ddd; padding: 0.3rem 0.5rem; text-align: left; }}
</style></head><body>
<h1>Underwriter workbench</h1>
<p>Synthetic queue. A decision is logged only with an id on the underwriter list. Decline and edit need a reason, and so does an approve after a decline. Approve, edit, and decline are saved with that reason. This page does not bind and does not send a carrier package.</p>
<p>Decisions so far: {counts['approve']} approved, {counts['edit']} edited, {counts['decline']} declined. Corrections: {corrections}.</p>
{''.join(blocks)}
</body></html>
"""


def serve(port: int = 8765, only: str | None = None) -> None:
    page = render(load_queue(only), correction_counts(LOG))
    PAGE.write_text(page)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = PAGE.read_text().encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            if self.path != "/decision":
                self.send_error(404)
                return
            size = int(self.headers.get("Content-Length", "0"))
            payload = {k: v[0] for k, v in parse_qs(self.rfile.read(size).decode()).items()}
            try:
                record_decision(payload, LOG)
            except ValueError as exc:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(str(exc).encode())
                return
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()

    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    import tempfile

    if "--serve" in sys.argv:
        chosen = next((arg for arg in sys.argv if arg.startswith("SUB-")), None)
        serve(only=chosen)
    else:
        def save(ext: Path, submission: str, status: str) -> None:
            """A saved run shaped like prepare.write_drafts() writes, no model call. The hash is the reader's."""
            payload = {
                "submission": submission,
                "status": status,
                "error": "model call failed: HTTP 429 rate limit" if status == "extraction_failed" else None,
                "complete": status == "complete",
                "conflicts": [],
                "needs_human": [],
                "sprinklers": None,
                "fields": [],
            }
            payload["hash_algorithm"] = prepare.HASH_ALGORITHM
            payload["saved_hash"] = prepare.hash_payload(payload)
            ext.mkdir(parents=True, exist_ok=True)
            (ext / f"{submission}.json").write_text(json.dumps(payload))

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            check = tmp / "decisions.jsonl"
            ext = tmp / "extractions"
            saved_dir = prepare.EXTRACT_DIR
            prepare.EXTRACT_DIR = ext
            try:
                try:
                    record_decision({"action": "decline"}, check)
                    raise SystemExit("missing id should fail")
                except ValueError:
                    pass
                try:
                    record_decision(
                        {"underwriter_id": "UW-001", "action": "decline", "submission": "SUB-000"},
                        check,
                    )
                    raise SystemExit("decline without reason should fail")
                except ValueError:
                    pass

                # T-071 (4): an approve with nothing saved is refused.
                try:
                    record_decision(
                        {"underwriter_id": "UW-001", "action": "approve", "submission": "SUB-000", "reason": "self-check"},
                        check,
                    )
                    raise SystemExit("an approve with no saved run should fail")
                except ValueError:
                    pass

                # A normal file: the approve is recorded.
                save(ext, "SUB-000", "complete")
                record_decision(
                    {
                        "underwriter_id": "UW-001",
                        "action": "approve",
                        "submission": "SUB-000",
                        "reason": "self-check",
                    },
                    check,
                )
                logged = json.loads(check.read_text().splitlines()[-1])

                # T-071 (4): an approve is refused on either refused status; edit and decline are still recorded.
                for sub, status in (("SUB-010", "extraction_failed"), ("SUB-011", "all_values_rejected")):
                    save(ext, sub, status)
                    try:
                        record_decision(
                            {"underwriter_id": "UW-001", "action": "approve", "submission": sub, "reason": "self-check"},
                            check,
                        )
                        raise SystemExit(f"an approve on {status} should fail")
                    except ValueError:
                        pass
                    record_decision(
                        {"underwriter_id": "UW-001", "action": "edit", "submission": sub, "reason": "corrected by hand"},
                        check,
                    )
                    record_decision(
                        {"underwriter_id": "UW-001", "action": "decline", "submission": sub, "reason": "not bindable as read"},
                        check,
                    )
                record_decision(
                    {"underwriter_id": "UW-001", "action": "edit", "submission": "SUB-000", "reason": "square feet were 4500"},
                    check,
                )
                assert correction_counts(check) == {"approve": 1, "edit": 3, "decline": 2}, correction_counts(check)

                # D-055: seq rises by one per entry; an unlisted id or an AI role cannot log.
                seqs = [json.loads(line)["seq"] for line in check.read_text().splitlines()]
                assert seqs == list(range(1, len(seqs) + 1)), seqs
                for who in ("UW-999", "senior-underwriter", "@compliance"):
                    try:
                        record_decision({"underwriter_id": who, "action": "edit", "submission": "SUB-000", "reason": "x"}, check)
                        raise SystemExit(f"{who} should not be able to log")
                    except ValueError:
                        pass

                # D-053: an approve after a decline needs a written reason at the workbench.
                save(ext, "SUB-012", "complete")
                record_decision({"underwriter_id": "user", "action": "decline", "submission": "SUB-012", "reason": "first look"}, check)
                try:
                    record_decision({"underwriter_id": "user", "action": "approve", "submission": "SUB-012"}, check)
                    raise SystemExit("an approve after a decline without a reason should fail")
                except ValueError:
                    pass
                record_decision({"underwriter_id": "user", "action": "approve", "submission": "SUB-012", "reason": "loss runs arrived"}, check)
                assert package.decisions("SUB-012", check)[-1]["action"] == "approve"
            finally:
                prepare.EXTRACT_DIR = saved_dir

        # T-071 (3): the refused card hides approve, Missing, the carrier match, and the score.
        def card(status: str, status_reason: str | None = None, needs_human=None, fields=None) -> dict:
            return {
                "id": f"SUB-{status}",
                "report": {
                    "status": status,
                    "status_reason": status_reason,
                    "error": "model call failed: HTTP 429 rate limit" if status == "extraction_failed" else None,
                    "complete": status == "complete",
                    "fields": fields or [{"field_id": "operations", "value": None}],
                    "conflicts": [],
                    "needs_human": needs_human or [],
                    "missing": ["named_insured"],
                    "extra": [],
                    "locations": [],
                },
                "files": ["application.md"],
                "ignored": [],
                "route": "hold",
                "score": {"points": 12, "reason_codes": ["COOKING"]},
                "snippets": {},
            }

        for item in (
            card("extraction_failed"),
            card("all_values_rejected", status_reason=prepare.REJECT_REASON, needs_human=["scan.jpg"]),
        ):
            page = render([item], {"approve": 0, "edit": 0, "decline": 0})
            assert "<option>approve</option>" not in page
            assert "<h3>Missing</h3>" not in page
            assert "Carrier match:" not in page
            assert "Score:" not in page
            assert "<option>edit</option>" in page and "<option>decline</option>" in page
        assert "REJECTED" in render([card("all_values_rejected", status_reason=prepare.REJECT_REASON)], None)
        normal = card("complete", fields=[{"field_id": "operations", "value": "accounting office"}])
        normal["report"]["missing"] = []
        page_ok = render([normal], None)
        assert "<option>approve</option>" in page_ok
        assert "<h3>Missing</h3>" in page_ok and "Carrier match:" in page_ok and "Score:" in page_ok

        assert logged["sent_to_carrier"] is False
        assert logged["reason"] == "self-check"
        assert logged["ai_version"].endswith("+rules-d015")
        fake = {
            "complete": True,
            "fields": [{"field_id": "operations", "value": "bookkeeping office, no cooking"}],
        }
        assert route(fake) == "carrier_a"
        held = {
            "complete": True,
            "sprinklers": "no",
            "fields": [{"field_id": "operations", "value": "habitational, 8 units, no commercial cooking"}],
        }
        ready = dict(held)
        ready["sprinklers"] = "yes"
        assert route(held) == "hold"
        assert route(ready) == "carrier_c"
        assert "COOKING" not in points.score(facts(fake))["reason_codes"]
        print("workbench ok")
