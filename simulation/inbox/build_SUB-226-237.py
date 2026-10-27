#!/usr/bin/env python3
"""Build SUB-226 .. SUB-237 (T-108 build stage 1b, out-of-scope half).

FICTIONAL synthetic submissions. Deterministic and re-runnable.
Every one of these must be handed to a person to read, each for a stated reason:
  criterion 1 = application is a scan (scanned JPG, or image-only PDF)
  criterion 2 = more than one location / premises
  criterion 3 = application not in English
  criterion 4 = email only, no identifiable application

Counts (12 total): 1 x4, 2 x5, 3 x4, 4 x2. Each file carries one
criterion, except three files that carry two criteria at once, and exactly
two files that carry criterion 4 alone. Criteria per file:

  SUB-226  C4        email only
  SUB-227  C4        email only
  SUB-228  C1        scanned JPG application
  SUB-229  C1        image-only PDF application
  SUB-230  C1        scanned JPG application
  SUB-231  C1+C2     scanned JPG application listing two buildings
  SUB-232  C2        "Location No. 2" in application
  SUB-233  C2        "Loc #2" / "Premises 2" in application, two-row schedule
  SUB-234  C3        Spanish single-location application (typed PDF)
  SUB-235  C3        Spanish single-location application letter (md)
  SUB-236  C3+C2     Spanish application listing two locations (typed PDF)
  SUB-237  C3+C2     Spanish application letter + second store in the email

  criterion 1 : SUB-228, 229, 230, 231                    (4)
  criterion 2 : SUB-231, 232, 233, 236, 237               (5)
  criterion 3 : SUB-234, 235, 236, 237                    (4)
  criterion 4 : SUB-226, 227                              (2)  alone = 2
  two-criteria files : SUB-231, 236, 237                  (3)

Loss runs on these files are NOT constrained (the file is hand-read either
way), so they stay realistic and varied.

Usage:
    .venv/bin/python build_SUB-226-237.py <worktree_root>

Writes only under <worktree_root>/simulation/inbox/SUB-226 .. SUB-237.
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
    return (FICT_MD + "\n\n"
            "Subject: " + subject + "\n\n"
            + body.strip() + "\n")


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


def app_spanish_lines(subid, campos):
    out = [FICT_PLAIN, "SOLICITUD DE SEGURO (estilo ACORD 125/140)", "",
           "Sometimiento: " + subid]
    for key, val in campos:
        out.append("%s: %s" % (key, val))
    return out


# ---------------------------------------------------------------- schedules

def schedule_csv(path, rows):
    if isinstance(rows, dict):
        rows = [rows]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(SCHED_COLS)
        for row in rows:
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
                data = re.sub(
                    rb"(<dcterms:modified[^>]*>)[^<]*(</dcterms:modified>)",
                    rb"\g<1>2026-10-01T09:00:00Z\g<2>", data)
            info = zipfile.ZipInfo(item.filename, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = item.external_attr
            zout.writestr(info, data)
    os.replace(tmp, path)


def schedule_xlsx(path, rows):
    if isinstance(rows, dict):
        rows = [rows]
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Schedule"
    ws.append(SCHED_COLS)
    for row in rows:
        ws.append([row.get(col, "") for col in SCHED_COLS])
    _fixed_props(wb)
    wb.save(path)
    _normalise_zip(path)


# ---------------------------------------------------------------- loss runs

def lr_carrier_d(name, terms, valued, rows):
    lines = ["CARRIER D — LOSS RUN (FICTIONAL)", "Insured: " + name]
    lines += ["Policy term: " + t for t in terms]
    if valued:
        lines.append("Valued as of: " + valued)
    if rows:
        lines += ["| Date of loss | Cause | Paid | Reserve | Status |",
                  "|---|---|---|---|---|"]
        lines += ["| " + " | ".join(r) + " |" for r in rows]
    else:
        lines.append("No claims reported by Carrier D for the terms above.")
    return lines


def lr_carrier_e(name, terms, valued, rows):
    lines = ["CARRIER E LOSS HISTORY (FICTIONAL)", "Named insured: " + name]
    lines += ["Term: " + t for t in terms]
    if valued:
        lines.append("Valued as of: " + valued)
    if rows:
        lines += ["| Loss date | Description | Paid | Open |",
                  "|---|---|---|---|"]
        lines += ["| " + " | ".join(r) + " |" for r in rows]
    else:
        lines.append("No losses on file with Carrier E.")
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

    import shutil
    for n in range(226, 240):
        path = os.path.join(inbox, "SUB-%d" % n)
        if os.path.isdir(path):
            shutil.rmtree(path)
    for n in range(226, 238):
        os.makedirs(os.path.join(inbox, "SUB-%d" % n))

    sections = []

    # ====================================================== C4 email only (2)

    # ---------------------------------------------------------- SUB-226 : C4
    # criterion 4: email only, no identifiable application
    d = sub_dir("SUB-226")
    write_text(os.path.join(d, "email.md"), email_md(
        "Sandia Peak Drywall - Albuquerque area / El Paso jobs",
        """Hey, got one for you. Sandia Peak Drywall does commercial drywall and metal stud
