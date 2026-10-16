"""T-103: build SUB-154 .. SUB-173 (fictional producer submissions).

Fictional data only. Carrier-format runs follow carrier-loss-run-formats.md.
Scans are drawn with Pillow here (no import from the pipeline tree).
"""
import csv, io, os, textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

INBOX = Path("/private/tmp/claude-501/-Users-disastershubz-INSURANCE-FLOW-AI--insureflow-ai-1/a2dadbe9-4490-4eb1-a41d-cf483f97eef8/scratchpad/wt/simulation/inbox")

FOOT = "**FICTIONAL.** All businesses, people, addresses and policy numbers are made up.\n\n"
CSV_HEAD = ["source", "loc", "address", "city", "zip", "bldg_tiv", "construction", "year_built", "sq_ft", "sprinklers", "cooking"]
A_HEAD = "CARRIER A — LOSS RUN (FICTIONAL)"
B_HEAD = "Carrier B Loss History Report (fictional)"
C_HEAD = "CARRIER C | LOSS RUN | FICTIONAL"
PAPER = (248, 246, 240)

ORDER = ["named", "mailing", "premises", "eff", "years", "entity", "lob", "ops", "emp", "sales", "tiv", "bpp",
         "sqft", "constr", "yr", "stories", "spk", "cook", "expiring", "claims", "bankr"]
LABELS = {
    "en": dict(sub="Submission", named="Named insured", mailing="Mailing address", premises="Premises address",
               eff="Effective date", years="Years in business", entity="Entity type", lob="Line of business",
               ops="Operations", emp="Number of employees", sales="Annual sales", tiv="Building TIV",
               bpp="Business personal property", sqft="Square footage", constr="Construction", yr="Year built",
               stories="Stories", spk="Sprinklers", cook="Cooking operations", expiring="Expiring carrier",
               claims="Pending or open claims", bankr="Bankruptcy or cancellation in last 5 years"),
    "es": dict(sub="Submision", named="Asegurado", mailing="Direccion postal", premises="Direccion del riesgo",
               eff="Fecha efectiva", years="Anos en el negocio", entity="Tipo de entidad", lob="Linea de negocio",
               ops="Operaciones", emp="Numero de empleados", sales="Ventas anuales", tiv="TIV del edificio",
               bpp="Propiedad personal comercial", sqft="Pies cuadrados", constr="Construccion",
               yr="Ano de construccion", stories="Pisos", spk="Rociadores", cook="Operaciones de cocina",
               expiring="Aseguradora actual", claims="Reclamos pendientes o abiertos",
               bankr="Bancarrota o cancelacion en los ultimos 5 anos"),
}


def pdf_bytes(lines):
    """Typed PDF with a text layer (Courier), same writer as the earlier build."""
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


def render_app(sub, f, lang="en"):
    L = LABELS[lang]
    f = dict(f)
    f.setdefault("claims", "None known")
    f.setdefault("bankr", "No")
    f.setdefault("mailing", "same as premises")
    head = "# Application (ACORD 125/140 style)" if lang == "en" else "# Solicitud (estilo ACORD 125/140)"
    lines = [head, "", f"{L['sub']}: {sub}"]
    for k in ORDER:
        lines.append(f"{L[k]}: {f.get(k, '')}")
    return "\n".join(lines) + "\n"


def app(sub, f, lang="en"):
    text = render_app(sub, f, lang)
    write(sub, "application.md", FOOT + text)
    return text


def ptext(sub, name, text):
    write(sub, name, text)


def font(size):
    for p in ["/System/Library/Fonts/Supplemental/Courier New.ttf", "/System/Library/Fonts/Menlo.ttc"]:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def scan(sub, name, text, kind="colour", rotate=0):
    """kind: 'grey' or 'colour' writes JPEG; 'pdf' writes an image-only PDF (no text layer)."""
    lines = []
    for l in text.split("\n"):
        lines += textwrap.wrap(l, 80) or [""]
    assert len(lines) <= 50, f"{sub}/{name}: {len(lines)} lines do not fit one page"
    ink = (20, 40, 110) if kind == "colour" else (25, 25, 25)
    img = Image.new("RGB", (1275, 1650), PAPER)
    d = ImageDraw.Draw(img)
    fnt = font(22)
    y = 110
    for l in lines:
        d.text((100, y), l, fill=ink, font=fnt)
        y += 29
    img = img.filter(ImageFilter.GaussianBlur(0.6))
    if rotate:
        img = img.rotate(rotate, expand=True, fillcolor=PAPER)
    path = INBOX / sub / name
    path.parent.mkdir(exist_ok=True)
    if kind == "grey":
        img.convert("L").save(path, "JPEG", quality=80)
    elif kind == "pdf":
        img.convert("RGB").save(path, "PDF", resolution=150)
    else:
        img.convert("RGB").save(path, "JPEG", quality=80)


def ptable(sub, name, lines):
    write(sub, name, "\n".join(lines) + "\n")


