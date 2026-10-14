"""Step 6 — one page of the queue. Does not bind and does not send to a carrier.

The React workbench in frontend/ is a different app and is not modified.

# ponytail: stdlib HTML plus one JSONL log. Split the page when a second screen exists.

Run: python underwriting_pipeline/app/workbench.py
Serve: python underwriting_pipeline/app/workbench.py --serve
"""

import html
import json
import os
import re
import shutil
import sys
import tempfile
import threading
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "underwriting_pipeline" / "ai"))
sys.path.insert(0, str(ROOT / "underwriting_pipeline" / "models"))
sys.path.insert(0, str(ROOT / "underwriting_pipeline" / "app"))
import llm_extract
import package
import points
import prepare
import quotes

INBOX = ROOT / "simulation" / "inbox"
PAGE = Path(__file__).resolve().parent / "workbench.html"
LOG = package.DECISIONS_LOG
PENDING = ROOT / "simulation" / "pending-approval"  # missing-info drafts waiting for approval
TO_PRODUCER = ROOT / "simulation" / "to-producer"
TO_CARRIER = ROOT / "simulation" / "to-carrier"
BANNER = ""  # set by serve(); the sandbox screenshots label the page with it
MESSAGES: dict[str, tuple[bool, str]] = {}  # submission -> (ok, plain-words result of the last action); shown once
# D-065 item 5: one line per user-visible feature: date, task or proposal, decision number, what an underwriter sees.
WHATS_NEW = (
    ("2026-10-14", "P-026", "D-069", "Every approve logs the saved run's hash; a re-saved file shows \"Re-review needed: file changed since your approval\" and the send is refused for everyone until you approve and acknowledge again."),
    ("2026-10-14", "B-248", "D-069", "The sent date comes from one place, the Sent-on line in the package file, on the card and in quote tracking alike (older packages show \"not recorded\")."),
    ("2026-10-14", "B-252", "D-069", "A sandbox run (--sandbox) writes the page, logs and outboxes into a temporary copy; the real files are never touched."),
    ("2026-10-14", "Session B", "D-069", "Each card has one History panel (decisions, acknowledgments, sends, resends: who, why, when, run hash), subjectivity closures with the \"evidence only\" label, a Suggested market field, and a model and prompt version footer."),
    ("2026-10-14", "B-244", "D-068", "A low-confidence scan value is a needs-review value: the send is refused for everyone until the latest approve acknowledged every one; the card names them."),
    ("2026-10-14", "B-247", "D-068", "A resend writes a new package file (SUB-###-resend-N.md); earlier files are kept and the card lists every package file sent."),
    ("2026-10-14", "B-249", "D-068", "The send form is hidden until an approve is logged; the card says \"Approve first\"."),
    ("2026-10-14", "B-231", "D-067", "Saved-run cards come first; every card with no usable saved run is folded into one closed section \"No saved run (N)\" with the reason and how a run is created."),
    ("2026-10-14", "B-232", "D-067", "The Send to carrier form names the carrier before you confirm; when there is no carrier or the file is refused or incomplete, the card says why there is no send."),
    ("2026-10-14", "B-233", "D-067", "A package already sent shows \"Already sent on <date> to <carrier>\"; a second send is refused unless you tick resend and write a reason, which is logged."),
    ("2026-10-14", "P-025", "D-067", "A scan read below the confidence line (0.50 to 0.74) is kept, marked \"Low-confidence scan read — check against the page\", and must be ticked at approve."),
    ("2026-10-14", "P-016", "D-064", "Needs-review values show their reason and cited text; approve needs each one ticked; unread pages are listed."),
    ("2026-10-14", "D-066 item 10", "D-066", "The page shows only the saved run (status, hash check, manifest check). It never runs extraction or a model call."),
    ("2026-10-14", "D-066 items 2/4/8", "D-066", "Every refused decision or send is shown on its card in plain words with the reason. No bare error pages."),
    ("2026-10-14", "D-066 item 1", "D-066", "Send to carrier on the card: type the exact line \"send to carrier SUB-###\"; it goes through the same send gate."),
    ("2026-10-14", "D-066 item 13", "D-066, D-050", "The missing-info draft shows on the card with an approve action (user override; refused for failed or all-rejected files)."),
)
_LOG_LOCK = threading.Lock()  # ponytail: one process writes the log; a file lock if a second writer appears


def _ops(report: dict) -> str:
    for row in report["fields"]:
        if row["field_id"] == "operations" and row["value"]:
            return row["value"].lower()
    return ""


# D-059 as amended by D-060. Whole word or exact phrase, case-insensitive, never substring.
# Spanish entries are translations of sourced classes only (D-060); @responsible-ai review is B-197.
# ponytail: plain lists in code; move to a data file when @head-of-underwriting edits them often.
PROHIBITED = ("bar", "bars", "nightclub", "nightclubs", "tavern", "taverns", "cantina", "taberna", "antro", "discoteca",
              "cannabis", "marijuana", "marihuana", "dispensary", "dispensario", "fireworks", "firework", "explosives", "explosive",
              "fuegos artificiales", "explosivos", "armed security", "armed guard", "seguridad armada", "guardia armado",
              "student housing", "subsidized housing", "alojamiento estudiantil", "vivienda subsidiada")  # CAG/AG:45-49
CLASSES = {
    "a": ("office", "offices", "oficina", "oficinas", "retail", "retail store", "dry retail", "storefront", "comercio minorista",
          "tienda minorista", "wholesale", "light wholesale", "mayoreo", "mayorista"),
    "b": ("restaurant", "restaurants", "restaurante", "restaurantes", "cafe", "café", "cafeteria", "cafetería", "coffee shop", "diner", "deli",
          "bakery", "panaderia", "panadería", "pizzeria", "pizzería", "pizza", "steakhouse", "barbecue", "bbq", "taqueria", "taquería",
          "tacos", "taco"),
    "contractor": ("contractor", "contractors", "contratista", "roofing", "roofer", "techado", "techador", "handyman", "painter", "painting",
                   "pintor", "pintura", "carpenter", "carpentry", "carpintero", "carpintería", "flooring", "drywall", "plumbing", "electrician"),
    "habitational": ("habitational", "habitacional", "apartment", "apartments", "apartamento", "apartamentos", "flats", "multifamily",
                     "multifamiliar", "duplex", "triplex", "fourplex"),
}
CAP_A, CAP_B, PILOT_TIV = 5_000_000, 2_000_000, 5_000_000  # B cap provisional (@actuary, D-060); caps inclusive
OUT_TIV = "outside pilot TIV limit (AG:16)"


def _has(text: str, words) -> bool:
    return any(re.search(rf"(?<!\w){re.escape(w)}(?!\w)", text) for w in words)


AREA_UNIT = re.compile(r"(?<![a-z])(sq\.?\s*f(?:ee|oo)?t\.?|sqft|sf|square\s+f(?:ee|oo)t)(?![a-z])", re.I)


