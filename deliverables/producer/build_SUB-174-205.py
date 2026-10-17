#!/usr/bin/env python3
"""Build producer submissions SUB-174..205 (T-104 hold-out inbox files). Deterministic content.

Usage: .venv/bin/python build_SUB-174-205.py <worktree_root>
Writes only simulation/inbox/SUB-174 .. SUB-205 under the given root.
"""
import csv
import io
import os
import shutil
import sys
import textwrap
from datetime import datetime, timedelta

from PIL import Image, ImageDraw, ImageFilter, ImageFont
import openpyxl

FIC = "**FICTIONAL.** All businesses, people, addresses and policy numbers are made up."
ROOT = sys.argv[1]
OUT = os.path.join(ROOT, "simulation", "inbox")

CON_ES = {"Masonry": "Mamposteria", "Frame": "Madera", "Joisted Masonry": "Mamposteria con techo de madera",
          "Non-combustible": "No combustible"}


def L(addr, city, zp, tiv, constr, year, sqft, spr="No", cook=""):
    return dict(addr=addr, city=city, zip=zp, tiv=tiv, constr=constr, year=year, sqft=sqft, spr=spr, cook=cook)


def R(yr, carrier, pol, typ, date, paid, status):
    return (str(yr), carrier, pol, typ, date, paid, status)


def CLEAN(carrier, pol, yrs=(2024, 2025, 2026)):
    return [R(y, carrier, pol, "No losses", "-", "$0", "Closed") for y in yrs]


# ---------------------------------------------------------------- submissions
# app: md | pdf (typed PDF) | jpg (scanned) | pdfscan (image-only PDF) | None
# loss: list of rows | "none" (no-known-loss letter) | None (missing)
# loss_fmt: md | jpg | pdfscan
# sched: csv | xlsx | None; schedule rows = all locs unless app_locs is set in ov_sched
S = []