def carrier_a(insured, periods, valued, rows=None, nocl=False):
    out = [A_HEAD, f"Named insured: {insured}"] + [f"Policy period: {p}" for p in periods]
    if valued:
        out.append(f"Valued as of: {valued}")
    if nocl:
        out.append("No claims reported by Carrier A for the policy periods above.")
    else:
        out += ["| Date of loss | Cause | Paid | Reserve | Status |", "|---|---|---|---|---|"] + rows
    return out


def carrier_b(insured, terms, valued, rows):
    out = [B_HEAD, f"Insured: {insured}"] + [f"Policy term: {t}" for t in terms]
    if valued:
        out.append(f"Valuation date: {valued}")
    return out + ["| Loss date | Description | Paid | Outstanding |", "|---|---|---|---|"] + rows


def carrier_c(account, term, valued, rows):
    out = [C_HEAD, f"Account: {account}", f"Term: {term}"]
    if valued:
        out.append(f"Valued: {valued}")
    return out + ["| Claim no. | Loss date | Type | Paid | Open reserve |", "|---|---|---|---|---|"] + rows


def pdf_lines_to_file(sub, lines):
    (INBOX / sub / "loss-runs.pdf").write_bytes(pdf_bytes(lines))


def to_text(lines):
    return "\n".join(lines) + "\n"


# =====================================================================
# Files 1-8: complete applications with a carrier-format loss run
# =====================================================================

# ---- SUB-154 (file 1): office, Carrier A typed PDF with a claims table ----
s = "SUB-154"
write(s, "email.md", FOOT + """Subject: Hollis & Varga Tax Advisory - moving to you 3/1

Hi, Hollis and Varga is a small tax and bookkeeping office on Elm St in Dallas. Carrier A is up about 22 percent at renewal so the owner wants other quotes. Loss run from A attached as a pdf, they had one roof leak claim in fall.

Thanks, Walt Greenway (producer)
""")
app(s, dict(named="Hollis & Varga Tax Advisory LLC", premises="2210 Elm St, Dallas, TX 75201", eff="2027-03-01",
            years=14, entity="limited liability company", lob="commercial property and general liability, office",
            ops="Tax preparation and bookkeeping office, 2nd floor. Clients by appointment. No inventory, no goods held for sale.",
            emp=8, sales="$940,000 (gross fees, prior year)", tiv="$980,000", bpp="$72,000", sqft="3,800",
            constr="Masonry non-combustible", yr=1984, stories=3, spk="Yes", cook="None",
            expiring="Carrier A, policy expiring 2027-03-01"))
csv_file(s, [["FICTIONAL", 1, "2210 Elm St", "Dallas", "75201", 980000, "Masonry non-combustible", 1984, 3800, "Yes", "none"]])
pdf_lines_to_file(s, carrier_a("Hollis & Varga Tax Advisory LLC",
                               ["2024-03-01 to 2025-03-01", "2025-03-01 to 2026-03-01"], "2026-09-30",
                               ["| 2025-10-03 | roof leak | $6,800 | $0 | closed |"]))

# ---- SUB-155 (file 2): dry retail, Carrier A typed .md with Carrier A's no-claims line ----
s = "SUB-155"
write(s, "email.md", FOOT + """Subject: Plains Home & Candle - Lubbock, eff 2/1/27

Hey, Plains Home is a candle and home decor shop on Ave Q in Lubbock. Been with A since they opened, we are shopping because A wants a big increase. A loss run is attached, they never had a claim.

Thanks, Marisol Tate (producer)
""")
app(s, dict(named="Plains Home & Candle Co LLC", premises="1615 Ave Q, Lubbock, TX 79401", eff="2027-02-01",
            years=6, entity="limited liability company", lob="commercial property and general liability, retail",
            ops="Dry retail gift shop: candles, home decor, greeting cards, frames. No food, no alcohol, no repackaging.",
            emp=5, sales="$610,000", tiv="$520,000", bpp="$118,000", sqft="2,900", constr="Masonry", yr=1981,
            stories=1, spk="No", cook="None", expiring="Carrier A, policy expiring 2027-02-01"))
csv_file(s, [["FICTIONAL", 1, "1615 Ave Q", "Lubbock", "79401", 520000, "Masonry", 1981, 2900, "No", "none"]])
ptext(s, "loss-runs.md", to_text(carrier_a("Plains Home & Candle Co LLC",
                                           ["2024-02-01 to 2025-02-01", "2025-02-01 to 2026-02-01"], "2026-09-30",
                                           nocl=True)))

