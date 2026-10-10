"""Step 7 — carrier package.

The user can send any package. The account manager can send only when the
agency rules pass, and must write a reason. No AI role can send.

# ponytail: one markdown file per submission. Quote tracking is the from-carrier reply, add a tracker when a carrier answers.

Run: python underwriting_pipeline/app/package.py
"""

from pathlib import Path


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


def agency_problem(report: dict | None) -> str:
    """Empty string means the account manager may approve. The user may override."""
    if not report:
        return "the account manager needs the extraction report"
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
    report: dict | None = None,
) -> Path:
    name = _actor(actor)
    if name not in {"user", "account-manager"}:
        raise ValueError("only the user or the account manager may send to a carrier")
    if name == "account-manager":
        if not (reason or "").strip():
            raise ValueError("the account manager must write a reason")
        problem = agency_problem(report)
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
    import tempfile

    body = build_package("SUB-000", "FICTIONAL office. Recommend Carrier A.")
    assert "Nothing has been bound" in body
    try:
        send_to_carrier("SUB-000", "software-engineer", Path("simulation/to-carrier"), body)
        raise SystemExit("role send should fail")
    except ValueError:
        pass
    clean = {
        "complete": True,
        "conflicts": [],
        "needs_human": [],
        "sprinklers": "no",
        "fields": [{"field_id": "operations", "value": "accounting office"}],
    }
    held = {**clean, "complete": False}
    with tempfile.TemporaryDirectory() as tmp:
        dest_dir = Path(tmp) / "to-carrier"
        dest_dir.mkdir()
        try:
            send_to_carrier("SUB-000", "account-manager", dest_dir, body, reason="ready", report=held)
            raise SystemExit("incomplete send should fail")
        except ValueError:
            pass
        try:
            send_to_carrier("SUB-000", "account-manager", dest_dir, body, report=clean)
            raise SystemExit("missing reason should fail")
        except ValueError:
            pass
        sent = send_to_carrier(
            "SUB-000", "account-manager", dest_dir, body, reason="complete office file", report=clean
        )
        text = sent.read_text()
        assert text.startswith("Sent-by: account-manager")
        assert "Reason: complete office file" in text
        override = send_to_carrier("SUB-000", "user", dest_dir, body)
        assert override.read_text().startswith("Sent-by: user (override)")
        assert not (Path("simulation/to-carrier") / "SUB-000.md").exists()
    print("package ok")