# ---- in scope (20)
S += [
    dict(id="SUB-174", name="Sunbelt Office Suites LLC", lang="en", eff="2027-03-01", years=11,
         entity="LLC", lob="Commercial property, general liability - office",
         ops="Leased executive suites (6 tenants), reception desk, shared conference room. No cooking.",
         emp=3, sales="$310,000 (rent income)", bpp=42000, prior="Redbud Mutual, expiring 02/28/27",
         claims="One water damage 2025, closed, $4,200 paid", locs=[L("4410 Bluff Creek Dr", "Austin", "78745", 640000, "Masonry", 1994, 9200, "Yes")],
         app="md", loss=True, carrier="A", crows=[("2025-06-14", "water damage", "$4,200", "$0", "closed")],
         loss_fmt="jpg", sched=None,
         subj="Sunbelt Office Suites - new to us, renewal 2/28",
         body="Hi, Sunbelt Office Suites is new to our agency, they've been with Redbud for years.\n"
              "Application attached. Loss runs are a scan from the carrier portal (their typed version wouldn't load).\n\n"
              "Thanks, Dana Whitfield, Whitfield & Ko Insurance"),
    dict(id="SUB-175", name="Marisol's Bakery & Cafe LLC", lang="en", eff="2027-04-15", years=6,
         entity="LLC", lob="BOP - bakery/cafe, no liquor",
         ops="Bakery and cafe, seating 24, bakery deck ovens, espresso, lunch sandwiches. No fryer. No beer or wine.",
         emp=9, sales="$520,000", bpp=74000, prior="Redbud Mutual, expiring 04/15/27",
         claims="One slip-and-fall 2024, closed, $3,500 paid",
         locs=[L("1802 Pearl Ridge Rd", "San Antonio", "78228", 385000, "Joisted Masonry", 1978, 2600, "No",
                 "Deck ovens, convection oven, espresso machine")],
         hood="2026-08-12", app="md", loss=True, carrier="B", crows=[("2024-09-12", "slip and fall", "$3,500", "$0")],
         loss_fmt="pdfscan", sched=None,
         subj="Marisol's Bakery - app + loss runs",
         body="Marisol's is up for renewal in April. Here's the app. Old agent sent the loss runs as a PDF "
              "and it's image only so I just attached it.\n\nGracias, Lupe Ibarra\nIbarra Commercial Lines"),
    dict(id="SUB-176", name="Greenway Pet Grooming LLC", lang="en", eff="2027-05-01", years=5,
         entity="LLC", lob="BOP - pet services",
         ops="Dog and cat grooming, bathing, nail trims, small retail of pet supplies. Two bathing tubs with forced-air dryers.",
         emp=4, sales="$188,000", bpp=36500, prior="Caprock Specialty, expiring 04/30/27",
         claims="None known", locs=[L("8800 Westheimer Rd", "Houston", "77063", 150000, "Frame", 1988, 1800, "No")],
         app="md", loss="none", loss_fmt="md", sched=None,
         subj="Greenway Pet Grooming - nueva con nosotros",
         body="Hola, le mando la solicitud de Greenway Pet Grooming. Es cuenta nueva para la agencia.\n"
              "La carta de no reclamos esta adjunta (5 anos sin reclamos). Cualquier duda me llama.\n\n"
              "Gracias, Marisela Ochoa\nOchoa Seguros Hispanos"),
    dict(id="SUB-177", name="La Esquina Tortilleria LLC", lang="en", eff="2027-06-01", years=14,
         entity="LLC", lob="BOP - food manufacturing/retail (no liquor)",
         ops="Corn masa and tortilla production, retail counter sales. Tortilla press, comal, no deep fryer. Sells chips bought in.",
         emp=7, sales="$640,000", bpp=95000, prior="Redbud Mutual, expiring 05/31/27",
         claims="None", locs=[L("1200 Nolana Ave", "McAllen", "78504", 290000, "Masonry", 1986, 2100, "No",
                               "Comal, tortilla press, gas-fired masa mill")],
         hood="2026-09-03", app="md", loss=CLEAN("Redbud Mutual", "RBM-22987"), loss_fmt="md", sched="csv",
         subj="Tortilleria La Esquina - new business",
         body="Rigoberto Salinas owns La Esquina. First time with us. App attached, loss runs from Redbud attached.\n"
              "Let me know what else you need. Thanks!\n\nJesus Trevino, Trevino Agency"),
    dict(id="SUB-178", name="Ridgeline Auto Glass Repair LLC", lang="en", eff="2027-05-01", years=8,
         entity="LLC", lob="BOP - auto glass repair shop",
         ops="Windshield and side glass replacement, mobile and shop. Urethane adhesive, no painting.",
         emp=5, sales="$470,000", bpp=28000, prior="Brazos Surplus, expiring 04/30/27",
         claims="None", locs=[L("3350 Mesa Crest Rd", "Fort Worth", "76111", 180000, "Frame", 1972, 2400, "No")],
         app="md", loss=CLEAN("Brazos Surplus", "BS-7714"), loss_fmt="md", sched="csv",
         subj="Ridgeline Auto Glass",
         body="one location, schedule attached as csv. loss runs from brazos pls see attached\n\nRandy"),
    dict(id="SUB-179", name="Pinecrest Tax & Accounting PLLC", lang="en", eff="2027-01-01", years=19,
         entity="PLLC", lob="BOP - professional office",
         ops="Office. Clients by appointment. No food, no alcohol.",
         emp=11, sales="$1,250,000 (fees)", bpp=88000, prior="Caprock Specialty, expiring 12/31/26",
         claims="One water damage 2025, closed, $1,900 paid",
         mailing="PO Box 4190, Abilene, TX 79604",
         locs=[L("711 S Broadway Ave", "Tyler", "75701", 210000, "Joisted Masonry", 1960, 3400, "Yes")],
         app="md", loss=True, carrier="A", crows=[("2025-08-19", "water damage", "$1,900", "$0", "closed")],
         loss_fmt="md", sched="csv",
         subj="Pinecrest Tax - renewal app",
         body="Renewal for Pinecrest Tax. Mailing is our PO box, the office is the Tyler building. "
              "Loss runs attached.\n\nThanks, Kristen Hale"),
    dict(id="SUB-180", name="Brazos Pottery Studio LLC", lang="en", eff="2027-02-15", years=3,
         entity="LLC", lob="BOP - studio/retail with kilns",
         ops="Pottery studio and gallery. Two electric kilns (240V), class sessions for adults and kids, retail sales of finished work.",
         emp=3, sales="$96,000", bpp=61000, prior="None - new policy, prior carrier was personal lines",
         claims="None",
         prior_addr="401 Franklin Ave, Waco, TX 76701 (until 2025)",
         locs=[L("2045 Columbus Ave", "Waco", "76701", 165000, "Masonry", 1948, 3100, "No",
                 "Two electric kilns, no gas")],
         app="md", loss="none", loss_fmt="md", sched=None,
         subj="Brazos Pottery Studio app",
         body="App attached. They moved in 2025 so the old address is on there too. Let me know.\n\nBeth Quan"),
    dict(id="SUB-181", name="Lone Star Tire & Lube Inc", lang="en", eff="2027-07-01", years=22,
         entity="Corporation", lob="Garage liability and BOP - auto service",
         ops="Tires, oil change and lube, brake jobs, 4 service bays. No fuel dispensing. No car wash.",
         emp=12, sales="$1,890,000", bpp=140000, prior="Redbud Mutual, expiring 06/30/27",
         claims="One customer vehicle damage 2023, $2,100, closed",
         locs=[L("6105 Slide Rd", "Lubbock", "79424", 320000, "Frame", 1981, 6400, "No", "Tire balancer, air compressor")],
         app="md", loss=[R(2023, "Redbud Mutual", "RBM-44910", "Customer vehicle", "03/04/23", "$2,100", "Closed"),
                         R(2024, "Redbud Mutual", "RBM-44910", "No losses", "-", "$0", "-"),
                         R(2025, "Redbud Mutual", "RBM-44910", "No losses", "-", "$0", "-")],
         loss_fmt="md", sched="csv",
         subj="Lone Star Tire - renewal",
         body="Renewal 7/1. App and 3 yrs loss runs attached. Owner wants a quote w/ garage liab.\n\nC. Puga"),
    dict(id="SUB-182", name="Gulf Coast Sub & Deli Co", lang="en", eff="2027-03-15", years=9,
         entity="Corporation", lob="BOP - restaurant (quick service, no liquor)",
         ops="Sub shop, cold cuts, hot sandwiches on flat-top grill, convection ovens. No fryer, no hood suppression unknown.",
         emp=10, sales="$710,000", bpp=82000, prior="Caprock Specialty, expiring 03/15/27",
         claims="One walk-in cooler claim 2025, closed, $1,850 paid",
         locs=[L("415 Leopard St", "Corpus Christi", "78401", 240000, "Masonry", 1982, 1700, "No",
                 "Flat-top grill, two convection ovens")],
         hood="2026-07-28", app="md", loss=True, carrier="B", crows=[("2025-07-22", "walk-in cooler compressor", "$1,850", "$0")],
         loss_fmt="md", sched=None,
         subj="Gulf Coast Sub - BOP renewal",
         body="BOP renewal, app attached. Carrier loss run for 3 yrs attached. Let me know if you need the hood cert.\n\nM. Oakes"),
    dict(id="SUB-183", name="Stellar Self Storage LLC", lang="en", eff="2027-08-01", years=7,
         entity="LLC", lob="Commercial property - self storage",
         ops="Climate and non-climate self storage units, 212 units. Office with a small retail counter (locks, boxes).",
         emp=2, sales="$1,040,000", bpp=18000, prior="Brazos Surplus, expiring 07/31/27",
         claims="None",
         locs=[L("1510 Old Settlers Blvd", "Round Rock", "78664", 1450000, "Non-combustible", 2015, 38000, "Yes")],
         app="md", loss=True, carrier="A", crows=[], loss_fmt="md", sched="xlsx",
         subj="Stellar Self Storage - property",
         body="Single site. Schedule in the xlsx. Loss runs attached. Thanks.\n\nPriya Raman, Raman Commercial"),
    dict(id="SUB-184", name="Keller Insurance Services PA", lang="en", eff="2027-04-01", years=12,
         entity="PA", lob="BOP - office",
         ops="Office. Clients by appointment. No food, no alcohol.",
         emp=5, sales="$640,000", bpp=54000, prior="Redbud Mutual, expiring 03/31/27",
         claims="One water damage 2025, closed, $2,350 paid",
         locs=[L("1305 Dessau Rd", "Pflugerville", "78660", 260000, "Joisted Masonry", 2001, 2200, "Yes")],
         app="pdf", loss=True, carrier="A", crows=[("2025-10-14", "water damage", "$2,350", "$0", "closed")],
         loss_fmt="md", sched=None,
         subj="Keller Insurance Services app",
         body="Typed application attached as PDF. Loss runs too. The owner wants a quote for office liability and contents.\n\n"
              "Sarah Lindqvist"),
    dict(id="SUB-185", name="Sierra Vista Apartments LLC", lang="en", eff="2027-09-01", years=16,
         entity="LLC", lob="Commercial property - small residential (6 units)",
         ops="Six-unit apartment building, two floors, owner-managed. Electric heat and window AC. No commercial tenants.",
         emp=1, sales="$84,000 (rent)", bpp=9000, prior="Carrier C, expiring 08/31/27",
         claims="One water damage Jan 2026, closed, $5,800 paid",
         locs=[L("3410 Cedar Ridge Ln", "El Paso", "79936", 880000, "Masonry", 1988, 6400, "Yes")],
         app="md", loss=True, carrier="C", crows=[("C-2318", "2026-01-19", "water damage", "$5,800", "$0")],
         loss_fmt="md", sched="csv", stories=2,
         subj="Sierra Vista Apartments - new to us",
         body="Six-unit building in El Paso, owner is moving his coverage to us. App and carrier loss run attached.\n\n"
              "Robert Dominguez, Dominguez Insurance"),
    dict(id="SUB-186", name="Dos Rios Grill LLC", lang="en", eff="2027-06-15", years=15,
         entity="LLC", lob="BOP - restaurant with bar",
         ops="Full-service grill, beer and wine only, 96 seats. Two deep fryers, charbroiler, exhaust hood (fire suppression service yearly).",
         emp=22, sales="$1,380,000", bpp=212000, prior="Redbud Mutual, expiring 06/15/27",
         claims="Grease fire 2025 in fryer area, contained, $19,400 paid",
         locs=[L("2701 San Bernardo Ave", "Laredo", "78040", 480000, "Masonry", 1991, 4800, "No",
                 "Two deep fryers, charbroiler, hood with suppression")],
         hood="2026-08-19", app="pdf", loss=True, carrier="B", crows=[("2025-11-02", "grease fire, fryer area", "$19,400", "$0")],
         loss_fmt="md", sched=None,
         subj="Dos Rios Grill - renewal",
         body="Renewal, typed app attached. We had a small grease fire last Nov, it's on the loss run. "
              "Owner replaced the hood suppression already.\n\nThanks, Ernesto Quiroga"),
    dict(id="SUB-187", name="Carrizo Court Apartments LLC", lang="en", eff="2027-05-01", years=9,
         entity="LLC", lob="Commercial property - small residential (7 units)",
         ops="Seven-unit apartment building, two floors, owner-managed. Electric heat and window AC. No commercial tenants.",
         emp=1, sales="$96,000 (rent)", bpp=12000, prior="Brazos Surplus, expiring 04/30/27",
         claims="Electrical fire Feb 2025, unit 4, $48,000 paid, closed",
         locs=[L("418 Carrizo Ct", "San Antonio", "78205", 910000, "Frame", 1962, 7800, "No")],
         stories=2, app="md", loss=True, carrier="C", crows=[("C-2104", "2025-02-11", "electrical fire", "$48,000", "$0")],
         loss_fmt="md", sched=None,
         subj="Carrizo Court - 7 unit apt",
         body="Owner Gilberto Ozuna wants to renew. Old wiring was replaced after the fire last winter, invoice is in the file. "
              "Loss runs attached.\n\nNatalie Brandt"),
    dict(id="SUB-200", name="Brenner Roofing & Sheet Metal Inc", lang="en", eff="2027-07-01", years=18,
         entity="Corporation", lob="Contractor GL and BOP - roofing",
         ops="Commercial roofing and sheet metal, torch-down and hot-air welding on job sites, 14 field crew. Shop is metal fabrication with a press brake.",
         emp=14, sales="$3,100,000", bpp=190000, prior="Redbud Mutual, expiring 06/30/27",
         claims="None known",
         locs=[L("2300 Eastex Fwy", "Beaumont", "77703", 350000, "Frame", 1985, 5600, "No", "Hot-air welders, torch")],
         app="md", loss=CLEAN("Redbud Mutual", "RBM-63310"), loss_fmt="md", sched=None,
         subj="Brenner Roofing - GL + shop",
         body="GL and shop BOP renewal. Torch-down is maybe 40% of their work so I put it in the app. Loss runs attached.\n\n"
              "Tony Mireles, Mireles Risk Group"),
    dict(id="SUB-201", name="Velvet Room Lounge LLC", lang="en", eff="2027-03-01", years=4,
         entity="LLC", lob="Liquor liability and BOP - nightclub",
         ops="Nightclub and lounge, capacity 260, DJ and live music Thu-Sat until 2 a.m. Full liquor bar. Small kitchen, pre-packaged snacks only.",
         emp=18, sales="$1,150,000", bpp=210000, prior="Brazos Surplus, expiring 02/28/27",
         claims="Two liquor-related incidents 2025, one settled $12,000",
         locs=[L("5612 Harrisburg Blvd", "Houston", "77011", 520000, "Joisted Masonry", 1965, 6200, "Yes", "Snack warmer")],
         app="md", loss=[R(2025, "Brazos Surplus", "BS-7790", "Liquor liability", "06/21/25", "$12,000", "Closed"),
                         R(2025, "Brazos Surplus", "BS-7790", "Liquor liability", "10/04/25", "$0", "Open - no payment")],
         loss_fmt="md", sched=None,
         subj="Velvet Room - liquor",
         body="Need a quote. Full liquor, 2am close, capacity 260. Loss runs attached. Owner is in a hurry.\n\nMarcus Dunn"),
    dict(id="SUB-202", name="Oakhurst Physical Therapy LLC", lang="en", eff="2027-04-01", years=7,
         entity="LLC", lob="BOP - healthcare office",
         ops="Physical therapy clinic, 6 treatment bays, hydrotherapy pool (small, 4 ft), gym equipment.",
         emp=9, sales="$980,000", bpp=87000, prior="Caprock Specialty, expiring 03/31/27",
         claims="None",
         locs=[L("3105 S Western St", "Amarillo", "79109", 240000, "Masonry", None, 3600, "No")],
         app="md", loss=CLEAN("Caprock Specialty", "CS-48312"), loss_fmt="md", sched="csv",
         subj="Oakhurst PT - renewal",
         body="Here's the app and loss runs for Oakhurst. Year built is on the old form, not sure, I'll check with the landlord.\n\n"
              "Kendra Olson"),
    dict(id="SUB-203", name="Blue Heron Coffee Roasters LLC", lang="en", eff="2027-06-01", years=8,
         entity="LLC", lob="BOP - coffee roaster and retail cafe",
         ops="Coffee roasting (15 kg gas drum roaster, afterburner), retail cafe with 18 seats, wholesale bags.",
         emp=12, sales="$1,020,000", bpp=130000, prior="Redbud Mutual, expiring 05/31/27",
         claims="None",
         ov={"sqft": "3,200"},
         locs=[L("2814 Greenville Ave", "Dallas", "75206", 330000, "Joisted Masonry", 1955, 2850, "No",
                 "15 kg gas drum roaster, afterburner, espresso bar")],
         hood="2026-09-10", app="md", loss=CLEAN("Redbud Mutual", "RBM-38217"), loss_fmt="md", sched="csv",
         subj="Blue Heron - BOP app",
         body="BOP renewal for Blue Heron. App and loss runs attached, schedule too. Roaster has an afterburner, "
              "the cert is on the Redbud file.\n\nAmy Cho"),
    dict(id="SUB-204", name="Tejas Pool & Patio Supply", lang="en", eff="2027-05-01", years=13,
         entity="Corporation", lob="BOP - retail/wholesale pool supplies",
         ops="Pool chemicals (non-hazmat bagged), pumps, patio furniture. Warehouse and showroom. Forklift x2.",
         emp=16, sales="$1,100,000", bpp=340000, prior="Brazos Surplus, expiring 04/30/27",
         claims="None",
         ov={"sales": "$1,100,000"},
         locs=[L("1950 Pine St", "Abilene", "79601", 275000, "Masonry", 1983, 6100, "No",
                 "None. Forklifts electric and LPG.")],
         app="md", loss=CLEAN("Brazos Surplus", "BS-5520"), loss_fmt="md", sched=None,
         subj="Tejas Pool - renewal",
         body="Renewal. Sales went down last year, the app is what they sent me. Loss runs attached. $940K is the number "
              "they told me on the phone, not sure.\n\nJ. Espinoza"),
    dict(id="SUB-205", name="Sabine Pass Seafood Market LLC", lang="en", eff="2027-03-15", years=10,
         entity="LLC", lob="BOP - seafood market and boil shop",
         ops="Retail seafood counter, live crawfish and crab boiled outdoors on propane burner seasonally. Ice machine. No fryer.",
         emp=6, sales="$560,000", bpp=49000, prior="Redbud Mutual, expiring 03/15/27",
         claims="None known",
         locs=[L("1420 Procter St", "Port Arthur", "77640", 198000, "Frame", 1971, 2900, "No",
                 "Propane boil burner outdoors, ice machine")],
         app="md", loss=None, loss_fmt=None, sched=None,
         subj="Sabine Pass Seafood - loss runs coming",
         body="App is attached. Loss runs are still coming from the old agent, I asked twice. Will forward when I get them.\n\n"
              "Javier Ruiz"),
]