def _tiv(report: dict) -> int | None:
    """D-061: the existing normalizer (220k, $1.2M). None when missing, blank, "TBD" or unreadable."""
    for row in report["fields"]:
        if row["field_id"] == "tiv_building":
            if AREA_UNIT.search(row["value"] or ""):
                return None  # B-209 (P-022, D-063): an area is not a dollar amount
            return prepare.amount_value(row["value"] or "")
    return None


def match(report: dict) -> dict:
    """route: carrier_a/b/c, no_match, hold or senior_referral. overridable only for no_match (D-057). Never declines."""
    ops = _ops(report)

    def out(route, note="", suggested="", overridable=False):
        return {"route": route, "note": note, "suggested": suggested, "overridable": overridable}

    if ops and _has(ops, PROHIBITED):
        return out("no_match", "prohibited class (AG:45-49)")
    if not report["complete"] or not ops:
        return out("hold", "missing information")
    tiv = _tiv(report)
    if tiv is None or tiv <= 0:
        return out("hold", "TIV missing or unreadable")  # D-061, B-203 (D-062): never read as 0 or negative
    hit = [k for k, words in CLASSES.items() if _has(ops, words)]
    if not hit:
        return out("no_match", "readable class on no carrier list", overridable=True)
    if len(hit) > 1:
        return out("senior_referral", "class matches more than one carrier: " + ", ".join(hit))
    kind = hit[0]
    if kind == "contractor":
        return out("senior_referral", "contractor (AG:38); suggested market: carrier_b" + (f"; {OUT_TIV}" if tiv > PILOT_TIV else ""), suggested="carrier_b")
    if kind == "habitational":
        spr = report.get("sprinklers")
        if spr == "yes" or "sprinklers yes" in ops or (_has(ops, ("sprinklered",)) and spr != "no"):
            return out("senior_referral", OUT_TIV) if tiv > PILOT_TIV else out("carrier_c")
        if spr == "no" or _has(ops, ("unsprinklered", "no sprinklers", "sprinklers no")):
            return out("senior_referral", "habitational without sprinklers (AG:61)")
        return out("hold", "habitational: sprinkler answer missing")
    if tiv > PILOT_TIV:
        return out("senior_referral", OUT_TIV)
    if kind == "a":
        return out("carrier_a")
    if tiv > CAP_B:
        return out("senior_referral", "over Carrier B TIV cap $2,000,000 (provisional)")
    return out("carrier_b", "3 clean years not checked")


def route(report: dict) -> str:
    return match(report)["route"]


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
    try:
        text = path.read_text()
    except UnicodeDecodeError:  # a scan or other binary source has no text to quote; the saved quote is shown instead
        return ""
    return text[row["start"] : row["end"]]


def saved_report(name: str) -> tuple[dict | None, str]:
    """Item 10 (D-066): the last saved run only. Returns (report, "") or (None, plain reason). No extraction, no model call."""
    try:
        saved = prepare.read_saved_run(name)
    except ValueError as exc:
        return None, str(exc)
    fields = saved.get("fields") or []
    return {
        **saved,
        "fields": fields,
        "conflicts": saved.get("conflicts") or [],
        "missing": [r["field_id"] for r in fields if not r.get("value")],
        "extra": [],  # not stored in the saved run
        "locations": None,  # not stored in the saved run
        "status_reason": prepare.REJECT_REASON if saved.get("status") == "all_values_rejected" else None,
    }, ""


def load_queue(only: str | None = None) -> list[dict]:
    folders = sorted(p for p in INBOX.iterdir() if p.is_dir() and p.name.startswith("SUB-"))
    if only:
        folders = [folder for folder in folders if folder.name == only]
    rows = []
    for folder in folders:
        report, problem = saved_report(folder.name)
        files = sorted(p.name for p in folder.iterdir() if p.is_file())
        ignored = [name for name in files if not name.endswith((".md", ".csv"))]
        row = {"id": folder.name, "report": report, "saved_problem": problem, "files": files, "ignored": ignored}
        if report is not None:
            row.update(
                manifest=prepare.manifest_problem(folder.name, inbox=INBOX),
                route=route(report),
                note=match(report)["note"],
                suggested=match(report)["suggested"],
                score=points.score(facts(report)),
                snippets={r["field_id"]: snippet(folder, r) for r in report["fields"]},
            )
        rows.append(row)
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
    field_id, new_value = (payload.get("field_id") or "").strip(), (payload.get("new_value") or "").strip()
    if action != "edit" and (field_id or new_value):
        raise ValueError("field_id and new_value belong to an edit")
    if field_id or new_value:  # D-056 (B-139): an edit that changes a field stores the field and its new value
        if field_id not in prepare.FIELDS or not new_value:
            raise ValueError(f"an edit of a field needs field_id (one of {', '.join(prepare.FIELDS)}) and a new value")
    if action == "approve":
        submission = (payload.get("submission") or "").strip()
        # T-071: read the file's status from the last saved run itself. An approve is refused on either
        # refused status, and when nothing is saved or the run cannot be read (current_status raises).
        saved = prepare.read_saved_run(submission)
        status = saved["status"]
        if status in prepare.REFUSED_STATUSES:
            raise ValueError(f"this file's status is {status}; an approve is refused for it")
        # D-039: every value flagged needs-review is listed at approve; each must be acknowledged, and is logged.
        shown = (payload.get("run_hash") or "").strip()  # the run the card showed; the log stores the run read now (P-026)
        if shown and shown != saved["saved_hash"]:
            raise ValueError("the saved run changed since this card was opened; reload the page and review again")
        listed = needs_review_ids(saved)
        unacked = [f for f in listed if f not in (payload.get("ack") or [])]
        if unacked:
            raise ValueError(f"acknowledge every needs-review value before approving: {', '.join(unacked)}")
        payload = {**payload, "acknowledged": listed, "run_hash": saved["saved_hash"]}
    with _LOG_LOCK:
        if action == "approve" and not reason:
            # D-053: an approve after a decline needs a written reason; refused here, not only at the send.
            if any(r.get("action") == "decline" for r in package.decisions(submission, log_path)):
                raise ValueError("an approve after a decline needs a written reason")
        return _append(payload, action, actor, reason, log_path)


needs_review_ids = package.needs_review_ids  # D-068: one list, shared with the send gate


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
        **({"run_hash": payload["run_hash"]} if action == "approve" else {}),
        **({"acknowledged": payload["acknowledged"]} if payload.get("acknowledged") else {}),
        **({"field_id": payload["field_id"].strip(), "new_value": payload["new_value"].strip()} if (payload.get("field_id") or "").strip() else {}),
        "date": date.today().isoformat(),
        "at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "ai_version": ai_version(),
        "bound": False,
        "sent_to_carrier": False,
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a") as handle:
        handle.write(json.dumps(row) + "\n")
    return row


REFUSED_AS = {"/decision": "Decision refused", "/close-subjectivity": "Not closed", "/send": "Send refused", "/approve-draft": "Request not approved"}


