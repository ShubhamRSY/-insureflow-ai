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


def send_to_carrier(
    submission: str,
    actor: str,
    out_dir: Path,
    body: str,
    reason: str = "",
) -> Path:
    """T-071: read the status from the last saved run itself, before the actor is looked at, and refuse both refused statuses for every actor."""
    report = prepare.read_saved_run(submission)  # G2: no file, hash differs, or unknown status -> refuse
    status = report.get("status")
    if status in prepare.REFUSED_STATUSES:
        raise ValueError(f"this file's status is {status}; it cannot be sent, for any actor including the user")
    problem = _decision_problem((submission or "").strip())  # D-053, every actor
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

        seq = iter(range(1, 1000))

        def decide(sub: str, action: str, reason: str = "", who: str = "UW-001", n: int | None = None):
            row = {"seq": next(seq) if n is None else n, "submission": sub, "action": action, "underwriter_id": who, "reason": reason}
            with log.open("a") as handle:
                handle.write(json.dumps(row) + "\n")

        saved_dir, saved_log = prepare.EXTRACT_DIR, DECISIONS_LOG
        prepare.EXTRACT_DIR, DECISIONS_LOG = ext, log
        try:
            dest_dir = tmp / "to-carrier"
            dest_dir.mkdir()

            # No AI role may send, even a good file.
            save(ext, "SUB-001", "complete", complete=True, fields=office, sprinklers="no")
            for actor in ("software-engineer", "ai-engineer-assistant", "@model-risk"):
                try:
                    send_to_carrier("SUB-001", actor, dest_dir, body)
                    raise SystemExit(f"a send as {actor} should fail")
                except ValueError:
                    pass

            # T-071 (1): the two refused statuses are refused for every actor, with no report to pass.
            for sub, status in (("SUB-101", "extraction_failed"), ("SUB-102", "all_values_rejected")):
                save(ext, sub, status)
                for actor in ("user", "user (override)", "@account-manager", "ai-engineer-assistant"):
                    try:
                        send_to_carrier(sub, actor, dest_dir, body, reason="ready")
                        raise SystemExit(f"{status} must be refused for {actor}")
                    except ValueError:
                        pass
                assert agency_problem(sub), f"agency_problem must refuse {status}"
                assert agency_problem(prepare.read_saved_run(sub)), "and must refuse from the saved run dict"

            # T-071 (2): nothing saved, a changed hash, and an unknown status all refuse.
            try:
                send_to_carrier("SUB-190", "user", dest_dir, body)
                raise SystemExit("a send with no saved run should fail")
            except ValueError:
                pass
            save(ext, "SUB-191", "complete", complete=True, fields=office, sprinklers="no")
            tampered = json.loads((ext / "SUB-191.json").read_text())
            tampered["status"] = "incomplete"
            (ext / "SUB-191.json").write_text(json.dumps(tampered))
            try:
                send_to_carrier("SUB-191", "user", dest_dir, body)
                raise SystemExit("a changed saved run should fail")

            except ValueError:
                pass
            save(ext, "SUB-192", "incomplete")
            raw = json.loads((ext / "SUB-192.json").read_text())
            raw["status"] = "banana"
            raw["saved_hash"] = prepare.hash_payload(raw)
            (ext / "SUB-192.json").write_text(json.dumps(raw))
            try:
                send_to_carrier("SUB-192", "user", dest_dir, body)
                raise SystemExit("an unknown status should fail")
            except ValueError:
                pass

            for sub in ("SUB-001", "SUB-193", "SUB-194"):
                decide(sub, "approve")

            # The account-manager rules still gate a normal file.
            save(ext, "SUB-193", "complete", complete=True, fields=office, sprinklers="no")
            try:
                send_to_carrier("SUB-193", "account-manager", dest_dir, body)
                raise SystemExit("missing reason should fail")
            except ValueError:
                pass
            save(ext, "SUB-194", "incomplete", complete=False, fields=office)
            assert agency_problem("SUB-194") == "the file is not complete"
            try:
                send_to_carrier("SUB-194", "account-manager", dest_dir, body, reason="ready")
                raise SystemExit("an incomplete send should fail")
            except ValueError:
                pass

            # A good account-manager send, and the user's override on an incomplete file.
            sent = send_to_carrier("SUB-193", "account-manager", dest_dir, body, reason="complete office file")
            text = sent.read_text()
            assert text.startswith("Sent-by: account-manager")
            assert "Reason: complete office file" in text
            override = send_to_carrier("SUB-194", "user", dest_dir, body)
            assert override.read_text().startswith("Sent-by: user (override)")

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
                        send_to_carrier(sub, actor, dest_dir, body, reason="ready")
                        assert ok, f"{sub} must be refused for {actor}"
                    except ValueError:
                        assert not ok, f"{sub} must pass for {actor}"
            assert len(log.read_text().splitlines()) == 3 + 2 + 2 + 2 + 0 + 0  # history untouched by the sends

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
                    send_to_carrier(sub, "user", dest_dir, body)
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
        finally:
            prepare.EXTRACT_DIR, DECISIONS_LOG = saved_dir, saved_log
    print("package ok")
