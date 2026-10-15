#!/usr/bin/env python3
"""Builds SUB-107..SUB-126 (all names, addresses and numbers FICTIONAL).

Run with the repo venv: <repo>/.venv/bin/python build_SUB-107-126.py
Writes only under simulation/inbox/SUB-107..SUB-126. No model calls.
"""
import csv
import io
import os
import random
import shutil
import sys
import textwrap

import openpyxl
from PIL import Image, ImageDraw, ImageFilter, ImageFont

INBOX = "/Users/disastershubz/INSURANCE FLOW AI/-insureflow-ai-1/simulation/inbox"
PAGE_W, PAGE_H = 1275, 1650  # letter at 150 dpi

_REG = ["/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf"]
_BOLD = ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/Library/Fonts/Arial Bold.ttf"]


def _font(paths, size):
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size=size)


F_REG = _font(_REG, 24)
F_BOLD = _font(_BOLD, 28)

# ---------------------------------------------------------------- typed PDF


def typed_pdf(path, pages):
    """Minimal PDF with a real Helvetica text layer. pages: list of [(text, bold)]."""
    n = len(pages)
    objs = {1: b"<< /Type /Catalog /Pages 2 0 R >>"}
    kids = " ".join(f"{5 + 2 * i} 0 R" for i in range(n))
    objs[2] = f"<< /Type /Pages /Kids [{kids}] /Count {n} >>".encode()
    objs[3] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    objs[4] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>"
    for i, lines in enumerate(pages):
        ops = []
        y = 760
        for text, bold in lines:
            raw = text.encode("cp1252", "replace")
            raw = raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")
            font = b"/F2 11" if bold else b"/F1 10"
            ops.append(b"BT " + font + b" Tf 50 " + str(y).encode() + b" Td (" + raw + b") Tj ET")
            y -= 16 if bold else 14
        stream = b"\n".join(ops)
        objs[6 + 2 * i] = b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"
        objs[5 + 2 * i] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {6 + 2 * i} 0 R >>"
        ).encode()
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = {}
    for k in sorted(objs):
        offsets[k] = len(out)
        out += b"%d 0 obj\n" % k + objs[k] + b"\nendobj\n"
    xref = len(out)
    nobj = max(objs) + 1
    out += b"xref\n0 %d\n0000000000 65535 f \n" % nobj
    for k in range(1, nobj):
        out += b"%010d 00000 n \n" % offsets[k]
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (nobj, xref)
    with open(path, "wb") as fh:
        fh.write(out)


def paginate_typed(lines, per_page=46):
    flat = []
    for text, bold in lines:
        if bold or len(text) <= 92:
            flat.append((text, bold))
        else:
            for part in textwrap.wrap(text, 92, subsequent_indent="   "):
                flat.append((part, False))
    return [flat[i:i + per_page] for i in range(0, len(flat), per_page)] or [[]]


# ---------------------------------------------------------------- scans


def _wrap_img_lines(lines, width=80):
    out = []
    for text, bold in lines:
        if bold or len(text) <= width:
            out.append((text, bold))
        else:
            for part in textwrap.wrap(text, width, subsequent_indent="   "):
                out.append((part, False))
    return out


def scan_pages(lines, paper, ink, rotate=0, gray=False, seed=1, per_page=36):
    """Renders lines as scanned page images (no text layer)."""
    rnd = random.Random(seed)
    flat = _wrap_img_lines(lines)
    chunks = [flat[i:i + per_page] for i in range(0, len(flat), per_page)] or [[]]
    imgs = []
    for chunk in chunks:
        img = Image.new("RGB", (PAGE_W, PAGE_H), paper)
        d = ImageDraw.Draw(img)
        y = 120
        for text, bold in chunk:
            d.text((110, y), text, fill=ink, font=F_BOLD if bold else F_REG)
            y += 50 if bold else 40
        img = img.filter(ImageFilter.GaussianBlur(0.5))
        noise = Image.effect_noise((PAGE_W, PAGE_H), 14).convert("RGB")
        img = Image.blend(img, noise, 0.035)
        if rotate:
            img = img.rotate(rotate, expand=True, fillcolor=(255, 255, 255))
        if gray:
            img = img.convert("L")
        imgs.append(img)
    rnd.random()
    return imgs


def save_image_pdf(path, imgs):
    first, rest = imgs[0], imgs[1:]
    first.save(path, "PDF", resolution=150.0, save_all=bool(rest), append_images=rest)


# ---------------------------------------------------------------- other files

SCHED_HEADER = ["source", "loc", "address", "city", "zip", "bldg_tiv", "construction",
                "year_built", "sq_ft", "sprinklers", "cooking"]


def sched_rows(locs):
    return [["FICTIONAL", l["loc"], l["address"], l["city"], l["zip"], l["bldg"], l["const"],
             l["year"], l["sqft"], l["spr"], l["cook"]] for l in locs]


def write_csv(path, locs):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(SCHED_HEADER)
    w.writerows(sched_rows(locs))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(buf.getvalue())


