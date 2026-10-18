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

import hashlib
import json
import re
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


def seniors() -> dict[str, str]:
    """P-052 (D-098): id -> name of the listed underwriters with "senior": true. Only they may confirm a senior-referral market."""
    ids = underwriters()
    return {u["id"].strip(): u.get("name", "") for u in json.loads(UNDERWRITERS.read_text())["underwriters"] if u.get("senior") is True and (u.get("id") or "").strip() in ids}


def confirms_path() -> Path:
    return DECISIONS_LOG.with_name("market_confirms.jsonl")  # a sibling file: a confirm is not a decision, so the latest approve still gates the send


def confirm_problem(report: dict) -> str:
    """P-052: empty when a senior may confirm a market on this (reviewed) file. Never on a held file or one with a prohibited word."""
    from workbench import PROHIBITED, VACANT, _has, _ops, class_text, match

    if report.get("status") in prepare.REFUSED_STATUSES:
        return f"this file's status is {prepare.status_refusal(report)}"
    route = match(report)["route"]
    if route != "senior_referral":
        return f"the carrier match is {route}; a market confirm is only for a senior referral"
    hit = next((w for w in PROHIBITED if _has(class_text(report), (w,))), "")  # H1 (D-112): same text as the route, operations and the Line of business line
    if hit or "R2" in match(report)["note"]:  # any bar/liquor R2 referral is never a market confirm
        return f"a prohibited word (\"{hit or 'bar'}\": bar, pub, lounge or another W1 word) is on the file; no market confirm (D-057, D-060, D-112)"
    raw = " ".join(f"{r.get('value') or ''} {r.get('quote') or ''} {r.get('context') or ''}" for r in report.get("fields") or [] if r.get("field_id") == "operations").lower()
    if _has(_ops(report), VACANT) or _has(raw, VACANT):  # compliance H1: AG:51 prohibits true vacancy and no utilities
        return "vacant, unoccupied or no utilities: the guide prohibits true vacancy and buildings with no utilities (AG:51); a renovation under a signed GC contract (AG:40) needs its own rule; no market confirm"
    if report.get("needs_human"):
        return "an unread page is still on the file"
    return conflict_problem(report)


def match_note(report: dict) -> str:
    from workbench import match

    return match(report)["note"]


# P-054 (c): any note on the file (route note, extracted fields, the submission's text documents) can take a carrier out of a confirm.
# @model-risk check-P-054 H1: a carrier named in the same sentence as a decline word is excluded; over-excluding is the safe side.
CARRIER_NAME = re.compile(r"\b(?i:carrier)[\s_-]*(?:([ABCbc])|(a)(?!\s+(?:few|lot|bit|little|couple|number)\b))\b")  # the guard is for a lower-case "a" only
DECLINE = re.compile(r"declin|non-?renew|not renewing|cancel|refus|reject|turned (?:it )?down|no longer|not interested|will not|won't|would not|\bpassed\b"
                     r"|\bnot (?:a )?carrier|\bnever\b", re.I)


def excluded_carriers(report: dict) -> dict[str, str]:
    """@compliance M1 (D-099), P-054 (c): carrier -> where a note on the file excludes it ("not Carrier A", "declined by Carrier A").
    A senior cannot confirm one; they pick another market, or the note is fixed at source and the file re-run."""
    notes = [("carrier match note", match_note(report))]
    notes += [(r.get("field_id") or "a field", f"{r.get('value') or ''} {r.get('quote') or ''} {r.get('context') or ''}") for r in report.get("fields") or []]
    folder = prepare.INBOX_DIR / (report.get("submission") or "")
    for path in sorted(folder.iterdir()) if report.get("submission") and folder.is_dir() else []:
        try:
            notes.append((path.name, path.read_text()))
        except (UnicodeDecodeError, OSError):  # a scan or PDF has no text here; its extracted fields are read above
            continue
    found: dict[str, str] = {}
    for where, text in notes:
        for sentence in re.split(r"[.;!?\n]+", text):
            if DECLINE.search(sentence):
                for hit in CARRIER_NAME.finditer(sentence):
                    found.setdefault(f"carrier_{(hit.group(1) or hit.group(2)).lower()}", f'{where}: "{" ".join(sentence.split())[:120]}"')
    return found


def _reviewed_values(report: dict) -> str:
    """P-052 security review: the confirm is bound to the reviewed values too, so an edit or resolve logged after it voids it."""
    return hashlib.sha256(json.dumps([[r.get("field_id"), r.get("value")] for r in report.get("fields") or []]).encode()).hexdigest()