def act(path: str, payload: dict) -> tuple[str, bool, str]:
    """D-066 items 2/4/8: run one POST action. Returns (submission, ok, plain-words message); a refusal never raises."""
    sub = (payload.get("submission") or "").strip()
    try:
        if path in ("/send", "/approve-draft") and not re.fullmatch(r"SUB-\d+", sub):
            raise ValueError("no such submission id on the form")
        if path == "/decision":
            row = record_decision(payload, LOG)
            return sub, True, f"Decision recorded: {row['action']} by {row['underwriter_id']}."
        if path == "/close-subjectivity":
            quotes.close_subjectivity(*(payload.get(k, "") for k in ("submission", "carrier", "subjectivity", "underwriter_id", "reason")))
            return sub, True, "Subjectivity closed and logged."
        if path == "/send":  # item 1: the same gate as every send; the actor is the user, the line is typed on the card
            dest = package.send_to_carrier(sub, "user", TO_CARRIER, user_line=payload.get("user_line", ""), resend_reason=payload.get("resend_reason", ""))
            return sub, True, f"Sent: package {dest.name} written to to-carrier. Not bound."
        dest = prepare.approve(PENDING / f"{sub}.md", "user", TO_PRODUCER, payload.get("reason", ""))  # item 13: D-050, user override
        return sub, True, f"Approved: request {dest.name} written to to-producer. It lists only missing items and declines nothing."
    except (ValueError, OSError) as exc:
        return sub, False, f"{REFUSED_AS.get(path, 'Refused')}: {exc}"


def _confidence(row: dict) -> str:
    used = row.get("confidence", "")
    model = row.get("model_confidence")
    if model is None or model == used:
        return str(used)
    return f"{used} ocr / {model} model"


def _folded(cards: list[str]) -> str:
    """B-231: every card with no usable saved run, in one closed section with a count and how a run is created."""
    if not cards:
        return ""
    return (
        f"<details{' open' if 'role=\"alert\"' in ''.join(cards) else ''}><summary><b>No saved run ({len(cards)})</b></summary>"
        "<p>These files have no usable saved extraction run, so the workbench shows nothing for them and offers no decision or send. "
        "A run is created outside this page: the AI Engineer (or @ai-engineer-assistant for the team) runs "
        "<code>python underwriting_pipeline/ai/prepare.py simulation/inbox simulation/pending-approval deliverables/data-engineer/conflicts</code> "
        "with the model host set. Reload the page afterwards. This page never runs extraction.</p>"
        + "".join(cards) + "</details>"
    )


def _msg(messages: dict, key: str) -> str:
    if key not in messages:
        return ""
    ok, text = messages[key]
    return f'<p class="msg {"ok" if ok else "bad"}" role="alert">{html.escape(text)}</p>'


def _no_send_reason(item: dict, report: dict, refused: bool) -> str:
    """B-232: plain words for why this card has no send form; empty when a send can be offered."""
    if refused:
        return f"this file's status is {report.get('status')}; it cannot be sent"
    if item.get("manifest"):
        return f"documents changed since extraction ({item['manifest']})"
    if item["route"] not in package.CARRIERS:
        return f"the carrier match is {item['route']}" + (f" ({item['note']})" if item.get("note") else "") + ", so no carrier is named"
    if not report.get("complete"):
        return "the file is incomplete (a required field is empty)"
    return ""


def _send_html(item: dict, report: dict, refused: bool, manifest: str) -> str:
    sid = html.escape(item["id"])
    why = _no_send_reason(item, report, refused)
    if why:
        return f'<h3>Send to carrier</h3><p class="bad">No send: {html.escape(why)}.</p>'
    problem = package._decision_problem(item["id"], report.get("saved_hash") or "")
    if problem == package.STALE:  # P-026 (D-069)
        return f'<h3>Send to carrier</h3><p class="bad">{package.STALE}. No send form until you approve again and tick each needs-review value.</p>'
    if problem:  # B-249 (D-068): no form before an approve is logged
        return f'<h3>Send to carrier</h3><p class="bad">Approve first. No send form until an approve is logged ({html.escape(problem)}).</p>'
    unack = package.ack_problem(item["id"], report)  # B-244 (D-068)
    if unack:
        return f'<h3>Send to carrier</h3><p class="bad">Send refused: {html.escape(unack)}. Approve again and tick each one.</p>'
    when, to = package.sent_info(item["id"], TO_CARRIER)
    files = package.sent_files(item["id"], TO_CARRIER)
    already = f'<p class="msg ok">Already sent {html.escape(package.sent_phrase(when))} to {html.escape(to)}. Package files sent: {html.escape(", ".join(f.name for f in files))}.</p>' if when else ""
    resend = (
        '<label>Resend reason (required for a second send) <input name="resend_reason" size="30"></label> ' if when else ""
    )
    return (
        f'<h3>Send to carrier</h3>{already}<form method="post" action="/send"><input type="hidden" name="submission" value="{sid}">'
        f"<p>The package goes to <b>{html.escape(item['route'])}</b>. Check the carrier name, then confirm.</p>"
        f'{resend}<label>Type <code>send to carrier {sid}</code> to confirm <input name="user_line" size="28" autocomplete="off"></label> '
        f'<button type="submit">{"Resend" if when else "Send"} to {html.escape(item["route"])}</button></form>'
        "<p>Goes through the same send gate as every send: saved run, documents unchanged, an approve logged, no failed file. The underwriter decides; nothing is bound.</p>"
    )


def _short(h: str) -> str:
    return (h or "")[:8]


def history_html(sub: str, current: str) -> str:
    """D-069 Session B: one per-file panel: decisions, acknowledgments, sends and resends. Who, why, when, run hash."""
    events = []
    try:
        for r in package.decisions(sub, LOG):
            what = r.get("action", "")
            if what == "edit" and r.get("field_id"):
                what += f" {r['field_id']} to {r.get('new_value', '')}"
            if r.get("acknowledged"):
                what += f"; acknowledged {len(r['acknowledged'])}: {', '.join(r['acknowledged'])}"
            events.append((r.get("at") or f"{r.get('date', '')}T00:00:00", 0, r.get("underwriter_id", ""), what, r.get("reason", ""), r.get("run_hash") if r.get("action") == "approve" else None, r.get("at") or r.get("date", "")))
    except ValueError as exc:
        return f"<h3>History</h3><p class=\"bad\">History unavailable: {html.escape(str(exc))}</p>"
    if package.SENDS_LOG.exists():
        for line in package.SENDS_LOG.read_text().splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if isinstance(r, dict) and r.get("submission") == sub:
                events.append((r.get("at") or f"{r.get('date', '')}T00:00:00", 1, r.get("actor", ""), ("resend " if r.get("resend") else "send ") + Path(r.get("package", "")).name, r.get("resend_reason") or r.get("reason", ""), r.get("run_hash", ""), r.get("at") or r.get("date") or "date not recorded"))
    if not events:
        return "<h3>History</h3><p>No decision or send logged for this file.</p>"
    rows = []
    for _k, _o, who, what, why, run, when in sorted(events, key=lambda e: e[:2]):
        if run is None:
            mark = "—"
        elif not run:
            mark = "no run hash recorded — does not count"
        else:
            mark = f"run {_short(run)} " + ("(current run)" if run == current else "— not the current run")
        rows.append(f"<tr><td>{html.escape(when)}</td><td>{html.escape(who)}</td><td>{html.escape(what)}</td><td>{html.escape(why or '—')}</td><td>{html.escape(mark)}</td></tr>")
    return f"<h3>History</h3><table class=\"history\"><tr><th>When</th><th>Who</th><th>What</th><th>Why</th><th>Saved run</th></tr>{''.join(rows)}</table><p>Current run: {html.escape(_short(current) or 'unknown')}</p>"


