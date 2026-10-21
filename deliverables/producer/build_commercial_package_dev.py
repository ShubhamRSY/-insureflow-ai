#!/usr/bin/env python3
"""Build the commercial_package DEV set (SUB-270-279) and its dev gold.

Dev only, synthetic, D-120. 6 in-scope + 4 out-of-scope (one per P-055 criterion).
Writes simulation/inbox-dev/commercial_package/ and
deliverables/senior-underwriter/gold-set-commercial_package/dev/.
No pipeline run, no model call, no write outside those two new folders.
"""
import shutil
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
INBOX = ROOT / "simulation" / "inbox-dev" / "commercial_package"
GOLD = ROOT / "deliverables" / "senior-underwriter" / "gold-set-commercial_package" / "dev"
VALUED = "2026-07-15"
EFF = "2026-12-01"

FICTIONAL = "**FICTIONAL.** All businesses, people, addresses and policy numbers are made up.\n\n"

CASES = [
    dict(sid="SUB-270", name="Cedar Park Office LLC", address="1200 Cedar Park Blvd", city="Austin", zip="78727",
         ops="Office", items="business_type=office; no cooking", sales="480000", tiv="1250000",
         bpp="60000", construction="Masonry", year="2001", stories="1", sprinklers="Yes, full",
         cooking="None", sqft="7200", route="carrier_a (R14)",
         rec="Office allow-list class, no W1 or W2 word, TIV 1.25M <= 5M: direct Carrier A route (R14). Not a decline."),
    dict(sid="SUB-271", name="Bluebonnet Dry Goods LLC", address="88 Bluebonnet Way", city="Round Rock", zip="78664",
         ops="Retail", items="business_type=retail; no cooking; no alcohol", sales="920000", tiv="850000",
         bpp="140000", construction="Masonry", year="1996", stories="1", sprinklers="Yes, full",
         cooking="None", sqft="9800", route="carrier_a (R14)",
         rec="Dry retail allow-list class, no W1 or W2 word, TIV 850K <= 5M: direct Carrier A route (R14). Not a decline."),
    dict(sid="SUB-272", name="Alamo Business Center LLC", address="410 Alamo Plaza", city="San Antonio", zip="78205",
         ops="Office", items="business_type=office; no cooking", sales="610000", tiv="2400000",
         bpp="95000", construction="Masonry", year="1988", stories="3", sprinklers="Yes, full",
         cooking="None", sqft="21000", route="carrier_a (R14)",
         rec="Office allow-list class, no W1 or W2 word, TIV 2.4M <= 5M: direct Carrier A route (R14). Not a decline."),
    dict(sid="SUB-273", name="Gulf Coast Apparel LLC", address="2330 Strand St", city="Galveston", zip="77550",
         ops="Retail", items="business_type=retail; no cooking; no alcohol", sales="740000", tiv="975000",
         bpp="165000", construction="Masonry", year="2004", stories="2", sprinklers="Yes, full",
         cooking="None", sqft="8400", route="carrier_a (R14)",
         rec="Clothing retail allow-list class, no W1 or W2 word, TIV 975K <= 5M: direct Carrier A route (R14). Not a decline."),
    dict(sid="SUB-274", name="Mesquite Table LLC", address="701 Mesquite St", city="Fort Worth", zip="76102",
         ops="Restaurant", items="business_type=restaurant; no alcohol", sales="1180000", tiv="690000",
         bpp="120000", construction="Masonry", year="1999", stories="1", sprinklers="Yes, full",
         cooking="Yes, fryer and griddle", sqft="5200",
         route="senior_referral, suggested market carrier_b (R10)",
         rec="Restaurant with cooking (R9/R10): senior_referral, suggested Carrier B; the underwriter confirms. Not a decline."),
    dict(sid="SUB-276", name="Lone Star Builders LLC", address="3900 Industry Rd", city="Houston", zip="77032",
         ops="Contractor", items="business_type=contractor; no cooking", sales="1650000", tiv="720000",
         bpp="230000", construction="Masonry", year="2002", stories="2", sprinklers="Yes, full",
         cooking="None", sqft="14600", route="senior_referral, suggested market carrier_b (R11)",
         rec="Contractor (R11): senior_referral, suggested Carrier B; the underwriter confirms. Not a decline."),
]