def market_confirmation(submission: str, run_hash: str) -> dict | None:
    """P-052: the latest confirm by a listed senior on this saved run (same run_hash) and the same reviewed values, or None."""
    path, ok = confirms_path(), seniors()
    try:
        report = reviewed(submission)
    except ValueError:
        return None
    values, excluded = _reviewed_values(report), excluded_carriers(report)
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.is_file() else []
    rows = [r for r in rows if isinstance(r, dict) and r.get("submission") == submission and r.get("underwriter_id") in ok
            and r.get("carrier") in CARRIERS and (r.get("reason") or "").strip() and run_hash and r.get("run_hash") == run_hash and r.get("reviewed_values") == values and r.get("carrier") not in excluded]
    return rows[-1] if rows else None


def confirm_market(submission: str, underwriter_id: str, carrier: str, reason: str, shown_hash: str = "") -> dict:
    """P-052 (D-098): a senior underwriter picks the carrier for a senior_referral file, with a reason. Logged with the run hash.
    It opens no send gate: the send still needs the approve on this run, the acknowledgments and the typed line."""
    submission, who, carrier, reason = (submission or "").strip(), (underwriter_id or "").strip(), (carrier or "").strip().lower(), (reason or "").strip()
    if who not in seniors():
        raise ValueError("only a senior underwriter on underwriters.json may confirm a market")
    if carrier not in CARRIERS:
        raise ValueError("pick carrier_a, carrier_b or carrier_c")
    if not reason:
        raise ValueError("a market confirm needs a written reason")
    report = reviewed(submission)
    if shown_hash and shown_hash != report.get("saved_hash"):
        raise ValueError("the saved run changed since this card was opened; reload the page and review again")
    problem = confirm_problem(report)
    if problem:
        raise ValueError(problem)
    if carrier in excluded_carriers(report):  # @compliance M1
        raise ValueError(f"the file's notes exclude {carrier} ({excluded_carriers(report)[carrier]}); pick another market, or fix the note at source and re-run the file")
    row = {"submission": submission, "action": "confirm_market", "underwriter_id": who, "underwriter_name": seniors()[who], "carrier": carrier,
           "reason": reason, "run_hash": report["saved_hash"], "reviewed_values": _reviewed_values(report), "at": datetime.now().astimezone().isoformat(timespec="seconds")}
    confirms_path().parent.mkdir(parents=True, exist_ok=True)
    with confirms_path().open("a") as handle:
        handle.write(json.dumps(row) + "\n")
    return row


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


def resolutions(submission: str, run_hash: str) -> dict:
    """B-324 (D-089): conflict field -> the latest "resolve" row by a listed underwriter on this run (same run_hash). Another run's do not count."""
    out = {}
    for row in decisions(submission, DECISIONS_LOG):
        field, value = (row.get("conflict_field") or "").strip(), (row.get("new_value") or "").strip()
        if (row.get("action") or "").strip() == "resolve" and field and value and run_hash and row.get("run_hash") == run_hash:
            out[field] = row
    return out


def with_resolutions(report: dict, submission: str = "") -> dict:
    """B-324: open conflicts the underwriter resolved on this run read as resolved, with the chosen or entered value; a resolved
    required field takes that value. Nothing else changes."""
    done = resolutions(submission or report.get("submission") or "", report.get("saved_hash") or "")
    if not done:
        return report
    conflicts = [{**c, "resolution": "resolved", "resolved_value": done[c["field"]]["new_value"].strip(), "resolved_by": done[c["field"]]["underwriter_id"]}
                 if c.get("resolution") != "resolved" and c.get("field") in done else c for c in report.get("conflicts") or []]
    fields = [{**r, "value": done[r["field_id"]]["new_value"].strip(), "resolved_by": done[r["field_id"]]["underwriter_id"]} if r.get("field_id") in done else r
              for r in report.get("fields") or []]
    return {**report, "conflicts": conflicts, "fields": fields}


def conflict_problem(report: dict) -> str:
    """B-324 (D-089): empty when no conflict is open (after logged resolutions on this run). Every actor, the user included."""
    open_ = [c.get("field") or "?" for c in report.get("conflicts") or [] if c.get("resolution") != "resolved"]
    if not open_:
        return ""
    return f"open conflict on {', '.join(open_)}: the underwriter must choose or enter the value on the card (logged with this run) before a send"