# ---- out of scope (12)
S += [
    dict(id="SUB-188", name="Hillcrest Family Eye Care PLLC", lang="en", eff="2027-05-01", years=13,
         entity="PLLC", lob="BOP - optical retail/medical",
         ops="Optometry exam rooms, optical dispensary (frames, lenses). No cooking.",
         emp=7, sales="$1,240,000", bpp=112000, prior="Redbud Mutual, expiring 04/30/27",
         claims="None",
         locs=[L("6200 Camp Bowie Blvd", "Fort Worth", "76116", 410000, "Masonry", 1989, 3300, "Yes")],
         app="jpg", loss=CLEAN("Redbud Mutual", "RBM-27140"), loss_fmt="md", sched=None,
         subj="Hillcrest Eye Care - app scan",
         body="Scanned app attached (we print and sign). Loss runs typed, attached.\n\nGreg Tran"),
    dict(id="SUB-189", name="Coastal Bend Feed & Seed Co", lang="en", eff="2027-06-01", years=31,
         entity="Corporation", lob="BOP - farm and ranch supply",
         ops="Feed, seed, fertilizer (bagged), hardware, some pet supplies. Warehouse with a forklift.",
         emp=10, sales="$2,300,000", bpp=460000, prior="Caprock Specialty, expiring 05/31/27",
         claims="None",
         locs=[L("1100 N Main St", "Victoria", "77901", 340000, "Frame", 1968, 8200, "No",
                 "Forklift (LPG), no cooking")],
         app="pdfscan", loss=CLEAN("Caprock Specialty", "CS-29430"), loss_fmt="md", sched=None,
         subj="Coastal Bend Feed - app",
         body="Application attached, it's the copy from the office scanner, sorry it's crooked. Loss runs in the body "
              "of this email.\n\nRuth Ann Kolar"),
    dict(id="SUB-190", name="Kingsbridge Dental Partners LLC", lang="en", eff="2027-07-01", years=10,
         entity="LLC", lob="BOP - dental practice (two offices)",
         ops="General dentistry, two offices, digital x-ray, nitrous oxide in both. Sterilization autoclaves.",
         emp=21, sales="$3,400,000", bpp=290000, prior="Redbud Mutual, expiring 06/30/27",
         claims="None",
         locs=[L("5505 Westheimer Rd", "Houston", "77056", 620000, "Joisted Masonry", 1986, 5200, "Yes",
                 "Autoclaves, nitrous oxide"),
               L("8240 Fondren Rd", "Houston", "77074", 540000, "Masonry", 2004, 4700, "Yes",
                 "Autoclaves, nitrous oxide")],
         app="jpg", app_locs=1, loss=CLEAN("Redbud Mutual", "RBM-56602"), loss_fmt="md", sched="csv",
         subj="Kingsbridge Dental - 2 offices",
         body="Application (scanned, it's the wet-signed one) and schedule for both offices. Loss runs attached.\n\n"
              "Lori Pena"),
    dict(id="SUB-191", name="Parkway Sign Shop & Print", lang="en", eff="2027-04-01", years=17,
         entity="Corporation", lob="BOP - sign shop, two locations",
         ops="Sign fabrication (aluminum, LED channel letters), vinyl print, install crew. Shop and a second location used for storage and vehicle parking.",
         emp=15, sales="$1,650,000", bpp=230000, prior="Brazos Surplus, expiring 03/31/27",
         claims="One minor fall 2023, $1,200, closed",
         locs=[L("4410 Abrams Rd", "Dallas", "75219", 370000, "Joisted Masonry", 1977, 9400, "No",
                 "Welding for sign frames, no cooking"),
               L("4140 Harry Hines Blvd", "Dallas", "75235", 185000, "Frame", 1968, 3900, "No",
                 "No cooking. Vehicle storage.")],
         app="md", app_locs="all", loss=CLEAN("Brazos Surplus", "BS-4417"), loss_fmt="md", sched=None,
         subj="Parkway Sign - renewal, both buildings",
         body="Renewal with both buildings on it. Loss runs attached.\n\nBrian Stoltz"),
    dict(id="SUB-192", name="Eagle Pass Hardware Supply", lang="en", eff="2027-05-15", years=24,
         entity="LLC", lob="BOP - hardware and building supply",
         ops="Hardware retail, lumber and building supply counter, paint mixing (small). Yard storage of lumber and fence panels.",
         emp=8, sales="$1,430,000", bpp=310000, prior="Redbud Mutual, expiring 05/15/27",
         claims="None",
         locs=[L("1601 Garrison Rd", "Eagle Pass", "78852", 520000, "Masonry", 1974, 14000, "No",
                 "None. Paint mixing room.")],
         app="md", app_locs=1, loss=CLEAN("Redbud Mutual", "RBM-12088"), loss_fmt="md", sched="xlsx",
         sched_extra=L("Hwy 57 lumber yard (fenced), 0.4 mi west", "Eagle Pass", "78852", 65000, "Frame", 1990, 2500, "No"),
         subj="Eagle Pass Hardware - app + schedule",
         body="Everything's in: app, loss runs, and the schedule (xlsx). Lumber yard is on the schedule, it's not on the app.\n\n"
              "Felipe Garza"),
    dict(id="SUB-193", name="Ortega Auto Body Shop LLC", lang="es", eff="2027-06-01", years=9,
         entity="LLC", lob="Taller de carroceria - BOP y responsabilidad general",
         ops="Taller de carroceria y pintura. Cabina de pintura a base de solvente, soldadura MIG, sin cocina.",
         ops_es="Taller de carroceria y pintura. Cabina de pintura a base de solvente, soldadura MIG, sin cocina.",
         emp=6, sales="$720,000", bpp=95000, prior="Redbud Mutual, expiring 05/31/27",
         claims="None",
         locs=[L("2615 Roosevelt Ave", "San Antonio", "78228", 340000, "Frame", 1976, 7200, "No",
                 "Sin cocina. Cabina de pintura.")],
         app="md", loss=CLEAN("Redbud Mutual", "RBM-40019"), loss_fmt="md", sched=None,
         subj="Ortega Auto Body - renovacion",
         body="Good morning, attached is the application for Ortega Auto Body Shop. Loss runs from Redbud attached too. "
              "Let me know if you need anything else.\n\nThanks, Dana Whitfield"),
    dict(id="SUB-194", name="Panaderia El Sol LLC", lang="es", eff="2027-03-01", years=6,
         entity="LLC", lob="BOP - panaderia",
         ops="Panaderia con horno de piso, venta al mayoreo de pan dulce a dos tiendas, cafe. Sin freidora.",
         ops_es="Panaderia con horno de piso, venta al mayoreo de pan dulce a dos tiendas, cafe. Sin freidora.",
         emp=8, sales="$460,000", bpp=71000, prior="Caprock Specialty, expiring 02/28/27",
         claims="None",
         locs=[L("1450 E Price Rd", "Brownsville", "78520", 310000, "Joisted Masonry", 1983, 2800, "No",
                 "Horno de piso, horno de conveccion")],
         app="md", app_locs=1, loss="none", loss_fmt="md", sched="csv",
         sched_extra=L("1700 Boca Chica Blvd (tienda)", "Brownsville", "78521", 120000, "Masonry", 1990, 1400, "No",
                       "Solo horno de conveccion"),
         subj="Panaderia El Sol - solicitud",
         body="Buenas tardes, le mando la solicitud de Panaderia El Sol y el programa de ubicaciones. "
              "La tienda de Boca Chica esta en la lista. Carta de no reclamos adjunta.\n\nGracias, Esperanza Solis"),
    dict(id="SUB-195", name="Taller Hernandez Auto Repair LLC", lang="es", eff="2027-07-01", years=12,
         entity="LLC", lob="BOP - taller mecanico",
         ops="Mecanica general, cambio de aceite, frenos, sin gasolina. Cuatro bahias.",
         ops_es="Mecanica general, cambio de aceite, frenos, sin gasolina. Cuatro bahias.",
         emp=5, sales="$690,000", bpp=65000, prior="Brazos Surplus, expiring 06/30/27",
         claims="None",
         locs=[L("904 Zacatecas St", "Laredo", "78041", 225000, "Masonry", 1980, 5200, "No",
                 "Compresor de aire. Sin cocina.")],
         app="jpg", loss=CLEAN("Brazos Surplus", "BS-9902"), loss_fmt="md", sched=None,
         subj="Taller Hernandez - solicitud firmada",
         body="Le mando la solicitud firmada en escaneo, la tomamos con el celular. Las cartas de Brazos "
              "van en el correo siguiente.\n\nAtentamente, Oscar Villarreal"),
    dict(id="SUB-196", name="Tienda Mi Pueblo Grocery LLC", lang="es", eff="2027-04-15", years=5,
         entity="LLC", lob="BOP - tienda de abarrotes",
         ops="Tienda de abarrotes, carniceria pequena (sin fabricacion), tortilleria no. Venta de productos en lata y frescos.",
         ops_es="Tienda de abarrotes, carniceria pequena (sin fabricacion), tortilleria no. Venta de productos en lata y frescos.",
         emp=7, sales="$1,050,000", bpp=180000, prior="Redbud Mutual, expiring 04/15/27",
         claims="None",
         locs=[L("7930 Bellaire Blvd", "Houston", "77051", 470000, "Joisted Masonry", 1979, 6800, "Yes",
                 "Parrilla de carne en mostrador (una)")],
         app="pdf", loss=CLEAN("Redbud Mutual", "RBM-61720"), loss_fmt="md", sched=None,
         subj="Tienda Mi Pueblo - renovacion",
         body="Hi, here's the typed application for Tienda Mi Pueblo (it's in Spanish, the owner only reads Spanish). "
              "Loss runs are attached.\n\nThanks, Carla Mendez"),
    dict(id="SUB-197", name="Pearl Street Boutique (no application)", lang="en", eff="", years=None,
         entity="", lob="", ops="", emp=None, sales="", bpp=None, prior="", claims="",
         locs=[], app=None, loss=None, loss_fmt=None, sched=None,
         subj="quote for boutique waco",
         body="Hi need a quote for a boutique in Waco, around 1200 sq ft, retail clothing and some jewelry. "
              "Owner is a friend of a client. Send me what you need. Thx\n\nPaige"),
    dict(id="SUB-198", name="Juniper Kitchen (no attachment)", lang="en", eff="", years=None,
         entity="", lob="", ops="", emp=None, sales="", bpp=None, prior="", claims="",
         locs=[], app=None, loss=None, loss_fmt=None, sched=None,
         subj="Juniper Kitchen info",
         body="Attached is the info on the Plano restaurant, Juniper Kitchen. Let me know if you need the rest.\n\n"
              "Hannah Sim"),
    dict(id="SUB-199", name="Brazos Valley Plumbing Supply LLC", lang="en", eff="2027-06-01", years=20,
         entity="LLC", lob="BOP - plumbing wholesale and showroom, two locations",
         ops="Wholesale plumbing and HVAC parts sold to contractors, counter sales at the showroom. "
             "Warehouse with two electric forklifts. No cooking.",
         emp=11, sales="$2,400,000", bpp=310000, prior="Redbud Mutual, expiring 05/31/27",
         claims="None",
         locs=[L("2210 Rellis Pkwy", "Bryan", "77807", 520000, "Non-combustible", 2001, 18000, "Yes"),
               L("611 E 29th St", "College Station", "77840", 275000, "Joisted Masonry", 1986, 6400, "Yes")],
         app="md", app_locs="list", loss=CLEAN("Redbud Mutual", "RBM-70113"), loss_fmt="md", sched="csv",
         subj="Brazos Valley Plumbing - 2 locations, renewal",
         body="Renewal with both locations on the app. Warehouse is in Bryan, showroom is College Station. "
              "Schedule has both addresses. Loss runs attached.\n\nDale Hutchins, Hutchins Commercial"),
]