framing, they work mostly on El Paso and Hudspeth county jobs, about 14 guys and two
subcrews. Theyre between brokers and the old carrier cancelled for nonpayment (owner says it
was a billing mixup, theyre paid up now). They do hang and finish, SOME acoustic ceilings,
no fireproofing and no demolition. Doing around 2.1 mil. Need GL and a little on the tools
and a trailer. No policy number handy, waiting on their old agent to release the loss runs.
Can we get an indication? Eff 1/1/27.

Bertrand Okoye"""))
    sections.append("SUB-226")

    # ---------------------------------------------------------- SUB-227 : C4
    # criterion 4: email only, no identifiable application
    d = sub_dir("SUB-227")
    write_text(os.path.join(d, "email.md"), email_md(
        "Copper Creek Landscape & Irrigation - Round Rock",
        """Copper Creek does commercial landscape and irrigation in the Austin/Round Rock
area, install and maintenance contracts, no tree work above 20 ft, no chemical spraying
(they sub that out). Four trucks, a small yard in Round Rock with a shop building, owner
says its about 3,800 sf on half an acre, built around 1999, frame. Stores a little fertilizer
in bags, no bulk. Around $1.35 mil. They want property on the shop and contents plus GL and
commercial auto, maybe an umbrella. No app yet, I typed up what I have from the phone call.
Renewal eff 3/1/27. Loss runs should come from their carrier once they sign the release.

Reina Escobar"""))
    sections.append("SUB-227")

    # ====================================================== C1 scans (4)

    # ---------------------------------------------------------- SUB-228 : C1
    # criterion 1: application_scan.jpg (scanned JPG application)
    d = sub_dir("SUB-228")
    write_text(os.path.join(d, "email.md"), email_md(
        "Alamo Hydraulics & Machine - San Antonio machine shop",
        """Alamo Hydraulics & Machine is a small machine shop on the south side, they do
hydraulic cylinder repair and some new fab for the oilfield, 8 guys, manual lathes and a
mill, no foundry. App is a scan of the signed form, the Carrier D loss run is typed. Theyre
on Carrier D now and staying if the price is right. Eff 2/1/27.

Ruben Salas"""))
    fields = {
        "Named insured": "Alamo Hydraulics & Machine LLC",
        "Mailing address": "same as premises",
        "Premises address": "5920 S Flores St, San Antonio, TX 78214",
        "Effective date": "2027-02-01",
        "Years in business": "17",
        "Entity type": "LLC",
        "Line of business": "Commercial property, general liability - manufacturing",
        "Operations": ("Machine shop: hydraulic cylinder repair and light fabrication for the "
                       "oilfield. Manual lathes, one mill, welding bay. No foundry, no casting, "
                       "no grinding of exotic metals."),
        "Number of employees": "8",
        "Annual sales": "$1,060,000",
        "Building TIV": "$720,000",
        "Business personal property": "$335,000",
        "Square footage": "9,400",
        "Construction": "Masonry",
        "Year built": "1988",
        "Stories": "1",
        "Sprinklers": "No",
        "Cooking operations": "None",
        "Expiring carrier": "Carrier D, expiring 2027-01-31",
        "Pending or open claims": "One cut hand (no lost time) 2024, closed, $1,200 medical",
        "Bankruptcy or cancellation in last 5 years": "No",
    }
    write_scan(os.path.join(d, "application_scan.jpg"),
               app_plain_lines("SUB-228", fields), FONT_SANS, size=23, wrap=62)
    write_text(os.path.join(d, "loss-runs.md"), "\n".join(lr_carrier_d(
        "Alamo Hydraulics & Machine LLC",
        ["2023-02-01 to 2024-02-01", "2024-02-01 to 2025-02-01",
         "2025-02-01 to 2026-02-01"],
        "2026-08-30",
        [["2024-03-05", "employee cut hand (no lost time)", "$1,200", "$0", "closed"]])) + "\n")
    sections.append("SUB-228")

    # ---------------------------------------------------------- SUB-229 : C1
    # criterion 1: application.pdf image-only (no text layer)
    d = sub_dir("SUB-229")
    write_text(os.path.join(d, "email.md"), email_md(
        "Harborview Print & Copy - Corpus Christi, eff 3/1/27",
        """Harborview Print & Copy is a print shop in Corpus, digital printing, binding,