def write_xlsx(path, locs):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Schedule"
    ws.append(["FICTIONAL - location schedule (xlsx)"])
    ws.append([])
    ws.append(SCHED_HEADER)
    for r in sched_rows(locs):
        ws.append(r)
    wb.save(path)


def write_text(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text.strip() + "\n")


LBL = {
    "en": dict(name="Named insured", dba="DBA", prem="Premises address", mail="Mailing address",
               eff="Effective date", ops="Operations", sales="Annual sales / revenue",
               emp="Employees", bldg="Building TIV", bpp="Contents / BPP TIV",
               bi="Business income", const="Construction", year="Year built",
               sqft="Square feet", spr="Sprinklers", cook="Cooking / hood / suppression",
               bar="Bar / liquor", prior="Prior carrier", losses="Losses last 5 years"),
    "es": dict(name="Asegurado", dba="Nombre comercial", prem="Direccion del local",
               mail="Direccion postal", eff="Fecha efectiva", ops="Operaciones",
               sales="Ventas anuales", emp="Empleados", bldg="TIV edificio",
               bpp="TIV contenido", bi="Interrupcion de negocio", const="Construccion",
               year="Ano de construccion", sqft="Pies cuadrados", spr="Rociadores",
               cook="Cocina / campana / supresion", bar="Bar / licor",
               prior="Aseguradora anterior", losses="Perdidas ultimos 5 anos"),
}


def app_lines(s):
    lang = s["lang"]
    title = ("FICTICIO - Solicitud estilo ACORD 125 / 140 (texto)" if lang == "es"
             else "FICTIONAL - ACORD 125 / 140 style application (text)")
    out = [(title, True), ("Documento sintetico. Todos los datos son ficticios." if lang == "es"
                           else "Synthetic document. All names, addresses and numbers are fictional.", False)]
    a = s["app"]
    keys = ["name", "dba", "prem", "mail", "eff", "ops", "sales", "emp", "bldg", "bpp", "bi",
            "const", "year", "sqft", "spr", "cook", "bar", "prior", "losses"]
    for k in keys:
        if k in a:
            out.append((f"{LBL[lang][k]}: {a[k]}", False))
    return out


def lr_text(s):
    lang = s.get("lang", "en")
    head = "# Carta de pérdidas" if lang == "es" and s["lr_kind"] == "letter" else (
        "# Loss runs (typed)" if s["lr_kind"] == "typed" else "# No known loss letter")
    lines = [head, "_FICTIONAL / SYNTHETIC test data. No real applicant, person or business._",
             f"Named insured: {s['app']['name']}"]
    if s.get("vt"):
        lines.append(f"Valued through: {s['vt']}")
    lines += [("- " + x) for x in s["lr"]]
    return "\n".join(lines)


def email_text(s):
    return f"**FICTIONAL.**\n\n{s['email']}"


# ---------------------------------------------------------------- the 20 submissions

SUBS = []

SUBS.append(dict(
    id="SUB-107", lang="en", app_fmt="typed", sched="csv", lr_kind="typed", vt="2026-09-30",
    app=dict(name="Juniper Ridge Bookkeeping LLC", dba="Juniper Ridge Books",
             prem="7710 Shoal Creek Ct, Suite 210, Austin TX 78757", mail="Same as premises",
             eff="2027-03-01", ops="Bookkeeping and payroll services for small businesses, no client premises work",
             sales="$1,850,000", emp="14", bldg="$240,000 (tenant improvements)", bpp="$185,000",
             bi="$400,000 (12 months)", const="Masonry non-combustible", year="2004", sqft="6,200",
             spr="Yes, full", cook="N/A", bar="N/A", prior="Northline Mutual (fictional)",
             losses="None reported"),
    locs=[dict(loc=1, address="7710 Shoal Creek Ct Ste 210", city="Austin", zip="78757", bldg=240000,
               const="Masonry non-combustible", year=2004, sqft=6200, spr="Yes", cook="none")],
    lr=["Northline Mutual (fictional), policy 2023-03-01 to 2024-03-01: 0 claims, $0 paid",
        "Policy 2024-03-01 to 2025-03-01: 0 claims, $0 paid",
        "Policy 2025-03-01 to 2026-03-01: 0 claims, $0 paid",
        "Policy 2026-03-01 to 2026-09-30: 0 claims, $0 paid. Open reserve $0."],
    email=("Subject: Juniper Ridge - new business, eff 3/1/27\n\nHi team, Juniper Ridge Bookkeeping is "
           "moving to us from Northline. Office on Shoal Creek, 14 staff, about 1.85M in fees last year. "
           "Build-out is ours (tenant improvements). Loss runs attached, clean as far as I know. "
           "Let me know if you need the payroll vendor list.\n\nThanks, Dana Whitfield (producer)")
))