OUT = [
    dict(sid="SUB-275", criterion=1, line="criterion 1 (scanned application): the application is a JPG. Near-pass form: a clean, easily readable scan still goes to manual intake.",
         name="Sabine Family Dental PLLC", address="1500 Sabine St", city="Beaumont", zip="77701", ops="Dental office",
         sales="640000", tiv="380000", bpp="150000", construction="Masonry", year="2003", stories="1"),
    dict(sid="SUB-277", criterion=2, line="criterion 2 (multi-location: the application lists a second premises on a 'Location 2:' line and the schedule has two address rows).",
         name="Twin Oaks Storage LLC", address="2100 Twin Oaks Dr", city="Killeen", zip="76541", ops="Office",
         sales="410000", tiv="760000", bpp="72000", construction="Metal", year="2001", stories="1"),
    dict(sid="SUB-278", criterion=3, line="criterion 3 (non-English: the application is typed in Spanish).",
         name="Casa Verde Retail LLC", address="7700 Casa Verde Ave", city="Laredo", zip="78041", ops="Retail",
         sales="530000", tiv="480000", bpp="90000", construction="Masonry", year="1998", stories="1"),
    dict(sid="SUB-279", criterion=4, line="criterion 4 (application not identified: the file has an email and a loss run only, no application).",
         name="Piney Woods Office LLC", address="300 Piney Woods Rd", city="Tyler", zip="75701", ops="Office",
         sales="390000", tiv="520000", bpp="68000", construction="Masonry", year="2006", stories="1"),
]

APP = """{fic}# Application (ACORD 125/140/126 style)

Submission: {sid}
Named insured: {name}
Mailing address: same as premises
Premises address: {address}, {city} TX {zip}
Effective date: {eff}
Years in business: 9
Entity type: LLC
Line of business: Commercial package (property and general liability)
Operations: {ops}
Number of employees: 12
Annual sales: ${sales}
Property section
Building TIV: ${tiv}
Business personal property: ${bpp}
Square footage: {sqft}
Construction: {construction}
Year built: {year}
Stories: {stories}
Sprinklers: {sprinklers}
Cooking operations: {cooking}
General liability section
Occurrence basis: Yes
Each occurrence limit: $1,000,000
General aggregate limit: $2,000,000
Expiring carrier: Carrier A
Pending or open claims: None known
Bankruptcy or cancellation in last 5 years: No
"""

EMAIL = """{fic}Subject: {name} - package renewal

Attached is the commercial package application for {name} at {address}, {city}. The property schedule is one row and matches the application. No open claims; the loss run is attached from Carrier A.
"""

SCHED = """source,loc,address,city,zip,bldg_tiv,construction,year_built,sq_ft,sprinklers,cooking
application,1,{address},{city},{zip},${tiv},{construction},{year},{sqft},{sprinklers_short},{cooking_short}
"""

LOSS = """CARRIER A — LOSS RUN (FICTIONAL)
Named insured: {name}
Policy period: 2025-07-01 to 2026-07-01
Valued as of: {valued}
| Date of loss | Cause | Paid | Reserve | Status |
|---|---|---|---|---|
| None reported | — | $0 | $0 | — |
"""

