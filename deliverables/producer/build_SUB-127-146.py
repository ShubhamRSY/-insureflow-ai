import csv, io, sys, textwrap
from pathlib import Path

INBOX = Path("/Users/disastershubz/INSURANCE FLOW AI/-insureflow-ai-1/simulation/inbox")
sys.path.insert(0, "/Users/disastershubz/INSURANCE FLOW AI/-insureflow-ai-1/underwriting_pipeline/ai")
from smoke_readers import _scan  # read-only import

FOOT = "**FICTIONAL.** All businesses, people, addresses and policy numbers are made up.\n\n"
CSV_HEAD = ["source", "loc", "address", "city", "zip", "bldg_tiv", "construction", "year_built", "sq_ft", "sprinklers", "cooking"]


def pdf_bytes(lines):
    def enc(s):
        s = s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        return s.replace("—", "\\227")
    body = "BT /F1 10 Tf 40 750 Td 13 TL " + " ".join(f"({enc(l)}) Tj T*" for l in lines) + " ET"
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(body)} >>\nstream\n{body}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>",
    ]
    out = b"%PDF-1.4\n"
    offs = []
    for n, o in enumerate(objs, 1):
        offs.append(len(out))
        out += f"{n} 0 obj\n{o}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{o:010d} 00000 n \n" for o in offs).encode()
    out += f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out


def write(sub, name, text):
    d = INBOX / sub
    d.mkdir(exist_ok=True)
    (d / name).write_text(text, encoding="utf-8")


def csv_file(sub, rows):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(CSV_HEAD)
    for r in rows:
        w.writerow(r)
    write(sub, "schedule.csv", buf.getvalue())


def wrapped(text, width=72):
    out = []
    for line in text.split("\n"):
        out += textwrap.wrap(line, width) or [""]
    return out


def scan_text(sub, name, text, mode="L", turn=0, fmt=None):
    img = _scan(wrapped(text), mode, turn)
    path = INBOX / sub / name
    if fmt:
        img.save(path, fmt, resolution=150) if fmt == "PDF" else img.save(path, fmt, quality=85)
    else:
        img.save(path, "JPEG", quality=85)


def app(sub, name, addr, city, zc, ent, lob, ops, emp, sales, tiv, bpp, sqft, constr, yr, stories, spk, cook,
        expiring, years, claims="None known", mailing="same as premises", extra=""):
    text = f"""# Application (ACORD 125/140 style)

Submission: {sub}
Named insured: {name}
Mailing address: {mailing}
Premises address: {addr}, {city}, TX {zc}
Effective date: 2027-{extra_eff.get(sub, '03-01')}
Years in business: {years}
Entity type: {ent}
Line of business: {lob}
Operations: {ops}
Number of employees: {emp}
Annual sales: {sales}
Building TIV: {tiv}
Business personal property: {bpp}
Square footage: {sqft}
Construction: {constr}
Year built: {yr}
Stories: {stories}
Sprinklers: {spk}
Cooking operations: {cook}
Expiring carrier: {expiring}
Pending or open claims: {claims}
Bankruptcy or cancellation in last 5 years: No
{extra}"""
    write(sub, name, FOOT + text)


extra_eff = {}
def app(sub, name, eff, addr, city, zc, ent, lob, ops, emp, sales, tiv, bpp, sqft, constr, yr, stories, spk, cook,
        expiring, years, claims="None known", mailing="same as premises"):
    text = f"""# Application (ACORD 125/140 style)

Submission: {sub}
Named insured: {name}
Mailing address: {mailing}
Premises address: {addr}, {city}, TX {zc}
Effective date: {eff}
Years in business: {years}
Entity type: {ent}
Line of business: {lob}
Operations: {ops}
Number of employees: {emp}
Annual sales: {sales}
Building TIV: {tiv}
Business personal property: {bpp}
Square footage: {sqft}
Construction: {constr}
Year built: {yr}
Stories: {stories}
Sprinklers: {spk}
Cooking operations: {cook}
Expiring carrier: {expiring}
Pending or open claims: {claims}
Bankruptcy or cancellation in last 5 years: No
"""
    write(sub, "application.md", FOOT + text)
    return text


def ptext(sub, name, text):
    """Plain (no banner) document for carrier-format and letter files."""
    write(sub, name, text)


A_HEAD = "CARRIER A — LOSS RUN (FICTIONAL)"
B_HEAD = "Carrier B Loss History Report (fictional)"
C_HEAD = "CARRIER C | LOSS RUN | FICTIONAL"