SUBS.append(dict(
    id="SUB-108", lang="en", app_fmt="gray", sched="xlsx", lr_kind="letter", vt="2026-08-31",
    app=dict(name="Pecan Street Candle & Gift Co LLC", dba="Pecan Street Gifts",
             prem="1205 Old Settlers Blvd, Round Rock TX 78664", mail="Same as premises",
             eff="2027-04-01", ops="Retail sale of candles, gifts and cards. No food service.",
             sales="$940,000", emp="6", bldg="$1,600,000", bpp="$500,000", bi="$250,000",
             const="Joisted masonry", year="1994", sqft="5,400", spr="No", cook="N/A", bar="N/A",
             prior="Harbor Point Insurance (fictional)", losses="None"),
    locs=[dict(loc=1, address="1205 Old Settlers Blvd", city="Round Rock", zip="78664", bldg=1600000,
               const="Joisted masonry", year=1994, sqft=5400, spr="No", cook="none")],
    lr=["No known loss letter from prior agent, dated 2026-08-20.",
        "No claims in the last five years to our knowledge."],
    email=("Subject: Pecan Street Candle - new account\n\nHey, new one for us. Gift shop in Round Rock, "
           "owners own the building. Roof was done in 2019. Sales were about 940k last year. "
           "Its an older building so sprinklers arent in it. Paper app attached as scan.\n\nTom Okafor, agency desk")
))

SUBS.append(dict(
    id="SUB-109", lang="en", app_fmt="color", sched="csv", lr_kind="none", vt=None,
    app=dict(name="Llano Dry Goods Wholesale LLC", dba="Llano Foods Wholesale",
             prem="4420 Bellfort Industrial Row, Houston TX 77051", mail="PO Box 9102, Houston TX 77213",
             eff="2027-04-01",
             ops="Wholesale distributor of paper goods, dried beans, rice and cleaning supplies to grocers. Electric forklifts, no retail counter.",
             sales="$3,600,000", emp="22", bldg="$3,150,000", bpp="$1,250,000", bi="$600,000",
             const="Metal frame, insulated panel", year="2011", sqft="24,000", spr="Yes", cook="N/A",
             bar="N/A", prior="Gulf Shore Mutual (fictional)", losses="See loss runs (not yet received)"),
    locs=[dict(loc=1, address="4420 Bellfort Industrial Row", city="Houston", zip="77051", bldg=3150000,
               const="Metal frame, insulated panel", year=2011, sqft=24000, spr="Yes", cook="none")],
    lr=[],
    email=("Subject: Llano Dry Goods renewal app\n\nAttached the app. Warehouse is 24k sq ft on Bellfort. "
           "Sales were 3.1M last year, I put a bit more on the app to be safe. Loss runs are with the old "
           "agent, they promised them Monday. TIV all in, roughly 4.4M.\n\nRuth Anson")
))

SUBS.append(dict(
    id="SUB-110", lang="en", app_fmt="typed", sched="csv", lr_kind="typed", vt="2026-09-30",
    app=dict(name="Casa Mesquite Cantina LLC", dba="Casa Mesquite",
             prem="2210 Mesquite Bend Rd, San Antonio TX 78201", mail="Same as premises",
             eff="2027-01-15", ops="Full-service Tex-Mex restaurant, dine-in and takeout. Beer and wine only, no liquor license.",
             sales="$1,250,000", emp="26", bldg="$520,000", bpp="$300,000", bi="$180,000",
             const="Joisted masonry", year="1979", sqft="3,900", spr="Yes, full",
             cook="Fryers x2, flat-top, charbroiler. Type I hood, Ansul R-102 serviced 2026-07-14.",
             bar="No (beer and wine, no bar service)", prior="Lakeshore Specialty (fictional)",
             losses="None"),
    locs=[dict(loc=1, address="2210 Mesquite Bend Rd", city="San Antonio", zip="78201", bldg=520000,
               const="Joisted masonry", year=1979, sqft=3900, spr="Yes", cook="Type I hood, Ansul")],
    lr=["Lakeshore Specialty (fictional), 2023-24: 0 claims",
        "2024-25: 0 claims", "2025-26: 0 claims", "Open reserve: $0"],
    email=("Subject: Casa Mesquite - restaurant renewal\n\nHi, Casa Mesquite Cantina renewal, eff 1/15/27. "
           "Same kitchen as always. Hood was cleaned and Ansul serviced in July. No claims ever that I know of. "
           "Sales a little under 1.3M.\n\nMarco L. (producer)")
))