def reviewed(submission: str) -> dict:
    """The saved run (G2, hash-checked) with the underwriter's edits applied. Fields are all of prepare.FIELDS."""
    run = with_resolutions(prepare.read_saved_run(submission), submission)  # B-324: logged resolutions on this run
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
    if report.get("status") == prepare.MANUAL_INTAKE:  # P-055: no package for a manual-intake file, whatever was edited into it
        raise ValueError(f"no package: this file's status is {prepare.status_refusal(report)}")
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
    elif carrier == "senior_referral" and not confirm_problem(report) and market_confirmation(submission, report.get("saved_hash") or ""):  # P-052
        c = market_confirmation(submission, report["saved_hash"])
        carrier, label = c["carrier"], f"Senior referral — market confirmed by {c['underwriter_id']} {c.get('underwriter_name', '')}\nConfirm reason: {c['reason']}\n"
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


STALE = "Re-review needed: file changed since your approval"


def _current_hash(submission: str) -> str:
    try:
        return prepare.read_saved_run(submission)["saved_hash"]
    except ValueError:
        return ""


def _decision_problem(submission: str, run_hash: str | None = None) -> str:
    """Empty string if the latest logged decision is approve (D-053, D-055) made on the current saved run (P-026, D-069).

    Reads the one real log; takes nothing from the caller. An approve row with no run_hash, or another run's, does not count."""
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
    current = _current_hash(submission) if run_hash is None else run_hash
    if not current or last.get("run_hash") != current:
        return STALE
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
        report = with_resolutions(prepare.read_saved_run(submission), submission)  # B-324
    except ValueError:
        return "the saved extraction run for this file cannot be read"
    status = report.get("status")
    if status == "extraction_failed":
        return "extraction failed on this file"
    if status == "all_values_rejected":
        return "every value on this file was rejected"
    if status == prepare.MANUAL_INTAKE:
        return f"this file is {prepare.status_refusal(report)}: outside the pilot scope, a person reads it"
    if report.get("needs_human"):
        return "an unread page is still on the file"
    if conflict_problem(report):
        return conflict_problem(report)
    if not prepare.ready_to_route(report):  # P-041 (D-088): review pending is gated as complete was
        return "the file is not complete"
    if _route(report) == "senior_referral":  # T-107c (D-112): a P-052 senior-confirmed carrier passes; every gate above still applies
        return senior_confirm_problem(submission, report)
    if _route(report) not in {"carrier_a", "carrier_b", "carrier_c"}:
        return "the file is not in appetite"
    return ""


def senior_confirm_problem(submission: str, report: dict) -> str:
    """T-107c: empty unless the file is a senior referral with no valid senior market confirm on this run; then the card's reason (one text)."""
    if _route(report) != "senior_referral":
        return ""
    try:
        blocked = confirm_problem(reviewed(submission))
    except ValueError as exc:
        blocked = str(exc)
    if blocked:
        return f"no market can be confirmed on this file ({blocked})"
    return "" if market_confirmation(submission, report.get("saved_hash") or "") else "a senior referral needs a senior underwriter to confirm the market first"


def needs_review_ids(report: dict) -> list[str]:
    """Field ids of the rows the underwriter must acknowledge at approve (D-039, D-068): needs_review with a value. The one list."""
    ids = [r["field_id"] for r in report.get("fields") or [] if r.get("needs_review") and r.get("value")]
    if ((report.get("cooking") or {}).get("equipment") or {}).get("state") == "needs_review":  # P-029 (D-072)
        ids.append("cooking_equipment")
    return ids


def ack_problem(submission: str, report: dict) -> str:
    """D-068 (B-244): empty if the latest logged approve acknowledged every needs-review value of the saved run."""
    rows = decisions(submission, DECISIONS_LOG)
    done = set(rows[-1].get("acknowledged") or []) if rows and rows[-1].get("run_hash") == report.get("saved_hash") else set()  # P-026: another run's acknowledgments do not count
    open_ = [f for f in needs_review_ids(report) if f not in done]
    if not open_:
        return ""
    n = len(open_)
    return f"{n} value{'s' if n != 1 else ''} need{'' if n != 1 else 's'} review and {'are' if n != 1 else 'is'} not acknowledged ({', '.join(open_)})"


def sent_files(submission: str, out_dir: Path) -> list[Path]:
    """B-247: every package file sent for this submission, first send first."""
    first = out_dir / f"{submission}.md"
    more = sorted(out_dir.glob(f"{submission}-resend-*.md"), key=lambda p: int(p.stem.rsplit("-", 1)[1]))
    return ([first] if first.is_file() else []) + more


def sent_on(dest: Path) -> str:
    """B-248/B-250 (D-069): the one source of the sent date is the "Sent-on:" header written into the package at send,
    never file mtime (a copy or restore changes mtime). Older packages have no header: "not recorded"."""
    line = next((l for l in dest.read_text().splitlines()[:4] if l.startswith("Sent-on:")), "") if dest.is_file() else ""
    return line.split(":", 1)[1].strip() if line else "not recorded"


