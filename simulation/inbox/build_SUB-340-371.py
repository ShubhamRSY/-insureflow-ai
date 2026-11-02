"""Builds SUB-340 to SUB-371 (T-119 hold-out inbox). Reuses the typed/scan helpers
of the T-108 and T-117 builders by import only. Writes simulation/inbox/SUB-340..371 and nothing else.
Run: .venv/bin/python simulation/inbox/build_SUB-340-371.py"""
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


def app_scan(d, sub, fields):
    O.write_scan(os.path.join(d, "application_scan.jpg"),
                 O.app_plain_lines("SUB-%d" % sub, fields), FONT)


def app_image_pdf(d, sub, fields):
    O.write_image_pdf(os.path.join(d, "application.pdf"),
                      O.scan_jpeg_bytes(O.app_plain_lines("SUB-%d" % sub, fields), FONT))


def app_typed_pdf(d, sub, fields):
    O.write_typed_pdf(os.path.join(d, "application.pdf"),
                      O.app_plain_lines("SUB-%d" % sub, fields))


def app_spanish_pdf(d, sub, campos):
    O.write_typed_pdf(os.path.join(d, "application.pdf"),
                      O.app_spanish_lines("SUB-%d" % sub, campos))


def app_spanish_image_pdf(d, sub, campos):
    O.write_image_pdf(os.path.join(d, "application.pdf"),
                      O.scan_jpeg_bytes(O.app_spanish_lines("SUB-%d" % sub, campos), FONT))


def app_spanish_md(d, sub, campos):
    O.write_text(os.path.join(d, "application.md"),
                 "\n".join(O.app_spanish_lines("SUB-%d" % sub, campos)))


def loss_md(d, lines):
    O.write_text(os.path.join(d, "loss-runs.md"), "\n".join(lines))