SUBS.append(dict(
    id="SUB-111", lang="en", app_fmt="color", sched="csv", lr_kind="typed", vt="2026-09-30",
    app=dict(name="Lone Oak Smokehouse & Bar LLC", dba="Lone Oak BBQ",
             prem="5102 Lakeview Crossing, Dallas TX 75206", mail="Same as premises",
             eff="2027-02-01",
             ops="BBQ restaurant with full bar (beer, wine, spirits). Live music Fri and Sat until 1am.",
             sales="$2,400,000", emp="38", bldg="$780,000", bpp="$420,000", bi="$300,000",
             const="Masonry and steel", year="1968", sqft="4,800", spr="No",
             cook="Wood-fired smoker pits x4, fryers. Type I hood, Ansul serviced 2026-05-02.",
             bar="Full bar, last call 1am", prior="Lakeshore Specialty (fictional)",
             losses="2 claims, see loss runs"),
    locs=[dict(loc=1, address="5102 Lakeview Crossing", city="Dallas", zip="75206", bldg=780000,
               const="Masonry and steel", year=1968, sqft=4800, spr="No",
               cook="Type I hood, Ansul, wood smokers")],
    lr=["2025-05-19 kitchen grease fire, smoker hood. Paid $61,400. Status: closed.",
        "2026-02-03 water leak from ice machine line. Paid $0. Open reserve $3,000.",
        "Total paid 5 yrs: $61,400. Total open reserve: $3,000. Claim count: 2."],
    email=("Subject: Lone Oak Smokehouse renewal\n\nAttached app and loss runs. We had a grease fire "
           "last May in the smoker hood, fire dept came out, they're done with it now. Sales around 2.1M "
           "last year, and the bar is about a third of that. Ice maker leak in Feb is almost closed out.\n\n"
           "Priya Raman")
))

SUBS.append(dict(
    id="SUB-112", lang="es", app_fmt="typed", sched="none", lr_kind="letter", vt="2026-09-30",
    app=dict(name="Hernandez Plumbing & Drain LLC", dba="Hernandez Plomeria",
             prem="1450 Hemphill St, Fort Worth TX 76104", mail="Same as premises",
             eff="2027-03-15",
             ops="Plomeria residencial y comercial liviana, reparaciones y drenajes. Trabajo en sitio del cliente, sin trabajo en altura.",
             sales="$680,000", emp="7", bldg="$310,000", bpp="$140,000 (herramientas, van)",
             bi="$90,000", const="Masonry veneer over frame", year="1962", sqft="2,800", spr="No",
             cook="N/A", bar="N/A", prior="Bluebonnet Surplus (fictional)",
             losses="Ninguna"),
    locs=[],
    lr=["Sin reclamos reportados en los ultimos 3 anos (2024, 2025 y hasta 2026-09-30).",
        "Carta firmada por el agente anterior (ficticio), 2026-09-22."],
    email=("Subject: Hernandez Plumbing - renovacion\n\nHola, le mando la solicitud de Hernandez Plumbing. "
           "Vigencia 15 de marzo de 2027. Ventas como 680 mil el ano pasado. El taller esta en Hemphill, "
           "edificio propio. Sin reclamos en tres anos, la carta del agente anterior va adjunta.\n\nGracias, "
           "Elena Ruiz (productora)")
))

SUBS.append(dict(
    id="SUB-113", lang="en", app_fmt="typed", sched="csv", lr_kind="typed", vt="2026-09-30",
    app=dict(name="Mesa Court Apartments LLC", dba="Mesa Court",
             prem="3401 36th St, Lubbock TX 79412", mail="PO Box 4410, Lubbock TX 79408",
             eff="2027-05-01",
             ops="Residential apartments, 12 units in 2 buildings. On-site maintenance only, no short-term rentals.",
             sales="$612,000 gross rents", emp="2 (plus contract maintenance)", bldg="$3,400,000",
             bpp="$150,000", bi="$250,000", const="Wood frame", year="1986", sqft="14,200",
             spr="Yes, NFPA 13R", cook="N/A", bar="N/A", prior="Plains Residential Mutual (fictional)",
             losses="1 claim 2025"),
    locs=[dict(loc=1, address="3401 36th St (bldg A)", city="Lubbock", zip="79412", bldg=1900000,
               const="Wood frame", year=1986, sqft=7100, spr="Yes", cook="none"),
          dict(loc=2, address="3405 36th St (bldg B)", city="Lubbock", zip="79412", bldg=1500000,
               const="Wood frame", year=1986, sqft=7100, spr="Yes", cook="none")],
    lr=["2025-07-02 water loss, unit 6, burst supply line. Paid $18,900. Status: closed.",
        "No other claims 2023-2026. Total paid: $18,900. Open reserve: $0. Claim count: 1."],
    email=("Subject: Mesa Court - 12 unit renewal\n\nSee attached. Its 12 units total, 2 buildings, "
           "about 16,800 sq ft. We had one water claim in July 2025, unit 6, its closed. Rents about "
           "600k a year. Sprinklers are the 13R kind, done 2019.\n\nJoel Pruitt")
))

SUBS.append(dict(
    id="SUB-114", lang="en", app_fmt="typed", sched="csv", lr_kind="letter", vt="2026-09-30",
    app=dict(name="Bayfront Villas LP", dba="Bayfront Villas Apartments",
             prem="1180 Harbor Vista Dr, Corpus Christi TX 78404", mail="Same as premises",
             eff="2027-06-01", ops="Apartments, 24 units across 2 floors. Wood frame, no short-term rentals.",
             sales="$1,040,000", emp="3", bldg="$5,100,000", bpp="$250,000", bi="$850,000",
             const="Wood frame, stucco", year="1975", sqft="22,400", spr="No", cook="N/A", bar="N/A",
             prior="Gulf Shore Mutual (fictional)", losses="None per owner"),
    locs=[dict(loc=1, address="1180 Harbor Vista Dr", city="Corpus Christi", zip="78404", bldg=5100000,
               const="Wood frame, stucco", year=1975, sqft=22400, spr="No", cook="none")],
    lr=["No known loss letter from prior carrier, 2026-09-30.",
        "Owner states no claims in five years."],
    email=("Subject: Bayfront Villas - LP renewal, 24 units\n\nApp attached. 24 units, all wood frame, the "
           "building is from 75. Owner is a small LP out of Houston. Sprinklers are not in it. "
           "Rents are around 1M a year. Need a quote asap for June 1.\n\nDana Whitfield")
))