# ---- SUB-156 (file 3): restaurant, Carrier B typed PDF, no alcohol ----
s = "SUB-156"
write(s, "email.md", FOOT + """Subject: Sunny Side Grill - San Marcos, B to you

Hi, Sunny Side Grill is a breakfast and lunch restaurant in San Marcos, counter service, 48 seats. They're with B now, B loss run attached as pdf. One grease fire last winter, closed out and paid. No liquor, they don't even sell beer.

Thanks, Hope Lansing (producer)
""")
app(s, dict(named="Sunny Side Grill LLC", premises="620 N LBJ Dr, San Marcos, TX 78666", eff="2027-01-15",
            years=9, entity="limited liability company", lob="commercial property and general liability, restaurant",
            ops="Restaurant. Breakfast and lunch counter service, 48 seats, dine-in and takeout. No alcohol of any kind.",
            emp=14, sales="$860,000", tiv="$430,000", bpp="$96,000", sqft="2,700", constr="Masonry", yr=1989,
            stories=1, spk="Yes", cook="Flat-top, 2 fryers, 4-burner range, Type I hood with UL 300 suppression, hood cleaned 2026-07",
            expiring="Carrier B, policy expiring 2027-01-15"))
csv_file(s, [["FICTIONAL", 1, "620 N LBJ Dr", "San Marcos", "78666", 430000, "Masonry", 1989, 2700, "Yes",
              "flat-top, 2 fryers, 4-burner range, Type I hood UL 300"]])
pdf_lines_to_file(s, carrier_b("Sunny Side Grill LLC",
                               ["2023-01-15 to 2024-01-15", "2024-01-15 to 2025-01-15", "2025-01-15 to 2026-01-15",
                                "2026-01-15 to 2027-01-15"], "2026-09-30",
                               ["| 2024-12-03 | grease fire | $4,800 | $0 |"]))

# ---- SUB-157 (file 4): restaurant and bar, full liquor, Carrier B typed .md ----
s = "SUB-157"
write(s, "email.md", FOOT + """Subject: Rio Bend Kitchen & Bar - San Antonio renewal, shopping

Hi, Rio Bend is a restaurant and bar on the river walk side of town, full liquor, live music Thu-Sun. Carrier B renewal came in high. Loss run from B is pasted in the attachment. Walk-in cooler compressor went out in April, paid, closed.

Thanks, Connor Yates (producer)
""")
app(s, dict(named="Rio Bend Kitchen & Bar LLC", premises="210 Losoya St, San Antonio, TX 78205", eff="2027-02-01",
            years=11, entity="limited liability company", lob="commercial property and general liability, restaurant and bar",
            ops="Restaurant and bar. Full liquor (TABC mixed beverage permit), 140 seats, live music Thursday to Sunday until midnight. Dinner service and weekend brunch.",
            emp=32, sales="$2,350,000", tiv="$1,180,000", bpp="$310,000", sqft="5,600", constr="Joisted masonry", yr=1931,
            stories=2, spk="Yes, wet pipe throughout", cook="Charbroiler, 2 fryers, flat-top, 8-burner range, pizza oven. Type I hood with UL 300 system, serviced 2026-08.",
            expiring="Carrier B, policy expiring 2027-02-01"))
csv_file(s, [["FICTIONAL", 1, "210 Losoya St", "San Antonio", "78205", 1180000, "Joisted masonry", 1931, 5600, "Yes",
              "charbroiler, 2 fryers, flat-top, 8-burner range, pizza oven, Type I hood UL 300"]])
ptext(s, "loss-runs.md", to_text(carrier_b("Rio Bend Kitchen & Bar LLC",
                                           ["2023-02-01 to 2024-02-01", "2024-02-01 to 2025-02-01", "2025-02-01 to 2026-02-01",
                                            "2026-02-01 to 2027-02-01"], "2026-09-30",
                                           ["| 2025-04-09 | walk-in cooler compressor failure | $2,900 | $0 |"])))

# ---- SUB-158 (file 5): apartments, sprinklered, TIV under $5M, Carrier C typed PDF ----
s = "SUB-158"
write(s, "email.md", FOOT + """Subject: Garden Row Apartments - Waco, C renewal to you

Hi, Garden Row is a 16 unit apartment complex in Waco, two buildings, fully sprinklered. Owner is Garden Row Apartments LLC. Carrier C is the carrier now, renewal is 5/1 and they want a rate cut or they leave. Loss run from C attached.

Thanks, Lydia Frumm (producer)
""")
app(s, dict(named="Garden Row Apartments LLC", premises="1400 Franklin Ave, Waco, TX 76701", eff="2027-05-01",
            years=10, entity="limited liability company", lob="commercial property and general liability, habitational",
            ops="Residential apartments, 16 units in two two-story buildings, long-term leases. Occupancy 93 percent.",
            emp=2, sales="$288,000 (gross annual rents)", tiv="$2,350,000", bpp="$25,000", sqft="14,200",
            constr="Wood frame with masonry veneer", yr=2001, stories=2, spk="Yes, NFPA 13 system",
            cook="None (tenant electric ranges only)", expiring="Carrier C, policy expiring 2027-05-01"))
csv_file(s, [["FICTIONAL", 1, "1400 Franklin Ave", "Waco", "76701", 2350000, "Wood frame with masonry veneer", 2001, 14200, "Yes", "none"]])
pdf_lines_to_file(s, carrier_c("Garden Row Apartments LLC", "2025-05-01 - 2026-05-01", "2026-09-30",
                               ["| C-1190 | 2025-09-05 | water damage | $6,750 | $0 |"]))