banners, small walk in. They scan the app to a pdf and send it that way so it comes in as a
picture, sorry. Schedule attached as csv. Loss run is their no known loss letter. Need BPP
and GL. Eff 3/1/27.

Denise Krueger"""))
    fields = {
        "Named insured": "Harborview Print & Copy LLC",
        "Mailing address": "same as premises",
        "Premises address": "4101 S Port Ave, Corpus Christi, TX 78415",
        "Effective date": "2027-03-01",
        "Years in business": "11",
        "Entity type": "LLC",
        "Line of business": "BOP - retail / printing",
        "Operations": ("Digital print and copy shop: copying, digital printing, binding and "
                       "banners. Small walk-in retail. No offset press, no solvents, no "
                       "vehicle wraps."),
        "Number of employees": "5",
        "Annual sales": "$486,000",
        "Building TIV": "$0 (tenant)",
        "Business personal property": "$155,000",
        "Square footage": "2,900",
        "Construction": "Masonry",
        "Year built": "1992",
        "Stories": "1",
        "Sprinklers": "No",
        "Cooking operations": "None",
        "Expiring carrier": "Carrier D, expiring 2027-02-28",
        "Pending or open claims": "None known",
        "Bankruptcy or cancellation in last 5 years": "No",
    }
    write_image_pdf(os.path.join(d, "application.pdf"),
                    scan_jpeg_bytes(app_plain_lines("SUB-229", fields),
                                    FONT_SANS, size=23, wrap=62))
    schedule_csv(os.path.join(d, "schedule.csv"), {
        "source": "FICTIONAL", "loc": 1, "address": "4101 S Port Ave",
        "city": "Corpus Christi", "zip": "78415", "bldg_tiv": 0,
        "construction": "Masonry", "year_built": 1992, "sq_ft": 2900,
        "sprinklers": "No", "cooking": "none",
    })
    write_text(os.path.join(d, "loss-runs.md"), """No known loss letter

To whom it may concern,

Harborview Print & Copy LLC has had no known losses in the last five years. The owner asks
that this letter be accepted in place of carrier loss runs.

FICTIONAL. Not a loss run.
""")
    sections.append("SUB-229")

    # ---------------------------------------------------------- SUB-230 : C1
    # criterion 1: application_scan.jpg (scanned JPG application)
    d = sub_dir("SUB-230")
    write_text(os.path.join(d, "email.md"), email_md(
        "Falcon Ridge Veterinary Clinic - El Paso",
        """Falcon Ridge is a small animal vet clinic in El Paso, they bought the building last
year, one story masonry, no boarding kennel, no large animals. The app is a scan, and they
have a non-carrier loss summary the office manager put together (its a pdf). Eff 1/1/27.