SUBS.append(dict(
    id="SUB-115", lang="en", app_fmt="typed", sched="xlsx", lr_kind="letter", vt="2026-06-30",
    app=dict(name="Cedar Gate Dental Partners LLC", dba="Cedar Gate Dental",
             prem="Main office: 6600 Hwy 290 W, Austin TX 78735", mail="Same as main office",
             eff="2027-07-01",
             ops="Dental offices, 3 locations. General dentistry, orthodontic consults. No overnight care.",
             sales="$3,900,000 (all 3 locations)", emp="41", bldg="$6,800,000 total (see schedule)",
             bpp="included in TIV above", bi="$1,100,000", const="Masonry non-combustible",
             year="2003 / 2011 / 2016", sqft="11,900 total", spr="Yes, all locations",
             cook="N/A", bar="N/A", prior="Northline Mutual (fictional)", losses="None"),
    locs=[dict(loc=1, address="6600 Hwy 290 W", city="Austin", zip="78735", bldg=2900000,
               const="Masonry non-combustible", year=2003, sqft=5200, spr="Yes", cook="none"),
          dict(loc=2, address="1900 Round Rock Ave Ste 4", city="Round Rock", zip="78681", bldg=2300000,
               const="Masonry non-combustible", year=2011, sqft=4100, spr="Yes", cook="none"),
          dict(loc=3, address="1420 Cypress Creek Rd", city="Cedar Park", zip="78613", bldg=1600000,
               const="Masonry non-combustible", year=2016, sqft=2600, spr="Yes", cook="none")],
    lr=["No known loss letter from prior carrier, valued 2026-06-30. Three years no claims."],
    email=("Subject: Cedar Gate Dental - 3 offices\n\nSee the app and the xlsx. Total values are around "
           "4.9M I think, the 6.8 on the app is probably the old number from before the Cedar Park "
           "build out. Same docs as last year.\n\nTom Okafor")
))

SUBS.append(dict(
    id="SUB-116", lang="en", app_fmt="imgpdf", sched="csv", lr_kind="typed", vt="2026-09-30",
    app=dict(name="Tri-County Air & Heat LLC", dba="Tri-County Air",
             prem="2901 Ridgecrest Ct Ste B, Plano TX 75074", mail="Same as premises",
             eff="2027-04-15",
             ops="HVAC install and service contractor, residential and light commercial. Service vans, no roofing work.",
             sales="$1,400,000", emp="11", bldg="$260,000", bpp="$180,000 (tools, parts, vans)",
             bi="$120,000", const="Metal frame", year="1998", sqft="4,100", spr="No", cook="N/A",
             bar="N/A", prior="Bluebonnet Surplus (fictional)", losses="None"),
    locs=[dict(loc=1, address="2901 Ridgecrest Ct Ste B", city="Plano", zip="75074", bldg=260000,
               const="Metal frame", year=1998, sqft=4100, spr="No", cook="none")],
    lr=["Bluebonnet Surplus (fictional), 2023-24: 0 claims, $0 paid",
        "2024-25: 0 claims, $0 paid", "2025-26 through 2026-09-30: 0 claims, $0 paid"],
    email=("Subject: Tri-County Air - contractor renewal\n\nScanned app attached (copy machine at the "
           "office, sorry for the quality). Shop is in Plano, 4,100 sq ft. Sales about 1.4M. Loss runs "
           "typed up below, clean three years.\n\nRuth Anson")
))

SUBS.append(dict(
    id="SUB-117", lang="en", app_fmt="none", sched="none", lr_kind="none", vt=None,
    app=dict(name="Brazos Custom Cabinets LLC", dba="Brazos Cabinets",
             prem="3418 Bosque Industrial Blvd, Waco TX 76706", mail="Same as premises",
             eff="2027-08-01", ops="Custom cabinet and millwork shop. Wood cutting, spray finishing in one booth.",
             sales="$1,100,000", emp="9", bldg="about $700,000", bpp="about $350,000", bi="not sure",
             const="Steel frame", year="1989", sqft="8,000", spr="Not sure", cook="N/A", bar="N/A",
             prior="unknown", losses="none that I know of"),
    locs=[],
    lr=[],
    email=("Subject: Brazos Cabinets renewal - 8/1/27\n\nHi, new one for you. Cabinet shop in Waco, "
           "3418 Bosque Industrial. Steel frame built 89, we own it. Sales around 1.1M. Employees 9. "
           "I dont have an app done yet and I dont have the loss runs, the owner says there were none in 5 "
           "years but he might be wrong. Can you tell me what you need? Thanks\n\nMarisol Vega (producer)")
))