# carrier-format loss runs: letter per file; prior carrier named to match the run header
CARRIER_LETTER = {"SUB-174": "A", "SUB-175": "B", "SUB-179": "A", "SUB-182": "B", "SUB-183": "A", "SUB-184": "A",
                  "SUB-185": "C", "SUB-186": "B", "SUB-187": "C"}
for s in S:
    if s.get("carrier"):
        assert CARRIER_LETTER[s["id"]] == s["carrier"], s["id"]
        s["prior"] = f"Carrier {s['carrier']}, " + s["prior"].split(", ", 1)[1]

ORDER = [s["id"] for s in S]
assert sorted(ORDER) == [f"SUB-{n}" for n in range(174, 206)], ORDER

LAB = {
    "en": dict(sub="Submission", ins="Named insured", mail="Mailing address", same="same as premises",
               prem="Premises address", eff="Effective date", yrs="Years in business", ent="Entity type",
               lob="Line of business", ops="Operations", emp="Number of employees", sales="Annual sales",
               tiv="Building TIV", bpp="Business personal property", sq="Square footage", con="Construction",
               yb="Year built", st="Stories", spr="Sprinklers", cook="Cooking operations",
               prior="Expiring carrier", claims="Pending or open claims",
               prior_addr="Prior address (last 3 years)", loc="Location", bk="Bankruptcy or cancellation in last 5 years",
               yes="Yes", no="No", head="# Application (ACORD 125/140 style)"),
    "es": dict(sub="Solicitud", ins="Asegurado", mail="Direccion postal", same="igual al local",
               prem="Direccion del local", eff="Fecha efectiva", yrs="Anos en el negocio", ent="Tipo de entidad",
               lob="Linea", ops="Operaciones", emp="Numero de empleados", sales="Ventas anuales",
               tiv="Valor del edificio (TIV)", bpp="Propiedad comercial personal", sq="Pies cuadrados",
               con="Construccion", yb="Ano de construccion", st="Pisos", spr="Rociadores",
               cook="Operaciones de cocina", prior="Aseguradora anterior", claims="Reclamos abiertos",
               prior_addr="Direccion anterior (ultimos 3 anos)", loc="Ubicacion",
               bk="Quiebra o cancelacion en los ultimos 5 anos", yes="Si", no="No",
               head="# Solicitud (estilo ACORD 125/140)"),
}


