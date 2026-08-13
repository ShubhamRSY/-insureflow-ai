"""Canonical marketplace catalog — 80+ UW / lending / mortgage data sources.

Existing DEMO_CONNECTORS stay the live pull adapters. This catalog is the
discovery + connect registry surface (Bold Penguin-style marketplace) covering
oracles, PAS, AMS, KYC/AML, CAT, claims, and bank-feed vendors.
"""

from __future__ import annotations

from typing import Any

# id, name, type, category, description, verticals
_ROWS: list[tuple[str, str, str, str, str, tuple[str, ...]]] = [
    ("google-drive", "Google Drive", "cloud", "Document Storage", "Broker shared drive / MGA submission folder", ("insurance", "mortgage", "lending")),
    ("sharepoint", "SharePoint / OneDrive", "cloud", "Document Storage", "Carrier or MGA document library (Microsoft 365)", ("insurance", "mortgage", "lending")),
    ("s3-bucket", "AWS S3", "cloud", "Document Storage", "Submission drop bucket", ("insurance", "mortgage", "lending")),
    ("azure-blob", "Azure Blob Storage", "cloud", "Document Storage", "Carrier intake container", ("insurance", "mortgage", "lending")),
    ("box", "Box Enterprise", "cloud", "Document Storage", "Enterprise content cloud for broker submissions", ("insurance",)),
    ("dropbox-business", "Dropbox Business", "cloud", "Document Storage", "Broker file drops and shared submission folders", ("insurance", "mortgage")),
    ("email-inbox", "Email Inbox", "email", "Submission Intake", "Pull broker submission attachments from mailbox", ("insurance", "mortgage", "lending")),
    ("sftp", "SFTP / Broker Portal", "sftp", "Submission Intake", "Wholesale broker automated feed", ("insurance",)),
    ("ivans-download", "IVANS Download", "data", "Industry Exchange", "Carrier/broker transactions via IVANS", ("insurance",)),
    ("acord-al3", "ACORD AL3 / XML Hub", "data", "Industry Exchange", "ACORD 125/126/140 XML and AL3 intake", ("insurance",)),
    ("server-folder", "Server Directory", "filesystem", "Document Storage", "Pull from a folder on the API server", ("insurance", "mortgage", "lending")),
    ("guidewire-policycenter", "Guidewire PolicyCenter", "policy", "Policy Admin", "Submission attachments from PolicyCenter", ("insurance",)),
    ("guidewire-claimcenter", "Guidewire ClaimCenter", "claims", "Claims Admin", "Prior claims and FNOL export", ("insurance",)),
    ("guidewire-billingcenter", "Guidewire BillingCenter", "policy", "Policy Admin", "Premium billing and installment history", ("insurance",)),
    ("duck-creek", "Duck Creek Policy", "policy", "Policy Admin", "Submission documents from Duck Creek Policy", ("insurance",)),
    ("duck-creek-claims", "Duck Creek Claims", "claims", "Claims Admin", "Claims extract for loss-run enrichment", ("insurance",)),
    ("majesco-policy", "Majesco Policy", "policy", "Policy Admin", "P&C policy admin submission bundle export", ("insurance",)),
    ("britecore", "BriteCore", "policy", "Policy Admin", "MGA/carrier PAS — quote, bind, endorsement", ("insurance",)),
    ("nowcerts", "NowCerts", "policy", "Policy Admin", "Agency/MGA cloud PAS", ("insurance",)),
    ("applied-epic", "Applied Epic (Vertafore)", "agency", "Agency Management", "AMS broker submission export", ("insurance",)),
    ("sagitta", "Vertafore Sagitta", "agency", "Agency Management", "Legacy AMS download for independent agents", ("insurance",)),
    ("ams360", "Vertafore AMS360", "agency", "Agency Management", "Independent agency management system", ("insurance",)),
    ("hawksoft", "HawkSoft AMS", "agency", "Agency Management", "Independent agency new-business submissions", ("insurance",)),
    ("qq-catalyst", "QQCatalyst", "agency", "Agency Management", "Vertafore QQ agency platform", ("insurance",)),
    ("ezlynx", "EZLynx", "agency", "Agency Management", "Comparative rater + AMS intake", ("insurance",)),
    ("salesforce-crm", "Salesforce", "crm", "CRM / Distribution", "Broker opportunity files from Opportunity / Case", ("insurance", "lending")),
    ("hubspot-crm", "HubSpot", "crm", "CRM / Distribution", "Producer pipeline and attachment sync", ("insurance", "lending")),
    ("microsoft-dynamics", "Microsoft Dynamics 365", "crm", "CRM / Distribution", "Enterprise CRM submission records", ("insurance",)),
    ("docusign", "DocuSign", "signature", "eSignature", "Signed application packets and attestations", ("insurance", "mortgage", "lending")),
    ("adobe-sign", "Adobe Acrobat Sign", "signature", "eSignature", "Signed applications and disclosures", ("insurance", "mortgage")),
    ("microsoft-teams", "Microsoft Teams", "messaging", "Collaboration", "UW intake channel file drops", ("insurance",)),
    ("slack-intake", "Slack", "messaging", "Collaboration", "#submissions channel file uploads", ("insurance",)),
    ("snowflake", "Snowflake", "data", "Data Warehouse", "Historical loss and exposure warehouse", ("insurance", "lending")),
    ("databricks", "Databricks", "data", "Data Warehouse", "Lakehouse exposure and loss triangles", ("insurance",)),
    ("bigquery", "Google BigQuery", "data", "Data Warehouse", "Carrier analytics warehouse pull", ("insurance",)),
    ("redshift", "Amazon Redshift", "data", "Data Warehouse", "Legacy carrier warehouse", ("insurance",)),
    ("verisk-iso", "Verisk / ISO", "data", "Rating & Loss Data", "ISO loss costs, PPC, and property analytics", ("insurance",)),
    ("verisk-claimsearch", "ISO ClaimSearch", "data", "Claims Data", "Industry prior-claim index", ("insurance",)),
    ("verisk-property", "Verisk Property", "data", "Rating & Loss Data", "Building characteristics and PPC", ("insurance",)),
    ("corelogic", "CoreLogic / Cotality", "data", "Rating & Loss Data", "Property risk, RCV, and catastrophe models", ("insurance", "mortgage")),
    ("corelogic-flood", "CoreLogic Flood", "data", "CAT / Flood", "Flood zone determination", ("insurance", "mortgage")),
    ("clue", "LexisNexis CLUE", "oracle", "Loss History", "Comprehensive Loss Underwriting Exchange", ("insurance",)),
    ("a-plus", "ISO A-PLUS", "oracle", "Loss History", "Automobile / property loss underwriting exchange", ("insurance",)),
    ("ncci", "NCCI Experience Rating", "oracle", "Workers Comp", "Mod, class codes, and experience rating", ("insurance",)),
    ("cat-model", "CAT Model Feed", "oracle", "CAT", "Hurricane / EQ / severe convective storm scores", ("insurance",)),
    ("bureau-credit", "Credit Bureau (commercial)", "oracle", "Credit", "Commercial credit and trade-line snapshot", ("insurance", "lending")),
    ("public-records", "Public Records", "oracle", "Public Records", "Liens, judgments, SOS filings, UCC", ("insurance", "lending")),
    ("osha", "OSHA IMIS", "oracle", "Safety", "Federal OSHA inspection and citation history", ("insurance",)),
    ("rating-agency-ambest", "AM Best", "oracle", "Rating Agency", "Financial strength ratings for reinsurers/carriers", ("insurance",)),
    ("mib-life", "MIB Life", "oracle", "Life Underwriting", "Medical Information Bureau codes", ("insurance",)),
    ("nicb", "NICB", "data", "Claims Data", "National Insurance Crime Bureau referrals", ("insurance",)),
    ("bold-penguin", "Bold Penguin", "marketplace", "Submission Intake", "Small commercial marketplace routing", ("insurance",)),
    ("coverwallet", "CoverWallet", "marketplace", "Submission Intake", "Digital small-commercial placement", ("insurance",)),
    ("simply-business", "Simply Business", "marketplace", "Submission Intake", "SMB quote marketplace", ("insurance",)),
    ("pie-insurance", "Pie Insurance", "marketplace", "Workers Comp", "Digital WC marketplace", ("insurance",)),
    ("next-insurance", "Next Insurance", "marketplace", "Small Commercial", "Direct small-commercial intake", ("insurance",)),
    ("hiscox-connect", "Hiscox Connect", "marketplace", "Submission Intake", "Professional lines digital intake", ("insurance",)),
    ("chubb-small-biz", "Chubb Small Business", "marketplace", "Submission Intake", "Chubb digital small-business portal", ("insurance",)),
    ("nationwide-agency", "Nationwide Agency", "marketplace", "Submission Intake", "Captive/IA comparative submission", ("insurance",)),
    ("travelers-e-sub", "Travelers eSubmission", "marketplace", "Submission Intake", "Travelers broker e-submit", ("insurance",)),
    ("hartford-express", "The Hartford Express", "marketplace", "Submission Intake", "Hartford small-commercial express", ("insurance",)),
    ("cna-connect", "CNA Connect", "marketplace", "Submission Intake", "CNA producer portal", ("insurance",)),
    ("aig-private-client", "AIG Private Client", "marketplace", "HNW", "High-net-worth personal lines intake", ("insurance",)),
    ("lloyds-market", "Lloyd's Market", "marketplace", "Wholesale", "Open-market slip / MRC intake", ("insurance",)),
    ("munich-re-fac", "Munich Re Fac", "reinsurance", "Reinsurance", "Facultative placement feed", ("insurance",)),
    ("swiss-re-fac", "Swiss Re Fac", "reinsurance", "Reinsurance", "Facultative submission to Swiss Re", ("insurance",)),
    ("transre", "TransRe", "reinsurance", "Reinsurance", "Treaty and facultative bordereau", ("insurance",)),
    ("rmis", "RMIS / Origami", "data", "Risk Management", "Insured RMIS loss and exposure export", ("insurance",)),
    ("lexisnexis-bridger", "LexisNexis Bridger", "kyc", "Sanctions / KYC", "Watchlist, PEP, and adverse media", ("insurance", "lending")),
    ("dow-jones-watchlist", "Dow Jones Watchlist", "kyc", "Sanctions / KYC", "DJ sanctions / PEP screening", ("insurance", "lending")),
    ("world-check", "Refinitiv World-Check", "kyc", "Sanctions / KYC", "Global KYC / AML screening", ("insurance", "lending")),
    ("ofac-sdn", "OFAC SDN", "kyc", "Sanctions", "US Treasury SDN + consolidated lists", ("insurance", "lending", "mortgage")),
    ("middesk", "Middesk", "kyc", "Business KYC", "Business identity, SOS, and TIN match", ("lending", "insurance")),
    ("persona", "Persona", "kyc", "Identity", "Consumer identity verification", ("lending", "mortgage")),
    ("socure", "Socure", "kyc", "Identity", "Digital identity + fraud score", ("lending", "mortgage")),
    ("alloy", "Alloy", "kyc", "Identity", "Orchestrated KYC / CIP workflows", ("lending",)),
    ("jumio", "Jumio", "kyc", "Identity", "Document + biometric IDV", ("lending", "mortgage")),
    ("onfido", "Onfido", "kyc", "Identity", "Photo ID and liveness", ("lending", "mortgage")),
    ("experian-biz", "Experian Business", "credit", "Credit", "Commercial credit and Intelliscore", ("lending", "insurance")),
    ("experian-consumer", "Experian Consumer", "credit", "Credit", "Consumer credit for personal lines / mortgage", ("mortgage", "lending")),
    ("transunion", "TransUnion", "credit", "Credit", "Consumer credit + insurance scores", ("mortgage", "lending", "insurance")),
    ("equifax-commercial", "Equifax Commercial", "credit", "Credit", "Commercial credit and SBFE", ("lending", "insurance")),
    ("dnb", "Dun & Bradstreet", "credit", "Credit", "DUNS, PAYDEX, and firmographics", ("lending", "insurance")),
    ("plaid", "Plaid", "banking", "Bank Feeds", "Account linking, balances, and transactions", ("lending", "mortgage")),
    ("yodlee", "Yodlee", "banking", "Bank Feeds", "Aggregated bank and card transactions", ("lending", "mortgage")),
    ("finicity", "Finicity (Mastercard)", "banking", "Bank Feeds", "Open-banking cash-flow verification", ("lending", "mortgage")),
    ("mx-banking", "MX", "banking", "Bank Feeds", "Clean-room transaction categorization", ("lending",)),
    ("ocrolus", "Ocrolus", "banking", "Bank Docs", "Bank-statement OCR + cash-flow analytics", ("lending", "mortgage")),
    ("black-knight", "Black Knight", "mortgage", "Mortgage Data", "MSP servicing and origination data", ("mortgage",)),
    ("fannie-mae", "Fannie Mae", "mortgage", "GSE", "DU findings and ULDD export", ("mortgage",)),
    ("freddie-mac", "Freddie Mac", "mortgage", "GSE", "LPA findings and ULDD", ("mortgage",)),
    ("mers", "MERS", "mortgage", "Mortgage Data", "MIN registration and transfer history", ("mortgage",)),
    ("credit-plus", "Credit Plus", "mortgage", "Credit", "Tri-merge mortgage credit", ("mortgage",)),
    ("fema-nfip", "FEMA NFIP", "cat", "CAT / Flood", "NFIP flood maps and claim history", ("insurance", "mortgage")),
    ("noaa-weather", "NOAA Weather", "cat", "CAT", "Severe weather event confirmation", ("insurance",)),
    ("rms-risklink", "RMS RiskLink", "cat", "CAT Model", "Vendor CAT model scores", ("insurance",)),
    ("air-touchstone", "Moody's RMS / AIR Touchstone", "cat", "CAT Model", "Touchstone catastrophe modeling", ("insurance",)),
    ("karen-clark", "Karen Clark & Co", "cat", "CAT Model", "Independent CAT view", ("insurance",)),
    ("hazardhub", "HazardHub", "cat", "Property Hazard", "Parcel-level hazard scores", ("insurance", "mortgage")),
    ("first-street", "First Street", "cat", "Climate", "Climate flood / fire / heat risk", ("insurance", "mortgage")),
    ("zesty-ai", "ZestyAI", "cat", "Property Hazard", "AI property risk scores", ("insurance",)),
    ("cape-analytics", "Cape Analytics", "imagery", "Property Imagery", "Aerial property condition attributes", ("insurance",)),
    ("eagleview", "EagleView", "imagery", "Property Imagery", "Roof measurements and imagery", ("insurance",)),
    ("pictometry", "Pictometry / EagleView", "imagery", "Property Imagery", "Oblique aerial imagery", ("insurance",)),
    ("betterview", "Betterview", "imagery", "Property Imagery", "Property intelligence platform", ("insurance",)),
    ("google-earth-engine", "Google Earth Engine", "imagery", "Geospatial", "Satellite change detection", ("insurance",)),
    ("snapsheet", "Snapsheet", "claims", "Claims FNOL", "Digital FNOL and virtual adjuster", ("insurance",)),
    ("tractable", "Tractable", "claims", "Claims AI", "Photo-based damage estimating", ("insurance",)),
    ("ccc-intelligent", "CCC Intelligent Solutions", "claims", "Auto Claims", "Auto estimating and total-loss", ("insurance",)),
    ("mitchell", "Mitchell / Enlyte", "claims", "Auto Claims", "Auto and casualty estimating", ("insurance",)),
    ("milliman", "Milliman", "actuarial", "Actuarial", "Life/health/P&C consulting data feeds", ("insurance",)),
    ("limra", "LIMRA", "actuarial", "Life Data", "Life industry persistency and mortality", ("insurance",)),
    ("turbo-rater", "TurboRater", "rating", "Comparative Rater", "Personal lines comparative rater", ("insurance",)),
    ("pl-rating-exchange", "PL Rating Exchange", "rating", "Comparative Rater", "Personal-lines rate exchange", ("insurance",)),
    ("iso-on-demand", "ISO on Demand", "rating", "Rating", "ISO circulars and loss costs API", ("insurance",)),
    ("ncci-class", "NCCI Class Lookup", "rating", "Workers Comp", "Class code and scoping lookup", ("insurance",)),
]