def loss_image_pdf(d, lines):
    O.write_image_pdf(os.path.join(d, "loss-runs.pdf"),
                      O.scan_jpeg_bytes(lines, FONT))


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
    for n in range(340, 372):
        path = os.path.join(HERE, "SUB-%d" % n)
        if os.path.isdir(path):
            shutil.rmtree(path)

    # ------------------------------------------------------------ in scope (340-359)
    # 340 office tenant, Carrier A clean shape (plain class words only)
    d = folder(340)
    email(d, "Tallgrass Office - renewal",
          "We are an office tenant in a strip center in Round Rock, about 9 people, desks and "
          "computers only, nothing stored on site. Renewing with Carrier A, nothing has changed. "
          "App attached.")
    app_md(d, 340, app(named="Tallgrass Office LLC", mail="PO Box 2290, Round Rock TX 78680",
                       prem="1600 Lakeview Plaza Dr Ste 210, Round Rock TX 78664",
                       eff="2026-11-01", yrs="5", entity="LLC", lob="Business owners policy",
                       ops="Office", emp="9", sales="$1,050,000", tiv="$95,000", bpp="$74,000",
                       sqft="2,100", constr="Masonry", yb="1998", stories="1",
                       spk="Yes", cook="None", carrier="Carrier A", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_a("Tallgrass Office LLC", ["2025-11-01 to 2026-11-01"],
                              "2026-08-27", []))

    # 341 clothing retail storefront, Carrier A clean shape
    d = folder(341)
    email(d, "Pinecrest Threads storefront",
          "Clothing store on Sherwood Way in San Angelo, racks and fitting rooms up front. "
          "No claims since we opened. Loss run from Carrier A attached, same as last year.")
    app_md(d, 341, app(named="Pinecrest Threads LLC", mail="same as premises",
                       prem="2215 Sherwood Way, San Angelo TX 76901", eff="2026-11-15",
                       yrs="4", entity="LLC", lob="Business owners policy",
                       ops="Clothing retail storefront", emp="5", sales="$430,000",
                       tiv="$160,000", bpp="$118,000", sqft="3,300", constr="Masonry",
                       yb="1972", stories="1", spk="No", cook="None", carrier="Carrier A",
                       claims="None", bk="No"))
    loss_md(d, A.lr_carrier_a("Pinecrest Threads LLC", ["2025-11-15 to 2026-11-15"],
                              "2026-06-29", []))

    # 342 dry goods retail store, Carrier A clean shape
    d = folder(342)
    email(d, "Prairie Dry Goods",
          "Dry goods retail store in Lamesa, been on Main St since 1991. Fabric, notions and "
          "work wear, nothing else. Loss run attached, clean. Please send quote.")
    app_md(d, 342, app(named="Prairie Dry Goods Co LLC", mail="same as premises",
                       prem="508 Main St, Lamesa TX 79331", eff="2026-12-01", yrs="18",
                       entity="LLC", lob="Business owners policy", ops="Dry goods retail store",
                       emp="4", sales="$480,000", tiv="$210,000", bpp="$140,000",
                       sqft="5,600", constr="Masonry", yb="1948", stories="1",
                       spk="No", cook="None", carrier="Carrier A", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_a("Prairie Dry Goods Co LLC", ["2025-12-01 to 2026-12-01"],
                              "2026-09-14", []))

    # 343 thrift store, Carrier A clean shape
    d = folder(343)
    email(d, "Old Mill Thrift - Victoria",
          "Thrift store on Navarro St in Victoria. Donations come in the back door, we sell "
          "out front. Carrier A has us, loss run is attached, no claims. App below.")
    app_md(d, 343, app(named="Old Mill Thrift Co LLC", mail="same as premises",
                       prem="1407 N Navarro St, Victoria TX 77901", eff="2026-11-20",
                       yrs="6", entity="LLC", lob="Business owners policy", ops="Thrift store",
                       emp="7", sales="$395,000", tiv="$175,000", bpp="$96,000",
                       sqft="4,000", constr="Masonry", yb="1963", stories="1",
                       spk="Yes", cook="None", carrier="Carrier A", claims="None", bk="No"))
    schedule(d, [row("application", "1", "1407 N Navarro St", "Victoria", "77901", "$175000",
                     "Masonry", "1963", "4000", "Yes", "No")])
    loss_md(d, A.lr_carrier_a("Old Mill Thrift Co LLC", ["2025-11-20 to 2026-11-20"],
                              "2026-07-16", []))

    # 344 electrical contractor, square footage conflict (application vs schedule), typed PDF app
    d = folder(344)
    email(d, "Gulf Plains Electric - sq ft question",
          "Electrical contractor in Beaumont, 6 vans, office and a small shop. Heads up, the "
          "building is 2,450 square feet, the appraisal says that. The application says 3,200, "
          "that number came off the old lease. Carrier B loss run attached.")
    app_typed_pdf(d, 344, app(named="Gulf Plains Electrical Contractors LLC",
                              mail="same as premises", prem="3320 Tanglewood Dr, Beaumont TX 77705",
                              eff="2026-11-01", yrs="9", entity="LLC",
                              lob="Contractors general liability",
                              ops="Electrical contracting, office and shop", emp="14",
                              sales="$1,600,000", tiv="$260,000", bpp="$180,000",
                              sqft="3,200", constr="Masonry", yb="1984", stories="1",
                              spk="No", cook="None", carrier="Carrier B",
                              claims="Van backed into pole 2026, closed", bk="No"))
    schedule(d, [row("appraisal 2025", "1", "3320 Tanglewood Dr", "Beaumont", "77705", "$260000",
                     "Masonry", "1984", "2450", "No", "No")])
    loss_md(d, A.lr_carrier_b("Gulf Plains Electrical Contractors LLC", ["2025-11-01 to 2026-11-01"],
                              "2026-05-26",
                              [["2026-02-09", "vehicle damage, company van", "$3,900", "$0"]]))

    # 345 janitorial supply wholesale, annual sales conflict (application vs email)
    d = folder(345)
    email(d, "Brazos Janitorial Supply renewal",
          "Janitorial supply wholesale out of a warehouse in Waco. We sell to cleaning crews "
          "and offices. Last year we did about $1.42 million, the application shows the "
          "smaller number, it was the budget figure. Carrier C run attached, no claims.")
    app_md(d, 345, app(named="Brazos Janitorial Supply LLC", mail="same as premises",
                       prem="7741 Old Hickory Rd, Waco TX 76710", eff="2026-12-01", yrs="11",
                       entity="LLC", lob="Commercial property and general liability",
                       ops="Wholesale janitorial supplies, warehouse", emp="12",
                       sales="$1,240,000", tiv="$520,000", bpp="$310,000", sqft="9,800",
                       constr="Metal", yb="2002", stories="1", spk="Yes", cook="None",
                       carrier="Carrier C", claims="None", bk="No"))
    loss_md(d, lr_c("Brazos Janitorial Supply LLC", ["2025-12-01 to 2026-12-01"],
                              "2026-08-05", []))

    # 346 office building lessor, suite count conflict (application vs email)
    d = folder(346)
    email(d, "Ironwood Professional Plaza",
          "Office building in Temple. We have nine suites now, the last one just rented to a "
          "title company. App says eight, it's from before the lease. Tenants are all "
          "professional offices. Loss run from Carrier A, one roof claim.")
    app_md(d, 346, app(named="Ironwood Professional Plaza LLC", mail="same as premises",
                       prem="1135 Ironwood Dr, Temple TX 76502", eff="2026-12-01", yrs="12",
                       entity="LLC", lob="Commercial property and general liability",
                       ops="Lessor of office building, 8 suites, professional tenants",
                       emp="2", sales="$612,000 (rent roll)", tiv="$1,380,000", bpp="$42,000",
                       sqft="11,200", constr="Masonry", yb="2001", stories="2",
                       spk="Yes, full", cook="None",
                       carrier="Carrier A", claims="Roof leak 2025, closed", bk="No"))
    schedule(d, [row("application", "1", "1135 Ironwood Dr", "Temple", "76502", "$1380000",
                     "Masonry", "2001", "11200", "Yes", "No")])
    loss_md(d, A.lr_carrier_a("Ironwood Professional Plaza LLC",
                              ["2024-12-01 to 2025-12-01", "2025-12-01 to 2026-12-01"],
                              "2026-06-08",
                              [["2025-03-22", "roof leak, suite 105", "$5,400", "$0", "closed"]]))

    # 347 office building lessor, clean, Carrier C no-claims
    d = folder(347)
    email(d, "Lamar Professional Center",
          "Six suite professional building off Ridgecrest in Austin. Tenants are CPAs, a title "
          "office and two insurance agencies. Clean loss history with Carrier C. Schedule and "
          "loss run attached.")
    app_md(d, 347, app(named="Lamar Professional Center LLC", mail="same as premises",
                       prem="6205 Ridgecrest Ln, Austin TX 78746", eff="2026-11-25", yrs="10",
                       entity="LLC", lob="Commercial property and general liability",
                       ops="Lessor of office building, 6 suites, professional tenants",
                       emp="2", sales="$388,000 (rent roll)", tiv="$1,120,000", bpp="$30,000",
                       sqft="7,400", constr="Masonry", yb="2008", stories="2",
                       spk="Yes, full", cook="None", carrier="Carrier C", claims="None", bk="No"))
    schedule(d, [row("application", "1", "6205 Ridgecrest Ln", "Austin", "78746", "$1120000",
                     "Masonry", "2008", "7400", "Yes", "No")])
    loss_md(d, lr_c("Lamar Professional Center LLC", ["2025-11-25 to 2026-11-25"],
                              "2026-09-18", []))

    # 348 deli, application says no cooking, email says hot food on a stove and a flat grill
    d = folder(348)
    email(d, "Sunny Side Deli - Wichita Falls",
          "Counter deli on Seymour Hwy, sandwiches and soups, catering on weekdays. We heat up "
          "the soup on the stove top and grill the panini on a flat grill, hot food all day. "
          "Carrier B loss run attached, one slip and fall.")
    app_md(d, 348, app(named="Sunny Side Deli LLC", mail="same as premises",
                       prem="2609 Seymour Hwy, Wichita Falls TX 76301", eff="2026-11-08", yrs="4",
                       entity="LLC", lob="Restaurant package, no liquor",
                       ops="Deli, counter service sandwiches and soups", emp="8",
                       sales="$520,000", tiv="$150,000", bpp="$70,000", sqft="1,900",
                       constr="Masonry", yb="1979", stories="1", spk="Yes, hood only",
                       cook="None", carrier="Carrier B", claims="Slip and fall 2026, closed",
                       bk="No"))
    loss_md(d, A.lr_carrier_b("Sunny Side Deli LLC", ["2025-11-08 to 2026-11-08"], "2026-07-30",
                              [["2026-04-02", "customer slip, entry mat", "$1,850", "$0"]]))

    # 349 deli, application says no cooking, schedule says cooking yes (griddle)
    d = folder(349)
    email(d, "Cornerstone Sandwich Bar",
          "Sandwich and soup bar on Broadway in Galveston. Everything hot is made to order on "
          "the griddle at the counter. Schedule attached, Carrier A loss run also attached.")
    app_md(d, 349, app(named="Cornerstone Sandwich Bar LLC", mail="same as premises",
                       prem="917 Broadway St, Galveston TX 77550", eff="2026-12-03", yrs="7",
                       entity="LLC", lob="Restaurant package, no liquor",
                       ops="Deli, counter sandwiches and soups", emp="6", sales="$395,000",
                       tiv="$120,000", bpp="$64,000", sqft="1,700", constr="Masonry",
                       yb="1956", stories="1", spk="No", cook="None",
                       carrier="Carrier A", claims="None", bk="No"))
    schedule(d, [row("application", "1", "917 Broadway St", "Galveston", "77550", "$120000",
                     "Masonry", "1956", "1700", "No", "Yes")])
    loss_md(d, A.lr_carrier_a("Cornerstone Sandwich Bar LLC", ["2025-12-03 to 2026-12-03"],
                              "2026-09-01", []))

    # 350 plumbing supply wholesale, owner's dated no-known-loss letter (no carrier run)
    d = folder(350)
    email(d, "Hollis Plumbing Supply",
          "Plumbing supply wholesale in Killeen, we sell pipe, fittings and water heaters to "
          "plumbers. Our old carrier shut down the program. Owner wrote the letter, he says "
          "that's all we have, the carrier closed.")
    app_md(d, 350, app(named="Hollis Plumbing Supply Co", mail="same as premises",
                       prem="2904 E Rancier Ave, Killeen TX 76543", eff="2026-11-30", yrs="13",
                       entity="Corporation", lob="Commercial property and general liability",
                       ops="Wholesale plumbing supplies, warehouse, counter pickup", emp="11",
                       sales="$2,050,000", tiv="$640,000", bpp="$390,000", sqft="12,000",
                       constr="Metal", yb="1999", stories="1", spk="Yes", cook="None",
                       carrier="Carrier B (closed 2026)", claims="None", bk="No"))
    loss_md(d, [
        "NO KNOWN LOSS LETTER (FICTIONAL)",
        "Applicant: Hollis Plumbing Supply Co",
        "Dated 2026-09-29. To the best of my knowledge the applicant has had no losses or",
        "claims at this location in the past five years.",
        "Signed: Walt Hollis, owner"])

    # 351 pancake house, restaurant with griddle and fryer, Carrier C claim
    d = folder(351)
    email(d, "Blue Plate Pancake House - Denton",
          "Breakfast restaurant, 70 seats, we open at 6. Griddles, a fryer for hash browns and "
          "the hood was cleaned in June. Typed application attached. Carrier C loss run has one "
          "kitchen fire claim from last winter, closed.")
    app_typed_pdf(d, 351, app(named="Blue Plate Pancake House LLC", mail="same as premises",
                              prem="4101 Fort Worth Dr, Denton TX 76205", eff="2026-11-18",
                              yrs="8", entity="LLC", lob="Restaurant package, no liquor",
                              ops="Breakfast and lunch restaurant, table service, 70 seats",
                              emp="19", sales="$1,180,000", tiv="$330,000", bpp="$165,000",
                              sqft="3,600", constr="Masonry", yb="1985", stories="1",
                              spk="Yes, full", cook="Griddle, fryer, oven, hood with suppression",
                              carrier="Carrier C", claims="Kitchen fire 2026, closed", bk="No"))
    loss_md(d, lr_c("Blue Plate Pancake House LLC", ["2025-11-18 to 2026-11-18"],
                              "2026-06-24",
                              [["C-50311", "2026-01-27", "kitchen fire, fryer", "$14,600", "$0"]]))

    # 352 pub with full bar and kitchen (fryer) on ground floor, two office suites upstairs
    d = folder(352)
    email(d, "Foxhole Pub & Kitchen",
          "Pub on Hickory in Denton. Downstairs is the bar, full liquor, and a kitchen with a "
          "fryer and flat top for pub food. Upstairs is two office suites, a CPA and a "
          "remodel design office. One policy, one building. Carrier C loss run attached, "
          "liquor claim from 2025.")
    app_typed_pdf(d, 352, app(named="Foxhole Pub & Kitchen LLC", mail="same as premises",
                              prem="221 W Hickory St, Denton TX 76201", eff="2026-12-01",
                              yrs="6", entity="LLC", lob="Business owners policy with liquor liability",
                              ops="Pub with full bar and kitchen, ground floor; office suites, second floor",
                              emp="12", sales="$910,000", tiv="$420,000", bpp="$140,000",
                              sqft="5,200", constr="Masonry", yb="1931", stories="2",
                              spk="Yes, bar area and kitchen", cook="Fryer, flat top, hood",
                              carrier="Carrier C", claims="Liquor liability 2025, closed", bk="No"))
    loss_md(d, lr_c("Foxhole Pub & Kitchen LLC", ["2025-12-01 to 2026-12-01"],
                              "2026-08-14",
                              [["C-50418", "2025-10-11", "liquor liability, patron", "$16,500", "$0"]]))

    # 353 cocktail lounge, full liquor, prohibited class
    d = folder(353)
    email(d, "Velvet Crane Lounge - Dallas",
          "Cocktail lounge on Gaston, full liquor, cocktails and bottle service, DJ Thu to "
          "Sat, open till 2. No kitchen at all. Carrier B loss run attached. "
          "Need a quote fast, our current policy ends next month.")
    app_md(d, 353, app(named="Velvet Crane Cocktail Lounge LLC", mail="same as premises",
                       prem="3816 Gaston Ave, Dallas TX 75246", eff="2026-11-28", yrs="5",
                       entity="LLC", lob="Liquor liability, general liability",
                       ops="Cocktail lounge, full liquor, bottle service, DJ", emp="10",
                       sales="$840,000", tiv="$290,000", bpp="$110,000", sqft="3,100",
                       constr="Masonry", yb="1949", stories="1", spk="Partial",
                       cook="None",
                       carrier="Carrier B", claims="Patron altercation 2026, closed", bk="No"))
    loss_md(d, A.lr_carrier_b("Velvet Crane Cocktail Lounge LLC", ["2025-11-28 to 2026-11-28"],
                              "2026-09-10",
                              [["2026-03-14", "patron altercation, bar area", "$7,300", "$0"]]))

    # 354 nightclub, prohibited class
    d = folder(354)
    email(d, "Neon Harbor Nightclub",
          "Nightclub near the harbor in Corpus. Dance floor, DJs, full bar, open Thu to Sun "
          "until 2. Carrier C loss run attached with one assault claim from last year, closed. "
          "Owner is Ray Brandt.")
    app_md(d, 354, app(named="Neon Harbor Nightclub LLC", mail="same as premises",
                       prem="1700 N Chaparral St, Corpus Christi TX 78401", eff="2026-12-05",
                       yrs="4", entity="LLC", lob="Liquor liability, general liability",
                       ops="Nightclub, dance floor, DJ, full bar", emp="16", sales="$1,060,000",
                       tiv="$450,000", bpp="$160,000", sqft="6,400", constr="Masonry",
                       yb="1975", stories="1", spk="Partial", cook="None",
                       carrier="Carrier C", claims="Assault claim 2025, closed", bk="No"))
    loss_md(d, lr_c("Neon Harbor Nightclub LLC", ["2025-12-05 to 2026-12-05"],
                              "2026-07-09",
                              [["C-50522", "2025-09-06", "assault, patron", "$11,800", "$0"]]))

    # 355 hookah lounge, prohibited class, Carrier A no-claims
    d = folder(355)
    email(d, "Ember Smoke Lounge Arlington",
          "Hookah lounge on Abram St, we do hookah, tea and energy drinks, some beer and wine "
          "on weekends. Open to 1 am. Carrier A has us, no claims. Application attached.")
    app_md(d, 355, app(named="Ember Smoke Hookah Lounge LLC", mail="same as premises",
                       prem="1020 E Abram St, Arlington TX 76010", eff="2026-11-12", yrs="2",
                       entity="LLC", lob="Business owners policy with liquor liability",
                       ops="Hookah lounge, lounge seating, beer and wine", emp="6",
                       sales="$310,000", tiv="$130,000", bpp="$95,000", sqft="2,000",
                       constr="Frame", yb="1961", stories="1", spk="No",
                       cook="None", carrier="Carrier A", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_a("Ember Smoke Hookah Lounge LLC", ["2025-11-12 to 2026-11-12"],
                              "2026-08-21", []))

    # 356 garden apartments, 16 units, Carrier C claim
    d = folder(356)
    email(d, "Juniper Glen Apartments - 16 units",
          "16 unit apartments in Lufkin, two story, two buildings joined by a breezeway, one "
          "address. Owner is an LP. Carrier C loss run attached, one plumbing claim, fixed.")
    app_typed_pdf(d, 356, app(named="Juniper Glen Apartments LP", mail="PO Box 3350, Lufkin TX 75901",
                              prem="905 Juniper Glen Dr, Lufkin TX 75904", eff="2026-12-01",
                              yrs="9", entity="Limited partnership",
                              lob="Commercial property and liability",
                              ops="Residential apartments, 16 units", emp="3",
                              sales="$384,000 (rent roll)", tiv="$1,240,000", bpp="$22,000",
                              sqft="15,600", constr="Masonry", yb="1986", stories="2",
                              spk="No", cook="Electric ranges only", carrier="Carrier C",
                              claims="Plumbing leak 2026, closed", bk="No"))
    loss_md(d, lr_c("Juniper Glen Apartments LP", ["2025-12-01 to 2026-12-01"],
                              "2026-09-07",
                              [["C-50633", "2026-02-18", "plumbing leak, unit 9", "$8,750", "$0"]]))

    # 357 apartments, 8 units, Carrier B water claim
    d = folder(357)
    email(d, "Redbud Court - 8 unit",
          "8 units in Temple, one building, built 1974, we redid the kitchens and roof in 2022. "
          "Loss run from Carrier B, water claim last year, closed. Electric ranges in every unit.")
    app_md(d, 357, app(named="Redbud Court Apartments LLC", mail="same as premises",
                       prem="1812 Redbud Ct, Temple TX 76504", eff="2026-12-10", yrs="7",
                       entity="LLC", lob="Commercial property and liability",
                       ops="Residential apartments, 8 units", emp="1",
                       sales="$196,000 (rent roll)", tiv="$690,000", bpp="$12,000",
                       sqft="7,200", constr="Masonry", yb="1974", stories="2",
                       spk="No", cook="Electric ranges only", carrier="Carrier B",
                       claims="Water damage 2025, closed", bk="No"))
    loss_md(d, A.lr_carrier_b("Redbud Court Apartments LLC", ["2025-12-10 to 2026-12-10"],
                              "2026-06-15",
                              [["2025-12-29", "water damage, unit 4", "$4,600", "$0"]]))

    # 358 light manufacturing, metal fabrication shop, Carrier A fire claim
    d = folder(358)
    email(d, "Tejas Metal Fab - Pearland",
          "Light metal fab shop in Pearland, we make brackets and railings for commercial jobs. "
          "Shop has a welder and a chop saw. Had a small fire from a welding spark last year, "
          "put out with an extinguisher. Carrier A loss run attached.")
    app_md(d, 358, app(named="Tejas Metal Fabrication LLC", mail="same as premises",
                       prem="4410 Mykawa Rd, Pearland TX 77581", eff="2026-11-22", yrs="10",
                       entity="LLC", lob="Commercial property and general liability",
                       ops="Light metal fabrication, brackets and railings, shop",
                       emp="15", sales="$2,300,000", tiv="$780,000", bpp="$460,000",
                       sqft="12,500", constr="Metal", yb="2004", stories="1",
                       spk="Yes, wet pipe", cook="None", carrier="Carrier A",
                       claims="Welding spark fire 2025, closed", bk="No"))
    schedule(d, [row("application", "1", "4410 Mykawa Rd", "Pearland", "77581", "$780000",
                     "Metal", "2004", "12500", "Yes", "No")])
    loss_md(d, A.lr_carrier_a("Tejas Metal Fabrication LLC", ["2025-11-22 to 2026-11-22"],
                              "2026-07-22",
                              [["2025-11-03", "welding spark fire, shop, small", "$9,300", "$0", "closed"]]))

    # 359 flooring contractor, no loss run (missing document), email promises it
    d = folder(359)
    email(d, "Piney Creek Floors",
          "Floor install contractor in Tyler, hardwood, tile and LVP for homes and a few small "
          "offices. Five crew and two trucks. The loss run is coming from our old agent, I "
          "asked twice. Application is below.")
    app_md(d, 359, app(named="Piney Creek Floors LLC", mail="same as premises",
                       prem="611 Crestview Dr, Tyler TX 75701", eff="2026-12-01", yrs="6",
                       entity="LLC", lob="Contractors general liability",
                       ops="Flooring installation, hardwood, tile and vinyl", emp="7",
                       sales="$690,000", tiv="$110,000", bpp="$125,000", sqft="2,000",
                       constr="Masonry", yb="1992", stories="1", spk="No", cook="None",
                       carrier="Carrier C", claims="Unknown, loss run requested", bk="No"))

    # ------------------------------------------------------------ out of scope (360-371)
    # 360 criterion 1: scanned application
    d = folder(360)
    email(d, "Harmon Auto Trim - app scan",
          "Auto trim and upholstery in San Angelo. Application is a scan from the copier, "
          "sorry. Carrier B loss run attached, no claims.")
    app_scan(d, 360, app(named="Harmon Auto Trim LLC", mail="same as premises",
                         prem="318 Chadbourne St, San Angelo TX 76903", eff="2026-12-01",
                         yrs="10", entity="LLC", lob="Business owners policy",
                         ops="Auto trim and upholstery shop", emp="4", sales="$290,000",
                         tiv="$120,000", bpp="$70,000", sqft="2,200", constr="Masonry",
                         yb="1966", stories="1", spk="No", cook="None",
                         carrier="Carrier B", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_b("Harmon Auto Trim LLC", ["2025-12-01 to 2026-12-01"], "2026-07-07", []))

    # 361 criterion 1: image-only PDF application (printed, signed, scanned)
    d = folder(361)
    email(d, "Sabine Tire - pdf is a scan",
          "Tire and wheel shop in Beaumont, we printed the app and signed it, then scanned it, "
          "so it's a picture. Loss run from Carrier A typed, attached.")
    app_image_pdf(d, 361, app(named="Sabine Tire & Wheel LLC", mail="same as premises",
                              prem="2480 Eastex Fwy, Beaumont TX 77703", eff="2026-11-27",
                              yrs="12", entity="LLC", lob="Business owners policy",
                              ops="Tire and wheel service, retail tires", emp="6",
                              sales="$720,000", tiv="$200,000", bpp="$150,000", sqft="4,400",
                              constr="Masonry", yb="1978", stories="1", spk="No", cook="None",
                              carrier="Carrier A", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_a("Sabine Tire & Wheel LLC", ["2025-11-27 to 2026-11-27"],
                              "2026-05-13",
                              [["2026-01-08", "theft of wheels from yard", "$2,250", "$0", "closed"]]))

    # 362 criterion 2: two locations on the application and schedule
    d = folder(362)
    email(d, "Red Oak Glass - two shops",
          "Glass repair and install, main shop in Fort Worth and a second shop in Grapevine. "
          "Both are in the app and schedule. Carrier C loss run attached, one claim.")
    app_md(d, 362, app(named="Red Oak Glass Works LLC", mail="same as Loc 1",
                       prem="Loc 1: 5312 Bryant Irvin Rd, Fort Worth TX 76132; Loc 2: 1216 W State Hwy 114, Grapevine TX 76051",
                       eff="2026-12-01", yrs="8", entity="LLC", lob="Business owners policy",
                       ops="Glass repair and installation, two shops", emp="10",
                       sales="$980,000", tiv="$300,000", bpp="$150,000",
                       sqft="3,800 (Loc 1), 1,500 (Loc 2)", constr="Metal", yb="2001",
                       stories="1", spk="No", cook="None", carrier="Carrier C",
                       claims="Break-in 2025, closed", bk="No"))
    schedule(d, [row("application", "1", "5312 Bryant Irvin Rd", "Fort Worth", "76132", "$300000",
                     "Metal", "2001", "3800", "No", "No"),
                 row("application", "2", "1216 W State Hwy 114", "Grapevine", "76051", "$90000",
                     "Metal", "2014", "1500", "No", "No")])
    loss_md(d, lr_c("Red Oak Glass Works LLC", ["2025-12-01 to 2026-12-01"],
                              "2026-08-29",
                              [["C-50740", "2025-11-14", "break-in, tools stolen", "$6,200", "$0"]]))

    # 363 criterion 2: email says two locations, application lists only one, schedule has two
    d = folder(363)
    email(d, "Crescent Print - two sites",
          "Print shop on Rivercrest in Georgetown, plus a second press room over in Round Rock "
          "that we rent by the month. Application only has the main one, I forgot the second. "
          "Schedule has both. Loss run from B.")
    app_md(d, 363, app(named="Crescent Print Shop LLC", mail="same as premises",
                       prem="2001 Rivercrest Dr, Georgetown TX 78628", eff="2026-11-16",
                       yrs="5", entity="LLC", lob="Business owners policy",
                       ops="Commercial printing, digital and offset", emp="6",
                       sales="$470,000", tiv="$180,000", bpp="$160,000", sqft="3,000",
                       constr="Masonry", yb="1994", stories="1", spk="No", cook="None",
                       carrier="Carrier B", claims="None", bk="No"))
    schedule(d, [row("application", "1", "2001 Rivercrest Dr", "Georgetown", "78628", "$180000",
                     "Masonry", "1994", "3000", "No", "No"),
                 row("email", "2", "Press room, 1415 Sam Bass Rd", "Round Rock", "78681", "$40000",
                     "Metal", "2008", "1200", "No", "No")])
    loss_md(d, A.lr_carrier_b("Crescent Print Shop LLC", ["2025-11-16 to 2026-11-16"],
                              "2026-06-03", []))

    # 364 criterion 3: Spanish typed PDF application
    d = folder(364)
    email(d, "lavanderia Azul",
          "Laundromat in Brownsville, 24 machines, self serve. App is in Spanish, owner fills "
          "forms in Spanish. Loss run from Carrier B attached.")
    app_spanish_pdf(d, 364, [
        ("Asegurado", "Lavandería Azul LLC"),
        ("Dirección postal", "Mismo que la ubicación"),
        ("Dirección de la ubicación", "1140 E Price Rd, Brownsville TX 78521"),
        ("Fecha de vigencia", "2026-12-01"),
        ("Años en el negocio", "7"),
        ("Tipo de entidad", "LLC"),
        ("Operaciones", "Lavandería de autoservicio"),
        ("Número de empleados", "3"),
        ("Ventas anuales", "$210,000"),
        ("Valor del edificio", "$140,000"),
        ("Pies cuadrados", "2,600"),
        ("Construcción", "Masonería"),
        ("Año de construcción", "1989"),
        ("Rociadores", "No"),
        ("Aseguradora anterior", "Carrier B"),
    ])
    loss_md(d, A.lr_carrier_b("Lavandería Azul LLC", ["2025-12-01 to 2026-12-01"], "2026-07-19",
                              [["2026-02-24", "water leak, dryer line", "$1,950", "$0"]]))

    # 365 criterion 3: Spanish markdown application
    d = folder(365)
    email(d, "taller mendoza",
          "Auto repair shop in McAllen, 3 bays. I wrote the app in Spanish, it is all there. "
          "Carrier C loss run attached, no claims.")
    app_spanish_md(d, 365, [
        ("Asegurado", "Taller Mendoza Auto LLC"),
        ("Dirección de la ubicación", "2550 Nolana Ave, McAllen TX 78504"),
        ("Fecha de vigencia", "2026-12-08"),
        ("Años en el negocio", "11"),
        ("Operaciones", "Taller de reparación de autos, 3 bahías"),
        ("Número de empleados", "5"),
        ("Ventas anuales", "$560,000"),
        ("Valor del edificio", "$240,000"),
        ("Pies cuadrados", "3,000"),
        ("Año de construcción", "1980"),
        ("Rociadores", "No"),
        ("Aseguradora anterior", "Carrier C"),
    ])
    loss_md(d, lr_c("Taller Mendoza Auto LLC", ["2025-12-08 to 2026-12-08"],
                              "2026-09-11", []))

    # 366 criterion 4 alone: email only, no application
    d = folder(366)
    email(d, "roofing, need a quote",
          "Roofing and gutter company in Waco, 4 crews. Want liability and a truck policy. "
          "Owner is Dale. I'll send the app and loss run when I get back from the job site.")

    # 367 criterion 4 alone: email only
    d = folder(367)
    email(d, "landscape company, coverage question",
          "Landscape crew in Killeen, mowing and tree work for HOAs. Do you write this? Our "
          "carrier left in the spring and I need something by next month. Will send paperwork "
          "later.")

    # 368 criterion 1 + 2: scanned application listing two locations
    d = folder(368)
    email(d, "Brazos Bend Sign Works - scan",
          "Sign shop in Waco, main shop plus a small install yard in Bellmead. App is a copier "
          "scan. Loss run from carrier A attached.")
    app_scan(d, 368, app(named="Brazos Bend Sign Works LLC", mail="same as premises",
                         prem="Loc 1: 1906 Lake Shore Dr, Waco TX 76705; Loc 2: 400 Hillcrest Ave, Bellmead TX 76705",
                         eff="2026-12-14", yrs="9", entity="LLC", lob="Business owners policy",
                         ops="Sign fabrication and install, shop and yard", emp="8",
                         sales="$640,000", tiv="$190,000", bpp="$120,000",
                         sqft="3,000 (Loc 1), 2,000 (Loc 2)", constr="Metal", yb="1999",
                         stories="1", spk="No", cook="None", carrier="Carrier A",
                         claims="None", bk="No"))
    schedule(d, [row("application", "1", "1906 Lake Shore Dr", "Waco", "76705", "$190000",
                     "Metal", "1999", "3000", "No", "No"),
                 row("application", "2", "400 Hillcrest Ave", "Bellmead", "76705", "$60000",
                     "Metal", "2010", "2000", "No", "No")])
    loss_md(d, A.lr_carrier_a("Brazos Bend Sign Works LLC", ["2025-12-14 to 2026-12-14"],
                              "2026-08-06", []))

    # 369 criterion 2 + 3: Spanish typed PDF listing two stores
    d = folder(369)
    email(d, "panaderia dos tiendas",
          "Panadería in Harlingen and a second store in San Benito. Bread and pastries, the "
          "ovens are in the Harlingen store. App in Spanish with both addresses. Carrier A "
          "loss run attached.")
    app_spanish_pdf(d, 369, [
        ("Asegurado", "Panadería San Judas Inc"),
        ("Dirección postal", "PO Box 4402, Harlingen TX 78551"),
        ("Tienda 1", "1601 W Harrison Ave, Harlingen TX 78550 (horno y tienda)"),
        ("Tienda 2", "711 W Expressway 83, San Benito TX 78586 (tienda)"),
        ("Fecha de vigencia", "2026-12-15"),
        ("Años en el negocio", "14"),
        ("Operaciones", "Panadería, venta al menudeo"),
        ("Número de empleados", "12"),
        ("Ventas anuales", "$890,000"),
        ("Valor de los edificios", "$460,000"),
        ("Pies cuadrados", "Tienda 1: 3,100; Tienda 2: 1,200"),
        ("Construcción", "Masonería"),
        ("Rociadores", "No"),
        ("Aseguradora anterior", "Carrier A"),
    ])
    schedule(d, [row("application", "1", "1601 W Harrison Ave", "Harlingen", "78550", "$340000",
                     "Masonry", "1981", "3100", "No", "Yes"),
                 row("application", "2", "711 W Expressway 83", "San Benito", "78586", "$120000",
                     "Masonry", "1995", "1200", "No", "No")])
    loss_md(d, A.lr_carrier_a("Panadería San Judas Inc", ["2025-12-15 to 2026-12-15"],
                              "2026-09-28", []))

    # 370 criterion 1 + 3: Spanish application as an image-only PDF
    d = folder(370)
    email(d, "carpinteria rivera",
          "Cabinet and woodwork shop in Edinburg. Form is in Spanish and it's a scan, I signed "
          "it and scanned it. Carrier C loss run attached.")
    app_spanish_image_pdf(d, 370, [
        ("Asegurado", "Carpintería Rivera LLC"),
        ("Dirección de la ubicación", "1930 W Freddy Gonzalez Dr, Edinburg TX 78539"),
        ("Fecha de vigencia", "2026-12-01"),
        ("Años en el negocio", "9"),
        ("Operaciones", "Carpintería, gabinetes y muebles a medida"),
        ("Número de empleados", "6"),
        ("Ventas anuales", "$430,000"),
        ("Valor del edificio", "$210,000"),
        ("Pies cuadrados", "4,200"),
        ("Construcción", "Metal"),
        ("Año de construcción", "1993"),
        ("Rociadores", "No"),
        ("Aseguradora anterior", "Carrier C"),
    ])
    loss_md(d, lr_c("Carpintería Rivera LLC", ["2025-12-01 to 2026-12-01"],
                              "2026-08-18",
                              [["C-50851", "2026-03-30", "theft of hand tools", "$1,400", "$0"]]))

    # 371 criterion 2 + 4: email only, describes two sites
    d = folder(371)
    email(d, "pressure washing and sealing, 2 sites",
          "Pressure washing and parking lot sealing. We work out of Waco and Temple, two yards. "
          "I don't have the app filled in yet, I can send the numbers if you tell me what you "
          "need. Current carrier is in the file, I think it's C.")

    print("Wrote 32 submissions: SUB-340 .. SUB-371")


if __name__ == "__main__":
    build()