def footer_html() -> str:
    """D-069: the model and prompt version of this environment. Never a key or a host address."""
    model = os.environ.get("LLM_MODEL") or "not set"
    return f"<footer><p>Model (this environment): {html.escape(model)} · Prompt version (this code): {html.escape(str(llm_extract.PROMPT_VERSION))}</p></footer>"


def render(queue: list[dict], counts: dict | None = None, messages: dict | None = None) -> str:
    counts = counts or {"approve": 0, "edit": 0, "decline": 0}
    messages = messages or {}
    corrections = counts["edit"] + counts["decline"]
    blocks, unsaved = [], []
    for item in queue:
        report = item["report"]
        if report is None:  # item 10: no saved run, or it cannot be read; nothing is extracted here
            unsaved.append(
                f'<article id="{html.escape(item["id"])}"><h2>{html.escape(item["id"])}</h2>{_msg(messages, item["id"])}'
                f'<p class="bad">No usable saved run: {html.escape(item.get("saved_problem") or "none found")}. '
                "This page shows saved runs only and does not run extraction. Run extraction, then reload. No decision or send is offered.</p></article>"
            )
            continue
        refused = report.get("status") in prepare.REFUSED_STATUSES
        field_rows = []
        for row in report["fields"]:
            note = ""
            if row.get("needs_review") and row.get("value"):
                note = "NEEDS REVIEW: " + (row.get("reason") or "flagged")
            elif row.get("reason") and not row.get("value"):
                note = row["reason"]
            field_rows.append(
                "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                    html.escape(row["field_id"]),
                    html.escape(row["value"] or "—"),
                    html.escape(_confidence(row)),
                    html.escape(row.get("source") or "—"),
                    html.escape(row.get("quote") or item["snippets"].get(row["field_id"]) or "—"),
                    html.escape(note or "—"),
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
        unread = report.get("unread") or []
        unread_html = "<p>Not read: none</p>" if not unread else "<p>Not read:</p><ul>" + "".join(
            "<li>{}, {}: {}</li>".format(
                html.escape(u["file"]),
                "whole file" if u.get("page") is None else f"page {u['page']}",
                html.escape(u["reason"]),
            )
            for u in unread
        ) + "</ul>"
        manifest = item.get("manifest") or ""
        lines = [
            f"<h2>{html.escape(item['id'])}</h2>",
            _msg(messages, item["id"]),
            (f'<p class="msg bad" role="alert">{package.STALE}. Approve and tick each needs-review value again.</p>' if package._decision_problem(item["id"], report.get("saved_hash") or "") == package.STALE else ""),
            f"<p>Saved run: status {html.escape(str(report.get('status')))} · hash check: ok · manifest check: "
            + (f'<span class="bad">FAILED — {html.escape(manifest)}. A send will be refused.</span>' if manifest else "ok")
            + "</p>",
            f"<p>Files: {html.escape(', '.join(item['files']) or 'none')}</p>",
            f"<p>Not read by extraction: {html.escape(', '.join(item['ignored']) or 'none')}</p>",
        ]
        if not refused:
            lines += [
                f"<p>Score: {item['score']['points']} · {html.escape(', '.join(item['score']['reason_codes']) or 'none')} · not a price</p>",
                f"<p>Carrier match: {html.escape(item['route'])}{html.escape(' · ' + item['note']) if item.get('note') else ''} · recommendation only</p>",
                f"<p>Suggested market: <b>{html.escape(item.get('suggested') or 'none')}</b> · recommendation only; the underwriter decides</p>",
            ]
        lines += [
            f"<p>Extraction: {html.escape(extraction)}</p>",
            unread_html,
            f"<p>Needs human read: {html.escape(', '.join(report.get('needs_human') or []) or 'none')}</p>",
            f"<p>Address check: {html.escape(address_check)}</p>",
            f"<p>Locations: {html.escape('; '.join(('primary ' if row.get('primary') else 'other ') + row['address'] for row in report['locations']) or 'one premises') if report.get('locations') is not None else 'not stored in the saved run'}</p>",
            "<h3>Extracted fields</h3>",
            f"<table><tr><th>Field</th><th>Value</th><th>Confidence</th><th>Source</th><th>Cited text</th><th>Review note</th></tr>{''.join(field_rows)}</table>",
            f"<h3>Conflicts</h3>{conflict_html}",
            quotes.html_for(item["id"]),
        ]
        if not refused:
            missing = report["missing"] + report.get("extra", [])
            lines += ["<h3>Missing</h3>", f"<p>{html.escape(', '.join(missing) or 'none')}</p>"]
        # T-071: on a refused card there is no approve option. Edit and decline stay so a person decides.
        options = "<option>edit</option><option>decline</option>" if refused else "<option>approve</option><option>edit</option><option>decline</option>"
        acks = "".join(
            '<label><input type="checkbox" name="ack" value="{0}"> I checked {0}: {1} (cited: {2})</label><br>'.format(
                html.escape(row["field_id"]), html.escape(row["value"]), html.escape(row.get("quote") or "—")
            )
            for row in report["fields"]
            if row.get("needs_review") and row.get("value")
        )
        if acks and not refused:
            acks = f"<fieldset><legend>Needs-review values: acknowledge each to approve</legend>{acks}</fieldset>"
        else:
            acks = ""
        lines.append(
            f"""<form method="post" action="/decision">
<input type="hidden" name="submission" value="{html.escape(item['id'])}">
<input type="hidden" name="run_hash" value="{html.escape(report.get('saved_hash') or '')}">
{acks}
<label>Underwriter id <input name="underwriter_id" required></label>
<label>Action
<select name="action">{options}</select>
</label>
<label>Edited field <input name="field_id" placeholder="e.g. year_built"></label>
<label>New value <input name="new_value"></label>
<label>Reason <input name="reason"></label>
<button type="submit">Record decision</button>
</form>"""
        )
        sid = html.escape(item["id"])
        draft = PENDING / f"{item['id']}.md"
        if draft.is_file():
            lines.append(
                f"<h3>Missing-info draft for the producer (not sent)</h3><pre>{html.escape(draft.read_text())}</pre>"
                f'<form method="post" action="/approve-draft"><input type="hidden" name="submission" value="{sid}">'
                '<label>Reason (optional) <input name="reason"></label> '
                '<button type="submit">Approve and send to producer (user override)</button></form>'
            )
        if (TO_PRODUCER / f"{item['id']}.md").is_file():
            lines.append("<p>Producer request on file in to-producer.</p>")
        lines.append(_send_html(item, report, refused, manifest))
        lines.append(history_html(item["id"], report.get("saved_hash") or ""))
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
.msg {{ padding: 0.5rem 0.75rem; border-left: 4px solid; font-weight: 600; }}
.msg.ok {{ border-color: #1a7f37; background: #e9f7ee; }}
.msg.bad, .bad {{ border-color: #b42318; color: #b42318; }}
.msg.bad {{ background: #fdecea; }}
.banner {{ background: #fff3bf; border: 2px dashed #b08900; padding: 0.5rem 0.75rem; font-weight: 700; }}
pre {{ background: #f6f6f6; padding: 0.5rem; white-space: pre-wrap; }}
details {{ margin: 0.5rem 0; }}
footer {{ border-top: 1px solid #ccc; margin-top: 2rem; color: #555; }}
</style></head><body>
{f'<p class="banner">{html.escape(BANNER)}</p>' if BANNER else ''}
<h1>Underwriter workbench</h1>
{''.join(_msg(messages, k) for k in messages if k not in {q["id"] for q in queue})}
<details open><summary><b>What's new</b></summary><ul>{''.join(f"<li>{html.escape(d)} · {html.escape(t)} · {html.escape(n)}: {html.escape(w)}</li>" for d, t, n, w in WHATS_NEW)}</ul></details>
<p>Synthetic queue. A decision is logged only with an id on the underwriter list. Decline and edit need a reason, and so does an approve after a decline. Approve, edit, and decline are saved with that reason. This page shows saved runs only. It never binds. A carrier send needs the typed line and passes the send gate.</p>
<p>Decisions so far: {counts['approve']} approved, {counts['edit']} edited, {counts['decline']} declined. Corrections: {corrections}.</p>
{''.join(blocks)}
{_folded(unsaved)}
{footer_html()}
</body></html>
"""


def sandbox(tmp: Path) -> None:
    """B-252 (D-069): copy the real inputs into tmp and point every path the page can write at the copy.

    Covers the page, the decision/sends/closure logs, the three outboxes, the saved runs, the inbox and the model cache
    (token log). Nothing real is written afterwards. Call before serve() or any test that posts an action."""
    global PAGE, LOG, INBOX, PENDING, TO_PRODUCER, TO_CARRIER, BANNER
    tmp = Path(tmp)
    for name, src in (("inbox", INBOX), ("extractions", prepare.EXTRACT_DIR), ("pending", PENDING), ("to-producer", TO_PRODUCER),
                      ("to-carrier", TO_CARRIER), ("from-carrier", quotes.FROM_CARRIER), ("cache", llm_extract.CACHE)):
        if src.is_dir() and name != "cache":  # the cache starts empty: a sandbox never reads or grows the real token log
            shutil.copytree(src, tmp / name, dirs_exist_ok=True)
        (tmp / name).mkdir(exist_ok=True)
    logs = {"decisions.jsonl": package.DECISIONS_LOG, "sends.jsonl": package.SENDS_LOG, "closures.jsonl": quotes.CLOSURES}
    for name, src in logs.items():
        if src.is_file():
            shutil.copy2(src, tmp / name)
    PAGE, LOG, INBOX = tmp / "workbench.html", tmp / "decisions.jsonl", tmp / "inbox"
    PENDING, TO_PRODUCER, TO_CARRIER = tmp / "pending", tmp / "to-producer", tmp / "to-carrier"
    package.DECISIONS_LOG, package.SENDS_LOG, package.INBOX = LOG, tmp / "sends.jsonl", INBOX
    quotes.CLOSURES, quotes.TO_CARRIER, quotes.FROM_CARRIER = tmp / "closures.jsonl", TO_CARRIER, tmp / "from-carrier"
    prepare.EXTRACT_DIR, prepare.INBOX_DIR, llm_extract.CACHE = tmp / "extractions", INBOX, tmp / "cache"
    BANNER = f"SANDBOX COPY in {tmp}: nothing here is real; no real log, outbox or page is written"


def serve(port: int = 8765, only: str | None = None, sandbox_dir: Path | None = None) -> None:
    if sandbox_dir is not None:
        sandbox(sandbox_dir)
    PAGE.write_text(render(load_queue(only), correction_counts(LOG)))

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            shown = dict(MESSAGES)
            MESSAGES.clear()
            body = render(load_queue(only), correction_counts(LOG), shown).encode()  # saved runs only: no extraction here
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            if self.path not in REFUSED_AS:
                self.send_error(404)
                return
            size = int(self.headers.get("Content-Length", "0"))
            form = parse_qs(self.rfile.read(size).decode())
            payload = {k: v[0] for k, v in form.items()}
            payload["ack"] = form.get("ack", [])
            sub, ok, text = act(self.path, payload)
            MESSAGES[sub] = (ok, text)
            self.send_response(303)  # never a bare 400 page: back to the card with the reason on it
            self.send_header("Location", "/" + (f"#{sub}" if sub else ""))
            self.end_headers()

    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    if "--serve" in sys.argv:
        chosen = next((arg for arg in sys.argv if arg.startswith("SUB-")), None)
        box = None  # --sandbox [DIR]: every write goes to a temporary copy (B-252)
        if "--sandbox" in sys.argv:
            after = sys.argv[sys.argv.index("--sandbox") + 1 :][:1]
            box = Path(after[0]) if after and not after[0].startswith(("-", "SUB-")) else Path(tempfile.mkdtemp(prefix="workbench-sandbox-"))
            print(f"sandbox: {box}", flush=True)
        serve(only=chosen, sandbox_dir=box)
    else:
        def save(ext: Path, submission: str, status: str, fields=None) -> None:
            """A saved run shaped like prepare.write_drafts() writes, no model call. The hash is the reader's."""
            payload = {
                "submission": submission,
                "status": status,
                "error": "model call failed: HTTP 429 rate limit" if status == "extraction_failed" else None,
                "complete": status == "complete",
                "conflicts": [],
                "needs_human": [],
                "sprinklers": None,
                "fields": fields or [],
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

                # D-039: needs-review values must each be acknowledged at approve; the log names them.
                nr = lambda extra: {"field_id": "year_built", "value": "1942", "needs_review": True, "quote": "Built 1942", "reason": "number or date read from a scan", **extra}
                save(ext, "SUB-020", "complete", [nr({}), {"field_id": "operations", "value": "office", "needs_review": False}, {"field_id": "roof", "value": None, "needs_review": True}])
                ap = {"underwriter_id": "UW-001", "action": "approve", "submission": "SUB-020", "reason": "checked"}
                for ack in (None, []):
                    try:
                        record_decision({**ap, "ack": ack}, check)
                        raise SystemExit("an approve without the acknowledgment should fail")
                    except ValueError:
                        pass
                n = len(check.read_text().splitlines())
                assert record_decision({**ap, "ack": ["year_built"]}, check)["acknowledged"] == ["year_built"]
                assert len(check.read_text().splitlines()) == n + 1
                assert "acknowledged" not in logged  # a report with no needs-review value approves as before

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
                assert correction_counts(check) == {"approve": 2, "edit": 3, "decline": 2}, correction_counts(check)

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

                # D-056 (B-139): an edit row stores its field and new value; a half edit or a non-edit with them is refused.
                record_decision({"underwriter_id": "user", "action": "edit", "submission": "SUB-012", "reason": "loss run", "field_id": "year_built", "new_value": " 1987 "}, check)
                last = json.loads(check.read_text().splitlines()[-1])
                assert last["field_id"] == "year_built" and last["new_value"] == "1987"
                before = len(check.read_text().splitlines())
                for bad in (
                    {"action": "edit", "field_id": "year_built"},
                    {"action": "edit", "new_value": "1987"},
                    {"action": "edit", "field_id": "not_a_field", "new_value": "1"},
                    {"action": "decline", "field_id": "year_built", "new_value": "1"},
                ):
                    try:
                        record_decision({"underwriter_id": "user", "submission": "SUB-012", "reason": "x", **bad}, check)
                        raise SystemExit(f"{bad} should fail")
                    except ValueError:
                        pass
                assert len(check.read_text().splitlines()) == before
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
        # P-016 R1/D-039: the card shows reason, quote, unread rows, and a checkbox per needs-review value.
        lowc = render([card("complete", fields=[{"field_id": "tiv_building", "value": "220000", "needs_review": True, "quote": "TIV 220,000", "reason": "Low-confidence scan read — check against the page"}])], None)
        assert "NEEDS REVIEW: Low-confidence scan read — check against the page" in lowc and needs_review_ids({"fields": [{"field_id": "tiv_building", "value": "220000", "needs_review": True}]}) == ["tiv_building"], "P-025 label and approve list"
        flagged = card("complete", fields=[{"field_id": "year_built", "value": "1942", "needs_review": True, "quote": "Built 1942", "reason": "number or date read from a scan"}])
        flagged["report"]["unread"] = [{"file": "a.pdf", "page": 2, "reason": "blank"}, {"file": "b.docx", "page": None, "reason": "file type .docx is not read"}]
        pf = render([flagged], None)
        assert "NEEDS REVIEW: number or date read from a scan" in pf and "Built 1942" in pf and 'name="ack" value="year_built"' in pf
        assert "a.pdf, page 2: blank" in pf and "b.docx, whole file:" in pf
        assert 'name="ack"' not in page_ok
        # T-087: the card shows the quote status per carrier and SUB-002's open subjectivity.
        sub2 = card("complete", fields=[{"field_id": "operations", "value": "restaurant"}])
        sub2["id"] = "SUB-002"
        page2 = render([sub2], None)
        assert "carrier_b: quoted, subjectivities open" in page2 and "confirm hood and suppression on the inspection [open]" in page2 and "not bound" in page2
        assert "No carrier reply on file" in page_ok
        # D-058: the open subjectivity has a close form posting to /close-subjectivity (listed id + reason, logged)
        assert 'action="/close-subjectivity"' in page2

        assert logged["sent_to_carrier"] is False
        assert logged["reason"] == "self-check"
        assert logged["ai_version"].endswith("+rules-d015")
        fake = {
            "complete": True,
            "fields": [{"field_id": "operations", "value": "bookkeeping office, no cooking"}, {"field_id": "tiv_building", "value": "$900,000"}],
        }
        assert route(fake) == "carrier_a"
        held = {
            "complete": True,
            "sprinklers": "no",
            "fields": [{"field_id": "operations", "value": "habitational, 8 units, no commercial cooking"}, {"field_id": "tiv_building", "value": "$3,000,000"}],
        }
        ready = dict(held)
        ready["sprinklers"] = "yes"
        assert route(held) == "senior_referral"  # D-059 item 6: sprinklers "no" (AG:61)
        assert route({**held, "sprinklers": None}) == "hold"
        assert route(ready) == "carrier_c"
        # T-083: D-059 + D-060, written to the temp-free in-memory report only.
        def r(ops, tiv="$1,000,000", **kw):
            f = [{"field_id": "operations", "value": ops}]
            if tiv is not None:
                f.append({"field_id": "tiv_building", "value": tiv})
            return {"complete": True, "fields": f, **kw}

        m = match(r("barber shop"))
        assert m["route"] == "no_match" and m["overridable"]
        assert route(r("barbecue restaurant")) == "carrier_b" and match(r("Barbecue Restaurant"))["note"] == "3 clean years not checked"
        m = match(r("accounting office", "$8,000,000"))
        assert m["route"] == "senior_referral" and m["note"] == "outside pilot TIV limit (AG:16)"
        for ops in ("cannabis dispensary retail", "armed security office", "sprinklered student housing", "Bar and grill", "fireworks"):
            m = match(r(ops, sprinklers="yes"))
            assert m["route"] == "no_match" and not m["overridable"], ops
        m = match(r("roofing contractor"))
        assert m["route"] == "senior_referral" and m["suggested"] == "carrier_b"
        assert match(r("office and restaurant"))["route"] == "senior_referral"
        assert route(r("office", "$5,000,000")) == "carrier_a" and route(r("office", "$5,000,001")) == "senior_referral"
        assert route(r("restaurant", "$2,000,000")) == "carrier_b" and route(r("restaurant", "$2,000,001")) == "senior_referral"
        # D-061: the existing normalizer; missing or unreadable TIV holds; over $5M is senior referral, no $10M rule.
        assert match(r("office", "$8M"))["note"] == OUT_TIV and route(r("office", "$12,000,000")) == "senior_referral"
        assert route(r("office", "750K")) == "carrier_a" and route(r("office", "$1.2M")) == "carrier_a"
        assert route(r("office", "$1.2MM")) == "carrier_a" and route(r("office", "$5.1MM")) == "senior_referral"  # P-021
        for bad in ("", "TBD", None, "$0", "0", "-$5,000",  # B-203: 0 or negative holds
                    "50,000 sq ft", "50000 SF", "12,000 square feet", "8,000 sq. ft.", "9000sqft", "1 square foot"):  # B-209
            m = match(r("office", bad))
            assert m == {"route": "hold", "note": "TIV missing or unreadable", "suggested": "", "overridable": False}, (bad, m)
        assert route(r("taqueria")) == "carrier_b" and route(r("oficina")) == "carrier_a" and route(r("")) == "hold"
        assert route(r("sprinklered apartments", "$4,000,000")) == "carrier_c"
        assert match(r("sprinklered apartments", "$6,000,000"))["note"] == OUT_TIV
        assert route(r("office")) == "carrier_a" and route(r("barley mill")) == "no_match"
        assert "COOKING" not in points.score(facts(fake))["reason_codes"]

        # D-066 items 10, 2/4/8, 1, 13: saved run only on load, refusals as plain messages, typed send, draft approve.
        import llm_extract

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            ext, inbox, dlog = tmp / "extractions", tmp / "inbox", tmp / "decisions.jsonl"
            old = (prepare.EXTRACT_DIR, prepare.INBOX_DIR, INBOX, LOG, PENDING, TO_PRODUCER, TO_CARRIER, package.DECISIONS_LOG, package.SENDS_LOG, package.INBOX, llm_extract._post, prepare.process_submission)

            def stored(sub: str, status: str, fields=None, complete=True) -> None:
                folder = inbox / sub
                folder.mkdir(parents=True, exist_ok=True)
                (folder / "application.md").write_text(f"SYNTHETIC application {sub}\n")
                payload = {"submission": sub, "status": status, "error": None, "complete": complete, "conflicts": [], "needs_human": [], "unread": [], "sprinklers": "no", "fields": fields or [],
                           "input_manifest": prepare.folder_manifest(folder), "hash_algorithm": prepare.HASH_ALGORITHM}
                payload["saved_hash"] = prepare.hash_payload(payload)
                ext.mkdir(exist_ok=True)
                (ext / f"{sub}.json").write_text(json.dumps(payload))

            def boom(*_a, **_k):
                raise SystemExit("page load must not extract or call a model")

            try:
                prepare.EXTRACT_DIR, prepare.INBOX_DIR, INBOX, LOG = ext, inbox, inbox, dlog
                PENDING, TO_PRODUCER, TO_CARRIER = tmp / "pending", tmp / "to-producer", tmp / "to-carrier"
                package.DECISIONS_LOG, package.SENDS_LOG, package.INBOX = dlog, tmp / "sends.jsonl", inbox
                good = [{"field_id": f, "value": "x", "source": "application.md", "start": 0, "end": 3} for f in prepare.FIELDS]
                good = [{**r, "value": {"operations": "accounting office", "tiv_building": "$1,000,000"}.get(r["field_id"], "x")} for r in good]
                stored("SUB-901", "complete", good)
                stored("SUB-903", "complete", good)
                stored("SUB-910", "extraction_failed", complete=False)
                stored("SUB-929", "incomplete", [{**r, "value": None} if r["field_id"] == "effective_date" else r for r in good], complete=False)
                (inbox / "SUB-902").mkdir()  # no saved run
                (inbox / "SUB-903" / "application.md").write_text("changed after extraction\n")
                # item 10: page load with the model call and extraction both patched to raise.
                llm_extract._post, prepare.process_submission = boom, boom
                q = load_queue()
                pg = render(q, None)
                assert "No usable saved run: no saved run for SUB-902" in pg and "does not run extraction" in pg
                assert "hash check: ok · manifest check: ok" in pg and "changed since extraction" in pg
                llm_extract._post, prepare.process_submission = old[-2:]

                # items 2/4/8: refusals come back as (submission, False, plain words), never an exception.
                def refused(path, **kw):
                    sub, ok, text = act(path, {"submission": "SUB-901", **kw})
                    assert not ok and sub == "SUB-901", text
                    return text

                assert "Decision refused: only an id on underwriters.json" in refused("/decision", underwriter_id="UW-999", action="approve")
                assert refused("/send", user_line="send to carrier SUB-901").startswith("Send refused: no logged decision")
                assert "changed since extraction" in act("/send", {"submission": "SUB-903", "user_line": "send to carrier SUB-903"})[2]
                assert "Send refused: this file's status is extraction_failed" in act("/send", {"submission": "SUB-910", "user_line": "send to carrier SUB-910"})[2]
                assert act("/send", {"submission": "../x"})[2].startswith("Send refused: no such submission")
                pg = render(load_queue(), None, {"SUB-901": (False, "Send refused: x")})
                assert 'class="msg bad"' in pg and "Send refused: x" in pg and "Approve first" in pg and 'action="/send"' not in pg  # B-249

                # item 1: a recorded approve, then the typed line. A wrong line is refused; the right one writes the package.
                assert act("/decision", {"submission": "SUB-901", "underwriter_id": "user", "action": "approve", "reason": "ok"})[1]
                assert "exact line" in refused("/send", user_line="yes")
                assert not TO_CARRIER.exists()
                sub, ok, text = act("/send", {"submission": "SUB-901", "user_line": "send to carrier SUB-901"})
                assert ok and text.startswith("Sent:") and (TO_CARRIER / "SUB-901.md").is_file(), text
                assert json.loads((tmp / "sends.jsonl").read_text().splitlines()[-1])["actor"] == "user"

                # B-231/B-232/B-233 (D-067): folding with a count, carrier named, second send refused, resend logged.
                pg = render(load_queue(), None)
                assert "No saved run (1)" in pg and pg.index('id="SUB-901"') < pg.index("No saved run (1)") < pg.index('id="SUB-902"')
                assert "<details><summary><b>No saved run" in pg  # closed by default
                assert "carrier_a" in pg and "Already sent on" in pg and "to carrier_a" in pg and "Resend reason" in pg
                assert "No send: the carrier match is hold" in pg or "No send: the file is incomplete" in pg  # SUB-929
                assert "No send: this file&#x27;s status is extraction_failed" in pg
                line = "send to carrier SUB-901"
                assert act("/send", {"submission": "SUB-901", "user_line": line})[2].startswith("Send refused: already sent on")
                assert "written reason" in act("/send", {"submission": "SUB-901", "user_line": line})[2]
                sub, ok, text = act("/send", {"submission": "SUB-901", "user_line": line, "resend_reason": "carrier lost it"})
                assert ok and json.loads((tmp / "sends.jsonl").read_text().splitlines()[-1])["resend_reason"] == "carrier lost it", text
                stored("SUB-904", "complete", good)
                assert act("/decision", {"submission": "SUB-904", "underwriter_id": "user", "action": "approve", "reason": "ok"})[1]
                assert "The package goes to <b>carrier_a</b>" in render(load_queue(), None)
                assert "SUB-901.md, SUB-901-resend-2.md" in render(load_queue(), None)  # B-247 card lists each file
                # B-244: an approve logged before the run held low-confidence values does not cover them.
                stored("SUB-905", "complete", [{**r, "needs_review": True} if r["field_id"] == "named_insured" else r for r in good])
                with dlog.open("a") as h:
                    h.write(json.dumps({"seq": 9000, "submission": "SUB-905", "action": "approve", "underwriter_id": "user", "reason": "ok", "run_hash": package._current_hash("SUB-905")}) + "\n")
                assert "Send refused: 1 value needs review and is not acknowledged (named_insured)" in render(load_queue(), None)
                assert "not acknowledged (named_insured)" in act("/send", {"submission": "SUB-905", "user_line": "send to carrier SUB-905"})[2]

                # item 13: the draft shows on the card; the user approves it (D-050); refused files cannot be approved.
                PENDING.mkdir()
                (PENDING / "SUB-929.md").write_text("Submission SUB-929\nNothing has been declined. Nothing has been bound.\n\nMissing:\n- effective date\n")
                (PENDING / "SUB-910.md").write_text("Submission SUB-910\nNothing has been declined.\n")
                pg = render(load_queue(), None)
                assert "Missing-info draft for the producer (not sent)" in pg and "- effective date" in pg and 'action="/approve-draft"' in pg
                assert act("/approve-draft", {"submission": "SUB-910"})[2].startswith("Request not approved: this file's status is extraction_failed")
                sub, ok, text = act("/approve-draft", {"submission": "SUB-929", "reason": "producer asked"})
                assert ok and (TO_PRODUCER / "SUB-929.md").read_text().startswith("Approved-by: user (override)"), text
                assert "Producer request on file" in render(load_queue(), None)
                assert not act("/approve-draft", {"submission": "SUB-901"})[1]  # no draft file: plain refusal, not a crash

                # P-026 (D-069): approve, re-save with a changed value -> re-review message and refused send; approve again -> allowed.
                def art(page: str, sub: str) -> str:
                    start = page.index(f'<article id="{sub}">')
                    return page[start : page.index("</article>", start)]

                stored("SUB-906", "complete", good)
                assert act("/decision", {"submission": "SUB-906", "underwriter_id": "user", "action": "approve", "reason": "ok", "run_hash": "0ld"})[2].startswith("Decision refused: the saved run changed since this card was opened")
                assert act("/decision", {"submission": "SUB-906", "underwriter_id": "user", "action": "approve", "reason": "ok"})[1]
                first = json.loads(dlog.read_text().splitlines()[-1])
                assert first["run_hash"] == package._current_hash("SUB-906") and first["at"] and "Re-review needed" not in art(render(load_queue(), None), "SUB-906")
                stored("SUB-906", "complete", [{**r, "value": "Different Co"} if r["field_id"] == "named_insured" else r for r in good])
                pg = render(load_queue(), None)
                assert "Re-review needed: file changed since your approval" in art(pg, "SUB-906") and 'action="/send"' not in art(pg, "SUB-906")
                assert act("/send", {"submission": "SUB-906", "user_line": "send to carrier SUB-906"})[2] == "Send refused: Re-review needed: file changed since your approval"
                assert "not the current run" in art(pg, "SUB-906")
                assert act("/decision", {"submission": "SUB-906", "underwriter_id": "user", "action": "approve", "reason": "ok again"})[1]
                pg = render(load_queue(), None)
                assert "Re-review needed" not in art(pg, "SUB-906") and 'action="/send"' in art(pg, "SUB-906")
                assert act("/send", {"submission": "SUB-906", "user_line": "send to carrier SUB-906"})[1]

                # History panel: decisions, acknowledgments, sends and resends with who, why, when, short run hash.
                h = art(render(load_queue(), None), "SUB-901")
                cur = package._current_hash("SUB-901")[:8]
                assert "<h3>History</h3>" in h and "send SUB-901.md" in h and "resend SUB-901-resend-2.md" in h and "carrier lost it" in h
                assert f"run {cur} (current run)" in h and "approve" in h and "user" in h
                ack = art(render(load_queue(), None), "SUB-905")
                assert "approve" in ack and "no run hash" not in ack
                assert "No decision or send logged" in art(render(load_queue(), None), "SUB-929")

                stored("SUB-908", "complete", [{**r, "needs_review": True, "quote": "Acme", "reason": "r"} if r["field_id"] == "named_insured" else r for r in good])
                assert act("/decision", {"submission": "SUB-908", "underwriter_id": "user", "action": "approve", "reason": "checked", "ack": ["named_insured"]})[1]
                assert "acknowledged 1: named_insured" in art(render(load_queue(), None), "SUB-908")

                # Suggested market is its own field; the footer shows model and prompt version, never a key or a host.
                stored("SUB-907", "complete", [{**r, "value": "roofing contractor"} if r["field_id"] == "operations" else r for r in good])
                assert "Suggested market: <b>carrier_b</b>" in art(render(load_queue(), None), "SUB-907")
                assert "Suggested market: <b>none</b>" in art(render(load_queue(), None), "SUB-901")
                env_old = {k: os.environ.get(k) for k in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL")}
                try:
                    for k in env_old:
                        os.environ.pop(k, None)
                    assert f"Model (this environment): not set · Prompt version (this code): {llm_extract.PROMPT_VERSION}" in render([], None)
                    os.environ.update(LLM_MODEL="test-model", LLM_API_KEY="sk-SECRET", LLM_BASE_URL="https://user:pw@host.example/v1")
                    foot = render(load_queue(), None)
                    assert "Model (this environment): test-model" in foot and "SECRET" not in foot and "host.example" not in foot and "pw@" not in foot
                finally:
                    for k, v in env_old.items():
                        os.environ.pop(k, None)
                        if v is not None:
                            os.environ[k] = v
            finally:
                (prepare.EXTRACT_DIR, prepare.INBOX_DIR, INBOX, LOG, PENDING, TO_PRODUCER, TO_CARRIER, package.DECISIONS_LOG, package.SENDS_LOG, package.INBOX, llm_extract._post, prepare.process_submission) = old

        # B-252 (D-069): a sandbox run writes only inside its temp directory; the real files' bytes stay the same.
        import hashlib

        real = [PAGE, package.DECISIONS_LOG, package.SENDS_LOG, quotes.CLOSURES, llm_extract.CACHE / "token_log.jsonl"]
        real_dirs = [PENDING, TO_PRODUCER, TO_CARRIER, prepare.EXTRACT_DIR]

        def fingerprint() -> dict:
            files = [f for f in real if f.is_file()] + [f for d in real_dirs if d.is_dir() for f in sorted(d.rglob("*")) if f.is_file()]
            return {str(f): hashlib.sha256(f.read_bytes()).hexdigest() for f in files} | {str(d): sorted(x.name for x in d.iterdir()) for d in real_dirs if d.is_dir()} | {f"exists {f}": f.is_file() for f in real}

        before_real = fingerprint()
        names = ("PAGE", "LOG", "INBOX", "PENDING", "TO_PRODUCER", "TO_CARRIER", "BANNER")
        saved_mod = {n: globals()[n] for n in names}
        saved_other = (package.DECISIONS_LOG, package.SENDS_LOG, package.INBOX, quotes.CLOSURES, quotes.TO_CARRIER, quotes.FROM_CARRIER, prepare.EXTRACT_DIR, prepare.INBOX_DIR, llm_extract.CACHE)
        with tempfile.TemporaryDirectory() as box_dir:
            box_dir = Path(box_dir)
            try:
                sandbox(box_dir)
                assert PAGE.parent == box_dir and "SANDBOX COPY" in BANNER
                PAGE.write_text(render(load_queue(), correction_counts(LOG)))  # what serve() writes first
                sid = next(p.name for p in INBOX.iterdir() if p.name.startswith("SUB-") and (prepare.EXTRACT_DIR / f"{p.name}.json").is_file())
                act("/decision", {"submission": sid, "underwriter_id": "user", "action": "approve", "reason": "sandbox check"})
                act("/send", {"submission": sid, "user_line": f"send to carrier {sid}"})
                act("/close-subjectivity", {"submission": "SUB-002", "carrier": "carrier_b", "subjectivity": "x", "underwriter_id": "user", "reason": "sandbox check"})
                assert LOG.is_file() and (box_dir / "workbench.html").is_file() and "SANDBOX COPY" in PAGE.read_text()
            finally:
                for n, v in saved_mod.items():
                    globals()[n] = v
                (package.DECISIONS_LOG, package.SENDS_LOG, package.INBOX, quotes.CLOSURES, quotes.TO_CARRIER, quotes.FROM_CARRIER, prepare.EXTRACT_DIR, prepare.INBOX_DIR, llm_extract.CACHE) = saved_other
        assert fingerprint() == before_real, "a sandbox run changed a real file"
        print("workbench ok")