# ---- SUB-159 (file 6): cafe / bakery, Carrier B JPG greyscale scan ----
s = "SUB-159"
write(s, "email.md", FOOT + """Subject: Crumb & Cup Bakery Cafe - SA, B account

Hi, Crumb and Cup is a bakery and cafe on Broadway in San Antonio, 30 seats inside. Carrier B is the carrier. Their loss run is a scan, the B portal only lets me print it. Oven fire in June, closed.

Thanks, Abel Quintero (producer)
""")
app(s, dict(named="Crumb & Cup Bakery Cafe LLC", premises="2640 Broadway St, San Antonio, TX 78215", eff="2027-03-15",
            years=5, entity="limited liability company", lob="commercial property and general liability, restaurant",
            ops="Bakery and cafe. Pastries, sandwiches, coffee. 30 seats, dine-in and takeout. No alcohol sold.",
            emp=9, sales="$540,000", tiv="$310,000", bpp="$88,000", sqft="2,200", constr="Masonry", yr=1960,
            stories=1, spk="Yes", cook="Deck oven, 2 convection ovens, 4-burner range, flat-top, Type I hood with UL 300",
            expiring="Carrier B, policy expiring 2027-03-15"))
csv_file(s, [["FICTIONAL", 1, "2640 Broadway St", "San Antonio", "78215", 310000, "Masonry", 1960, 2200, "Yes",
              "deck oven, 2 convection ovens, 4-burner range, flat-top, Type I hood UL 300"]])
scan(s, "loss-runs.jpg", to_text(carrier_b("Crumb & Cup Bakery Cafe LLC",
                                           ["2023-03-15 to 2024-03-15", "2024-03-15 to 2025-03-15", "2025-03-15 to 2026-03-15"],
                                           "2026-09-30", ["| 2025-06-22 | oven fire | $5,200 | $0 |"])).rstrip("\n"),
     kind="grey")

# ---- SUB-160 (file 7): apartments, not sprinklered, Carrier C JPG colour, rotated ----
s = "SUB-160"
write(s, "email.md", FOOT + """Subject: Alder Park Apartments - Killeen, C account

Hi, Alder Park is 8 units in Killeen, two small buildings, older wood frame. No sprinklers, owner never put them in. Carrier C has them. Loss run from C is a scan, sideways, sorry. Eff 4/1/27.

Thanks, Connor Yates (producer)
""")
app(s, dict(named="Alder Park Apartments LLC", premises="905 Alder Park Dr, Killeen, TX 76541", eff="2027-04-01",
            years=18, entity="limited liability company", lob="commercial property and general liability, habitational",
            ops="Residential apartments, 8 units in two two-story buildings, long-term leases. Occupancy 88 percent.",
            emp=1, sales="$158,000 (gross annual rents)", tiv="$860,000", bpp="$12,000", sqft="7,100",
            constr="Wood frame", yr=1972, stories=2, spk="No", cook="None (tenant electric ranges only)",
            expiring="Carrier C, policy expiring 2027-04-01"))
csv_file(s, [["FICTIONAL", 1, "905 Alder Park Dr", "Killeen", "76541", 860000, "Wood frame", 1972, 7100, "No", "none"]])
scan(s, "loss-runs.jpg", to_text(carrier_c("Alder Park Apartments LLC", "2025-04-01 - 2026-04-01", "2026-09-30",
                                           ["| C-1215 | 2025-12-14 | wind/hail | $4,300 | $0 |"])).rstrip("\n"),
     kind="colour", rotate=90)

# ---- SUB-161 (file 8): light wholesale, goods not hazardous, Carrier A image-only PDF ----
s = "SUB-161"
write(s, "email.md", FOOT + """Subject: Gulf Plains Hardware Wholesale - Houston, A to you

Hi, Gulf Plains is a wholesale distributor, home goods, kitchenware and small hand tools, sells to stores across Texas. Big warehouse off 59. A is the carrier now and they are pushing a big increase at 4/1. Loss run from A attached, it's a scan of the printout.

Thanks, Walt Greenway (producer)
""")
app(s, dict(named="Gulf Plains Hardware Wholesale LLC", premises="8800 Sam Houston Pkwy E, Houston, TX 77049",
            eff="2027-04-01", years=12, entity="limited liability company",
            lob="commercial property and general liability, light wholesale",
            ops="Light wholesale of home goods, kitchenware and small hand tools to retail stores. Goods are not hazardous: no flammable liquids, no aerosols, no pesticides, no batteries. Warehouse with loading dock, no repackaging.",
            emp=21, sales="$4,100,000", tiv="$2,050,000", bpp="$640,000", sqft="38,000", constr="Tilt-up concrete",
            yr=1998, stories=1, spk="Yes, ESFR sprinklers", cook="None",
            expiring="Carrier A, policy expiring 2027-04-01"))
