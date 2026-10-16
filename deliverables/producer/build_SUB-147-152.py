import os, sys
from pathlib import Path

INBOX = Path("/Users/disastershubz/INSURANCE FLOW AI/-insureflow-ai-1/simulation/inbox")
sys.path.insert(0, "/Users/disastershubz/INSURANCE FLOW AI/-insureflow-ai-1/underwriting_pipeline/ai")
from smoke_readers import _scan  # read-only import, used for the greyscale scan

FOOT = "**FICTIONAL.** All businesses, people, addresses and policy numbers are made up.\n\n"

def pdf_bytes(lines):
    def enc(s):
        s = s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        return s.replace("—", "\\227")  # WinAnsi em dash
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

def csv(sub, row):
    write(sub, "schedule.csv",
          "source,loc,address,city,zip,bldg_tiv,construction,year_built,sq_ft,sprinklers,cooking\n" + row + "\n")

# ---------------- SUB-147 Carrier A, typed PDF ----------------
s = "SUB-147"
write(s, "email.md", FOOT + """Subject: Marlow Creek Accounting - new biz eff 3/1/27

Hi, Marlow Creek is coming to you guys from Carrier A, they are not renewing the account with them at 3/1 because of the rate change. Downtown office, 11 people, CPA and bookkeeping. Loss run attached as a pdf from A's portal. Nothing big on it i think.

Thanks, Ray Osterholt (producer)
""")
write(s, "application.md", FOOT + """# Application (ACORD 125/140 style)

Submission: SUB-147
Named insured: Marlow Creek Accounting PLLC
Mailing address: same as premises
Premises address: 1205 Congress Ave, Austin, TX 78701
Effective date: 2027-03-01
Years in business: 9
Entity type: professional limited liability company
Line of business: commercial property and general liability, office
Operations: CPA tax preparation and bookkeeping office. Clients by appointment. No inventory, no goods held for sale.
Number of employees: 11
Annual sales (gross fees, prior year): $1,240,000
Building TIV: $640,000
Business personal property: $85,000
Square footage: 6,100
Construction: Masonry non-combustible
Year built: 1998
Stories: 3
Sprinklers: Yes
Cooking operations: None
Expiring carrier: Carrier A, policy expiring 2027-03-01
Pending or open claims: None known
Bankruptcy or cancellation in last 5 years: No
""")
csv(s, "FICTIONAL,1,1205 Congress Ave,Austin,78701,640000,Masonry non-combustible,1998,6100,Yes,none")
pdf_lines = [
    "CARRIER A — LOSS RUN (FICTIONAL)",
    "Named insured: Marlow Creek Accounting PLLC",
    "Policy period: 2024-03-01 to 2025-03-01",
    "Policy period: 2025-03-01 to 2026-03-01",
    "Policy period: 2026-03-01 to 2027-03-01",
    "Valued as of: 2026-09-30",
    "| Date of loss | Cause | Paid | Reserve | Status |",
    "|---|---|---|---|---|",
    "| 2025-06-14 | water damage | $4,200 | $0 | closed |",
]
(INBOX / s / "loss-runs.pdf").write_bytes(pdf_bytes(pdf_lines))

# ---------------- SUB-148 Carrier B, greyscale scan ----------------
s = "SUB-148"
write(s, "email.md", FOOT + """Subject: Hollis & Vane Kitchen - restaurant, eff 1/1/27

Hey, Hollis and Vane is our restaurant on Travis downtown, 140 seats, been there since 94 at the building. Renewal moving to you, Carrier B has been good to them. Hood got cleaned in august and the ansul was serviced same week, invoices in the app folder if you need them. Loss run is a scan of the carrier letter, sorry its crooked.

Thx, Dee Halvorsen (producer)
""")
write(s, "application.md", FOOT + """# Application (ACORD 125/140 style)

Submission: SUB-148
Named insured: Hollis and Vane Kitchen LLC
Mailing address: same as premises
Premises address: 1100 Travis St, Houston, TX 77002
Effective date: 2027-01-01
Years in business: 12
Entity type: limited liability company
Line of business: commercial property and general liability, restaurant
Operations: full-service restaurant, lunch and dinner, 140 seats, beer and wine only, no liquor license. Weekend brunch.
Number of employees: 34
Annual sales: $1,480,000
Building TIV: $615,000
Business personal property: $210,000
Square footage: 4,800
Construction: Joisted masonry
Year built: 1994
Stories: 2
Sprinklers: Yes
Cooking operations: gas char-broiler (36 in), two gas fryers (50 lb each), flat-top griddle, 6-burner range, 2-deck convection oven. Type I hood over all cooking lines with UL 300 wet chemical suppression. Hood and duct cleaned quarterly by licensed vendor, last cleaned 2026-08-20.
Expiring carrier: Carrier B, policy expiring 2027-01-01
Pending or open claims: None known
Bankruptcy or cancellation in last 5 years: No
""")
csv(s, 'FICTIONAL,1,1100 Travis St,Houston,77002,615000,Joisted masonry,1994,4800,Yes,"Type I hood, UL 300 wet chem; gas char-broiler, 2 fryers, griddle, range, oven"')
b_lines = [
    "Carrier B Loss History Report (fictional)",
    "Insured: Hollis and Vane Kitchen LLC",
    "Policy term: 2024-01-01 to 2025-01-01",
    "Policy term: 2025-01-01 to 2026-01-01",
    "Policy term: 2026-01-01 to 2027-01-01",
    "Valuation date: 2026-09-30",
    "Carrier B certifies no claims for the policy terms above.",
]
_scan(b_lines, "L").save(INBOX / s / "loss-runs.jpg", "JPEG", quality=85)