Sonia Aldrete"""))
    fields = {
        "Named insured": "Falcon Ridge Veterinary Clinic PLLC",
        "Mailing address": "same as premises",
        "Premises address": "10760 Kenworthy St, El Paso, TX 79924",
        "Effective date": "2027-01-01",
        "Years in business": "9",
        "Entity type": "PLLC",
        "Line of business": "Commercial property, general liability - office",
        "Operations": ("Small animal veterinary clinic: exams, surgery suite, x-ray, in-house "
                       "lab. Outpatient only, no overnight boarding, no large animals."),
        "Number of employees": "7",
        "Annual sales": "$890,000",
        "Building TIV": "$980,000",
        "Business personal property": "$210,000",
        "Square footage": "4,600",
        "Construction": "Masonry",
        "Year built": "2007",
        "Stories": "1",
        "Sprinklers": "Yes",
        "Cooking operations": "None",
        "Expiring carrier": "Carrier E, expiring 2026-12-31",
        "Pending or open claims": "One dog bite to staff 2025, closed, $2,800 medical",
        "Bankruptcy or cancellation in last 5 years": "No",
    }
    write_scan(os.path.join(d, "application_scan.jpg"),
               app_plain_lines("SUB-230", fields), FONT_SANS, size=23, wrap=62)
    write_typed_pdf(os.path.join(d, "loss-summary.pdf"), [
        FICT_PLAIN,
        "Loss summary - prepared by the office manager, as of 2026-08-22",
        "(not a carrier loss run)",
        "",
        "Named insured: Falcon Ridge Veterinary Clinic PLLC",
        "",
        "| Year | Carrier | Policy | Loss | Date | Paid | Status |",
        "| 2023 | Carrier E | CE-55810 | none | - | $0 | closed |",
        "| 2024 | Carrier E | CE-55810 | none | - | $0 | closed |",
        "| 2025 | Carrier E | CE-60123 | dog bite to staff | 2025-04-17 | $2,800 | closed |",
        "| 2026 | Carrier E | CE-60123 | none to date | - | $0 | open term |",
    ])
    sections.append("SUB-230")

    # ---------------------------------------------------------- SUB-231 : C1+C2
    # criterion 1: application_scan.jpg (scanned JPG application)
    # criterion 2: "Building 2" / "Bldg 2" (two buildings) in the scanned application
    d = sub_dir("SUB-231")
    write_text(os.path.join(d, "email.md"), email_md(
        "Pecos Feed & Grain - Fort Stockton",
        """Pecos Feed & Grain sells bagged feed and seed, some farm hardware, they now have the
main store and a second warehouse building a block over. No bulk fertilizer storage, no
chemical blending, no grain bins on site. They mail the app in and the office scans it, so its
a jpg. The Carrier D run has a valued date on it. Schedule xlsx attached. Eff 2/15/27.

Walt Bingham"""))
    fields = {
        "Named insured": "Pecos Feed & Grain LLC",
        "Mailing address": "PO Box 771, Fort Stockton, TX 79735",
        "Premises address": ("Building 1 (store): 1802 W Dickinson Blvd, Fort Stockton, TX "
                             "79735; Bldg 2 (warehouse): 1908 W Dickinson Blvd, Fort "
                             "Stockton, TX 79735"),
        "Effective date": "2027-02-15",
        "Years in business": "22",
        "Entity type": "LLC",
        "Line of business": "BOP - retail (2 buildings)",
        "Operations": ("Retail feed and farm supply store plus a separate warehouse building "
                       "for overstock. Bagged feed, seed, small farm hardware and fencing "
                       "supplies. No bulk fertilizer, no ag chemicals, no grain storage."),
        "Number of employees": "6",
        "Annual sales": "$1,320,000",
        "Building TIV": "$940,000 (store 540,000 + warehouse 400,000)",
        "Business personal property": "$180,000",
        "Square footage": "12,600 total (8,200 + 4,400)",
        "Construction": "Metal",
        "Year built": "1990 / 2004",
        "Stories": "1",
        "Sprinklers": "No",
        "Cooking operations": "None",
        "Expiring carrier": "Carrier D, expiring 2027-02-14",
        "Pending or open claims": "None known",
        "Bankruptcy or cancellation in last 5 years": "No",
    }
    write_scan(os.path.join(d, "application_scan.jpg"),
               app_plain_lines("SUB-231", fields), FONT_SANS, size=23, wrap=62)
    schedule_xlsx(os.path.join(d, "schedule.xlsx"), [
        {"source": "FICTIONAL", "loc": 1, "address": "1802 W Dickinson Blvd",
         "city": "Fort Stockton", "zip": "79735", "bldg_tiv": 540000,
         "construction": "Metal", "year_built": 1990, "sq_ft": 8200,
         "sprinklers": "No", "cooking": "none"},
        {"source": "FICTIONAL", "loc": 2, "address": "1908 W Dickinson Blvd",
         "city": "Fort Stockton", "zip": "79735", "bldg_tiv": 400000,
         "construction": "Metal", "year_built": 2004, "sq_ft": 4400,
         "sprinklers": "No", "cooking": "none"},
    ])
    write_text(os.path.join(d, "loss-runs.md"), "\n".join(lr_carrier_d(
        "Pecos Feed & Grain LLC",
        ["2023-02-15 to 2024-02-15", "2024-02-15 to 2025-02-15",
         "2025-02-15 to 2026-02-15"],
        "2026-09-28", [])) + "\n")
    sections.append("SUB-231")

    # ====================================================== C2 multi-location (4)

    # ---------------------------------------------------------- SUB-232 : C2
    # criterion 2: "Location No. 2" in application
    d = sub_dir("SUB-232")
    write_text(os.path.join(d, "email.md"), email_md(
        "Two Moon Tex-Mex - Lubbock, second store opening",
        """Two Moon Tex-Mex is opening a second store in Lubbock, the first one is going fine