csv_file(s, [["FICTIONAL", 1, "8800 Sam Houston Pkwy E", "Houston", "77049", 2050000, "Tilt-up concrete", 1998, 38000, "Yes", "none"]])
scan(s, "loss-runs.pdf", to_text(carrier_a("Gulf Plains Hardware Wholesale LLC",
                                           ["2024-04-01 to 2025-04-01", "2025-04-01 to 2026-04-01"], "2026-09-30",
                                           ["| 2025-05-27 | theft from warehouse | $2,200 | $0 | closed |"])).rstrip("\n"),
     kind="pdf")

# =====================================================================
# Files 9-14: a gap or an unclear loss run
# =====================================================================

# ---- SUB-162 (file 9): office, English no-known-loss letter ----
s = "SUB-162"
write(s, "email.md", FOOT + """Subject: Ellison Bookkeeping & Payroll - Plano, new to commercial

Hi, Ellison Bookkeeping is a payroll and bookkeeping office in Plano, 6 staff, one suite. Dana Ellison is the owner, she was with a personal lines agent before. Eff 3/1/27. She wrote the no loss letter herself, hope thats ok.

Thanks, Lydia Frumm (producer)
""")
app(s, dict(named="Ellison Bookkeeping & Payroll PLLC", premises="5900 W Plano Pkwy, Plano, TX 75093", eff="2027-03-01",
            years=7, entity="professional limited liability company", lob="commercial property and general liability, office",
            ops="Bookkeeping and payroll services, one office suite, clients by appointment and online. No inventory.",
            emp=6, sales="$720,000", tiv="$310,000", bpp="$64,000", sqft="2,400", constr="Masonry", yr=1999,
            stories=1, spk="Yes", cook="None", expiring="Other (prior personal lines policy), policy ends 2027-03-01"))
csv_file(s, [["FICTIONAL", 1, "5900 W Plano Pkwy", "Plano", "75093", 310000, "Masonry", 1999, 2400, "Yes", "none"]])
ptext(s, "loss-runs.md", """To whom it may concern,

I, Dana Ellison, owner of Ellison Bookkeeping & Payroll PLLC, state that the business has had no insurance claims or losses in the last five years, to my knowledge. No fire, no water damage, no theft and no liability claims were made.

Date: 2026-09-27
Signed: Dana Ellison
""")

# ---- SUB-163 (file 10): Spanish application, restaurant with cooking line, Spanish no-loss letter ----
s = "SUB-163"
write(s, "email.md", FOOT + """Subject: Cenaduria Los Abuelos - Harlingen, nuevo con nosotros

Hola, Cenaduria Los Abuelos es un restaurante familiar en Harlingen, 60 asientos, cerveza y vino, sin barra. El dueno Ruben Salinas no habla mucho ingles, por eso la solicitud va en espanol. Su agente se jubilo, no hay loss run de aseguradora. Carta de no reclamos adjunta. Vigencia 2/15/27.

Gracias, Hope Lansing (productora)
""")
text_es = render_app(s, dict(named="Cenaduria Los Abuelos LLC", premises="510 E Harrison Ave, Harlingen, TX 78550",
                             eff="2027-02-15", years=13,
                             entity="sociedad de responsabilidad limitada",
                             lob="propiedad comercial y responsabilidad general, restaurante",
                             ops="Restaurante familiar de cocina mexicana. 60 asientos, cerveza y vino, sin barra. Servicio en mesa y para llevar.",
                             emp=9, sales="$710,000", tiv="$390,000", bpp="$84,000", sqft="2,600",
                             constr="Mamposteria", yr=1986, stories=1, spk="No",
                             cook="Comal, parrilla, 2 freidoras, estufa de 6 quemadores. Campana tipo I con sistema UL 300, limpieza 2026-06.",
                             expiring="No indicada (agente anterior), poliza vence 2027-02-15"), "es")
write(s, "application.md", FOOT + text_es)
csv_file(s, [["FICTIONAL", 1, "510 E Harrison Ave", "Harlingen", "78550", 390000, "Mamposteria", 1986, 2600, "No",
              "comal, parrilla, 2 freidoras, estufa 6 quemadores, campana tipo I UL 300"]])
ptext(s, "loss-runs.md", """Declaracion de no reclamos

Yo, Ruben Salinas, dueno de Cenaduria Los Abuelos LLC, declaro que en los ultimos cinco anos el negocio no ha tenido reclamos de seguro ni perdidas que yo conozca. No hemos tenido incendios, danos por agua ni robos reportados.

Fecha: 2026-09-24
Firma: Ruben Salinas
""")