def app_pairs(s):
    lang = s["lang"]
    T = LAB[lang]
    L0 = s["locs"][0]
    ov = s.get("ov", {})
    yn = lambda b: T["yes"] if b else T["no"]
    constr = CON_ES.get(L0["constr"], L0["constr"]) if lang == "es" else L0["constr"]
    ops = s.get("ops_es", s["ops"]) if lang == "es" else s["ops"]
    pairs = [
        (T["ins"], s["name"]),
        (T["mail"], s.get("mailing") or T["same"]),
        (T["prem"], f"{L0['addr']}, {L0['city']}, TX {L0['zip']}"),
        (T["eff"], s["eff"]),
        (T["yrs"], str(s["years"])),
        (T["ent"], s["entity"]),
        (T["lob"], s["lob"]),
        (T["ops"], ops),
        (T["emp"], str(s["emp"])),
        (T["sales"], ov.get("sales", s["sales"])),
        (T["tiv"], f"${L0['tiv']:,}"),
        (T["bpp"], f"${s['bpp']:,}"),
        (T["sq"], ov.get("sqft", f"{L0['sqft']:,}")),
        (T["con"], constr),
    ]
    if L0["year"]:
        pairs.append((T["yb"], str(L0["year"])))
    pairs += [(T["st"], str(s.get("stories", 1))), (T["spr"], yn(L0["spr"] == "Yes"))]
    if L0.get("cook"):
        pairs.append((T["cook"], L0["cook"]))
    if s.get("hood"):
        pairs.append(("Hood & extinguishing system last inspected", f"{s['hood']} (semi-annual service)"))
    if s.get("prior_addr"):
        pairs.append((T["prior_addr"], s["prior_addr"]))
    if s.get("app_locs") == "list":
        for i, loc in enumerate(s["locs"], start=1):
            pairs.append((f"{T['loc']} {i}", f"{loc['addr']}, {loc['city']}, TX {loc['zip']} - TIV ${loc['tiv']:,}, "
                          f"{loc['sqft']:,} sq ft, {loc['constr']}, built {loc['year']}"))
    if s.get("app_locs") == "all":
        for i, loc in enumerate(s["locs"][1:], start=2):
            pairs.append((f"{T['loc']} {i}", f"{loc['addr']}, {loc['city']}, TX {loc['zip']} - TIV ${loc['tiv']:,}, "
                          f"{loc['sqft']:,} sq ft, {loc['constr']}, built {loc['year']}"))
    pairs += [(T["prior"], s["prior"]), (T["claims"], s["claims"]), (T["bk"], T["no"])]
    return pairs