so the owner is expanding. They want both under one BOP if that works. App lists the two
locations, schedule attached. Loss run from Carrier E. Second one is in a strip center. Eff
4/1/27.

Hank Morelos"""))
    fields = {
        "Named insured": "Two Moon Tex-Mex LLC",
        "Mailing address": "PO Box 6402, Lubbock, TX 79493",
        "Premises address": ("Location 1: 2620 34th St, Lubbock, TX 79410; "
                             "Location No. 2: 5109 82nd St, Lubbock, TX 79424"),
        "Effective date": "2027-04-01",
        "Years in business": "12",
        "Entity type": "LLC",
        "Line of business": "BOP - restaurant (2 locations)",
        "Operations": ("Two full-service Tex-Mex restaurants. Each has a Type I hood and "
                       "ansul over the grill and fryer, beer and wine only, no hard liquor. "
                       "Seating 110 and 90."),
        "Number of employees": "31 (17 + 14)",
        "Annual sales": "$2,240,000 (both stores)",
        "Building TIV": "$0 (both tenant)",
        "Business personal property": "$260,000 (combined)",
        "Square footage": "4,800 total (2,700 + 2,100)",
        "Construction": "Masonry",
        "Year built": "1994 / 2006",
        "Stories": "1",
        "Sprinklers": "No",
        "Cooking operations": "Grill and fryer, Type I hood and ansul (both locations)",
        "Expiring carrier": "Carrier E, expiring 2027-03-31",
        "Pending or open claims": "One slip and fall 2025, closed, $4,100 paid",
        "Bankruptcy or cancellation in last 5 years": "No",
    }
    write_text(os.path.join(d, "application.md"), app_md("SUB-232", fields))
    schedule_csv(os.path.join(d, "schedule.csv"), [
        {"source": "FICTIONAL", "loc": 1, "address": "2620 34th St",
         "city": "Lubbock", "zip": "79410", "bldg_tiv": 0,
         "construction": "Masonry", "year_built": 1994, "sq_ft": 2700,
         "sprinklers": "No", "cooking": "grill & fryer"},
        {"source": "FICTIONAL", "loc": 2, "address": "5109 82nd St",
         "city": "Lubbock", "zip": "79424", "bldg_tiv": 0,
         "construction": "Masonry", "year_built": 2006, "sq_ft": 2100,
         "sprinklers": "No", "cooking": "grill & fryer"},
    ])
    write_text(os.path.join(d, "loss-runs.md"), "\n".join(lr_carrier_e(
        "Two Moon Tex-Mex LLC",
        ["2023-04-01 to 2024-04-01", "2024-04-01 to 2025-04-01",
         "2025-04-01 to 2026-04-01"],
        "2026-07-29",
        [["2025-06-11", "customer slip and fall (store 1)", "$4,100", "$0"]])) + "\n")
    sections.append("SUB-232")

    # ---------------------------------------------------------- SUB-233 : C2
    # criterion 2: "Loc #2" in application
    d = sub_dir("SUB-233")
    write_text(os.path.join(d, "email.md"), email_md(
        "Amarillo Auto Salon - Amarillo",
        """Amarillo Auto Salon runs an auto detailing and tint shop, second location just
opened across town for the west side customers. Need property and GL on both. The app shows
the two stops. Carrier D loss run attached, no val date on it I think. Eff 1/1/27.