# ---- SUB-164 (file 11): roofing contractor, states building TIV; applicant note under copied Carrier A header ----
s = "SUB-164"
write(s, "email.md", FOOT + """Subject: Fwd: Gulf Shore Roofing - corpus, eff 1/1/27

Hi, Gulf Shore Roofing is a residential and commercial roofing contractor in Corpus, 11 crew. Shop and yard on Leopard St. Their A loss run, the owner typed up his own note under the header because A's portal was down. See the file.

Thanks, Walt Greenway (producer)
""")
app(s, dict(named="Gulf Shore Roofing LLC", premises="2715 Leopard St, Corpus Christi, TX 78404", eff="2027-01-01",
            years=8, entity="limited liability company", lob="commercial property and general liability, roofing contractor",
            ops="Roofing contractor, residential and commercial re-roofing and repair. Shop and yard on premises, materials stored outside under tarps, torch-down work on some jobs.",
            emp=11, sales="$2,180,000", tiv="$240,000", bpp="$155,000", sqft="6,300", constr="Metal frame, metal siding",
            yr=2008, stories=1, spk="No", cook="None", expiring="Carrier A, policy expiring 2027-01-01"))
csv_file(s, [["FICTIONAL", 1, "2715 Leopard St", "Corpus Christi", "78404", 240000, "Metal frame, metal siding", 2008, 6300, "No", "none"]])
ptext(s, "loss-runs.md", """Fwd: CARRIER A — LOSS RUN (FICTIONAL)
> Named insured: Gulf Shore Roofing LLC
> Policy period: 2025-01-01 to 2026-01-01
> Valued as of: 2026-09-30
>
Hi, we had no claims with A this term. Nothing was filed. One hail dent on a box truck, we paid that ourselves out of pocket.
Losses are valued as of 2026-09-30 from our own books, not from A.
Thanks, Eduardo Salas, owner
""")

# ---- SUB-165 (file 12): prohibited class (fireworks seller); agency summary naming a carrier ----
s = "SUB-165"
write(s, "email.md", FOOT + """Subject: Boom Town Fireworks - Waco, seasonal + storefront

Hi, Boom Town is a fireworks seller, storefront on Hwy 84 plus a seasonal tent June and July. They want GL and property on the storefront. Previous carrier was C, they had a couple small claims, summary from our system attached. Eff 3/15/27.

Thanks, Walt Greenway (producer)
""")
app(s, dict(named="Boom Town Fireworks LLC", premises="4415 Hwy 84 E, Waco, TX 76708", eff="2027-03-15",
            years=4, entity="limited liability company", lob="commercial property and general liability, retail",
            ops="Retail sale of consumer fireworks (aerial, ground and cakes), storefront and seasonal tent. Fireworks inventory stored on premises, including in a trailer on the lot.",
            emp=7, sales="$640,000", tiv="$350,000", bpp="$410,000", sqft="3,000", constr="Metal frame, metal siding",
            yr=1995, stories=1, spk="No", cook="None", expiring="Carrier C, policy expiring 2027-03-15"))
csv_file(s, [["FICTIONAL", 1, "4415 Hwy 84 E", "Waco", "76708", 350000, "Metal frame, metal siding", 1995, 3000, "No", "none"]])
ptext(s, "loss-runs.md", """AGENCY SUMMARY - NOT A CARRIER LOSS RUN (FICTIONAL)
Account: Boom Town Fireworks LLC
Prepared by: Walt Greenway, agency
Prepared: 2026-09-25
Per our agency system, Carrier C shows 2 small claims for this account, 2023 and 2024, both closed.
Carrier C printout not attached. Summary only, from agency records.
""")

# ---- SUB-166 (file 13): office, building TIV over $5M; applicant note as JPG under copied Carrier B header ----
s = "SUB-166"
write(s, "email.md", FOOT + """Subject: Pinecrest Office Holdings - Houston, 2-story office bldg

Hi, Pinecrest Office Holdings owns a 2-story office building in Houston, owner occupies the first floor, two tenants upstairs. Big one, the building value is high. Loss run is a photo of the B printout with the owner's note on it, Carol typed the note. Eff 4/1/27.

Thanks, Hope Lansing (producer)
""")
app(s, dict(named="Pinecrest Office Holdings LLC", premises="1200 Westheimer Rd, Houston, TX 77024", eff="2027-04-01",
            years=16, entity="limited liability company", lob="commercial property and general liability, office",
            ops="Owner-occupied two-story office building. Insured occupies first floor for its own office, two tenants on second floor, office use only. No retail, no food.",
            emp=4, sales="$1,250,000 (gross rents)", tiv="$5,850,000", bpp="$95,000", sqft="18,400",
            constr="Masonry non-combustible", yr=1992, stories=2, spk="Yes, wet pipe throughout",
            cook="None", expiring="Carrier B, policy expiring 2027-04-01"))
csv_file(s, [["FICTIONAL", 1, "1200 Westheimer Rd", "Houston", "77024", 5850000, "Masonry non-combustible", 1992, 18400, "Yes", "none"]])
scan(s, "loss-runs.jpg", """Carrier B Loss History Report (fictional)
Insured: Pinecrest Office Holdings LLC
Policy term: 2025-04-01 to 2026-04-01
Valuation date: 2026-09-30

Note from insured (typed by me, Carol Ing, manager):
Hi, we had one water claim this term, the roof leak over suite 2B in March. We paid the repair ourselves under the deductible and nothing was filed with B after that. Hope this helps, thanks.""",
     kind="colour")