def app_text_lines(s):
    T = LAB[s["lang"]]
    lines = [FIC, ""]
    if s["app"] == "md":
        lines = [T["head"], ""]
        if s["lang"] == "en":
            lines.append(f"{T['sub']}: {s['sid']}")
    else:
        lines = [FIC, "", T["head"].replace("# ", "")]
    lines += [f"{k}: {v}" for k, v in app_pairs(s)]
    return lines


def wrap_lines(lines, width=74):
    out = []
    for ln in lines:
        out += textwrap.wrap(ln, width) or [""]
    return out


# ---------------------------------------------------------------- PDF helpers
def esc(text):
    b = text.encode("cp1252", "replace")
    return b.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def text_content(lines):
    out = [b"BT", b"/F1 10 Tf", b"12 TL", b"40 750 Td"]
    for ln in lines:
        out.append(b"(" + esc(ln) + b") '")
    out.append(b"ET")
    return b"\n".join(out)


def make_pdf(pages):
    objs = []

    def add(body):
        objs.append(body)
        return len(objs)

    add(b"")  # 1 catalog
    add(b"")  # 2 pages
    font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    kids = []
    for pg in pages:
        content = pg["content"]
        cobj = add(b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream")
        res = b"/Font << /F1 %d 0 R >>" % font
        if pg.get("image"):
            jpg, w, h, cs = pg["image"]
            iobj = add(b"<< /Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace /%s /BitsPerComponent 8 "
                       b"/Filter /DCTDecode /Length %d >>\nstream\n" % (w, h, cs.encode(), len(jpg))
                       + jpg + b"\nendstream")
            res += b" /XObject << /Im0 %d 0 R >>" % iobj
        kids.append(add(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << %s >> /Contents %d 0 R >>"
                        % (res, cobj)))
    objs[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objs[1] = b"<< /Type /Pages /Kids [%s] /Count %d >>" % (b" ".join(b"%d 0 R" % k for k in kids), len(kids))
    out = bytearray(b"%PDF-1.4\n")
    offs = []
    for i, body in enumerate(objs):
        offs.append(len(out))
        out += b"%d 0 obj\n" % (i + 1) + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for o in offs:
        out += b"%010d 00000 n \n" % o
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    return bytes(out)


def font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def scan_page(lines, size=26, rot=0.0, blur=0.0, q=85, W=1275, H=1650):
    lh = int(size * 1.5)
    img = Image.new("L", (W, H), 250)
    d = ImageDraw.Draw(img)
    f = font(size)
    for i, ln in enumerate(lines):
        d.text((90, 90 + i * lh), ln, fill=25, font=f)
    if rot:
        img = img.rotate(rot, resample=Image.BICUBIC, fillcolor=255)
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(blur))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=q)
    return buf.getvalue(), W, H