SUBS.append(dict(
    id="SUB-118", lang="en", app_fmt="rot90", sched="csv", lr_kind="none", vt=None,
    app=dict(name="Ironwood Physical Therapy PLLC", dba="Ironwood PT",
             prem="1620 Ranch Rd 12, Suite 4, San Marcos TX 78666", mail="Same as premises",
             eff="2027-03-01",
             ops="Outpatient physical therapy clinic, 3 treatment rooms, gym equipment. No surgery.",
             sales="$1,050,000", emp="9", bldg="$410,000 (tenant improvements)", bpp="$570,000",
             bi="$300,000", const="Masonry", year="2001", sqft="3,600", spr="Yes", cook="N/A", bar="N/A",
             prior="Harbor Point Insurance (fictional)", losses="None known"),
    locs=[dict(loc=1, address="1620 Ranch Rd 12 Ste 4", city="San Marcos", zip="78666", bldg=410000,
               const="Masonry", year=2001, sqft=3600, spr="Yes", cook="none")],
    lr=[],
    email=("Subject: Ironwood PT - new biz 3/1\n\nApp scan attached, sideways, sorry. Loss runs are "
           "coming from the old agency, they said end of week. Clinic is 3,600 sq ft in San Marcos. "
           "Sales about 1.05M.\n\nRuth Anson")
))

SUBS.append(dict(
    id="SUB-119", lang="en", app_fmt="rot180", sched="csv", lr_kind="typed", vt="2026-09-30",
    app=dict(name="Pastor Norte Taqueria LLC", dba="Pastor Norte",
             prem="4410 Blanco Rd, San Antonio TX 78216", mail="Same as premises",
             eff="2027-02-15",
             ops="Taqueria, counter service. Tortillas made on site. Al pastor trompo.",
             sales="$890,000", emp="16", bldg="$480,000", bpp="$210,000", bi="$140,000",
             const="Joisted masonry", year="1983", sqft="2,600", spr="No",
             cook="Trompo, plancha, 2 fryers. Type I hood. No suppression system listed.",
             bar="N/A", prior="Lakeshore Specialty (fictional)", losses="None"),
    locs=[dict(loc=1, address="4140 Blanco Rd", city="San Antonio", zip="78216", bldg=480000,
               const="Joisted masonry", year=1983, sqft=2600, spr="No",
               cook="Trompo, plancha, fryers, Type I hood")],
    lr=["Lakeshore Specialty (fictional), 2023-24: 0 claims",
        "2024-25: 0 claims", "2025-26: 0 claims. Total paid $0."],
    email=("Subject: Pastor Norte - taqueria renewal\n\nScan attached, its upside down (sorry, the "
           "copier). Address is 4140 Blanco, not the one on the app. Sales were 1.09M last year, the 890 "
           "is from two years ago. No claims.\n\nMarco L. (producer)")
))

SUBS.append(dict(
    id="SUB-120", lang="en", app_fmt="copy", sched="copy", lr_kind="copy", vt="2026-09-30",
    copy_of="SUB-107",
    email=("Subject: RESUBMIT Juniper Ridge - new business eff 3/1/27\n\nHi again, sending the Juniper Ridge "
           "file again in case the first one got lost in the portal. Same app, same loss runs, same "
           "schedule. Sorry for the double.\n\nDana Whitfield (producer)")
))

SUBS.append(dict(
    id="SUB-121", lang="en", app_fmt="typed", sched="csv", lr_kind="letter", vt="2026-08-31",
    app=dict(name="Gulf Coast Pool Supply Wholesale LLC", dba="Gulf Coast Pool Supply",
             prem="2650 Concord Rd, Beaumont TX 77705", mail="Same as premises",
             eff="2027-05-15",
             ops="Wholesale pool chemicals and equipment to retailers. Warehouse with forklifts, no retail counter.",
             sales="$2,200,000", emp="17", bldg="$1,900,000", bpp="$1,500,000", bi="$450,000",
             const="Metal frame", year="2008", sqft="16,000", spr="Yes", cook="N/A", bar="N/A",
             prior="Gulf Shore Mutual (fictional)", losses="None"),
    locs=[dict(loc=1, address="2650 Concord Rd", city="Beaumont", zip="77705", bldg=1900000,
               const="Metal frame", year=2008, sqft=16000, spr="Yes", cook="none")],
    lr=["No known loss letter, prior carrier, 2026-08-31. No losses in five years."],
    email=("Subject: Gulf Coast Pool Supply - wholesale renewal\n\nApp attached. TIV is about 2.9M total, "
           "building and contents, I think the 3.4 on the app counted the stock twice. Sales 2.2M. "
           "Warehouse is 16k sq ft in Beaumont, sprinklered.\n\nJoel Pruitt")
))

