"""Step 7 — carrier package.

The send reads the file's current status from the last saved extraction run
itself; it takes no report from the caller (T-071, item (b) of the T-020 veto).
A file whose status is extraction_failed or all_values_rejected is never sent,
for any actor including the user. The account manager can send only when the
agency rules pass, and must write a reason. No AI role can send.
Every other block keeps the user's override (D-017).

T-079 / D-053: a carrier send also reads the decision log itself and refuses
unless the latest logged decision for the submission is approve, for every
actor. An approve after a decline needs a written reason on that approve row.
The whole history stays in the log; nothing here edits it. No decision is
passed in by the caller, and the caller cannot choose the log: the send always
reads DECISIONS_LOG. D-055: "last" is the highest sequence number (`seq`) in
that one log, never a timestamp; only ids in underwriters.json count, and AI
roles never count. A row with no integer seq, a repeated seq, or an id not on
the list is not a decision.

T-085 / D-056: the package body is built here from the saved reviewed run (hash-checked), the cited text,
the underwriter's logged edits (an edit row stores field_id and new_value), and the carrier named by
workbench.route() on that edited file. The caller supplies no body. A package with an empty required
field, or with no carrier named, is refused for every actor. It is labeled SYNTHETIC.
T-086 / D-056: an actor "user" must pass the user's exact line "send to carrier SUB-###" for this
submission. It is checked after every other gate, so it opens none of them, and it is logged to SENDS_LOG.

# ponytail: one markdown file per submission. Quote tracking is the from-carrier reply, add a tracker when a carrier answers.

Run: python underwriting_pipeline/app/package.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# B-169: the status reader lives in prepare.py. Reach it the same way workbench.py does.
sys.path.insert(0, str(ROOT / "underwriting_pipeline" / "ai"))
import prepare

DECISIONS_LOG = ROOT / "deliverables" / "software-engineer" / "decisions.jsonl"
SENDS_LOG = ROOT / "deliverables" / "software-engineer" / "sends.jsonl"  # not DECISIONS_LOG: a send row must never read as a decision
INBOX = ROOT / "simulation" / "inbox"
UNDERWRITERS = Path(__file__).resolve().parent / "underwriters.json"
AI_ROLES = {p.stem for p in (ROOT / ".claude" / "agents").glob("*.md")} | {"ai-engineer"}


def underwriters() -> set[str]:
    """D-055: the ids that count as an underwriter. Refuses the file if it lists an AI role."""
    ids = {(u.get("id") or "").strip() for u in json.loads(UNDERWRITERS.read_text())["underwriters"]}
    ids.discard("")
    ai = {i for i in ids if i.lstrip("@") in AI_ROLES}
    if ai:
        raise ValueError(f"underwriters.json lists AI roles, which never count: {sorted(ai)}")
    return ids


def decisions(submission: str, log_path: Path) -> list[dict]:
    """D-055: this file's decisions by a listed underwriter, in seq order. Raises on a repeated seq (fail closed)."""
    allowed = underwriters()
    rows = []
    if log_path.exists():
        for line in log_path.read_text().splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue  # a bad line is never a decision
            if not isinstance(row, dict) or (row.get("submission") or "").strip() != submission:
                continue
            seq = row.get("seq")
            if isinstance(seq, int) and not isinstance(seq, bool) and (row.get("underwriter_id") or "").strip() in allowed:
                rows.append(row)
    rows.sort(key=lambda r: r["seq"])
    if len({r["seq"] for r in rows}) != len(rows):
        raise ValueError("the decision log repeats a sequence number for this file; no latest decision can be read")
    return rows


def _edits(submission: str) -> dict:
    """The latest logged edit per field (highest seq) by a listed underwriter. Only edit rows with field_id and new_value count."""
    out = {}
    for row in decisions(submission, DECISIONS_LOG):
        field, value = (row.get("field_id") or "").strip(), (row.get("new_value") or "").strip()
        if (row.get("action") or "").strip() == "edit" and field and value:
            out[field] = row
    return out