Nita Bobbitt"""))
    fields = {
        "Named insured": "Amarillo Auto Salon LLC",
        "Mailing address": "same as Loc 1",
        "Premises address": ("Loc 1: 3412 S Georgia St, Amarillo, TX 79109; "
                             "Loc #2: 6901 Bell St, Amarillo, TX 79106"),
        "Effective date": "2027-01-01",
        "Years in business": "8",
        "Entity type": "LLC",
        "Line of business": "BOP - retail / service",
        "Operations": ("Auto detailing, window tint and ceramic coating. Two bays per "
                       "location, no paint spray booth, no body work, no mechanical repair. "
                       "Vehicles stored indoors overnight."),
        "Number of employees": "9",
        "Annual sales": "$740,000",
        "Building TIV": "$0 (both tenant)",
        "Business personal property": "$95,000",
        "Square footage": "5,200 total (2,800 + 2,400)",
        "Construction": "Masonry",
        "Year built": "2001 / 2015",
        "Stories": "1",
        "Sprinklers": "No",
        "Cooking operations": "None",
        "Expiring carrier": "Carrier D, expiring 2026-12-31",
        "Pending or open claims": "None known",
        "Bankruptcy or cancellation in last 5 years": "No",
    }
    write_text(os.path.join(d, "application.md"), app_md("SUB-233", fields))
    write_text(os.path.join(d, "loss-runs.md"), "\n".join(lr_carrier_d(
        "Amarillo Auto Salon LLC",
        ["2023-01-01 to 2024-01-01", "2024-01-01 to 2025-01-01",
         "2025-01-01 to 2026-01-01"],
        None, [])) + "\n")
    sections.append("SUB-233")

    # ====================================================== C3 non-English (4)

    # ---------------------------------------------------------- SUB-234 : C3
    # criterion 3: Spanish single-location application (typed PDF)
    d = sub_dir("SUB-234")
    write_text(os.path.join(d, "email.md"), email_md(
        "Panaderia La Estrella - San Antonio bakery",
        """Panaderia La Estrella is a Mexican bakery in San Antonio, they bake pan dulce and
cakes, ovens are gas deck ovens, small walk in counter, no frying, one location only. The
owner sent the app in Spanish as a pdf, I couldnt get him to redo it. Carrier D loss run
attached. Eff 1/15/27.

Lupita Carrasco"""))
    campos = [
        ("Nombre del asegurado", "Panaderia La Estrella LLC"),
        ("Direccion postal", "misma que la propiedad"),
        ("Direccion de la propiedad", "1330 Guadalupe St, San Antonio, TX 78207"),
        ("Fecha de vigencia", "2027-01-15"),
        ("Anos en el negocio", "20"),
        ("Tipo de entidad", "LLC"),
        ("Linea de negocio", "BOP - panaderia"),
        ("Operaciones", ("Panaderia mexicana: pan dulce, bolillos y pasteles. Hornos de gas tipo "
                         "deck, sin freidora, sin cocina de restaurante. Venta al mostrador.")),
        ("Numero de empleados", "7"),
        ("Ventas anuales", "$520,000"),
        ("TIV del edificio", "$0 (inquilino)"),
        ("Propiedad personal", "$88,000"),
        ("Pies cuadrados", "2,100"),
        ("Construccion", "Mamposteria"),
        ("Ano de construccion", "1975"),
        ("Pisos", "1"),
        ("Rociadores", "No"),
        ("Operaciones de cocina", "Hornos de gas tipo deck, sin freidora"),
        ("Aseguradora actual", "Carrier D, vence 2027-01-14"),
        ("Reclamos pendientes", "Ninguno conocido"),
        ("Quiebra o cancelacion (5 anos)", "No"),
    ]
    write_typed_pdf(os.path.join(d, "application.pdf"),
                    app_spanish_lines("SUB-234", campos))
    write_text(os.path.join(d, "loss-runs.md"), "\n".join(lr_carrier_d(
        "Panaderia La Estrella LLC",
        ["2023-01-15 to 2024-01-15", "2024-01-15 to 2025-01-15",
         "2025-01-15 to 2026-01-15"],
        "2026-06-05", [])) + "\n")
    sections.append("SUB-234")

    # ---------------------------------------------------------- SUB-235 : C3
    # criterion 3: Spanish single-location application letter (md)
    d = sub_dir("SUB-235")
    write_text(os.path.join(d, "email.md"), email_md(
        "Jessica's Beauty Salon - Laredo (letter in Spanish)",
        """Jessica's Beauty Salon is a hair and nail salon in Laredo, one location, four
styling chairs, two nail stations, no tanning beds and no massage. The owner wrote the
application as a letter in Spanish, Im attaching it. No carrier runs, she has a no-known-loss
letter also in Spanish. Eff 3/1/27.

Odalys Fuentes"""))
    write_text(os.path.join(d, "application.md"), """**FICTIONAL.** All businesses, people, addresses and policy numbers are made up.

