"""T-116 gold migration (dev only): P-069-format COPIES of the dev gold. Never edits gold-set/ or gold-set-T-108-corrected/.
Run: .venv/bin/python deliverables/ai-engineer/evals/P-069-dev/migrate_gold.py
Writes gold-SUB-127-173/, gold-T-108/ and gold-mapping.md next to this file. Mapping by hand from operations-gold-rule.md (P-069)."""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
SRC = ROOT / "deliverables/senior-underwriter"
B = lambda *v: [f"business_type={x}" for x in v]
CK = ["no cooking operations"]
RESTO_HOOD = ["Type I hood", "UL 300"]

# sid -> (items, notes)
M: dict[int, tuple[list[str], list[str]]] = {
    # ---- SUB-127..173 (from the one-line "- Operations:") ----
    127: (B("office") + ["second floor"], ["financial advisory and tax", "4-story building, insured on 2nd floor"]),
    128: (B("retail"), ["gift shop: candles, home goods, greeting cards, gift wrap"]),
    129: (B("wholesale"), ["electrical supplies: wire, breakers, conduit, fixtures"]),
    130: (B("restaurant") + ["64 seats", "beer and wine only"], ["breakfast and lunch"]),
    131: (B("contractor"), ["water heater installs", "small remodel work"]),
    132: (B("restaurant") + ["90 seats", "beer and wine only"], ["Southern", "breakfast and lunch"]),
    133: (B("habitational") + ["12 units"], ["one two-story building", "long-term leases"]),
    134: (B("contractor"), ["glass cutting, tempering and framing for commercial storefronts"]),
    135: (B("retail") + ["sorting on site"], ["used book and thrift shop", "donated goods"]),
    136: (B("restaurant") + ["70 seats", "beer and wine only"], ["Mexican", "no bar"]),
    137: (B("contractor"), ["HVAC installation and service"]),
    138: (B("wholesale", "retail", "hazardous_goods"), ["animal feed, seed and fertilizer bags"]),
    139: (B("habitational") + ["6 units"], ["two two-story buildings", "long-term leases"]),
    140: (B("restaurant"), ["barbecue", "two locations", "dine-in and takeout"]),
    141: (B("restaurant", "bar_pub") + ["180 seats", "full liquor license", "live music"], ["music Friday and Saturday"]),
    142: (B("contractor"), []),
    143: (B("retail"), []),
    144: (B("lab_medical"), ["outpatient physical and speech therapy"]),
    145: (B("habitational") + ["40 units"], ["three two-story buildings", "long-term leases"]),
    146: (B("restaurant", "bar_pub") + ["180 seats", "full liquor license", "live music"], ["music Friday and Saturday"]),
    147: (B("office"), ["CPA tax preparation and bookkeeping"]),
    148: (B("restaurant") + ["140 seats", "beer and wine only"] + RESTO_HOOD, ["wet chemical", "hood and duct cleaned quarterly, last 2026-08-20"]),
    149: (B("habitational") + ["12 units"], ["long-term leases", "92 percent occupied"]),
    150: (B("wholesale") + ["no manufacturing", "no repackaging"], ["hardware and janitorial supplies to contractors", "trade counter"]),
    151: (B("contractor"), ["drywall, trim carpentry, acoustic ceilings", "commercial and residential remodel", "office and tool shop", "no hot work on premises"]),
    152: (B("retail"), ["outdoor gear and apparel", "sales floor and one storage room", "no firearms or ammunition"]),
    153: (B("retail", "wholesale"), ["stationery and office supplies", "admin office"]),
    154: (B("office") + ["second floor"], ["clients by appointment", "no inventory, no goods held for sale"]),
    155: (B("retail") + ["ground floor", "no alcohol", "no repackaging"], ["clothing and dry goods", "no food"]),
    156: (B("restaurant") + ["no alcohol", "48 seats", "flat-top", "2 fryers", "4-burner range"] + RESTO_HOOD, ["breakfast and lunch counter service", "dine-in and takeout"]),
    157: (B("restaurant", "bar_pub") + ["full liquor license", "140 seats", "charbroiler", "2 fryers", "flat-top", "8-burner range", "pizza oven", "live music"] + RESTO_HOOD,
          ["TABC mixed beverage permit", "live music Thursday to Sunday until midnight", "dinner service and weekend brunch"]),
    158: (B("habitational") + ["16 units"] + CK, ["two two-story buildings", "long-term leases", "tenant electric ranges only"]),
    159: (B("restaurant") + ["no alcohol", "30 seats", "deck oven", "4-burner range", "flat-top"] + RESTO_HOOD, ["pastries, sandwiches, coffee", "2 convection ovens", "dine-in and takeout"]),
    160: (B("habitational") + ["8 units"] + CK, ["two two-story buildings", "long-term leases", "tenant electric ranges only"]),
    161: (B("wholesale") + ["no flammable liquids", "no repackaging"], ["home goods, kitchenware, small hand tools to retail stores", "no aerosols, pesticides, batteries", "warehouse with loading dock"]),
    162: (B("office"), ["clients by appointment", "no inventory"]),
    163: (B("restaurant") + ["beer and wine only", "60 seats", "comal", "grill", "2 fryers", "6-burner range"] + RESTO_HOOD, ["Mexican", "no bar", "table service and takeout"]),
    164: (B("contractor") + ["torch-down"], ["residential and commercial re-roofing and repair", "shop and yard on premises", "materials stored outside under tarps"]),
    165: (B("retail", "fireworks_explosives") + ["fireworks"], ["aerial, ground and cakes", "seasonal tent June and July", "inventory stored on premises including a trailer on the lot"]),
    166: (B("office"), ["two-story, owner-occupied", "insured on first floor, two tenants on second floor", "no retail, no food"]),
    167: (B("habitational") + ["24 units"] + CK, ["three two-story buildings", "long-term leases", "tenant electric ranges only"]),
    169: (B("other_class") + ["no commercial pressing", "no delivery service"], ["self-service laundromat", "14 washers and 8 gas dryers", "customers wash their own clothes"]),
    170: (B("restaurant") + ["beer and wine only", "flat-top", "2 fryers", "charbroiler", "8-burner range"] + RESTO_HOOD, ["burgers, chicken and breakfast", "2 locations", "no liquor license", "dine-in and takeout"]),
    171: (B("restaurant", "bar_pub") + ["full liquor license", "140 seats", "charbroiler", "2 fryers", "flat-top", "8-burner range", "pizza oven", "live music"] + RESTO_HOOD,
          ["TABC mixed beverage permit", "live music Thursday to Sunday until midnight", "dinner service and weekend brunch"]),
    172: (B("habitational") + ["30 units"] + CK, ["3 properties", "long-term leases", "tenant electric ranges only"]),
    173: (B("restaurant") + ["no liquor", "35 seats"], ["counter service taqueria: tacos, burritos, quesadillas, agua fresca", "dine-in and takeout"]),
    # ---- T-108 in-scope SUB-206..225 (from the items line) ----
    206: (B("office"), ["leases office suites", "lessor only"]),
    207: (B("restaurant") + ["no cooking", "no fryer", "no hood", "24 seats"], ["deli and sub shop", "counter service", "cold prep and assembly only (documents say both this and no cooking; gold holds cooking=none)"]),
    208: (B("wholesale") + ["no manufacturing"], ["craft and hobby supplies, small-package novelties", "sells to retail shops only", "warehouse shelving, small office", "no retail walk-in"]),
    209: (B("contractor"), ["concrete flatwork: driveways, patios, sidewalks, small commercial slabs", "12 employees", "25% subcontracted", "no roofing, no demolition, no structural"]),
    210: (B("habitational") + ["14 units"], ["2 two-story garden buildings", "long-term leases", "on-site part-time manager", "no short-term rentals"]),
    211: (B("restaurant") + ["grill", "Type I hood", "96 seats", "full liquor", "closes 11 p.m.", "no dancing"], ["offset smoker", "ansul system", "documents say full bar (beer, wine, liquor); gold item is full liquor so the word bar does not read as bar_pub", "no late-night entertainment"]),
    212: (B("contractor"), ["interior finish carpentry and cabinet installation", "residential and light commercial", "6 employees in 3 crews", "no roofing, no structural, no demolition, no exterior work above 2 stories"]),
    213: (B("office"), ["single-story building", "9 suites leased to small professional tenants", "lessor only", "no tenant cooking, no retail"]),
    214: (B("retail"), ["outdoor gear, apparel, footwear", "no repair, no fuel, no firearms, no rentals"]),
    215: (B("restaurant", "retail") + ["no cooking", "no fryer", "no hood"], ["deli and sandwich shop with a small grocery/market section", "canned and dry goods, no meat counter", "cold prep and assembly only (documents say both this and no cooking; gold holds cooking=none)", "6 tables"]),
    216: (B("wholesale") + ["no manufacturing"], ["paper and packaging supplies to restaurants and offices", "warehouse racking, small office"]),
    217: (B("habitational") + ["10 units"], ["2 two-story wood frame buildings", "long-term leases", "on-site manager unit", "no short-term rentals", "tenant electric ranges only"]),
    218: (B("cold_storage"), ["frozen and chilled goods for food distributors", "ammonia refrigeration plant, 2 compressors", "monitored 24/7", "storage only, no processing, no packaging"]),
    219: (B("hazardous_goods", "other_listed") + ["flammable liquids"], ["blending and packaging of industrial paints and solvent-based coatings, small batch", "no bulk storage above ground", "rated cabinet, max 55 gal per batch", "small office"]),
    220: (B("restaurant") + ["wok", "Type I hood", "18 seats", "no alcohol"], ["fast-casual Chinese", "ansul", "takeout", "no bar"]),
    221: (B("retail", "vacant") + ["no cooking"], ["strip center, 6 units", "last tenant vacated June 2026", "building owner", "no contents, no business income", "owner marketing the space"]),
    222: (B("lounge_nightclub") + ["open until 2:00 a.m.", "full liquor", "dance floor", "DJ", "capacity 350", "no cooking"], ["bottle service", "cover charge", "21+ only", "bar snacks only", "documents say full liquor bar; gold item is full liquor so the word bar does not read as bar_pub"]),
    223: (B("habitational") + ["12 units"], ["single two-story wood frame building", "long-term leases", "on-site manager unit", "no short-term rentals, no commercial tenants", "tenant electric ranges only"]),
    224: (B("habitational") + ["10 units"], ["2 two-story wood frame buildings", "long-term leases", "on-site manager unit", "no short-term rentals", "tenant electric ranges only"]),
    225: (B("lounge_nightclub", "bar_pub") + ["full liquor license", "open until 2:00 a.m.", "DJ", "dance floor", "no cooking"], ["small dance floor on weekends", "21+", "no food service beyond bar snacks"]),
}

