"""Step 7 — carrier package.

The send reads the file's current status from the last saved extraction run
itself; it takes no report from the caller (T-071, item (b) of the T-020 veto).
A file whose status is extraction_failed or all_values_rejected is never sent,
for any actor including the user. The account manager can send only when the
agency rules pass, and must write a reason. No AI role can send.
Every other block keeps the user's override (D-017).

T-079: a carrier send also requires a logged underwriter approve; the send
reads the decision log itself and refuses unless the last decision for the
submission is approve, for every actor. The log is read as append-only JSONL.
"last" is the final matching line by insertion order (line number), because
the log records only a date and no time (B-104). Which ids count as an
underwriter is not answered by the log: the log takes any id and stores it
as-is (B-138, B-100), so this gate does not filter ids — it trusts the stored
rows. Both are raised as QUESTIONs in the handoff. The one case @user has not
decided, a decline earlier in the history followed by a later approve, is not
picked: the send refuses and leaves the file with a person (D-033 Amends).
No decision is passed in by the caller.

# ponytail: one markdown file per submission. Quote tracking is the from-carrier reply, add a tracker when a carrier answers.

Run: python underwriting_pipeline/app/package.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# B-169: the status reader lives in prepare.py. Reach it the same way workbench.py does.
sys.path.insert(0, str(ROOT / "underwriting_pipeline" / "ai"))
import prepare

DECISIONS_LOG = ROOT / "deliverables" / "software-engineer" / "decisions.jsonl"


def build_package(submission: str, summary: str) -> str:
    return (
        f"Package {submission}\n"
        "Nothing has been declined. Nothing has been bound.\n"
        "The underwriter has not been replaced by this file.\n\n"
        f"{summary.rstrip()}\n"
    )


def _actor(actor: str) -> str:
    return (actor or "").strip().lstrip("@").lower().replace(" ", "-")


def _route(report: dict) -> str:
    from workbench import route

    return route(report)


def _submission_of(target) -> str:
    """The id to read. A caller passes the id, or the saved run that prepare.approve() already read."""
    if isinstance(target, dict):
        target = target.get("submission")
    return target.strip() if isinstance(target, str) else ""


def _submission_rows(submission: str, log_path: Path = DECISIONS_LOG) -> list:
    """Every decision row for this submission, in the log's insertion (line) order."""
    if not submission or not log_path.exists():
        return []
    rows = []
    for line in log_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if (row.get("submission") or "").strip() == submission:
            rows.append(row)
    return rows


def _last_approve_decision(submission: str, log_path: Path = DECISIONS_LOG) -> str:
    """Return empty string if the last decision for this submission is approve.

    "Last" is the final matching line by insertion order (line number) because the log records
    only a date and no time (B-104). The log takes any id and stores it as-is (B-138, B-100);
    this gate does not filter ids, it trusts the stored rows. No decision is passed in by the
    caller, and the caller's actor does not change the answer.
    """
    rows = _submission_rows(submission, log_path)
    if not rows:
        return "no logged decision for this file"
    last = rows[-1]
    action = (last.get("action") or "").strip()
    if action == "approve":
        # T-079: a decline earlier in the history followed by a later approve is the one case
        # @user has not decided (D-033 Amends: "a logged underwriter approve with no later
        # decline"). Do not pick it: refuse and leave the file with a person.
        earlier_decline = any((row.get("action") or "").strip() == "decline" for row in rows[:-1])
        if earlier_decline:
            return "this file was declined and later approved; that case is not decided, waiting for @user"
        return ""
    if action == "decline":
        return "the last logged decision is decline"
    if action == "edit":
        return "the last logged decision is edit, not approve"
    return "the last logged decision is not approve"