Carta de solicitud de seguro

Estimado agente:

Jessica's Beauty Salon solicita cotizacion de responsabilidad general y propiedad para
una sola ubicacion:

  Direccion: 2409 Guadalupe St, Laredo, TX 78043

Operacion: salon de belleza, corte y tinte de cabello, unas acrilicas. Cuatro sillas de
estilista y dos estaciones de unas. Sin camas de bronceado, sin masajes, sin venta de
alcohol. Un solo local, inquilino.

Empleados: 5.
Ventas anuales: aproximadamente $212,000.
Sin reclamos conocidos.

Atentamente,
Jessica Amador, Jessica's Beauty Salon
""")
    write_text(os.path.join(d, "loss-runs.md"), """**FICTIONAL.** All businesses, people, addresses and policy numbers are made up.

Carta de perdidas desconocidas

A quien corresponda:

Jessica's Beauty Salon abrio en 2017 y no tiene perdidas conocidas. La propietaria
solicita que esta carta se acepte en lugar de los reportes de siniestros de la
aseguradora.

FICTIONAL. No es un loss run.
""")
    sections.append("SUB-235")

    # ====================================================== C3 + C2 (3 files)

    # ---------------------------------------------------------- SUB-236 : C3+C2
    # criterion 3: Spanish application; criterion 2: two locations listed in it
    d = sub_dir("SUB-236")
    write_text(os.path.join(d, "email.md"), email_md(
        "Taqueria El Faro - two locations, Dallas",
        """Taqueria El Faro is a taqueria with two locations in Dallas. The owner filled the
application out in Spanish and we typed it up as a PDF for you. Both locations are listed on
the form (Sucursal 1 and Sucursal 2). They want BOP on both if you can. Loss run from Carrier
E. Eff 12/1/26.

Gloria Pena"""))
    campos = [
        ("Nombre del asegurado", "Taqueria El Faro LLC"),
        ("Direccion postal", "misma que Sucursal 1"),
        ("Direccion de la propiedad", ("Sucursal 1: 4809 Maple Ave, Dallas, TX 75219; "
                                       "Sucursal 2: 1123 Singleton Blvd, Dallas, TX 75212")),
        ("Numero de sucursales", "2 (vea el detalle por sucursal abajo)"),
        ("Fecha de vigencia", "2026-12-01"),
        ("Anos en el negocio", "14"),
        ("Tipo de entidad", "LLC"),
        ("Linea de negocio", "BOP - restaurante (2 sucursales)"),
        ("Operaciones", ("Taqueria de servicio completo. Plancha y freidora, campana Tipo I "
                         "con ansul. Cerveza solamente, sin licor. Dos sucursales.")),
        ("Numero de empleados", "19 (10 + 9)"),
        ("Ventas anuales", "$1,540,000 (las dos)"),
        ("TIV del edificio", "$0 (inquilino en las dos)"),
        ("Propiedad personal", "$150,000"),
        ("Pies cuadrados", "3,400 total"),
        ("Construccion", "Mamposteria"),
        ("Ano de construccion", "1988 / 1999"),
        ("Pisos", "1"),
        ("Rociadores", "No"),
        ("Operaciones de cocina", "Plancha y freidora, campana Tipo I con ansul"),
        ("Aseguradora actual", "Carrier E, vence 2026-11-30"),
        ("Reclamos pendientes", "Ninguno conocido"),
        ("Quiebra o cancelacion (5 anos)", "No"),
    ]
    solicitud = app_spanish_lines("SUB-236", campos)
    solicitud += [
        "",
        "Detalle por sucursal",
        "",
        "Sucursal 1",
        "Direccion Sucursal 1: 4809 Maple Ave",
        "Ciudad Sucursal 1: Dallas",
        "Codigo postal Sucursal 1: 75219",
        "Pies cuadrados Sucursal 1: 1,900",
        "Construccion Sucursal 1: Mamposteria",
        "Ano de construccion Sucursal 1: 1988",
        "Rociadores Sucursal 1: No",
        "Operaciones de cocina Sucursal 1: Plancha y freidora, campana Tipo I con ansul",
        "",
        "Sucursal 2",
        "Direccion Sucursal 2: 1123 Singleton Blvd",
        "Ciudad Sucursal 2: Dallas",
        "Codigo postal Sucursal 2: 75212",
        "Pies cuadrados Sucursal 2: 1,500",
        "Construccion Sucursal 2: Mamposteria",
        "Ano de construccion Sucursal 2: 1999",
        "Rociadores Sucursal 2: No",
        "Operaciones de cocina Sucursal 2: Plancha y freidora, campana Tipo I con ansul",
    ]
    write_typed_pdf(os.path.join(d, "application.pdf"), solicitud)
    schedule_csv(os.path.join(d, "schedule.csv"), [
        {"source": "FICTIONAL", "loc": 1, "address": "4809 Maple Ave",
         "city": "Dallas", "zip": "75219", "bldg_tiv": 0,
         "construction": "Masonry", "year_built": 1988, "sq_ft": 1900,
         "sprinklers": "No", "cooking": "plancha y freidora"},
        {"source": "FICTIONAL", "loc": 2, "address": "1123 Singleton Blvd",
         "city": "Dallas", "zip": "75212", "bldg_tiv": 0,
         "construction": "Masonry", "year_built": 1999, "sq_ft": 1500,
         "sprinklers": "No", "cooking": "plancha y freidora"},
    ])
    write_text(os.path.join(d, "loss-runs.md"), "\n".join(lr_carrier_e(
        "Taqueria El Faro LLC",
        ["2023-12-01 to 2024-12-01", "2024-12-01 to 2025-12-01",
         "2025-12-01 to 2026-12-01"],
        "2026-08-11",
        [["2025-01-24", "water damage (sucursal 1)", "$3,900", "$0"]])) + "\n")
    sections.append("SUB-236")

    # ---------------------------------------------------------- SUB-237 : C3+C2
    # criterion 3: Spanish application letter; criterion 2: second store in the email
    d = sub_dir("SUB-237")
    write_text(os.path.join(d, "email.md"), email_md(
        "Casa Del Sol Furniture - El Paso (2nd store)",
        """Casa Del Sol is a furniture store in El Paso, we just added a second showroom on
