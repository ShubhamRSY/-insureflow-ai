#!/usr/bin/env python3
"""Build the document_conflicts DEV set (SUB-290-298) and its dev gold.

P-074 (D-132) adds SUB-297 and SUB-298 (dev note): the SUB-345 shape. The application states one sales figure and the email another
("about $1.35 million"); the model answered with a conflict, and the pipeline used to keep one flagged figure and no conflict.
SUB-297: both sides stated, the email side is approximate. SUB-298: every side unverifiable (D2) plus a "~$1.2m" side from a
third note. The model reply is a stub in prepare.py's self-check (the SUB-345 stored conflict shape); no cache is read or written.

Dev only, synthetic, P-070 (D-122). Six files, one property each, all in scope:
three files where two documents disagree (a floor area, a count of suites, a sales figure),
one file where a document states "Cooking operations: None", and two negative controls
(the documents agree; the same figure in different words).

The files are new. Nothing is reused from the hold-out and nothing from it is read.
Writes simulation/inbox-dev/document_conflicts/ and
deliverables/senior-underwriter/gold-set-document_conflicts/dev/ (+ a manifest).
No pipeline run, no model call, no write outside those two new folders.
"""
import hashlib
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INBOX = ROOT / "simulation" / "inbox-dev" / "document_conflicts"
GOLD = ROOT / "deliverables" / "senior-underwriter" / "gold-set-document_conflicts" / "dev"
VALUED = "2026-07-15"
EFF = "2026-12-01"

FICTIONAL = "**FICTIONAL.** All businesses, people, addresses and policy numbers are made up.\n\n"

APP = """{fic}# Application (property, ACORD 125 style)

Submission: {sid}
Named insured: {name}
Premises address: {address}, {city} TX {zip}
Effective date: {eff}
Operations: {ops}
Annual sales: ${sales}
Building TIV: ${tiv}
Square footage: {sqft}
Construction: {construction}
Year built: {year}
Sprinklers: {sprinklers}
Cooking operations: {cooking}
Expiring carrier: Carrier A
Pending or open claims: None known
"""

EMAIL = """{fic}Subject: {name} - {address}, {city}

Hi,
{body}
The loss run from Carrier A is attached.
Thanks
"""

LOSS = """CARRIER A — LOSS RUN (FICTIONAL)
Named insured: {name}
Policy period: 2025-07-01 to 2026-07-01
Valued as of: {valued}
| Date of loss | Cause | Paid | Reserve | Status |
|---|---|---|---|---|
| None reported | — | $0 | $0 | — |
"""

# P-071 (D-123), kept by P-072: the published Carrier A no-claims layout (prepare.CARRIER_RUN_FORMATS), so the file does not
# hold on its loss run and an end-to-end status shows only what the cooking rule did (@model-risk T-118 M4).
LOSS_PUBLISHED = """CARRIER A — LOSS RUN (FICTIONAL)
Named insured: {name}
Policy period: 2025-07-01 to 2026-07-01
Valued as of: {valued}
No claims reported by Carrier A for the policy periods above.
"""

SCHED = """location\tsq_ft\tyear_built
Main building\t{sqft}\t{year}
"""

GOLD_T = """# Gold answer - {sid}

- Author: @senior-underwriter (dev gold, written in OpenCode, not independently reviewed)
- Written for the P-070 document_conflicts dev set from the documents and the written rules only (carrier-match.md; operations-gold-rule.md; required-fields.md). Nothing was run. FICTIONAL. Dev only, not hold-out evidence, not a carrier decision.

- Source read by hand: {read}
- Status: {status}
- Scope: in scope — typed English application, one premises, no scan of the application, no second location; no scope criterion applies.
- Named insured: {name}
- Premises: {address}, {city}, TX {zip}
- Effective date: {eff}
- Operations: {ops}
- Operations items: {items}
- Operations notes (unscored): {notes}
- Sales: {sales}
- TIV: {tiv}
- Construction: {construction}
- Year built: {year}
- Loss runs: Carrier A format, 1 policy period 2025-07-01 to 2026-07-01, valued as of {valued}, no claims. Recognised Carrier A layout.
- Loss runs valued as of: {valued}
- Claims: count 0, paid $0, open $0
- Missing: {missing}
- Conflict: {conflict}
- Expected carrier route: {route}
- Expected recommendation: {rec}
- Expected loss run: Carrier A format recognised
- Expected pipeline status: {status}
"""

