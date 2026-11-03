"""Builds SUB-510 to SUB-541 (T-121 hold-out inbox): 20 in scope (510-529), 12 out of scope (530-541).
Out of scope: criterion 1 = 530-531, criterion 2 = 532-537 (534-537 words only, no second street address), 3 = 538-539, 4 = 540-541.
Scope rule (P-077, D-146, D-149): a different premises street address in any document, or a second store/branch/shop in words
(incl. a sold or closed one), is out of scope. Near-misses that stay in scope: 527 "two floors", 528 "2nd floor", 529 "two entrances".
Reuses the typed/scan helpers of the T-108 and T-117 builders by import only. Writes simulation/inbox/SUB-510..541 and nothing else.
Idempotent: removes and rebuilds only SUB-510..SUB-541.
Run: .venv/bin/python simulation/inbox/build_SUB-510-541.py"""
import importlib.util
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, fname):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


O = _load("b_226", "build_SUB-226-237.py")
A = _load("b_206", "build_SUB-206-225.py")
FONT = O.FONT_SANS


def app(**k):
    names = {
        "named": "Named insured", "mail": "Mailing address", "prem": "Premises address",
        "eff": "Effective date", "yrs": "Years in business", "entity": "Entity type",
        "lob": "Line of business", "ops": "Operations", "emp": "Number of employees",
        "sales": "Annual sales", "tiv": "Building TIV", "bpp": "Business personal property",
        "sqft": "Square footage", "constr": "Construction", "yb": "Year built",
        "stories": "Stories", "spk": "Sprinklers", "cook": "Cooking operations",
        "carrier": "Expiring carrier", "claims": "Pending or open claims",
        "bk": "Bankruptcy or cancellation in last 5 years",
    }
    return {names[key]: val for key, val in k.items()}


def folder(sub):
    d = os.path.join(HERE, "SUB-%d" % sub)
    os.makedirs(d, exist_ok=True)
    return d


def email(d, subject, body):
    O.write_text(os.path.join(d, "email.md"), O.email_md(subject, body))


def app_md(d, sub, fields):
    O.write_text(os.path.join(d, "application.md"), O.app_md("SUB-%d" % sub, fields))


def app_typed_pdf(d, sub, fields):
    O.write_typed_pdf(os.path.join(d, "application.pdf"), O.app_plain_lines("SUB-%d" % sub, fields))


def app_scan(d, sub, fields):
    O.write_scan(os.path.join(d, "application_scan.jpg"), O.app_plain_lines("SUB-%d" % sub, fields), FONT)


def app_image_pdf(d, sub, fields):
    O.write_image_pdf(os.path.join(d, "application.pdf"),
                      O.scan_jpeg_bytes(O.app_plain_lines("SUB-%d" % sub, fields), FONT))


def app_spanish_pdf(d, sub, campos):
    O.write_typed_pdf(os.path.join(d, "application.pdf"), O.app_spanish_lines("SUB-%d" % sub, campos))


def app_spanish_md(d, sub, campos):
    O.write_text(os.path.join(d, "application.md"), "\n".join(O.app_spanish_lines("SUB-%d" % sub, campos)))


def loss_md(d, lines):
    O.write_text(os.path.join(d, "loss-runs.md"), "\n".join(lines))


def schedule(d, rows):
    O.schedule_csv(os.path.join(d, "schedule.csv"), rows)


def lr_c(name, terms, valued, rows):
    # Carrier C term layout is "YYYY-MM-DD - YYYY-MM-DD" (spaced hyphen), not "to"
    return A.lr_carrier_c(name, [t.replace(" to ", " - ") for t in terms], valued, rows)


def row(source, loc, address, city, zip_, tiv, constr, yb, sqft, spk, cook):
    return {"source": source, "loc": loc, "address": address, "city": city, "zip": zip_,
            "bldg_tiv": tiv, "construction": constr, "year_built": yb, "sq_ft": sqft,
            "sprinklers": spk, "cooking": cook}