GOLD_T = """# Gold answer - {sid}

- Author: @senior-underwriter (dev gold, written in OpenCode, not independently reviewed)
- Written for the D-120 commercial_package dev set from the documents and the written rules only (P-055 scope criteria 1-4; carrier-match.md R1-R17; operations-gold-rule.md; carrier-loss-run-formats.md; required-fields.md). Nothing was run. FICTIONAL. Dev only, not hold-out evidence, not a carrier decision.

- Source read by hand: application.md (typed English, {ops_lower}; 12 employees, sales {sales}, building {tiv}, BPP {bpp}, {sqft} sq ft, {construction} {year}, {stories} stories, sprinklers {sprinklers_lower}, cooking {cooking_lower}; expiring Carrier A; no claims), email.md (one property, schedule matches), schedule.csv (one row; matches), loss-runs.md (Carrier A layout, one period 2025-07-01 to 2026-07-01, valued {valued}, no claims). One premises.

- Status: complete
- Scope: in scope — typed English application, one premises, no scan of the application, a one-row schedule (not multi-location); no scope criterion applies.
- Named insured: {name}
- Premises: {address}, {city}, TX {zip}
- Effective date: {eff}
- Operations: {ops}
- Operations items: {items}
- Operations notes (unscored): BPP ${bpp}; sprinklers {sprinklers_lower}; package of property and general liability; one premises; cooking {cooking_lower}
- Sales: {sales}
- TIV: {tiv}
- Construction: {construction}
- Year built: {year}
- Loss runs: Carrier A format, 1 policy period 2025-07-01 to 2026-07-01, valued as of {valued}, no claims. Recognised Carrier A layout.
- Loss runs valued as of: {valued}
- Claims: count 0, paid $0, open $0
- Missing: not in documents (has valued date)
- Conflict: none (schedule matches application on TIV/sq ft/construction/year built)
- Format: typed md app (property + GL), typed md loss run (Carrier A), schedule csv, email
- Expected carrier route: {route}
- Expected recommendation: {rec}
- Expected loss run: Carrier A format recognised
- Expected pipeline status: complete
"""

OUT_GOLD = """# Gold answer - {sid}

- Author: @senior-underwriter (dev gold, written in OpenCode, not independently reviewed)
- Written for the D-120 commercial_package dev set from the documents and the written rules only (P-055 scope criteria 1-4). Nothing was run. FICTIONAL. Dev only, not hold-out evidence, not a carrier decision.
- Source read by hand: {read}. {reason}

- Status: manual intake
- Scope: out of scope — {line}
- Named insured: {name}
- Premises: {address}, {city}, TX {zip}
- Effective date: {eff}
- Operations: {ops}
- Sales: {sales}
- TIV: {tiv}
- Construction: {construction}
- Year built: {year}
- Missing: not assessed: a person reads the whole file.
- Conflict: none
- Expected carrier route: none — manual intake, no route, no suggested carrier
- Expected recommendation: Manual intake: {short}. No field is shown as complete, no route, no send. A person reads it.
- Expected loss run: not assessed — manual intake
- Expected pipeline status: manual intake
"""


def write_scan(path: Path, sid: str, name: str) -> None:
    img = Image.new("L", (1000, 700), "white")
    d = ImageDraw.Draw(img)
    d.text((40, 40), "FICTIONAL SCANNED APPLICATION", fill="black")
    d.text((40, 90), f"Submission: {sid}", fill="black")
    d.text((40, 130), f"Named insured: {name}", fill="black")
    d.text((40, 170), "Typed application, rendered as a JPG scan.", fill="black")
    d.text((40, 210), "Decorative only: no pipeline run reads this dev file.", fill="black")
    img.save(path, "JPEG")


