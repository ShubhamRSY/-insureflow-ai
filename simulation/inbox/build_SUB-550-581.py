"""Builds SUB-550 to SUB-581 (T-128 hold-out inbox): 20 in scope (550-569), 12 out of scope (570-581).
Out of scope: criterion 1 = 570-571, criterion 2 = 572-577 (572 second address is a highway in a sentence that names a carrier,
573 second address on the line below "Mailing address: same as premises", 574-577 words only), 3 = 578-579, 4 = 580-581.
Scope rule (P-077, D-146, D-149, P-080): a different premises street, highway or route address in any document, or a second
store/branch/shop in words (incl. a sold or closed one), is out of scope. In-scope near-misses: 567 "two floors", 568 "2nd floor",
569 "two entrances", 550 "One address, one building". Highway premises in scope: 550 (Hwy 71 W), 552 (US-59 N), B-525 forms avoided.
Reuses the typed/scan helpers of the T-108 and T-117 builders by import only. Writes simulation/inbox/SUB-550..581 and nothing else.
Idempotent: removes and rebuilds only SUB-550..SUB-581.
Run: .venv/bin/python simulation/inbox/build_SUB-550-581.py"""
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
    for n in range(550, 582):
        path = os.path.join(HERE, "SUB-%d" % n)
        if os.path.isdir(path):
            shutil.rmtree(path)

    # ============================================================ in scope (550-569)
    # 550 office tenant on a highway (Hwy 71 W). Carrier A clean. Direct A. Email: "One address, one building."
    d = folder(550)
    email(d, 'Yaupon Ridge Advisors - renewal',
          'Renewal request. The insured rents a single office on Hwy 71 in Bastrop, and everything is under one roof at the address on the application. Clean Carrier A history; the run is attached.')
    app_md(d, 550, app(named="Yaupon Ridge Advisors LLC", mail="same as premises",
                       prem="2604 Hwy 71 W, Bastrop TX 78602", eff="2026-12-10",
                       yrs="9", entity="LLC", lob="Business owners policy",
                       ops="Office", emp="4", sales="$520,000",
                       tiv="$112,000", bpp="$61,000", sqft="1,900", constr="Masonry", yb="2006",
                       stories="1", spk="Yes", cook="None", carrier="Carrier A", claims="None",
                       bk="No"))
    loss_md(d, A.lr_carrier_a("Yaupon Ridge Advisors LLC", ["2025-12-10 to 2026-12-10"],
                              "2026-09-22", []))

    # 551 apparel boutique, typed PDF app. Carrier A clean. Direct A.
    d = folder(551)
    email(d, 'Calico Thread Apparel - Denton',
          'Please quote the attached typed application as a renewal. Carrier A wrote the expiring policy and the attached run shows nothing reported.')
    app_typed_pdf(d, 551, app(named="Calico Thread Apparel LLC", mail="same as premises",
                              prem="1417 W University Dr, Denton TX 76201", eff="2026-12-15",
                              yrs="6", entity="LLC", lob="Business owners policy",
                              ops="Apparel boutique", emp="5", sales="$445,000",
                              tiv="$141,000", bpp="$103,000", sqft="2,350", constr="Masonry",
                              yb="1989", stories="1", spk="No", cook="None", carrier="Carrier A",
                              claims="None", bk="No"))
    loss_md(d, A.lr_carrier_a("Calico Thread Apparel LLC", ["2025-12-15 to 2026-12-15"],
                              "2026-08-27", []))

    # 552 dry retail storefront on a highway (US-59 N), md app. Carrier A clean. Direct A.
    d = folder(552)
    email(d, 'Big Thicket Dry Goods - Livingston',
          'New quote request for a storefront on US-59 in Livingston. The Carrier A run is attached and shows no losses.')
    app_md(d, 552, app(named="Big Thicket Dry Goods LLC", mail="same as premises",
                       prem="3115 US-59 N, Livingston TX 77351", eff="2027-01-06", yrs="14",
                       entity="LLC", lob="Business owners policy", ops="Dry retail storefront",
                       emp="6", sales="$560,000", tiv="$186,000", bpp="$124,000", sqft="4,100",
                       constr="Metal", yb="1997", stories="1", spk="No", cook="None",
                       carrier="Carrier A", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_a("Big Thicket Dry Goods LLC", ["2026-01-06 to 2027-01-06"],
                              "2026-10-05", []))

    # 553 office suite tenant, typed PDF app. Carrier A clean. Direct A.
    d = folder(553)
    email(d, 'Pecan Bayou Consulting',
          'Small office suite on Austin Ave in Brownwood. Renewal, Carrier A expiring, no losses on the attached run. Typed app enclosed.')
    app_typed_pdf(d, 553, app(named="Pecan Bayou Consulting LLC", mail="same as premises",
                              prem="1902 Austin Ave Ste 3, Brownwood TX 76801",
                              eff="2026-12-23", yrs="7", entity="LLC", lob="Business owners policy",
                              ops="Office suite", emp="3",
                              sales="$585,000", tiv="$72,000", bpp="$46,000", sqft="1,250",
                              constr="Frame", yb="2011", stories="1", spk="No",
                              cook="None", carrier="Carrier A", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_a("Pecan Bayou Consulting LLC", ["2025-12-23 to 2026-12-23"],
                              "2026-09-30", []))

    # 554 electrical contractor, typed PDF app. Planted conflict: square footage (email 2,450, app 3,150), plain figures.
    d = folder(554)
    email(d, 'Sabine Current Electric - square footage',
          'Quick correction before you quote: the landlord measured the shop at 2,450 square feet, so ignore the 3,150 on the application, it is wrong. Electrical contractor in Orange running six vans. One van claim on the Carrier B run, attached.')
    app_typed_pdf(d, 554, app(named="Sabine Current Electric LLC", mail="same as premises",
                              prem="2810 N 16th St, Orange TX 77630", eff="2026-12-04",
                              yrs="12", entity="LLC", lob="Contractors general liability",
                              ops="Electrical contractor, shop and yard",
                              emp="14", sales="$1,620,000", tiv="$238,000", bpp="$171,000",
                              sqft="3,150", constr="Metal", yb="1995", stories="1",
                              spk="No", cook="None", carrier="Carrier B",
                              claims="Van backing claim 2026, closed", bk="No"))
    loss_md(d, A.lr_carrier_b("Sabine Current Electric LLC", ["2025-12-04 to 2026-12-04"],
                              "2026-08-18",
                              [["2026-03-17", "vehicle damage, van backed into gate post", "$2,260", "$0"]]))

    # 555 packaging goods wholesale. Planted conflict: annual sales, worded (email "$1.9 million", app $1,640,000).
    d = folder(555)
    email(d, 'Ship Channel Packaging Supply - renewal',
          'Renewal for a wholesale packaging distributor in Pasadena (boxes, tape, shipping bags) working out of one warehouse on Fairmont Pkwy. Actual sales for last year: $1.9 million. The application still shows the old projection. Carrier C run attached; no claims.')
    app_md(d, 555, app(named="Ship Channel Packaging Supply LLC", mail="same as premises",
                       prem="6120 Fairmont Pkwy, Pasadena TX 77505", eff="2026-12-18", yrs="11",
                       entity="LLC", lob="Commercial property and general liability",
                       ops="Wholesale packaging goods, warehouse", emp="12",
                       sales="$1,640,000", tiv="$585,000", bpp="$362,000", sqft="11,800",
                       constr="Metal", yb="2004", stories="1", spk="Yes", cook="None",
                       carrier="Carrier C", claims="None", bk="No"))
    loss_md(d, lr_c("Ship Channel Packaging Supply LLC", ["2025-12-18 to 2026-12-18"],
                    "2026-09-14", []))

    # 556 landscaping contractor, mailing PO Box (role-labelled). Planted conflict: sales, plain (email 812,000, app $745,000).
    d = folder(556)
    email(d, 'Redbud Lawn & Landscape - Marshall',
          "Landscaper in Marshall: mowing, planting and irrigation repair, with seven on the crew and four trucks. Please use 812,000 for sales, that is the last 12 months; the application carries last year's figure. Mail should go to the PO Box. No claims on the Carrier B run.")
    app_md(d, 556, app(named="Redbud Lawn & Landscape LLC", mail="PO Box 4417, Marshall TX 75671",
                       prem="2207 Victory Dr, Marshall TX 75672", eff="2026-12-21", yrs="10",
                       entity="LLC", lob="Contractors general liability",
                       ops="Landscaping contractor, mowing and planting", emp="9",
                       sales="$745,000", tiv="$118,000", bpp="$93,000", sqft="1,800",
                       constr="Metal", yb="1990", stories="1", spk="No", cook="None",
                       carrier="Carrier B", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_b("Redbud Lawn & Landscape LLC", ["2025-12-21 to 2026-12-21"],
                              "2026-09-09", []))

    # 557 office building lessor. Planted conflict: suite count, plain (email 10 suites, app 9 suites).
    # The only hold is the conflict: an underwriter resolving it (P-081) would make the file routable; gold is scored before any action.
    d = folder(557)
    email(d, 'Louetta Oaks Executive Suites - Spring',
          'Update on the office building in Spring: a title company signed for the last open suite in October, so 10 suites are now leased, not the 9 on the application. All tenants are professional offices. Carrier C run attached, no claims.')
    app_md(d, 557, app(named="Louetta Oaks Executive Suites LLC", mail="same as premises",
                       prem="7015 Louetta Rd, Spring TX 77379", eff="2026-12-28", yrs="13",
                       entity="LLC", lob="Commercial property and general liability",
                       ops="Lessor of office building, 9 suites, professional tenants", emp="2",
                       sales="$655,000 (rent roll)", tiv="$1,430,000", bpp="$38,000",
                       sqft="11,600", constr="Masonry", yb="2005", stories="2",
                       spk="Yes, full", cook="None", carrier="Carrier C", claims="None", bk="No"))
    loss_md(d, lr_c("Louetta Oaks Executive Suites LLC", ["2025-12-28 to 2026-12-28"],
                    "2026-10-08", []))

    # 558 office building lessor. Planted conflict: floor area, approximate (email about 4,300, app 4,900).
    d = folder(558)
    email(d, 'Chisos Professional Plaza - San Angelo',
          'San Angelo office building with five suites, about 4,300 sq ft in all by my estimate. Tenants: an engineer, a CPA, a title company, a land surveyor and an insurance agent. The Carrier C run shows nothing.')
    app_md(d, 558, app(named="Chisos Professional Plaza LLC", mail="same as premises",
                       prem="3014 Sherwood Way, San Angelo TX 76901", eff="2027-01-11", yrs="8",
                       entity="LLC", lob="Commercial property and general liability",
                       ops="Lessor of office building, 5 suites, professional tenants", emp="1",
                       sales="$362,000 (rent roll)", tiv="$980,000", bpp="$19,000",
                       sqft="4,900", constr="Masonry", yb="2012", stories="1",
                       spk="Yes, full", cook="None", carrier="Carrier C", claims="None", bk="No"))
    loss_md(d, lr_c("Chisos Professional Plaza LLC", ["2026-01-11 to 2027-01-11"],
                    "2026-10-12", []))

    # 559 roofing contractor, Carrier B hail claim. Planted conflict: TIV, plain (email 980,000, app $845,000).
    d = folder(559)
    email(d, 'Caprock Roofing - Lubbock',
          'Lubbock roofer, 16 on staff, mostly commercial work with some residential. There is a shop plus a material yard. An appraisal this spring put the building at 980,000; please use that instead of the older value on the application. Carrier B run attached with one hail claim.')
    app_md(d, 559, app(named="Caprock Roofing Co", mail="same as premises",
                       prem="4415 Clovis Rd, Lubbock TX 79415", eff="2026-12-30",
                       yrs="18", entity="Corporation", lob="Contractors general liability",
                       ops="Roofing contractor, shop and material yard",
                       emp="16", sales="$2,040,000", tiv="$845,000", bpp="$196,000",
                       sqft="6,900", constr="Metal", yb="2000", stories="1", spk="No",
                       cook="None", carrier="Carrier B", claims="Hail roof damage 2026, closed",
                       bk="No"))
    loss_md(d, A.lr_carrier_b("Caprock Roofing Co", ["2025-12-30 to 2026-12-30"],
                              "2026-07-28", [["2026-05-14", "hail damage to shop roof", "$8,420", "$0"]]))

    # 560 candle and gift shop. COOKING CONFLICT: app says None, email says funnel cakes fried in a countertop fryer.
    d = folder(560)
    email(d, 'Bluebonnet Candle Co - Salado',
          'Salado candle and gift shop (candles, soaps, local honey). Something the application leaves out: on weekends the owner fries funnel cakes in a small countertop fryer near the front door and sells them warm. The Carrier B run is clean.')
    app_typed_pdf(d, 560, app(named="Bluebonnet Candle Co LLC", mail="same as premises",
                              prem="205 N Main St, Salado TX 76571", eff="2026-12-08",
                              yrs="5", entity="LLC", lob="Business owners policy",
                              ops="Candle and gift shop", emp="3",
                              sales="$298,000", tiv="$176,000", bpp="$88,000", sqft="2,100",
                              constr="Masonry", yb="1921", stories="1", spk="No", cook="None",
                              carrier="Carrier B", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_b("Bluebonnet Candle Co LLC", ["2025-12-08 to 2026-12-08"],
                              "2026-08-06", []))

    # 561 deli, cooking stated. Planted conflict: sales, approximate (email about $530,000, app $498,000).
    d = folder(561)
    email(d, 'Courthouse Square Deli - Weatherford',
          "Weatherford deli on the square: sandwiches, salads and soups. Last year's sales came in at about $530,000; the application shows the year before. One customer slip on the Carrier B run, attached.")
    app_md(d, 561, app(named="Courthouse Square Deli LLC", mail="same as premises",
                       prem="110 N Main St, Weatherford TX 76086", eff="2026-12-14", yrs="7",
                       entity="LLC", lob="Restaurant package, no liquor",
                       ops="Deli, counter service sandwiches and salads", emp="8",
                       sales="$498,000", tiv="$154,000", bpp="$69,000", sqft="1,850",
                       constr="Masonry", yb="1939", stories="1", spk="Yes, hood only",
                       cook="Flat-top, panini press, soup warmer",
                       carrier="Carrier B", claims="Slip and fall 2026, closed", bk="No"))
    loss_md(d, A.lr_carrier_b("Courthouse Square Deli LLC", ["2025-12-14 to 2026-12-14"], "2026-08-21",
                              [["2026-05-08", "customer slip near the order counter", "$1,370", "$0"]]))

    # 562 deli. COOKING CONFLICT: app says None, email says shrimp and fries fried every day.
    d = folder(562)
    email(d, 'Mustang Island Deli - Port Aransas',
          'Port Aransas deli on Alister St selling po-boys and sandwiches to beach traffic. I left this off the application: shrimp and fries are fried every day. Carrier C run attached, no claims.')
    app_md(d, 562, app(named="Mustang Island Deli LLC", mail="same as premises",
                       prem="1101 S Alister St, Port Aransas TX 78373", eff="2026-12-17", yrs="5",
                       entity="LLC", lob="Business owners policy",
                       ops="Deli, counter sandwiches", emp="5", sales="$318,000",
                       tiv="$122,000", bpp="$57,000", sqft="1,400", constr="Frame", yb="1983",
                       stories="1", spk="No", cook="None", carrier="Carrier C", claims="None",
                       bk="No"))
    loss_md(d, lr_c("Mustang Island Deli LLC", ["2025-12-17 to 2026-12-17"], "2026-09-03", []))

    # 563 tavern, prohibited class (W1, held). Carrier C fight claim.
    d = folder(563)
    email(d, 'Iron Horse Tavern - Big Spring',
          'Quote needed for a Big Spring tavern on East 3rd: full bar, darts, pool tables, closes at 2. The Carrier C run has one closed fight claim from July.')
    app_md(d, 563, app(named="Iron Horse Tavern LLC", mail="same as premises",
                       prem="710 E 3rd St, Big Spring TX 79720", eff="2026-12-26",
                       yrs="11", entity="LLC", lob="Liquor liability, general liability",
                       ops="Tavern, full bar, darts, pool tables", emp="6", sales="$585,000",
                       tiv="$262,000", bpp="$78,000", sqft="3,000", constr="Masonry",
                       yb="1952", stories="1", spk="No", cook="None",
                       carrier="Carrier C", claims="Patron fight 2026, closed", bk="No"))
    loss_md(d, lr_c("Iron Horse Tavern LLC", ["2025-12-26 to 2026-12-26"], "2026-09-01",
                    [["C-62418", "2026-07-19", "assault, patron fight", "$6,850", "$0"]]))

    # 564 nightclub, prohibited class (W1, held). Carrier A, no claims.
    d = folder(564)
    email(d, 'Coyote Moon Nightclub - Corpus Christi',
          'Corpus Christi nightclub on Padre Island Dr. DJs Thursday through Saturday, a dance floor and a full bar. Expiring with Carrier A; their run is clean.')
    app_md(d, 564, app(named="Coyote Moon Nightclub LLC", mail="same as premises",
                       prem="1520 S Padre Island Dr, Corpus Christi TX 78416", eff="2027-01-02", yrs="4",
                       entity="LLC", lob="Liquor liability, general liability",
                       ops="Nightclub, dance floor, DJ, full bar", emp="14",
                       sales="$860,000", tiv="$395,000", bpp="$131,000", sqft="5,200",
                       constr="Masonry", yb="1984", stories="1", spk="Partial", cook="None",
                       carrier="Carrier A", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_a("Coyote Moon Nightclub LLC", ["2026-01-02 to 2027-01-02"],
                              "2026-09-18", []))

    # 565 breakfast restaurant, cooking stated (griddle, two fryers, hood with suppression). Carrier C grease fire.
    d = folder(565)
    email(d, 'Prairie Dawn Restaurant - Corsicana',
          'This one is a 48-seat breakfast and lunch spot on 7th Ave in Corsicana that opens its doors at 6. The line is a griddle and two fryers, all under the hood. Back in April a fryer caused a small grease fire; Carrier C paid it and the claim is closed. Typed app attached.')
    app_typed_pdf(d, 565, app(named="Prairie Dawn Restaurant LLC", mail="same as premises",
                              prem="2310 W 7th Ave, Corsicana TX 75110", eff="2026-12-11",
                              yrs="9", entity="LLC", lob="Restaurant package, no liquor",
                              ops="Breakfast and lunch restaurant, table service, 48 seats",
                              emp="13", sales="$842,000", tiv="$271,000", bpp="$133,000",
                              sqft="2,950", constr="Masonry", yb="1987", stories="1",
                              spk="Yes, full", cook="Griddle, two fryers, hood with suppression",
                              carrier="Carrier C", claims="Grease fire 2026, closed", bk="No"))
    loss_md(d, lr_c("Prairie Dawn Restaurant LLC", ["2025-12-11 to 2026-12-11"], "2026-09-25",
                    [["C-62533", "2026-04-09", "grease fire, fryer", "$10,980", "$0"]]))

    # 566 bakery cafe, cooking stated (oven). Planted conflict: square footage, plain (email 2,450, app 2,150).
    d = folder(566)
    email(d, 'Kolache Corner Bakery - Schulenburg',
          'Schulenburg bakery cafe on Main (kolaches, bread, coffee; counter plus a few tables). After we added the back room the space measures 2,450 square feet; the application still lists 2,150. Carrier B run attached, nothing reported.')
    app_md(d, 566, app(named="Kolache Corner Bakery LLC", mail="same as premises",
                       prem="915 N Main St, Schulenburg TX 78956", eff="2027-01-07", yrs="11",
                       entity="LLC", lob="Restaurant package, no liquor",
                       ops="Bakery cafe, counter service", emp="7", sales="$436,000",
                       tiv="$163,000", bpp="$79,000", sqft="2,150", constr="Masonry", yb="1958",
                       stories="1", spk="No", cook="Oven, espresso machine",
                       carrier="Carrier B", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_b("Kolache Corner Bakery LLC", ["2026-01-07 to 2027-01-07"],
                              "2026-10-14", []))

    # 567 NEAR-MISS "two floors" (in scope): architecture office on two floors of one building. Carrier A clean.
    d = folder(567)
    email(d, 'Tierra Alta Architects - renewal',
          'Cuero architecture firm on Main St. The team works on two floors of the building, with drafting on the ground level and the principals upstairs; it is all at the address on the application. Carrier A run attached, no losses.')
    app_md(d, 567, app(named="Tierra Alta Architects LLC", mail="same as premises",
                       prem="221 N Main St, Cuero TX 77954", eff="2026-12-29", yrs="16",
                       entity="LLC", lob="Business owners policy",
                       ops="Architecture office", emp="8", sales="$910,000",
                       tiv="$295,000", bpp="$88,000", sqft="3,400", constr="Masonry", yb="1931",
                       stories="2", spk="No", cook="None", carrier="Carrier A", claims="None",
                       bk="No"))
    loss_md(d, A.lr_carrier_a("Tierra Alta Architects LLC", ["2025-12-29 to 2026-12-29"],
                              "2026-09-24", []))

    # 568 NEAR-MISS "2nd floor" (in scope): law office in suite 220 on the 2nd floor. Carrier C clean.
    d = folder(568)
    email(d, 'Vasquez & Lund Law Office',
          'Longview law office, two attorneys and two staff, still in suite 220 on the 2nd floor of the Judson Rd building. Carrier C run attached, no claims.')
    app_typed_pdf(d, 568, app(named="Vasquez & Lund PLLC", mail="same as premises",
                              prem="1110 Judson Rd Ste 220, Longview TX 75601", eff="2026-12-16",
                              yrs="10", entity="PLLC", lob="Business owners policy",
                              ops="Law office", emp="4", sales="$980,000",
                              tiv="$58,000", bpp="$66,000", sqft="2,050", constr="Masonry",
                              yb="2001", stories="3", spk="Yes", cook="None",
                              carrier="Carrier C", claims="None", bk="No"))
    loss_md(d, lr_c("Vasquez & Lund PLLC", ["2025-12-16 to 2026-12-16"], "2026-09-11", []))

    # 569 NEAR-MISS "two entrances" (in scope): saddle and tack retail store, one building. Carrier A clean.
    d = folder(569)
    email(d, 'Rio Frio Saddle & Tack - Uvalde',
          'Uvalde saddle and tack store on Getty St. Shoppers use two entrances, the front door on Getty and a side door off the parking lot, and both open into the same store. Carrier A run attached, clean.')
    app_md(d, 569, app(named="Rio Frio Saddle & Tack LLC", mail="same as premises",
                       prem="103 N Getty St, Uvalde TX 78801", eff="2027-01-04", yrs="23",
                       entity="LLC", lob="Business owners policy",
                       ops="Saddle and tack retail store", emp="5", sales="$615,000",
                       tiv="$214,000", bpp="$171,000", sqft="3,100", constr="Masonry", yb="1928",
                       stories="1", spk="No", cook="None", carrier="Carrier A", claims="None",
                       bk="No"))
    loss_md(d, A.lr_carrier_a("Rio Frio Saddle & Tack LLC", ["2026-01-04 to 2027-01-04"],
                              "2026-10-02", []))

    # ============================================================ out of scope (570-581)
    # criterion 1: application is a scan. 570 JPG, 571 image-only PDF.
    d = folder(570)
    email(d, 'Caprice Sign Shop - scan',
          'Attached is a phone scan of the signed application for a Plainview sign shop (vinyl signs, banners). Carrier B run attached, no claims.')
    app_scan(d, 570, app(named="Caprice Sign Shop LLC", mail="same as premises",
                         prem="806 E 4th St, Plainview TX 79072", eff="2026-12-09", yrs="7",
                         entity="LLC", lob="Business owners policy", ops="Sign shop, vinyl signs and banners",
                         emp="3", sales="$212,000", tiv="$96,000", bpp="$52,000", sqft="1,600",
                         constr="Metal", yb="1978", stories="1", spk="No", cook="None",
                         carrier="Carrier B", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_b("Caprice Sign Shop LLC", ["2025-12-09 to 2026-12-09"], "2026-08-12", []))

    d = folder(571)
    email(d, 'Pedernales Bike Works - pdf is a scan',
          'Johnson City bicycle shop, sales and repair. The application PDF is a scanned picture of the signed form. Typed Carrier A run attached.')
    app_image_pdf(d, 571, app(named="Pedernales Bike Works LLC", mail="same as premises",
                              prem="406 W Main St, Johnson City TX 78636", eff="2026-12-22", yrs="8",
                              entity="LLC", lob="Business owners policy",
                              ops="Bicycle shop, sales and repair", emp="4",
                              sales="$388,000", tiv="$167,000", bpp="$121,000", sqft="2,200",
                              constr="Masonry", yb="1949", stories="1", spk="No", cook="None",
                              carrier="Carrier A", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_a("Pedernales Bike Works LLC", ["2025-12-22 to 2026-12-22"], "2026-09-15", []))

    # criterion 2: more than one location.
    # 572 SUB-533 shape: the second address is a highway address, in a sentence that also names a carrier.
    d = folder(572)
    email(d, 'Navasota Post & Wire - renewal',
          'Fence supply in Bryan on College Ave: posts, wire and gates. The storage yard at 1408 Hwy 36 S, Brenham is on the same Carrier B policy. Loss run attached.')
    app_md(d, 572, app(named="Navasota Post & Wire LLC", mail="same as premises",
                       prem="2408 S College Ave, Bryan TX 77801", eff="2026-12-12", yrs="15",
                       entity="LLC", lob="Business owners policy", ops="Fence supply retail store",
                       emp="7", sales="$1,120,000", tiv="$230,000", bpp="$310,000", sqft="5,600",
                       constr="Metal", yb="1992", stories="1", spk="No", cook="None",
                       carrier="Carrier B", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_b("Navasota Post & Wire LLC", ["2025-12-12 to 2026-12-12"], "2026-08-25", []))

    # 573 SUB-533 shape: the second address is on the line below a filled "Mailing address: same as premises" line.
    d = folder(573)
    email(d, 'Guadalupe Glass & Mirror - Seguin',
          'Seguin glass and mirror shop on Court St (storefront glass, shower doors).\nMailing address: same as premises\nInstallation trailers are parked at 711 N Austin St, Seguin, which the application does not list.\nNo claims on the Carrier C run.')
    app_md(d, 573, app(named="Guadalupe Glass & Mirror LLC", mail="same as premises",
                       prem="1220 E Court St, Seguin TX 78155", eff="2026-12-19", yrs="12",
                       entity="LLC", lob="Business owners policy", ops="Glass and mirror shop",
                       emp="6", sales="$690,000", tiv="$205,000", bpp="$97,000", sqft="3,300",
                       constr="Masonry", yb="1976", stories="1", spk="No", cook="None",
                       carrier="Carrier C", claims="None", bk="No"))
    loss_md(d, lr_c("Guadalupe Glass & Mirror LLC", ["2025-12-19 to 2026-12-19"], "2026-09-08", []))

    # 574-577 words only (no second street address anywhere).
    d = folder(574)
    email(d, 'Red River Shoe Repair - both shops',
          'Shoe and boot repair in Wichita Falls. We want both shops on one policy; the application figures combine the two. The expiring carrier is Carrier A and their run is in the folder.')
    app_md(d, 574, app(named="Red River Shoe Repair LLC", mail="same as premises",
                       prem="1715 Kemp Blvd, Wichita Falls TX 76309", eff="2026-12-05", yrs="20",
                       entity="LLC", lob="Business owners policy",
                       ops="Shoe and boot repair shop", emp="4",
                       sales="$265,000", tiv="$118,000", bpp="$64,000", sqft="1,500",
                       constr="Masonry", yb="1963", stories="1", spk="No", cook="None",
                       carrier="Carrier A", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_a("Red River Shoe Repair LLC", ["2025-12-05 to 2026-12-05"], "2026-08-20", []))

    d = folder(575)
    email(d, 'Spicewood Printing - renewal',
          'Printing shop in Georgetown (flyers, menus, forms). Large-format jobs are handled at our other location in Round Rock, which has its own staff. Same owner and policy as last year; Carrier C run attached, no claims.')
    app_typed_pdf(d, 575, app(named="Spicewood Printing LLC", mail="same as premises",
                              prem="905 S Austin Ave, Georgetown TX 78626", eff="2026-12-27", yrs="13",
                              entity="LLC", lob="Business owners policy",
                              ops="Printing shop", emp="9",
                              sales="$840,000", tiv="$260,000", bpp="$215,000", sqft="3,800",
                              constr="Masonry", yb="1999", stories="1", spk="Yes", cook="None",
                              carrier="Carrier C", claims="None", bk="No"))
    loss_md(d, lr_c("Spicewood Printing LLC", ["2025-12-27 to 2026-12-27"], "2026-09-29", []))

    d = folder(576)
    email(d, 'Concho Valley Hardware - Ballinger',
          'San Angelo hardware store (tools, paint, garden goods). Since August there is a second store in Ballinger, run the same way. Carrier B run attached, no claims.')
    app_md(d, 576, app(named="Concho Valley Hardware LLC", mail="same as premises",
                       prem="2632 Knickerbocker Rd, San Angelo TX 76904", eff="2026-12-07", yrs="17",
                       entity="LLC", lob="Business owners policy", ops="Hardware retail store",
                       emp="10", sales="$1,350,000", tiv="$410,000", bpp="$385,000", sqft="9,200",
                       constr="Masonry", yb="1981", stories="1", spk="No", cook="None",
                       carrier="Carrier B", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_b("Concho Valley Hardware LLC", ["2025-12-07 to 2026-12-07"], "2026-08-29", []))

    d = folder(577)
    email(d, 'Lavaca Bay Marine Supply - one shop now',
          'Port Lavaca marine supply (ropes, anchors, boat parts). The second shop was sold in March, leaving just this one. Carrier A run attached, no claims.')
    app_md(d, 577, app(named="Lavaca Bay Marine Supply LLC", mail="same as premises",
                       prem="1402 N Virginia St, Port Lavaca TX 77979", eff="2026-12-31", yrs="9",
                       entity="LLC", lob="Business owners policy", ops="Marine supply retail store",
                       emp="5", sales="$472,000", tiv="$158,000", bpp="$139,000", sqft="2,800",
                       constr="Metal", yb="1986", stories="1", spk="No", cook="None",
                       carrier="Carrier A", claims="None", bk="No"))
    loss_md(d, A.lr_carrier_a("Lavaca Bay Marine Supply LLC", ["2025-12-31 to 2026-12-31"], "2026-09-23", []))

    # criterion 3: application not in English. 578 typed Spanish PDF, 579 Spanish md.
    d = folder(578)
    email(d, 'muebleria - Eagle Pass',
          'Muebleria en Eagle Pass: muebles y colchones. Adjunto la solicitud en PDF, en espanol, y el loss run de Carrier C.')
    app_spanish_pdf(d, 578, [
        ("Asegurado", "Muebleria Los Encinos LLC"),
        ("Dirección de la ubicación", "2190 Del Rio Blvd, Eagle Pass TX 78852"),
        ("Fecha de vigencia", "2026-12-20"),
        ("Años en el negocio", "14"),
        ("Operaciones", "Venta de muebles y colchones"),
        ("Número de empleados", "7"),
        ("Ventas anuales", "$610,000"),
        ("Valor del edificio", "$245,000"),
        ("Pies cuadrados", "6,400"),
        ("Construcción", "Metal"),
        ("Año de construcción", "1994"),
        ("Rociadores", "No"),
        ("Aseguradora anterior", "Carrier C"),
    ])
    loss_md(d, lr_c("Muebleria Los Encinos LLC", ["2025-12-20 to 2026-12-20"], "2026-09-10", []))

    d = folder(579)
    email(d, 'Ferreteria El Mezquite',
          'Ferreteria en Pharr con herramientas y material electrico. La solicitud en espanol esta en el archivo. Nos cubre Carrier A.')
    app_spanish_md(d, 579, [
        ("Asegurado", "Ferreteria El Mezquite LLC"),
        ("Dirección de la ubicación", "601 N Cage Blvd, Pharr TX 78577"),
        ("Fecha de vigencia", "2026-12-24"),
        ("Años en el negocio", "18"),
        ("Operaciones", "Ferretería, herramientas y material eléctrico"),
        ("Número de empleados", "6"),
        ("Ventas anuales", "$540,000"),
        ("Valor del edificio", "$198,000"),
        ("Pies cuadrados", "4,800"),
        ("Construcción", "Mampostería"),
        ("Año de construcción", "1979"),
        ("Rociadores", "No"),
        ("Aseguradora anterior", "Carrier A"),
    ])
    loss_md(d, A.lr_carrier_a("Ferreteria El Mezquite LLC", ["2025-12-24 to 2026-12-24"], "2026-09-19", []))

    # criterion 4: email only, no application. 580-581
    d = folder(580)
    email(d, 'Sandy Creek Stables - quote',
          'Looking for a quote on a horse boarding stable near Elgin: 24 stalls and a riding arena. The application will follow once I locate it; what else do you need from me?')

    d = folder(581)
    email(d, 'Blue Norther Moving - quote',
          'Abilene moving company with three box trucks and a packing room needs coverage starting January 1. Not sure who the current carrier is; my partner set that up.')

    print("Wrote 32 submissions: SUB-550 .. SUB-581")


if __name__ == "__main__":
    build()