# ---------- SUB-127 Carrier A typed PDF, clean ----------
s = "SUB-127"
write(s, "email.md", FOOT + """Subject: Cedar Bend Financial - new to you eff 3/1/27

Hi, Cedar Bend Financial is moving from Carrier A to you guys at 3/1, rate went up at renewal. Financial advisory office downtown, 9 people, 2nd floor. Loss run from A's portal attached, one small water claim last year and its closed.

Thanks, Gina Ferrante (producer)
""")
app(s, "Cedar Bend Financial Advisors LLC", "2027-03-01", "1800 Main St", "Dallas", "75201", "limited liability company",
    "commercial property and general liability, office",
    "Financial advisory and tax office, 2nd floor. Clients by appointment. No inventory, no goods held for sale.",
    9, "$1,060,000 (gross fees, prior year)", "$1,150,000", "$95,000", "5,400", "Masonry non-combustible", 1987, 4,
    "Yes", "None", "Carrier A, policy expiring 2027-03-01", 11)
csv_file(s, [["FICTIONAL", 1, "1800 Main St", "Dallas", "75201", 1150000, "Masonry non-combustible", 1987, 5400, "Yes", "none"]])
write_pdf = lambda sub, lines: (INBOX / sub / "loss-runs.pdf").write_bytes(pdf_bytes(lines))
write_pdf(s, [
    A_HEAD,
    "Named insured: Cedar Bend Financial Advisors LLC",
    "Policy period: 2024-03-01 to 2025-03-01",
    "Policy period: 2025-03-01 to 2026-03-01",
    "Valued as of: 2026-09-30",
    "| Date of loss | Cause | Paid | Reserve | Status |",
    "|---|---|---|---|---|",
    "| 2025-06-14 | water damage | $4,200 | $0 | closed |",
])

# ---------- SUB-128 Carrier A typed md, no-claims line, clean ----------
s = "SUB-128"
write(s, "email.md", FOOT + """Subject: Prairie Hill Candle & Gift - Abilene, shopping it

Hey, Prairie Hill is a gift and candle shop on 1st street in Abilene, they've been with Carrier A since they opened. We are shopping it because A wants a big increase. A loss run is below in the attachment. They never had a claim.

Thanks, Paulette Vance (producer)
""")
app(s, "Prairie Hill Candle & Gift Co LLC", "2027-02-01", "1901 N 1st St", "Abilene", "79601", "limited liability company",
    "commercial property and general liability, retail",
    "Dry retail gift shop: candles, home goods, greeting cards, gift wrap. No food, no alcohol, no repackaging.",
    7, "$820,000", "$780,000", "$140,000", "3,200", "Masonry", 1978, 1, "No", "None", "Carrier A, policy expiring 2027-02-01", 11)
csv_file(s, [["FICTIONAL", 1, "1901 N 1st St", "Abilene", "79601", 780000, "Masonry", 1978, 3200, "No", "none"]])
ptext(s, "loss-runs.md", f"""{A_HEAD}
Named insured: Prairie Hill Candle & Gift Co LLC
Policy period: 2024-02-01 to 2025-02-01
Policy period: 2025-02-01 to 2026-02-01
Valued as of: 2026-09-30
No claims reported by Carrier A for the policy periods above.
""")

# ---------- SUB-129 Carrier A image-only PDF loss run, scanned application, revenue conflict ----------
s = "SUB-129"
write(s, "email.md", FOOT + """Subject: Brazos Electrical Supply - renewal to you

Hi again. Brazos Electrical is light wholesale, we sell wire, breakers, conduit to electricians. Their building is about 2.4 mil. Sales are around 3.1 mil this year (they grew). Carrier A is renewing but the owner wants a second quote. Loss run from A is attached as a scan, the portal printed it funny. Application is a scan too, sorry.

Thanks, Hector Quiroz (producer)
""")
b129 = app(s, "Brazos Electrical Supply Inc", "2027-04-01", "3115 S 31st St", "Temple", "76501", "corporation",
           "commercial property and general liability, light wholesale",
           "Light wholesale of electrical supplies (wire, breakers, conduit, fixtures) to licensed electricians. Counter and warehouse, will-call pickup. No manufacturing.",
           18, "$2,600,000", "$2,400,000", "$620,000", "14,000", "Tilt-up concrete", 2004, 1, "Yes, wet pipe system",
           "None", "Carrier A, policy expiring 2027-04-01", 14)
