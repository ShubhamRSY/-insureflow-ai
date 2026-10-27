#!/usr/bin/env python3
"""Build SUB-206 .. SUB-225 (T-108 build stage 1a, in-scope half).

FICTIONAL synthetic submissions. Deterministic and re-runnable.

Usage:
    .venv/bin/python build_SUB-206-225.py <worktree_root>

Writes only under <worktree_root>/simulation/inbox/SUB-206 .. SUB-225.
"""

import csv
import io
import os
import sys
import textwrap
import zipfile

from PIL import Image, ImageDraw, ImageFont
import openpyxl

FICT_MD = "**FICTIONAL.** All businesses, people, addresses and policy numbers are made up."
FICT_PLAIN = "FICTIONAL. All businesses, people, addresses and policy numbers are made up."

FIELD_ORDER = [
    "Named insured",
    "Mailing address",
    "Premises address",
    "Effective date",
    "Years in business",
    "Entity type",
    "Line of business",
    "Operations",
    "Number of employees",
    "Annual sales",
    "Building TIV",
    "Business personal property",
    "Square footage",
    "Construction",
    "Year built",
    "Stories",
    "Sprinklers",
    "Cooking operations",
    "Expiring carrier",
    "Pending or open claims",
    "Bankruptcy or cancellation in last 5 years",
]

SCHED_COLS = [
    "source", "loc", "address", "city", "zip", "bldg_tiv",
    "construction", "year_built", "sq_ft", "sprinklers", "cooking",
]

FONT_SANS = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_COURIER = "/System/Library/Fonts/Supplemental/Courier New.ttf"


# ---------------------------------------------------------------- text files

def write_text(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text if text.endswith("\n") else text + "\n")


def email_md(subject, body):
    return (
        FICT_MD + "\n\n"
        "Subject: " + subject + "\n\n"
        + body.strip() + "\n"
    )


def app_md(subid, fields):
    out = [FICT_MD, "", "# Application (ACORD 125/140 style)", "",
           "Submission: " + subid]
    for key in FIELD_ORDER:
        val = fields.get(key)
        if val is not None:
            out.append("%s: %s" % (key, val))
    return "\n".join(out) + "\n"


def app_plain_lines(subid, fields):
    out = [FICT_PLAIN, "Application (ACORD 125/140 style)", "Submission: " + subid]
    for key in FIELD_ORDER:
        val = fields.get(key)
        if val is not None:
            out.append("%s: %s" % (key, val))
    return out


# ---------------------------------------------------------------- schedules

def schedule_csv(path, row):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(SCHED_COLS)
        writer.writerow([row.get(col, "") for col in SCHED_COLS])


def _fixed_props(wb):
    import datetime
    stamp = datetime.datetime(2026, 10, 1, 9, 0, 0)
    wb.properties.creator = "FICTIONAL"
    wb.properties.lastModifiedBy = "FICTIONAL"
    wb.properties.title = "FICTIONAL"
    wb.properties.created = stamp
    wb.properties.modified = stamp


def _normalise_zip(path):
    import re
    tmp = path + ".tmp"
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "docProps/core.xml":
                # openpyxl stamps dcterms:modified with the current time on save
                data = re.sub(
                    rb"(<dcterms:modified[^>]*>)[^<]*(</dcterms:modified>)",
                    rb"\g<1>2026-10-01T09:00:00Z\g<2>", data)
            info = zipfile.ZipInfo(item.filename, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = item.external_attr
            zout.writestr(info, data)
    os.replace(tmp, path)


def schedule_xlsx(path, row):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Schedule"
    ws.append(SCHED_COLS)
    ws.append([row.get(col, "") for col in SCHED_COLS])
    _fixed_props(wb)
    wb.save(path)
    _normalise_zip(path)


def lossrun_xlsx(path, lines):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "LossRun"
    for line in lines:
        if line.startswith("|") and set(line) <= set("|-"):
            continue
        if line.startswith("|"):
            ws.append([c.strip() for c in line.strip("|").split("|")])
        else:
            ws.append([line])
    _fixed_props(wb)
    wb.save(path)
    _normalise_zip(path)


def lossrun_md(path, lines):
    write_text(path, "\n".join(lines) + "\n")


# ---------------------------------------------------------------- loss runs

def lr_carrier_a(name, periods, valued, rows):
    lines = ["CARRIER A — LOSS RUN (FICTIONAL)", "Named insured: " + name]
    lines += ["Policy period: " + p for p in periods]
    if valued:
        lines.append("Valued as of: " + valued)
    if rows:
        lines += ["| Date of loss | Cause | Paid | Reserve | Status |",
                  "|---|---|---|---|---|"]
        lines += ["| " + " | ".join(r) + " |" for r in rows]
    else:
        lines.append("No claims reported by Carrier A for the policy periods above.")
    return lines


def lr_carrier_b(name, terms, valued, rows):
    lines = ["Carrier B Loss History Report (fictional)", "Insured: " + name]
    lines += ["Policy term: " + t for t in terms]
    if valued:
        lines.append("Valuation date: " + valued)
    if rows:
        lines += ["| Loss date | Description | Paid | Outstanding |",
                  "|---|---|---|---|"]
        lines += ["| " + " | ".join(r) + " |" for r in rows]
    else:
        lines.append("Carrier B certifies no claims for the policy terms above.")
    return lines


def lr_carrier_c(name, terms, valued, rows):
    lines = ["CARRIER C | LOSS RUN | FICTIONAL", "Account: " + name]
    lines += ["Term: " + t for t in terms]
    if valued:
        lines.append("Valued: " + valued)
    if rows:
        lines += ["| Claim no. | Loss date | Type | Paid | Open reserve |",
                  "|---|---|---|---|---|"]
        lines += ["| " + " | ".join(r) + " |" for r in rows]
    else:
        lines.append("Carrier C: no claims reported.")
    return lines


# ---------------------------------------------------------------- scans

def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _wrapped(lines, width):
    out = []
    for line in lines:
        if not line:
            out.append("")
        else:
            out.extend(textwrap.wrap(line, width=width) or [""])
    return out


def scan_jpeg_bytes(lines, font_path, size=24, width=1275, height=1650,
                    wrap=64, tilt=0.6):
    img = Image.new("L", (width, height), 244)
    draw = ImageDraw.Draw(img)
    for y in range(0, height, 4):
        shade = 233 + int(12 * y / height)
        draw.line([(0, y), (width, y)], fill=shade)
    for x in range(width - 26, width):
        draw.line([(x, 0), (x, height)], fill=214)
    font = _font(font_path, size)
    x0, y0 = 118, 132
    leading = int(size * 1.5)
    for i, line in enumerate(_wrapped(lines, wrap)):
        draw.text((x0, y0 + i * leading), line, fill=28, font=font)
    img = img.rotate(tilt, resample=Image.BICUBIC, expand=False, fillcolor=228)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=82)
    return buf.getvalue()


def write_scan(path, lines, font_path, size=24, wrap=64):
    with open(path, "wb") as fh:
        fh.write(scan_jpeg_bytes(lines, font_path, size=size, wrap=wrap))


# ---------------------------------------------------------------- PDF writer