the east side so please quote both stores under one policy. The owner writes the app in
Spanish, letter attached. Carrier E loss run attached, its typed. Eff 2/1/27.

Victor Mancilla"""))
    write_text(os.path.join(d, "application.md"), """**FICTIONAL.** All businesses, people, addresses and policy numbers are made up.

Carta de solicitud de seguro

Estimado agente:

Casa Del Sol Furniture LLC solicita cotizacion de propiedad y responsabilidad general
para dos salas de exhibicion:

  Tienda 1: 7820 Alameda Ave, El Paso, TX 79915
  Tienda 2: 11405 Rojas Dr, El Paso, TX 79936

Operacion: venta de muebles al menudeo, entrega con camion propio, sin tapiceria ni
manufactura en el local. Sin bodega de liquidos inflamables.

Aseguradora actual: Carrier E, vence 2027-01-31.
Ventas anuales: aproximadamente $2,010,000 entre las dos tiendas.
Empleados: 16.

Atentamente,
Tomas Villareal, Casa Del Sol Furniture LLC
""")
    schedule_csv(os.path.join(d, "schedule.csv"), [
        {"source": "FICTIONAL", "loc": 1, "address": "7820 Alameda Ave",
         "city": "El Paso", "zip": "79915", "bldg_tiv": 0,
         "construction": "Masonry", "year_built": 1990, "sq_ft": 9200,
         "sprinklers": "Yes", "cooking": "none"},
        {"source": "FICTIONAL", "loc": 2, "address": "11405 Rojas Dr",
         "city": "El Paso", "zip": "79936", "bldg_tiv": 0,
         "construction": "Masonry", "year_built": 2005, "sq_ft": 7800,
         "sprinklers": "Yes", "cooking": "none"},
    ])
    write_text(os.path.join(d, "loss-runs.md"), "\n".join(lr_carrier_e(
        "Casa Del Sol Furniture LLC",
        ["2023-02-01 to 2024-02-01", "2024-02-01 to 2025-02-01",
         "2025-02-01 to 2026-02-01"],
        "2026-07-18",
        [["2024-09-30", "delivery truck damage (tienda 1)", "$5,600", "$0"]])) + "\n")
    sections.append("SUB-237")

    print("Wrote %d submissions: %s .. %s" %
          (len(sections), sections[0], sections[-1]))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: %s <worktree_root>" % sys.argv[0])
    build(os.path.abspath(sys.argv[1]))