def scan_capacity(size=26, H=1650):
    return (H - 120) // int(size * 1.5)


def write_scan_jpg(path, lines, size=26, q=88):
    # one tall page image, same width as a letter scan
    lh = int(size * 1.5)
    H = max(1650, 120 + lh * len(lines))
    data, W, _ = scan_page(lines, size=size, q=q, H=H)
    with open(path, "wb") as fh:
        fh.write(data)


def write_scan_pdf(path, lines, size=26, rot=1.4, blur=0.7, q=45):
    cap = scan_capacity(size)
    pages = []
    for i in range(0, len(lines), cap):
        data, W, H = scan_page(lines[i:i + cap], size=size, rot=rot, blur=blur, q=q)
        pages.append({"content": b"q 612 0 0 792 0 0 cm /Im0 Do Q", "image": (data, W, H, "DeviceGray")})
    with open(path, "wb") as fh:
        fh.write(make_pdf(pages))


def write_typed_pdf(path, lines):
    pages = []
    for i in range(0, len(lines), 58):
        pages.append({"content": text_content(lines[i:i + 58])})
    with open(path, "wb") as fh:
        fh.write(make_pdf(pages))


# ---------------------------------------------------------------- file writers
def loss_md_lines(s):
    rows = s["loss"]
    if rows == "none":
        return [FIC, "", "No known losses in the last 5 years for the named insured or its premises.",
                "Signed: " + s["name"] + " (owner)", "Date: " + "01/15/27"]
    lines = [FIC, "", "Loss history (5 yrs)", "",
             "| Year | Carrier | Policy | Type | Date | Paid | Status |",
             "|---|---|---|---|---|---|---|"]
    for yr, c, p, t, d, paid, st in rows:
        lines.append(f"| {yr} | {c} | {p} | {t} | {d} | {paid} | {st} |")
    return lines