def _pdf_escape(text):
    raw = text.encode("cp1252", "replace")
    return (raw.replace(b"\\", b"\\\\")
               .replace(b"(", b"\\(")
               .replace(b")", b"\\)"))


def _assemble_pdf(objects):
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += ("%d 0 obj\n" % number).encode("ascii") + body + b"\nendobj\n"
    xref = len(out)
    size = len(objects) + 1
    out += ("xref\n0 %d\n" % size).encode("ascii")
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += ("%010d 00000 n \n" % off).encode("ascii")
    out += ("trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (size, xref)).encode("ascii")
    return bytes(out)


def typed_pdf_bytes(lines, size=10, leading=13.6, wrap=96):
    body = bytearray()
    body += b"BT\n/F1 %g Tf\n%g TL\n1 0 0 1 54 756 Tm\n" % (size, leading)
    for line in _wrapped(lines, wrap):
        body += b"(" + _pdf_escape(line) + b") Tj T*\n"
    body += b"ET\n"
    stream = bytes(body)
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
         b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"),
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"endstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    return _assemble_pdf(objects)


def write_typed_pdf(path, lines):
    with open(path, "wb") as fh:
        fh.write(typed_pdf_bytes(lines))


def write_image_pdf(path, jpeg_bytes, width=1275, height=1650):
    content = b"q 612 0 0 792 0 0 cm /Im0 Do Q"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
         b"/Resources << /XObject << /Im0 5 0 R >> >> /Contents 4 0 R >>"),
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
        (b"<< /Type /XObject /Subtype /Image /Width %d /Height %d "
         b"/ColorSpace /DeviceGray /BitsPerComponent 8 /Filter /DCTDecode "
         b"/Length %d >>\nstream\n" % (width, height, len(jpeg_bytes))
         + jpeg_bytes + b"\nendstream"),
    ]
    with open(path, "wb") as fh:
        fh.write(_assemble_pdf(objects))


# ---------------------------------------------------------------- build