csv_file(s, [["FICTIONAL", 1, "3115 S 31st St", "Temple", "76501", 2400000, "Tilt-up concrete", 2004, 14000, "Yes", "none"]])
scan_text(s, "application.jpg", b129.replace(FOOT, ""), "RGB")
scan_text(s, "loss-runs.pdf", "\n".join([
    A_HEAD,
    "Named insured: Brazos Electrical Supply Inc",
    "Policy period: 2024-04-01 to 2025-04-01",
    "Policy period: 2025-04-01 to 2026-04-01",
    "Valued as of: 2026-09-30",
    "| Date of loss | Cause | Paid | Reserve | Status |",
    "|---|---|---|---|---|",
    "| 2024-11-08 | theft | $1,850 | $0 | closed |",
]), "L", fmt="PDF")
# wrapped() splits on \n only; the loss run lines are short so no wrap happens above

# ---------- SUB-130 Carrier B typed PDF, restaurant, one claim outside the 3 clean years ----------
s = "SUB-130"
write(s, "email.md", FOOT + """Subject: Harbor Lane Cafe - Corpus Christi, eff 1/1/27

Hi, Harbor Lane Cafe is a breakfast and lunch place on Ocean Dr in Corpus. They're with B now and B has been fine. B loss run attached. One grease fire in 2023 at the flat top hood, cleaned up and closed out. Hood was cleaned July this year.

Thanks, Dee Halvorsen (producer)
""")
app(s, "Harbor Lane Cafe LLC", "2027-01-01", "5010 Ocean Dr", "Corpus Christi", "78412", "limited liability company",
    "commercial property and general liability, restaurant",
    "Breakfast and lunch cafe, 64 seats, beer and wine only, no liquor license. Dine-in and takeout.",
    15, "$1,120,000", "$520,000", "$145,000", "3,100", "Masonry", 1991, 1, "Yes",
    "Flat-top griddle, 2 fryers, 6-burner range, convection oven. Type I hood with UL 300 wet chemical suppression, hood cleaned 2026-07.",
    "Carrier B, policy expiring 2027-01-01", 11)
csv_file(s, [["FICTIONAL", 1, "5010 Ocean Dr", "Corpus Christi", "78412", 520000, "Masonry", 1991, 3100, "Yes",
              "flat-top, 2 fryers, 6-burner range, convection oven, Type I hood UL 300"]])
pdf_b = [
    B_HEAD,
    "Insured: Harbor Lane Cafe LLC",
    "Policy term: 2023-01-01 to 2024-01-01",
    "Policy term: 2024-01-01 to 2025-01-01",
    "Policy term: 2025-01-01 to 2026-01-01",
    "Policy term: 2026-01-01 to 2027-01-01",
    "Valuation date: 2026-09-30",
    "| Loss date | Description | Paid | Outstanding |",
    "|---|---|---|---|",
    "| 2023-05-02 | grease fire | $9,500 | $0 |",
]
(INBOX / s / "loss-runs.pdf").write_bytes(pdf_bytes(pdf_b))

# ---------- SUB-131 Carrier B greyscale JPG scan, contractor, conflicts (sq ft, claims) ----------
s = "SUB-131"
write(s, "email.md", FOOT + """Subject: Ruiz & Pope Plumbing - Killeen, B to you at 2/15

Ruiz and Pope, plumbers in Killeen, commercial service and water heater installs. Been with B for years, were moving the account to you guys because B wants a rate bump. Loss run from B attached, its a scan of the printout because the portal wouldnt let me download it. Let me know if you need the pdf.

Thanks, Sonia Pope (producer's assistant)
""")
app(s, "Ruiz & Pope Plumbing Co LLC", "2027-02-15", "2407 E Rancier Ave", "Killeen", "76542", "limited liability company",
    "commercial property and general liability, light contractor",
    "Commercial plumbing service and repair, water heater installs, small remodel work. Office and shop on premises, 2 service vans kept on site overnight. No roofing, no hot work on premises.",
    12, "$1,640,000", "$310,000", "$285,000", "2,100", "Metal frame, metal siding", 2009, 1, "No", "None",
    "Carrier B, policy expiring 2027-02-15", 16)
csv_file(s, [["FICTIONAL", 1, "2407 E Rancier Ave", "Killeen", "76542", 310000, "Metal frame, metal siding", 2009, 2800, "No", "none"]])
scan_text(s, "loss-runs.jpg", "\n".join([
    B_HEAD,
    "Insured: Ruiz & Pope Plumbing Co LLC",
    "Policy term: 2023-02-15 to 2024-02-15",
    "Policy term: 2024-02-15 to 2025-02-15",
    "Policy term: 2025-02-15 to 2026-02-15",
    "Policy term: 2026-02-15 to 2027-02-15",
    "Valuation date: 2026-09-30",
    "| Loss date | Description | Paid | Outstanding |",
    "|---|---|---|---|",
    "| 2025-08-18 | water line break | $7,400 | $1,100 |",
]), "L")