# ---------------- SUB-149 Carrier C, typed text, sprinklered habitational ----------------
s = "SUB-149"
write(s, "email.md", FOOT + """Subject: Ridgeview Court Apts - 12 unit, eff 4/1/27

Hi! Ridgeview Court is our 12 unit complex in Lubbock, owner is Ridgeview Court Apartments LLC. Carrier C writes it now, we want to see if you can do it at renewal. Its fully sprinklered (did the retrofit in 2019, inspection was march). Rents are about 212k a year gross. Loss run attached.

Thanks, Pam Ostrander (producer)
""")
write(s, "application.md", FOOT + """# Application (ACORD 125/140 style)

Submission: SUB-149
Named insured: Ridgeview Court Apartments LLC
Mailing address: 2210 Quaker Ave, Lubbock, TX 79409
Premises address: 4402 Ridgeview Ct, Lubbock, TX 79424
Effective date: 2027-04-01
Years in business: 14
Entity type: limited liability company
Line of business: commercial property and general liability, habitational
Operations: residential apartment complex, 12 units in one two-story building, long-term leases
Number of units: 12
Occupancy: 92 percent
Annual sales (gross annual rents): $212,000
Building TIV: $1,380,000
Business personal property: $40,000
Square footage: 13,600
Construction: Joisted masonry
Year built: 1986
Stories: 2
Sprinklers: Yes, full NFPA 13 system, retrofit 2019, inspection 2026-03-12
Cooking operations: none (tenant electric ranges only)
Expiring carrier: Carrier C, policy expiring 2027-04-01
Pending or open claims: None known
Bankruptcy or cancellation in last 5 years: No
""")
csv(s, "FICTIONAL,1,4402 Ridgeview Ct,Lubbock,79424,1380000,Joisted masonry,1986,13600,Yes,none")
write(s, "loss-runs.md", """CARRIER C | LOSS RUN | FICTIONAL
Account: Ridgeview Court Apartments LLC
Term: 2024-04-01 - 2025-04-01
Term: 2025-04-01 - 2026-04-01
Term: 2026-04-01 - 2027-04-01
Valued: 2026-09-30
| Claim no. | Loss date | Type | Paid | Open reserve |
|---|---|---|---|---|
| C-2207 | 2026-01-14 | water | $6,850 | $0 |
""")

# ---------------- SUB-150 applicant letter, copies Carrier A header ----------------
s = "SUB-150"
write(s, "email.md", FOOT + """Subject: Tucker Ridge Hardware - renewal eff 1/15/27

Morning. Tucker Ridge Hardware Supply is a hardware and janitorial wholesaler in Waco, they sell to contractors mostly. Owner wrote the loss history himself, he didnt want to wait on the carrier letter. Let me know what else you need.

Thanks, Ben Carrow (producer)
""")
write(s, "application.md", FOOT + """# Application (ACORD 125/140 style)

Submission: SUB-150
Named insured: Tucker Ridge Hardware Supply LLC
Mailing address: same as premises
Premises address: 715 Franklin Ave, Waco, TX 76701
Effective date: 2027-01-15
Years in business: 22
Entity type: limited liability company
Line of business: commercial property and general liability, light wholesale
Operations: light wholesale of hardware and janitorial supplies to contractors. Warehouse with a small counter for trade customers. No manufacturing, no repackaging.
Number of employees: 6
Annual sales: $2,350,000
Building TIV: $870,000
Business personal property: $260,000
Square footage: 18,500
Construction: Tilt-up concrete
Year built: 1987
Stories: 1
Sprinklers: No
Cooking operations: None
Expiring carrier: Carrier A, policy expiring 2027-01-15
Pending or open claims: None known
Bankruptcy or cancellation in last 5 years: No
""")
csv(s, "FICTIONAL,1,715 Franklin Ave,Waco,76701,870000,Tilt-up concrete,1987,18500,No,none")
write(s, "loss-runs.md", """CARRIER A — LOSS RUN (FICTIONAL)

To whom it may concern,

We have been with Carrier A since early 2024 and I want to give you our history in my own words. In June 2025 (about the 14th) the roof flashing on the east side let go during a storm and water got into a few pallets of boxed inventory and a section of drywall in the front office. We reported it right away to Carrier A. They paid about $4,200 and the claim is closed, we have nothing open. We have had no other losses in the last three years that I can think of. We did put in new roof drains and checked the flashing all around in July 2025 so it should not happen again.

Thanks for taking a look,
Dale Tucker, owner
""")