def build():
    for n in range(510, 542):
        path = os.path.join(HERE, "SUB-%d" % n)
        if os.path.isdir(path):
            shutil.rmtree(path)

    # ============================================================ in scope (510-529)
    # 510 office tenant. Carrier A clean. Ops line allow-list only. Direct A.
    d = folder(510)
    email(d, "Lone Oak Accounting - renewal",
          "We rent an office in a small building on Hwy 290 in Brenham. Desks, computers and "
          "files only. Carrier A has us, loss run attached, no claims.")
    app_md(d, 510, app(named="Lone Oak Accounting LLC", mail="same as premises",
                       prem="1906 Hwy 290 W Ste 104, Brenham TX 77833", eff="2026-12-14",
                       yrs="11", entity="LLC", lob="Business owners policy",
                       ops="Office", emp="5", sales="$480,000",
                       tiv="$96,000", bpp="$58,000", sqft="1,850", constr="Masonry", yb="2003",
                       stories="1", spk="Yes", cook="None", carrier="Carrier A", claims="None",
                       bk="No"))
    loss_md(d, A.lr_carrier_a("Lone Oak Accounting LLC", ["2025-12-14 to 2026-12-14"],
                              "2026-09-15", []))

    # 511 clothing boutique, typed PDF app. Carrier A clean. Direct A.
    d = folder(511)
    email(d, "Bluestem Boutique - Nacogdoches",
          "Clothing boutique on North Street in Nacogdoches, dresses and accessories. "
          "No claims. Carrier A loss run attached, typed app attached.")
    app_typed_pdf(d, 511, app(named="Bluestem Boutique LLC", mail="same as premises",
                              prem="3010 North St, Nacogdoches TX 75965", eff="2026-12-18",
                              yrs="5", entity="LLC", lob="Business owners policy",
                              ops="Clothing boutique", emp="4", sales="$410,000",
                              tiv="$132,000", bpp="$96,000", sqft="2,200", constr="Masonry",
                              yb="1986", stories="1", spk="No", cook="None", carrier="Carrier A",
                              claims="None", bk="No"))
    loss_md(d, A.lr_carrier_a("Bluestem Boutique LLC", ["2025-12-18 to 2026-12-18"],
                              "2026-08-24", []))

    # 512 dry goods retail store, md app. Carrier A clean. Direct A.
    d = folder(512)
    email(d, "Pine Hollow Mercantile - Lufkin",
          "Retail store on Timberland Dr in Lufkin, dry goods on shelves and a front counter. "
          "Carrier A loss run attached, clean.")
    app_md(d, 512, app(named="Pine Hollow Mercantile LLC", mail="same as premises",
                       prem="2205 S Timberland Dr, Lufkin TX 75901", eff="2027-01-04", yrs="12",
                       entity="LLC", lob="Business owners policy", ops="Dry goods retail store",
                       emp="6", sales="$520,000", tiv="$174,000", bpp="$118,000", sqft="3,900",
                       constr="Masonry", yb="1971", stories="1", spk="No", cook="None",
                       carrier="Carrier A", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_a("Pine Hollow Mercantile LLC", ["2026-01-04 to 2027-01-04"],
                              "2026-10-02", []))

    # 513 office suite tenant, typed PDF app. Carrier A clean. Direct A.
    d = folder(513)
    email(d, "Granite Shoals Consulting",
          "We lease one office suite on Marble Falls Ave, four people. Carrier A has us, nothing "
          "reported, loss run attached.")
    app_typed_pdf(d, 513, app(named="Granite Shoals Consulting LLC", mail="same as premises",
                              prem="806 Marble Falls Ave Ste 2, Granite Shoals TX 78654",
                              eff="2026-12-21", yrs="6", entity="LLC", lob="Business owners policy",
                              ops="Office suite", emp="4",
                              sales="$615,000", tiv="$78,000", bpp="$49,000", sqft="1,300",
                              constr="Frame", yb="2009", stories="1", spk="No",
                              cook="None", carrier="Carrier A", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_a("Granite Shoals Consulting LLC", ["2025-12-21 to 2026-12-21"],
                              "2026-09-29", []))

    # 514 plumbing contractor, typed PDF app. Planted conflict: square footage (email 2,700, app 3,500).
    d = folder(514)
    email(d, "Riverbend Plumbing - square footage",
          "Plumbing contractor in Victoria, eight trucks and a shop on Port Lavaca Dr. The shop "
          "building is 2,700 square feet, we had it measured for the lease. The application says "
          "3,500, that number is wrong. Carrier B loss run attached, one truck claim.")
    app_typed_pdf(d, 514, app(named="Riverbend Plumbing Services LLC", mail="same as premises",
                              prem="4120 N Port Lavaca Dr, Victoria TX 77904", eff="2026-12-07",
                              yrs="13", entity="LLC", lob="Contractors general liability",
                              ops="Plumbing contractor, shop and yard",
                              emp="17", sales="$1,880,000", tiv="$265,000", bpp="$190,000",
                              sqft="3,500", constr="Metal", yb="1993", stories="1",
                              spk="No", cook="None", carrier="Carrier B",
                              claims="Truck mirror claim 2026, closed", bk="No"))
    loss_md(d, A.lr_carrier_b("Riverbend Plumbing Services LLC", ["2025-12-07 to 2026-12-07"],
                              "2026-08-11",
                              [["2026-02-23", "vehicle damage, service truck mirror", "$1,940", "$0"]]))

    # 515 paper goods wholesale. Planted conflict: annual sales (email "$2.35 million", app $2,080,000).
    d = folder(515)
    email(d, "Trinity Bay Paper Supply - renewal",
          "Wholesale paper and packaging goods from our warehouse on Garth Rd in Baytown. "
          "We sell boxes, wrap and bags to local businesses. Sales last year came to "
          "$2.35 million, the application shows the old budget. Carrier C run attached, no claims.")
    app_md(d, 515, app(named="Trinity Bay Paper Supply LLC", mail="same as premises",
                       prem="5530 Garth Rd, Baytown TX 77521", eff="2026-12-11", yrs="10",
                       entity="LLC", lob="Commercial property and general liability",
                       ops="Wholesale paper and packaging goods, warehouse", emp="14",
                       sales="$2,080,000", tiv="$640,000", bpp="$410,000", sqft="12,500",
                       constr="Metal", yb="2001", stories="1", spk="Yes", cook="None",
                       carrier="Carrier C", claims="None", bk="No"))
    loss_md(d, lr_c("Trinity Bay Paper Supply LLC", ["2025-12-11 to 2026-12-11"],
                    "2026-09-18", []))

    # 516 painting contractor, MISSING loss run (email says it is coming). Mailing address is a PO Box (role-labelled).
    d = folder(516)
    email(d, "Copperleaf Painting - Tyler",
          "Painting contractor, interior and exterior repaints for homes and businesses around "
          "Tyler. Six painters and three trucks. Mail goes to our PO Box. The loss run is coming "
          "from Carrier C, I asked last week. Application below.")
    app_md(d, 516, app(named="Copperleaf Painting LLC", mail="PO Box 7781, Tyler TX 75711",
                       prem="1820 W Gentry Pkwy, Tyler TX 75702", eff="2026-12-15", yrs="8",
                       entity="LLC", lob="Contractors general liability",
                       ops="Painting contractor, interior and exterior repaints", emp="8",
                       sales="$720,000", tiv="$105,000", bpp="$88,000", sqft="1,700",
                       constr="Masonry", yb="1984", stories="1", spk="No", cook="None",
                       carrier="Carrier C", claims="Unknown, loss run requested", bk="No"))

    # 517 office building lessor. Planted conflict: suite count (email 12 suites, app 11 suites).
    d = folder(517)
    email(d, "Live Oak Commons - New Braunfels",
          "Office building on Loop 337 in New Braunfels. We have 12 suites leased now, the last "
          "one went to an engineering firm in September. The app says 11, that was before the "
          "new lease. Tenants are all professional offices. Carrier C loss run attached, no claims.")
    app_md(d, 517, app(named="Live Oak Commons Office Center LLC", mail="same as premises",
                       prem="1255 N Loop 337, New Braunfels TX 78130", eff="2026-12-19", yrs="14",
                       entity="LLC", lob="Commercial property and general liability",
                       ops="Lessor of office building, 11 suites, professional tenants", emp="2",
                       sales="$742,000 (rent roll)", tiv="$1,560,000", bpp="$44,000",
                       sqft="13,200", constr="Masonry", yb="2002", stories="2",
                       spk="Yes, full", cook="None", carrier="Carrier C", claims="None", bk="No"))
    loss_md(d, lr_c("Live Oak Commons Office Center LLC", ["2025-12-19 to 2026-12-19"],
                    "2026-10-06", []))

    # 518 office building lessor. Planted conflict: floor area (email roughly 5,100, app 5,800).
    d = folder(518)
    email(d, "Kestrel Point office bldg - Midland",
          "Six suite office building on Wadley Ave in Midland, roughly 5,100 sq ft in all. "
          "Tenants are a law firm, two CPAs, a surveyor and two insurance agents. Carrier C loss "
          "run attached, nothing reported.")
    app_md(d, 518, app(named="Kestrel Point Professional Building LLC", mail="same as premises",
                       prem="3300 W Wadley Ave, Midland TX 79705", eff="2027-01-08", yrs="9",
                       entity="LLC", lob="Commercial property and general liability",
                       ops="Lessor of office building, 6 suites, professional tenants", emp="1",
                       sales="$408,000 (rent roll)", tiv="$1,120,000", bpp="$22,000",
                       sqft="5,800", constr="Masonry", yb="2014", stories="1",
                       spk="Yes, full", cook="None", carrier="Carrier C", claims="None", bk="No"))
    loss_md(d, lr_c("Kestrel Point Professional Building LLC", ["2026-01-08 to 2027-01-08"],
                    "2026-10-09", []))

    # 519 roofing contractor, Carrier B hail claim. Planted conflict: TIV (email 1,320,000, app $1,050,000).
    d = folder(519)
    email(d, "High Plains Roofing - Abilene",
          "Roofing contractor, commercial flat roofs and some homes, 19 people. Shop and a "
          "material yard. The building appraised at 1,320,000 this spring, the app still has "
          "the old value. Carrier B loss run attached, one hail claim.")
    app_md(d, 519, app(named="High Plains Roofing Co", mail="same as premises",
                       prem="4402 S 14th St, Abilene TX 79605", eff="2026-12-28",
                       yrs="16", entity="Corporation", lob="Contractors general liability",
                       ops="Roofing contractor, shop and material yard",
                       emp="19", sales="$2,260,000", tiv="$1,050,000", bpp="$215,000",
                       sqft="7,400", constr="Metal", yb="1999", stories="1", spk="No",
                       cook="None", carrier="Carrier B", claims="Hail roof damage 2026, closed",
                       bk="No"))
    loss_md(d, A.lr_carrier_b("High Plains Roofing Co", ["2025-12-28 to 2026-12-28"],
                              "2026-07-21", [["2026-04-02", "hail damage to shop roof", "$9,650", "$0"]]))

    # 520 gift shop. COOKING CONFLICT: app says None, email says empanadas fried in a countertop fryer.
    d = folder(520)
    email(d, "Willow Creek Gifts - Fredericksburg",
          "Gift shop on Main St in Fredericksburg, candles, pottery and local jams. On Saturdays "
          "we fry empanadas in a small countertop fryer by the register and sell them warm. "
          "Carrier B loss run attached, clean.")
    app_typed_pdf(d, 520, app(named="Willow Creek Gifts LLC", mail="same as premises",
                              prem="219 E Main St, Fredericksburg TX 78624", eff="2026-12-03",
                              yrs="7", entity="LLC", lob="Business owners policy",
                              ops="Gift shop", emp="4",
                              sales="$355,000", tiv="$188,000", bpp="$102,000", sqft="2,400",
                              constr="Masonry", yb="1912", stories="1", spk="No", cook="None",
                              carrier="Carrier B", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_b("Willow Creek Gifts LLC", ["2025-12-03 to 2026-12-03"],
                              "2026-08-04", []))

    # 521 deli, cooking stated. Planted conflict: sales (email around $610,000, app $575,000).
    d = folder(521)
    email(d, "Station Street Deli - Bryan",
          "Deli on Main in Bryan, sandwiches, soups and box lunches. Sales were around $610,000 "
          "last year, the app has the lower number from the year before. Carrier B loss run "
          "attached, one customer slip.")
    app_md(d, 521, app(named="Station Street Deli LLC", mail="same as premises",
                       prem="404 N Main St, Bryan TX 77803", eff="2026-12-09", yrs="6",
                       entity="LLC", lob="Restaurant package, no liquor",
                       ops="Deli, counter service sandwiches and soups", emp="9",
                       sales="$575,000", tiv="$160,000", bpp="$74,000", sqft="2,000",
                       constr="Masonry", yb="1948", stories="1", spk="Yes, hood only",
                       cook="Flat-top, panini press, soup warmer",
                       carrier="Carrier B", claims="Slip and fall 2026, closed", bk="No"))
    loss_md(d, A.lr_carrier_b("Station Street Deli LLC", ["2025-12-09 to 2026-12-09"], "2026-08-19",
                              [["2026-06-02", "customer slip near drink cooler", "$1,480", "$0"]]))

    # 522 deli. COOKING CONFLICT: app says None, email says a fryer runs every day.
    d = folder(522)
    email(d, "Seawall Deli - Galveston",
          "Deli on Seawall Blvd in Galveston, po-boys and sandwiches for the beach crowd. We run "
          "a fryer for fries and shrimp every day, it is not on the app, my mistake. Carrier C "
          "loss run attached, no claims.")
    app_md(d, 522, app(named="Seawall Deli Co LLC", mail="same as premises",
                       prem="3702 Seawall Blvd, Galveston TX 77550", eff="2026-12-16", yrs="4",
                       entity="LLC", lob="Business owners policy",
                       ops="Deli, counter sandwiches", emp="6", sales="$345,000",
                       tiv="$128,000", bpp="$61,000", sqft="1,500", constr="Masonry", yb="1976",
                       stories="1", spk="No", cook="None", carrier="Carrier C", claims="None",
                       bk="No"))
    loss_md(d, lr_c("Seawall Deli Co LLC", ["2025-12-16 to 2026-12-16"], "2026-09-02", []))

    # 523 tavern, prohibited class (W1, held). Carrier C fight claim.
    d = folder(523)
    email(d, "Rusty Spur Tavern - Odessa",
          "Tavern on East 8th in Odessa, full bar and pool tables, open until 2. One fight claim "
          "this spring on the Carrier C run, closed. Need a quote.")
    app_md(d, 523, app(named="Rusty Spur Tavern LLC", mail="same as premises",
                       prem="1110 E 8th St, Odessa TX 79761", eff="2026-12-20",
                       yrs="9", entity="LLC", lob="Liquor liability, general liability",
                       ops="Tavern, full bar, pool tables", emp="7", sales="$640,000",
                       tiv="$290,000", bpp="$85,000", sqft="3,200", constr="Masonry",
                       yb="1958", stories="1", spk="No", cook="None",
                       carrier="Carrier C", claims="Patron fight 2026, closed", bk="No"))
    loss_md(d, lr_c("Rusty Spur Tavern LLC", ["2025-12-20 to 2026-12-20"], "2026-08-28",
                    [["C-61207", "2026-04-11", "assault, patron fight", "$7,300", "$0"]]))

    # 524 nightclub, prohibited class (W1, held). Carrier A, no claims.
    d = folder(524)
    email(d, "Velvet Room Nightclub - El Paso",
          "Nightclub on Mesa St in El Paso, dance floor and DJs Friday and Saturday, full bar. "
          "Carrier A has us, no claims, loss run attached.")
    app_md(d, 524, app(named="Velvet Room Nightclub LLC", mail="same as premises",
                       prem="5025 N Mesa St, El Paso TX 79912", eff="2026-12-26", yrs="3",
                       entity="LLC", lob="Liquor liability, general liability",
                       ops="Nightclub, dance floor, DJ, full bar", emp="12",
                       sales="$780,000", tiv="$350,000", bpp="$120,000", sqft="4,600",
                       constr="Masonry", yb="1979", stories="1", spk="Partial", cook="None",
                       carrier="Carrier A", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_a("Velvet Room Nightclub LLC", ["2025-12-26 to 2026-12-26"],
                              "2026-09-10", []))

    # 525 breakfast restaurant, cooking stated (griddle, two fryers, hood with suppression). Carrier C grease fire.
    d = folder(525)
    email(d, "Sunrise Skillet - Amarillo",
          "Breakfast and lunch restaurant on Georgia St in Amarillo, 54 seats, open at 6. "
          "Griddle and two fryers under the hood. Carrier C has the small grease fire from "
          "March, closed. Typed app attached.")
    app_typed_pdf(d, 525, app(named="Sunrise Skillet LLC", mail="same as premises",
                              prem="3415 S Georgia St, Amarillo TX 79109", eff="2026-12-12",
                              yrs="8", entity="LLC", lob="Restaurant package, no liquor",
                              ops="Breakfast and lunch restaurant, table service, 54 seats",
                              emp="15", sales="$905,000", tiv="$285,000", bpp="$140,000",
                              sqft="3,100", constr="Masonry", yb="1991", stories="1",
                              spk="Yes, full", cook="Griddle, two fryers, hood with suppression",
                              carrier="Carrier C", claims="Grease fire 2026, closed", bk="No"))
    loss_md(d, lr_c("Sunrise Skillet LLC", ["2025-12-12 to 2026-12-12"], "2026-09-24",
                    [["C-61344", "2026-03-06", "grease fire, fryer", "$11,750", "$0"]]))

    # 526 bakery cafe, cooking stated (oven). Carrier B clean.
    d = folder(526)
    email(d, "Golden Crust Bakery - Temple",
          "Bakery cafe on South 1st in Temple, bread, kolaches and coffee, counter service and "
          "a few tables. Carrier B loss run attached, no claims.")
    app_md(d, 526, app(named="Golden Crust Bakery LLC", mail="same as premises",
                       prem="612 S 1st St, Temple TX 76501", eff="2027-01-05", yrs="10",
                       entity="LLC", lob="Restaurant package, no liquor",
                       ops="Bakery cafe, counter service", emp="8", sales="$465,000",
                       tiv="$170,000", bpp="$82,000", sqft="2,100", constr="Masonry", yb="1964",
                       stories="1", spk="No", cook="Oven, espresso machine",
                       carrier="Carrier B", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_b("Golden Crust Bakery LLC", ["2026-01-05 to 2027-01-05"],
                              "2026-10-13", []))

    # 527 NEAR-MISS "two floors" (in scope): accounting office on two floors of one building. Carrier A clean.
    d = folder(527)
    email(d, "Cottonwood Tax & Accounting - renewal",
          "Tax and accounting office on Austin Ave in Waco. We use two floors of the building, "
          "front desk and preparers downstairs, the partners upstairs. One address, one building. "
          "Carrier A loss run attached, no claims.")
    app_md(d, 527, app(named="Cottonwood Tax & Accounting LLC", mail="same as premises",
                       prem="1424 Austin Ave, Waco TX 76701", eff="2026-12-22", yrs="15",
                       entity="LLC", lob="Business owners policy",
                       ops="Tax and accounting office", emp="9", sales="$860,000",
                       tiv="$310,000", bpp="$95,000", sqft="3,600", constr="Masonry", yb="1925",
                       stories="2", spk="No", cook="None", carrier="Carrier A", claims="None",
                       bk="No"))
    loss_md(d, A.lr_carrier_a("Cottonwood Tax & Accounting LLC", ["2025-12-22 to 2026-12-22"],
                              "2026-09-21", []))

    # 528 NEAR-MISS "2nd floor" (in scope): law office in suite 210 on the 2nd floor. Carrier C clean.
    d = folder(528)
    email(d, "Hardin & Pruitt Law Office",
          "Law office in Beaumont, three lawyers and two staff. We are on the 2nd floor, suite "
          "210, same place as last year. Carrier C loss run attached, no claims.")
    app_typed_pdf(d, 528, app(named="Hardin & Pruitt PLLC", mail="same as premises",
                              prem="2615 Calder Ave Ste 210, Beaumont TX 77702", eff="2026-12-17",
                              yrs="12", entity="PLLC", lob="Business owners policy",
                              ops="Law office", emp="5", sales="$1,150,000",
                              tiv="$64,000", bpp="$70,000", sqft="2,300", constr="Masonry",
                              yb="1998", stories="3", spk="Yes", cook="None",
                              carrier="Carrier C", claims="None", bk="No"))
    loss_md(d, lr_c("Hardin & Pruitt PLLC", ["2025-12-17 to 2026-12-17"], "2026-09-08", []))

    # 529 NEAR-MISS "two entrances" (in scope): shoe retail store, one building. Carrier A clean.
    d = folder(529)
    email(d, "Brazos Boot & Shoe - Waxahachie",
          "Shoe store on the square in Waxahachie. The store has two entrances, the front door "
          "on the square and a back door from the parking lot. Same single building. Carrier A "
          "loss run attached, no claims.")
    app_md(d, 529, app(named="Brazos Boot & Shoe LLC", mail="same as premises",
                       prem="108 S College St, Waxahachie TX 75165", eff="2026-12-29", yrs="21",
                       entity="LLC", lob="Business owners policy",
                       ops="Shoe and boot retail store", emp="5", sales="$590,000",
                       tiv="$205,000", bpp="$160,000", sqft="2,900", constr="Masonry", yb="1902",
                       stories="2", spk="No", cook="None", carrier="Carrier A", claims="None",
                       bk="No"))
    loss_md(d, A.lr_carrier_a("Brazos Boot & Shoe LLC", ["2025-12-29 to 2026-12-29"],
                              "2026-10-01", []))

    # ============================================================ out of scope (530-541)
    # criterion 1: application is a scan. 530 JPG, 531 image-only PDF.
    d = folder(530)
    email(d, "Mesa Verde Frame Shop - scan",
          "Picture framing shop in Alpine. Application is a scan from my phone, sorry. Carrier B "
          "loss run attached, no claims.")
    app_scan(d, 530, app(named="Mesa Verde Frame Shop LLC", mail="same as premises",
                         prem="507 E Holland Ave, Alpine TX 79830", eff="2026-12-10", yrs="6",
                         entity="LLC", lob="Business owners policy", ops="Picture framing shop",
                         emp="2", sales="$165,000", tiv="$90,000", bpp="$40,000", sqft="1,400",
                         constr="Masonry", yb="1949", stories="1", spk="No", cook="None",
                         carrier="Carrier B", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_b("Mesa Verde Frame Shop LLC", ["2025-12-10 to 2026-12-10"], "2026-08-13", []))

    d = folder(531)
    email(d, "Clearwater Pool Supply - pdf is a scan",
          "Pool supply store in Kerrville. We signed the app and scanned it, so the PDF is a "
          "picture. Carrier A loss run typed, attached.")
    app_image_pdf(d, 531, app(named="Clearwater Pool Supply LLC", mail="same as premises",
                              prem="1240 Junction Hwy, Kerrville TX 78028", eff="2026-12-24", yrs="9",
                              entity="LLC", lob="Business owners policy",
                              ops="Pool supply retail store", emp="5",
                              sales="$690,000", tiv="$240,000", bpp="$150,000", sqft="4,000",
                              constr="Metal", yb="1995", stories="1", spk="No", cook="None",
                              carrier="Carrier A", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_a("Clearwater Pool Supply LLC", ["2025-12-24 to 2026-12-24"], "2026-09-16", []))

    # criterion 2: more than one location. 532-533 a second street address in another document;
    # 534-537 words only (no second street address anywhere).
    d = folder(532)
    email(d, "Bayside Auto Glass - schedule",
          "Auto glass shop, main bay in Corpus and a second bay in Portland. The schedule has both "
          "buildings. Carrier C loss run attached.")
    app_md(d, 532, app(named="Bayside Auto Glass LLC", mail="same as premises",
                       prem="4818 Ayers St, Corpus Christi TX 78415",
                       eff="2026-12-05", yrs="11", entity="LLC", lob="Business owners policy",
                       ops="Auto glass replacement shop", emp="10",
                       sales="$980,000", tiv="$260,000", bpp="$95,000",
                       sqft="3,800", constr="Metal", yb="1988", stories="1",
                       spk="No", cook="None", carrier="Carrier C", claims="None", bk="No"))
    schedule(d, [row("application", "1", "4818 Ayers St", "Corpus Christi", "78415", "$260000", "Metal", "1988", "3800", "No", "No"),
                 row("email", "2", "1902 Wildcat Dr", "Portland", "78374", "$110000", "Metal", "2006", "1600", "No", "No")])
    loss_md(d, lr_c("Bayside Auto Glass LLC", ["2025-12-05 to 2026-12-05"], "2026-08-07", []))

    d = folder(533)
    email(d, "Prairie Rose Florist - stock",
          "Florist on Texas Ave in Bryan. We also keep stock and the delivery vans at our "
          "warehouse, 2215 Leonard Rd, Bryan, which is not on the app. Carrier A loss run attached.")
    app_md(d, 533, app(named="Prairie Rose Florist LLC", mail="same as premises",
                       prem="3109 S Texas Ave, Bryan TX 77802", eff="2026-12-13", yrs="17",
                       entity="LLC", lob="Business owners policy", ops="Florist, retail flowers and gifts",
                       emp="8", sales="$540,000", tiv="$185,000", bpp="$70,000", sqft="2,600",
                       constr="Masonry", yb="1980", stories="1", spk="No", cook="None",
                       carrier="Carrier A", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_a("Prairie Rose Florist LLC", ["2025-12-13 to 2026-12-13"], "2026-09-04", []))

    d = folder(534)
    email(d, "Hill Country Vacuum & Sew - both stores",
          "Vacuum and sewing machine sales and repair. Please quote the same coverage for both "
          "stores, the numbers on the app are for the two together. Carrier B loss run attached.")
    app_md(d, 534, app(named="Hill Country Vacuum & Sew LLC", mail="same as premises",
                       prem="2140 Sidney Baker St, Kerrville TX 78028", eff="2026-12-08", yrs="19",
                       entity="LLC", lob="Business owners policy",
                       ops="Vacuum and sewing machine sales and repair", emp="6",
                       sales="$470,000", tiv="$150,000", bpp="$135,000", sqft="2,500",
                       constr="Masonry", yb="1977", stories="1", spk="No", cook="None",
                       carrier="Carrier B", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_b("Hill Country Vacuum & Sew LLC", ["2025-12-08 to 2026-12-08"], "2026-08-26", []))

    d = folder(535)
    email(d, "Permian Pump & Supply - renewal",
          "Pump and pipe supply in Odessa. Our other branch in Midland handles the west side "
          "customers and keeps its own stock. Same owner, same policy as last year. Carrier C "
          "loss run attached, no claims.")
    app_typed_pdf(d, 535, app(named="Permian Pump & Supply LLC", mail="same as premises",
                              prem="2901 W 2nd St, Odessa TX 79763", eff="2026-12-30", yrs="22",
                              entity="LLC", lob="Commercial property and general liability",
                              ops="Pump and pipe supply, counter sales and yard", emp="16",
                              sales="$3,100,000", tiv="$720,000", bpp="$540,000", sqft="14,000",
                              constr="Metal", yb="1983", stories="1", spk="No", cook="None",
                              carrier="Carrier C", claims="None", bk="No"))
    loss_md(d, lr_c("Permian Pump & Supply LLC", ["2025-12-30 to 2026-12-30"], "2026-09-30", []))

    d = folder(536)
    email(d, "Northgate Key & Lock - Lubbock",
          "Locksmith in Lubbock, keys cut and lockouts. We opened a second shop last spring "
          "across town, it runs the same way. Carrier A loss run attached, no claims.")
    app_md(d, 536, app(named="Northgate Key & Lock LLC", mail="same as premises",
                       prem="5217 34th St, Lubbock TX 79410", eff="2026-12-06", yrs="10",
                       entity="LLC", lob="Business owners policy", ops="Locksmith shop, key cutting",
                       emp="5", sales="$390,000", tiv="$120,000", bpp="$65,000", sqft="1,600",
                       constr="Masonry", yb="1969", stories="1", spk="No", cook="None",
                       carrier="Carrier A", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_a("Northgate Key & Lock LLC", ["2025-12-06 to 2026-12-06"], "2026-08-31", []))

    d = folder(537)
    email(d, "Twin Pines Pet Supply - one store now",
          "Pet food and supply store in Huntsville. We closed our second store in June, so it is "
          "just this one now. Carrier B loss run attached, no claims.")
    app_md(d, 537, app(named="Twin Pines Pet Supply LLC", mail="same as premises",
                       prem="1530 11th St, Huntsville TX 77340", eff="2026-12-27", yrs="8",
                       entity="LLC", lob="Business owners policy", ops="Pet food and supply retail store",
                       emp="4", sales="$430,000", tiv="$140,000", bpp="$112,000", sqft="3,000",
                       constr="Masonry", yb="1974", stories="1", spk="No", cook="None",
                       carrier="Carrier B", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_b("Twin Pines Pet Supply LLC", ["2025-12-27 to 2026-12-27"], "2026-09-25", []))

    # criterion 3: application not in English. 538 typed Spanish PDF, 539 Spanish md.
    d = folder(538)
    email(d, "tienda de llantas - Laredo",
          "Tienda de llantas en Laredo, montaje y balanceo. La solicitud va en PDF en espanol. "
          "Carrier C loss run adjunto.")
    app_spanish_pdf(d, 538, [
        ("Asegurado", "Llantera El Faro LLC"),
        ("Dirección de la ubicación", "3802 San Bernardo Ave, Laredo TX 78041"),
        ("Fecha de vigencia", "2026-12-14"),
        ("Años en el negocio", "12"),
        ("Operaciones", "Venta y montaje de llantas"),
        ("Número de empleados", "6"),
        ("Ventas anuales", "$540,000"),
        ("Valor del edificio", "$210,000"),
        ("Pies cuadrados", "4,200"),
        ("Construcción", "Metal"),
        ("Año de construcción", "1992"),
        ("Rociadores", "No"),
        ("Aseguradora anterior", "Carrier C"),
    ])
    loss_md(d, lr_c("Llantera El Faro LLC", ["2025-12-14 to 2026-12-14"], "2026-09-11", []))

    d = folder(539)
    email(d, "Papeleria Santa Cruz",
          "Papeleria en Brownsville, utiles escolares y copias. La solicitud esta en el archivo, "
          "en espanol. Carrier A nos cubre.")
    app_spanish_md(d, 539, [
        ("Asegurado", "Papeleria Santa Cruz LLC"),
        ("Dirección de la ubicación", "1150 E Elizabeth St, Brownsville TX 78520"),
        ("Fecha de vigencia", "2026-12-23"),
        ("Años en el negocio", "15"),
        ("Operaciones", "Papelería, útiles escolares y copias"),
        ("Número de empleados", "4"),
        ("Ventas anuales", "$310,000"),
        ("Valor del edificio", "$150,000"),
        ("Pies cuadrados", "2,100"),
        ("Construcción", "Mampostería"),
        ("Año de construcción", "1966"),
        ("Rociadores", "No"),
        ("Aseguradora anterior", "Carrier A"),
    ])
    loss_md(d, A.lr_carrier_a("Papeleria Santa Cruz LLC", ["2025-12-23 to 2026-12-23"], "2026-09-17", []))

    # criterion 4: email only, no application. 540-541
    d = folder(540)
    email(d, "Oakmont Kennels - quote",
          "Boarding kennel outside San Marcos, 30 runs and a play yard. I will send the "
          "application when I find it. Can you tell me what else you need?")

    d = folder(541)
    email(d, "Redbird Courier - quote",
          "Local courier service in Killeen, four cars and a sorting room. Need coverage from "
          "January 1. I don't know which carrier we have now, my brother handled it.")

    print("Wrote 32 submissions: SUB-510 .. SUB-541")


if __name__ == "__main__":
    build()