def sent_phrase(date_text: str) -> str:
    return "(date not recorded)" if date_text == "not recorded" else f"on {date_text}"


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
        raise ValueError(f"this file's status is {prepare.status_refusal(report)}; it cannot be sent, for any actor including the user")
    problem = prepare.manifest_problem(submission)  # P-020 (D-062): the input documents are the ones extracted, every actor
    if problem:
        raise ValueError(problem)
    problem = senior_confirm_problem(submission, with_resolutions(report, submission))  # T-107c (B-412): same order as the card, confirm before approve
    if problem:
        raise ValueError(problem)
    problem = _decision_problem(submission, report["saved_hash"])  # D-053 + P-026, every actor
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
    problem = ack_problem(submission, report)  # D-068 (B-244): every actor, user included
    if problem:
        raise ValueError(problem)
    problem = conflict_problem(with_resolutions(report, submission))  # B-324 (D-089): every actor, user included
    if problem:
        raise ValueError(problem)
    dest = out_dir / f"{submission}.md"
    resend = (resend_reason or "").strip()
    if dest.exists() and not resend:
        raise ValueError(f"already sent {sent_phrase(sent_on(dest))}; a second send needs an explicit resend with a written reason")
    if dest.exists():  # B-247: earlier package files are kept; the resend gets the next number
        dest = out_dir / f"{submission}-resend-{len(sent_files(submission, out_dir)) + 1}.md"
    body = build_package(submission, carrier, reason if name == "user" else "")  # T-085: raises on an empty required field or no carrier; nothing is written yet
    out_dir.mkdir(parents=True, exist_ok=True)
    who = "user (override)" if name == "user" else "account-manager"
    note = f"Reason: {reason.strip()}\n" if (reason or "").strip() else ""
    line = f"User-line: {user_line.strip()}\n" if name == "user" else ""
    again = f"Resend-reason: {resend}\n" if resend else ""
    today = datetime.now().astimezone()
    dest.write_text(f"Sent-by: {who}\nSent-on: {today.date().isoformat()}\n{line}{note}{again}\n{body}")
    # P-026/D-069: every send is logged (history panel), with the run it was built from
    SENDS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with SENDS_LOG.open("a") as handle:
        handle.write(json.dumps({"submission": submission, "actor": name, "date": today.date().isoformat(), "at": today.isoformat(timespec="seconds"), "run_hash": report["saved_hash"], "reason": (reason or "").strip(), "user_line": user_line.strip(), "package": str(dest), **({"resend": True, "resend_reason": resend} if resend else {}), **({"carrier_override": carrier.strip().lower(), "override_reason": reason.strip()} if (carrier or "").strip() else {})}) + "\n")
    return dest