def agency_problem(target) -> str:
    """Empty string means the account manager may approve. The user may override every block except the two refused statuses.

    T-071: the status is read from the last saved run in prepare.py (G2), never from a passed-in report. `target`
    is a submission id, or the saved run dict that prepare.approve() already read; only the id is taken from a dict.
    This is the agency rule block only. T-079's decision-log gate is a carrier-send rule and lives in
    `send_to_carrier`, not here, because `prepare.approve()` (a producer request) also calls this function.
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


def send_to_carrier(
    submission: str,
    actor: str,
    out_dir: Path,
    body: str,
    reason: str = "",
    log_path: Path = DECISIONS_LOG,
) -> Path:
    """T-071: read the status from the last saved run itself, before the actor is looked at, and refuse both refused statuses for every actor.
    T-079: also require the last logged decision is approve, for every actor. No decision is passed in by the caller.
    """
    report = prepare.read_saved_run(submission)  # G2: no file, hash differs, or unknown status -> refuse
    status = report.get("status")
    if status in prepare.REFUSED_STATUSES:
        raise ValueError(f"this file's status is {status}; it cannot be sent, for any actor including the user")
    decision_problem = _last_approve_decision(submission, log_path)
    if decision_problem:
        raise ValueError(decision_problem)
    name = _actor(actor)
    if name not in {"user", "account-manager"}:
        raise ValueError("only the user or the account manager may send to a carrier")
    if name == "account-manager":
        if not (reason or "").strip():
            raise ValueError("the account manager must write a reason")
        problem = agency_problem(submission)
        if problem:
            raise ValueError(problem)
    if out_dir.name != "to-carrier":
        raise ValueError("packages go to to-carrier")
    if "Nothing has been declined" not in body or "Nothing has been bound" not in body:
        raise ValueError("refusing a package that does not say it is not a decline or a bind")
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"{submission}.md"
    who = "user (override)" if name == "user" else "account-manager"
    note = f"Reason: {reason.strip()}\n" if (reason or "").strip() else ""
    dest.write_text(f"Sent-by: {who}\n{note}\n{body}")
    return dest


if __name__ == "__main__":
    import json
    import tempfile

    body = build_package("SUB-000", "FICTIONAL office. Recommend Carrier A.")
    assert "Nothing has been bound" in body

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
        payload["hash_algorithm"] = prepare.HASH_ALGORITHM
        payload["saved_hash"] = prepare.hash_payload(payload)
        ext.mkdir(parents=True, exist_ok=True)
        (ext / f"{submission}.json").write_text(json.dumps(payload))
        return payload

    office = [{"field_id": "operations", "value": "accounting office"}]
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ext = tmp / "extractions"
        log = tmp / "decisions.jsonl"
        saved_dir = prepare.EXTRACT_DIR
        prepare.EXTRACT_DIR = ext
        try:
            dest_dir = tmp / "to-carrier"
            dest_dir.mkdir()

            def decide(submission: str, action: str, reason: str = "") -> dict:
                """Append one decision row to the temp log, shaped like workbench.record_decision()."""
                row = {
                    "submission": submission,
                    "action": action,
                    "underwriter_id": "u.underwriter",
                    "reason": reason,
                    "date": "2026-10-13",
                    "bound": False,
                    "sent_to_carrier": False,
                }
                with log.open("a") as handle:
                    handle.write(json.dumps(row) + "\n")
                return row

            # No AI role may send, even a good, approved file (the actor block, not the decision gate).
            save(ext, "SUB-001", "complete", complete=True, fields=office, sprinklers="no")
            decide("SUB-001", "approve")
            for actor in ("software-engineer", "ai-engineer-assistant", "@model-risk"):
                try:
                    send_to_carrier("SUB-001", actor, dest_dir, body, log_path=log)
                    raise SystemExit(f"a send as {actor} should fail")
                except ValueError:
                    pass

            # T-071 (1): the two refused statuses are refused for every actor, with no report to pass.
            for sub, status in (("SUB-101", "extraction_failed"), ("SUB-102", "all_values_rejected")):
                save(ext, sub, status)
                decide(sub, "approve")
                for actor in ("user", "user (override)", "@account-manager", "ai-engineer-assistant"):
                    try:
                        send_to_carrier(sub, actor, dest_dir, body, reason="ready", log_path=log)
                        raise SystemExit(f"{status} must be refused for {actor}")
                    except ValueError:
                        pass
                assert agency_problem(sub), f"agency_problem must refuse {status}"
                assert agency_problem(prepare.read_saved_run(sub)), "and must refuse from the saved run dict"

            # T-071 (2): nothing saved, a changed hash, and an unknown status all refuse.
            try:
                send_to_carrier("SUB-190", "user", dest_dir, body, log_path=log)
                raise SystemExit("a send with no saved run should fail")
            except ValueError:
                pass
            save(ext, "SUB-191", "complete", complete=True, fields=office, sprinklers="no")
            decide("SUB-191", "approve")
            tampered = json.loads((ext / "SUB-191.json").read_text())
            tampered["status"] = "incomplete"
            (ext / "SUB-191.json").write_text(json.dumps(tampered))
            try:
                send_to_carrier("SUB-191", "user", dest_dir, body, log_path=log)
                raise SystemExit("a changed saved run should fail")

            except ValueError:
                pass
            save(ext, "SUB-192", "incomplete")
            decide("SUB-192", "approve")
            raw = json.loads((ext / "SUB-192.json").read_text())
            raw["status"] = "banana"
            raw["saved_hash"] = prepare.hash_payload(raw)
            (ext / "SUB-192.json").write_text(json.dumps(raw))
            try:
                send_to_carrier("SUB-192", "user", dest_dir, body, log_path=log)
                raise SystemExit("an unknown status should fail")
            except ValueError:
                pass

            # T-079: the send reads the decision log itself (never a passed-in decision).
            # (i) no decision at all is refused...
            save(ext, "SUB-301", "complete", complete=True, fields=office, sprinklers="no")
            try:
                send_to_carrier("SUB-301", "user", dest_dir, body, log_path=log)
                raise SystemExit("a send with no logged decision should fail")
            except ValueError as exc:
                assert "no logged decision" in str(exc), exc
            assert _last_approve_decision("SUB-301", log).startswith("no logged decision")
            # ...(ii) an approve passes this gate...
            decide("SUB-301", "approve")
            sent301 = send_to_carrier("SUB-301", "user", dest_dir, body, log_path=log)
            assert sent301.read_text().startswith("Sent-by: user (override)")
            # ...(iii) an approve followed by a later decline is refused.
            save(ext, "SUB-302", "complete", complete=True, fields=office, sprinklers="no")
            decide("SUB-302", "approve")
            decide("SUB-302", "decline", reason="declined after review")
            try:
                send_to_carrier("SUB-302", "user", dest_dir, body, log_path=log)
                raise SystemExit("an approve followed by a decline should fail")
            except ValueError as exc:
                assert "decline" in str(exc), exc
            assert _last_approve_decision("SUB-302", log) == "the last logged decision is decline"

            # The decision gate binds the account manager too: an approve is required.
            save(ext, "SUB-303", "complete", complete=True, fields=office, sprinklers="no")
            try:
                send_to_carrier("SUB-303", "account-manager", dest_dir, body, reason="looks complete", log_path=log)
                raise SystemExit("the account manager must also have a logged approve")
            except ValueError as exc:
                assert "no logged decision" in str(exc), exc

            # The account-manager rules still gate a normal, approved file.
            save(ext, "SUB-193", "complete", complete=True, fields=office, sprinklers="no")
            decide("SUB-193", "approve")
            try:
                send_to_carrier("SUB-193", "account-manager", dest_dir, body, log_path=log)
                raise SystemExit("missing reason should fail")
            except ValueError:
                pass
            save(ext, "SUB-194", "incomplete", complete=False, fields=office)
            decide("SUB-194", "approve")
            assert agency_problem("SUB-194") == "the file is not complete"
            try:
                send_to_carrier("SUB-194", "account-manager", dest_dir, body, reason="ready", log_path=log)
                raise SystemExit("an incomplete send should fail")
            except ValueError:
                pass

            # A good account-manager send, and the user's override on an incomplete (but approved) file.
            sent = send_to_carrier(
                "SUB-193", "account-manager", dest_dir, body, reason="complete office file", log_path=log
            )
            text = sent.read_text()
            assert text.startswith("Sent-by: account-manager")
            assert "Reason: complete office file" in text
            override = send_to_carrier("SUB-194", "user", dest_dir, body, log_path=log)
            assert override.read_text().startswith("Sent-by: user (override)")

            # T-079, the one case @user has not decided: declined then later approved. The code does
            # not pick a side; it refuses and leaves the file with a person, with that message.
            save(ext, "SUB-304", "complete", complete=True, fields=office, sprinklers="no")
            decide("SUB-304", "decline", reason="declined, then reopened")
            decide("SUB-304", "approve")
            try:
                send_to_carrier("SUB-304", "user", dest_dir, body, log_path=log)
                raise SystemExit("declined-then-approved must wait for @user, so it must refuse")
            except ValueError as exc:
                assert "waiting for @user" in str(exc), exc
        finally:
            prepare.EXTRACT_DIR = saved_dir
    print("package ok")