def reviewed(submission: str) -> dict:
    """The saved run (G2, hash-checked) with the underwriter's edits applied. Fields are all of prepare.FIELDS."""
    run = prepare.read_saved_run(submission)
    edits = _edits(submission)
    fields = []
    by_id = {r.get("field_id"): r for r in run.get("fields") or []}
    for field_id in prepare.FIELDS:
        row = dict(by_id.get(field_id) or {"field_id": field_id, "value": None})
        if field_id in edits:
            row["edited_by"], row["edit_reason"] = edits[field_id]["underwriter_id"], edits[field_id].get("reason", "")
            row["original_value"], row["value"] = row.get("value"), edits[field_id]["new_value"].strip()
        fields.append(row)
    return {**run, "fields": fields, "complete": all((r.get("value") or "").strip() for r in fields)}


CARRIERS = {"carrier_a", "carrier_b", "carrier_c"}
OVERRIDE_LABEL = "Outside matched appetite — placed by underwriter override"


def build_package(submission: str, carrier_override: str = "", override_reason: str = "") -> str:
    """T-085: the whole body comes from the saved run, the log and route(). Refuses an empty required field or no carrier.

    D-057: carrier_override is honoured only when route() gives no_match (never hold), with a written reason.
    """
    submission = (submission or "").strip()
    report = reviewed(submission)
    empty = [r["field_id"] for r in report["fields"] if not (r.get("value") or "").strip()]
    if empty:
        raise ValueError(f"required field empty: {', '.join(empty)}")
    carrier, label = _route(report), ""
    chosen = (carrier_override or "").strip().lower()
    if chosen:  # D-057 item 1
        if carrier != "no_match" or not _overridable(report):
            raise ValueError(f"a carrier override is allowed only on an overridable no_match (match is {carrier})")
        if chosen not in CARRIERS:
            raise ValueError(f"the override must name carrier_a, carrier_b or carrier_c, not {chosen!r}")
        if not (override_reason or "").strip():
            raise ValueError("a carrier override needs a written reason")
        carrier, label = chosen, f"{OVERRIDE_LABEL}\nOverride reason: {override_reason.strip()}\n"
    elif carrier not in CARRIERS:
        raise ValueError(f"no carrier is named for this file (match is {carrier})")
    from workbench import snippet

    lines = []
    for r in report["fields"]:
        cite = f"{r.get('source')} [{r.get('start')}:{r.get('end')}]" if r.get("source") else "no citation"
        text = snippet(INBOX / submission, r)
        cite += f' "{text.strip()}"' if text.strip() else ""
        if "edited_by" in r:
            cite = f"EDITED by {r['edited_by']} (was: {r['original_value'] or 'empty'}; reason: {r['edit_reason']}); original citation: {cite}"
        lines.append(f"- {r['field_id']}: {r['value']}\n  Citation: {cite}")
    return (
        f"Package {submission}\n"
        "SYNTHETIC: test data, not a real submission.\n"
        "Nothing has been declined. Nothing has been bound.\n"
        "The underwriter has not been replaced by this file.\n\n"
        f"Carrier: {carrier}\n{label}"
        f"Sprinklers: {report.get('sprinklers') or 'not stated'}\n\n"
        "Fields:\n" + "\n".join(lines) + "\n"
    )


def _actor(actor: str) -> str:
    return (actor or "").strip().lstrip("@").lower().replace(" ", "-")


def _route(report: dict) -> str:
    from workbench import route

    return route(report)


def _overridable(report: dict) -> bool:
    from workbench import match

    return match(report)["overridable"]  # D-060: only the no_match cases it names, never hold or senior referral


def _submission_of(target) -> str:
    """The id to read. A caller passes the id, or the saved run that prepare.approve() already read."""
    if isinstance(target, dict):
        target = target.get("submission")
    return target.strip() if isinstance(target, str) else ""


def _decision_problem(submission: str) -> str:
    """Empty string if the latest logged decision is approve (D-053, D-055). Reads the one real log; takes nothing from the caller."""
    rows = decisions(submission, DECISIONS_LOG)
    if not rows:
        return "no logged decision by a listed underwriter for this file"
    last = rows[-1]  # highest seq (D-055)
    action = (last.get("action") or "").strip()
    if action != "approve":
        return f"the latest logged decision is {action or 'not an approve'}, not approve"
    declined = any((r.get("action") or "").strip() == "decline" for r in rows[:-1])
    if declined and not (last.get("reason") or "").strip():
        return "an approve after a decline needs a written reason"
    return ""