# ---------- SUB-132 Carrier B typed md, restaurant, old claim only (clean last 3 terms) ----------
s = "SUB-132"
write(s, "email.md", FOOT + """Subject: Sweet Tea & Biscuit Co - San Antonio, eff 3/1/27

Hi, Sweet Tea and Biscuit on Broadway. Nine years with B and they say the account is clean for the last few terms. The dish machine leaked in 2023 and they replaced the flooring, that's on the loss run. Breakfast and lunch, 90 seats, beer and wine only.

Thanks, Dee Halvorsen (producer)
""")
app(s, "Sweet Tea & Biscuit Co LLC", "2027-03-01", "1407 Broadway St", "San Antonio", "78215", "limited liability company",
    "commercial property and general liability, restaurant",
    "Southern breakfast and lunch restaurant, 90 seats, beer and wine only, dine-in and takeout.",
    22, "$1,380,000", "$680,000", "$190,000", "3,900", "Joisted masonry", 1952, 1, "Yes",
    "Two fryers, flat-top, 8-burner range, two convection ovens. Type I hood with UL 300 wet chemical system, serviced 2026-06.",
    "Carrier B, policy expiring 2027-03-01", 9)
csv_file(s, [["FICTIONAL", 1, "1407 Broadway St", "San Antonio", "78215", 680000, "Joisted masonry", 1952, 3900, "Yes",
              "2 fryers, flat-top, 8-burner range, 2 convection ovens, Type I hood UL 300"]])
ptext(s, "loss-runs.md", f"""{B_HEAD}
Insured: Sweet Tea & Biscuit Co LLC
Policy term: 2023-03-01 to 2024-03-01
Policy term: 2024-03-01 to 2025-03-01
Policy term: 2025-03-01 to 2026-03-01
Policy term: 2026-03-01 to 2027-03-01
Valuation date: 2026-09-30
| Loss date | Description | Paid | Outstanding |
|---|---|---|---|
| 2023-07-19 | dish machine leak | $2,100 | $0 |
""")

# ---------- SUB-133 Carrier C colour JPG scan, rotated, habitational, units conflict ----------
s = "SUB-133"
write(s, "email.md", FOOT + """Subject: Canyon Oaks Apartments - Lubbock, C to you

Hi, Canyon Oaks is a 12 or 14 unit complex in Lubbock, sprinklered, owner is Canyon Oaks Apartments LP. Carrier C has them now. Want to see if you can beat C at renewal 4/1. Loss run from C attached, its a scan, sideways sorry. Check the app for the unit count, I forget which.

Thanks, Pam Ostrander (producer)
""")
app(s, "Canyon Oaks Apartments LP", "2027-04-01", "4120 82nd St", "Lubbock", "79423", "limited partnership",
    "commercial property and general liability, habitational",
    "Residential apartments, 12 units in one two-story building, long-term leases. Occupancy 91 percent.",
    3, "$236,000 (gross annual rents)", "$1,460,000", "$35,000", "12,900", "Wood frame with masonry veneer", 1989, 2,
    "Yes, NFPA 13 system, retrofit 2020", "None (tenant electric ranges only)", "Carrier C, policy expiring 2027-04-01", 17)
csv_file(s, [["FICTIONAL", 1, "4120 82nd St", "Lubbock", "79423", 1460000, "Wood frame with masonry veneer", 1989, 12900, "Yes", "none"]])
scan_text(s, "loss-runs.jpg", "\n".join([
    C_HEAD,
    "Account: Canyon Oaks Apartments LP",
    "Term: 2025-04-01 - 2026-04-01",
    "Valued: 2026-09-30",
    "| Claim no. | Loss date | Type | Paid | Open reserve |",
    "|---|---|---|---|---|",
    "| C-1187 | 2025-11-20 | wind/hail | $8,500 | $0 |",
]), "RGB", turn=90)

# ---------- SUB-134 Carrier C typed PDF, light manufacturing, clean ----------
s = "SUB-134"
write(s, "email.md", FOOT + """Subject: Bayou Glass & Mirror Works - Beaumont, eff 5/1/27

Hi, Bayou Glass is a cutting and tempering shop in Beaumont, they make storefront glass and framing. 4 years with Carrier C, C is ok but high. One hail claim last fall, loss run from C attached.

Thanks, Ben Carrow (producer)
""")
app(s, "Bayou Glass & Mirror Works LLC", "2027-05-01", "2145 Pine St", "Beaumont", "77701", "limited liability company",
    "commercial property and general liability, light manufacturing",
    "Glass cutting, tempering and framing for commercial storefronts. Shop and small showroom, no chemicals beyond cleaning supplies.",
    14, "$1,950,000", "$890,000", "$610,000", "11,500", "Masonry", 1972, 1, "Yes", "None",
    "Carrier C, policy expiring 2027-05-01", 13)