SUBS.append(dict(
    id="SUB-122", lang="en", app_fmt="typed", sched="xlsx", lr_kind="typed", vt="2026-06-30",
    app=dict(name="Brewhouse Lane Pizza & Tap Co LLC", dba="Brewhouse Lane",
             prem="812 Brewster Ln, Arlington TX 76010", mail="Same as premises",
             eff="2027-03-01",
             ops="Pizza restaurant with wood-fired oven, full bar (beer, wine, cocktails), patio seating.",
             sales="$1,600,000", emp="31", bldg="$430,000", bpp="$260,000", bi="$150,000",
             const="Joisted masonry", year="1996", sqft="4,800", spr="Yes",
             cook="Wood-fired oven, fryer x1. Type I hood, Ansul serviced 2026-04-20.",
             bar="Full bar, last call 1am", prior="Lakeshore Specialty (fictional)",
             losses="None"),
    locs=[dict(loc=1, address="812 Brewster Ln", city="Arlington", zip="76010", bldg=430000,
               const="Joisted masonry", year=1996, sqft=4800, spr="Yes",
               cook="Wood-fired oven, fryer, Type I hood, Ansul")],
    lr=["Policy 2024-10-01 to 2025-09-30: 0 claims, $0 paid",
        "Policy 2025-10-01 to 2026-06-30: 0 claims, $0 paid",
        "Prior years not included in this extract."],
    email=("Subject: Brewhouse Lane - restaurant + bar, 3/1/27\n\nLoss runs attached for the last two "
           "years, clean. We switched agents in 2024 so the older ones are with the old carrier. Sales "
           "1.6M. Oven is wood fired, hood and ansul were done in April.\n\nPriya Raman")
))

SUBS.append(dict(
    id="SUB-123", lang="es", app_fmt="color", sched="csv", lr_kind="letter", vt="2026-09-30",
    app=dict(name="Tienda Luna Azul LLC", dba="Luna Azul Boutique",
             prem="7822 Gulf Plaza Dr, Houston TX 77036", mail="Same as premises",
             eff="2027-06-01", ops="Tienda de ropa y accesorios al por menor. Sin alteraciones ni servicios.",
             sales="$720,000", emp="5", bldg="$900,000 (mejoras al local)", bpp="$450,000",
             bi="$120,000", const="Mamposteria", year="1983", sqft="3,100", spr="No",
             cook="N/A", bar="N/A", prior="Bluebonnet Surplus (fictional)", losses="Ninguna"),
    locs=[dict(loc=1, address="7822 Gulf Plaza Dr", city="Houston", zip="77036", bldg=900000,
               const="Masonry", year=1983, sqft=3100, spr="No", cook="none")],
    lr=["Sin reclamos reportados en los ultimos 5 anos segun el solicitante.",
        "Carta de pérdidas sin reclamos, agente anterior, 2026-09-30."],
    email=("Subject: Luna Azul - tienda nueva\n\nHola, le mando la solicitud escaneada a color de Tienda "
           "Luna Azul. Ventas como 720 mil. Local de 3,100 pies cuadrados en Gulf Plaza. Vigencia 1 de junio "
           "de 2027. Sin reclamos.\n\nElena Ruiz (productora)")
))

SUBS.append(dict(
    id="SUB-124", lang="en", app_fmt="gray", sched="xlsx", lr_kind="typed", vt="2026-09-30",
    app=dict(name="Brisket & Co Group LLC", dba="Brisket & Co (Plano and Frisco)",
             prem="1401 Legacy Gardens Dr, Plano TX 75024 (Plano); Frisco location see schedule",
             mail="Same as Plano", eff="2027-09-01",
             ops="Two full-service BBQ restaurants with full bars and live music on weekends.",
             sales="$4,100,000 (both locations)", emp="74", bldg="$1,350,000 total",
             bpp="$980,000 total", bi="$700,000", const="Masonry and steel", year="2003 / 2014",
             sqft="6,200 + 5,400", spr="Plano: No. Frisco: Yes.",
             cook="Smokers, fryers. Type I hoods at both, Ansul serviced 2026-03.",
             bar="Full bar at both locations", prior="Northline Mutual (fictional)",
             losses="1 claim, see loss runs"),
    locs=[dict(loc=1, address="1401 Legacy Gardens Dr", city="Plano", zip="75024", bldg=800000,
               const="Masonry and steel", year=2003, sqft=6200, spr="No",
               cook="Smokers, fryers, Type I hood, Ansul"),
          dict(loc=2, address="8290 Main St Ste 110", city="Frisco", zip="75034", bldg=550000,
               const="Masonry and steel", year=2014, sqft=5400, spr="Yes",
               cook="Smokers, fryers, Type I hood, Ansul")],
    lr=["2024-11-08 kitchen fire, Frisco location. Paid $112,000. Status: closed.",
        "Total paid 5 yrs: $112,000. Open reserve: $0. Claim count: 1."],
    email=("Subject: Brisket & Co group - 2 locations\n\nThe app says 4.1M but Dana (our acct) says the "
           "real number is 3.6 combined, the Frisco one only opened mid 2024. Frisco had the kitchen fire "
           "in Nov 2024, all closed. Attached schedule. Eff 9/1/27.\n\nRuth Anson")
))