def agency_problem(target) -> str:
    """Empty string means the account manager may approve. The user may override every block except the two refused statuses.

    T-071: the status is read from the last saved run in prepare.py (G2), never from a passed-in report. `target`
    is a submission id, or the saved run dict that prepare.approve() already read; only the id is taken from a dict.
    """
    submission = _submission_of(target)
    if not submission:
        return "the account manager needs the extraction report"
    try:
        report = prepare.read_saved_run(submission)
    except ValueError:
        return "the saved extraction run for this file cannot be read"
    status = report.get("status")
    if status == "extraction_failed":
        return "extraction failed on this file"
    if status == "all_values_rejected":
        return "every value on this file was rejected"
    if report.get("needs_human"):
        return "an unread page is still on the file"
    open_conflicts = [
        item for item in report.get("conflicts") or [] if item.get("resolution") != "resolved"
    ]
    if open_conflicts:
        return "an open conflict is still on the file"
    if not report.get("complete"):
        return "the file is not complete"
    if _route(report) not in {"carrier_a", "carrier_b", "carrier_c"}:
        return "the file is not in appetite"
    return ""


def sent_on(dest: Path) -> str:
    return datetime.fromtimestamp(dest.stat().st_mtime).date().isoformat()


def sent_info(submission: str, out_dir: Path) -> tuple[str, str]:
    """(date, carrier) of the package already in out_dir, or ("", "")."""
    dest = out_dir / f"{submission}.md"
    if not dest.is_file():
        return "", ""
    carrier = next((l.split(":", 1)[1].strip() for l in dest.read_text().splitlines() if l.startswith("Carrier:")), "unknown")
    return sent_on(dest), carrier


def send_to_carrier(
    submission: str,
    actor: str,
    out_dir: Path,
    reason: str = "",
    user_line: str = "",
    carrier: str = "",
    resend_reason: str = "",
) -> Path:
    """B-233 (D-067): a second send for the same submission is refused unless resend_reason is written; the resend is logged.

    T-071: read the status from the last saved run itself, before the actor is looked at, and refuse both refused statuses for every actor."""
    submission = (submission or "").strip()
    report = prepare.read_saved_run(submission)  # G2: no file, hash differs, or unknown status -> refuse
    status = report.get("status")
    if status in prepare.REFUSED_STATUSES:
        raise ValueError(f"this file's status is {status}; it cannot be sent, for any actor including the user")
    problem = prepare.manifest_problem(submission)  # P-020 (D-062): the input documents are the ones extracted, every actor
    if problem:
        raise ValueError(problem)
    problem = _decision_problem(submission)  # D-053, every actor
    if problem:
        raise ValueError(problem)
    name = _actor(actor)
    if name not in {"user", "account-manager"}:
        raise ValueError("only the user or the account manager may send to a carrier")
    if name == "account-manager":
        if not (reason or "").strip():
            raise ValueError("the account manager must write a reason")
        problem = agency_problem(submission)
        if problem:
            raise ValueError(problem)
    if name == "user" and (user_line or "").strip() != f"send to carrier {submission}":  # T-086, D-056: after every other gate
        raise ValueError(f'a user send needs the exact line "send to carrier {submission}"')
    if out_dir.name != "to-carrier":
        raise ValueError("packages go to to-carrier")
    if (carrier or "").strip() and name != "user":
        raise ValueError("only the user may override the carrier")
    dest = out_dir / f"{submission}.md"
    resend = (resend_reason or "").strip()
    if dest.exists() and not resend:
        raise ValueError(f"already sent on {sent_on(dest)}; a second send needs an explicit resend with a written reason")
    body = build_package(submission, carrier, reason if name == "user" else "")  # T-085: raises on an empty required field or no carrier; nothing is written yet
    out_dir.mkdir(parents=True, exist_ok=True)
    who = "user (override)" if name == "user" else "account-manager"
    note = f"Reason: {reason.strip()}\n" if (reason or "").strip() else ""
    line = f"User-line: {user_line.strip()}\n" if name == "user" else ""
    again = f"Resend-reason: {resend}\n" if resend else ""
    dest.write_text(f"Sent-by: {who}\n{line}{note}{again}\n{body}")
    if name == "user" or resend:
        SENDS_LOG.parent.mkdir(parents=True, exist_ok=True)
        with SENDS_LOG.open("a") as handle:
            handle.write(json.dumps({"submission": submission, "actor": name, "user_line": user_line.strip(), "package": str(dest), **({"resend": True, "resend_reason": resend} if resend else {}), **({"carrier_override": carrier.strip().lower(), "override_reason": reason.strip()} if (carrier or "").strip() else {})}) + "\n")
    return dest