# ---- SUB-167 (file 14): apartments, sprinkler question not answered; Carrier C layout missing valued line ----
s = "SUB-167"
write(s, "email.md", FOOT + """Subject: Mesquite Court Apartments - Abilene, C to you

Hi, Mesquite Court is 24 units in Abilene, three buildings. Carrier C is the carrier, their renewal is up. Loss run from C attached. Owner says the sprinklers thing on the app, I didnt get an answer from him yet. Eff 7/1/27.

Thanks, Connor Yates (producer)
""")
app(s, dict(named="Mesquite Court Apartments LP", premises="3350 Mesquite Dr, Abilene, TX 79605", eff="2027-07-01",
            years=15, entity="limited partnership", lob="commercial property and general liability, habitational",
            ops="Residential apartments, 24 units in three two-story buildings, long-term leases. Occupancy 90 percent.",
            emp=2, sales="$402,000 (gross annual rents)", tiv="$1,640,000", bpp="$30,000", sqft="21,600",
            constr="Wood frame with masonry veneer", yr=1985, stories=2, spk="",
            cook="None (tenant electric ranges only)", expiring="Carrier C, policy expiring 2027-07-01"))
csv_file(s, [["FICTIONAL", 1, "3350 Mesquite Dr", "Abilene", "79605", 1640000, "Wood frame with masonry veneer", 1985, 21600, "", "none"]])
ptext(s, "loss-runs.md", to_text(carrier_c("Mesquite Court Apartments LP", "2025-07-01 - 2026-07-01", None,
                                           ["| C-1203 | 2026-02-14 | wind/hail | $5,100 | $0 |"])))

# =====================================================================
# Files 15-20: none (email only, scanned app, duplicate, no loss run)
# =====================================================================

# ---- SUB-168 (file 15): email only, operations not stated, no loss run ----
s = "SUB-168"
write(s, "email.md", FOOT + """Subject: new one - Cobble Creek Holdings, Wichita Falls

Hi, new one: Cobble Creek Holdings LLC, 800 Eighth St Wichita Falls 76301, 7 employees on site. Eff 4/1/27. Prior carrier is B. Need GL and property. Ill send the app once the owner gets back to me, and loss runs from B when I have them.

Thanks, Connor Yates (producer)
""")

# ---- SUB-169 (file 16): Spanish email only, operations stated, no loss run ----
s = "SUB-169"
write(s, "email.md", FOOT + """Subject: cotizacion lavanderia Pharr

Hola, les escribo por Lavanderia Burbuja, lavanderia de autoservicio en Pharr TX. 14 lavadoras y 8 secadoras de gas, los clientes lavan su propia ropa, no hacemos planchado comercial ni servicio a domicilio. Eff 5/1/27. Les mando la solicitud despues y las loss runs de la aseguradora anterior.

Gracias, Abel Quintero (productor)
""")

# ---- SUB-170 (file 17): scanned application JPG, 2 locations, restaurant; one TIV conflicts with schedule ----
s = "SUB-170"
app170 = render_app(s, dict(named="Bluebonnet Kitchen Co LLC",
                            mailing="same as location 1",
                            premises="4808 Slide Rd, Lubbock, TX 79414 (loc 1); 2200 N Judge Ely Blvd, Abilene, TX 79601 (loc 2)",
                            eff="2027-03-01", years=6, entity="limited liability company",
                            lob="commercial property and general liability, restaurant, 2 locations",
                            ops="Restaurant, 2 locations. Burgers, chicken and breakfast, dine-in and takeout. Beer and wine, no liquor license.",
                            emp=36, sales="$3,300,000 combined", tiv="$1,040,000 loc 1; $465,000 loc 2",
                            bpp="$260,000 combined", sqft="4,900 loc 1; 3,600 loc 2",
                            constr="Masonry (loc 1), Metal (loc 2)", yr="2004 (loc 1), 1998 (loc 2)", stories="1 both",
                            spk="Yes at loc 1, No at loc 2",
                            cook="Flat-top, 2 fryers, charbroiler, 8-burner range. Type I hood with UL 300 at both locations.",
                            expiring="Carrier B, policy expiring 2027-03-01"))
write(s, "email.md", FOOT + """Subject: Bluebonnet Kitchen Co - 2 spots, Lubbock and Abilene

Hi, Bluebonnet Kitchen has two burger and chicken places, Lubbock and Abilene. Application is a scan of their paper form, sorry it's crooked. Beer and wine only. B is the carrier now, loss runs coming from them, they are slow. Eff 3/1/27.

Thanks, Marisol Tate (producer)
""")
scan(s, "application.jpg", app170, kind="colour")
csv_file(s, [
    ["FICTIONAL", 1, "4808 Slide Rd", "Lubbock", "79414", 1040000, "Masonry", 2004, 4900, "Yes",
     "flat-top, 2 fryers, charbroiler, 8-burner range, Type I hood UL 300"],
    ["FICTIONAL", 2, "2200 N Judge Ely Blvd", "Abilene", "79601", 546000, "Metal", 1998, 3600, "No",
     "flat-top, 2 fryers, charbroiler, 8-burner range, Type I hood UL 300"],
])

