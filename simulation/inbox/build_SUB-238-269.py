"""Builds SUB-238 to SUB-269 (T-117 hold-out inbox). Reuses the typed/scan helpers
of the T-108 builders by import only. Writes simulation/inbox/SUB-238..269 and nothing else.
Run: .venv/bin/python simulation/inbox/build_SUB-238-269.py"""
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


def app_spanish_md(d, sub, campos):
    O.write_text(os.path.join(d, "application.md"),
                 "\n".join(O.app_spanish_lines("SUB-%d" % sub, campos)))


def loss_md(d, lines):
    O.write_text(os.path.join(d, "loss-runs.md"), "\n".join(lines))


def loss_scan(d, lines):
    O.write_scan(os.path.join(d, "loss-runs_scan.jpg"), lines, FONT)


def loss_image_pdf(d, lines):
    O.write_image_pdf(os.path.join(d, "loss-runs.pdf"),
                      O.scan_jpeg_bytes(lines, FONT))


def schedule(d, rows):
    O.schedule_csv(os.path.join(d, "schedule.csv"), rows)


def row(source, loc, address, city, zip_, tiv, constr, yb, sqft, spk, cook):
    return {"source": source, "loc": loc, "address": address, "city": city, "zip": zip_,
            "bldg_tiv": tiv, "construction": constr, "year_built": yb, "sq_ft": sqft,
            "sprinklers": spk, "cooking": cook}


