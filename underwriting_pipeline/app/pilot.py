"""Assist-only pilot controls (T-027 C1–C8).

PILOT_MODE=assist-only disables every acting path in the workbench:
no carrier send, no package, no producer request, and no approve that could
make a file sendable. The underwriter records a per-value confirmation instead.

Two append-only logs carry the pilot's evidence:
  pilot-corrections.jsonl  field, suggested value, final value, reason, actor, run hash
  pilot-events.jsonl       every action and refusal, for counts and time per file

No log is written when PILOT_MODE is off. A failed log write raises; callers show
the failure in plain words and never treat it as success.
"""

from __future__ import annotations

import fcntl
import json
import os
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODE = "PILOT_MODE"
ASSIST_ONLY = "assist-only"
MODE_VALUES = {"", "off", ASSIST_ONLY}

CORRECTIONS = ROOT / "deliverables" / "software-engineer" / "pilot-corrections.jsonl"
EVENTS = ROOT / "deliverables" / "software-engineer" / "pilot-events.jsonl"

# C6: the warning must name measured accuracy. T-117 is the latest frozen run but
# @model-risk kept the veto (not a production approval); T-108 is the last approved
# number. Both are shown so neither can be mistaken for a fresh approval.
ACCURACY = {
    "operations": (9, 20),
    "loss_run_valued_through": (5, 20),
    "source": "T-108 frozen run",
    "latest": {"run": "T-117", "operations": (13, 20), "loss_run_valued_through": (16, 20),
               "status": "@model-risk KEEP, not a production approval"},
}


class PilotError(ValueError):
    """An action refused because the assist-only pilot is active."""


def mode() -> str:
    value = (os.environ.get(MODE) or "").strip().lower()
    if value not in MODE_VALUES:
        raise PilotError(f"{MODE}={value!r} is not a known pilot mode; use off or {ASSIST_ONLY}")
    return value


def active() -> bool:
    return mode() == ASSIST_ONLY


def guard(action: str, submission: str = "") -> None:
    """Refuse an acting path. The reason is the condition's plain-language wording."""
    if not active():
        return
    who = f" for {submission}" if submission else ""
    if action in {"send", "package"}:
        raise PilotError(f"assist-only pilot: send disabled{who}")
    if action in {"draft", "producer-request"}:
        raise PilotError(f"assist-only pilot: missing-info drafts and producer requests are disabled{who}")
    if action == "approve":
        raise PilotError(f"assist-only pilot: approve is disabled{who}; record a per-value confirmation")
    raise PilotError(f"assist-only pilot: {action} is disabled{who}")


def _append(path: Path, row: dict) -> dict:
    if not active():
        return row
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    with lock_path.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            with path.open("a") as handle:
                handle.write(json.dumps(row) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
    return row


def record_correction(*, submission: str, field: str, kind: str, suggested: str, final: str,
                      reason: str, actor: str, run_hash: str = "") -> dict:
    """C5: one row for each edit, conflict resolution, decline or code correction."""
    return _append(CORRECTIONS, {
        "v": 1, "submission": submission, "field": field, "kind": kind,
        "suggested": suggested, "final": final, "reason": reason,
        "actor": actor, "run_hash": run_hash,
        "at": datetime.now().astimezone().isoformat(timespec="seconds"),
    })


def record_event(*, action: str, submission: str = "", actor: str = "", outcome: str = "ok",
                 message: str = "", run_hash: str = "") -> dict:
    """C5: every action and refusal, so counts and time per file survive a restart."""
    return _append(EVENTS, {
        "v": 1, "action": action, "submission": submission, "actor": actor,
        "outcome": outcome, "message": (message or "")[:500], "run_hash": run_hash,
        "at": datetime.now().astimezone().isoformat(timespec="seconds"),
    })


def _rows(path: Path) -> list[dict]:
    out = []
    for line in path.read_text().splitlines() if path.is_file() else []:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def corrections_for(submission: str) -> list[dict]:
    return [r for r in _rows(CORRECTIONS) if r.get("submission") == submission]


def summary(queue: list[dict] | None = None) -> dict:
    """Counts the pilot report needs: edits per field, overrides, refusals, time per file."""
    corrections = _rows(CORRECTIONS)
    events = _rows(EVENTS)
    per_field: dict[str, int] = {}
    for row in corrections:
        if row.get("kind") in {"edit", "resolve"} and row.get("field"):
            per_field[row["field"]] = per_field.get(row["field"], 0) + 1
    times: dict[str, list[str]] = {}
    for row in events:
        sub = row.get("submission")
        at = row.get("at")
        if sub and at:
            times.setdefault(sub, []).append(str(at))
    durations = {}
    for sub, stamps in times.items():
        if len(stamps) > 1:
            try:
                first = datetime.fromisoformat(min(stamps))
                last = datetime.fromisoformat(max(stamps))
                durations[sub] = max(0, int((last - first).total_seconds()))
            except ValueError:
                continue
    failed = sorted({item["id"] for item in queue or [] if (item.get("report") or {}).get("status") == "extraction_failed"})
    return {
        "corrections": len(corrections),
        "per_field": dict(sorted(per_field.items(), key=lambda kv: (-kv[1], kv[0]))),
        "overrides": sum(1 for r in corrections if r.get("kind") == "override") + sum(1 for e in events if e.get("action") == "override"),
        "refusals": sum(1 for e in events if e.get("outcome") == "refused"),
        "duration_seconds": dict(sorted(durations.items())),
        "extraction_failed": failed,
    }


def warning_text() -> str:
    """C6 standing warning. Both the approved and the latest frozen numbers are named."""
    old = ACCURACY
    new = ACCURACY["latest"]
    return (
        "Check each of these against the cited page. Last approved numbers: "
        f"operations {old['operations'][0]}/{old['operations'][1]}, "
        f"loss runs {old['loss_run_valued_through'][0]}/{old['loss_run_valued_through'][1]} ({old['source']}). "
        f"Latest frozen run {new['run']} (not approved): operations {new['operations'][0]}/{new['operations'][1]}, "
        f"loss runs {new['loss_run_valued_through'][0]}/{new['loss_run_valued_through'][1]} ({new['status']})."
    )