# ---- SUB-171 (file 18): resend of file 4's application (SUB-157), no loss run ----
s = "SUB-171"
write(s, "email.md", FOOT + """Subject: RESEND - Rio Bend app (first one maybe didnt go through)

Hi, resending the Rio Bend app, I think the first one didnt go through. Same as before. Loss run from B is with the other email.

Thanks, Connor Yates (producer)
""")
write(s, "application.md", (INBOX / "SUB-157" / "application.md").read_text(encoding="utf-8"))
(INBOX / s / "schedule.csv").write_text((INBOX / "SUB-157" / "schedule.csv").read_text(encoding="utf-8"), encoding="utf-8")

# ---- SUB-172 (file 19): 3-location schedule, sprinklered apartments, no loss run ----
s = "SUB-172"
write(s, "email.md", FOOT + """Subject: Cypress Pointe Apartments - 3 properties, eff 6/1/27

Hi, Cypress Pointe is three apartment properties, Denton, Killeen and Waco. All sprinklered, all built in the 2010s. Units total 30. Schedule is attached with the building values. Ill get the loss runs from the carrier.

Thanks, Hope Lansing (producer)
""")
app(s, dict(named="Cypress Pointe Apartments LLC", mailing="same as location 1",
            premises="1100 Cypress Pointe Dr, Denton, TX 76205 (loc 1); 2450 Trimmier Rd, Killeen, TX 76542 (loc 2); 710 Lake Air Dr, Waco, TX 76710 (loc 3)",
            eff="2027-06-01", years=9, entity="limited liability company",
            lob="commercial property and general liability, habitational, 3 locations",
            ops="Residential apartments, 3 properties, 30 units total, long-term leases. Occupancy 95 percent.",
            emp=3, sales="$612,000 (gross annual rents, combined)", tiv="$1,380,000 (combined, see schedule)",
            bpp="$28,000 combined", sqft="27,500 combined", constr="Wood frame with masonry veneer",
            yr="2012 (loc 1), 2015 (loc 2), 2017 (loc 3)", stories="2 all", spk="Yes, NFPA 13 at all 3 locations",
            cook="None (tenant electric ranges only)", expiring="Other (new carrier needed, prior expires 2027-06-01)"))
csv_file(s, [
    ["FICTIONAL", 1, "1100 Cypress Pointe Dr", "Denton", "76205", 520000, "Wood frame with masonry veneer", 2012, 11200, "Yes", "none"],
    ["FICTIONAL", 2, "2450 Trimmier Rd", "Killeen", "76542", 470000, "Wood frame with masonry veneer", 2015, 9600, "Yes", "none"],
    ["FICTIONAL", 3, "710 Lake Air Dr", "Waco", "76710", 390000, "Wood frame with masonry veneer", 2017, 6700, "Yes", "none"],
])

# ---- SUB-173 (file 20): restaurant named only by a cuisine word; no cooking line ----
s = "SUB-173"
write(s, "email.md", FOOT + """Subject: Los Primos Taqueria - Brownsville, new to us

Hi, our taqueria on Boca Chica Blvd is Los Primos, owner is Abel Quintero's cousin, Jorge. 35 seats, counter service, no beer or liquor. Current policy ends 2/1/27. Application attached. Loss runs from the old agent are coming.

Thanks, Lydia Frumm (producer)
""")
app(s, dict(named="Los Primos Taqueria LLC", premises="2310 Boca Chica Blvd, Brownsville, TX 78521",
            eff="2027-02-01", years=5, entity="limited liability company",
            lob="commercial property and general liability, retail food",
            ops="Counter service. Tacos, burritos, quesadillas and agua fresca, 35 seats, dine-in and takeout. No liquor.",
            emp=6, sales="$430,000", tiv="$210,000", bpp="$55,000", sqft="1,900", constr="Masonry", yr=1975,
            stories=1, spk="No", cook="not listed", expiring="Other (prior agent, policy expiring 2027-02-01)"))
csv_file(s, [["FICTIONAL", 1, "2310 Boca Chica Blvd", "Brownsville", "78521", 210000, "Masonry", 1975, 1900, "No", ""]])

# =====================================================================
# Count check (file -> folder), printed for the report
# =====================================================================
if __name__ == "__main__":
    exp = {f"SUB-{153 + n}": n for n in range(1, 21)}
    for sub in sorted(exp):
        d = INBOX / sub
        names = sorted(p.name for p in d.iterdir())
        print(sub, exp[sub], names)