def main() -> None:
    if INBOX.exists():
        shutil.rmtree(INBOX)
    INBOX.mkdir(parents=True, exist_ok=True)
    GOLD.mkdir(parents=True, exist_ok=True)
    for c in CASES:
        d = INBOX / c["sid"]
        d.mkdir(exist_ok=True)
        fmt = dict(c, fic=FICTIONAL, eff=EFF, sprinklers_short="Yes",
                   cooking_short=("Yes" if c["cooking"].startswith("Yes") else "No"))
        (d / "application.md").write_text(APP.format(**fmt))
        (d / "email.md").write_text(EMAIL.format(**fmt))
        (d / "schedule.csv").write_text(SCHED.format(**fmt))
        (d / "loss-runs.md").write_text(LOSS.format(valued=VALUED, **fmt))
        g = dict(c, eff=EFF, valued=VALUED, ops_lower=c["ops"][0].lower() + c["ops"][1:],
                 sprinklers_lower=c["sprinklers"].lower(), cooking_lower=c["cooking"].lower())
        (GOLD / f"{c['sid']}.md").write_text(GOLD_T.format(**g))

    for c in OUT:
        d = INBOX / c["sid"]
        d.mkdir(exist_ok=True)
        base = dict(c, fic=FICTIONAL, eff=EFF, sqft="8000", sprinklers="Yes, full", cooking="None",
                    sprinklers_short="Yes", cooking_short="No")
        if c["criterion"] == 1:
            write_scan(d / "application_scan.jpg", c["sid"], c["name"])
            (d / "email.md").write_text(EMAIL.format(**base))
            (d / "loss-runs.md").write_text(LOSS.format(valued=VALUED, **base))
            read = "application_scan.jpg (a JPG scan, not read by any rule), email.md, loss-runs.md (Carrier A)"
            reason = "The application is an image; manual intake."
        elif c["criterion"] == 2:
            app = APP.format(**base).replace("Premises address:", "Location 2: 44 Second St, Killeen TX 76541\nPremises address:")
            (d / "application.md").write_text(app)
            (d / "email.md").write_text(EMAIL.format(**base))
            (d / "loss-runs.md").write_text(LOSS.format(valued=VALUED, **base))
            (d / "schedule.csv").write_text(
                "source,loc,address,city,zip,bldg_tiv,construction,year_built,sq_ft,sprinklers,cooking\n"
                f"application,1,{c['address']},{c['city']},{c['zip']},${c['tiv']},{c['construction']},{c['year']},8000,Yes,No\n"
                f"application,2,44 Second St,Killeen,76541,$240000,{c['construction']},2001,3000,Yes,No\n")
            read = "application.md (a 'Location 2:' line), schedule.csv (two address rows), email.md, loss-runs.md"
            reason = "Two distinct locations; manual intake."
        elif c["criterion"] == 3:
            (d / "application.md").write_text(
                f"{FICTIONAL}# Solicitud (estilo ACORD 125/140)\n\n"
                f"Submission: {c['sid']}\nNombre asegurado: {c['name']}\n"
                f"Direccion: {c['address']}, {c['city']} TX {c['zip']}\n"
                f"Fecha de vigencia: {EFF}\nOperaciones: {c['ops']}\nVentas anuales: ${c['sales']}\n"
                f"Edificio TIV: ${c['tiv']}\nConstruccion: {c['construction']}\nAno construido: {c['year']}\n"
                f"Rociadores: Si\nCocina: No\n")
            (d / "email.md").write_text(EMAIL.format(**base))
            (d / "loss-runs.md").write_text(LOSS.format(valued=VALUED, **base))
            read = "application.md (typed Spanish), email.md, loss-runs.md"
            reason = "The application is not in English; manual intake."
        else:
            (d / "email.md").write_text(EMAIL.format(**base))
            (d / "loss-runs.md").write_text(LOSS.format(valued=VALUED, **base))
            read = "email.md, loss-runs.md (no application in the folder)"
            reason = "No application can be identified; manual intake."
        short = c["line"].split(":", 1)[1].strip() if ":" in c["line"] else c["line"]
        (GOLD / f"{c['sid']}.md").write_text(OUT_GOLD.format(
            sid=c["sid"], read=read, reason=reason, line=c["line"], name=c["name"], address=c["address"],
            city=c["city"], zip=c["zip"], eff=EFF, ops=c["ops"], sales=c["sales"], tiv=c["tiv"],
            construction=c["construction"], year=c["year"], short=short))

    print(f"wrote {len(CASES) + len(OUT)} dev submissions to {INBOX}")
    print(f"wrote {len(CASES) + len(OUT)} dev gold cards to {GOLD}")


if __name__ == "__main__":
    main()