def _row_to_source(row: tuple[str, str, str, str, str, tuple[str, ...]]) -> dict[str, Any]:
    source_id, name, kind, category, description, verticals = row
    return {
        "id": source_id,
        "name": name,
        "type": kind,
        "category": category,
        "description": description,
        "verticals": list(verticals),
        "status": "ready",
        "config_fields": [{"key": "api_key", "label": "API key / account", "placeholder": f"{source_id}-key"}],
        "connectable": True,
    }


MARKETPLACE_SOURCES: list[dict[str, Any]] = [_row_to_source(r) for r in _ROWS]
_BY_ID: dict[str, dict[str, Any]] = {s["id"]: s for s in MARKETPLACE_SOURCES}


def list_marketplace_sources(
    *,
    category: str | None = None,
    vertical: str | None = None,
    q: str | None = None,
) -> list[dict[str, Any]]:
    items = list(MARKETPLACE_SOURCES)
    if category:
        cat = category.lower()
        items = [s for s in items if str(s["category"]).lower() == cat or str(s["type"]).lower() == cat]
    if vertical:
        vert = vertical.lower()
        items = [s for s in items if vert in [v.lower() for v in s["verticals"]]]
    if q:
        needle = q.lower()
        items = [s for s in items if needle in str(s["name"]).lower() or needle in str(s["description"]).lower() or needle in str(s["id"]).lower()]
    return items


def get_source(source_id: str) -> dict[str, Any] | None:
    return _BY_ID.get(source_id)