def build():
    for n in range(238, 270):
        path = os.path.join(HERE, "SUB-%d" % n)
        if os.path.isdir(path):
            shutil.rmtree(path)

    # ------------------------------------------------------------ in scope
    # 238 W1 nightclub, year built left off the application
    d = folder(238)
    email(d, "Cobalt Room - renewal, need quote asap",
          "Hi, this is for the Cobalt Room on Ash Street in Lubbock. We are open until 2 am "
          "Thu-Sat, DJ and dance floor, full liquor under our TABC license. No kitchen, just "
          "a prepackaged snack cooler. Old carrier wants out. I think the building is from "
          "the 80s but I'd have to dig for the exact year. Loss run attached.")
    app_md(d, 238, app(named="Cobalt Room Nightlife LLC", mail="PO Box 4410, Lubbock TX 79408",
                       prem="1907 Ash St, Lubbock TX 79401", eff="2026-12-01",
                       yrs="9", entity="LLC", lob="Commercial general liability, liquor liability",
                       ops="Nightclub, DJ and dance floor, bar service until 2 am",
                       emp="14", sales="$1,120,000", tiv="$310,000", bpp="$95,000",
                       sqft="5,600", constr="Masonry", stories="1",
                       spk="Partial (bar area only)", cook="None, prepackaged snacks only",
                       carrier="Carrier C", claims="None known",
                       bk="No"))
    loss_md(d, A.lr_carrier_c("Cobalt Room Nightlife LLC",
                              ["2024-03-01 to 2025-03-01", "2025-03-01 to 2026-03-01"],
                              "2026-06-12",
                              [["CL-771204", "2025-08-16", "liability, patron injury",
                                "$18,000", "$0"]]))

    # 239 W1 cocktail lounge, full liquor, image-only loss run
    d = folder(239)
    email(d, "Pale Moon Lounge - new business",
          "Looking to place the Pale Moon on Guadalupe in Austin. Cocktail lounge, full bar, "
          "live music on weekends, closes around midnight. No real kitchen, we heat up frozen "
          "pizza in a countertop oven. Built 1968. Scan of the loss run is attached as a PDF, "
          "sorry it is not typed.")
    app_md(d, 239, app(named="Pale Moon Lounge Inc", mail="same as premises",
                       prem="2210 Guadalupe St Unit A, Austin TX 78705", eff="2026-11-15",
                       yrs="4", entity="Corporation", lob="Commercial package",
                       ops="Cocktail lounge, full liquor, live music Fri and Sat",
                       emp="7", sales="$640,000", tiv="$240,000", bpp="$70,000",
                       sqft="2,900", constr="Frame", yb="1968", stories="1",
                       spk="No", cook="Countertop oven, frozen pizza only",
                       carrier="Carrier B", claims="One slip and fall, closed",
                       bk="No"))
    loss_image_pdf(d, [
        "CARRIER B LOSS HISTORY (FICTIONAL, SCAN)", "Insured: Pale Moon Lounge Inc",
        "Policy term: 2025-05-01 to 2026-05-01", "Valuation date: 2026-07-02",
        "Loss date 2025-11-09  slip and fall at bar  paid $4,200  outstanding $0",
        "Carrier B certifies the claims listed above."])

    # 240 sit-down Italian restaurant, beer and wine only, typed PDF application
    d = folder(240)
    email(d, "Rosetta Trattoria - new account",
          "Sit down Italian in San Marcos, about 60 seats. Beer and wine only, no hard liquor. "
          "Full kitchen with a wood oven. We had one grease fire in January that the hood "
          "system handled, the hood was cleaned after. Application is a PDF, I typed it out.")
    app_typed_pdf(d, 240, app(named="Rosetta Trattoria LLC", mail="same as premises",
                              prem="318 Hopkins St, San Marcos TX 78666", eff="2026-11-01",
                              yrs="6", entity="LLC", lob="Restaurant package",
                              ops="Full-service Italian restaurant, beer and wine, 60 seats",
                              emp="22", sales="$1,450,000", tiv="$380,000", bpp="$160,000",
                              sqft="3,400", constr="Masonry", yb="1994", stories="1",
                              spk="Yes, full", cook="Wood-fired oven, fryer, flat-top, hood with suppression",
                              carrier="Carrier B", claims="Grease fire Jan 2026, closed",
                              bk="No"))
    loss_md(d, A.lr_carrier_b("Rosetta Trattoria LLC", ["2025-09-01 to 2026-09-01"],
                              "2026-08-10",
                              [["2026-01-22", "grease fire, hood cleaned, small", "$7,800", "$0"]]))

    # 241 Vietnamese cafe, no alcohol, undated no-known-loss letter
    d = folder(241)
    email(d, "Saigon Mint Cafe",
          "Small cafe in Beaumont, 30 seats, coffee and noodle bowls, no alcohol. Never had a "
          "claim. Owner wrote a letter, he said that's all I can get. Application attached.")
    app_md(d, 241, app(named="Saigon Mint Cafe LLC", mail="same as premises",
                       prem="612 Calder Ave, Beaumont TX 77701", eff="2026-12-15",
                       yrs="3", entity="LLC", lob="Restaurant package",
                       ops="Cafe, coffee, noodle soup, sandwiches, no alcohol",
                       emp="5", sales="$380,000", tiv="$150,000", bpp="$45,000",
                       sqft="1,650", constr="Masonry", yb="1978", stories="1",
                       spk="No", cook="Gas range, fryer, hood",
                       carrier="None (new to coverage)", claims="None", bk="No"))
    loss_md(d, [
        "NO KNOWN LOSS LETTER (FICTIONAL)",
        "Applicant: Saigon Mint Cafe LLC",
        "To whom it may concern: to the best of my knowledge the applicant has had no",
        "losses or claims in the past five years at this location.",
        "Signed: Tuan Le, owner"])

    # 242 frozen seafood wholesale, Carrier A typed run with no valued line
    d = folder(242)
    email(d, "Gulf Coast Frozen - wholesale seafood",
          "Frozen shrimp and fish wholesale out of a 22k sq ft warehouse in Corpus. Two "
          "walk-in freezers and a dock. Loss run from our last carrier attached, it is the "
          "standard one.")
    app_md(d, 242, app(named="Gulf Coast Frozen Foods Inc", mail="PO Box 880, Corpus Christi TX 78403",
                       prem="4420 Navigation Blvd, Corpus Christi TX 78407", eff="2026-11-01",
                       yrs="11", entity="Corporation", lob="Commercial property and general liability",
                       ops="Wholesale distributor, frozen seafood, cold storage",
                       emp="16", sales="$5,900,000", tiv="$1,100,000", bpp="$640,000",
                       sqft="22,000", constr="Metal", yb="2001", stories="1",
                       spk="Yes, wet pipe", cook="None",
                       carrier="Carrier A", claims="Forklift door damage, closed", bk="No"))
    loss_md(d, A.lr_carrier_a("Gulf Coast Frozen Foods Inc",
                              ["2024-10-01 to 2025-10-01", "2025-10-01 to 2026-10-01"],
                              None,
                              [["2025-02-11", "forklift impact to cold room door", "$3,100",
                                "$0", "closed"]]))

    # 243 bicycle retail, allow-list style retail
    d = folder(243)
    email(d, "Pedal and Spoke - renewal",
          "Bike shop and repair in Round Rock. Retail floor plus a small repair bench. "
          "Renewing with same carrier, nothing new. Schedule attached.")
    app_md(d, 243, app(named="Pedal & Spoke Cycle Co LLC", mail="same as premises",
                       prem="905 Round Rock Ave Ste 4, Round Rock TX 78681", eff="2026-11-20",
                       yrs="12", entity="LLC", lob="Business owners policy",
                       ops="Retail bicycles, parts and repair service",
                       emp="6", sales="$890,000", tiv="$210,000", bpp="$180,000",
                       sqft="3,100", constr="Masonry", yb="1986", stories="1",
                       spk="Yes", cook="None", carrier="Carrier A",
                       claims="None", bk="No"))
    schedule(d, [row("application", "1", "905 Round Rock Ave Ste 4", "Round Rock", "78681",
                     "$210000", "Masonry", "1986", "3100", "Yes", "No")])
    loss_md(d, A.lr_carrier_a("Pedal & Spoke Cycle Co LLC",
                              ["2025-11-20 to 2026-11-20"], "2026-04-14", []))

    # 244 roofing contractor, no loss run at all
    d = folder(244)
    email(d, "Lone Star Roof Pros",
          "Roofing contractor out of Killeen, 9 trucks, yard and a small office. We need a "
          "quote by end of month. The loss run is coming from our old agent, should be "
          "Friday. Application below.")
    app_md(d, 244, app(named="Lone Star Roof Pros LLC", mail="same as premises",
                       prem="2803 Stan Schlueter Loop, Killeen TX 76542", eff="2026-11-01",
                       yrs="7", entity="LLC", lob="Contractors general liability",
                       ops="Residential and light commercial roofing, tear-off and install",
                       emp="19", sales="$2,300,000", tiv="$120,000", bpp="$310,000",
                       sqft="2,200", constr="Masonry", yb="1990", stories="1",
                       spk="No", cook="None", carrier="Carrier B",
                       claims="Unknown, loss run requested", bk="No"))

    # 245 garden apartments, 12 units, Carrier C typed run
    d = folder(245)
    email(d, "Mesquite Hollow apts - 12 units",
          "12 unit apartment complex in Abilene, two story walk ups, one building. "
          "Owner is an LP. Water damage claim last winter was fixed. Loss run from carrier C.")
    app_md(d, 245, app(named="Mesquite Hollow Apartments LP", mail="PO Box 1290, Abilene TX 79604",
                       prem="1450 Mesquite Hollow Dr, Abilene TX 79602", eff="2026-12-01",
                       yrs="10", entity="Limited partnership", lob="Commercial property and liability",
                       ops="Residential apartments, 12 units",
                       emp="2", sales="$310,000 (rent roll)", tiv="$920,000", bpp="$25,000",
                       sqft="11,800", constr="Frame", yb="1979", stories="2",
                       spk="No", cook="Electric ranges only", carrier="Carrier C",
                       claims="Water damage, closed", bk="No"))
    loss_md(d, A.lr_carrier_c("Mesquite Hollow Apartments LP",
                              ["2024-08-01 to 2025-08-01", "2025-08-01 to 2026-08-01"],
                              "2026-07-21",
                              [["CL-660118", "2025-12-04", "water damage, unit 6", "$9,400", "$0"]]))

    # 246 office building lessor, 14 suites (allow-list office lessor)
    d = folder(246)
    email(d, "Heritage Oak Office Plaza - renewal",
          "14 suite office building in Waco, all professional tenants (CPA, insurance, "
          "two law offices, a dentist's billing office). Two floors. Schedule is attached. "
          "Loss run from our carrier, clean except a roof leak in 2024.")
    app_md(d, 246, app(named="Heritage Oak Office Plaza LLC", mail="same as premises",
                       prem="4100 Heritage Oak Pkwy, Waco TX 76708", eff="2026-12-01",
                       yrs="13", entity="LLC", lob="Commercial property and general liability",
                       ops="Lessor of office building, 14 suites, professional tenants",
                       emp="3", sales="$842,000 (rent roll)", tiv="$2,650,000", bpp="$55,000",
                       sqft="18,400", constr="Masonry", yb="1999", stories="2",
                       spk="Yes, full", cook="None (no tenant food service)",
                       carrier="Carrier A", claims="Roof leak 2024, closed", bk="No"))
    schedule(d, [row("application", "1", "4100 Heritage Oak Pkwy", "Waco", "76708",
                     "$2650000", "Masonry", "1999", "18400", "Yes", "No")])
    loss_md(d, A.lr_carrier_a("Heritage Oak Office Plaza LLC",
                              ["2023-06-01 to 2024-06-01", "2024-06-01 to 2025-06-01",
                               "2025-06-01 to 2026-06-01"],
                              "2026-05-18",
                              [["2024-02-14", "roof leak, suite 204", "$6,800", "$0", "closed"]]))

    # 247 deli sandwich shop, Carrier B run with no claims
    d = folder(247)
    email(d, "Brisket and Bread Deli",
          "Deli in Lubbock, counter service, sandwiches and soups, we do catering too. No "
          "beer, no wine. Clean loss history. Application and loss run attached.")
    app_md(d, 247, app(named="Brisket & Bread Deli LLC", mail="same as premises",
                       prem="3015 34th St, Lubbock TX 79410", eff="2026-11-10",
                       yrs="5", entity="LLC", lob="Restaurant package, no liquor",
                       ops="Deli, counter service sandwiches and soups, catering",
                       emp="11", sales="$710,000", tiv="$185,000", bpp="$92,000",
                       sqft="2,300", constr="Masonry", yb="1982", stories="1",
                       spk="Yes, hood only", cook="Slicer, flat-top grill, steam table, hood",
                       carrier="Carrier B", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_b("Brisket & Bread Deli LLC", ["2025-11-10 to 2026-11-10"],
                              "2026-07-08", []))

    # 248 office lessor, 6 suites, dated no-known-loss letter (no carrier run)
    d = folder(248)
    email(d, "Cedar Mill Professional Center",
          "Six suite professional building in Tyler. Accountants, an insurance agency, a "
          "physical therapist. Owner says the building has been very quiet. Letter from the "
          "owner attached instead of a carrier run, they changed carriers in 2024.")
    app_md(d, 248, app(named="Cedar Mill Professional Center LLC", mail="same as premises",
                       prem="1880 Cedar Mill Rd, Tyler TX 75703", eff="2026-12-01",
                       yrs="8", entity="LLC", lob="Commercial property and general liability",
                       ops="Lessor of professional office building, six suites",
                       emp="2", sales="$224,000 (rent roll)", tiv="$780,000", bpp="$18,000",
                       sqft="6,200", constr="Masonry", yb="2005", stories="1",
                       spk="Yes", cook="None", carrier="Carrier C (2024 to 2026)",
                       claims="None", bk="No"))
    loss_md(d, [
        "NO KNOWN LOSS LETTER (FICTIONAL)",
        "Applicant: Cedar Mill Professional Center LLC",
        "As of 2026-09-15 the applicant reports no known losses or claims at this location",
        "since the policy with Carrier C began in 2024. Prior carrier history not included.",
        "Signed: Denise Holt, managing member"])

    # 249 deli with grocery market, square feet conflict (application vs schedule)
    d = folder(249)
    email(d, "Corner Stop Deli and Market - Amarillo",
          "Deli plus a little grocery market, the market is the back half of the building. "
          "We sell milk, chips and soda, no beer. "
          "Schedule has the square footage from the appraisal, the application I think is "
          "the old number.")
    app_md(d, 249, app(named="Corner Stop Deli & Market Inc", mail="same as premises",
                       prem="2120 S Georgia St, Amarillo TX 79109", eff="2026-11-05",
                       yrs="14", entity="Corporation", lob="Restaurant and mercantile package",
                       ops="Deli sandwiches and grocery market (milk, snacks, soda), no alcohol",
                       emp="9", sales="$1,040,000", tiv="$260,000", bpp="$135,000",
                       sqft="2,800", constr="Masonry", yb="1975", stories="1",
                       spk="No", cook="Slicer, grill, hood", carrier="Carrier B",
                       claims="One customer slip, closed", bk="No"))
    schedule(d, [row("appraisal 2025", "1", "2120 S Georgia St", "Amarillo", "79109",
                     "$260000", "Masonry", "1975", "3150", "No", "Yes")])
    loss_md(d, A.lr_carrier_b("Corner Stop Deli & Market Inc", ["2025-10-01 to 2026-10-01"],
                              "2026-09-30",
                              [["2026-03-07", "customer slip, market aisle", "$2,900", "$0"]]))

    # 250 two operations: tax office and phone repair retail
    d = folder(250)
    email(d, "Kestrel Tax and Phone Repair",
          "Two things in one building in El Paso. Upstairs is a tax prep office, downstairs "
          "is cell phone repair and accessories. Same owner, same policy. Loss run attached "
          "from the carrier, the theft was from the counter.")
    app_md(d, 250, app(named="Kestrel Tax & Phone Repair LLC", mail="same as premises",
                       prem="5500 Mesa St, El Paso TX 79912", eff="2026-11-01",
                       yrs="6", entity="LLC", lob="Business owners policy",
                       ops="Tax preparation office (second floor); cell phone repair and retail accessories (ground floor)",
                       emp="5", sales="$520,000", tiv="$275,000", bpp="$88,000",
                       sqft="2,700", constr="Masonry", yb="1984", stories="2",
                       spk="No", cook="None", carrier="Carrier A",
                       claims="Counter theft 2025, closed", bk="No"))
    schedule(d, [row("application", "1", "5500 Mesa St", "El Paso", "79912",
                     "$275000", "Masonry", "1984", "2700", "No", "No")])
    loss_md(d, A.lr_carrier_a("Kestrel Tax & Phone Repair LLC",
                              ["2025-04-02 to 2026-04-02"], "2026-04-02",
                              [["2025-09-18", "theft from counter, retail side", "$1,850",
                                "$0", "closed"]]))

    # 251 two operations: retail wine shop plus tasting room
    d = folder(251)
    email(d, "Grape and Gravel - wine shop",
          "Wine shop in New Braunfels, retail bottles on the main floor and a tasting room "
          "in the back. Tasting room pours wine and beer by the glass, no hard liquor, no "
          "kitchen, cheese boards only. Typed loss run from carrier C attached, no claims.")
    app_md(d, 251, app(named="Grape & Gravel Wine Shop LLC", mail="same as premises",
                       prem="210 San Antonio St, New Braunfels TX 78130", eff="2026-11-12",
                       yrs="4", entity="LLC", lob="Business owners policy with liquor liability",
                       ops="Retail wine shop; tasting room (wine and beer by the glass, no hard liquor)",
                       emp="6", sales="$610,000", tiv="$290,000", bpp="$140,000",
                       sqft="3,000", constr="Masonry", yb="1931", stories="1",
                       spk="Yes", cook="Cheese boards only, no cooking",
                       carrier="Carrier C", claims="None", bk="No"))
    schedule(d, [row("application", "1", "210 San Antonio St", "New Braunfels", "78130",
                     "$290000", "Masonry", "1931", "3000", "Yes", "No")])
    loss_md(d, A.lr_carrier_c("Grape & Gravel Wine Shop LLC", ["2025-07-01 to 2026-07-01"],
                              "2026-06-20", []))

    # 252 two operations: pub downstairs, two office suites upstairs (W1 pub)
    d = folder(252)
    email(d, "Hollow Oak Pub and Office Suites - Odessa",
          "Building on Grant Ave in Odessa. Bottom floor is a pub, full bar, pub food from "
          "a fryer and a warmer, no full kitchen. Top floor is two office suites, the "
          "owner's business and an accountant. Email says three suites, the application "
          "says two, the third is a storage room that I think counts. Loss run attached.")
    app_md(d, 252, app(named="Hollow Oak Pub & Office Suites LLC", mail="same as premises",
                       prem="612 Grant Ave, Odessa TX 79761", eff="2026-12-01",
                       yrs="5", entity="LLC", lob="Business owners policy with liquor liability",
                       ops="Pub with full bar on ground floor; two office suites on second floor",
                       emp="8", sales="$840,000", tiv="$330,000", bpp="$150,000",
                       sqft="4,100", constr="Frame", yb="1952", stories="2",
                       spk="No", cook="Fryer and warmer, no full kitchen",
                       carrier="Carrier C", claims="Liquor liability claim 2025, open review",
                       bk="No"))
    loss_md(d, A.lr_carrier_c("Hollow Oak Pub & Office Suites LLC", ["2025-03-03 to 2026-03-03"],
                              "2026-03-03",
                              [["CL-552901", "2025-10-30", "liquor liability, pub patron",
                                "$22,000", "$0"]]))

    # 253 Chinese restaurant, wok and hood, scanned loss run (JPG)
    d = folder(253)
    email(d, "Dragon Pearl - Wichita Falls",
          "Fast casual Chinese, wok line and a big hood. About 40 seats. No beer. Loss run "
          "is a scan from the carrier, sorry, it is what they sent. Hood was serviced in "
          "spring.")
    app_md(d, 253, app(named="Dragon Pearl Wok Kitchen Inc", mail="same as premises",
                       prem="1408 Kemp Blvd, Wichita Falls TX 76308", eff="2026-11-18",
                       yrs="7", entity="Corporation", lob="Restaurant package, no liquor",
                       ops="Fast casual Chinese, wok stir fry, counter service",
                       emp="13", sales="$980,000", tiv="$240,000", bpp="$120,000",
                       sqft="2,600", constr="Masonry", yb="1988", stories="1",
                       spk="Yes, hood and duct", cook="Wok range, deep fryer, hood",
                       carrier="Carrier B", claims="Hood suppression discharge, closed",
                       bk="No"))
    loss_scan(d, A.lr_carrier_b("Dragon Pearl Wok Kitchen Inc", ["2025-08-27 to 2026-08-27"],
                                "2026-08-27",
                                [["2026-02-02", "hood fire suppression discharged", "$3,350",
                                  "$0"]]))

    # 254 wholesale electrical supply, Carrier C typed run with no valued line
    d = folder(254)
    email(d, "Panhandle Electric Supply",
          "Electrical supply wholesale in Amarillo, 18,500 sq ft warehouse, we sell to "
          "contractors, counter pickup. Loss run from carrier C, it's the one they print, "
          "no date on it I think.")
    app_md(d, 254, app(named="Panhandle Electric Supply Co", mail="PO Box 2201, Amarillo TX 79189",
                       prem="6802 Hollywood Rd, Amarillo TX 79108", eff="2026-11-01",
                       yrs="18", entity="Corporation", lob="Commercial property and general liability",
                       ops="Wholesale electrical supplies to contractors, counter pickup",
                       emp="24", sales="$8,700,000", tiv="$1,450,000", bpp="$1,020,000",
                       sqft="18,500", constr="Masonry", yb="1997", stories="1",
                       spk="Yes", cook="None", carrier="Carrier C",
                       claims="Racking damage 2025, closed", bk="No"))
    schedule(d, [row("application", "1", "6802 Hollywood Rd", "Amarillo", "79108",
                     "$1450000", "Masonry", "1997", "18500", "Yes", "No")])
    loss_md(d, A.lr_carrier_c("Panhandle Electric Supply Co", ["2024-11-01 to 2025-11-01",
                                                              "2025-11-01 to 2026-11-01"],
                              None,
                              [["CL-713320", "2025-11-11", "forklift damage to racking",
                                "$5,200", "$0"]]))

    # 255 light manufacturing, custom cabinets, typed Carrier B run with a fire claim
    d = folder(255)
    email(d, "Mesquite Cabinet Works - Lufkin",
          "Custom wood cabinets, we run table saws and a dust collector in a metal building. "
          "Had a dust collector fire in January, put out fast, sprinkler not needed. Looking "
          "for a quote, the carrier is not renewing us at our current price.")
    app_md(d, 255, app(named="Mesquite Cabinet Works LLC", mail="same as premises",
                       prem="1105 Industrial Dr, Lufkin TX 75901", eff="2026-11-15",
                       yrs="10", entity="LLC", lob="Commercial property and general liability",
                       ops="Custom wood cabinets, millwork, shop with dust collection",
                       emp="17", sales="$2,150,000", tiv="$690,000", bpp="$430,000",
                       sqft="14,000", constr="Metal", yb="2006", stories="1",
                       spk="No", cook="None, shop heaters only", carrier="Carrier B",
                       claims="Dust collector fire 2026, closed", bk="No"))
    schedule(d, [row("application", "1", "1105 Industrial Dr", "Lufkin", "75901",
                     "$690000", "Metal", "2006", "14000", "No", "No")])
    loss_md(d, A.lr_carrier_b("Mesquite Cabinet Works LLC", ["2025-07-01 to 2026-07-01"],
                              "2026-06-30",
                              [["2026-01-14", "dust collector fire, shop", "$38,000", "$0"]]))

    # 256 garden apartments, 12 units, image-only PDF loss run
    d = folder(256)
    email(d, "Pecan Court Apartments - McAllen",
          "One building, 12 units, two floors, built in the 70s and rehabbed kitchens last "
          "year. Owner is an LP. Loss run from our carrier is a scanned PDF, the "
          "carrier sends them that way.")
    app_md(d, 256, app(named="Pecan Court Apartments LP", mail="PO Box 7712, McAllen TX 78502",
                       prem="2601 Pecan Ct, McAllen TX 78501", eff="2026-12-01",
                       yrs="12", entity="Limited partnership", lob="Commercial property and liability",
                       ops="Residential apartments, 12 units",
                       emp="2", sales="$268,000 (rent roll)", tiv="$850,000", bpp="$20,000",
                       sqft="10,400", constr="Masonry", yb="1974", stories="2",
                       spk="No", cook="Electric ranges only", carrier="Carrier C",
                       claims="Plumbing leak 2025, closed", bk="No"))
    schedule(d, [row("application", "1", "2601 Pecan Ct", "McAllen", "78501",
                     "$850000", "Masonry", "1974", "10400", "No", "No")])
    loss_image_pdf(d, A.lr_carrier_c("Pecan Court Apartments LP",
                                     ["2024-06-01 to 2025-06-01", "2025-06-01 to 2026-06-01"],
                                     "2026-05-05",
                                     [["CL-598711", "2025-10-02", "plumbing leak, unit 3",
                                       "$6,100", "$0"]]))

    # 257 thrift and clothing retail, revenue conflict (application vs email)
    d = folder(257)
    email(d, "Second Chance Threads and Thrift",
          "Thrift store in Brownsville, clothing and household goods, donations in the back. "
          "Last year was about 540k in sales, the application says 412k because the "
          "accountant used the tax form number. Loss run attached, shoplifting only.")
    app_md(d, 257, app(named="Second Chance Threads & Thrift LLC", mail="same as premises",
                       prem="1290 Boca Chica Blvd, Brownsville TX 78521", eff="2026-11-01",
                       yrs="3", entity="LLC", lob="Business owners policy",
                       ops="Thrift retail, used clothing and household goods",
                       emp="7", sales="$412,000", tiv="$160,000", bpp="$110,000",
                       sqft="4,200", constr="Masonry", yb="1968", stories="1",
                       spk="No", cook="None", carrier="Carrier A",
                       claims="Shoplifting 2026, closed", bk="No"))
    schedule(d, [row("application", "1", "1290 Boca Chica Blvd", "Brownsville", "78521",
                     "$160000", "Masonry", "1968", "4200", "No", "No")])
    loss_md(d, A.lr_carrier_a("Second Chance Threads & Thrift LLC",
                              ["2025-09-01 to 2026-09-01"], "2026-09-01",
                              [["2026-04-19", "shoplifting, cash loss", "$750", "$0", "closed"]]))

    # ------------------------------------------------------------ out of scope
    # 258, 259: criterion 4 alone (email only)
    d = folder(258)
    email(d, "new one, window tint installer",
          "Commercial window tint for offices and a few storefronts in Dallas area. Two vans, "
          "five guys. Owner wants a quote, will send more details later, the old carrier "
          "dropped us.")
    d = folder(259)
    email(d, "tree trimming, need coverage",
          "Tree trimming and lot clearing crew based in Waco. Mostly residential jobs but "
          "some commercial lots. Owner is Gary. Can you quote liability and a truck policy? "
          "I'll get the rest to you once I hear back from him.")

    # 260 criterion 1: scanned application
    d = folder(260)
    email(d, "upholstery shop, scanned app",
          "Upholstery and trim shop in San Angelo, auto and furniture. Application is "
          "scanned, sorry, it's from the copy machine. Loss run attached.")
    app_scan(d, 260, app(named="Lone Star Upholstery & Trim LLC", mail="same as premises",
                         prem="419 Koenigheim St, San Angelo TX 76903", eff="2026-12-01",
                         yrs="9", entity="LLC", lob="Business owners policy",
                         ops="Upholstery for auto and furniture, fabric shop",
                         emp="4", sales="$360,000", tiv="$140,000", bpp="$85,000",
                         sqft="2,400", constr="Masonry", yb="1960", stories="1",
                         spk="No", cook="None", carrier="Carrier B",
                         claims="None", bk="No"))
    loss_md(d, A.lr_carrier_b("Lone Star Upholstery & Trim LLC", ["2025-12-01 to 2026-12-01"],
                              "2026-06-01", []))

    # 261 criterion 1: image-only PDF application, schedule, loss run
    d = folder(261)
    email(d, "Colorado River auto parts - application is a pdf scan",
          "Auto parts retail in Temple, counter and a small warehouse in the back. Printed "
          "the application, signed it, scanned it, so it's a picture. Schedule is typed.")
    app_image_pdf(d, 261, app(named="Colorado River Auto Parts Supply LLC", mail="same as premises",
                              prem="2208 S 31st St, Temple TX 76504", eff="2026-11-25",
                              yrs="15", entity="LLC", lob="Business owners policy",
                              ops="Auto parts retail and wholesale to local shops",
                              emp="10", sales="$1,300,000", tiv="$330,000", bpp="$260,000",
                              sqft="6,800", constr="Masonry", yb="1989", stories="1",
                              spk="Yes", cook="None", carrier="Carrier A",
                              claims="Shoplifting 2025, closed", bk="No"))
    schedule(d, [row("application", "1", "2208 S 31st St", "Temple", "76504",
                     "$330000", "Masonry", "1989", "6800", "Yes", "No")])
    loss_md(d, A.lr_carrier_a("Colorado River Auto Parts Supply LLC", ["2025-11-25 to 2026-11-25"],
                              "2026-08-03",
                              [["2025-11-20", "shoplifting", "$900", "$0", "closed"]]))

    # 262 criterion 1: scanned application
    d = folder(262)
    email(d, "dental lab - scanned application",
          "Dental lab, we make crowns and dentures for three offices in Abilene. Not a "
          "retail thing, all work order. Attached the app as a scan and the carrier letter.")
    app_scan(d, 262, app(named="Prairie Smile Dental Lab LLC", mail="same as premises",
                         prem="1714 Sayles Blvd, Abilene TX 79605", eff="2026-12-01",
                         yrs="6", entity="LLC", lob="Business owners policy",
                         ops="Dental lab, crowns, dentures, appliances",
                         emp="8", sales="$690,000", tiv="$170,000", bpp="$210,000",
                         sqft="2,100", constr="Masonry", yb="1995", stories="1",
                         spk="No", cook="None", carrier="Carrier C",
                         claims="None", bk="No"))
    loss_md(d, A.lr_carrier_c("Prairie Smile Dental Lab LLC", ["2025-12-01 to 2026-12-01"],
                              "2026-07-14", []))

    # 263 criterion 1 + 2: scanned application, shop and storage unit in a second town
    d = folder(263)
    email(d, "sign shop plus storage",
          "Sign and print shop in Kerrville, main shop on Water St and a storage unit in "
          "Fredericksburg where we keep the big vinyl rolls. Scan of the app attached. Loss "
          "run from carrier B.")
    app_scan(d, 263, app(named="Hill Country Sign & Print Co", mail="same as premises",
                         prem="801 Water St, Kerrville TX 78028; storage unit 4, Fredericksburg TX 78624",
                         eff="2026-11-30", yrs="11", entity="Corporation",
                         lob="Business owners policy",
                         ops="Sign making and digital print, vinyl wraps",
                         emp="6", sales="$520,000", tiv="$205,000", bpp="$190,000",
                         sqft="3,600 (shop), 900 (storage)", constr="Masonry", yb="1980",
                         stories="1", spk="No", cook="None", carrier="Carrier B",
                         claims="Sign truck damage 2025, closed", bk="No"))
    schedule(d, [row("application", "1", "801 Water St", "Kerrville", "78028", "$205000",
                     "Masonry", "1980", "3600", "No", "No"),
                 row("application", "2", "Storage unit 4", "Fredericksburg", "78624",
                     "$25000", "Metal", "2012", "900", "No", "No")])
    loss_md(d, A.lr_carrier_b("Hill Country Sign & Print Co", ["2025-05-29 to 2026-05-29"],
                              "2026-05-29",
                              [["2025-12-12", "vehicle damage, sign truck", "$4,700", "$0"]]))

    # 264 criterion 2: diner, Location No. 2 on the application
    d = folder(264)
    email(d, "Maple Street Diner - two spots",
          "Diner in Brenham, breakfast and lunch, plus we just opened a second spot in "
          "Navasota. Both are full kitchens. Application lists both, schedule has both. "
          "Loss run from our carrier.")
    app_md(d, 264, app(named="Maple Street Diner Inc", mail="same as Location 1",
                       prem="Location 1: 402 Maple St, Brenham TX 77833; Location No. 2: 115 E Washington Ave, Navasota TX 77868",
                       eff="2026-12-10", yrs="8", entity="Corporation",
                       lob="Restaurant package, no liquor",
                       ops="Breakfast and lunch diner, no alcohol",
                       emp="21", sales="$1,460,000", tiv="$310,000", bpp="$180,000",
                       sqft="3,000 (Loc 1), 2,600 (Loc No. 2)", constr="Masonry",
                       yb="1956 (Loc 1), 1998 (Loc No. 2)", stories="1",
                       spk="Yes, hood", cook="Grill, fryer, oven, hood at both",
                       carrier="Carrier A", claims="Grease fire Loc 1, 2026, closed", bk="No"))
    schedule(d, [row("application", "1", "402 Maple St", "Brenham", "77833", "$310000",
                     "Masonry", "1956", "3000", "Yes", "Yes"),
                 row("application", "2", "115 E Washington Ave", "Navasota", "77868",
                     "$280000", "Masonry", "1998", "2600", "Yes", "Yes")])
    loss_md(d, A.lr_carrier_a("Maple Street Diner Inc", ["2025-12-10 to 2026-12-10"],
                              "2026-09-09",
                              [["2026-03-03", "grease fire, range hood, Loc 1", "$11,200",
                                "$0", "closed"]]))

    # 265 criterion 2: auto glass and detail, Loc #2 on the application
    d = folder(265)
    email(d, "auto glass and detailing, two locs",
          "Auto glass install and detailing bays. Main shop in Killeen and the Loc #2 is "
          "a detail only bay in Harker Heights. Both have a compressor. Loss run attached, "
          "carrier C.")
    app_md(d, 265, app(named="Clearview Auto Glass & Detail LLC", mail="same as Loc #1",
                       prem="Loc #1: 3307 E Central Texas Expy, Killeen TX 76543; Loc #2: 920 Indian Trail, Harker Heights TX 76548",
                       eff="2026-11-20", yrs="5", entity="LLC", lob="Business owners policy",
                       ops="Auto glass replacement, auto detailing",
                       emp="9", sales="$730,000", tiv="$260,000", bpp="$140,000",
                       sqft="4,000 (Loc #1), 1,800 (Loc #2)", constr="Metal",
                       yb="2003", stories="1", spk="No", cook="None",
                       carrier="Carrier C", claims="None", bk="No"))
    schedule(d, [row("application", "1", "3307 E Central Texas Expy", "Killeen", "76543",
                     "$260000", "Metal", "2003", "4000", "No", "No"),
                 row("application", "2", "920 Indian Trail", "Harker Heights", "76548",
                     "$90000", "Metal", "2010", "1800", "No", "No")])
    loss_md(d, A.lr_carrier_c("Clearview Auto Glass & Detail LLC", ["2025-11-20 to 2026-11-20"],
                              "2026-08-20", []))

    # 266 criterion 3: Spanish typed application (laundry)
    d = folder(266)
    email(d, "lavanderia, application en español",
          "Laundromat in Harlingen, 30 machines, self serve and drop off. Application is in "
          "Spanish, the owner fills out the forms in Spanish. Loss run from carrier B "
          "attached.")
    app_spanish_pdf(d, 266, [
        ("Asegurado", "Lavandería Espuma LLC"),
        ("Dirección postal", "Mismo que la ubicación"),
        ("Dirección de la ubicación", "1502 W Tyler Ave, Harlingen TX 78550"),
        ("Fecha de vigencia", "2026-12-01"),
        ("Años en el negocio", "8"),
        ("Tipo de entidad", "LLC"),
        ("Operaciones", "Lavandería de autoservicio y servicio a domicilio"),
        ("Número de empleados", "5"),
        ("Ventas anuales", "$295,000"),
        ("Valor del edificio", "$180,000"),
        ("Pies cuadrados", "2,900"),
        ("Construcción", "Masonería"),
        ("Año de construcción", "1985"),
        ("Rociadores", "No"),
        ("Aseguradora anterior", "Carrier B"),
    ])
    loss_md(d, A.lr_carrier_b("Lavandería Espuma LLC", ["2025-12-01 to 2026-12-01"],
                                         "2026-06-10",
                                         [["2025-10-09", "water leak, dryer line", "$2,300", "$0"]]))

    # 267 criterion 3: Spanish letter application (nail salon)
    d = folder(267)
    email(d, "salon de unas (luna)",
          "Nail salon in McAllen, 6 stations, walk in. The app is in Spanish, my English is "
          "not great so I filled it in Spanish. Loss run is from carrier C.")
    app_spanish_md(d, 267, [
        ("Asegurado", "Salón Luna Nails LLC"),
        ("Dirección de la ubicación", "2108 N 10th St, McAllen TX 78501"),
        ("Fecha de vigencia", "2026-12-05"),
        ("Años en el negocio", "4"),
        ("Operaciones", "Salón de uñas, manicura y pedicura"),
        ("Número de empleados", "4"),
        ("Ventas anuales", "$240,000"),
        ("Valor del edificio", "No aplica, local rentado"),
        ("Pies cuadrados", "1,400"),
        ("Año de construcción", "1999"),
        ("Rociadores", "No"),
        ("Aseguradora anterior", "Carrier C"),
    ])
    loss_md(d, A.lr_carrier_c("Salón Luna Nails LLC", ["2025-12-05 to 2026-12-05"],
                              "2026-07-30", []))

    # 268 criterion 2 + 3: Spanish typed application, two branches
    d = folder(268)
    email(d, "tortilleria dos sucursales",
          "Tortilla factory and store in Edinburg, and a second store in Mission that sells "
          "the same. Application in Spanish with both branches on it. Schedule attached. "
          "Loss run from carrier A.")
    app_spanish_pdf(d, 268, [
        ("Asegurado", "Tortillería Doña Chela Inc"),
        ("Dirección postal", "PO Box 655, Edinburg TX 78540"),
        ("Sucursal 1", "1815 S Closner Blvd, Edinburg TX 78539 (fábrica y tienda)"),
        ("Sucursal 2", "903 E Griffin Pkwy, Mission TX 78572 (tienda)"),
        ("Fecha de vigencia", "2026-12-01"),
        ("Años en el negocio", "13"),
        ("Operaciones", "Fabricación de tortillas, venta al menudeo"),
        ("Número de empleados", "19"),
        ("Ventas anuales", "$1,850,000"),
        ("Valor de los edificios", "$640,000"),
        ("Pies cuadrados", "Sucursal 1: 5,200; Sucursal 2: 1,600"),
        ("Construcción", "Masonería"),
        ("Rociadores", "Sí, en Sucursal 1"),
        ("Aseguradora anterior", "Carrier A"),
    ])
    schedule(d, [row("application", "1", "1815 S Closner Blvd", "Edinburg", "78539",
                     "$520000", "Masonry", "1990", "5200", "Yes", "Yes"),
                 row("application", "2", "903 E Griffin Pkwy", "Mission", "78572",
                     "$120000", "Masonry", "2011", "1600", "No", "No")])
    loss_md(d, A.lr_carrier_a("Tortillería Doña Chela Inc", ["2025-12-01 to 2026-12-01"],
                              "2026-09-22",
                              [["2026-01-30", "walk-in cooler compressor failure", "$8,400",
                                "$0", "closed"]]))

    # 269 criterion 2 + 3: Spanish letter application, two stores
    d = folder(269)
    email(d, "celulares dos tiendas",
          "Cell phone store with two locations in Laredo, Tienda Norte and Tienda Sur. Both "
          "sell phones and accessories and do repairs. I wrote the app in Spanish like "
          "always. Loss run from carrier B.")
    app_spanish_md(d, 269, [
        ("Asegurado", "Celulares Norte y Sur LLC"),
        ("Dirección postal", "PO Box 9120, Laredo TX 78042"),
        ("Tienda Norte", "5210 McPherson Rd, Laredo TX 78041"),
        ("Tienda Sur", "2101 San Bernardo Ave, Laredo TX 78040"),
        ("Fecha de vigencia", "2026-12-15"),
        ("Años en el negocio", "6"),
        ("Operaciones", "Venta de celulares, accesorios y reparación"),
        ("Número de empleados", "8"),
        ("Ventas anuales", "$710,000"),
        ("Valor del edificio", "$150,000 (entre las dos tiendas)"),
        ("Pies cuadrados", "Norte: 1,800; Sur: 1,300"),
        ("Construcción", "Masonería"),
        ("Rociadores", "No"),
        ("Aseguradora anterior", "Carrier B"),
    ])
    schedule(d, [row("application", "1", "5210 McPherson Rd", "Laredo", "78041", "$90000",
                     "Masonry", "2001", "1800", "No", "No"),
                 row("application", "2", "2101 San Bernardo Ave", "Laredo", "78040",
                     "$60000", "Masonry", "1994", "1300", "No", "No")])
    loss_md(d, A.lr_carrier_b("Celulares Norte y Sur LLC", ["2025-12-15 to 2026-12-15"],
                              "2026-08-12", []))

    print("Wrote 32 submissions: SUB-238 .. SUB-269")


if __name__ == "__main__":
    build()