csv_file(s, [["FICTIONAL", 1, "2145 Pine St", "Beaumont", "77701", 890000, "Masonry", 1972, 11500, "Yes", "none"]])
pdf_c = [
    C_HEAD,
    "Account: Bayou Glass & Mirror Works LLC",
    "Term: 2024-05-01 - 2025-05-01",
    "Term: 2025-05-01 - 2026-05-01",
    "Valued: 2026-09-30",
    "| Claim no. | Loss date | Type | Paid | Open reserve |",
    "|---|---|---|---|---|",
    "| C-1139 | 2025-09-12 | wind/hail | $3,200 | $0 |",
]
(INBOX / s / "loss-runs.pdf").write_bytes(pdf_bytes(pdf_c))

# ---------- SUB-135 non-carrier English no-known-loss letter, dry retail ----------
s = "SUB-135"
write(s, "email.md", FOOT + """Subject: Lone Oak Thrift & Books - new biz 1/15/27

Hi, Lone Oak is a used book and thrift shop in Denton, owner Marcus is new to commercial, his old policy was through a personal lines agent. He cant get a loss run from them so he wrote a letter. Eff 1/15/27.

Thanks, Ray Osterholt (producer)
""")
app(s, "Lone Oak Thrift & Books LLC", "2027-01-15", "412 W Oak St", "Denton", "76201", "limited liability company",
    "commercial property and general liability, retail",
    "Used book and thrift shop, donated goods sorted on site, sales floor and back room. No food, no alcohol.",
    4, "$390,000", "$430,000", "$110,000", "2,600", "Frame", 1958, 1, "No", "None",
    "Other (prior personal lines policy, not a commercial carrier), policy ends 2027-01-15", 6)
csv_file(s, [["FICTIONAL", 1, "412 W Oak St", "Denton", "76201", 430000, "Frame", 1958, 2600, "No", "none"]])
ptext(s, "loss-runs.md", """To whom it may concern,

I, Marcus Lindell, owner of Lone Oak Thrift & Books LLC, state that the business has had no insurance claims or losses in the last five years, to my knowledge. We have had no fires, no water damage and no theft claims reported to any insurer.

Date: 2026-09-28
Signed: Marcus Lindell
""")

# ---------- SUB-136 Spanish no-known-loss letter, restaurant with cooking lines ----------
s = "SUB-136"
write(s, "email.md", FOOT + """Subject: Taqueria La Esquina - Laredo, new to us

Hola, Taqueria La Esquina is a family restaurant in Laredo, 70 seats, beer and wine only. Jorge the owner wrote the no-loss letter himself in spanish, hope thats ok, he isnt comfortable with english on paper. Their last agent is retiring so no carrier loss run. Eff 2/1/27.

Gracias, Ben Carrow (producer)
""")
app(s, "Taqueria La Esquina LLC", "2027-02-01", "1810 San Bernardo Ave", "Laredo", "78040", "limited liability company",
    "commercial property and general liability, restaurant",
    "Mexican restaurant, 70 seats, beer and wine only, no bar. Dine-in and takeout.",
    11, "$940,000", "$510,000", "$165,000", "2,900", "Masonry", 1985, 1, "No",
    "Comal and flat-top, two deep fryers, 6-burner range. Type I hood with UL 300 system, cleaned 2026-06.",
    "Not named (prior agent), policy expiring 2027-02-01", 8)
csv_file(s, [["FICTIONAL", 1, "1810 San Bernardo Ave", "Laredo", "78040", 510000, "Masonry", 1985, 2900, "No",
              "comal, flat-top, 2 deep fryers, 6-burner range, Type I hood UL 300"]])
ptext(s, "loss-runs.md", """Declaracion de no reclamos

Yo, Jorge Alberto Trevino, dueno de Taqueria La Esquina LLC, declaro que en los ultimos cinco anos el negocio no ha tenido reclamos de seguro ni perdidas que yo conozca. No hemos tenido incendios, danos por agua ni robos reportados.

Fecha: 2026-09-20
Firma: Jorge Alberto Trevino
""")

# ---------- SUB-137 non-carrier applicant letter: copies Carrier B header, has valued-as-of date ----------
s = "SUB-137"
write(s, "email.md", FOOT + """Subject: Northline Heating & Air - Round Rock, B renewal to you

Hi, Northline is an HVAC install and service outfit in Round Rock, 13 guys. They're with B, B is slow getting us the loss run so the owner Dale typed his own up. Let me know if that works or if you need B's official one.

Thanks, Pam Ostrander (producer)
""")
app(s, "Northline Heating & Air LLC", "2027-03-01", "3205 Sam Bass Rd", "Round Rock", "78681", "limited liability company",
    "commercial property and general liability, light contractor",
    "HVAC installation and service contractor. Office and warehouse on premises, trucks off site overnight, light shop work.",
    13, "$1,320,000", "$380,000", "$210,000", "4,200", "Metal", 2011, 1, "No", "None",
    "Carrier B, policy expiring 2027-03-01", 14)