def build(root):
    inbox = os.path.join(root, "simulation", "inbox")
    if not os.path.isdir(inbox):
        sys.exit("not a worktree root (missing simulation/inbox): %s" % root)

    def sub_dir(subid):
        path = os.path.join(inbox, subid)
        if not os.path.isdir(path):
            os.makedirs(path)
        return path

    # start clean so the directory matches the script exactly
    import shutil
    for n in range(206, 226):
        path = os.path.join(inbox, "SUB-%d" % n)
        if os.path.isdir(path):
            shutil.rmtree(path)
        os.makedirs(path)

    sections = []

    # ---------------------------------------------------------- SUB-206
    d = sub_dir("SUB-206")
    write_text(os.path.join(d, "email.md"), email_md(
        "Bluebonnet Ridge Office Park - office building, eff 1/1/27",
        """Dear team, Bluebonnet Ridge Office Park is a 3 story office building in Austin
(Westlake area). The owner leases suites to small tenants and doesnt operate anything
himself. New to our agency, been with Carrier A a long time. App and schedule attached,
loss run is As typed copy. They want property and GL. Renewal is 1/1/27.

Thanks, Marcy Delgado, Delgado & Sloane Insurance"""))
    fields = {
        "Named insured": "Bluebonnet Ridge Office Park LLC",
        "Mailing address": "same as premises",
        "Premises address": "3800 Bee Caves Rd, Austin, TX 78746",
        "Effective date": "2027-01-01",
        "Years in business": "16",
        "Entity type": "LLC",
        "Line of business": "Commercial property, general liability",
        "Operations": ("Owns and leases office suites to tenants; 3-story office building, "
                       "22 suites, common lobby and restrooms. Building owner/lessor only, "
                       "no tenant operations. No tenant cooking."),
        "Number of employees": "2",
        "Annual sales": "$742,000 (annual rents)",
        "Building TIV": "$2,450,000",
        "Business personal property": "$28,000",
        "Square footage": "41,500",
        "Construction": "Masonry",
        "Year built": "2005",
        "Stories": "3",
        "Sprinklers": "Yes",
        "Cooking operations": "None",
        "Expiring carrier": "Carrier A, expiring 2026-12-31",
        "Pending or open claims": "One water damage 2024, closed, $6,400 paid",
        "Bankruptcy or cancellation in last 5 years": "No",
    }
    write_text(os.path.join(d, "application.md"), app_md("SUB-206", fields))
    schedule_csv(os.path.join(d, "schedule.csv"), {
        "source": "FICTIONAL", "loc": 1, "address": "3800 Bee Caves Rd",
        "city": "Austin", "zip": "78746", "bldg_tiv": 2450000,
        "construction": "Masonry", "year_built": 2005, "sq_ft": 41500,
        "sprinklers": "Yes", "cooking": "none",
    })
    write_text(os.path.join(d, "loss-runs.md"), "\n".join(lr_carrier_a(
        "Bluebonnet Ridge Office Park LLC",
        ["2023-06-01 to 2024-06-01", "2024-06-01 to 2025-06-01",
         "2025-06-01 to 2026-06-01"],
        "2026-08-15",
        [["2024-07-18", "broken water pipe", "$6,400", "$0", "closed"]])) + "\n")
    sections.append("SUB-206")

    # ---------------------------------------------------------- SUB-207
    d = sub_dir("SUB-207")
    write_text(os.path.join(d, "email.md"), email_md(
        "Pecan Street Sandwich Co - deli / sub shop, SA, eff 2/1/27",
        """Hey, Pecan Street Sandwich Co. runs a deli and sub shop downtown San Antonio (the
sign says sandwich shop). Counter service, cold prep only, no hood and no fryer. Theyre on
Carrier B now and want to stay there. I typed the app up as a PDF, Carrier B loss history
attached.

Thx, Ray Ochoa (Ochoa & Vance)"""))
    fields = {
        "Named insured": "Pecan Street Sandwich Co. LLC",
        "DBA": "Pecan St Deli & Sub Shop",
        "Mailing address": "same as premises",
        "Premises address": "714 E Houston St, San Antonio, TX 78205",
        "Effective date": "2027-02-01",
        "Years in business": "9",
        "Entity type": "LLC",
        "Line of business": "BOP - restaurant",
        "Operations": ("Deli and sub shop (sandwich shop), counter service, cold prep and "
                       "assembly only. No cooking, no fryer, no hood. Retail seating for 24."),
        "Number of employees": "6 full time, 3 part time",
        "Annual sales": "$612,000",
        "Building TIV": "$0 (tenant)",
        "Business personal property": "$95,000",
        "Square footage": "1,850",
        "Construction": "Masonry",
        "Year built": "1968",
        "Stories": "1",
        "Sprinklers": "No",
        "Cooking operations": "None (cold prep)",
        "Expiring carrier": "Carrier B, expiring 2027-01-31",
        "Pending or open claims": "None",
        "Bankruptcy or cancellation in last 5 years": "No",
    }
    f = dict(fields)
    f.pop("DBA")
    write_typed_pdf(os.path.join(d, "application.pdf"), app_plain_lines("SUB-207", fields))
    write_text(os.path.join(d, "loss-runs.md"), "\n".join(lr_carrier_b(
        "Pecan Street Sandwich Co. LLC",
        ["2023-02-01 to 2024-02-01", "2024-02-01 to 2025-02-01",
         "2025-02-01 to 2026-02-01"],
        "2026-07-31", [])) + "\n")
    sections.append("SUB-207")

    # ---------------------------------------------------------- SUB-208
    d = sub_dir("SUB-208")
    write_text(os.path.join(d, "email.md"), email_md(
        "Lone Star Craft Supply - wholesale, Waco",
        """Hi, Lone Star Craft Supply is a small wholesale distributor of craft and hobby
supplies in Waco. They sell to shops only, no walk in. App and schedule attached. Loss
runs are coming from their old carrier, should be a day or two. No losses that Im aware
of. They want BPP and GL.

Cullen Rusk, Rusk Insurance"""))
    fields = {
        "Named insured": "Lone Star Craft Supply LLC",
        "Mailing address": "PO Box 2214, Waco, TX 76703",
        "Premises address": "1518 Franklin Ave, Waco, TX 76701",
        "Effective date": "2027-01-15",
        "Years in business": "7",
        "Entity type": "LLC",
        "Line of business": "Commercial property, general liability - wholesale",
        "Operations": ("Wholesale distributor of craft and hobby supplies and small-package "
                       "novelties. Sells to retail shops only. Warehouse shelving and a small "
                       "office. No manufacturing, no retail walk-in."),
        "Number of employees": "5",
        "Annual sales": "$1,480,000",
        "Building TIV": "$640,000",
        "Business personal property": "$210,000",
        "Square footage": "12,400",
        "Construction": "Tilt-up concrete",
        "Year built": "1998",
        "Stories": "1",
        "Sprinklers": "Yes",
        "Cooking operations": "None",
        "Expiring carrier": "Caprock Specialty, expiring 2027-01-14",
        "Pending or open claims": "None known",
        "Bankruptcy or cancellation in last 5 years": "No",
    }
    write_text(os.path.join(d, "application.md"), app_md("SUB-208", fields))
    schedule_csv(os.path.join(d, "schedule.csv"), {
        "source": "FICTIONAL", "loc": 1, "address": "1518 Franklin Ave",
        "city": "Waco", "zip": "76701", "bldg_tiv": 640000,
        "construction": "Tilt-up concrete", "year_built": 1998, "sq_ft": 12400,
        "sprinklers": "Yes", "cooking": "none",
    })
    sections.append("SUB-208")

    # ---------------------------------------------------------- SUB-209
    d = sub_dir("SUB-209")
    write_text(os.path.join(d, "email.md"), email_md(
        "Garcia & Sons Flatwork - concrete contractor, San Antonio",
        """Hi, Garcia & Sons Flatwork does concrete work (driveways, patios, sidewalks, small
slabs), about 12 guys, they sub out maybe a quarter of it. Doing around 1.6 mil the last
couple yrs. App is attached, I typed it up. The Carrier B loss run is a scan, sorry theyre
a little dark. Want GL and a little on the tools. Eff 12/1/26.

Anita Vela"""))
    fields = {
        "Named insured": "Garcia & Sons Flatwork LLC",
        "Mailing address": "same as premises",
        "Premises address": "4319 Rittiman Rd, San Antonio, TX 78218",
        "Effective date": "2026-12-01",
        "Years in business": "12",
        "Entity type": "LLC",
        "Line of business": "Commercial general liability - contractor",
        "Operations": ("Concrete flatwork contractor: driveways, patios, sidewalks and small "
                       "commercial slabs. 12 employees; approximately 25% of work subcontracted "
                       "to other concrete crews. No roofing, no demolition, no structural."),
        "Number of employees": "12",
        "Annual sales": "$1,248,000",
        "Building TIV": "$0 (tenant office and yard)",
        "Business personal property": "$140,000 (tools and equipment)",
        "Square footage": "2,200",
        "Construction": "Masonry",
        "Year built": "1991",
        "Stories": "1",
        "Sprinklers": "No",
        "Cooking operations": "None",
        "Expiring carrier": "Carrier B, expiring 2026-11-30",
        "Pending or open claims": "One fence damage claim 2025, closed, $2,150 paid",
        "Bankruptcy or cancellation in last 5 years": "No",
    }
    write_text(os.path.join(d, "application.md"), app_md("SUB-209", fields))
    lr = lr_carrier_b("Garcia & Sons Flatwork LLC",
                      ["2023-09-01 to 2024-09-01", "2024-09-01 to 2025-09-01",
                       "2025-09-01 to 2026-09-01"],
                      "2026-06-15",
                      [["2025-03-12", "trailer hit client fence", "$2,150", "$0"]])
    write_scan(os.path.join(d, "loss-runs_scan.jpg"),
               [FICT_PLAIN] + lr, FONT_COURIER, size=23, wrap=62)
    sections.append("SUB-209")

    # ---------------------------------------------------------- SUB-210
    d = sub_dir("SUB-210")
    write_text(os.path.join(d, "email.md"), email_md(
        "Magnolia Court Apartments - Tyler, 14 units",
        """Hi, Magnolia Court is 14 units in Tyler, garden style, two buildings, long term
tenants. Carrier C has them now. Schedule is in the xlsx I attached, loss run too.
Eff 3/1/27.

Doug Kiefer"""))
    fields = {
        "Named insured": "Magnolia Court Apartments LLC",
        "Mailing address": "same as premises",
        "Premises address": "2110 E Southeast Loop 323, Tyler, TX 75701",
        "Effective date": "2027-03-01",
        "Years in business": "14",
        "Entity type": "LLC",
        "Line of business": "Commercial property, general liability - habitational",
        "Operations": ("Residential apartments, 14 units in 2 two-story garden buildings, "
                       "long-term leases. On-site part-time manager. No short-term rentals."),
        "Number of employees": "2",
        "Annual sales": "$224,000 (gross rents)",
        "Building TIV": "$2,350,000",
        "Business personal property": "$34,000",
        "Square footage": "16,800",
        "Construction": "Masonry",
        "Year built": "1996",
        "Stories": "2",
        "Sprinklers": "Yes",
        "Cooking operations": "Tenant electric ranges only",
        "Expiring carrier": "Carrier C, expiring 2027-03-01",
        "Pending or open claims": "None known",
        "Bankruptcy or cancellation in last 5 years": "No",
    }
    write_text(os.path.join(d, "application.md"), app_md("SUB-210", fields))
    schedule_xlsx(os.path.join(d, "schedule.xlsx"), {
        "source": "FICTIONAL", "loc": 1, "address": "2110 E Southeast Loop 323",
        "city": "Tyler", "zip": "75701", "bldg_tiv": 2350000,
        "construction": "Masonry", "year_built": 1996, "sq_ft": 16800,
        "sprinklers": "Yes", "cooking": "tenant ranges",
    })
    write_text(os.path.join(d, "loss-runs.md"), "\n".join(lr_carrier_c(
        "Magnolia Court Apartments LLC",
        ["2023-07-01 - 2024-07-01", "2024-07-01 - 2025-07-01",
         "2025-07-01 - 2026-07-01"],
        "2026-06-30",
        [["C-33471", "2024-12-09", "water damage (frozen pipe)", "$11,200", "$0"]])) + "\n")
    sections.append("SUB-210")

    # ---------------------------------------------------------- SUB-211
    d = sub_dir("SUB-211")
    write_text(os.path.join(d, "email.md"), email_md(
        "Vaquero Smokehouse & Grill - Laredo, eff 2/1/27",
        """Hey, Vaquero Smokehouse & Grill is our new one in Laredo, we just moved them to
their new spot on Guadalupe. Full service, mesquite grill and a smoker, Type I hood with
ansul, 96 seats, full bar. Carrier B loss history attached (its a pdf off the portal).
They close at 11, no dancing.

Luz Herrera"""))
    fields = {
        "Named insured": "Vaquero Smokehouse & Grill LLC",
        "Mailing address": "same as premises",
        "Premises address": "1120 Commerce St, Laredo, TX 78040",
        "Effective date": "2027-02-01",
        "Years in business": "6",
        "Entity type": "LLC",
        "Line of business": "BOP - restaurant",
        "Operations": ("Full-service restaurant: mesquite grill and offset smoker with Type I "
                       "hood and ansul system, 96 seats. Full bar (beer, wine, liquor). Closes "
                       "at 11 p.m. No dancing or late-night entertainment."),
        "Number of employees": "22",
        "Annual sales": "$1,980,000",
        "Building TIV": "$0 (tenant)",
        "Business personal property": "$180,000",
        "Square footage": "3,600",
        "Construction": "Masonry",
        "Year built": "1994",
        "Stories": "1",
        "Sprinklers": "No",
        "Cooking operations": "Mesquite grill and smoker, Type I hood and ansul",
        "Expiring carrier": "Carrier B, expiring 2027-01-31",
        "Pending or open claims": "One kitchen hood fire 2025, closed, $24,500 paid",
        "Bankruptcy or cancellation in last 5 years": "No",
    }
    write_text(os.path.join(d, "application.md"), app_md("SUB-211", fields))
    lr = lr_carrier_b("Vaquero Smokehouse & Grill LLC",
                      ["2023-03-01 to 2024-03-01", "2024-03-01 to 2025-03-01",
                       "2025-03-01 to 2026-03-01"],
                      "2026-07-20",
                      [["2025-02-08", "kitchen hood fire", "$24,500", "$0"]])
    write_image_pdf(os.path.join(d, "loss-runs.pdf"),
                    scan_jpeg_bytes([FICT_PLAIN] + lr, FONT_COURIER, size=23, wrap=62))
    sections.append("SUB-211")

    # ---------------------------------------------------------- SUB-212
    d = sub_dir("SUB-212")
    write_text(os.path.join(d, "email.md"), email_md(
        "Reyes Finish Carpentry - Fort Worth",
        """Reyes Finish Carpentry does interior finish work and cabinet installs, 3 crews, no
roofing and no structural. The owner says theyve never filed a claim, so instead of runs we
have a no-known-loss letter (attached). App attached. Eff 1/15/27.

Blake Ferris"""))
    fields = {
        "Named insured": "Reyes Finish Carpentry LLC",
        "Mailing address": "same as premises",
        "Premises address": "2900 Race St, Fort Worth, TX 76111",
        "Effective date": "2027-01-15",
        "Years in business": "5",
        "Entity type": "LLC",
        "Line of business": "Commercial general liability - contractor",
        "Operations": ("Interior finish carpentry and cabinet installation, residential and "
                       "light commercial. 6 employees in 3 crews. No roofing, no structural, "
                       "no demolition, no exterior work above 2 stories."),
        "Number of employees": "6",
        "Annual sales": "$740,000",
        "Building TIV": "$0 (tenant)",
        "Business personal property": "$46,000 (tools)",
        "Construction": "Masonry",
        "Year built": "1984",
        "Stories": "1",
        "Sprinklers": "No",
        "Cooking operations": "None",
        "Expiring carrier": "Brazos Surplus, expiring 2027-01-14",
        "Pending or open claims": "None known",
        "Bankruptcy or cancellation in last 5 years": "No",
    }
    write_text(os.path.join(d, "application.md"), app_md("SUB-212", fields))
    write_text(os.path.join(d, "loss-runs.md"), """No known loss letter

To whom it may concern,

Reyes Finish Carpentry LLC has had no known losses since the business began in 2021. The
owner asks that this letter be accepted in place of carrier loss runs.

FICTIONAL. Not a loss run.
""")
    sections.append("SUB-212")

    # ---------------------------------------------------------- SUB-213
    d = sub_dir("SUB-213")
    write_text(os.path.join(d, "email.md"), email_md(
        "Cedar Park Office Suites - office building, eff 4/1/27",
        """Hi, Cedar Park Office Suites owns a single story office building in Cedar Park and
leases the suites to small professionals (an insurance agent, an accountant, a therapist).
Building owner only, no tenant cooking. App and schedule attached, the loss run is a typed
copy from Carrier A.

Priya Nandakumar"""))
    fields = {
        "Named insured": "Cedar Park Office Suites LLC",
        "Mailing address": "same as premises",
        "Premises address": "1101 Cypress Creek Rd, Cedar Park, TX 78613",
        "Effective date": "2027-04-01",
        "Years in business": "10",
        "Entity type": "LLC",
        "Line of business": "Commercial property, general liability",
        "Operations": ("Owns and leases a single-story office building; 9 suites leased to "
                       "small professional tenants (insurance, accounting, therapy). Office "
                       "building lessor only. No tenant cooking, no retail."),
        "Number of employees": "1",
        "Annual sales": "$388,000 (annual rents)",
        "Building TIV": "$1,980,000",
        "Business personal property": "$19,000",
        "Square footage": "32,600",
        "Construction": "Masonry",
        "Year built": "2008",
        "Stories": "1",
        "Sprinklers": "Yes",
        "Cooking operations": "None",
        "Expiring carrier": "Carrier A, expiring 2027-03-31",
        "Pending or open claims": "None known",
        "Bankruptcy or cancellation in last 5 years": "No",
    }
    write_text(os.path.join(d, "application.md"), app_md("SUB-213", fields))
    schedule_csv(os.path.join(d, "schedule.csv"), {
        "source": "FICTIONAL", "loc": 1, "address": "1101 Cypress Creek Rd",
        "city": "Cedar Park", "zip": "78613", "bldg_tiv": 1980000,
        "construction": "Masonry", "year_built": 2008, "sq_ft": 32600,
        "sprinklers": "Yes", "cooking": "none",
    })
    lr = lr_carrier_a("Cedar Park Office Suites LLC",
                      ["2023-04-01 to 2024-04-01", "2024-04-01 to 2025-04-01",
                       "2025-04-01 to 2026-04-01"],
                      "2026-04-30",
                      [["2024-10-02", "roof leak (storm)", "$8,900", "$0", "closed"]])
    lossrun_md(os.path.join(d, "loss-runs.md"), lr)
    sections.append("SUB-213")

    # ---------------------------------------------------------- SUB-214
    d = sub_dir("SUB-214")
    write_text(os.path.join(d, "email.md"), email_md(
        "Brazos Bend Outfitters - College Station retail",
        """Brazos Bend Outfitters is a retail store in College Station, outdoor gear, apparel
and footwear. No repair, no guns, no fuel. App is attached, I typed it up. Schedule
attached. Ill send loss runs once the client signs the release.

Wes Tolliver"""))
    fields = {
        "Named insured": "Brazos Bend Outfitters LLC",
        "Mailing address": "same as premises",
        "Premises address": "2209 Texas Ave S, College Station, TX 77840",
        "Effective date": "2027-02-15",
        "Years in business": "8",
        "Entity type": "LLC",
        "Line of business": "BOP - retail",
        "Operations": ("Retail store, outdoor gear, apparel and footwear. No repair, no fuel, "
                       "no firearms, no rentals."),
        "Number of employees": "7",
        "Annual sales": "$1,120,000",
        "Building TIV": "$0 (tenant)",
        "Business personal property": "$260,000",
        "Square footage": "9,800",
        "Construction": "Masonry",
        "Year built": "2003",
        "Stories": "1",
        "Sprinklers": "Yes",
        "Cooking operations": "None",
        "Expiring carrier": "Carrier A, expiring 2027-02-14",
        "Pending or open claims": "None known",
        "Bankruptcy or cancellation in last 5 years": "No",
    }
    write_text(os.path.join(d, "application.md"), app_md("SUB-214", fields))
    schedule_csv(os.path.join(d, "schedule.csv"), {
        "source": "FICTIONAL", "loc": 1, "address": "2209 Texas Ave S",
        "city": "College Station", "zip": "77840", "bldg_tiv": 890000,
        "construction": "Masonry", "year_built": 2003, "sq_ft": 9800,
        "sprinklers": "Yes", "cooking": "none",
    })
    sections.append("SUB-214")

    # ---------------------------------------------------------- SUB-215
    d = sub_dir("SUB-215")
    write_text(os.path.join(d, "email.md"), email_md(
        "Delgado's Deli & Market - Corpus Christi, eff 3/1/27",
        """Delgado's Deli & Market in Corpus Christi, a deli and sandwich shop with a small
grocery/market side. Cold prep only, no cooking, no fryer, no hood. Carrier B loss history
attached. Need property and GL. Eff 3/1/27.

Carla Mendez"""))
    fields = {
        "Named insured": "Delgado's Deli & Market LLC",
        "Mailing address": "same as premises",
        "Premises address": "5802 S Staples St, Corpus Christi, TX 78413",
        "Effective date": "2027-03-01",
        "Years in business": "11",
        "Entity type": "LLC",
        "Line of business": "BOP - restaurant",
        "Operations": ("Deli and sandwich shop with a small grocery/market section (canned "
                       "and dry goods, no meat counter). Cold prep and assembly only, no "
                       "cooking, no fryer, no hood. 6 tables."),
        "Number of employees": "8",
        "Annual sales": "$845,000",
        "Building TIV": "$0 (tenant)",
        "Business personal property": "$120,000",
        "Square footage": "2,400",
        "Construction": "Masonry",
        "Year built": "1986",
        "Stories": "1",
        "Sprinklers": "No",
        "Cooking operations": "None (cold prep)",
        "Expiring carrier": "Carrier B, expiring 2027-02-28",
        "Pending or open claims": "One slip and fall 2024, closed, $3,750 paid",
        "Bankruptcy or cancellation in last 5 years": "No",
    }
    write_typed_pdf(os.path.join(d, "application.pdf"), app_plain_lines("SUB-215", fields))
    write_text(os.path.join(d, "loss-runs.md"), "\n".join(lr_carrier_b(
        "Delgado's Deli & Market LLC",
        ["2022-08-01 to 2023-08-01", "2023-08-01 to 2024-08-01",
         "2024-08-01 to 2025-08-01"],
        "2026-07-15",
        [["2024-01-19", "customer slip on wet floor", "$3,750", "$0"]])) + "\n")
    sections.append("SUB-215")

    # ---------------------------------------------------------- SUB-216
    d = sub_dir("SUB-216")
    write_text(os.path.join(d, "email.md"), email_md(
        "Trinity Paper & Packaging - Irving, light wholesale",
        """Trinity Paper & Packaging distributes paper and packaging supplies to restaurants
and offices. Warehouse plus a small office, no manufacturing. They moved to a bigger space
this year so the sq ft on the old schedule is smaller than what the app says now. Loss run
from Carrier A attached but I dont see a valuation date on it, can you live with it?

Josh Renfro"""))
    fields = {
        "Named insured": "Trinity Paper & Packaging LLC",
        "Mailing address": "same as premises",
        "Premises address": "3300 N Belt Line Rd, Irving, TX 75062",
        "Effective date": "2027-01-01",
        "Years in business": "9",
        "Entity type": "LLC",
        "Line of business": "Commercial property, general liability - wholesale",
        "Operations": ("Wholesale distributor of paper and packaging supplies to restaurants "
                       "and offices. Warehouse racking and a small office. No manufacturing."),
        "Number of employees": "9",
        "Annual sales": "$2,140,000",
        "Building TIV": "$1,390,000",
        "Business personal property": "$320,000",
        "Square footage": "24,500",
        "Construction": "Tilt-up concrete",
        "Year built": "1996",
        "Stories": "1",
        "Sprinklers": "Yes",
        "Cooking operations": "None",
        "Expiring carrier": "Carrier A, expiring 2026-12-31",
        "Pending or open claims": "One forklift/rack claim 2024, closed, $5,100 paid",
        "Bankruptcy or cancellation in last 5 years": "No",
    }
    write_text(os.path.join(d, "application.md"), app_md("SUB-216", fields))
    schedule_csv(os.path.join(d, "schedule.csv"), {
        "source": "FICTIONAL", "loc": 1, "address": "3300 N Belt Line Rd",
        "city": "Irving", "zip": "75062", "bldg_tiv": 1390000,
        "construction": "Tilt-up concrete", "year_built": 1996, "sq_ft": 18900,
        "sprinklers": "Yes", "cooking": "none",
    })
    write_text(os.path.join(d, "loss-runs.md"), "\n".join(lr_carrier_a(
        "Trinity Paper & Packaging LLC",
        ["2023-08-01 to 2024-08-01", "2024-08-01 to 2025-08-01",
         "2025-08-01 to 2026-08-01"],
        None,
        [["2024-06-27", "forklift damaged rack", "$5,100", "$0", "closed"]])) + "\n")
    sections.append("SUB-216")

    # ---------------------------------------------------------- SUB-217
    d = sub_dir("SUB-217")
    write_text(os.path.join(d, "email.md"), email_md(
        "Cypress Bend Apartments - Midland (partial)",
        """Cypress Bend is 10 units in Midland, two wood frame buildings. Sending the app and
the Carrier C loss run now, Ill follow up with the schedule today or tomorrow. Eff 5/1/27.

Tammy Spence"""))
    fields = {
        "Named insured": "Cypress Bend Apartments LLC",
        "Mailing address": "same as premises",
        "Premises address": "911 N Big Spring St, Midland, TX 79701",
        "Effective date": "2027-05-01",
        "Years in business": "6",
        "Entity type": "LLC",
        "Line of business": "Commercial property, general liability - habitational",
        "Operations": ("Residential apartments, 10 units in 2 two-story wood frame buildings, "
                       "long-term leases. On-site manager unit. No short-term rentals."),
        "Number of employees": "1",
        "Annual sales": "$171,000 (gross rents)",
        "Building TIV": "$1,290,000",
        "Business personal property": "$22,000",
        "Square footage": "9,800",
        "Construction": "Wood frame",
        "Year built": "1979",
        "Stories": "2",
        "Sprinklers": "Yes",
        "Cooking operations": "Tenant electric ranges only",
        "Expiring carrier": "Carrier C, expiring 2027-05-01",
        "Pending or open claims": "One hail claim 2024, closed, $14,600 paid",
        "Bankruptcy or cancellation in last 5 years": "No",
    }
    write_text(os.path.join(d, "application.md"), app_md("SUB-217", fields))
    lr = lr_carrier_c("Cypress Bend Apartments LLC",
                      ["2023-05-01 - 2024-05-01", "2024-05-01 - 2025-05-01",
                       "2025-05-01 - 2026-05-01"],
                      "2026-08-05",
                      [["C-88021", "2024-09-15", "hail (roof)", "$14,600", "$0"]])
    write_scan(os.path.join(d, "loss-runs.jpg"),
               [FICT_PLAIN] + lr, FONT_COURIER, size=23, wrap=62)
    sections.append("SUB-217")

    # ---------------------------------------------------------- SUB-218
    d = sub_dir("SUB-218")
    write_text(os.path.join(d, "email.md"), email_md(
        "Gulf Coast Cold Storage - Beaumont",
        """Gulf Coast Cold Storage is a refrigerated warehouse in Beaumont, frozen and chilled
goods for food distributors. Ammonia refrigeration plant on site, monitored. They want
property, GL and a B and M quote. Loss run is the pdf from Carrier C, schedule in xlsx.

Elena Ruiz"""))
    fields = {
        "Named insured": "Gulf Coast Cold Storage LLC",
        "Mailing address": "same as premises",
        "Premises address": "5895 Eastex Fwy, Beaumont, TX 77706",
        "Effective date": "2027-04-01",
        "Years in business": "15",
        "Entity type": "LLC",
        "Line of business": "Commercial property, general liability, boiler & machinery",
        "Operations": ("Refrigerated cold storage warehouse for frozen and chilled goods, "
                       "serving food distributors. Ammonia refrigeration plant (2 compressors), "
                       "monitored 24/7. Storage only, no processing or packaging."),
        "Number of employees": "14",
        "Annual sales": "$3,620,000",
        "Building TIV": "$4,200,000",
        "Business personal property": "$860,000",
        "Square footage": "46,500",
        "Construction": "Fire-resistive",
        "Year built": "2001",
        "Stories": "1",
        "Sprinklers": "Yes",
        "Cooking operations": "None",
        "Expiring carrier": "Carrier C, expiring 2027-03-31",
        "Pending or open claims": "One ammonia leak 2025, no injury, closed, $7,400 paid",
        "Bankruptcy or cancellation in last 5 years": "No",
    }
    write_text(os.path.join(d, "application.md"), app_md("SUB-218", fields))
    schedule_xlsx(os.path.join(d, "schedule.xlsx"), {
        "source": "FICTIONAL", "loc": 1, "address": "5895 Eastex Fwy",
        "city": "Beaumont", "zip": "77706", "bldg_tiv": 4200000,
        "construction": "Fire-resistive", "year_built": 2001, "sq_ft": 46500,
        "sprinklers": "Yes", "cooking": "none",
    })
    lr = lr_carrier_c("Gulf Coast Cold Storage LLC",
                      ["2023-04-01 - 2024-04-01", "2024-04-01 - 2025-04-01",
                       "2025-04-01 - 2026-04-01"],
                      "2026-08-31",
                      [["C-51209", "2025-04-02", "ammonia leak (no injury)", "$7,400", "$0"]])
    write_image_pdf(os.path.join(d, "loss-runs.pdf"),
                    scan_jpeg_bytes([FICT_PLAIN] + lr, FONT_COURIER, size=23, wrap=62))
    sections.append("SUB-218")

    # ---------------------------------------------------------- SUB-219
    d = sub_dir("SUB-219")
    write_text(os.path.join(d, "email.md"), email_md(
        "Sabine Protective Coatings - Port Arthur, light manufacturing",
        """Sabine Protective Coatings makes and blends industrial paint and solvent based
coatings in Port Arthur, small batch, no bulk tanks, flammables in a rated cabinet. Light
manufacturing. App and schedule attached. Their Carrier C run has no valuation date on it,
hope thats ok.

Grant Holloway"""))
    fields = {
        "Named insured": "Sabine Protective Coatings LLC",
        "Mailing address": "same as premises",
        "Premises address": "2701 Memorial Blvd, Port Arthur, TX 77640",
        "Effective date": "2027-02-01",
        "Years in business": "13",
        "Entity type": "LLC",
        "Line of business": "Commercial property, general liability - manufacturing",
        "Operations": ("Light manufacturing: blending and packaging of industrial paints and "
                       "solvent-based coatings, small batch. No bulk storage above ground; "
                       "flammable liquids in a rated cabinet, max 55 gal per batch. Small office."),
        "Number of employees": "11",
        "Annual sales": "$1,740,000",
        "Building TIV": "$1,450,000",
        "Business personal property": "$410,000",
        "Square footage": "28,600",
        "Construction": "Fire-resistive",
        "Year built": "1989",
        "Stories": "1",
        "Sprinklers": "Yes",
        "Cooking operations": "None",
        "Expiring carrier": "Carrier C, expiring 2027-01-31",
        "Pending or open claims": "One solvent spill cleanup 2024, closed, $9,800 paid",
        "Bankruptcy or cancellation in last 5 years": "No",
    }
    write_text(os.path.join(d, "application.md"), app_md("SUB-219", fields))
    schedule_csv(os.path.join(d, "schedule.csv"), {
        "source": "FICTIONAL", "loc": 1, "address": "4810 Twin City Hwy",
        "city": "Groves", "zip": "77619", "bldg_tiv": 1450000,
        "construction": "Fire-resistive", "year_built": 1989, "sq_ft": 28600,
        "sprinklers": "Yes", "cooking": "none",
    })
    write_text(os.path.join(d, "loss-runs.md"), "\n".join(lr_carrier_c(
        "Sabine Protective Coatings LLC",
        ["2023-02-01 - 2024-02-01", "2024-02-01 - 2025-02-01",
         "2025-02-01 - 2026-02-01"],
        None,
        [["C-41007", "2024-11-21", "solvent spill cleanup", "$9,800", "$0"]])) + "\n")
    sections.append("SUB-219")

    # ---------------------------------------------------------- SUB-220
    d = sub_dir("SUB-220")
    write_text(os.path.join(d, "email.md"), email_md(
        "Golden Wok Express - Houston, eff 12/15/26",
        """Golden Wok Express is a fast casual Chinese restaurant in Houston, wok line with a
Type I hood and ansul, mostly takeout, 18 seats, no bar. Theyre only 2 yrs old so no carrier
runs, the owner gave us a no-known-loss letter. App attached. Eff 12/15/26.

Marta Quintero"""))
    fields = {
        "Named insured": "Golden Wok Express LLC",
        "Mailing address": "same as premises",
        "Premises address": "6830 Hwy 6 N, Houston, TX 77084",
        "Effective date": "2026-12-15",
        "Years in business": "2",
        "Entity type": "LLC",
        "Line of business": "BOP - restaurant",
        "Operations": ("Fast-casual Chinese restaurant: wok line with Type I hood and ansul, "
                       "takeout and limited seating for 18. No bar, no alcohol."),
        "Number of employees": "9",
        "Annual sales": "$690,000",
        "Building TIV": "$0 (tenant)",
        "Business personal property": "$75,000",
        "Square footage": "1,600",
        "Construction": "Masonry",
        "Year built": "1999",
        "Stories": "1",
        "Sprinklers": "Yes",
        "Cooking operations": "Wok range, Type I hood and ansul",
        "Expiring carrier": "Brazos Surplus (non-renewing), expiring 2026-12-14",
        "Pending or open claims": "None known",
        "Bankruptcy or cancellation in last 5 years": "No",
    }
    write_text(os.path.join(d, "application.md"), app_md("SUB-220", fields))
    write_text(os.path.join(d, "loss-runs.md"), """No known loss letter

To whom it may concern,

Golden Wok Express LLC opened in 2024 and has had no known losses. The owner asks that this
letter be accepted in place of carrier loss runs.

FICTIONAL. Not a loss run.
""")
    sections.append("SUB-220")

    # ---------------------------------------------------------- SUB-221
    d = sub_dir("SUB-221")
    write_text(os.path.join(d, "email.md"), email_md(
        "Yucca Flats Retail Center - Odessa, VACANT",
        """Yucca Flats is a small retail strip in Odessa, 6 units, and right now its VACANT,
the last tenant left in June. Owner is marketing it. Building only, no contents, no BI. Need
to see if anyone will write a vacant property. App is a typed pdf, schedule xlsx, and the
loss run is a typed copy from Carrier A.

Devon Pratt"""))
    fields = {
        "Named insured": "Yucca Flats Retail Center LLC",
        "Mailing address": "PO Box 1188, Odessa, TX 79760",
        "Premises address": "2801 E 42nd St, Odessa, TX 79762",
        "Effective date": "2027-03-01",
        "Years in business": "20",
        "Entity type": "LLC",
        "Line of business": "Commercial property (vacant), general liability",
        "Operations": ("Small retail strip center, 6 units, currently 100% vacant (last tenant "
                       "vacated June 2026). Building owner. No contents, no business income. "
                       "Owner is marketing the space."),
        "Number of employees": "0",
        "Annual sales": "$0 (vacant, no rents)",
        "Building TIV": "$1,650,000",
        "Business personal property": "$0",
        "Square footage": "22,000",
        "Construction": "Masonry",
        "Year built": "1985",
        "Stories": "1",
        "Sprinklers": "Yes",
        "Cooking operations": "None",
        "Expiring carrier": "Carrier A, expiring 2027-02-28",
        "Pending or open claims": "None known",
        "Bankruptcy or cancellation in last 5 years": "No",
    }
    write_typed_pdf(os.path.join(d, "application.pdf"), app_plain_lines("SUB-221", fields))
    schedule_xlsx(os.path.join(d, "schedule.xlsx"), {
        "source": "FICTIONAL", "loc": 1, "address": "2801 E 42nd St",
        "city": "Odessa", "zip": "79762", "bldg_tiv": 1650000,
        "construction": "Masonry", "year_built": 1985, "sq_ft": 22000,
        "sprinklers": "Yes", "cooking": "none",
    })
    lr = lr_carrier_a("Yucca Flats Retail Center LLC",
                      ["2023-08-01 to 2024-08-01", "2024-08-01 to 2025-08-01",
                       "2025-08-01 to 2026-08-01"],
                      "2026-08-20",
                      [["2025-03-04", "roof leak (storm)", "$4,600", "$0", "closed"]])
    lossrun_md(os.path.join(d, "loss-runs.md"), lr)
    sections.append("SUB-221")

    # ---------------------------------------------------------- SUB-222
    d = sub_dir("SUB-222")
    write_text(os.path.join(d, "email.md"), email_md(
        "Neon Spur Nightclub - Dallas, eff 12/1/26",
        """Neon Spur is a nightclub downtown Dallas, open until 2am, full liquor bar, dance
floor and DJ, bottle service, cover charge at the door, 350 capacity. Their current broker
told the owner the carrier is non-renewing because of the bar and liquor exposure. App attached, the
year built is not on it (owner thinks late 70s, checking with the county). Loss run from
Carrier C attached. Eff 12/1/26.

Shea Bannister"""))
    fields = {
        "Named insured": "Neon Spur Nightclub LLC",
        "Mailing address": "same as premises",
        "Premises address": "1808 Main St, Dallas, TX 75201",
        "Effective date": "2026-12-01",
        "Years in business": "4",
        "Entity type": "LLC",
        "Line of business": "Commercial general liability, property",
        "Operations": ("Nightclub open until 2:00 a.m.: full liquor bar, dance floor and DJ "
                       "booth, bottle service, cover charge at the door. Capacity 350, 21+ "
                       "only."),
        "Number of employees": "24",
        "Annual sales": "$1,980,000",
        "Building TIV": "$1,250,000",
        "Business personal property": "$340,000",
        "Square footage": "8,600",
        "Construction": "Masonry",
        "Year built": None,
        "Stories": "2",
        "Sprinklers": "Yes",
        "Cooking operations": "None (bar snacks only)",
        "Expiring carrier": "Carrier C (non-renewing), expiring 2026-11-30",
        "Pending or open claims": "One broken window 2025, closed, $1,900 paid",
        "Bankruptcy or cancellation in last 5 years": "Non-renewal notice received",
    }
    write_text(os.path.join(d, "application.md"), app_md("SUB-222", fields))
    write_text(os.path.join(d, "loss-runs.md"), "\n".join(lr_carrier_c(
        "Neon Spur Nightclub LLC",
        ["2023-08-01 - 2024-08-01", "2024-08-01 - 2025-08-01",
         "2025-08-01 - 2026-08-01"],
        "2026-05-27",
        [["C-60118", "2025-01-12", "broken window", "$1,900", "$0"]])) + "\n")
    sections.append("SUB-222")

    # ---------------------------------------------------------- SUB-223
    d = sub_dir("SUB-223")
    write_text(os.path.join(d, "email.md"), email_md(
        "Llano Verde Apartments - Del Rio, signed app attached",
        """Llano Verde is 12 units in Del Rio, older wood frame, no sprinklers. The signed app
is attached now, along with the schedule and the owners own loss summary (not a carrier run,
he typed it himself). Eff 1/1/27.

Bea Ostrander"""))
    fields = {
        "Named insured": "Llano Verde Apartments LP",
        "Mailing address": "same as premises",
        "Premises address": "3402 Veterans Blvd, Del Rio, TX 78840",
        "Effective date": "2027-01-01",
        "Years in business": "19",
        "Entity type": "Limited partnership",
        "Line of business": "Commercial property, general liability - habitational",
        "Operations": ("Residential apartments, 12 units in a single two-story wood frame "
                       "building, long-term leases, on-site manager unit. No short-term "
                       "rentals, no commercial tenants."),
        "Number of employees": "1",
        "Annual sales": "$168,000 (gross rents)",
        "Building TIV": "$1,180,000",
        "Business personal property": "$18,000",
        "Square footage": "11,200",
        "Construction": "Wood frame",
        "Year built": "1974",
        "Stories": "2",
        "Sprinklers": "No",
        "Cooking operations": "Tenant electric ranges only",
        "Expiring carrier": "Brazos Surplus, lapsed 2026-10-01",
        "Pending or open claims": "None known",
        "Bankruptcy or cancellation in last 5 years": "No",
    }
    write_text(os.path.join(d, "application.md"), app_md("SUB-223", fields))
    schedule_csv(os.path.join(d, "schedule.csv"), {
        "source": "FICTIONAL", "loc": 1, "address": "3402 Veterans Blvd",
        "city": "Del Rio", "zip": "78840", "bldg_tiv": 1180000,
        "construction": "Wood frame", "year_built": 1974, "sq_ft": 11200,
        "sprinklers": "No", "cooking": "tenant ranges",
    })
    write_text(os.path.join(d, "loss-runs.md"), """**FICTIONAL.** All businesses, people, addresses and policy numbers are made up.

Loss history - prepared by the owner, as of 2026-08-28 (not a carrier loss run)

| Year | Carrier | Policy | Type | Date | Paid | Status |
|---|---|---|---|---|---|---|
| 2022 | Brazos Surplus | BS-33120 | No losses | - | $0 | Closed |
| 2023 | Brazos Surplus | BS-33120 | No losses | - | $0 | Closed |
| 2024 | Brazos Surplus | BS-40188 | No losses | - | $0 | Closed |
| 2025 | Brazos Surplus | BS-40188 | No losses | - | $0 | Closed |
| 2026 | Brazos Surplus (lapsed 10/1) | BS-40188 | No losses | - | $0 | Closed |
""")
    sections.append("SUB-223")

    # ---------------------------------------------------------- SUB-224
    d = sub_dir("SUB-224")
    write_text(os.path.join(d, "email.md"), email_md(
        "Cypress Bend Apartments - Midland - COMPLETE resubmission",
        """Sorry for the mess, this replaces the partial package I sent earlier this week (the
first one had no schedule). Here is the complete Cypress Bend file: app, schedule xlsx and
the Carrier C loss run. Same effective date 5/1/27.

Tammy Spence"""))
    fields = {
        "Named insured": "Cypress Bend Apartments LLC",
        "Mailing address": "same as premises",
        "Premises address": "911 N Big Spring St, Midland, TX 79701",
        "Effective date": "2027-05-01",
        "Years in business": "6",
        "Entity type": "LLC",
        "Line of business": "Commercial property, general liability - habitational",
        "Operations": ("Residential apartments, 10 units in 2 two-story wood frame buildings, "
                       "long-term leases. On-site manager unit. No short-term rentals."),
        "Number of employees": "1",
        "Annual sales": "$171,000 (gross rents)",
        "Building TIV": "$1,290,000",
        "Business personal property": "$22,000",
        "Square footage": "9,800",
        "Construction": "Wood frame",
        "Year built": "1979",
        "Stories": "2",
        "Sprinklers": "Yes",
        "Cooking operations": "Tenant electric ranges only",
        "Expiring carrier": "Carrier C, expiring 2027-05-01",
        "Pending or open claims": "One hail claim 2024, closed, $14,600 paid",
        "Bankruptcy or cancellation in last 5 years": "No",
    }
    write_text(os.path.join(d, "application.md"), app_md("SUB-224", fields))
    schedule_xlsx(os.path.join(d, "schedule.xlsx"), {
        "source": "FICTIONAL", "loc": 1, "address": "911 N Big Spring St",
        "city": "Midland", "zip": "79701", "bldg_tiv": 1290000,
        "construction": "Wood frame", "year_built": 1979, "sq_ft": 9800,
        "sprinklers": "Yes", "cooking": "tenant ranges",
    })
    write_text(os.path.join(d, "loss-runs.md"), "\n".join(lr_carrier_c(
        "Cypress Bend Apartments LLC",
        ["2023-05-01 - 2024-05-01", "2024-05-01 - 2025-05-01",
         "2025-05-01 - 2026-05-01"],
        "2026-07-06",
        [["C-88021", "2024-09-15", "hail (roof)", "$14,600", "$0"]])) + "\n")
    sections.append("SUB-224")

    # ---------------------------------------------------------- SUB-225
    d = sub_dir("SUB-225")
    write_text(os.path.join(d, "email.md"), email_md(
        "La Vida Loca Lounge & Bar - Amarillo, eff 12/1/26",
        """La Vida Loca is a lounge and bar in Amarillo, full liquor license, open until 2am,
DJ and a small dance floor on weekends, no kitchen. Their broker says the carrier won't write it because of the bar and liquor exposure. Year
built is not on the app, the owner is checking with the county. Loss run is the portal pdf
from Carrier C. Eff 12/1/26.

Marcus Deveraux"""))
    fields = {
        "Named insured": "La Vida Loca Lounge & Bar LLC",
        "Mailing address": "same as premises",
        "Premises address": "6501 Amarillo Blvd W, Amarillo, TX 79106",
        "Effective date": "2026-12-01",
        "Years in business": "3",
        "Entity type": "LLC",
        "Line of business": "Commercial general liability, property",
        "Operations": ("Lounge and bar with full liquor license, open until 2:00 a.m. DJ and "
                       "small dance floor on weekends. 21+. No food service beyond bar snacks."),
        "Number of employees": "12",
        "Annual sales": "$1,140,000",
        "Building TIV": "$940,000",
        "Business personal property": "$180,000",
        "Square footage": "7,200",
        "Construction": "Masonry",
        "Year built": None,
        "Stories": "1",
        "Sprinklers": "Yes",
        "Cooking operations": "None (bar snacks only)",
        "Expiring carrier": "Carrier B (non-renewing), expiring 2026-11-30",
        "Pending or open claims": "One water damage 2024, closed, $3,300 paid",
        "Bankruptcy or cancellation in last 5 years": "No",
    }
    write_text(os.path.join(d, "application.md"), app_md("SUB-225", fields))
    lr = lr_carrier_c("La Vida Loca Lounge & Bar LLC",
                      ["2023-05-01 - 2024-05-01", "2024-05-01 - 2025-05-01",
                       "2025-05-01 - 2026-05-01"],
                      "2026-06-01",
                      [["C-72214", "2024-06-14", "water damage", "$3,300", "$0"]])
    write_image_pdf(os.path.join(d, "loss-runs.pdf"),
                    scan_jpeg_bytes([FICT_PLAIN] + lr, FONT_COURIER, size=23, wrap=62))
    sections.append("SUB-225")

    print("Wrote %d submissions: %s .. %s" %
          (len(sections), sections[0], sections[-1]))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: %s <worktree_root>" % sys.argv[0])
    build(os.path.abspath(sys.argv[1]))