def loss_plain_lines(s):
    lines = [FIC, "", f"LOSS RUN - {s['name']}", ""]
    for yr, c, p, t, d, paid, st in s["loss"]:
        lines.append(f"{yr}   {c}   {p}   {t}   DOL {d}   Paid {paid}   {st}")
    lines += ["", "Valued 01/2027. Prepared from carrier portal."]
    return lines


def schedule_rows(s):
    rows = []
    for i, loc in enumerate(s["locs"], start=1):
        rows.append(["FICTIONAL", i, loc["addr"], loc["city"], loc["zip"], loc["tiv"], loc["constr"],
                     loc["year"] or "", loc["sqft"], loc["spr"], loc["cook"]])
    if s.get("sched_extra"):
        ex = s["sched_extra"]
        rows.append(["FICTIONAL", len(rows) + 1, ex["addr"], ex["city"], ex["zip"], ex["tiv"], ex["constr"],
                     ex["year"] or "", ex["sqft"], ex["spr"], ex["cook"]])
    return rows


SCHED_HEADER = ["source", "loc", "address", "city", "zip", "bldg_tiv", "construction", "year_built", "sq_ft",
                "sprinklers", "cooking"]


def write_sched(folder, s):
    rows = schedule_rows(s)
    if s["sched"] == "csv":
        with open(os.path.join(folder, "schedule.csv"), "w", newline="") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(SCHED_HEADER)
            w.writerows(rows)
    elif s["sched"] == "xlsx":
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Schedule"
        ws.append(SCHED_HEADER)
        for r in rows:
            ws.append(r)
        wb.properties.created = datetime(2026, 10, 1, 9, 0)
        wb.properties.modified = datetime(2026, 10, 1, 9, 0)
        wb.save(os.path.join(folder, "schedule.xlsx"))


def write_text(path, lines):
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")


def write_email(folder, s):
    text = f"{FIC}\n\nSubject: {s['subj']}\n\n{s['body']}\n"
    with open(os.path.join(folder, "email.md"), "w") as fh:
        fh.write(text)


def carrier_lines(s):
    """Forward the carrier's own loss run layout. 3 policy periods ending before 2027; valued 45 days before eff."""
    eff = datetime.strptime(s["eff"], "%Y-%m-%d").date()
    last = eff.replace(year=eff.year - 1)
    spans = [(last.replace(year=last.year - k), last.replace(year=last.year - k + 1)) for k in (3, 2, 1)]
    valued = (eff - timedelta(days=45)).isoformat()
    rows = s["crows"]
    if s["carrier"] == "A":
        lines = ["CARRIER A — LOSS RUN (FICTIONAL)", f"Named insured: {s['name']}"]
        lines += [f"Policy period: {a.isoformat()} to {b.isoformat()}" for a, b in spans]
        lines.append(f"Valued as of: {valued}")
        if rows:
            lines += ["| Date of loss | Cause | Paid | Reserve | Status |", "|---|---|---|---|---|"]
            lines += [f"| {d} | {c} | {p} | {r} | {st} |" for d, c, p, r, st in rows]
        else:
            lines.append("No claims reported by Carrier A for the policy periods above.")
    elif s["carrier"] == "B":
        lines = ["Carrier B Loss History Report (fictional)", f"Insured: {s['name']}"]
        lines += [f"Policy term: {a.isoformat()} to {b.isoformat()}" for a, b in spans]
        lines.append(f"Valuation date: {valued}")
        if rows:
            lines += ["| Loss date | Description | Paid | Outstanding |", "|---|---|---|---|"]
            lines += [f"| {d} | {c} | {p} | {o} |" for d, c, p, o in rows]
        else:
            lines.append("Carrier B certifies no claims for the policy terms above.")
    else:
        lines = ["CARRIER C | LOSS RUN | FICTIONAL", f"Account: {s['name']}"]
        lines += [f"Term: {a.isoformat()} - {b.isoformat()}" for a, b in spans]
        lines.append(f"Valued: {valued}")
        if rows:
            lines += ["| Claim no. | Loss date | Type | Paid | Open reserve |", "|---|---|---|---|---|"]
            lines += [f"| {n} | {d} | {t} | {p} | {r} |" for n, d, t, p, r in rows]
        else:
            lines.append("Carrier C: no claims reported.")
    return lines


def build(s):
    s["sid"] = s["id"]
    folder = os.path.join(OUT, s["id"])
    if os.path.isdir(folder):
        shutil.rmtree(folder)
    os.makedirs(folder)
    write_email(folder, s)
    app = s.get("app")
    if app == "md":
        write_text(os.path.join(folder, "application.md"), app_text_lines(s))
    elif app == "pdf":
        write_typed_pdf(os.path.join(folder, "application.pdf"), wrap_lines(app_text_lines(s)))
    elif app == "jpg":
        write_scan_jpg(os.path.join(folder, "application_scan.jpg"), wrap_lines(app_text_lines(s), 72))
    elif app == "pdfscan":
        write_scan_pdf(os.path.join(folder, "application_scan.pdf"), wrap_lines(app_text_lines(s), 72))
    loss = s.get("loss")
    fmt = s.get("loss_fmt")
    if s.get("carrier"):
        lines = carrier_lines(s)
        if fmt == "md":
            write_text(os.path.join(folder, "loss-runs.md"), lines)
        elif fmt == "jpg":
            write_scan_jpg(os.path.join(folder, "loss-runs_scan.jpg"), wrap_lines(lines, 72))
        elif fmt == "pdfscan":
            write_scan_pdf(os.path.join(folder, "loss-runs_scan.pdf"), wrap_lines(lines, 72))
    elif loss is not None:
        if fmt == "md":
            write_text(os.path.join(folder, "loss-runs.md"), loss_md_lines(s))
        elif fmt == "jpg":
            write_scan_jpg(os.path.join(folder, "loss-runs_scan.jpg"), wrap_lines(loss_plain_lines(s), 72))
        elif fmt == "pdfscan":
            write_scan_pdf(os.path.join(folder, "loss-runs_scan.pdf"), wrap_lines(loss_plain_lines(s), 72))
    if s.get("sched"):
        write_sched(folder, s)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    todo = [s for s in S if int(s["id"][4:]) >= 174]  # 174..205 only; 188..198 stay as built
    for s in todo:
        build(s)
    print(f"wrote {len(todo)} folders to {OUT}")