csv_file(s, [["FICTIONAL", 1, "3205 Sam Bass Rd", "Round Rock", "78681", 380000, "Metal", 2011, 4200, "No", "none"]])
ptext(s, "loss-runs.md", f"""{B_HEAD}
Insured: Northline Heating & Air LLC
Policy term: 2026-03-01 to 2027-03-01
Valued as of: 2026-09-30
Owner note: we had one small water claim in 2025 that we paid ourselves, under the deductible. No claims were filed with any carrier.
Dale Ruffner, owner
""")

# ---------- SUB-138 non-carrier agent summary naming Carrier A, light wholesale ----------
s = "SUB-138"
write(s, "email.md", FOOT + """Subject: Pecan Grove Feed & Seed - Amarillo renewal

Hi, Pecan Grove is feed, seed and fertilizer bags, wholesale plus a little counter. Big warehouse. A has them now at 4/1. I put a summary together from our agency system, didnt get the pdf from A yet, we have a portal login but I didnt pull it. TIV about 1.85.

Thanks, Renee Batts (producer)
""")
app(s, "Pecan Grove Feed & Seed Co LLC", "2027-04-01", "1600 S Fillmore St", "Amarillo", "79101", "limited liability company",
    "commercial property and general liability, light wholesale",
    "Wholesale and retail of animal feed, seed and fertilizer bags. Warehouse with loading dock and a small trade counter.",
    16, "$3,200,000", "$1,850,000", "$740,000", "22,000", "Concrete block (CMU)", 1968, 1, "No", "None",
    "Carrier A, policy expiring 2027-04-01", 19)
csv_file(s, [["FICTIONAL", 1, "1600 S Fillmore St", "Amarillo", "79101", 1850000, "Concrete block (CMU)", 1968, 22000, "No", "none"]])
ptext(s, "loss-runs.md", """AGENCY SUMMARY - NOT A CARRIER LOSS RUN (FICTIONAL)
Account: Pecan Grove Feed & Seed Co LLC
Prepared by: Renee Batts, producer
Prepared: 2026-09-22
Per our agency system, Carrier A shows no claims for this account from 2021 through 2026.
Carrier A printout not attached. Summary only, from agency records.
""")

# ---------- SUB-139 non-panel carrier layout, habitational without sprinklers (no-match) ----------
s = "SUB-139"
write(s, "email.md", FOOT + """Subject: Azalea Court Apts - Tyler, Lone Star Mutual non-renewing

Hi, Azalea Court is 6 units in Tyler, two story, Lone Star Mutual is non-renewing at 6/1 because of the rate. The summary from LSM is attached. Owner is Teddy Ash. No idea if you guys do apartments, just sending it over.

Thanks, Ray Osterholt (producer)
""")
app(s, "Azalea Court Apartments LLC", "2027-06-01", "1418 Azalea Dr", "Tyler", "75701", "limited liability company",
    "commercial property, habitational",
    "Residential apartments, 6 units in two two-story buildings, long-term leases, occupancy 83 percent.",
    1, "$118,000 (gross annual rents)", "$720,000", "$15,000", "7,400", "Wood frame", 1974, 2, "No", "None",
    "Lone Star Mutual, policy expiring 2027-06-01", 14)
csv_file(s, [["FICTIONAL", 1, "1418 Azalea Dr", "Tyler", "75701", 720000, "Wood frame", 1974, 7400, "No", "none"]])
ptext(s, "loss-runs.md", """LONE STAR MUTUAL - FIVE YEAR CLAIMS SUMMARY (FICTIONAL)
Insured name: Azalea Court Apartments LLC
Report prepared: 2026-09-15
Period 2022-06-01 to 2023-06-01: 0 claims
Period 2023-06-01 to 2024-06-01: 1 claim, plumbing leak, paid $3,100, open $0
Period 2024-06-01 to 2025-06-01: 0 claims
Period 2025-06-01 to 2026-06-01: 0 claims
Total paid: $3,100
Summary only. Full loss runs available on request from the carrier claims portal.
""")