SUBS.append(dict(
    id="SUB-125", lang="en", app_fmt="typed", sched="xlsx", lr_kind="typed", vt="2026-09-30",
    app=dict(name="Ledger & Lane Tax Services LLC", dba="Ledger & Lane",
             prem="2310 Hidden Ridge Dr, Irving TX 75039", mail="Same as premises",
             eff="2027-08-01", ops="Tax preparation and bookkeeping offices, seasonal staff. No walk-in retail.",
             sales="$1,100,000", emp="12 (up to 20 in season)", bldg="$1,200,000 (tenant improvements)",
             bpp="$700,000", bi="$300,000", const="Masonry non-combustible", year="1999",
             sqft="5,000", spr="Yes", cook="N/A", bar="N/A", prior="Northline Mutual (fictional)",
             losses="1 claim, 2025"),
    locs=[dict(loc=1, address="2310 Hidden Ridge Dr", city="Irving", zip="75039", bldg=1200000,
               const="Masonry non-combustible", year=1999, sqft=5000, spr="Yes", cook="none")],
    lr=["2025-11-02 water loss, roof leak over suite 2. Paid $8,450. Status: closed.",
        "No other claims. Total paid: $8,450. Open reserve: $0. Claim count: 1."],
    email=("Subject: Ledger & Lane - renewal\n\nHere is the app. Eff date is 9/1/27 I think, the app says "
           "8/1 but I may have typed that wrong. One roof leak claim last November, closed. Sales 1.1M.\n\n"
           "Dana Whitfield")
))

SUBS.append(dict(
    id="SUB-126", lang="en", app_fmt="typed", sched="none", lr_kind="letter", vt="2026-09-30",
    app=dict(name="Red Mesa Screen Print Co LLC", dba="Red Mesa Prints",
             prem="6150 Mesa Industrial Ln, El Paso TX 79905", mail="Same as premises",
             eff="TBD (to confirm with insured)",
             ops="Screen printing of apparel and promo items. Two presses, heat press, dryer ovens.",
             sales="$1,300,000", emp="13", bldg="$520,000", bpp="$360,000", bi="$150,000",
             const="Tilt-wall concrete", year="1990", sqft="7,200", spr="No", cook="N/A", bar="N/A",
             prior="Harbor Point Insurance (fictional)", losses="None"),
    locs=[],
    lr=["No known loss letter, prior carrier, valued 2026-09-30. No claims in five years."],
    email=("Subject: Red Mesa Screen Print - app\n\nSending the app. Effective date we still have to confirm "
           "with the owner, probably spring. Shop is 7,200 sq ft, built 1990, tilt wall. Sales 1.3M. Dryer "
           "ovens are gas. No claims.\n\nTom Okafor")
))


# ---------------------------------------------------------------- build


def build_one(s):
    d = os.path.join(INBOX, s["id"])
    os.makedirs(d, exist_ok=True)
    write_text(os.path.join(d, "email.md"), email_text(s))
    fmt = s["app_fmt"]
    seed = int(s["id"].split("-")[1])
    if fmt == "typed":
        typed_pdf(os.path.join(d, "application.pdf"), paginate_typed(app_lines(s)))
    elif fmt in ("gray", "color", "rot90", "rot180", "imgpdf"):
        paper = (238, 236, 228) if fmt == "color" else (255, 255, 255)
        ink = (30, 40, 90) if fmt == "color" else (10, 10, 10)
        rot = {"rot90": 90, "rot180": 180}.get(fmt, 0)
        imgs = scan_pages(app_lines(s), paper, ink, rotate=rot, gray=(fmt == "gray"), seed=seed)
        save_image_pdf(os.path.join(d, "application.pdf"), imgs)
    if s["lr_kind"] in ("typed", "letter"):
        write_text(os.path.join(d, "loss-runs.md"), lr_text(s))
    if s["sched"] == "csv":
        write_csv(os.path.join(d, "schedule.csv"), s["locs"])
    elif s["sched"] == "xlsx":
        write_xlsx(os.path.join(d, "schedule.xlsx"), s["locs"])


def build_copy(s):
    src = os.path.join(INBOX, s["copy_of"])
    d = os.path.join(INBOX, s["id"])
    os.makedirs(d, exist_ok=True)
    for name in ("application.pdf", "loss-runs.md", "schedule.csv"):
        if os.path.exists(os.path.join(src, name)):
            shutil.copyfile(os.path.join(src, name), os.path.join(d, name))
    write_text(os.path.join(d, "email.md"), email_text(s))


def main():
    for s in SUBS:
        if "copy_of" in s:
            continue
        build_one(s)
    for s in SUBS:
        if "copy_of" in s:
            build_copy(s)
    print("built", len(SUBS), "submissions into", INBOX)


if __name__ == "__main__":
    sys.exit(main())