if __name__ == "__main__":
    import json
    import tempfile

    def save(ext: Path, submission: str, status: str, complete=False, fields=None, needs_human=None, sprinklers=None):
        """A saved run shaped like prepare.write_drafts() writes, no model call. The hash is the reader's."""
        payload = {
            "submission": submission,
            "status": status,
            "error": "model call failed: HTTP 429 rate limit" if status == "extraction_failed" else None,
            "complete": bool(complete),
            "conflicts": [],
            "needs_human": needs_human or [],
            "sprinklers": sprinklers,
            "fields": fields or [],
        }
        folder = ext.parent / "inbox" / submission  # P-020: one input document, its manifest in the saved run
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "application.md").write_text(f"SYNTHETIC application {submission}\n")
        payload["input_manifest"] = prepare.folder_manifest(folder)
        payload["hash_algorithm"] = prepare.HASH_ALGORITHM
        payload["saved_hash"] = prepare.hash_payload(payload)
        ext.mkdir(parents=True, exist_ok=True)
        (ext / f"{submission}.json").write_text(json.dumps(payload))
        return payload

    def full(**over):
        vals = {f: "x" for f in prepare.FIELDS} | {"operations": "accounting office", "tiv_building": "$1,000,000"} | over
        return [{"field_id": f, "value": v, "source": "application.md", "start": 0, "end": 3} for f, v in vals.items()]

    office = full()
    LINE = "send to carrier {}".format
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ext = tmp / "extractions"
        log = tmp / "decisions.jsonl"

        seq = iter(range(1, 1000))

        def decide(sub: str, action: str, reason: str = "", who: str = "UW-001", n: int | None = None):
            row = {"seq": next(seq) if n is None else n, "submission": sub, "action": action, "underwriter_id": who, "reason": reason}
            with log.open("a") as handle:
                handle.write(json.dumps(row) + "\n")

        saved_dir, saved_log, saved_sends, saved_inbox = prepare.EXTRACT_DIR, DECISIONS_LOG, SENDS_LOG, prepare.INBOX_DIR
        sends = tmp / "sends.jsonl"
        prepare.EXTRACT_DIR, DECISIONS_LOG, SENDS_LOG, prepare.INBOX_DIR = ext, log, sends, tmp / "inbox"
        try:
            dest_dir = tmp / "to-carrier"
            dest_dir.mkdir()

            # No AI role may send, even a good file.
            save(ext, "SUB-001", "complete", complete=True, fields=office, sprinklers="no")
            for actor in ("software-engineer", "ai-engineer-assistant", "@model-risk"):
                try:
                    send_to_carrier("SUB-001", actor, dest_dir, user_line=LINE("SUB-001"))
                    raise SystemExit(f"a send as {actor} should fail")
                except ValueError:
                    pass

            # T-071 (1): the two refused statuses are refused for every actor, with no report to pass.
            for sub, status in (("SUB-101", "extraction_failed"), ("SUB-102", "all_values_rejected")):
                save(ext, sub, status)
                for actor in ("user", "user (override)", "@account-manager", "ai-engineer-assistant"):
                    try:
                        send_to_carrier(sub, actor, dest_dir, reason="ready", user_line=LINE(sub))
                        raise SystemExit(f"{status} must be refused for {actor}")
                    except ValueError:
                        pass
                assert agency_problem(sub), f"agency_problem must refuse {status}"
                assert agency_problem(prepare.read_saved_run(sub)), "and must refuse from the saved run dict"

            # T-071 (2): nothing saved, a changed hash, and an unknown status all refuse.
            try:
                send_to_carrier("SUB-190", "user", dest_dir, user_line=LINE("SUB-190"))
                raise SystemExit("a send with no saved run should fail")
            except ValueError:
                pass
            save(ext, "SUB-191", "complete", complete=True, fields=office, sprinklers="no")
            tampered = json.loads((ext / "SUB-191.json").read_text())
            tampered["status"] = "incomplete"
            (ext / "SUB-191.json").write_text(json.dumps(tampered))
            try:
                send_to_carrier("SUB-191", "user", dest_dir, user_line=LINE("SUB-191"))
                raise SystemExit("a changed saved run should fail")

            except ValueError:
                pass
            save(ext, "SUB-192", "incomplete")
            raw = json.loads((ext / "SUB-192.json").read_text())
            raw["status"] = "banana"
            raw["saved_hash"] = prepare.hash_payload(raw)
            (ext / "SUB-192.json").write_text(json.dumps(raw))
            try:
                send_to_carrier("SUB-192", "user", dest_dir, user_line=LINE("SUB-192"))
                raise SystemExit("an unknown status should fail")
            except ValueError:
                pass

            for sub in ("SUB-001", "SUB-193", "SUB-194"):
                decide(sub, "approve")

            # The account-manager rules still gate a normal file.
            save(ext, "SUB-193", "complete", complete=True, fields=office, sprinklers="no")
            try:
                send_to_carrier("SUB-193", "account-manager", dest_dir)
                raise SystemExit("missing reason should fail")
            except ValueError:
                pass
            save(ext, "SUB-194", "incomplete", complete=False, fields=full(year_built=""))
            assert agency_problem("SUB-194") == "the file is not complete"
            try:
                send_to_carrier("SUB-194", "account-manager", dest_dir, reason="ready")
                raise SystemExit("an incomplete send should fail")
            except ValueError:
                pass

            # A good account-manager send, and the user's override on an incomplete file.
            sent = send_to_carrier("SUB-193", "account-manager", dest_dir, reason="complete office file")
            text = sent.read_text()
            assert text.startswith("Sent-by: account-manager")
            assert "Reason: complete office file" in text
            assert "SYNTHETIC" in text and "Carrier: carrier_a" in text and "application.md [0:3]" in text
            # T-085: an empty required field is refused for the user too; the caller's text is not a body.
            try:
                send_to_carrier("SUB-194", "user", dest_dir, user_line=LINE("SUB-194"))
                raise SystemExit("an empty required field should fail")
            except ValueError as exc:
                assert "year_built" in str(exc)
            assert not (dest_dir / "SUB-194.md").exists()
            try:
                send_to_carrier("SUB-193", "user", dest_dir, body="free text body", user_line=LINE("SUB-193"))
                raise SystemExit("a caller body should not be accepted")
            except TypeError:
                pass
            # T-085: an edit stores its field and new value; the package carries it, labeled, with the original citation.
            save(ext, "SUB-195", "incomplete", fields=full(year_built=""))
            decide("SUB-195", "approve")
            try:
                build_package("SUB-195")
                raise SystemExit("year_built is empty before the edit")
            except ValueError:
                pass
            with log.open("a") as handle:
                handle.write(json.dumps({"seq": 800, "submission": "SUB-195", "action": "edit", "underwriter_id": "UW-001", "reason": "from the loss run", "field_id": "year_built", "new_value": "1987"}) + "\n")
                handle.write(json.dumps({"seq": 801, "submission": "SUB-195", "action": "approve", "underwriter_id": "UW-001", "reason": ""}) + "\n")
            edited = build_package("SUB-195")
            assert "year_built: 1987" in edited and "EDITED by UW-001" in edited and "from the loss run" in edited
            # T-085: no carrier named (nightclub) -> refused.
            save(ext, "SUB-196", "complete", complete=True, fields=full(operations="barber shop"))
            decide("SUB-196", "approve")
            try:
                build_package("SUB-196")
                raise SystemExit("no carrier should fail")
            except ValueError as exc:
                assert "no carrier" in str(exc)

            # T-086: the user's exact line, matched to the id, logged; none or another file's line writes nothing.
            sends.unlink(missing_ok=True)  # earlier user sends in this check logged here; start clean
            if True:
                for bad in ("", "send to carrier SUB-999", "Send to carrier SUB-194x", "send to carrier"):
                    try:
                        send_to_carrier("SUB-193", "user", dest_dir / "x" / "to-carrier", user_line=bad)
                        raise SystemExit(f"line {bad!r} should fail")
                    except ValueError:
                        pass
                assert not (dest_dir / "x").exists() and not sends.exists()
                # The line opens no other gate: refused status, no approve, and decline-latest all still refuse.
                for sub in ("SUB-101", "SUB-301", "SUB-302"):
                    try:
                        send_to_carrier(sub, "user", dest_dir, user_line=LINE(sub))
                        raise SystemExit(f"the line must not get {sub} past its gate")
                    except ValueError:
                        pass
                    assert not (dest_dir / f"{sub}.md").exists() and not sends.exists()
                ok = send_to_carrier("SUB-195", "user", dest_dir, user_line=LINE("SUB-195"))
                assert "User-line: send to carrier SUB-195" in ok.read_text()
                logged = [json.loads(x) for x in sends.read_text().splitlines()]
                assert len(logged) == 1 and logged[0]["submission"] == "SUB-195" and logged[0]["user_line"] == LINE("SUB-195")

            # D-057 item 1: override only on no_match, with carrier and reason; never hold; logged.
            save(ext, "SUB-401", "complete", complete=True, fields=full(operations="barber shop"))
            save(ext, "SUB-402", "complete", complete=True, fields=full(operations="apartments, 8 units"))
            save(ext, "SUB-403", "complete", complete=True, fields=full(operations="nightclub"))
            for sub in ("SUB-401", "SUB-402", "SUB-403"):
                decide(sub, "approve")
            sends.unlink(missing_ok=True)
            for sub, kw in (("SUB-402", dict(carrier="carrier_a", reason="x")), ("SUB-403", dict(carrier="carrier_a", reason="x")), ("SUB-401", dict(reason="x")), ("SUB-401", dict(carrier="carrier_a")),
                            ("SUB-401", dict(carrier="carrier_z", reason="x")), ("SUB-193", dict(carrier="carrier_b", reason="x"))):
                try:
                    send_to_carrier(sub, "user", dest_dir, user_line=LINE(sub), **kw)
                    raise SystemExit(f"{sub} {kw} must be refused")
                except ValueError:
                    pass
            try:
                send_to_carrier("SUB-401", "account-manager", dest_dir, reason="x", carrier="carrier_a")
                raise SystemExit("the account manager may not override")
            except ValueError:
                pass
            assert not (dest_dir / "SUB-401.md").exists() and not (dest_dir / "SUB-402.md").exists() and not sends.exists()
            done = send_to_carrier("SUB-401", "user", dest_dir, user_line=LINE("SUB-401"), carrier="carrier_b", reason="client asked, bar is a small tasting room")
            text = done.read_text()
            assert OVERRIDE_LABEL in text and "Carrier: carrier_b" in text and "small tasting room" in text
            row = json.loads(sends.read_text().splitlines()[-1])
            assert row["carrier_override"] == "carrier_b" and row["override_reason"].startswith("client asked") and row["submission"] == "SUB-401"

            # T-079 / D-053: the log decides, for every actor, with no decision passed in.
            for sub in ("SUB-301", "SUB-302", "SUB-303", "SUB-304"):
                save(ext, sub, "complete", complete=True, fields=office, sprinklers="no")
            decide("SUB-302", "approve")
            decide("SUB-302", "decline", reason="not in appetite")
            decide("SUB-303", "decline", reason="first look")
            decide("SUB-303", "approve")
            decide("SUB-304", "decline", reason="first look")
            decide("SUB-304", "approve", reason="producer sent the missing loss runs")
            for sub, ok in (("SUB-301", False), ("SUB-302", False), ("SUB-303", False), ("SUB-304", True)):
                for actor in ("user", "account-manager"):
                    try:
                        send_to_carrier(sub, actor, dest_dir, reason="ready", user_line=LINE(sub))
                        assert ok, f"{sub} must be refused for {actor}"
                        (dest_dir / f"{sub}.md").unlink()  # B-233: the next actor sends afresh
                    except ValueError:
                        assert not ok, f"{sub} must pass for {actor}"
            assert len(log.read_text().splitlines()) == 16  # history untouched by the sends

            # D-055: highest seq wins, not line order; an unlisted id or an AI role is not a decision;
            # a repeated seq refuses; no seq is not a decision; underwriters.json may not list an AI role.
            for sub in ("SUB-305", "SUB-306", "SUB-307", "SUB-308", "SUB-309"):
                save(ext, sub, "complete", complete=True, fields=office, sprinklers="no")
            decide("SUB-305", "approve", reason="seq decides, not the line", n=901)
            decide("SUB-305", "decline", reason="later line, lower seq", n=900)
            decide("SUB-306", "approve", who="senior-underwriter")
            decide("SUB-306", "approve", who="UW-999")
            decide("SUB-307", "approve", n=950)
            decide("SUB-307", "approve", n=950)
            with log.open("a") as handle:
                handle.write(json.dumps({"submission": "SUB-308", "action": "approve", "underwriter_id": "user"}) + "\n")
            decide("SUB-309", "decline", reason="first look", who="user")
            decide("SUB-309", "approve", reason="loss runs arrived", who="user")
            for sub, ok in (("SUB-305", True), ("SUB-306", False), ("SUB-307", False), ("SUB-308", False), ("SUB-309", True)):
                try:
                    send_to_carrier(sub, "user", dest_dir, user_line=LINE(sub))
                    assert ok, f"{sub} must be refused"
                except ValueError:
                    assert not ok, f"{sub} must pass"
            assert "user" in underwriters() and not underwriters() & AI_ROLES
            saved_uw = UNDERWRITERS
            UNDERWRITERS = tmp / "uw.json"
            UNDERWRITERS.write_text(json.dumps({"underwriters": [{"id": "user"}, {"id": "@pm"}]}))
            try:
                underwriters()
                raise SystemExit("an AI role on the underwriter list should fail")
            except ValueError:
                pass
            finally:
                UNDERWRITERS = saved_uw

            # P-020 (D-062): a document added after extraction refuses the send, for the user too.
            save(ext, "SUB-320", "complete", complete=True, fields=office, sprinklers="no")
            decide("SUB-320", "approve")
            assert send_to_carrier("SUB-320", "user", dest_dir, user_line=LINE("SUB-320")).exists()
            # B-233 (D-067): a second send is refused without a resend reason; with one it is allowed and logged.
            try:
                send_to_carrier("SUB-320", "user", dest_dir, user_line=LINE("SUB-320"))
                raise SystemExit("a second send without a resend reason must be refused")
            except ValueError as exc:
                assert "already sent on" in str(exc), exc
            assert sent_info("SUB-320", dest_dir)[1] == "carrier_a"
            send_to_carrier("SUB-320", "user", dest_dir, user_line=LINE("SUB-320"), resend_reason="carrier lost the file")
            last = json.loads(SENDS_LOG.read_text().splitlines()[-1])
            assert last["resend"] is True and last["resend_reason"] == "carrier lost the file"
            assert "Resend-reason: carrier lost the file" in (dest_dir / "SUB-320.md").read_text()
            (tmp / "inbox" / "SUB-320" / "late-loss-run.pdf").write_bytes(b"added after extraction")
            try:
                send_to_carrier("SUB-320", "user", dest_dir, user_line=LINE("SUB-320"))
                raise SystemExit("a document added after extraction must refuse the send")
            except ValueError as exc:
                assert "changed since extraction" in str(exc), exc
        finally:
            prepare.EXTRACT_DIR, DECISIONS_LOG, SENDS_LOG, prepare.INBOX_DIR = saved_dir, saved_log, saved_sends, saved_inbox
    print("package ok")
