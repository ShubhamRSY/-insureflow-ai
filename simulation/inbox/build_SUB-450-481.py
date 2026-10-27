"""Builds SUB-450 to SUB-481 (T-120 hold-out inbox): 20 in scope (450-469), 12 out of scope (470-481).
Reuses the typed/scan helpers of the T-108 and T-117 builders by import only. Writes simulation/inbox/SUB-450..481 and nothing else.
Idempotent: removes and rebuilds only SUB-450..SUB-481.
Run: .venv/bin/python simulation/inbox/build_SUB-450-481.py"""
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
    for n in range(450, 482):
        path = os.path.join(HERE, "SUB-%d" % n)
        if os.path.isdir(path):
            shutil.rmtree(path)

    # ============================================================ in scope (450-469)
    # 450 office tenant, bookkeeping office. Carrier A clean. Allow-list class. No cooking.
    d = folder(450)
    email(d, "Cedar Bend Bookkeeping - renewal",
          "Bookkeeping office in Killeen, we rent suite 300 in a small professional center. "
          "Desks and computers only, nothing stored on site. Carrier A has us, loss run attached, "
          "no claims. App below.")
    app_md(d, 450, app(named="Cedar Bend Bookkeeping LLC", mail="same as premises",
                       prem="2750 Bee Creek Rd Ste 300, Killeen TX 76542", eff="2026-12-01",
                       yrs="8", entity="LLC", lob="Business owners policy",
                       ops="Office, bookkeeping and tax preparation", emp="6", sales="$540,000",
                       tiv="$88,000", bpp="$61,000", sqft="2,400", constr="Masonry", yb="2001",
                       stories="1", spk="Yes", cook="None", carrier="Carrier A", claims="None",
                       bk="No"))
    loss_md(d, A.lr_carrier_a("Cedar Bend Bookkeeping LLC", ["2025-12-01 to 2026-12-01"],
                              "2026-08-12", []))

    # 451 clothing retail storefront, typed PDF app. Carrier A clean. Allow-list class. No cooking.
    d = folder(451)
    email(d, "Juniper Lane Apparel - San Angelo",
          "Clothing store on Concho St in San Angelo, racks and fitting rooms, open 10 to 8. "
          "No claims since we opened. Loss run from Carrier A attached, same as last year. "
          "Typed app attached.")
    app_typed_pdf(d, 451, app(named="Juniper Lane Apparel LLC", mail="same as premises",
                              prem="1804 Concho St, San Angelo TX 76903", eff="2026-11-15",
                              yrs="4", entity="LLC", lob="Business owners policy",
                              ops="Clothing retail storefront", emp="5", sales="$465,000",
                              tiv="$150,000", bpp="$105,000", sqft="3,100", constr="Masonry",
                              yb="1975", stories="1", spk="No", cook="None", carrier="Carrier A",
                              claims="None", bk="No"))
    loss_md(d, A.lr_carrier_a("Juniper Lane Apparel LLC", ["2025-11-15 to 2026-11-15"],
                              "2026-07-21", []))

    # 452 hardware retail store, typed md app. Carrier A clean. Allow-list class. No cooking.
    d = folder(452)
    email(d, "Walnut Creek Hardware - Crane",
          "Hardware store in Crane, paint, tools and yard supplies. Retail counter and aisles, "
          "been on South 2nd since 2011. Carrier A loss run attached, clean. Please send a quote.")
    app_md(d, 452, app(named="Walnut Creek Hardware Co LLC", mail="same as premises",
                       prem="418 S 2nd St, Crane TX 79731", eff="2026-12-01", yrs="14",
                       entity="LLC", lob="Business owners policy", ops="Hardware and paint retail store",
                       emp="4", sales="$395,000", tiv="$185,000", bpp="$120,000", sqft="4,200",
                       constr="Masonry", yb="1958", stories="1", spk="No", cook="None",
                       carrier="Carrier A", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_a("Walnut Creek Hardware Co LLC", ["2025-12-01 to 2026-12-01"],
                              "2026-09-02", []))

    # 453 insurance agency office, typed PDF app. Carrier A clean. Allow-list class. No cooking.
    d = folder(453)
    email(d, "Mesquite Ridge Agency",
          "Small insurance agency in a two story office on Gus Thomasson Rd, five agents and a "
          "receptionist. Carrier A has us, nothing reported, loss run attached.")
    app_typed_pdf(d, 453, app(named="Mesquite Ridge Insurance Agency LLC", mail="same as premises",
                              prem="3100 Gus Thomasson Rd Ste 120, Mesquite TX 75150",
                              eff="2026-11-29", yrs="7", entity="LLC", lob="Business owners policy",
                              ops="Insurance agency office, personal and commercial lines", emp="5",
                              sales="$690,000", tiv="$140,000", bpp="$92,000", sqft="2,600",
                              constr="Masonry", yb="2006", stories="2", spk="Yes",
                              cook="None", carrier="Carrier A", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_a("Mesquite Ridge Insurance Agency LLC", ["2025-11-29 to 2026-11-29"],
                              "2026-07-30", []))

    # 454 electrical contractor, typed PDF app. Planted conflict: square footage (email 2,450, app 3,200).
    d = folder(454)
    email(d, "Neches River Electric - sq ft",
          "Electrical contractor in Beaumont, six vans, office and a shop on Pine Island Rd. "
          "The building is 2,450 square feet, I measured it last winter. The application says "
          "3,200, that is off the old lease. Carrier B loss run attached, one van claim.")
    app_typed_pdf(d, 454, app(named="Neches River Electric LLC", mail="same as premises",
                              prem="1472 Pine Island Rd, Beaumont TX 77713", eff="2026-11-01",
                              yrs="9", entity="LLC", lob="Contractors general liability",
                              ops="Electrical contracting, commercial service calls, office and shop",
                              emp="14", sales="$1,450,000", tiv="$240,000", bpp="$175,000",
                              sqft="3,200", constr="Masonry", yb="1989", stories="1",
                              spk="No", cook="None", carrier="Carrier B",
                              claims="Van backed into pole 2026, closed", bk="No"))
    loss_md(d, A.lr_carrier_b("Neches River Electric LLC", ["2025-11-01 to 2026-11-01"],
                              "2026-05-26",
                              [["2026-01-19", "vehicle damage, service van", "$2,750", "$0"]]))

    # 455 janitorial supply wholesale. Planted conflict: annual sales (email $1.42 million, app $1,240,000).
    d = folder(455)
    email(d, "Chisholm Trail Janitorial - renewal",
          "Janitorial supply wholesale out of a warehouse on Bosque Blvd in Waco. We sell to "
          "cleaning crews and offices. Last year we did $1.42 million, the application has the "
          "lower budget number. Carrier C run attached, no claims.")
    app_md(d, 455, app(named="Chisholm Trail Janitorial Supply LLC", mail="same as premises",
                       prem="2215 Bosque Blvd, Waco TX 76706", eff="2026-12-01", yrs="9",
                       entity="LLC", lob="Commercial property and general liability",
                       ops="Wholesale janitorial supplies, warehouse", emp="12",
                       sales="$1,240,000", tiv="$505,000", bpp="$300,000", sqft="9,400",
                       constr="Metal", yb="2004", stories="1", spk="Yes", cook="None",
                       carrier="Carrier C", claims="None", bk="No"))
    loss_md(d, lr_c("Chisholm Trail Janitorial Supply LLC", ["2025-12-01 to 2026-12-01"],
                    "2026-08-05", []))

    # 456 flooring contractor, MISSING loss run (email says it is coming).
    d = folder(456)
    email(d, "Azalea Floor Works - Tyler",
          "Floor install contractor in Tyler, hardwood, tile and LVP for homes and a few small "
          "offices. Five crew and two trucks. The loss run is coming from our old agent, I asked "
          "twice. Application is below.")
    app_md(d, 456, app(named="Azalea Floor Works LLC", mail="same as premises",
                       prem="2108 Shiloh Rd, Tyler TX 75703", eff="2026-12-01", yrs="6",
                       entity="LLC", lob="Contractors general liability",
                       ops="Flooring installation, hardwood, tile and vinyl", emp="7",
                       sales="$655,000", tiv="$110,000", bpp="$125,000", sqft="2,000",
                       constr="Masonry", yb="1992", stories="1", spk="No", cook="None",
                       carrier="Carrier C", claims="Unknown, loss run requested", bk="No"))

    # 457 light metal fabrication shop, Carrier A fire claim. No cooking.
    d = folder(457)
    email(d, "Bayou Ridge Metal Works - Pearland",
          "Light metal shop in Pearland, brackets and railings for commercial jobs. We have a "
          "welder and a chop saw. Small fire from a welding spark this spring, put out with an "
          "extinguisher. Carrier A loss run attached.")
    app_md(d, 457, app(named="Bayou Ridge Metal Works LLC", mail="same as premises",
                       prem="6615 Industrial Dr, Pearland TX 77584", eff="2026-12-02", yrs="8",
                       entity="LLC", lob="Commercial property and general liability",
                       ops="Light metal fabrication, brackets and railings, shop", emp="13",
                       sales="$2,050,000", tiv="$690,000", bpp="$380,000", sqft="11,800",
                       constr="Metal", yb="2008", stories="1", spk="Yes, wet pipe", cook="None",
                       carrier="Carrier A", claims="Welding spark fire 2026, closed", bk="No"))
    loss_md(d, A.lr_carrier_a("Bayou Ridge Metal Works LLC", ["2025-12-02 to 2026-12-02"],
                              "2026-08-18",
                              [["2026-04-14", "welding spark fire, shop, small", "$6,850", "$0", "closed"]]))

    # 458 office building lessor. Planted conflict: suite count (email 9 suites, app 8 suites).
    d = folder(458)
    email(d, "Pecan Row Professional Center - Temple",
          "Office building on South 31st in Temple. We have 9 suites now, the new one was "
          "leased to a title company. The app says 8, that was before the lease. All tenants "
          "are professional offices. Carrier C loss run attached, no claims.")
    app_md(d, 458, app(named="Pecan Row Professional Center LLC", mail="same as premises",
                       prem="1520 S 31st St, Temple TX 76504", eff="2026-12-05", yrs="11",
                       entity="LLC", lob="Commercial property and general liability",
                       ops="Lessor of office building, 8 suites, professional tenants", emp="2",
                       sales="$598,000 (rent roll)", tiv="$1,240,000", bpp="$38,000",
                       sqft="10,600", constr="Masonry", yb="1999", stories="2",
                       spk="Yes, full", cook="None", carrier="Carrier C", claims="None", bk="No"))
    loss_md(d, lr_c("Pecan Row Professional Center LLC", ["2025-12-05 to 2026-12-05"],
                    "2026-09-09", []))

    # 459 office building lessor. Planted conflict: floor area (email roughly 2,400, app 2,950).
    d = folder(459)
    email(d, "Duval Road professional bldg",
          "Four suite office building on Duval Rd in Austin, roughly 2,400 sq ft total. Tenants "
          "are CPAs, a title office and an insurance agency. Carrier C loss run attached, nothing "
          "reported.")
    app_md(d, 459, app(named="Bluebonnet Duval Professional LLC", mail="same as premises",
                       prem="4418 Duval Rd, Austin TX 78759", eff="2026-12-08", yrs="6",
                       entity="LLC", lob="Commercial property and general liability",
                       ops="Lessor of office building, 4 suites, professional tenants", emp="2",
                       sales="$332,000 (rent roll)", tiv="$910,000", bpp="$25,000",
                       sqft="2,950", constr="Masonry", yb="2011", stories="2",
                       spk="Yes, full", cook="None", carrier="Carrier C", claims="None", bk="No"))
    loss_md(d, lr_c("Bluebonnet Duval Professional LLC", ["2025-12-08 to 2026-12-08"],
                    "2026-08-27", []))

    # 460 roofing and sheet metal contractor, Carrier B hail claim. Planted conflict: TIV (email 1,180,000, app $980,000).
    d = folder(460)
    email(d, "Stonegate Roofing - Round Rock",
          "Roofing and sheet metal, we do commercial and some homes, 22 people. Shop plus a small "
          "counter where we sell gutter parts. The building is valued at 1,180,000 on the "
          "appraisal from last year, the app shows the old number. Carrier B loss run attached, "
          "one hail claim.")
    app_md(d, 460, app(named="Stonegate Roofing & Sheet Metal Co", mail="same as premises",
                       prem="1902 Chisholm Trail Rd, Round Rock TX 78681", eff="2026-12-02",
                       yrs="12", entity="Corporation", lob="Contractors general liability",
                       ops="Roofing and sheet metal contractor, shop and small supply counter",
                       emp="22", sales="$2,450,000", tiv="$980,000", bpp="$240,000",
                       sqft="6,800", constr="Metal", yb="1996", stories="1", spk="No",
                       cook="None", carrier="Carrier B", claims="Hail roof damage 2026, closed",
                       bk="No"))
    loss_md(d, A.lr_carrier_b("Stonegate Roofing & Sheet Metal Co", ["2025-12-02 to 2026-12-02"],
                              "2026-06-30", [["2026-03-17", "hail damage to roof coverings", "$8,200", "$0"]]))

    # 461 gift shop with lunch counter. Cooking CONFLICT: app says None, email says soup on the stove top.
    d = folder(461)
    email(d, "Magnolia Gifts - Marshall",
          "Gift shop on East Houston in Marshall, candles, cards, home stuff. We do a little "
          "lunch counter too, I heat the soup on the stove top at noon and sell it by the cup. "
          "Carrier B loss run attached, clean.")
    app_typed_pdf(d, 461, app(named="Magnolia Gifts & Home Goods LLC", mail="same as premises",
                              prem="815 E Houston St, Marshall TX 75670", eff="2026-11-19",
                              yrs="6", entity="LLC", lob="Business owners policy",
                              ops="Gift and home goods retail store, small lunch counter", emp="5",
                              sales="$380,000", tiv="$165,000", bpp="$110,000", sqft="2,800",
                              constr="Masonry", yb="1968", stories="1", spk="No", cook="None",
                              carrier="Carrier B", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_b("Magnolia Gifts & Home Goods LLC", ["2025-11-19 to 2026-11-19"],
                              "2026-07-08", []))

    # 462 deli, cooking stated in the application. Planted conflict: sales (email about $560,000, app $505,000).
    d = folder(462)
    email(d, "Corner Table Deli - Killeen",
          "Deli on Ohio Ave in Killeen, sandwiches and soups, lunch rush and catering. Last year "
          "we did about $560,000 in sales, the app has the lower number. Carrier B loss run "
          "attached, one slip and fall at the door.")
    app_md(d, 462, app(named="Corner Table Deli LLC", mail="same as premises",
                       prem="1315 Ohio Ave, Killeen TX 76541", eff="2026-11-08", yrs="5",
                       entity="LLC", lob="Restaurant package, no liquor",
                       ops="Deli, counter service sandwiches and soups", emp="8",
                       sales="$505,000", tiv="$150,000", bpp="$70,000", sqft="1,900",
                       constr="Masonry", yb="1979", stories="1", spk="Yes, hood only",
                       cook="Flat grill, panini press, soup kept warm on stove top",
                       carrier="Carrier B", claims="Slip and fall 2026, closed", bk="No"))
    loss_md(d, A.lr_carrier_b("Corner Table Deli LLC", ["2025-11-08 to 2026-11-08"], "2026-07-30",
                              [["2026-05-11", "customer slip at door mat", "$1,250", "$0"]]))

    # 463 deli, COOKING CONFLICT: app says None, email and schedule say fryer / cooking yes.
    d = folder(463)
    email(d, "Harbor Deli Co - Ocean Dr",
          "Deli on Ocean Dr in Corpus Christi, wraps and sandwiches for the lunch crowd. We fry "
          "chicken tenders in the fryer every day, that's our best seller, I forgot to put it on "
          "the app. Schedule attached. Carrier C loss run attached, no claims.")
    app_md(d, 463, app(named="Harbor Deli Co LLC", mail="same as premises",
                       prem="2740 Ocean Dr, Corpus Christi TX 78404", eff="2026-12-10", yrs="3",
                       entity="LLC", lob="Business owners policy",
                       ops="Deli, counter sandwiches and wraps", emp="5", sales="$315,000",
                       tiv="$115,000", bpp="$58,000", sqft="1,600", constr="Masonry", yb="1981",
                       stories="1", spk="No", cook="None", carrier="Carrier C", claims="None",
                       bk="No"))
    schedule(d, [row("application", "1", "2740 Ocean Dr", "Corpus Christi", "78404", "$115000",
                     "Masonry", "1981", "1600", "No", "Yes")])
    loss_md(d, lr_c("Harbor Deli Co LLC", ["2025-12-10 to 2026-12-10"], "2026-08-03", []))

    # 464 pub with full bar and kitchen, one building, two operations (SUB-352 shape). Typed PDF.
    d = folder(464)
    email(d, "Lantern Hill Pub & Grill - Denton",
          "Pub on West Oak in Denton. Bar downstairs, kitchen with a fryer and flat top for pub "
          "food. Upstairs is two office suites. One building, one policy. Carrier C loss run "
          "attached, one liquor claim last fall, closed.")
    app_typed_pdf(d, 464, app(named="Lantern Hill Pub & Grill LLC", mail="same as premises",
                              prem="512 W Oak St, Denton TX 76201", eff="2026-12-03", yrs="5",
                              entity="LLC", lob="Business owners policy with liquor liability",
                              ops="Pub with full bar and kitchen, ground floor; two office suites, second floor",
                              emp="11", sales="$870,000", tiv="$405,000", bpp="$130,000",
                              sqft="4,900", constr="Masonry", yb="1938", stories="2",
                              spk="Yes, bar area and kitchen", cook="Fryer, flat top, hood",
                              carrier="Carrier C", claims="Liquor liability 2025, closed", bk="No"))
    loss_md(d, lr_c("Lantern Hill Pub & Grill LLC", ["2025-12-03 to 2026-12-03"], "2026-08-21",
                    [["C-50612", "2025-10-19", "liquor liability, patron", "$12,900", "$0"]]))

    # 465 nightclub, prohibited class (W1, held). Carrier C assault claim.
    d = folder(465)
    email(d, "Sunset Pier Nightclub - Corpus",
          "Nightclub on Yorktown in Corpus. Dance floor, DJs and a full bar, open Thu to Sun "
          "until 2. One assault claim from last year on the Carrier C loss run, closed. Need "
          "a quote before our policy ends.")
    app_md(d, 465, app(named="Sunset Pier Nightclub LLC", mail="same as premises",
                       prem="2410 Yorktown Blvd, Corpus Christi TX 78416", eff="2026-12-12",
                       yrs="3", entity="LLC", lob="Liquor liability, general liability",
                       ops="Nightclub, dance floor, DJ, full bar", emp="14", sales="$930,000",
                       tiv="$380,000", bpp="$140,000", sqft="5,800", constr="Masonry",
                       yb="1982", stories="1", spk="Partial", cook="None",
                       carrier="Carrier C", claims="Assault claim 2025, closed", bk="No"))
    loss_md(d, lr_c("Sunset Pier Nightclub LLC", ["2025-12-12 to 2026-12-12"], "2026-07-15",
                    [["C-50734", "2025-09-22", "assault, patron", "$11,400", "$0"]]))

    # 466 hookah lounge, prohibited class (W1, held). Carrier A, no claims.
    d = folder(466)
    email(d, "Smoke Ring Hookah Lounge - Arlington",
          "Hookah lounge on West Pioneer Pkwy in Arlington. Hookah, tea and energy drinks, beer "
          "and wine on weekends. Open to 1 am. Carrier A has us, no claims, loss run attached.")
    app_md(d, 466, app(named="Smoke Ring Hookah Lounge LLC", mail="same as premises",
                       prem="2030 W Pioneer Pkwy, Arlington TX 76013", eff="2026-11-14", yrs="2",
                       entity="LLC", lob="Business owners policy with liquor liability",
                       ops="Hookah lounge, lounge seating, beer and wine on weekends", emp="6",
                       sales="$295,000", tiv="$125,000", bpp="$90,000", sqft="2,100",
                       constr="Frame", yb="1963", stories="1", spk="No", cook="None",
                       carrier="Carrier A", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_a("Smoke Ring Hookah Lounge LLC", ["2025-11-14 to 2026-11-14"],
                              "2026-08-26", []))

    # 467 breakfast restaurant, cooking stated (griddle, fryers). Typed PDF. Carrier C grease fire claim.
    d = folder(467)
    email(d, "Harvest Moon Breakfast House - Lubbock",
          "Breakfast restaurant on Lakeside in Lubbock, 60 seats, open at 6. Griddle, two fryers, "
          "a convection oven. Carrier C has the grease fire from February, closed. Typed app attached.")
    app_typed_pdf(d, 467, app(named="Harvest Moon Breakfast House LLC", mail="same as premises",
                              prem="2210 Lakeside Dr, Lubbock TX 79411", eff="2026-12-01",
                              yrs="7", entity="LLC", lob="Restaurant package, no liquor",
                              ops="Breakfast and lunch restaurant, table service, 60 seats",
                              emp="16", sales="$990,000", tiv="$300,000", bpp="$150,000",
                              sqft="3,300", constr="Masonry", yb="1989", stories="1",
                              spk="Yes, full", cook="Griddle, two fryers, convection oven, hood with suppression",
                              carrier="Carrier C", claims="Grease fire 2026, closed", bk="No"))
    loss_md(d, lr_c("Harvest Moon Breakfast House LLC", ["2025-12-01 to 2026-12-01"], "2026-09-02",
                    [["C-50881", "2026-02-14", "grease fire, fryer", "$13,200", "$0"]]))

    # 468 bakery cafe, cooking stated. Owner no-known-loss letter (prior carrier program closed).
    d = folder(468)
    email(d, "Cypress Bend Bakery Cafe - Sulphur Springs",
          "Bakery cafe on South Gilmer in Sulphur Springs, bread, pastries and breakfast "
          "sandwiches, dine in and counter. Old carrier's program closed in 2026. Owner wrote a "
          "letter, that is all we have.")
    app_md(d, 468, app(named="Cypress Bend Bakery Cafe LLC", mail="same as premises",
                       prem="1403 S Gilmer St, Sulphur Springs TX 75482", eff="2026-12-06", yrs="4",
                       entity="LLC", lob="Restaurant package, no liquor",
                       ops="Bakery cafe, counter service, dine in", emp="9", sales="$440,000",
                       tiv="$135,000", bpp="$88,000", sqft="2,300", constr="Masonry", yb="1972",
                       stories="1", spk="No", cook="Convection ovens, panini press, espresso machine",
                       carrier="Carrier B (program closed 2026)", claims="None", bk="No"))
    loss_md(d, [
        "NO KNOWN LOSS LETTER (FICTIONAL)",
        "Applicant: Cypress Bend Bakery Cafe LLC",
        "Dated 2026-09-21. To the best of my knowledge the applicant has had no losses or",
        "claims at this location in the past five years.",
        "Signed: Marla Stiles, owner"])

    # 469 wholesale auto parts and tire mounting (mixed class). Planted conflict: floor area (email 3,600, app 4,100).
    d = folder(469)
    email(d, "Ridgeline Auto Parts & Tire - Lubbock",
          "Auto parts wholesale and tire mounting in Lubbock on Frankford. The warehouse is 3,600 "
          "square feet, the rest is the bay. The app has 4,100 from the county record, that is not "
          "right, I measured it. Carrier A loss run attached, one theft claim.")
    app_md(d, 469, app(named="Ridgeline Auto Parts & Tire Service LLC", mail="same as premises",
                       prem="3015 Frankford Ave, Lubbock TX 79407", eff="2026-12-09", yrs="8",
                       entity="LLC", lob="Commercial property and general liability",
                       ops="Wholesale auto parts, tire mounting and installation, warehouse",
                       emp="10", sales="$1,310,000", tiv="$420,000", bpp="$275,000", sqft="4,100",
                       constr="Metal", yb="1994", stories="1", spk="No", cook="None",
                       carrier="Carrier A", claims="Theft of tires 2026, closed", bk="No"))
    loss_md(d, A.lr_carrier_a("Ridgeline Auto Parts & Tire Service LLC", ["2025-12-09 to 2026-12-09"],
                              "2026-07-28",
                              [["2026-01-22", "theft of tires from yard", "$2,800", "$0", "closed"]]))

    # ============================================================ out of scope (470-481)
    # criterion 1: application is a scan (JPG or image-only PDF). 470-472
    d = folder(470)
    email(d, "Tumbleweed Upholstery - app scan",
          "Upholstery shop on Abe St in San Angelo, we recover couches and car seats. Application "
          "is a scan from the copier, sorry again. Carrier B loss run attached, no claims.")
    app_scan(d, 470, app(named="Tumbleweed Upholstery LLC", mail="same as premises",
                         prem="418 N Abe St, San Angelo TX 76903", eff="2026-12-15", yrs="7",
                         entity="LLC", lob="Business owners policy", ops="Upholstery and auto trim shop",
                         emp="3", sales="$210,000", tiv="$95,000", bpp="$64,000", sqft="2,000",
                         constr="Masonry", yb="1959", stories="1", spk="No", cook="None",
                         carrier="Carrier B", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_b("Tumbleweed Upholstery LLC", ["2025-12-15 to 2026-12-15"], "2026-07-14", []))

    d = folder(471)
    email(d, "Brightwater Laundry - pdf is a scan",
          "Coin laundry and dry cleaning drop off in Beaumont. We printed the app, signed it, then "
          "scanned it, so it is a picture. Carrier A loss run typed, attached.")
    app_image_pdf(d, 471, app(named="Brightwater Laundry Co LLC", mail="same as premises",
                              prem="1870 Dowlen Rd, Beaumont TX 77706", eff="2026-11-21", yrs="6",
                              entity="LLC", lob="Business owners policy",
                              ops="Coin laundry and dry cleaning drop off", emp="5",
                              sales="$340,000", tiv="$210,000", bpp="$80,000", sqft="3,500",
                              constr="Masonry", yb="1984", stories="1", spk="Yes", cook="None",
                              carrier="Carrier A", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_a("Brightwater Laundry Co LLC", ["2025-11-21 to 2026-11-21"], "2026-06-11", []))

    d = folder(472)
    email(d, "Rosewood Tile - scan again",
          "Tile and stone wholesale out of our Abilene warehouse. App is a scan, the copier again. "
          "Carrier C loss run attached, no claims.")
    app_scan(d, 472, app(named="Rosewood Tile & Stone Supply LLC", mail="PO Box 884, Abilene TX 79604",
                         prem="2950 N 1st St, Abilene TX 79603", eff="2026-12-02", yrs="10",
                         entity="LLC", lob="Commercial property and general liability",
                         ops="Wholesale tile and stone, warehouse", emp="8", sales="$1,150,000",
                         tiv="$480,000", bpp="$260,000", sqft="9,000", constr="Metal", yb="1997",
                         stories="1", spk="Yes", cook="None", carrier="Carrier C", claims="None", bk="No"))
    loss_md(d, lr_c("Rosewood Tile & Stone Supply LLC", ["2025-12-02 to 2026-12-02"], "2026-09-03", []))

    # criterion 2: more than one location. 473-475
    d = folder(473)
    email(d, "Cactus Hill Pest Control - two branches",
          "Pest control company with the office in Amarillo and a branch in Lubbock. Both are on "
          "the app and the schedule. Carrier B loss run attached, one van accident.")
    app_md(d, 473, app(named="Cactus Hill Pest Control LLC", mail="PO Box 1402, Amarillo TX 79105",
                       prem="Loc 1: 3311 Soncy Rd, Amarillo TX 79124; Loc 2: 5602 Slide Rd, Lubbock TX 79414",
                       eff="2026-12-04", yrs="12", entity="LLC", lob="Business owners policy",
                       ops="Pest control service, office and chemical storage", emp="18",
                       sales="$1,320,000", tiv="$490,000", bpp="$190,000",
                       sqft="4,200 (Loc 1), 2,600 (Loc 2)", constr="Masonry", yb="1990", stories="1",
                       spk="No", cook="None", carrier="Carrier B", claims="Vehicle accident 2025, closed", bk="No"))
    schedule(d, [row("application", "1", "3311 Soncy Rd", "Amarillo", "79124", "$350000", "Masonry", "1990", "4200", "No", "No"),
                 row("application", "2", "5602 Slide Rd", "Lubbock", "79414", "$140000", "Masonry", "2003", "2600", "No", "No")])
    loss_md(d, A.lr_carrier_b("Cactus Hill Pest Control LLC", ["2025-12-04 to 2026-12-04"], "2026-08-12",
                              [["2025-11-06", "vehicle accident, service van", "$6,100", "$0"]]))

    d = folder(474)
    email(d, "Panhandle Office Staffing - second desk",
          "Staffing agency, main office in Amarillo. We opened a second desk in Canyon in March, "
          "I forgot to put it on the app. Schedule has both. Carrier A loss run attached.")
    app_md(d, 474, app(named="Panhandle Office Staffing LLC", mail="same as premises",
                       prem="2801 Hillside Rd, Amarillo TX 79109", eff="2026-11-30", yrs="9",
                       entity="LLC", lob="Business owners policy", ops="Temporary staffing office",
                       emp="6", sales="$880,000", tiv="$120,000", bpp="$55,000", sqft="2,400",
                       constr="Masonry", yb="1996", stories="1", spk="Yes", cook="None",
                       carrier="Carrier A", claims="None", bk="No"))
    schedule(d, [row("application", "1", "2801 Hillside Rd", "Amarillo", "79109", "$120000", "Masonry", "1996", "2400", "Yes", "No"),
                 row("email", "2", "1100 4th Ave", "Canyon", "79015", "$45000", "Frame", "2011", "1200", "No", "No")])
    loss_md(d, A.lr_carrier_a("Panhandle Office Staffing LLC", ["2025-11-30 to 2026-11-30"], "2026-09-05", []))

    d = folder(475)
    email(d, "Coastal Bend Bike Works - two stores",
          "Bike shop on Leopard in Corpus, and a repair and rental store on Austin St in Rockport. "
          "Both are on the app. Carrier C loss run attached.")
    app_typed_pdf(d, 475, app(named="Coastal Bend Bike Works LLC", mail="same as premises",
                              prem="1419 Leopard St, Corpus Christi TX 78401", eff="2026-12-07", yrs="5",
                              entity="LLC", lob="Business owners policy",
                              ops="Bicycle retail and repair, two stores", emp="7", sales="$460,000",
                              tiv="$170,000", bpp="$118,000", sqft="3,000 (Corpus), 1,800 (Rockport)",
                              constr="Masonry", yb="1982", stories="1", spk="No", cook="None",
                              carrier="Carrier C", claims="None", bk="No"))
    loss_md(d, lr_c("Coastal Bend Bike Works LLC", ["2025-12-07 to 2026-12-07"], "2026-08-20", []))

    # criterion 3: application not in English. 476-478
    d = folder(476)
    email(d, "lavanderia mariposa",
          "Lavanderia en Edinburg, monedas y planchado. Solicitud en espanol, la mande escaneada "
          "antes. Carrier C loss run adjunto.")
    app_spanish_pdf(d, 476, [
        ("Asegurado", "Lavanderia Mariposa LLC"),
        ("Dirección de la ubicación", "1205 S Closner Blvd, Edinburg TX 78539"),
        ("Fecha de vigencia", "2026-12-01"),
        ("Años en el negocio", "8"),
        ("Operaciones", "Lavanderia de monedas y servicio de planchado"),
        ("Número de empleados", "5"),
        ("Ventas anuales", "$295,000"),
        ("Valor del edificio", "$240,000"),
        ("Pies cuadrados", "3,800"),
        ("Construcción", "Mampostería"),
        ("Año de construcción", "1987"),
        ("Rociadores", "No"),
        ("Aseguradora anterior", "Carrier C"),
    ])
    loss_md(d, lr_c("Lavanderia Mariposa LLC", ["2025-12-01 to 2026-12-01"], "2026-08-27", []))

    d = folder(477)
    email(d, "Ferreteria Los Olmos",
          "Ferreteria en Harlingen, pintura y materiales de jardin. Le dejo la solicitud en el "
          "archivo. Carrier A nos cubre, reclamacion no hay.")
    app_spanish_md(d, 477, [
        ("Asegurado", "Ferreteria Los Olmos LLC"),
        ("Dirección de la ubicación", "402 E Van Buren Ave, Harlingen TX 78550"),
        ("Fecha de vigencia", "2026-11-18"),
        ("Años en el negocio", "14"),
        ("Operaciones", "Ferretería, pintura y materiales para jardín"),
        ("Número de empleados", "6"),
        ("Ventas anuales", "$720,000"),
        ("Valor del edificio", "$260,000"),
        ("Pies cuadrados", "5,400"),
        ("Construcción", "Mampostería"),
        ("Año de construcción", "1979"),
        ("Rociadores", "No"),
        ("Aseguradora anterior", "Carrier A"),
    ])
    loss_md(d, A.lr_carrier_a("Ferreteria Los Olmos LLC", ["2025-11-18 to 2026-11-18"], "2026-07-09", []))

    d = folder(478)
    email(d, "servicios norte",
          "Limpieza de oficinas en McAllen, 9 personas. La solicitud va en PDF, esta en espanol. "
          "Carrier B tiene nuestra cuenta, adjunto la carta de siniestros.")
    app_spanish_pdf(d, 478, [
        ("Asegurado", "Servicios de Limpieza Norte LLC"),
        ("Dirección de la ubicación", "1700 N 10th St, McAllen TX 78501"),
        ("Fecha de vigencia", "2026-12-09"),
        ("Años en el negocio", "6"),
        ("Operaciones", "Servicio de limpieza de oficinas comerciales"),
        ("Número de empleados", "9"),
        ("Ventas anuales", "$410,000"),
        ("Valor del edificio", "$90,000"),
        ("Pies cuadrados", "1,900"),
        ("Construcción", "Mampostería"),
        ("Año de construcción", "1998"),
        ("Rociadores", "No"),
        ("Aseguradora anterior", "Carrier B"),
    ])
    loss_md(d, A.lr_carrier_b("Servicios de Limpieza Norte LLC", ["2025-12-09 to 2026-12-09"], "2026-06-22",
                              [["2026-03-03", "water damage, client office", "$2,300", "$0"]]))

    # criterion 4: email only, no application. 479-481
    d = folder(479)
    email(d, "Wren & Hollis Pet Grooming",
          "Pet grooming salon in Waco, two groomers and a bath room. I'll send the app later this "
          "week, I don't have the carrier name in front of me. Thanks.")

    d = folder(480)
    email(d, "Lakeshore Drywall - quote please",
          "Drywall and acoustic ceiling contractor in Amarillo, nine crew and three trucks. I think "
          "our current carrier is C. I can send the numbers if you tell me what you need.")

    d = folder(481)
    email(d, "Hillcrest Movers Abilene",
          "Local moving company in Abilene, three trucks and a storage yard on the north side. "
          "Need coverage starting December 1. Let me know what you need from us.")

    print("Wrote 32 submissions: SUB-450 .. SUB-481")


if __name__ == "__main__":
    build()