# ---------- SUB-140 two locations, Carrier B layout with the valuation line missing ----------
s = "SUB-140"
write(s, "email.md", FOOT + """Subject: Smokehouse Row BBQ - 2 locations Fort Worth, eff 6/1/27

Hi, Smokehouse Row has two spots in Fort Worth, Rosedale and Camp Bowie. B has had them forever. Loss run from B attached. Kitchen fire last year at Rosedale, its covered, B paid it out, still open a little on it. Beer and wine, no liquor.

Thanks, Dee Halvorsen (producer)
""")
app(s, "Smokehouse Row BBQ Co LLC", "2027-06-01", "2300 Rosedale St", "Fort Worth", "76105", "limited liability company",
    "commercial property and general liability, restaurant, 2 locations",
    "Barbecue restaurants, two locations, dine-in and takeout. Location 1 80 seats, location 2 60 seats. Beer and wine, no liquor license.",
    38, "$2,640,000 (combined)", "$690,000 loc 1 / $540,000 loc 2 (total $1,230,000)", "$240,000 combined",
    "6,300 loc 1 / 4,900 loc 2", "Joisted masonry (loc 1), masonry (loc 2)", "1987 (loc 1), 1999 (loc 2)", "1 both",
    "Yes at loc 1, No at loc 2",
    "Two offset smokers (wood fired, indoor vented) at each location, fryers, flat-top, Type I hoods with UL 300 at both.",
    "Carrier B, policy expiring 2027-06-01", 12, "Yes, kitchen fire 2025 (see loss run)",
    mailing="same as loc 1")
csv_file(s, [
    ["FICTIONAL", 1, "2300 Rosedale St", "Fort Worth", "76105", 690000, "Joisted masonry", 1987, 6300, "Yes", "2 smokers, fryers, flat-top, Type I hood UL 300"],
    ["FICTIONAL", 2, "6100 Camp Bowie Blvd", "Fort Worth", "76116", 540000, "Masonry", 1999, 4900, "No", "2 smokers, fryers, flat-top, Type I hood UL 300"],
])
ptext(s, "loss-runs.md", f"""{B_HEAD}
Insured: Smokehouse Row BBQ Co LLC
Policy term: 2023-06-01 to 2024-06-01
Policy term: 2024-06-01 to 2025-06-01
Policy term: 2025-06-01 to 2026-06-01
| Loss date | Description | Paid | Outstanding |
|---|---|---|---|
| 2025-08-02 | kitchen fire | $12,000 | $3,000 |
""")

# ---------- SUB-141 none: restaurant with full bar, TIV conflict between email and app ----------
s = "SUB-141"
write(s, "email.md", FOOT + """Subject: Ember and Oak Kitchen & Bar - Plano, eff 2/1/27

Hi, Ember and Oak is a full bar and restaurant in Plano, live music on weekends until 1. The building is around 1.4 mil I think, check the app. Prior agent is sending the loss runs when he gets them. Application attached.

Thanks, Pam Ostrander (producer)
""")
app(s, "Ember and Oak Kitchen & Bar LLC", "2027-02-01", "3400 Coit Rd", "Plano", "75075", "limited liability company",
    "commercial property and general liability, restaurant and bar",
    "Full-service restaurant and bar, 180 seats, full liquor license (TABC mixed beverage permit), live music Friday and Saturday until 1 am. Dinner and weekend brunch.",
    46, "$2,400,000", "$1,250,000", "$380,000", "6,200", "Masonry", 2006, 1, "Yes",
    "Wood-fired oven, charbroiler, two fryers, 8-burner range. Type I hood with UL 300 wet chemical suppression.",
    "Other (not named), policy expiring 2027-02-01", 9, "None known", "same as premises")
csv_file(s, [["FICTIONAL", 1, "3400 Coit Rd", "Plano", "75075", 1250000, "Masonry", 2006, 6200, "Yes",
              "wood-fired oven, charbroiler, 2 fryers, 8-burner range, Type I hood UL 300"]])

# ---------- SUB-142 none: email only (roofing contractor) ----------
s = "SUB-142"
write(s, "email.md", FOOT + """Subject: quote request - roofing co San Antonio

Hi, need a quote for Alamo Roof & Gutter Pros LLC. Roofing contractor, 5 employees, shop and yard at 2270 Fredericksburg Rd San Antonio 78201. Eff 1/1/27, GL and property for the shop. Prior carrier loss runs to follow.

Thanks, Ben Carrow (producer)
""")

# ---------- SUB-143 none: email only, Spanish ----------
s = "SUB-143"
write(s, "email.md", FOOT + """Subject: cotizacion tienda El Paso

Hola, soy Teresa Ocampo, duena de Sol y Luna Boutique, tienda de ropa en El Paso, 1204 Mesa St, El Paso TX 79901. Tengo 3 empleados. Quiero cotizacion de seguro comercial para el 1 de febrero de 2027. Les mando los documentos despues. Gracias.

Ray Osterholt (producer)
""")