if __name__ == "__main__":
    import json
    import tempfile

    def save(ext: Path, submission: str, status: str, complete=False, fields=None, needs_human=None, sprinklers=None, conflicts=None, class_lines=None):
        """A saved run shaped like prepare.write_drafts() writes, no model call. The hash is the reader's."""
        payload = {
            "submission": submission,
            "status": status,
            "error": "model call failed: HTTP 429 rate limit" if status == "extraction_failed" else None,
            "complete": bool(complete),
            "conflicts": conflicts or [],
            "needs_human": needs_human or [],
            "sprinklers": sprinklers,
            "fields": fields or [],
            "class_lines": class_lines,
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
        vals = {f: "x" for f in prepare.FIELDS} | {"operations": "office building", "tiv_building": "$1,000,000"} | over
        return [{"field_id": f, "value": v, "source": "application.md", "start": 0, "end": 3} for f, v in vals.items()]

    office = full()
    LINE = "send to carrier {}".format
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ext = tmp / "extractions"
        log = tmp / "decisions.jsonl"

        seq = iter(range(1, 1000))

        def decide(sub: str, action: str, reason: str = "", who: str = "UW-001", n: int | None = None):
            row = {"seq": next(seq) if n is None else n, "submission": sub, "action": action, "underwriter_id": who, "reason": reason, "run_hash": _current_hash(sub)}
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

            # P-055 (D-105): a manual-intake file is refused for every actor with its reasons, even if every field was filled in by hand.
            save(ext, "SUB-103", prepare.MANUAL_INTAKE, complete=True, fields=office, sprinklers="no")
            raw_mi = json.loads((ext / "SUB-103.json").read_text())
            raw_mi["scope"] = prepare.scope.detect([{"name": "application.jpg", "text": "", "needs_human": True}])
            raw_mi["saved_hash"] = prepare.hash_payload(raw_mi)
            (ext / "SUB-103.json").write_text(json.dumps(raw_mi))
            for actor in ("user", "@account-manager", "ai-engineer-assistant"):
                try:
                    send_to_carrier("SUB-103", actor, dest_dir, reason="ready", user_line=LINE("SUB-103"))
                    raise SystemExit(f"manual intake must be refused for {actor}")
                except ValueError as exc:
                    assert "manual intake (scanned application" in str(exc), exc
            assert "manual intake (scanned application" in agency_problem("SUB-103")
            assert "manual intake" in confirm_problem(reviewed("SUB-103"))
            try:
                build_package("SUB-103")
                raise SystemExit("no package for a manual-intake file")
            except ValueError as exc:
                assert "manual intake" in str(exc), exc
            assert not list(dest_dir.iterdir()), "nothing was sent"

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

            # The account-manager rules still gate a normal file.
            save(ext, "SUB-193", "complete", complete=True, fields=office, sprinklers="no")
            save(ext, "SUB-194", "incomplete", complete=False, fields=full(year_built=""))
            for sub in ("SUB-001", "SUB-193", "SUB-194"):
                decide(sub, "approve")
            try:
                send_to_carrier("SUB-193", "account-manager", dest_dir)
                raise SystemExit("missing reason should fail")
            except ValueError:
                pass
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
                handle.write(json.dumps({"seq": 801, "submission": "SUB-195", "action": "approve", "underwriter_id": "UW-001", "reason": "", "run_hash": _current_hash("SUB-195")}) + "\n")
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

            # P-052 (D-098): only a senior confirms a senior_referral market, with a reason, bound to the run; the send gate still applies.
            save(ext, "SUB-410", "complete", complete=True, fields=full(operations="family restaurant, 60 seats"))
            save(ext, "SUB-411", "complete", complete=True, fields=full(operations="pub and kitchen"))
            save(ext, "SUB-412", "complete", complete=True, fields=full(operations="apartments, 8 units"))  # held: sprinkler answer missing
            assert set(seniors()) == {"UW-001"} and "UW-002" in underwriters()
            for i, ops in enumerate(("office building, no utilities", "office, unoccupied", "fully vacant building", "office, utilities disconnected")):  # compliance H1
                save(ext, f"SUB-42{i}", "complete", complete=True, fields=full(operations=ops))
                assert "AG:51" in confirm_problem(reviewed(f"SUB-42{i}")), ops
            save(ext, "SUB-440", "complete", complete=True, fields=full(operations="Dining venue"), class_lines={"line_of_business": "restaurant and bar", "cooking_operations": "Two fryers"})  # H1 (D-112): SUB-186 shape
            assert match_note(reviewed("SUB-440")).find("R2") > 0 and '"bar"' in confirm_problem(reviewed("SUB-440")), "H1: a bar word on the Line of business line refuses the confirm"
            try:
                confirm_market("SUB-440", "UW-001", "carrier_b", "x", _current_hash("SUB-440"))
                raise SystemExit("H1: confirm must be refused")
            except ValueError as exc:
                assert '"bar"' in str(exc), exc
            assert "no market can be confirmed" in agency_problem("SUB-440") and '"bar"' in agency_problem("SUB-440")
            for args in (("SUB-410", "UW-002", "carrier_b", "x"), ("SUB-410", "user", "carrier_b", "x"), ("SUB-410", "UW-001", "carrier_z", "x"),
                         ("SUB-410", "UW-001", "carrier_b", " "), ("SUB-411", "UW-001", "carrier_b", "x"), ("SUB-412", "UW-001", "carrier_c", "x"),
                         ("SUB-401", "UW-001", "carrier_b", "x"), ("SUB-410", "UW-001", "carrier_b", "x", "stale-hash")):
                try:
                    confirm_market(*args)
                    raise SystemExit(f"confirm {args} must be refused")
                except ValueError:
                    pass
            assert not confirms_path().exists() and market_confirmation("SUB-410", _current_hash("SUB-410")) is None
            try:
                send_to_carrier("SUB-410", "user", dest_dir, user_line=LINE("SUB-410"))
                raise SystemExit("no confirm: a senior referral names no carrier")
            except ValueError as exc:
                assert "confirm the market first" in str(exc), exc  # T-107c (B-412): the card's order, not "no logged decision"
            assert agency_problem("SUB-410") == "a senior referral needs a senior underwriter to confirm the market first"
            assert "appetite" not in agency_problem("SUB-411") and "no market can be confirmed" in agency_problem("SUB-411"), "pub: no confirm, real reason"
            c = confirm_market("SUB-410", "UW-001", "carrier_b", "3 clean years seen on the loss runs", _current_hash("SUB-410"))
            assert c["run_hash"] == _current_hash("SUB-410") and c["underwriter_name"].startswith("Dana Reyes")
            assert "confirm the market" not in agency_problem("SUB-410"), "T-107c: confirmed, so the appetite text is gone"
            for gate in ("no approve", "no line"):
                try:
                    send_to_carrier("SUB-410", "user", dest_dir, reason="x", user_line="" if gate == "no line" else LINE("SUB-410"))
                    raise SystemExit(f"{gate}: the normal send gate must still refuse")
                except ValueError as exc:
                    assert gate != "no approve" or "no logged decision" in str(exc), exc  # T-107c: confirmed, so approve is the next gate
                if gate == "no approve":
                    decide("SUB-410", "approve")
            am_dir = dest_dir.parent / "am" / "to-carrier"  # T-107c: the account manager passes on the confirmed carrier; own folder so the user send below is the first one there
            try:
                send_to_carrier("SUB-410", "account-manager", am_dir)
                raise SystemExit("the account manager must write a reason")
            except ValueError as exc:
                assert "reason" in str(exc), exc
            assert "Carrier: carrier_b" in send_to_carrier("SUB-410", "account-manager", am_dir, reason="complete, senior confirmed carrier_b").read_text()
            body = send_to_carrier("SUB-410", "user", dest_dir, user_line=LINE("SUB-410")).read_text()
            assert "Carrier: carrier_b" in body and "market confirmed by UW-001" in body and "3 clean years" in body
            assert agency_problem("SUB-410") == "", "T-107c: a senior-confirmed carrier passes the account-manager check"
            assert market_confirmation("SUB-410", _current_hash("SUB-410"))
            with log.open("a") as handle:  # security review: an edit after the confirm voids it, on the same run
                handle.write(json.dumps({"seq": next(seq), "submission": "SUB-410", "action": "edit", "underwriter_id": "UW-002", "reason": "typo", "field_id": "operations", "new_value": "roofing contractor", "run_hash": _current_hash("SUB-410")}) + "\n")
            assert market_confirmation("SUB-410", _current_hash("SUB-410")) is None
            save(ext, "SUB-410", "complete", complete=True, fields=full(operations="family restaurant, 70 seats"))  # a new run: the old confirm does not count
            assert market_confirmation("SUB-410", _current_hash("SUB-410")) is None
            # @compliance M1 (D-099): a carrier the note excludes ("not Carrier A") cannot be confirmed, and a logged confirm for it does not count.
            save(ext, "SUB-430", "complete", complete=True, fields=full(operations="office with a medical clinic"))
            assert set(excluded_carriers(reviewed("SUB-430"))) == {"carrier_a"}
            try:
                confirm_market("SUB-430", "UW-001", "carrier_a", "x", _current_hash("SUB-430"))
                raise SystemExit("M1: an excluded carrier must be refused")
            except ValueError as exc:
                assert "notes exclude carrier_a" in str(exc), exc
            with confirms_path().open("a") as handle:
                handle.write(json.dumps({"submission": "SUB-430", "underwriter_id": "UW-001", "carrier": "carrier_a", "reason": "x", "run_hash": _current_hash("SUB-430"), "reviewed_values": _reviewed_values(reviewed("SUB-430"))}) + "\n")
            assert market_confirmation("SUB-430", _current_hash("SUB-430")) is None
            assert confirm_market("SUB-430", "UW-001", "carrier_b", "medical tenant fits B", _current_hash("SUB-430"))["carrier"] == "carrier_b"
            # P-054 (c): a producer remark in a document or a field excludes too ("declined by Carrier A"); a loss run from Carrier A does not.
            (tmp / "inbox" / "SUB-432").mkdir(parents=True)
            (tmp / "inbox" / "SUB-432" / "email.md").write_text("Prior carrier: Carrier A loss run attached. Renewal was declined by Carrier A in 2025. Quote declined by carrier a few times.\n")
            save(ext, "SUB-432", "complete", complete=True, fields=full(operations="office and casino"))
            assert set(excluded_carriers(reviewed("SUB-432"))) == {"carrier_a"} and "email.md" in excluded_carriers(reviewed("SUB-432"))["carrier_a"], excluded_carriers(reviewed("SUB-432"))
            # check-P-054 H1: the SUB-147 email and the phrasings the first pattern missed; "carrier a few times" and a plain loss run do not exclude.
            for i, remark in enumerate(("coming to you guys from Carrier A, they are not renewing the account with them", "declined by carrier a in 2025",
                                        "Carrier A has declined", "Carrier A: declined", "Carrier A - declined 2024", "Carrier A (declined)",
                                        "Prior carrier Carrier A, non-renewed", "Carrier A not interested", "Carrier A no longer writes this class",
                                        "non-renewal notice from Carrier A", "Not a Carrier A risk", "Carrier A passed",
                                        "declined by Carrier A while the loss run was open", "Carrier A new business: declined")):
                (tmp / "inbox" / f"SUB-44{i:02d}").mkdir(parents=True)
                (tmp / "inbox" / f"SUB-44{i:02d}" / "email.md").write_text(remark + "\n")
                save(ext, f"SUB-44{i:02d}", "complete", complete=True, fields=full(operations="office and casino"))
                assert set(excluded_carriers(reviewed(f"SUB-44{i:02d}"))) == {"carrier_a"}, (remark, excluded_carriers(reviewed(f"SUB-44{i:02d}")))
            (tmp / "inbox" / "SUB-4499").mkdir(parents=True)
            (tmp / "inbox" / "SUB-4499" / "email.md").write_text("Carrier A loss run attached, five years. We called carrier a few times about the quote.\n")
            save(ext, "SUB-4499", "complete", complete=True, fields=full(operations="office and casino"))
            assert not excluded_carriers(reviewed("SUB-4499")), excluded_carriers(reviewed("SUB-4499"))
            try:
                confirm_market("SUB-432", "UW-001", "carrier_a", "x", _current_hash("SUB-432"))
                raise SystemExit("P-054 (c): a producer remark must exclude")
            except ValueError as exc:
                assert "email.md" in str(exc), exc
            save(ext, "SUB-433", "complete", complete=True, fields=full(operations="office and casino", loss_run_valued_through="Carrier B will not renew"))
            assert set(excluded_carriers(reviewed("SUB-433"))) == {"carrier_b"}
            save(ext, "SUB-431", "complete", complete=True, fields=full(operations="office and casino"))  # P-053: Carrier A suggested, so a senior may confirm it
            assert not excluded_carriers(reviewed("SUB-431")) and confirm_market("SUB-431", "UW-001", "carrier_a", "casino is a lobby slot room, seen", _current_hash("SUB-431"))

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
            assert len(log.read_text().splitlines()) == 18  # history untouched by the sends (16 + the P-052 approve and edit)

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
            assert "Resend-reason" not in (dest_dir / "SUB-320.md").read_text()  # B-247: first file unchanged
            assert "Resend-reason: carrier lost the file" in (dest_dir / "SUB-320-resend-2.md").read_text() and last["package"].endswith("SUB-320-resend-2.md")
            # D-068 (B-244): a needs-review value (SUB-038 shape: low-confidence scan rows) blocks the send until the approve acknowledged it.
            low = full(named_insured="Acme")
            low = [{**r, "needs_review": True} if r["field_id"] in ("named_insured", "operations") else r for r in low]
            save(ext, "SUB-321", "complete", complete=True, fields=low, sprinklers="no")
            decide("SUB-321", "approve")
            try:
                send_to_carrier("SUB-321", "user", dest_dir, user_line=LINE("SUB-321"))
                raise SystemExit("unacknowledged needs-review values must refuse the send, for the user too")
            except ValueError as exc:
                assert "2 values need review and are not acknowledged (named_insured, operations)" in str(exc), exc
            with log.open("a") as handle:
                handle.write(json.dumps({"seq": 9001, "submission": "SUB-321", "action": "approve", "underwriter_id": "UW-001", "reason": "", "acknowledged": ["named_insured", "operations"], "run_hash": _current_hash("SUB-321")}) + "\n")
            assert send_to_carrier("SUB-321", "user", dest_dir, user_line=LINE("SUB-321")).exists()
            # P-026 (D-069, B-220): approve + acknowledge, then a re-save with a changed value -> refused; approve + acknowledge again -> allowed.
            save(ext, "SUB-322", "complete", complete=True, fields=low, sprinklers="no")
            def approve_ack(n):
                with log.open("a") as handle:
                    handle.write(json.dumps({"seq": n, "submission": "SUB-322", "action": "approve", "underwriter_id": "UW-001", "reason": "", "acknowledged": ["named_insured", "operations"], "run_hash": _current_hash("SUB-322")}) + "\n")
            approve_ack(9100)
            save(ext, "SUB-322", "complete", complete=True, fields=[{**r, "value": "Other Co"} if r["field_id"] == "named_insured" else r for r in low], sprinklers="no")
            for actor, kw in (("user", {"user_line": LINE("SUB-322")}), ("account-manager", {"reason": "ready"})):
                try:
                    send_to_carrier("SUB-322", actor, dest_dir, **kw)
                    raise SystemExit(f"a re-saved run must refuse the send for {actor}")
                except ValueError as exc:
                    assert str(exc) == STALE, exc
            approve_ack(9101)
            assert send_to_carrier("SUB-322", "user", dest_dir, user_line=LINE("SUB-322")).exists()
            # an approve row with no run_hash (an old row) does not count, even with every acknowledgment
            save(ext, "SUB-323", "complete", complete=True, fields=low, sprinklers="no")
            with log.open("a") as handle:
                handle.write(json.dumps({"seq": 9200, "submission": "SUB-323", "action": "approve", "underwriter_id": "UW-001", "acknowledged": ["named_insured", "operations"]}) + "\n")
            try:
                send_to_carrier("SUB-323", "user", dest_dir, user_line=LINE("SUB-323"))
                raise SystemExit("an approve with no run hash must not count")
            except ValueError as exc:
                assert str(exc) == STALE, exc
            # B-248: the sent date is the package header, not file mtime.
            import os
            sent = dest_dir / "SUB-322.md"
            os.utime(sent, (0, 0))
            assert sent_on(sent) == datetime.now().astimezone().date().isoformat() and "Sent-on:" in sent.read_text()
            (dest_dir / "old.md").write_text("Sent-by: user\n\nPackage old\n")
            assert sent_on(dest_dir / "old.md") == "not recorded"
            assert {json.loads(x)["run_hash"] for x in SENDS_LOG.read_text().splitlines()} - {""}
            (tmp / "inbox" / "SUB-320" / "late-loss-run.pdf").write_bytes(b"added after extraction")
            try:
                send_to_carrier("SUB-320", "user", dest_dir, user_line=LINE("SUB-320"))
                raise SystemExit("a document added after extraction must refuse the send")
            except ValueError as exc:
                assert "changed since extraction" in str(exc), exc

            # B-324 (D-089): a review-pending file with an open conflict is not sent by anyone until the underwriter resolves it on this run.
            sq = {"field": "square_feet", "values": [{"value": "16800", "source": "email.md"}, {"value": "14200", "source": "application.md"}], "resolution": "unresolved"}
            save(ext, "SUB-330", prepare.REVIEW_PENDING, fields=office, sprinklers="no", conflicts=[sq])
            decide("SUB-330", "approve")
            assert "open conflict on square_feet" in agency_problem("SUB-330")
            for actor in ("user", "account-manager"):
                try:
                    send_to_carrier("SUB-330", actor, dest_dir, reason="ready", user_line=LINE("SUB-330"))
                    raise SystemExit(f"B-324: an open conflict must refuse the send for {actor}")
                except ValueError as exc:
                    assert "open conflict on square_feet" in str(exc), exc
            resolve = lambda run_hash: log.open("a").write(json.dumps({"seq": next(seq), "submission": "SUB-330", "action": "resolve", "underwriter_id": "UW-001", "reason": "",
                                                                       "conflict_field": "square_feet", "new_value": "14200", "run_hash": run_hash}) + "\n")
            resolve("another-run")
            decide("SUB-330", "approve")
            assert conflict_problem(with_resolutions(prepare.read_saved_run("SUB-330"))), "another run's resolution does not count"
            resolve(_current_hash("SUB-330"))
            assert with_resolutions(prepare.read_saved_run("SUB-330"))["conflicts"][0]["resolved_value"] == "14200"
            try:
                send_to_carrier("SUB-330", "user", dest_dir, user_line=LINE("SUB-330"))
                raise SystemExit("a resolve after the approve: the latest decision must be an approve again")
            except ValueError as exc:
                assert "not approve" in str(exc), exc
            decide("SUB-330", "approve")
            assert send_to_carrier("SUB-330", "user", dest_dir, user_line=LINE("SUB-330")).is_file(), "resolved on this run, then approved: sent"
        finally:
            prepare.EXTRACT_DIR, DECISIONS_LOG, SENDS_LOG, prepare.INBOX_DIR = saved_dir, saved_log, saved_sends, saved_inbox
    # P-029 (D-072): an ambiguous cooking line joins the one needs-review list, so the send gate waits for its acknowledgment.
    assert needs_review_ids({"fields": [], "cooking": {"equipment": {"state": "needs_review"}}}) == ["cooking_equipment"]
    assert needs_review_ids({"fields": [], "cooking": {"equipment": {"state": "yes"}}}) == []
    print("package ok")