CASES = [
    dict(sid="SUB-290", name="Lone Oak Holdings LLC", address="4100 Lone Oak Pkwy", city="Mesquite", zip="75149",
         ops="Lessor of professional office building", items="business_type=office; no cooking",
         notes="one premises; cooking none; sprinklers full", sales="640000", tiv="2400000", sqft="2800",
         construction="Masonry", year="1998", sprinklers="Yes, full", cooking="None",
         body="The appraisal that came with the file is attached as schedule.csv. Everything else is on the application.",
         schedule=("3150", "2025"),
         read="application.md (typed English application, one premises, sales 640000, building 2400000, 2800 sq ft, masonry 1998, sprinklers full, cooking none, expiring Carrier A, no claims), email.md (one property, the appraisal is attached), schedule.csv (one row: Main building 3150 sq ft, built 2025), loss-runs.md (Carrier A layout, one period 2025-07-01 to 2026-07-01, valued 2026-07-15, no claims). One premises.",
         status="complete — review pending",
         missing="none",
         conflict="square feet: 2800 (application.md) vs 3150 (schedule.csv)",
         route="carrier_a (R14)",
         rec="Office lessor, no W1 or W2 word, TIV 2.4M <= 5M: the route is a recommendation only. The open conflict on the floor area holds the file until the underwriter chooses the area; nothing is declined.",
         expect="an open conflict on square footage with both sides stored (2800 from the application, 3150 from the appraisal schedule); the floor area is not a scored field, so every other field stays"),
    dict(sid="SUB-291", name="Riverside Commons LLC", address="77 Riverside Commons Dr", city="Garland", zip="75040",
         ops="Lessor of professional office building with two office suites on the second floor", items="business_type=office; no cooking",
         notes="one premises; cooking none; sprinklers full", sales="810000", tiv="1800000", sqft="5400",
         construction="Masonry", year="1991", sprinklers="Yes, full", cooking="None",
         body="We lease the offices on the second floor. The second floor holds three suites.",
         schedule=None,
         read="application.md (typed English application, one premises, sales 810000, building 1800000, 5400 sq ft, masonry 1991, sprinklers full, cooking none, two office suites, expiring Carrier A, no claims), email.md (one property; the second floor holds three suites), loss-runs.md (Carrier A layout, one period 2025-07-01 to 2026-07-01, valued 2026-07-15, no claims). One premises.",
         status="complete — review pending",
         missing="none",
         conflict="suite count: 2 (application.md) vs 3 (email.md)",
         route="carrier_a (R14)",
         rec="Office lessor, no W1 or W2 word, TIV 1.8M <= 5M: the route is a recommendation only. The open conflict on the number of suites holds the file until the underwriter chooses the count; nothing is declined.",
         expect="an open conflict on the suite count with both sides stored (2 from the application, 3 from the email); the operations value stays as the answer"),
    dict(sid="SUB-292", name="Lakeshore Holdings LLC", address="2300 Lakeshore Dr", city="Killeen", zip="76541",
         ops="Lessor of professional office building", items="business_type=office; no cooking",
         notes="one premises; cooking none; sprinklers full", sales="412000", tiv="1500000", sqft="4100",
         construction="Masonry", year="2000", sprinklers="Yes, full", cooking="None",
         body="Last year we did about 540k in sales. The rent roll on the application is lower because two suites are between tenants.",
         schedule=None,
         read="application.md (typed English application, one premises, annual sales 412000, building 1500000, 4100 sq ft, masonry 2000, sprinklers full, cooking none, expiring Carrier A, no claims), email.md (one property; about 540k in sales last year), loss-runs.md (Carrier A layout, one period 2025-07-01 to 2026-07-01, valued 2026-07-15, no claims). One premises.",
         status="incomplete",
         missing="sales or payroll (the two documents state different sales figures; the producer is asked which figure stands)",
         conflict="sales: 412000 (application.md) vs 540000 (email.md)",
         route="carrier_a (R14)",
         rec="Office lessor, no W1 or W2 word, TIV 1.5M <= 5M: the route is a recommendation only. The sales value is emptied and the file is asked for the sales figure; nothing is declined.",
         expect="an open conflict on sales or payroll with both sides stored (412000 from the application, 540000 from the email), the sales value emptied, and the file incomplete until the producer answers"),
    dict(sid="SUB-293", name="Brookfield Design Studio LLC", address="915 Brookfield Rd", city="Plano", zip="75074",
         ops="Office of an architectural design studio", items="business_type=office; no cooking",
         notes="one premises; sprinklers full", sales="950000", tiv="900000", sqft="3600",
         construction="Masonry", year="2005", sprinklers="Yes, full", cooking="None",
         body="We are an architecture studio on the first floor. There is no kitchen or any cooking on site.",
         schedule=None,
         read="application.md (typed English application, one premises, sales 950000, building 900000, 3600 sq ft, masonry 2005, sprinklers full, the line Cooking operations: None, expiring Carrier A, no claims), email.md (one property; no kitchen or cooking on site), loss-runs.md (Carrier A layout, one period 2025-07-01 to 2026-07-01, valued 2026-07-15, no claims). One premises.",
         status="complete — review pending",
         missing="none",
         conflict="none (one property, the email agrees)",
         route="carrier_a (R14)",
         rec="Office allow-list class, no W1 or W2 word, TIV 900K <= 5M: direct Carrier A route (R14). Not a decline.",
         expect="no conflict. P-072 (D-124): \"no cooking\" is never added to operations; the value stays as stated and the operations flag stays for the underwriter"),
    dict(sid="SUB-294", name="Fairmont Services LLC", address="640 Fairmont Blvd", city="Arlington", zip="76010",
         ops="Office of a professional services company with twelve employees", items="business_type=office; no cooking",
         notes="one premises; sprinklers full", sales="730000", tiv="1100000", sqft="4200",
         construction="Masonry", year="1996", sprinklers="Yes, full", cooking="None",
         body="The building is 4,200 square footage and sales were $730,000 last year. Nothing changed since the application.",
         schedule=None,
         read="application.md (typed English application, one premises, annual sales 730000, building 1100000, 4200 sq ft, masonry 1996, sprinklers full, cooking none, expiring Carrier A, no claims), email.md (one property; 4,200 square footage; sales $730,000), loss-runs.md (Carrier A layout, one period 2025-07-01 to 2026-07-01, valued 2026-07-15, no claims). One premises.",
         status="complete — review pending",  # P-072 (D-124): the operations flag (no cooking) stays
         missing="none",
         conflict="none (the email states the same area and the same sales figure)",
         route="carrier_a (R14)",
         rec="Office allow-list class, no W1 or W2 word, TIV 1.1M <= 5M: direct Carrier A route (R14). Not a decline.",
         expect="no conflict: the same figure in other words is the same figure (4,200 square footage is 4200; $730,000 is 730000)"),
    dict(sid="SUB-295", name="Stonegate Warehousing LLC", address="3300 Stonegate Way", city="Waco", zip="76712",
         ops="Lessor of professional office building with four units", items="business_type=office; no cooking",
         notes="one premises; cooking none; sprinklers full", sales="540000", tiv="1250000", sqft="6500",
         construction="Masonry", year="1994", sprinklers="Yes, full", cooking="None",
         body="We did about 540k in sales and the building is 6,500 sq ft. There are four units.",
         schedule=None,
         read="application.md (typed English application, one premises, annual sales 540000, building 1250000, 6500 sq ft, masonry 1994, sprinklers full, cooking none, four units, expiring Carrier A, no claims), email.md (one property; about 540k in sales; 6,500 sq ft; four units), loss-runs.md (Carrier A layout, one period 2025-07-01 to 2026-07-01, valued 2026-07-15, no claims). One premises.",
         status="complete — review pending",  # P-072 (D-124): the operations flag (no cooking) stays
         missing="none",
         conflict="none (the email states the same figures in other words)",
         route="carrier_a (R14)",
         rec="Office allow-list class, no W1 or W2 word, TIV 1.25M <= 5M: direct Carrier A route (R14). Not a decline.",
         expect="no conflict: about 540k and $540,000 are the same amount (540000); a rounding difference, on the other hand, is a disagreement and holds the file"),
    dict(sid="SUB-296", name="Harborview Insurance Agency LLC", address="1450 Harborview Dr", city="Corpus Christi", zip="78401",
         ops="Office of an insurance agency", items="business_type=office; cooking stated in the email (griddle, wok)",
         notes="one premises; sprinklers full; the application says cooking none, the email says a griddle and a wok were added", sales="620000", tiv="1300000", sqft="3900",
         construction="Masonry", year="2003", sprinklers="Yes, full", cooking="None",
         body="Since the application the tenant added a flat-top griddle and a wok station for staff lunches.",
         schedule=None, loss="published",
         read="application.md (typed English application, one premises, sales 620000, building 1300000, 3900 sq ft, masonry 2003, sprinklers full, the line Cooking operations: None, expiring Carrier A, no claims), email.md (one property; a flat-top griddle and a wok station were added), loss-runs.md (published Carrier A layout, one period 2025-07-01 to 2026-07-01, valued 2026-07-15, no claims). One premises.",
         status="complete — review pending",
         missing="none",
         conflict="none as a conflict topic; the operations value is flagged because the email states cooking equipment the application denies",
         route="hold until the underwriter clears the cooking flag",
         rec="Not complete: the application says no cooking, the email names a griddle and a wok. The operations value must not say no cooking; the underwriter decides. Not a decline.",
         expect="the @model-risk T-118 H1 case (P-072, D-124): the value does not gain \"no cooking\", the operations flag stays, and process_submission does not return complete"),
    dict(sid="SUB-297", name="Cedar Ridge Paper Supply LLC", address="5120 Cedar Ridge Ln", city="Temple", zip="76502",
         ops="Wholesale paper and packaging supplies, warehouse", items="business_type=wholesale; no cooking",
         notes="one premises; cooking none; sprinklers full; the application and the email state different sales", sales="1180000", tiv="640000", sqft="8800",
         construction="Metal", year="2001", sprinklers="Yes, full", cooking="None",
         body="Last year we did about $1.35 million, the application is the budget.",
         schedule=None, loss="published",
         read="application.md (typed English application, one premises, annual sales 1180000, building 640000, 8800 sq ft, metal 2001, sprinklers full, cooking none, expiring Carrier A, no claims), email.md (one property; about $1.35 million last year, the application is the budget), loss-runs.md (published Carrier A layout, one period 2025-07-01 to 2026-07-01, valued 2026-07-15, no claims). One premises.",
         status="incomplete — hold: open conflict (sales)",
         missing="sales or payroll (the application says 1180000, the email says about 1.35 million; the producer is asked which figure stands)",
         conflict="sales: 1180000 (application.md) vs 1350000, approximate (email.md)",
         route="hold until the underwriter chooses the sales figure",
         rec="Wholesale warehouse, no W1 or W2 word: the route is a recommendation only. The sales value is emptied and the file is held on the open conflict; nothing is declined and nothing is sent.",
         expect="P-074 (D-132), the SUB-345 shape: an open conflict on sales or payroll with both sides stored (the email side flagged approximate), the sales value emptied, not complete, not routed, not sendable; the card shows the reason"),
    dict(sid="SUB-298", name="Pinecrest Tile Supply LLC", address="880 Pinecrest Blvd", city="Round Rock", zip="78664",
         ops="Wholesale ceramic tile, warehouse", items="business_type=wholesale; no cooking",
         notes="one premises; cooking none; sprinklers full; three documents, three sales statements", sales="1150000", tiv="710000", sqft="9200",
         construction="Masonry", year="1999", sprinklers="Yes, full", cooking="None",
         body="We did roughly 1.2 million last year.",
         schedule=None, loss="published", extra=("broker-note.md", "Broker note\nSales ~$1.2m per the insured.\n"),
         read="application.md (typed English application, one premises, annual sales 1150000, building 710000, 9200 sq ft, masonry 1999, sprinklers full, cooking none, expiring Carrier A, no claims), email.md (one property; roughly 1.2 million last year), broker-note.md (Sales ~$1.2m per the insured), loss-runs.md (published Carrier A layout, one period 2025-07-01 to 2026-07-01, valued 2026-07-15, no claims). One premises.",
         status="incomplete — hold: open conflict (sales)",
         missing="sales or payroll (1150000 against about 1.2 million; the producer is asked which figure stands)",
         conflict="sales: 1150000 (application.md) vs 1200000, approximate (email.md; broker-note.md)",
         route="hold until the underwriter chooses the sales figure",
         rec="Wholesale warehouse, no W1 or W2 word: the route is a recommendation only. The sales value is emptied and the file is held on the open conflict; nothing is declined and nothing is sent.",
         expect="P-074 (D-132), D2: the model's stated sides cannot be checked against the quotes it gave, so every side is stored as unverified and the conflict is open; the sales value is emptied; the file is held and not sent"),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if INBOX.exists():
        shutil.rmtree(INBOX)
    INBOX.mkdir(parents=True, exist_ok=True)
    if GOLD.exists():
        shutil.rmtree(GOLD)
    GOLD.mkdir(parents=True, exist_ok=True)
    written = []
    for c in CASES:
        d = INBOX / c["sid"]
        d.mkdir(exist_ok=True)
        fmt = dict(c, fic=FICTIONAL, eff=EFF)
        (d / "application.md").write_text(APP.format(**fmt))
        (d / "email.md").write_text(EMAIL.format(**fmt))
        (d / "loss-runs.md").write_text((LOSS_PUBLISHED if c.get("loss") == "published" else LOSS).format(valued=VALUED, **fmt))
        if c.get("extra"):
            (d / c["extra"][0]).write_text(c["extra"][1])
        if c["schedule"]:
            (d / "schedule.csv").write_text(SCHED.format(sqft=c["schedule"][0], year=c["schedule"][1]))
        g = dict(c, eff=EFF, valued=VALUED)
        g.pop("loss", None)
        g.pop("extra", None)
        (GOLD / f"{c['sid']}.md").write_text(GOLD_T.format(**g))
        for path in sorted(d.iterdir()) + [GOLD / f"{c['sid']}.md"]:
            written.append(f"{sha256(path)}  {path.relative_to(ROOT)}")
    manifest = GOLD / "MANIFEST.sha256"
    manifest.write_text("\n".join(written) + "\n")
    print(f"document_conflicts dev set: {len(CASES)} files, manifest {manifest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