# ---------- SUB-144 none: scanned application, two locations, no loss run ----------
s = "SUB-144"
write(s, "email.md", FOOT + """Subject: Westgate Pediatric Therapy - 2 offices, new to you

Hi, Westgate Pediatric is outpatient therapy, PT and speech, two offices, Round Rock and Cedar Park. Application is a scan from the office printer, sorry. They dont have loss runs from their old carrier yet, they are asking for them. Eff 3/15/27.

Thanks, Dee Halvorsen (producer)
""")
app_text_144 = """# Application (ACORD 125/140 style)

Submission: SUB-144
Named insured: Westgate Pediatric Therapy PLLC
Mailing address: same as location 1
Premises address: 2801 N Mays St, Round Rock, TX 78664 (location 1); 1250 Cypress Creek Rd, Cedar Park, TX 78613 (location 2)
Effective date: 2027-03-15
Years in business: 8
Entity type: professional limited liability company
Line of business: commercial property and general liability, office and clinic
Operations: outpatient pediatric physical and speech therapy. Treatment rooms, waiting room, offices. No overnight, no beds.
Number of employees: 24
Annual sales (gross fees, prior year): $1,850,000 combined
Building TIV: $740,000 location 1; $410,000 location 2
Business personal property: $220,000 combined
Square footage: 6,800 location 1; 4,100 location 2
Construction: Masonry (loc 1), Joisted masonry (loc 2)
Year built: 2002 (loc 1), 2015 (loc 2)
Stories: 1 both
Sprinklers: Yes at loc 1, No at loc 2
Cooking operations: None
Expiring carrier: None (new to us, prior carrier loss runs requested)
Pending or open claims: None known
Bankruptcy or cancellation in last 5 years: No
"""
scan_text(s, "application.jpg", app_text_144, "RGB")
csv_file(s, [
    ["FICTIONAL", 1, "2801 N Mays St", "Round Rock", "78664", 740000, "Masonry", 2002, 6800, "Yes", "none"],
    ["FICTIONAL", 2, "1250 Cypress Creek Rd", "Cedar Park", "78613", 410000, "Joisted masonry", 2015, 4100, "No", "none"],
])

# ---------- SUB-145 none: habitational over $5M TIV, sprinklered, senior referral ----------
s = "SUB-145"
write(s, "email.md", FOOT + """Subject: Lakeview Gardens - 40 units Amarillo, big one

Hi, Lakeview Gardens is 40 units in three buildings on Lakeview Dr in Amarillo. All sprinklered, put in new in 2019. TIV about 6.8 mil. Carrier C has them, we haven't asked for loss runs yet, will do when you say you're interested.

Thanks, Renee Batts (producer)
""")
app(s, "Lakeview Gardens Partners LP", "2027-05-01", "3300 Lakeview Dr", "Amarillo", "79106", "limited partnership",
    "commercial property and general liability, habitational",
    "Residential apartments, 40 units in three two-story buildings, long-term leases, 94 percent occupied. Pools closed for season.",
    4, "$780,000 (gross annual rents)", "$6,800,000 (three buildings)", "$120,000", "46,000", "Joisted masonry", 1994, 2,
    "Yes, full NFPA 13 system in all buildings, 2019", "None (tenant electric ranges only)",
    "Carrier C, policy expiring 2027-05-01 (loss run not yet requested)", 31)
csv_file(s, [
    ["FICTIONAL", 1, "3300 Lakeview Dr", "Amarillo", "79106", 2300000, "Joisted masonry", 1994, 15300, "Yes", "none"],
    ["FICTIONAL", 2, "3300 Lakeview Dr Bldg B", "Amarillo", "79106", 2250000, "Joisted masonry", 1994, 15400, "Yes", "none"],
    ["FICTIONAL", 3, "3300 Lakeview Dr Bldg C", "Amarillo", "79106", 2250000, "Joisted masonry", 1994, 15300, "Yes", "none"],
])

# ---------- SUB-146 none: duplicate resubmission of SUB-141 ----------
s = "SUB-146"
write(s, "email.md", FOOT + """Subject: RESEND - Ember and Oak app (first one maybe didnt go through)

Hi, resending the Ember and Oak app, I think the first one didnt go through. Same as before. Loss runs still coming from the prior agent.

Thanks, Pam Ostrander (producer)
""")
write(s, "application.md", (INBOX / "SUB-141" / "application.md").read_text(encoding="utf-8"))
(INBOX / s / "schedule.csv").write_text((INBOX / "SUB-141" / "schedule.csv").read_text(encoding="utf-8"), encoding="utf-8")
print("built")