# per-decision explanation table (rule section 3 row used)
RULES = {
    "class": "business class phrase -> business_type= (rule 3, row 1; synonyms from section 1)",
    "note-list": "merchandise / work list, role word, trade exclusion, service style, location or building count, lease terms, occupancy, dates -> unscored note (rule 3)",
    "nonslot": "item the v10/v11 slot reader has no trigger for (no bar, no hot work, buildings/stories, meal periods, until midnight, ansul) -> unscored note",
}


def card(src: Path, items: list[str], notes: list[str]) -> str:
    out = []
    for line in src.read_text().splitlines():
        if line.startswith("- Operations items:") or line.startswith("- Operations notes"):
            continue
        out.append(line)
        if line.startswith("- Operations:"):
            out.append("- Operations items: " + "; ".join(items))
            if notes:
                out.append("- Operations notes (unscored): " + "; ".join(notes))
    return "\n".join(out) + "\n"


def old_of(src: Path) -> str:
    t = src.read_text()
    m = re.search(r"(?m)^- Operations items: ?:? ?(.*)$", t)
    o = re.search(r"(?m)^- Operations: (.*)$", t)
    return ("items: " + m.group(1)) if m else "ops: " + (o.group(1) if o else "")


rows = ["| Card | Old (gold today) | New Operations items | New Operations notes (unscored) |", "|---|---|---|---|"]
for name, rng, srcdir in (("gold-SUB-127-173", range(127, 174), SRC / "gold-set"), ("gold-T-108", range(206, 238), SRC / "gold-set-T-108-corrected")):
    dst = HERE / name
    shutil.rmtree(dst, ignore_errors=True)
    dst.mkdir()
    for n in rng:
        src = srcdir / f"SUB-{n:03d}.md"
        if n in M:
            (dst / src.name).write_text(card(src, *M[n]))
            rows.append(f"| SUB-{n:03d} | {old_of(src)[:200]} | {'; '.join(M[n][0])} | {'; '.join(M[n][1])} |")
        else:
            shutil.copyfile(src, dst / src.name)  # SUB-168 (not in documents) and the 12 out-of-scope cards: byte copies
            rows.append(f"| SUB-{n:03d} | (copied unchanged: not in documents or out of scope) | | |")
(HERE / "gold-mapping-rows.md").write_text("\n".join(rows) + "\n")
print(len(M), "cards migrated")