# ---------------- SUB-151 Carrier B layout, valuation line left out ----------------
s = "SUB-151"
write(s, "email.md", FOOT + """Subject: Lone Star Drywall - contractor renewal eff 5/1/27

Hi, Lone Star Drywall and Trim, interior finish contractor out of Round Rock, 14 guys in the field. Currently with Carrier B. One theft claim on the trailer in 2024, its on the loss run. Sales around 1.15M last year. Let me know.

Thanks, Owen Kittrell (producer)
""")
write(s, "application.md", FOOT + """# Application (ACORD 125/140 style)

Submission: SUB-151
Named insured: Lone Star Drywall and Trim LLC
Mailing address: same as premises
Premises address: 1510 Chisholm Trail Rd, Round Rock, TX 78664
Effective date: 2027-05-01
Years in business: 11
Entity type: limited liability company
Line of business: commercial property and general liability, contractor
Operations: interior drywall hanging and finishing, trim carpentry, acoustic ceilings. Commercial and residential remodel. Office and tool shop on site, no hot work on premises.
Number of employees: 16 (14 field)
Annual sales (gross receipts, prior year): $1,150,000
Building TIV: $395,000
Business personal property: $120,000 (tools and equipment)
Square footage: 4,200
Construction: Metal (pre-engineered steel frame, metal siding)
Year built: 2001
Stories: 1
Sprinklers: No
Cooking operations: None
Expiring carrier: Carrier B, policy expiring 2027-05-01
Pending or open claims: None known
Bankruptcy or cancellation in last 5 years: No
""")
csv(s, "FICTIONAL,1,1510 Chisholm Trail Rd,Round Rock,78664,395000,Metal,2001,4200,No,none")
write(s, "loss-runs.md", """Carrier B Loss History Report (fictional)
Insured: Lone Star Drywall and Trim LLC
Policy term: 2024-05-01 to 2025-05-01
Policy term: 2025-05-01 to 2026-05-01
Policy term: 2026-05-01 to 2027-05-01
| Loss date | Description | Paid | Outstanding |
|---|---|---|---|
| 2024-09-03 | tools stolen from job trailer | $1,850 | $0 |
""")

# ---------------- SUB-152 non-panel carrier, own layout ----------------
s = "SUB-152"
write(s, "email.md", FOOT + """Subject: Blue Mesa Outfitters - outdoor retail eff 6/1/27

Hi there. Blue Mesa is a outdoor gear store on Henderson in Fort Worth, been open since the 2010s. They were with Harbor Point Mutual, not sure you have them on your panel, but I am sending the loss history from there. One theft in 2025. Sales close to 1.9M.

Best, Jolene Park (producer)
""")
write(s, "application.md", FOOT + """# Application (ACORD 125/140 style)

Submission: SUB-152
Named insured: Blue Mesa Outfitters LLC
Mailing address: same as premises
Premises address: 2201 Henderson St, Fort Worth, TX 76102
Effective date: 2027-06-01
Years in business: 14
Entity type: limited liability company
Line of business: commercial property and general liability, retail
Operations: retail store selling outdoor gear and apparel. Sales floor and one storage room. No firearms or ammunition sold.
Number of employees: 9
Annual sales: $1,920,000
Building TIV: $720,000
Business personal property: $190,000
Square footage: 3,800
Construction: Masonry non-combustible
Year built: 1972
Stories: 1
Sprinklers: Yes
Cooking operations: None
Expiring carrier: Harbor Point Mutual Insurance Co. (not on our panel), policy expiring 2027-06-01
Pending or open claims: None known
Bankruptcy or cancellation in last 5 years: No
""")
csv(s, "FICTIONAL,1,2201 Henderson St,Fort Worth,76102,720000,Masonry non-combustible,1972,3800,Yes,none")
write(s, "loss-runs.md", """HARBOR POINT MUTUAL INSURANCE CO. - CLAIMS HISTORY SUMMARY (FICTIONAL)
Insured name: Blue Mesa Outfitters LLC
Coverage year: 2024-06-01 thru 2025-06-01
Coverage year: 2025-06-01 thru 2026-06-01
Coverage year: 2026-06-01 thru 2027-06-01
Losses valued through: 2026-09-30
Claim HPM-7731 | date of loss 2025-09-03 | theft from storage room | paid $2,600.00 | reserve $0.00 | closed
""")

print("built SUB-147 to SUB-152")
