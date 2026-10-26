"""Step 6 — one page of the queue. Does not bind and does not send to a carrier.

The React workbench in frontend/ is a different app and is not modified.

# ponytail: stdlib HTML plus one JSONL log. Split the page when a second screen exists.

Run: python underwriting_pipeline/app/workbench.py
Serve: python underwriting_pipeline/app/workbench.py --serve
"""

import html
import json
import os
import re
import fcntl
import shutil
import sys
import tempfile
import threading
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "underwriting_pipeline" / "ai"))
sys.path.insert(0, str(ROOT / "underwriting_pipeline" / "models"))
sys.path.insert(0, str(ROOT / "underwriting_pipeline" / "app"))
import auth
import llm_extract
import package
import pilot
import points
import prepare
import quotes

INBOX = ROOT / "simulation" / "inbox"
PAGE = Path(__file__).resolve().parent / "workbench.html"
LOG = package.DECISIONS_LOG
PENDING = ROOT / "simulation" / "pending-approval"  # missing-info drafts waiting for approval
TO_PRODUCER = ROOT / "simulation" / "to-producer"
TO_CARRIER = ROOT / "simulation" / "to-carrier"
BANNER = ""  # set by serve(); the sandbox screenshots label the page with it
MESSAGES: dict[str, tuple[bool, str]] = {}  # submission -> (ok, plain-words result of the last action); shown once
# D-065 item 5: one line per user-visible feature: date, task or proposal, decision number, what an underwriter sees.
WHATS_NEW = (
    ("2026-10-26", "P-075", "D-133", "When the application says \"Cooking operations: None\" and the operations answer leaves it out, the line is copied as written, with its quote, and marked \"copied by a rule, not read by the model\"; "
     "the system still never writes \"no cooking\" itself. If any other document (or the application's other lines, or a schedule cooking column) mentions cooking, the file is held on an open \"cooking operations\" conflict that shows both sentences."),
    ("2026-10-24", "P-074", "D-132", "A conflict the system cannot check against the document now stays open and holds the file. Each side says why: \"Not verified against the document\" "
     "or \"Approximate figure\" (about, around, roughly, ~). \"$1.42 million\" and \"250k\" are read as numbers. An approximate figure is kept with a review note and never counts as the exact amount."),
    ("2026-10-23", "T-118 (P-072)", "D-124", "Operations never gets \"no cooking\" added automatically. When the application says \"Cooking operations: None\" "
     "and the operations value does not say it, the value stays as stated and keeps its review note, so the underwriter checks cooking against every document."),
    ("2026-10-21", "T-118", "D-122",
     "Two documents that disagree are now seen (P-070). A floor area, a sales figure or a count of units that two documents state "
     "differently is an open conflict on the card, named in plain words (\"square footage\", \"sales or payroll\", \"suite count\"), "
     "the file is held until the underwriter chooses or enters the value, and the producer is asked which figure stands."),
    ("2026-10-21", "PILOT C5", "D-117/D-118 (T-027 C1–C8)", "Every per-value confirmation is now written to the pilot correction log, edited or not. The pilot monitor shows confirmations per field and the correction rate per field (the confirmed values the underwriter corrected, over the confirmed values), and each confirmation is a read-only row on the card with what the AI said and what was confirmed."),
    ("2026-10-21", "B-190", "D-057", "The workbench now needs a signed-in underwriter: OIDC sign-in, a signed session, a per-form token, an Origin check, and an audit row for every view, decision and send. The typed underwriter id is gone; a posted id cannot be used."),
    ("2026-10-21", "PILOT C1–C6", "D-117/D-118 (T-027 C1–C8)", "Assist-only pilot mode: send, package, draft and producer request are disabled with a plain reason; every value needs a per-value confirmation instead of an approve; scope is always shown; AI proposals and weak-field warnings are labelled; corrections, refusals and time per file are logged for the pilot review."),
    ("2026-10-20", "P-067", "D-118", "A rejected value now keeps its reason on the card: a field the extraction could not trust shows why (\"value not inside the cited text\", \"the date does not parse\") instead of an empty reason."),
    ("2026-10-20", "P-066", "D-118", "Every refusal now names its reason in plain words, and no action can crash the page: a blocked send, approve or carrier package shows why it was refused."),
    ("2026-10-19", "P-067", "D-117", "Loss-run dates read from a scan are kept for review when the date digits appear in the cited text: the card shows \"read from a scan — check it against the page\" and is never silently dropped."),
    ("2026-10-19", "T-109a", "D-116",
     "Scope check scope-v4 (P-063): a location label anywhere in the application (\"Loc 1 …; Loc #2 …\", \"Location 2\", \"Bldg 2\") "
     "now means multiple locations, so the file is manual intake. Every send re-checks scope at send time, whatever the status says, "
     "and an out-of-scope file shows \"No send: out of pilot scope at send time (…)\"."),
    ("2026-10-19", "B-428, B-411", "D-113",
     "\"Not read by extraction\" now lists only files the saved run did not read, taken from its own unread rows, "
     "not from the file name. A PDF, workbook, text file or scan that was read (by a reader or OCR) is no longer "
     "shown as not read beside values taken from it. A partly read file stays on the \"Not read\" line with its page."),
    ("2026-10-18", "T-107a", "D-112", "Carrier match reads the application's Line of business and Cooking operations lines (P-061). A nightclub or lounge beside restaurant evidence, and any bar word beside a non-food operation, is now a prohibited class; a bar, tavern or pub beside real restaurant evidence stays a senior referral (P-062). \"Snacks only\" is not restaurant evidence."),
    ("2026-10-18", "T-107d", "D-112", "What's new shows the latest 5 entries; \"Show all\" opens the rest."),
    ("2026-10-18", "T-107c", "D-112", "The account-manager check passes a carrier a senior confirmed on a senior referral (all other gates unchanged), and every card shows that check in words. A send before the senior confirm now says \"a senior referral needs a senior underwriter to confirm the market first\", the same as the card, instead of \"no logged decision\". \"The file is not in appetite\" is no longer shown for a senior referral."),
    ("2026-10-18", "T-106a", "D-111", "The \"operations may be missing\" flag now also reads the Cooking operations, Hood & extinguishing system and Line of business lines: equipment (e.g. snack warmer), \"no gas\", \"None\" under cooking (no cooking) and hood inspection dates are named in the flag when the operations answer leaves them out, so a file no longer shows a clean operations value that drops them."),
    ("2026-10-17", "T-104b", "D-108", "Manual intake now also catches numbered locations: an application or schedule that names \"Location No. 2\", \"Loc #2\", \"Building 2\", \"Bldg 2\" or \"Premises 2\" goes to manual intake with the reason \"multiple locations\"."),
    ("2026-10-17", "T-104a", "D-105", "Manual intake: a file with a scanned application, several locations, non-English documents (Spanish) or no identifiable application (email-only files) is a whole-file manual intake. The card lists every reason (\"Manual intake: scanned application\"); no field is filled in, no carrier route is shown, no missing-info draft is made, and the send, approve and edit are refused with the same reason. Files with several locations now go here whole instead of being read with other-location rows (earlier location notes apply to in-scope files only)."),
    ("2026-10-16", "P-056", "D-103", "Dates with a 2-digit year are read (\"3/1/27\" is 2027-03-01); a date that could be day or month first is read month first and marked NEEDS REVIEW: \"date read month first (US order)\". One low-confidence word on a scan marks the field for review instead of emptying it. A quote that joins two lines with \" ... \" is found. A trailing period is not a reword. Values labelled (loc 1), (loc 2) in one application are locations, not a conflict: the card shows location 1 and says \"values differ by location: ...\". The operations check reads the whole cited document."),
    ("2026-10-16", "P-052", "D-098", "A senior underwriter (marked senior on the underwriter list) can confirm the market on a senior-referral card: pick the carrier and write a reason. The card shows who confirmed and why. The send still needs an approve on this run and the typed line. Never offered on a held file, a file with a prohibited word (bar, pub, lounge), or a vacant, unoccupied or no-utilities file (AG:51)."),
    ("2026-10-16", "P-054", "D-100", "Carrier A direct now needs every other word to be a non-occupancy word (and, LLC, suite, floor...); shop, store, gift, home and trade words go to senior referral. More vacancy words (desocupado, vacante, power disconnected...) block the market confirm. A carrier excluded by any note on the file, including a producer remark such as \"declined by Carrier A\", is not offered, and the card says where the note is."),
    ("2026-10-16", "M1", "D-099", "A senior cannot confirm a carrier the carrier match note excludes (\"not Carrier A\"). The card says which carrier is not offered and why; pick another market, or fix the note at source and re-run the file."),
    ("2026-10-16", "P-053", "D-099", "Carrier A direct only when every operations word is on the allow-list or the short neutral-word list. Any other word goes to senior referral with Carrier A suggested, and the card names the unlisted words. Wholesale never routes directly."),
    ("2026-10-16", "P-051", "D-098", "Carrier A only for a file whose one operation is on the written allow-list (office, retail incl. clothing and thrift shops, light wholesale; AG:29-31). A second operation (office + pub, retail + lounge, office + retail) goes to senior referral (R16). Vacant, unoccupied and \"no utilities\" go to senior referral. Pubs and lounges are prohibited words (AG:46) and are never overridable."),
    ("2026-10-16", "P-049", "D-097", "Carrier match follows the written rules (carrier-match.md); each note shows its rule ID (R1-R14). Carrier A is the only direct route. Restaurants and apartments (sprinklered or not) go to senior referral, with Carrier B or C shown as the suggested market for the underwriter to confirm. Hazardous goods, lab or medical, cold storage, liquor and vacant files go to senior referral even when an office or retail word is present. The unsourced Carrier B $2,000,000 cap is gone."),
    ("2026-10-16", "P-050", "D-096", "When TIV is missing, a held file shows the route its class gives: \"Provisional route: senior_referral (provisional — TIV needed to confirm)\". No TIV cap is applied until the TIV is known, and sending stays blocked. The habitational-without-sprinklers referral now cites AG:37, AG:62."),
    ("2026-10-15", "P-048", "D-095", "A file on hold now shows the route it would take: \"Provisional route: carrier_c (provisional — file on hold: <reason>)\". Sending stays blocked until the hold clears. A scanned or image-only carrier loss run gives \"complete — review pending\" (check the date against the page), not hold."),
    ("2026-10-15", "P-047", "D-094", "Operations keeps every stated detail (alcohol, seats, units, stories, cooking, hours, live music). If the documents state one the value leaves out, it shows NEEDS REVIEW: \"operations may be missing: <item>\". Carrier match and the bar/liquor referral read the full cited operations; \"no bar\" or \"no alcohol\" does not trigger a referral."),
    ("2026-10-15", "P-046", "D-093", "Every loss-run document in a file is checked. When one is accepted but another is undated, a copy or sample, a scan or spreadsheet, or not a recognised carrier layout, the file shows \"complete — review pending\" and the loss-run note names that document and its reason."),
    ("2026-10-15", "P-045/B-343", "D-092", "A loss run marked copy, sample or not from the carrier, or with an impossible or future valued date, shows NEEDS REVIEW with the reason. A carrier run with no valued date says \"loss run found but no valued-as-of date; ask the producer for a dated carrier loss run\". Scanned, image-only and spreadsheet loss runs always show \"loss run from scan/spreadsheet: check it\"."),
    ("2026-10-15", "P-044", "D-090", "A loss run is accepted automatically only in a recognised carrier A/B/C layout. Anything else that looks like one (applicant or agent letters, other layouts) shows NEEDS REVIEW: \"not a recognised carrier loss run\"."),
    ("2026-10-15", "P-042/P-043/B-324", "D-089", "The address check accepts \"City TX\" and \"City, TX\" and every flag says why. A loss-run summary written by the applicant or agent goes to review. A review-pending file with an open conflict is not sent until you choose or enter the value under Conflicts (logged with this run), then approve."),
    ("2026-10-15", "P-040/P-041 (H1/H2)", "D-088", "A no-known-loss letter (English or Spanish) is never a loss run: the loss-run field stays missing with the reason. A file with every field but a value to review or an open conflict shows \"complete — review pending\" and what is pending; sends are gated as before."),
    ("2026-10-14", "P-015/B-264/B-265/B-266", "D-070", "The score shows \"Not scored — reason\" when a file is failed, incomplete or empty, and the cooking and hood lines; each code has a mark-wrong control (logged; the number does not change); the footer names the model and prompt version of the saved run; Suggested market shows only on senior referrals; a stale card lists the changed fields, old to new."),
    ("2026-10-14", "P-027 (B-268)", "D-071", "The cooking line names what was stated as not present (\"no fryer; gas grill\" counts the grill, not the fryer) and shows the quote, including on \"stated none\". Superseded by P-029, then P-030."),
    ("2026-10-15", "P-038 (B-317)", "D-086", "When two documents disagree and one side cannot be cited, the card keeps the cited value and marks it NEEDS REVIEW: \"conflict with rejected value: <other value> (<file>)\"; tick it at approve. A value that mixes two figures (sales with payroll) is still never stored."),
    ("2026-10-14", "P-037 (B-311)", "D-084", "A typed or structured value (application, email, typed PDF, Excel) is never replaced by a scan read. When a scan reads the same field differently, the card keeps the typed value and marks it NEEDS REVIEW: \"scan read differs: <scan value> (<file>); the typed value is kept — check against the page\"; tick it at approve like any needs-review value. A scan value still fills a field no typed document gives."),
    ("2026-10-14", "P-036 (B-304)", "D-083", "Two values that are the same once case, punctuation, \"&\"/\"and\" and St/Rd/Ave/Dr are set aside, or a street-only form of the full address, are one value, not a conflict: the card keeps the fuller value, its Cited text shows each other quote with its file after \"also:\", and the Review note says \"merged: N documents agree\". Any different number stays a conflict. Several schedule addresses are locations, not a premises conflict."),
    ("2026-10-14", "B-297", "D-080", "A card whose extraction failed shows \"Not read — extraction failed\" on the Not read, Not read by extraction and Needs human read lines, never \"none\"."),
    ("2026-10-14", "B-290, B-293, P-033, B-295", "D-079", "A bar, tavern, nightclub, pub or lounge word next to restaurant evidence goes to a senior referral: \"possible bar/liquor exposure — confirm liquor sales\". Bakery, coffee shop and deli count as food service. More words mark a cooking line for review (ningún, nada, w/o, isn't, removed, zero). A card whose extraction failed shows \"Not read — extraction failed\" for cooking and every field."),
    ("2026-10-14", "B-286", "D-078", "The carrier class for a restaurant comes only from generic evidence (restaurant, food service, kitchen, eatery, café, catering, or stated cooking equipment), never from a cuisine or ethnic word. A file named only by a cuisine word shows no_match with that reason."),
    ("2026-10-14", "P-028 (B-269)", "D-075", "Each saved run stores its extraction cache key (files, prompt version, OCR settings, model, host, temperature); the footer shows it in short form, and decision rows save it."),
    ("2026-10-14", "P-031 (B-279, B-280)", "D-074", "Cooking has two rules: a line with no negation word counts the hazards it names; a line with any negation word (no, none, not, without, never, don't, n/a, sin, nunca, ninguno, ninguna) is \"Cooking: needs review\" and the score stays provisional until you record present or none. Only the labelled line itself is read."),
    ("2026-10-14", "P-030 (B-276), B-278", "D-073", "Cooking: a negation directly before a hazard (\"no gas grill\") means none; any other line with a negation word (\"fryer, none\", \"none\", \"N/A\") is \"needs review\". While it is, the score reads \"Provisional — cooking not scored\"; an underwriter records present or none with a reason, logged with the run hash, and only then do points apply. The negation rule was simplified by P-031."),
    ("2026-10-14", "P-029 (B-272, B-274), B-273", "D-072", "A cooking line with a negation and more than one hazard term (or a hazard term past or/but/pero/&/-/period) shows \"Cooking: needs review\" with the quote and adds no points; it is acknowledged at approve like any needs-review value. N/A shows as not stated. Rule replaced by P-030."),
    ("2026-10-14", "P-026", "D-069", "Every approve logs the saved run's hash; a re-saved file shows \"Re-review needed: file changed since your approval\" and the send is refused for everyone until you approve and acknowledge again."),
    ("2026-10-14", "B-248", "D-069", "The sent date comes from one place, the Sent-on line in the package file, on the card and in quote tracking alike (older packages show \"not recorded\")."),
    ("2026-10-14", "B-252", "D-069", "A sandbox run (--sandbox) writes the page, logs and outboxes into a temporary copy; the real files are never touched."),
    ("2026-10-14", "Session B", "D-069", "Each card has one History panel (decisions, acknowledgments, sends, resends: who, why, when, run hash), subjectivity closures with the \"evidence only\" label, a Suggested market field, and a model and prompt version footer."),
    ("2026-10-14", "B-244", "D-068", "A low-confidence scan value is a needs-review value: the send is refused for everyone until the latest approve acknowledged every one; the card names them."),
    ("2026-10-14", "B-247", "D-068", "A resend writes a new package file (SUB-###-resend-N.md); earlier files are kept and the card lists every package file sent."),
    ("2026-10-14", "B-249", "D-068", "The send form is hidden until an approve is logged; the card says \"Approve first\"."),
    ("2026-10-14", "B-231", "D-067", "Saved-run cards come first; every card with no usable saved run is folded into one closed section \"No saved run (N)\" with the reason and how a run is created."),
    ("2026-10-14", "B-232", "D-067", "The Send to carrier form names the carrier before you confirm; when there is no carrier or the file is refused or incomplete, the card says why there is no send."),
    ("2026-10-14", "B-233", "D-067", "A package already sent shows \"Already sent on <date> to <carrier>\"; a second send is refused unless you tick resend and write a reason, which is logged."),
    ("2026-10-14", "P-025", "D-067", "A scan read below the confidence line (0.50 to 0.74) is kept, marked \"Low-confidence scan read — check against the page\", and must be ticked at approve."),
    ("2026-10-14", "P-016", "D-064", "Needs-review values show their reason and cited text; approve needs each one ticked; unread pages are listed."),
    ("2026-10-14", "D-066 item 10", "D-066", "The page shows only the saved run (status, hash check, manifest check). It never runs extraction or a model call."),
    ("2026-10-14", "D-066 items 2/4/8", "D-066", "Every refused decision or send is shown on its card in plain words with the reason. No bare error pages."),
    ("2026-10-14", "D-066 item 1", "D-066", "Send to carrier on the card: type the exact line \"send to carrier SUB-###\"; it goes through the same send gate."),
    ("2026-10-14", "D-066 item 13", "D-066, D-050", "The missing-info draft shows on the card with an approve action (user override; refused for failed or all-rejected files)."),
)
_LOG_LOCK = threading.Lock()  # ponytail: one process writes the log; a file lock if a second writer appears


NEGATED = re.compile(r"(?<!\w)(?:no|not an?|without(?: an?)?|sin|non)[- ]\w+")  # P-047 (c): "no bar" is not a bar
NEGATED_EQUIP = re.compile(r"(?<!\w)(?:no|not an?|without(?: an?)?|sin|non)[- ](?:[\w-]{1,30} ){0,2}[\w-]{1,30}|(?<!\w)(?:[\w-]{1,30} ){0,2}[\w-]{1,30} ?[:=-] ?(?:none|0|n/a|nil|no)(?!\w)|(?<!\w)(?:[\w-]{1,30} ){0,2}[\w-]{1,30} (?:is |are )?(?:not|never) (?:used|in use|present|installed|operated)")  # T-107a review: "no deep fryer", "Fryers: 0", "Oven not used" are not equipment; equipment only, never for bar/class words (M1, D-112: stricter wins)


def _line(report: dict, key: str) -> str:
    """P-061 (D-112): the application's Line of business / Cooking operations line (not the insured's name), negated words dropped. "" in a run saved before P-061."""
    return NEGATED.sub(" ", ((report.get("class_lines") or {}).get(key) or "").lower())


def class_text(report: dict) -> str:
    """P-061: the one class text, operations plus the Line of business line. _match and package.confirm_problem both read it."""
    return f"{_ops(report)} {_line(report, 'line_of_business')}"


def _route_value(row: dict) -> str:
    """P-075 (code review 4): the route reads the operations value as it was before a rule copied the cooking none-line into it,
    so a copied "No kitchen" or "Nil" can never add an unlisted word or a restaurant word to the route."""
    value = row.get("value") or ""
    if row.get("rule_copied"):
        for part in row.get("also_quoted") or []:
            if value.endswith("; " + str(part.get("quote"))):
                value = value[: -len("; " + part["quote"])]
    return value


def _ops(report: dict) -> str:
    """P-047 (c): the full operations, value and cited text, so a detail the value dropped still routes. Negated words are removed."""
    for row in report["fields"]:
        if row["field_id"] == "operations" and row["value"]:
            return NEGATED.sub(" ", f"{_route_value(row)} {row.get('quote') or ''} {row.get('context') or ''}".lower())  # H1: and the rule lines
    return ""


# P-049 (D-097): the rules and word lists are deliverables/head-of-underwriting/carrier-match.md (R1..R14, W1, W2); notes cite the IDs.
# D-059 as amended by D-060. Whole word or exact phrase, case-insensitive, never substring.
# Spanish entries are translations of sourced classes only (D-060); @responsible-ai review is B-197.
# ponytail: plain lists in code; move to a data file when @head-of-underwriting edits them often.
PROHIBITED = ("bar", "bars", "nightclub", "nightclubs", "tavern", "taverns", "cantina", "taberna", "antro", "discoteca",
              "cannabis", "marijuana", "marihuana", "dispensary", "dispensario", "fireworks", "firework", "explosives", "explosive",
              "fuegos artificiales", "explosivos", "armed security", "armed guard", "seguridad armada", "guardia armado",
              "student housing", "subsidized housing", "alojamiento estudiantil", "vivienda subsidiada",
              "hookah", "adult entertainment", "ammunition", "bail bonds", "sawmill", "sawmills", "pallet manufacturing",
              "plastics manufacturing", "recycling", "pub", "pubs", "lounge", "lounges")  # W1 (R1; AG:45-50); P-051: pubs, lounges per AG:46. Never overridable (D-057/D-060)
# W2 (R14, D-097 1d): referral words, checked before any class word; each sends the file to senior_referral, never to a carrier.
NO_UTILITIES = ("no utilities", "without utilities", "utilities off", "utilities disconnected", "utilities shut off", "power off", "power disconnected",
                "sin servicios", "sin luz", "no tenants", "building empty", "empty building", "utilities are off", "utilities turned off", "power is off",
                "no power", "no electricity", "electricity off", "electricity disconnected", "not occupied", "sin ocupar")  # P-051 (c), P-054 (b): read on the raw text, before the negation drop
VACANT = ("vacant", "vacancy", "vacante", "vacío", "vacio", "vacía", "vacia", "desocupado", "desocupada", "unoccupied", "abandoned", "abandonado", "abandonada", "deshabitado", "deshabitada") + NO_UTILITIES  # W2e; AG:51 lists true vacancy and no utilities as prohibited, so no market confirm (P-052)
REFERRAL = (
    (("fertilizer", "fertilizers", "pesticide", "pesticides", "herbicide", "chemical", "chemicals", "hazardous", "flammable", "solvent",
      "solvents", "propane", "fuel", "fertilizante", "pesticida", "químico", "químicos"), "wholesale/retail with hazardous goods - not Carrier A (R14; AG:31)"),
    (("laboratory", "laboratories", "lab", "medical", "clinic", "clinics", "therapy", "therapist", "physician", "doctor", "dental", "dentist",
      "pediatric", "chiropractic", "hospital", "médico", "clínica", "terapia", "pediátrico"), "lab or medical occupancy - not Carrier A (R14; AG:29)"),
    (("cold storage", "refrigerated", "freezer", "freezers", "almacenamiento en frío", "refrigerado"), "cold storage - not Carrier A (R14; AG:31)"),
    (("liquor", "liquor store", "package store", "licor"), "liquor sales, share of receipts not checked - not Carrier A (R14; AG:30)"),
    (VACANT, "vacant, unoccupied or no utilities: renovation with signed GC contract is a referral, true vacancy is prohibited; a person decides (R14; AG:40, AG:51)"),
)
NOT_READ = "Not read — extraction failed"  # D-079 (B-295)
MI_NOT_READ = "whole file: not read (manual intake)"  # P-055 (T-104a UI H1)


def not_read_by_extraction(report: dict | None, files: list[str]) -> list[str]:
    """B-428 (D-113): files extraction did not read, for the "Not read by extraction" line.
    The saved run's unread rows are the log of record: a .pdf, .xlsx, .txt or scan is read by a reader or OCR, so its
    name alone never means it was skipped (the old `.md`/`.csv` name test named a pdf that gave values, B-411/B-428).
    A partly read file (some pages unread) is not listed here; the "Not read" line carries that page.
    Only a run saved before unread rows existed (no key at all) falls back to the old name test."""
    if report is not None and "unread" in report:
        return sorted({row.get("file") for row in report["unread"] or [] if row.get("page") is None and row.get("file")})
    return sorted(name for name in files if not name.endswith((".md", ".csv")))


NEVER_SOFT = ("nightclub", "nightclubs", "lounge", "lounges")  # P-062 (D-112): R1 even beside restaurant evidence; bar, tavern, pub stay R2 there
SNACKS = ("pre-packaged snacks only", "prepackaged snacks only", "pre packaged snacks only", "snacks only", "snack warmer")  # P-062 (b): not restaurant evidence
EQUIP = ("fryer", "fryers", "deep fryer", "deep fryers", "burner", "burners", "flat-top", "flat top", "griddle", "charbroiler", "char-broiler",
         "broiler", "oven", "ovens", "smoker", "smokers", "comal", "wok", "freidora", "freidoras", "horno")  # P-061: stated cooking equipment (R9); "snack warmer" and "range" are not here
BAR_WORDS = ("bar", "bars", "tavern", "taverns", "nightclub", "nightclubs", "pub", "pubs", "lounge", "lounges")  # D-079

# P-051 (a): the Carrier A allow-list, one group per written guide line. Only a file whose one operation is on it routes to Carrier A.
ALLOW_A = {
    "office": ("office", "offices", "office building", "oficina", "oficinas"),  # AG:29 "Office: tenants and office-building lessors"
    "retail": ("retail", "retail store", "dry retail", "dry goods", "storefront", "clothing", "clothing store", "boutique", "apparel",
               "thrift shop", "thrift shops", "thrift store", "thrift stores", "comercio minorista", "tienda minorista", "tienda de ropa", "ropa"),  # AG:30 "Retail: dry goods, clothing, professional services storefront"
    "wholesale": ("wholesale", "light wholesale", "mayoreo", "mayorista"),  # AG:31 "Wholesale: light"
}
# P-051 (b): an occupancy word for a class that is not a target (AG:33 "No other class is a target"). Beside an allow-list word it is a
# second operation (senior_referral); alone it is R8. A word on no list goes to senior_referral under P-053 (NEUTRAL below).
OTHER_OPS = ("gym", "gyms", "fitness", "salon", "salons", "spa", "spas", "daycare", "day care", "school", "schools", "church", "churches",
             "hotel", "hotels", "motel", "motels", "theater", "theatre", "auto repair", "car wash", "gas station", "manufacturing", "factory")
# P-053 (D-099): the direct Carrier A route needs every operations word to be an allow-list phrase, a listed negation or a neutral word
# below; any other word goes to senior_referral with Carrier A suggested. Read on the raw text, so "no tenants" is not dropped.
NEUTRAL_NO = ("no food", "no alcohol", "no liquor", "no cooking", "no inventory", "no goods", "no repackaging", "no manufacturing", "held for sale",
              "cooking operations none", "cooking none")  # check-P-054 H2: "cooking" only as the empty label, matched after punctuation is dropped
# P-054 (a): non-occupancy words only. A word that names a business, a trade or goods (shop, store, gift, home, tax...) is never neutral.
NEUTRAL = frozenset((
    "and", "or", "of", "on", "by", "for", "with", "the", "a", "an", "at", "in", "to", "de", "del", "la", "el", "en", "y",  # joining words
    "llc", "inc", "co", "corp", "ltd", "lp", "pllc", "dba",  # company suffixes
    "operations", "none",  # field labels in the cited text ("cooking" is an occupancy word: check-P-054 H2)
    "floor", "floors", "story", "stories", "suite", "ground", "level", "room", "back", "front",  # where in the building
    "clients", "appointment", "appointments"))  # how visitors come, not what the business is
ORDINAL = re.compile(r"\d+(st|nd|rd|th)?")


def _unlisted(raw: str) -> list[str]:
    """P-053: the operations words that are not an allow-list phrase, a listed negation or a neutral word. Empty = Carrier A direct."""
    raw = " ".join(re.findall(r"[^\W_]+", raw.lower()))  # "Cooking: None" and "cooking - none" read alike
    for phrase in sorted(NEUTRAL_NO + tuple(w for words in ALLOW_A.values() for w in words), key=len, reverse=True):
        raw = re.sub(rf"(?<!\w){re.escape(phrase)}(?!\w)", " ", raw)
    return [w for w in re.findall(r"[^\W_]+", raw) if w not in NEUTRAL and not ORDINAL.fullmatch(w)]


CLASSES = {
    **ALLOW_A,
    # D-078 (B-286): generic restaurant evidence only, never a cuisine or ethnic word; Spanish only as translations (D-060).
    "b": ("restaurant", "restaurants", "restaurante", "restaurantes", "food service", "foodservice", "servicio de alimentos",
          "kitchen", "kitchens", "cocina", "eatery", "eateries", "comedor", "cafe", "café", "cafeteria", "cafetería",
          "catering", "banquetes", "bakery", "bakeries", "coffee shop", "coffee shops", "deli", "delis"),  # D-079 (B-293)
    "contractor": ("contractor", "contractors", "contratista", "roofing", "roofer", "techado", "techador", "handyman", "painter", "painting",
                   "pintor", "pintura", "carpenter", "carpentry", "carpintero", "carpintería", "flooring", "drywall", "plumbing", "electrician",
                   "hvac", "glazier", "mason"),  # R11
    "habitational": ("habitational", "habitacional", "apartment", "apartments", "apartamento", "apartamentos", "flats", "multifamily",
                     "multifamiliar", "duplex", "triplex", "fourplex"),
}
PILOT_TIV = 5_000_000  # R13, inclusive. R15 (P-049): the unsourced Carrier B $2,000,000 cap is removed
OUT_TIV = "outside pilot TIV limit (R13; AG:16)"
CONFIRM = ", underwriter confirms"  # P-049 (c): Carrier B and C are suggested markets only


def _has(text: str, words) -> bool:
    return any(re.search(rf"(?<!\w){re.escape(w)}(?!\w)", text) for w in words)


AREA_UNIT = re.compile(r"(?<![a-z])(sq\.?\s*f(?:ee|oo)?t\.?|sqft|sf|square\s+f(?:ee|oo)t)(?![a-z])", re.I)


def _tiv(report: dict) -> int | None:
    """D-061: the existing normalizer (220k, $1.2M). None when missing, blank, "TBD" or unreadable."""
    for row in report["fields"]:
        if row["field_id"] == "tiv_building":
            if AREA_UNIT.search(row["value"] or ""):
                return None  # B-209 (P-022, D-063): an area is not a dollar amount
            return prepare.amount_value(row["value"] or "")
    return None


PROVISIONAL = "provisional — file on hold: {}"  # P-048 (c) (D-095)
PROVISIONAL_TIV = "provisional — TIV needed to confirm"  # P-050 (D-096): a class-based route while TIV is missing


def match(report: dict) -> dict:
    """route: carrier_a/b/c, no_match, hold, senior_referral or manual_intake (P-055: out of pilot scope; no carrier, provisional or suggested route). overridable only for no_match (D-057). Never declines.
    P-048 (c): routing always runs. A held file also carries "provisional" (the route it would take once the hold clears, or None when
    the class, TIV or sprinkler answer it needs is missing) and its label. route stays "hold", so every send gate stays shut."""
    m = _match(report, gated=True)
    if m["route"] == "hold":
        p = _match(report, gated=False)
        m["provisional"] = p["route"] if p["route"] != "hold" else None
        m["provisional_note"] = p["note"] if p["route"] != "hold" else ""
        tiv = _tiv(report)
        m["provisional_label"] = PROVISIONAL_TIV if p["route"] != "hold" and (tiv is None or tiv <= 0) else PROVISIONAL.format(m["note"])
    return m


def _match(report: dict, gated: bool) -> dict:
    ops = _ops(report)

    def out(route, note="", suggested="", overridable=False):
        return {"route": route, "note": note, "suggested": suggested, "overridable": overridable}

    if report.get("status") == prepare.MANUAL_INTAKE:  # P-055 (D-105): no carrier, provisional or suggested route; not a hold either
        return out("manual_intake", prepare.status_refusal(report))

    cls = class_text(report)  # P-061: class, bar and prohibited words come from the operations and the Line of business line; R17 reads ops only
    snack = _has(cls, SNACKS)  # P-062 (b): a snack warmer or "snacks only" kitchen is not restaurant evidence
    word_food = _has(cls, CLASSES["b"]) and not snack
    raw = " ".join(f"{_route_value(r)} {r.get('quote') or ''} {r.get('context') or ''}" for r in report["fields"] if r["field_id"] == "operations").lower()
    raw_cook = ((report.get("class_lines") or {}).get("cooking_operations") or "").lower()
    equip = _has(NEGATED_EQUIP.sub(" ", f"{raw} {raw_cook}"), EQUIP) or ((report.get("cooking") or {}).get("equipment") or {}).get("state") == "yes"  # P-061: equipment in operations or the Cooking operations line
    food = bool(ops) and (word_food or equip)
    barred = bool(ops) and _has(cls, BAR_WORDS)
    other_prohibited = bool(ops) and _has(cls, tuple(w for w in PROHIBITED if w not in BAR_WORDS))
    if other_prohibited or (barred and not food) or (barred and food and _has(cls, NEVER_SOFT)):  # W1 before the hold gate, as since D-059 (carrier-match.md lists R5/R6 first: B-378); D-112: a bar word beside a non-food operation is R1 too (stricter of W1 and W1b); P-062 (a): nightclub, lounge never softened
        hit = next(w for w in PROHIBITED if _has(cls, (w,)))  # UI check H1: name the word and the line it was read from
        return out("no_match", f"prohibited class (R1; AG:45-50): \"{hit}\" in {'operations' if _has(ops, (hit,)) else 'the Line of business line (P-061)'}")
    if (gated and not prepare.ready_to_route(report)) or not ops:  # P-041: review pending routes as complete did before
        return out("hold", "open conflict" if ops and report.get("status") == prepare.REVIEW_PENDING else "missing information")
    tiv = _tiv(report)
    if tiv is None or tiv <= 0:
        if gated:
            return out("hold", "TIV missing or unreadable")  # D-061, B-203 (D-062): never read as 0 or negative
        tiv = None  # P-050 (D-096): the provisional route is class-based; no TIV cap or limit is applied without a TIV
    over = lambda cap: tiv is not None and tiv > cap
    if barred and food:  # D-079 (B-290): a bar word with restaurant evidence is a person's call, not a rule's
        return out("senior_referral", "possible bar/liquor exposure — confirm liquor sales (R2; AG:46, AG:39)")
    w2 = re.sub(r"(?<!\w)wet[\s-]+chemical(?!\w)", " ", ops) if food else ops  # a kitchen's wet chemical hood is fire suppression, not hazardous goods (as P-047); only with restaurant evidence
    for words, note in REFERRAL:  # W2 (D-097 1d): a referral word always wins over appetite (class) words
        if _has(w2, words) or _has(raw, tuple(w for w in words if w in NO_UTILITIES)):  # raw: _ops drops "no <word>"
            return out("senior_referral", note + (f"; {OUT_TIV}" if over(PILOT_TIV) else ""))
    hit = [k for k, words in CLASSES.items() if _has(cls, words) and not (k == "b" and snack)]
    if "b" not in hit and equip:
        hit.append("b")  # D-078, P-061: stated cooking equipment is generic restaurant evidence
    if not hit:
        return out("no_match", "readable class on no carrier list (R8; KO 8); a restaurant needs generic evidence (restaurant, food service, kitchen, eatery, café, catering or stated cooking equipment), never a cuisine word (D-078)", overridable=True)
    spr = report.get("sprinklers")
    unsprinklered = spr == "no" or _has(raw, ("unsprinklered", "no sprinklers", "sprinklers no"))  # raw: _ops drops "no <word>"
    knock = "; AG:61 knock-out candidate, a person decides" if "habitational" in hit and unsprinklered and food else ""  # R12: never a decline
    if len(hit) > 1 and set(hit) <= set(ALLOW_A):  # P-051 (b): two allow-list groups (office and retail) are two operations
        return out("senior_referral", "more than one operation (R16; AG:33): " + ", ".join(hit) + "; a person decides")
    if set(hit) <= set(ALLOW_A) and _has(ops, OTHER_OPS):  # P-051 (b): an allow-list word beside a non-target occupancy
        return out("senior_referral", "a second operation that is not a target class (R16; AG:33); a person decides")
    if len(hit) > 1:
        return out("senior_referral", "class matches more than one carrier (R7; KO 7): " + ", ".join(hit) + knock)
    kind = hit[0]
    big = f"; {OUT_TIV}" if over(PILOT_TIV) else ""
    if kind == "contractor":
        return out("senior_referral", "contractor (R11; AG:38, AG:62); suggested market: Carrier B" + CONFIRM + big, suggested="carrier_b")
    if kind == "habitational":
        if not unsprinklered and not (spr == "yes" or "sprinklers yes" in ops or _has(ops, ("sprinklered",))):
            return out("hold", "habitational: sprinkler answer missing")
        bare = "; no sprinklers" if unsprinklered else ""  # R12: the sprinkler fact stays on the card
        return out("senior_referral", "habitational (R12; AG:37, AG:62)" + bare + "; suggested market: Carrier C" + CONFIRM + big, suggested="carrier_c")
    if kind == "b":  # R10 (AG:39, AG:62): every restaurant or cooking occupancy is a senior referral
        return out("senior_referral", "restaurant / cooking occupancy (R10; AG:39, AG:62); suggested market: Carrier B" + CONFIRM + "; its 3 clean loss years are not checked" + big, suggested="carrier_b")
    if over(PILOT_TIV):
        return out("senior_referral", OUT_TIV)
    assert kind in ALLOW_A  # P-051 (a): Carrier A only from the allow-list
    if not _has(ops, ALLOW_A[kind]):  # P-061: a class read only from the Line of business line never routes directly (R17 reads operations)
        return out("senior_referral", "class read from the line of business only (P-061; AG:29-31); a person decides; suggested market: Carrier A" + CONFIRM, suggested="carrier_a")
    suggest_a = "; suggested market: Carrier A" + CONFIRM
    if kind == "wholesale":  # P-053: wholesale never routes directly; light or not is a person's call (AG:31 "Wholesale: light")
        return out("senior_referral", "wholesale: whether it is light is a person's call (P-053; AG:31)" + suggest_a, suggested="carrier_a")
    extra = _unlisted(raw)
    if extra:  # P-053: a word outside the allow-list and the neutral list (e.g. "office and casino")
        return out("senior_referral", "words not on the Carrier A allow-list: " + ", ".join(list(dict.fromkeys(extra))[:5]) + " (P-053; AG:29-30)" + suggest_a, suggested="carrier_a")
    return out("carrier_a", "Carrier A (R14; AG:29-31); verify: no restaurant, liquor <= 10%, no cold storage, no hazardous goods, no lab or medical")


def route(report: dict) -> str:
    return match(report)["route"]


def snippet(folder: Path, row: dict) -> str:
    source = row.get("source")
    if not source or row.get("start") is None:
        return ""
    path = folder / source
    if not path.is_file():
        return ""
    try:
        text = path.read_text()
    except UnicodeDecodeError:  # a scan or other binary source has no text to quote; the saved quote is shown instead
        return ""
    return text[row["start"] : row["end"]]


def saved_report(name: str) -> tuple[dict | None, str]:
    """Item 10 (D-066): the last saved run only. Returns (report, "") or (None, plain reason). No extraction, no model call."""
    try:
        saved = prepare.read_saved_run(name)
    except ValueError as exc:
        return None, str(exc)
    fields = saved.get("fields") or []
    return {
        **saved,
        "fields": fields,
        "conflicts": saved.get("conflicts") or [],
        "missing": [r["field_id"] for r in fields if not r.get("value")],
        "extra": [],  # not stored in the saved run
        "locations": None,  # not stored in the saved run
        "status_reason": prepare.REJECT_REASON if saved.get("status") == "all_values_rejected" else None,
    }, ""


def load_queue(only: str | None = None) -> list[dict]:
    folders = sorted(p for p in INBOX.iterdir() if p.is_dir() and p.name.startswith("SUB-"))
    if only:
        folders = [folder for folder in folders if folder.name == only]
    rows = []
    for folder in folders:
        report, problem = saved_report(folder.name)
        report = package.with_resolutions(report, folder.name) if report is not None else None  # B-324: logged resolutions on this run
        files = sorted(p.name for p in folder.iterdir() if p.is_file())
        ignored = not_read_by_extraction(report, files)  # B-428 (D-113)
        row = {"id": folder.name, "report": report, "saved_problem": problem, "files": files, "ignored": ignored}
        if report is not None:
            row.update(
                manifest=prepare.manifest_problem(folder.name, inbox=INBOX),
                scope_now=prepare.scope_problem(folder.name, inbox=INBOX),  # P-063: the send gate's own scope re-check
                route=route(report),
                note=match(report)["note"],
                suggested=match(report)["suggested"],
                provisional=match(report).get("provisional_label") and match(report),  # P-048 (c)
                score=scored(folder.name, report),
                marks=code_marks(folder.name),
                snippets={r["field_id"]: snippet(folder, r) for r in report["fields"]},
            )
        rows.append(row)
    return rows


def ai_version() -> str:
    model = os.environ.get("LLM_MODEL") or "local-default"
    return model + "+rules-d015"


def marks_path() -> Path:
    return LOG.with_name("code_marks.jsonl")  # a sibling file: a mark is not a decision and never changes the send gate (W1)


def code_marks(sub: str) -> list[dict]:
    path = marks_path()
    rows = []
    for line in path.read_text().splitlines() if path.is_file() else []:
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if isinstance(r, dict) and r.get("submission") == sub:
            rows.append(r)
    return rows


def mark_code(payload: dict) -> dict:
    """P-015 W1: an underwriter marks a shown reason code wrong, with a reason. Logged; the number, match() and the send gate do not change."""
    sub, code = (payload.get("submission") or "").strip(), (payload.get("code") or "").strip()
    actor, reason = (payload.get("underwriter_id") or "").strip(), (payload.get("reason") or "").strip()
    if not actor or actor not in package.underwriters():
        raise ValueError("only an id on underwriters.json may mark a code wrong")
    if not reason:
        raise ValueError("a reason is required")
    report, problem = saved_report(sub)
    if report is None:
        raise ValueError(problem)
    if code not in points.CODES or code not in scored(sub, report)["reason_codes"]:
        raise ValueError(f"{code or 'no code'} is not a code shown for {sub}; codes cannot be added (A1)")
    row = {"submission": sub, "code": code, "reason": reason, "underwriter_id": actor, "date": date.today().isoformat(),
           "at": datetime.now().astimezone().isoformat(timespec="seconds"), "points_version": points.POINTS_VERSION, "run_hash": report.get("saved_hash")}
    with _LOG_LOCK:
        marks_path().parent.mkdir(parents=True, exist_ok=True)
        with marks_path().open("a") as handle:
            handle.write(json.dumps(row) + "\n")
    return row


def calls_path() -> Path:
    return LOG.with_name("cooking_calls.jsonl")  # B-278 (D-073): a sibling log, like code marks; follows the sandbox


def cooking_call_for(sub: str, report: dict) -> dict | None:
    """The latest recorded cooking call for this submission and this run (same run_hash), or None."""
    path, last = calls_path(), None
    for line in path.read_text().splitlines() if path.is_file() else []:
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if isinstance(r, dict) and r.get("submission") == sub and r.get("run_hash") == report.get("saved_hash"):
            last = r
    return last


def scored(sub: str, report: dict) -> dict:
    """The one score the page shows and the decision row saves: the run with this run's cooking call applied, if any."""
    return points.score_run(points.apply_cooking_call(report, cooking_call_for(sub, report)))


def cooking_call(payload: dict) -> dict:
    """B-278 (D-073): a listed underwriter records cooking present or none, with a reason, on a needs-review cooking line.
    Logged with the run hash; points apply only after it, and only for that run."""
    sub, call = (payload.get("submission") or "").strip(), (payload.get("call") or "").strip()
    actor, reason = (payload.get("underwriter_id") or "").strip(), (payload.get("reason") or "").strip()
    if not actor or actor not in package.underwriters():
        raise ValueError("only an id on underwriters.json may record the cooking call")
    if call not in ("present", "none"):
        raise ValueError("choose present or none")
    if not reason:
        raise ValueError("a reason is required")
    report, problem = saved_report(sub)
    if report is None:
        raise ValueError(problem)
    if (payload.get("run_hash") or "") != report.get("saved_hash"):
        raise ValueError("the file changed since this card was shown; reload and look again")
    if ((report.get("cooking") or {}).get("equipment") or {}).get("state") != "needs_review":
        raise ValueError("cooking on this file is not waiting for a call")
    row = {"submission": sub, "call": call, "reason": reason, "underwriter_id": actor, "run_hash": report.get("saved_hash"),
           "at": datetime.now().astimezone().isoformat(timespec="seconds"), "points_version": points.POINTS_VERSION}
    with _LOG_LOCK:
        calls_path().parent.mkdir(parents=True, exist_ok=True)
        with calls_path().open("a") as handle:
            handle.write(json.dumps(row) + "\n")
    return row


def run_record(sub: str) -> dict:
    """P-015 E2: score, codes, versions and model/prompt of the saved run at the click. Never the form, never the environment."""
    report, problem = saved_report(sub) if re.fullmatch(r"SUB-\d+", sub or "") else (None, "no saved run")
    if report is None:
        return {"points": None, "not_scored_reason": f"Not scored — {problem}", "reason_codes": [], "points_version": points.POINTS_VERSION,
                "model_version": None, "prompt_version": None, "cache_key": None}
    s = scored(sub, report)
    return {"points": s["points"], "not_scored_reason": s["not_scored_reason"], "reason_codes": s["reason_codes"], "points_version": s["points_version"],
            "model_version": report.get("model_version"), "prompt_version": report.get("prompt_version"),
            "cache_key": report.get("cache_key")}  # P-028 (D-075): from the saved run; null for a run saved before P-028


def field_values(report: dict) -> dict:
    return {r["field_id"]: r.get("value") for r in report.get("fields") or []}


def correction_counts(log_path: Path) -> dict:
    counts = {"approve": 0, "edit": 0, "decline": 0}
    if not log_path.exists():
        return counts
    for line in log_path.read_text().splitlines():
        if not line.strip():
            continue
        action = json.loads(line).get("action")
        if action in counts:
            counts[action] += 1
    return counts


def record_decision(payload: dict, log_path: Path) -> dict:
    actor = (payload.get("underwriter_id") or "").strip()
    action = (payload.get("action") or "").strip()
    reason = (payload.get("reason") or "").strip()
    if not actor:
        raise ValueError("underwriter id required")
    if actor not in package.underwriters():
        raise ValueError("only an id on underwriters.json may log a decision (D-055); AI roles never count")
    if action not in {"approve", "edit", "decline", "resolve", "confirm"}:
        raise ValueError("action must be approve, edit, decline, resolve or confirm")
    if action == "approve" and pilot.active():
        pilot.guard("approve", (payload.get("submission") or "").strip())
    if action == "confirm" and not pilot.active():
        raise ValueError("confirm is an assist-only pilot action")
    if action == "resolve":  # B-324 (D-089): the underwriter chooses or enters the value of one open conflict on this run
        submission = (payload.get("submission") or "").strip()
        saved = prepare.read_saved_run(submission)
        shown = (payload.get("run_hash") or "").strip()
        if shown and shown != saved["saved_hash"]:
            raise ValueError("the saved run changed since this card was opened; reload the page and review again")
        field, value = (payload.get("conflict_field") or "").strip(), (payload.get("chosen_value") or payload.get("entered_value") or "").strip()
        if (payload.get("entered_value") or "").strip():
            value = payload["entered_value"].strip()  # a typed value wins over the choice
        open_ = [c.get("field") for c in saved.get("conflicts") or [] if c.get("resolution") != "resolved"]
        if field not in open_:
            raise ValueError(f"no open conflict on {field or 'that field'} in this run")
        if not value:
            raise ValueError("choose one of the values or enter the value")
        with _LOG_LOCK:
            return _append({**payload, "conflict_field": field, "new_value": value, "run_hash": saved["saved_hash"], "run_record": run_record(submission)}, action, actor, reason, log_path)
    if action in {"edit", "decline"} and not reason:
        raise ValueError("edit and decline require a reason")
    field_id, new_value = (payload.get("field_id") or "").strip(), (payload.get("new_value") or "").strip()
    if action != "edit" and (field_id or new_value):
        raise ValueError("field_id and new_value belong to an edit")
    if field_id or new_value:  # D-056 (B-139): an edit that changes a field stores the field and its new value
        if field_id not in prepare.FIELDS or not new_value:
            raise ValueError(f"an edit of a field needs field_id (one of {', '.join(prepare.FIELDS)}) and a new value")
    if action == "edit":  # P-055: a manual-intake file is read by a person; nothing is filled in by an edit
        try:
            mi_run = prepare.read_saved_run((payload.get("submission") or "").strip())
        except ValueError:
            mi_run = {}
        if mi_run.get("status") == prepare.MANUAL_INTAKE:
            raise ValueError(f"this file's status is {prepare.status_refusal(mi_run)}; an edit is refused for it")
    if action == "confirm":  # T-027 C1: a per-value confirmation, never an approve and never sendable
        submission = (payload.get("submission") or "").strip()
        saved = prepare.read_saved_run(submission)
        if saved["status"] in prepare.REFUSED_STATUSES:
            raise ValueError(f"this file's status is {prepare.status_refusal(saved)}; no confirmation is recorded for it")
        shown = (payload.get("run_hash") or "").strip()
        if shown and shown != saved["saved_hash"]:
            raise ValueError("the saved run changed since this card was opened; reload the page and review again")
        listed = [r["field_id"] for r in saved["fields"] if (r.get("value") or "").strip()]
        unacked = [f for f in listed if f not in (payload.get("ack") or [])]
        if unacked:
            raise ValueError(f"confirm every value before recording: {', '.join(unacked)}")
        if not listed:
            raise ValueError("there is no value to confirm on this run")
        payload = {**payload, "acknowledged": listed, "confirmed_values": field_values(saved), "run_hash": saved["saved_hash"]}
    if action == "approve":
        submission = (payload.get("submission") or "").strip()
        # T-071: read the file's status from the last saved run itself. An approve is refused on either
        # refused status, and when nothing is saved or the run cannot be read (current_status raises).
        saved = prepare.read_saved_run(submission)
        status = saved["status"]
        if status in prepare.REFUSED_STATUSES:
            raise ValueError(f"this file's status is {prepare.status_refusal(saved)}; an approve is refused for it")
        # D-039: every value flagged needs-review is listed at approve; each must be acknowledged, and is logged.
        shown = (payload.get("run_hash") or "").strip()  # the run the card showed; the log stores the run read now (P-026)
        if shown and shown != saved["saved_hash"]:
            raise ValueError("the saved run changed since this card was opened; reload the page and review again")
        listed = needs_review_ids(saved)
        unacked = [f for f in listed if f not in (payload.get("ack") or [])]
        if unacked:
            raise ValueError(f"acknowledge every needs-review value before approving: {', '.join(unacked)}")
        payload = {**payload, "acknowledged": listed, "run_hash": saved["saved_hash"], "approved_values": field_values(saved)}  # B-266: what was approved
    with _LOG_LOCK:
        if action == "approve" and not reason:
            # D-053: an approve after a decline needs a written reason; refused here, not only at the send.
            if any(r.get("action") == "decline" for r in package.decisions(submission, log_path)):
                raise ValueError("an approve after a decline needs a written reason")
        return _append({**payload, "run_record": run_record((payload.get("submission") or "").strip())}, action, actor, reason, log_path)


needs_review_ids = package.needs_review_ids  # D-068: one list, shared with the send gate


def _append(payload: dict, action: str, actor: str, reason: str, log_path: Path) -> dict:
    """D-055: every entry gets the next sequence number in the log; the highest seq is the latest decision."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = log_path.with_suffix(log_path.suffix + ".lock")
    with lock_path.open("a+") as lfh:
        fcntl.flock(lfh, fcntl.LOCK_EX)  # B-191 item 2: a lock failure is an error, never a silent append
        last = 0
        if log_path.exists():
            for line in log_path.read_text().splitlines():
                try:
                    seq = json.loads(line).get("seq")
                except (ValueError, AttributeError):
                    continue
                if isinstance(seq, int) and not isinstance(seq, bool):
                    last = max(last, seq)
        row = {
            "seq": last + 1,
            "submission": payload.get("submission"),
            "action": action,
            "underwriter_id": actor,
            "reason": reason,
            **({"run_hash": payload["run_hash"]} if action in ("approve", "resolve", "confirm") else {}),
            **({"conflict_field": payload["conflict_field"], "new_value": payload["new_value"]} if action == "resolve" else {}),
            **payload["run_record"],
            **({"approved_values": payload["approved_values"]} if action == "approve" else {}),
            **({"confirmed_values": payload["confirmed_values"]} if action == "confirm" else {}),
            **({"acknowledged": payload["acknowledged"]} if payload.get("acknowledged") else {}),
            **({"field_id": payload["field_id"].strip(), "new_value": payload["new_value"].strip()} if (payload.get("field_id") or "").strip() else {}),
            "date": date.today().isoformat(),
            "at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "ai_version": ai_version(),
            "bound": False,
            "sent_to_carrier": False,
        }
        try:
            with log_path.open("a") as handle:
                handle.write(json.dumps(row) + "\n")
                handle.flush()
                os.fsync(handle.fileno())  # B-191 item 2: a failed flush is an error, never a silent success
        finally:
            fcntl.flock(lfh, fcntl.LOCK_UN)
    return row


REFUSED_AS = {"/confirm-market": "Market confirm refused", "/decision": "Decision refused", "/mark-code": "Mark refused", "/cooking-call": "Cooking call refused", "/close-subjectivity": "Not closed", "/send": "Send refused", "/approve-draft": "Request not approved"}


def reviewed_values(submission: str) -> dict:
    """The values the underwriter stands behind: the saved run with the logged edits and resolutions."""
    try:
        run = package.reviewed(submission)
    except (ValueError, OSError):
        return {}
    return {r["field_id"]: r.get("value") for r in run.get("fields") or []}


def _pilot_correction(path: str, payload: dict, row: dict) -> None:
    """T-027 C5: capture field, suggested value, final value and reason for every correction."""
    if not pilot.active():
        return
    sub = (payload.get("submission") or "").strip()
    actor = str(row.get("underwriter_id") or payload.get("underwriter_id") or "")
    run_hash = str(row.get("run_hash") or "")
    if path == "/decision":
        action = row.get("action")
        if action == "confirm":
            # Every per-value confirmation, edited or not, is one row: the pilot measures a
            # correction rate per field, and the rate needs every confirmation as its denominator.
            suggested_values = row.get("confirmed_values") or {}
            effective = reviewed_values(sub)
            for field in row.get("acknowledged") or []:
                suggested = suggested_values.get(field, "")
                final = effective.get(field, suggested)
                pilot.record_correction(submission=sub, field=field, kind="confirm",
                                        suggested=str(suggested or ""), final=str(final or ""),
                                        reason=str(payload.get("reason") or "checked against the cited text"),
                                        actor=actor, run_hash=run_hash)
        if action in {"edit", "resolve", "decline"}:
            field = (payload.get("conflict_field") if action == "resolve" else payload.get("field_id")) or "file"
            suggested = ""
            try:
                saved = prepare.read_saved_run(sub)
                if action == "decline":
                    suggested = f"status {saved.get('status')}"
                elif action == "resolve":
                    for c in saved.get("conflicts") or []:
                        if c.get("field") == field:
                            suggested = json.dumps(c.get("values") or [])
                else:
                    suggested = field_values(saved).get(field, "")
            except (ValueError, OSError):
                suggested = ""
            pilot.record_correction(submission=sub, field=field, kind=action,
                                    suggested=str(suggested), final=str(payload.get("new_value") or action),
                                    reason=str(payload.get("reason") or ""), actor=actor, run_hash=run_hash)
    elif path == "/mark-code":
        pilot.record_correction(submission=sub, field=str(payload.get("code") or ""), kind="code",
                                suggested="shown in the score", final="marked wrong",
                                reason=str(payload.get("reason") or ""), actor=actor, run_hash="")


def _pilot_event(path: str, payload: dict, sub: str, outcome: str, message: str) -> str:
    """Log one action or refusal. Returns a note to show when the log itself failed."""
    if not pilot.active():
        return ""
    try:
        pilot.record_event(action=path.removeprefix("/"), submission=sub,
                           actor=str(payload.get("underwriter_id") or ""), outcome=outcome, message=message)
    except OSError as exc:
        return f" Pilot log failed: {exc}."
    return ""


def act(path: str, payload: dict) -> tuple[str, bool, str]:
    """D-066 items 2/4/8: run one POST action. Returns (submission, ok, plain-words message); a refusal never raises."""
    sub = (payload.get("submission") or "").strip()

    def done(message: str, row: dict | None = None) -> tuple[str, bool, str]:
        note = ""
        try:
            if row is not None:
                _pilot_correction(path, payload, row)
        except OSError as exc:
            note += f" Pilot correction log failed: {exc}."
        note += _pilot_event(path, payload, sub, "ok", message)
        return sub, True, message + note

    try:
        if path in ("/send", "/approve-draft") and not re.fullmatch(r"SUB-\d+", sub):
            raise ValueError("no such submission id on the form")
        if path == "/decision":
            row = record_decision(payload, LOG)
            return done(f"Decision recorded: {row['action']} by {row['underwriter_id']}.", row)
        if path == "/confirm-market":  # P-052 (D-098)
            row = package.confirm_market(sub, payload.get("underwriter_id", ""), payload.get("carrier", ""), payload.get("reason", ""), payload.get("run_hash", ""))
            return done(f"Market confirmed: {row['carrier']} by {row['underwriter_id']} {row['underwriter_name']}. Not sent: approve on this run and type the send line.", row)
        if path == "/mark-code":
            row = mark_code(payload)
            return done(f"Marked {row['code']} wrong by {row['underwriter_id']}. The number does not change.", row)
        if path == "/cooking-call":
            row = cooking_call(payload)
            return done(f"Cooking recorded {row['call']} by {row['underwriter_id']} for this run. Points now apply.", row)
        if path == "/close-subjectivity":
            quotes.close_subjectivity(*(payload.get(k, "") for k in ("submission", "carrier", "subjectivity", "underwriter_id", "reason")))
            return done("Subjectivity closed and logged.")
        if path == "/send":  # item 1: the same gate as every send; the actor is the user, the line is typed on the card
            dest = package.send_to_carrier(sub, payload.get("underwriter_id") or "user", TO_CARRIER, user_line=payload.get("user_line", ""), resend_reason=payload.get("resend_reason", ""))
            return done(f"Sent: package {dest.name} written to to-carrier. Not bound.")
        dest = prepare.approve(PENDING / f"{sub}.md", payload.get("underwriter_id") or "user", TO_PRODUCER, payload.get("reason", ""))  # item 13: D-050, user override
        return done(f"Approved: request {dest.name} written to to-producer. It lists only missing items and declines nothing.")
    except (ValueError, OSError) as exc:
        message = f"{REFUSED_AS.get(path, 'Refused')}: {exc}"
        message += _pilot_event(path, payload, sub, "refused", message)
        return sub, False, message


def _confidence(row: dict) -> str:
    used = row.get("confidence", "")
    model = row.get("model_confidence")
    if model is None or model == used:
        return str(used)
    return f"{used} ocr / {model} model"


def _folded(cards: list[str]) -> str:
    """B-231: every card with no usable saved run, in one closed section with a count and how a run is created."""
    if not cards:
        return ""
    return (
        f"<details{' open' if 'role=\"alert\"' in ''.join(cards) else ''}><summary><b>No saved run ({len(cards)})</b></summary>"
        "<p>These files have no usable saved extraction run, so the workbench shows nothing for them and offers no decision or send. "
        "A run is created outside this page: the AI Engineer (or @ai-engineer-assistant for the team) runs "
        "<code>python underwriting_pipeline/ai/prepare.py simulation/inbox simulation/pending-approval deliverables/data-engineer/conflicts</code> "
        "with the model host set. Reload the page afterwards. This page never runs extraction.</p>"
        + "".join(cards) + "</details>"
    )


def _msg(messages: dict, key: str) -> str:
    if key not in messages:
        return ""
    ok, text = messages[key]
    return f'<p class="msg {"ok" if ok else "bad"}" role="alert">{html.escape(text)}</p>'


def _msg_key(user: auth.User | None, key: str) -> str:
    return f"{user.id}|{key}" if user is not None else key


def _msg_for(messages: dict, user: auth.User | None, key: str) -> str:
    return _msg(messages, _msg_key(user, key)) or _msg(messages, key)


def side_note(v: dict) -> str:
    """P-074 (D-132): why a conflict side cannot be trusted as written. Plain words, escaped."""
    if v.get("unverified"):
        return html.escape(f"Not verified against the document: {v.get('reason') or 'the cited text was not found'}. Check it on the page before you choose it.")
    if v.get("approximate"):
        return html.escape(f"Approximate figure: '{v.get('quote') or v.get('value')}'. It does not confirm an exact amount.")
    return ""


def resolve_form(sub: str, report: dict, conflict: dict, user: auth.User | None = None) -> str:
    """B-324 (D-089): choose one stored side or enter the value; logged with this run's hash. Then approve.
    P-070 (D-122): the topic is named in plain words ("Resolve square footage")."""
    field = conflict.get("field") or ""
    plain = prepare.PLAIN.get(field, field)
    sides = "".join(f'<option value="{html.escape(str(v.get("value")))}">{html.escape(str(v.get("value")))} ({html.escape(v.get("source") or "file not named")})'
                    f'{" - not verified" if v.get("unverified") else " - approximate" if v.get("approximate") else ""}</option>'
                    for v in conflict.get("values") or [] if v.get("value"))
    notes = "".join(f'<p class="bad">{html.escape(str(v.get("value")))} ({html.escape(v.get("source") or "file not named")}): {side_note(v)}</p>'
                    for v in conflict.get("values") or [] if v.get("value") and side_note(v))
    actor = ('<label>Underwriter id <input name="underwriter_id" required></label> ' if user is None else
             f'<input type="hidden" name="csrf" value="{html.escape(auth.csrf_for(user))}"><span class="actor">Signed in as {html.escape(user.name)} ({html.escape(user.id)})</span> ')
    return (f'{notes}<form method="post" action="/decision"><input type="hidden" name="action" value="resolve">'
            f'<input type="hidden" name="submission" value="{html.escape(sub)}"><input type="hidden" name="run_hash" value="{html.escape(report.get("saved_hash") or "")}">'
            f'<input type="hidden" name="conflict_field" value="{html.escape(field)}">'
            f'<b>Resolve {html.escape(plain)}</b> <label>Choose <select name="chosen_value"><option value="">—</option>{sides}</select></label> '
            f'<label>or enter <input name="entered_value"></label> {actor}'
            f'<label>Reason <input name="reason"></label> <button type="submit">Record resolution</button> '
            "<small>Logged with this run. Resolve each open conflict, then approve.</small></form>")


def review_pending_html(report: dict) -> str:
    """P-041 (D-088): say what keeps a file with every field from being complete."""
    if report.get("status") != prepare.REVIEW_PENDING:
        return ""
    review = [r["field_id"] for r in report.get("fields") or [] if r.get("value") and r.get("needs_review")]
    open_ = [prepare.PLAIN.get(c.get("field") or "?", c.get("field") or "?") for c in report.get("conflicts") or [] if c.get("resolution") != "resolved"]  # P-070: plain words
    what = "; ".join(x for x in (review and "values to review: " + ", ".join(review), open_ and "open conflict: " + ", ".join(open_)) if x)
    return f'<p class="bad">Complete — review pending: {html.escape(what or "see the review notes")}. Not complete until checked.</p>'


def _carrier(item: dict, report: dict) -> str:
    """P-052: the route, or on a senior referral the carrier a senior confirmed on this run (and still confirmable)."""
    if item["route"] != "senior_referral":
        return item["route"]
    try:
        if package.confirm_problem(package.reviewed(item["id"])):
            return item["route"]
    except ValueError:
        return item["route"]  # confirm_html shows the reason; the card still renders
    c = package.market_confirmation(item["id"], report.get("saved_hash") or "")
    return c["carrier"] if c else item["route"]


def confirm_html(item: dict, report: dict, user: auth.User | None = None) -> str:
    """P-052 (D-098): who confirmed the market and why, or the senior confirm form, or why there is none."""
    sid = html.escape(item["id"])
    try:
        problem = package.confirm_problem(package.reviewed(item["id"]))
    except ValueError as exc:
        problem = str(exc)
    if problem:
        return f'<p class="bad">No market confirm and no send from this screen: {html.escape(problem)}.</p>'
    c = package.market_confirmation(item["id"], report.get("saved_hash") or "")
    if c:
        return (f'<p class="msg ok">Market confirmed: <b>{html.escape(c["carrier"])}</b> by {html.escape(c["underwriter_id"])} {html.escape(c.get("underwriter_name", ""))} (senior) '
                f'on {html.escape(c.get("at", "")[:10])}, run {html.escape(_short(c["run_hash"]))}. Reason: {html.escape(c["reason"])}. '
                "The send below still needs an approve on this run and the typed line.</p>")
    seniors = package.seniors()
    opts = "".join(f'<option value="{html.escape(i)}">{html.escape(i)} {html.escape(n)}</option>' for i, n in sorted(seniors.items()))
    if user is not None and not user.senior:
        return f'<p class="bad">No market confirm: {html.escape(user.name)} ({html.escape(user.id)}) is not a senior underwriter.</p>'
    excluded = package.excluded_carriers(package.reviewed(item["id"]))
    carriers = "".join(f'<option{" selected" if c == item.get("suggested") else ""}>{c}</option>' for c in sorted(package.CARRIERS - set(excluded)))
    why = ("".join(f'<p class="bad">Not offered: {html.escape(c)}. A note on the file excludes it ({html.escape(w)}). '
                   "Pick another market, or fix the note at source and re-run the file.</p>" for c, w in sorted(excluded.items())))  # @compliance M1 (D-099), P-054 (c)
    return (
        '<form method="post" action="/confirm-market"><fieldset><legend>Confirm the market (senior underwriter only)</legend>' + why +
        f'<input type="hidden" name="submission" value="{sid}"><input type="hidden" name="run_hash" value="{html.escape(report.get("saved_hash") or "")}">'
        + (f'<input type="hidden" name="csrf" value="{html.escape(auth.csrf_for(user))}"><span class="actor">Signed in as {html.escape(user.name)} ({html.escape(user.id)}, senior)</span> ' if user is not None else
           f'<label>Senior underwriter <select name="underwriter_id" required><option value="">choose</option>{opts}</select></label> ')
        + f'<label>Carrier <select name="carrier">{carriers}</select></label> '
        '<label>Reason (required) <input name="reason" size="40" required></label> '
        '<button type="submit">Confirm market</button>'
        "<p>Logged with this run. It sends nothing: the send still needs an approve on this run and the typed line. A new run needs a new confirm.</p>"
        "</fieldset></form>"
    )


def _no_send_reason(item: dict, report: dict, refused: bool) -> str:
    """B-232: plain words for why this card has no send form; empty when a send can be offered."""
    if refused:
        return f"this file's status is {prepare.status_refusal(report)}; it cannot be sent"
    if item.get("manifest"):
        return f"documents changed since extraction ({item['manifest']})"
    if item.get("scope_now"):  # P-063 (B-432): independent of status
        return item["scope_now"]
    if report.get("status") == prepare.REVIEW_PENDING and package.conflict_problem(report):  # B-324 (D-089)
        return package.conflict_problem(report)
    if item["route"] == "senior_referral" and _carrier(item, report) not in package.CARRIERS:  # P-052; T-107c: one text with the send gate
        return package.senior_confirm_problem(item["id"], report) or "a senior referral needs a senior underwriter to confirm the market first"
    if _carrier(item, report) not in package.CARRIERS:
        return f"the carrier match is {item['route']}" + (f" ({item['note']})" if item.get("note") else "") + ", so no carrier is named"
    if not prepare.ready_to_route(report):
        if report.get("status") == prepare.REVIEW_PENDING:
            return "an open conflict is still on the file"
        why = "the file is incomplete (a required field is empty)"
        open_ = [prepare.PLAIN.get(c.get("field") or "?", c.get("field") or "?") for c in report.get("conflicts") or [] if c.get("resolution") != "resolved"]  # P-070: the topic in plain words
        if open_:  # D-065 item 2: the block says what is open, not only that something is
            why += " and there is an open conflict on " + ", ".join(open_)
        return why
    return ""


def _send_html(item: dict, report: dict, refused: bool, manifest: str, user: auth.User | None = None) -> str:
    """The send panel plus, T-107c (D-112), the account-manager check result in plain words (the same check send_to_carrier runs)."""
    if pilot.active():
        return _send_panel(item, report, refused, manifest)
    try:
        am = package.agency_problem(item["id"])
    except Exception as exc:  # the card must still render
        am = str(exc)
    line = ('<p class="msg ok">Account-manager check: passes (complete file, no open conflict, no unread page' + (", senior-confirmed carrier" if item["route"] == "senior_referral" else "") + "). The account manager still writes a reason to send.</p>"
            if not am else f'<p class="bad">Account-manager check: refused, {html.escape(am)}.</p>')
    if not am and _no_send_reason(item, report, refused):
        line = ""  # the send panel already gives the reason; do not say "passes" beside it
    return _send_panel(item, report, refused, manifest, user) + line


def _send_panel(item: dict, report: dict, refused: bool, manifest: str, user: auth.User | None = None) -> str:
    sid = html.escape(item["id"])
    if pilot.active():
        return f'<h3>Send to carrier</h3><p class="bad">No send: assist-only pilot — send disabled for {sid}.</p>'
    why = _no_send_reason(item, report, refused)
    if why:
        return f'<h3>Send to carrier</h3><p class="bad">No send: {html.escape(why)}.</p>'
    problem = package._decision_problem(item["id"], report.get("saved_hash") or "")
    if problem == package.STALE:  # P-026 (D-069)
        return f'<h3>Send to carrier</h3><p class="bad">{package.STALE}. No send form until you approve again and tick each needs-review value.</p>'
    if problem:  # B-249 (D-068): no form before an approve is logged
        return f'<h3>Send to carrier</h3><p class="bad">Approve first. No send form until an approve is logged ({html.escape(problem)}).</p>'
    unack = package.ack_problem(item["id"], report)  # B-244 (D-068)
    if unack:
        return f'<h3>Send to carrier</h3><p class="bad">Send refused: {html.escape(unack)}. Approve again and tick each one.</p>'
    carrier = _carrier(item, report)
    when, to = package.sent_info(item["id"], TO_CARRIER)
    files = package.sent_files(item["id"], TO_CARRIER)
    already = f'<p class="msg ok">Already sent {html.escape(package.sent_phrase(when))} to {html.escape(to)}. Package files sent: {html.escape(", ".join(f.name for f in files))}.</p>' if when else ""
    resend = (
        '<label>Resend reason (required for a second send) <input name="resend_reason" size="30"></label> ' if when else ""
    )
    csrf = f'<input type="hidden" name="csrf" value="{html.escape(auth.csrf_for(user))}">' if user is not None else ""
    return (
        f'<h3>Send to carrier</h3>{already}<form method="post" action="/send"><input type="hidden" name="submission" value="{sid}">{csrf}'
        f"<p>The package goes to <b>{html.escape(carrier)}</b>{' (market confirmed by a senior underwriter)' if carrier != item['route'] else ''}. Check the carrier name, then confirm.</p>"
        f'{resend}<label>Type <code>send to carrier {sid}</code> to confirm <input name="user_line" size="28" autocomplete="off"></label> '
        f'<button type="submit">{"Resend" if when else "Send"} to {html.escape(carrier)}</button></form>'
        "<p>Goes through the same send gate as every send: saved run, documents unchanged, an approve logged, no failed file. The underwriter decides; nothing is bound.</p>"
    )


def whats_new_items(rows) -> str:
    return "".join(f"<li>{html.escape(d)} · {html.escape(t)} · {html.escape(n)}: {html.escape(w)}</li>" for d, t, n, w in rows)


def _short(h: str) -> str:
    return (h or "")[:8]


def manual_intake_html(report: dict) -> str:
    """P-055 (D-105, D-065): the Manual intake card. Every matched reason, in plain words, and what the file does not get."""
    if report.get("status") != prepare.MANUAL_INTAKE:
        return ""
    reasons = prepare.scope.reasons_text(report.get("scope")) or ["Manual intake: outside the pilot scope"]
    return (
        '<div class="msg bad" role="alert"><b>Manual intake</b> — a person reads this whole file. Why:<ul>'
        + "".join(f"<li>{html.escape(r)}</li>" for r in reasons)
        + "</ul>No field is filled in, no carrier route is shown, no missing-info draft is made, and the send is refused: "
        f"{html.escape(prepare.status_refusal(report))}. (scope check {html.escape(str((report.get('scope') or {}).get('version') or 'not recorded'))})</div>"
    )


def history_html(sub: str, current: str, marks: list[dict] | None = None) -> str:
    """D-069 Session B: one per-file panel: decisions, acknowledgments, sends and resends. Who, why, when, run hash."""
    events = []
    try:
        for r in package.decisions(sub, LOG):
            what = r.get("action", "")
            if what == "edit" and r.get("field_id"):
                what += f" {r['field_id']} to {r.get('new_value', '')}"
            if r.get("acknowledged"):
                what += f"; acknowledged {len(r['acknowledged'])}: {', '.join(r['acknowledged'])}"
            events.append((r.get("at") or f"{r.get('date', '')}T00:00:00", 0, r.get("underwriter_id", ""), what, r.get("reason", ""), r.get("run_hash") if r.get("action") == "approve" else None, r.get("at") or r.get("date", "")))
    except ValueError as exc:
        return f"<h3>History</h3><p class=\"bad\">History unavailable: {html.escape(str(exc))}</p>"
    for m in marks or []:
        events.append((m.get("at") or "", 2, m.get("underwriter_id", ""), f"marked {m.get('code')} wrong", m.get("reason", ""), m.get("run_hash") or "", m.get("at") or m.get("date", "")))
    if package.SENDS_LOG.exists():
        for line in package.SENDS_LOG.read_text().splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if isinstance(r, dict) and r.get("submission") == sub:
                events.append((r.get("at") or f"{r.get('date', '')}T00:00:00", 1, r.get("actor", ""), ("resend " if r.get("resend") else "send ") + Path(r.get("package", "")).name, r.get("resend_reason") or r.get("reason", ""), r.get("run_hash", ""), r.get("at") or r.get("date") or "date not recorded"))
    if not events:
        return "<h3>History</h3><p>No decision or send logged for this file.</p>"
    rows = []
    for _k, _o, who, what, why, run, when in sorted(events, key=lambda e: e[:2]):
        if run is None:
            mark = "—"
        elif not run:
            mark = "no run hash recorded — does not count"
        else:
            mark = f"run {_short(run)} " + ("(current run)" if run == current else "— not the current run")
        rows.append(f"<tr><td>{html.escape(when)}</td><td>{html.escape(who)}</td><td>{html.escape(what)}</td><td>{html.escape(why or '—')}</td><td>{html.escape(mark)}</td></tr>")
    return f"<h3>History</h3><table class=\"history\"><tr><th>When</th><th>Who</th><th>What</th><th>Why</th><th>Saved run</th></tr>{''.join(rows)}</table><p>Current run: {html.escape(_short(current) or 'unknown')}</p>"


def footer_html(queue: list[dict] | None = None) -> str:
    """B-265 (D-070): the model and prompt version that produced each saved run, not the environment's. Per card if they differ."""
    runs = {(i["id"]): (i["report"].get("model_version") or "not recorded", str(i["report"].get("prompt_version") or "not recorded"))
            for i in queue or [] if i.get("report")}
    if not runs:
        return "<footer><p>Model and prompt version: no saved run on this page</p></footer>"
    keys = "".join(f"<li>{html.escape(i['id'])}: {html.escape((i['report'].get('cache_key') or 'not recorded (saved before P-028)')[:12])}</li>"
                   for i in queue or [] if i.get("report"))
    keys = f"<p>Extraction cache key of each saved run (short form; files, prompt, OCR settings, model, host, temperature):</p><ul>{keys}</ul>"  # P-028 (D-075)
    kinds = set(runs.values())
    if len(kinds) == 1:
        m, p = next(iter(kinds))
        return f"<footer><p>Model (saved run): {html.escape(m)} · Prompt version (saved run): {html.escape(p)}</p>{keys}</footer>"
    rows = "".join(f"<li>{html.escape(k)}: model {html.escape(m)} · prompt {html.escape(p)}</li>" for k, (m, p) in runs.items())
    return f"<footer><p>Model and prompt version of each saved run (they differ):</p><ul>{rows}</ul>{keys}</footer>"


def stale_changes(sub: str, report: dict) -> str:
    """B-266: the fields that changed between the latest approve and the current saved run, old to new."""
    try:
        last = [r for r in package.decisions(sub, LOG) if r.get("action") == "approve"][-1]
    except (ValueError, IndexError):
        return ""
    old = last.get("approved_values")
    if not isinstance(old, dict):
        return "<p>Which fields changed was not recorded for this earlier approval. Compare the table below.</p>"
    new = field_values(report)
    diff = [f"{k}: {old.get(k) or '—'} → {new.get(k) or '—'}" for k in dict.fromkeys([*old, *new]) if (old.get(k) or None) != (new.get(k) or None)]
    if not diff:
        return "<p>No field value differs; the run changed in another way (status, a source file or a cited quote).</p>"
    return "<p>Changed since your approval (old → new):</p><ul>" + "".join(f"<li>{html.escape(d)}</li>" for d in diff) + "</ul>"


def _plain_reason(text: str) -> str:
    """P-070 (D-122): the topic of a conflict is named in plain words on the card. The score model keeps its
    own wording (points.py is a model file and is not touched); the card names the topic for the underwriter."""
    out = text or ""
    for field, plain in prepare.PLAIN.items():
        out = out.replace(f"open conflict on {field}", f"open conflict on {plain}")
    return out


def score_html(item: dict, report: dict, user: auth.User | None = None) -> list[str]:
    """P-015: the score, or why there is none; the three lines; a mark-wrong control beside each code (W1). No add-a-code control (A1)."""
    sc, sid = item["score"], html.escape(item["id"])
    marks = item.get("marks") or []
    out = []
    if sc["scored"]:
        out.append(f"<p>Score: {sc['points']} · not a price</p>")
        if not sc["reason_codes"]:
            out.append("<p>Codes: none</p>")
    else:
        out.append(f"<p class=\"bad\">{html.escape(_plain_reason(sc['not_scored_reason']))}</p>")
    for code in sc["reason_codes"]:
        shown = "".join(f" <i>(marked wrong by {html.escape(m['underwriter_id'])}: {html.escape(m['reason'])})</i>" for m in marks if m.get("code") == code)
        out.append(
            f'<form method="post" action="/mark-code" class="mark"><b>{html.escape(code)}</b>{shown} '
            f'<input type="hidden" name="submission" value="{sid}"><input type="hidden" name="code" value="{html.escape(code)}">'
            + (f'<input type="hidden" name="csrf" value="{html.escape(auth.csrf_for(user))}"><span class="actor">{html.escape(user.name)}</span> ' if user is not None else
               '<label>Mark wrong: id <input name="underwriter_id" size="8" required></label> ')
            + '<label>reason <input name="reason" required></label> '
            '<button type="submit">Mark wrong</button> <small>logged; the number does not change</small></form>'
        )
    out += [f"<p>{html.escape(line)}</p>" for line in sc["lines"]]
    for conflict in report.get("conflicts") or []:  # P-075 (D-133): the cooking line above reads the application only; say where else cooking is stated
        if conflict.get("field") == "cooking" and conflict.get("resolution") != "resolved":
            sides = conflict.get("values") or [{}, {}]  # code review 5, UI check H1: the conflict's own sides, every document that states cooking
            first = sides[0]
            others = "; ".join(f'{html.escape(str(v.get("source") or "a document"))}: "{html.escape(str(v.get("quote") or "—"))}"' for v in sides[1:])
            out.append(f'<p class="bad">Cooking: {html.escape(str(first.get("source") or "a document"))} says "{html.escape(str(first.get("quote") or "—"))}", but cooking is stated in {others}. '
                       'The file is held until you choose.</p>')
    if pilot.active():
        out.append(f'<p class="banner">AI proposal — verify against the source. {html.escape(pilot.warning_text())}</p>')
    if sc.get("provisional"):  # B-278 (D-073): the underwriter records the call; points apply only after it
        out.append(
            f'<form method="post" action="/cooking-call" class="mark"><b>Record cooking for this run</b> '
            f'<input type="hidden" name="submission" value="{sid}"><input type="hidden" name="run_hash" value="{html.escape(report.get("saved_hash") or "")}">'
            '<label><input type="radio" name="call" value="present" required> present</label> <label><input type="radio" name="call" value="none"> none</label> '
            + (f'<input type="hidden" name="csrf" value="{html.escape(auth.csrf_for(user))}"><span class="actor">{html.escape(user.name)}</span> ' if user is not None else
               '<label>id <input name="underwriter_id" size="8" required></label> ')
            + '<label>reason <input name="reason" required></label> '
            '<button type="submit">Record cooking</button> <small>logged with the run hash; points apply only after this</small></form>'
        )
    return out


def scope_html(item: dict, report: dict) -> str:
    """T-027 C3: the scope verdict on every card, not only when it refuses something."""
    if not pilot.active():
        return ""
    if item.get("scope_now"):
        return (f'<p class="bad"><b>Scope check:</b> manual intake — {html.escape(item["scope_now"])}. '
                "No send, no draft, no route. Your decision is logged.</p>")
    version = (report.get("scope") or {}).get("version") or "not recorded"
    return f'<p><b>Scope check:</b> in pilot scope (scope {html.escape(str(version))}).</p>'


def pilot_summary_html(queue: list[dict] | None = None) -> str:
    """T-027 C5: the pilot monitor. Read-only counts, refusals, time per file and failed extractions."""
    if not pilot.active():
        return ""
    s = pilot.summary(queue)
    fields = "; ".join(f"{k}: {v}" for k, v in s["per_field"].items()) or "none yet"
    # every pilot field is listed, confirmed or not, so a field nobody checked is never hidden
    confirms = "; ".join(f"{f}: {s['per_field_confirmations'].get(f, 0)}" for f in prepare.FIELDS)
    rates = "; ".join(
        f"{f}: no confirmations yet" if not s["per_field_confirmations"].get(f, 0)
        else f"{f}: {s['correction_rate'][f]}% ({s['per_field_corrected'].get(f, 0)} of {s['per_field_confirmations'][f]} confirmed values corrected)"
        for f in prepare.FIELDS
    )
    minutes = "; ".join(f"{k}: {v // 60}m {v % 60}s" for k, v in s["duration_seconds"].items()) or "none yet"
    failed = ", ".join(s["extraction_failed"]) or "none"
    return (
        '<details open><summary><b>Pilot monitor</b> (read-only; nothing here changes a file)</summary>'
        f'<p>Corrections logged: {s["corrections"]} · confirmations logged: {s["confirmations"]} · overrides: {s["overrides"]} · refusals: {s["refusals"]}</p>'
        f'<p>Edits per field: {html.escape(fields)}</p>'
        f'<p>Confirmations per field: {html.escape(confirms)}</p>'
        f'<p>Correction rate per field (corrected ÷ confirmed): {html.escape(rates)}</p>'
        f'<p>Time per file: {html.escape(minutes)}</p>'
        f'<p>Extraction failed (never a value): {html.escape(failed)}</p>'
        '<p>Pilot logs: deliverables/software-engineer/pilot-corrections.jsonl and pilot-events.jsonl.</p></details>'
    )


PILOT_KIND_LABEL = {
    "confirm": "confirmed",
    "edit": "edited",
    "resolve": "conflict resolved",
    "decline": "declined",
    "code": "code marked",
    "override": "override",
}


def pilot_corrections_html(submission: str) -> str:
    """T-027 C5: one read-only row per correction or per-value confirmation on this file."""
    if not pilot.active():
        return ""
    rows = pilot.corrections_for(submission)
    if not rows:
        return "<h3>Corrections</h3><p>None logged on this file yet.</p>"
    body = "".join(
        f'<tr><td>{html.escape(r.get("at", ""))}</td><td>{html.escape(r.get("actor", ""))}</td>'
        f'<td>{html.escape(PILOT_KIND_LABEL.get(r.get("kind", ""), r.get("kind", "")))}</td>'
        f'<td>{html.escape(r.get("field", ""))}</td><td>{html.escape(r.get("suggested", ""))}</td>'
        f'<td>{html.escape(r.get("final", ""))}</td><td>{html.escape(r.get("reason", ""))}</td></tr>'
        for r in rows
    )
    note = ('<p>"AI said" is the AI\'s proposal; "Final" is the value the underwriter stands behind, '
            "with the logged edits applied. One row per checked value.</p>")
    return ("<h3>Corrections</h3>" + note + "<table><tr><th>When</th><th>Who</th><th>Kind</th><th>Field</th>"
            f"<th>AI said</th><th>Final</th><th>Reason</th></tr>{body}</table>")


def render(queue: list[dict], counts: dict | None = None, messages: dict | None = None, user: auth.User | None = None) -> str:
    counts = counts or {"approve": 0, "edit": 0, "decline": 0}
    messages = messages or {}
    corrections = counts["edit"] + counts["decline"]
    blocks, unsaved = [], []
    for item in queue:
        report = item["report"]
        if report is None:  # item 10: no saved run, or it cannot be read; nothing is extracted here
            unsaved.append(
                f'<article id="{html.escape(item["id"])}"><h2>{html.escape(item["id"])}</h2>{_msg_for(messages, user, item["id"])}'
                f'<p class="bad">No usable saved run: {html.escape(item.get("saved_problem") or "none found")}. '
                "This page shows saved runs only and does not run extraction. Run extraction, then reload. No decision or send is offered.</p></article>"
            )
            continue
        refused = report.get("status") in prepare.REFUSED_STATUSES
        field_rows = []
        failed = report.get("status") == "extraction_failed"  # D-079 (B-295): nothing was read; never "none stated"
        for row in report["fields"]:
            note = ""
            if failed:
                note = NOT_READ
            elif row.get("needs_review") and row.get("value"):
                note = "NEEDS REVIEW: " + (row.get("reason") or "flagged")
            elif row.get("reason") and not row.get("value"):
                note = row["reason"]
            merged_n = len([q for q in row.get("also_quoted") or [] if not (row.get("rule_copied") and (row.get("value") or "").endswith("; " + str(q.get("quote"))))])
            if row.get("rule_copied") and not failed:  # P-075 (D-133, code review 6): the copied line is named, and a real merge is still shown
                note = (note + "; " if note else "") + "the cooking line was copied by a rule from the application, not read by the model"
            if merged_n and not failed:  # P-036 (@senior-underwriter H2): a merged value never looks like a single read
                note = (note + "; " if note else "") + f"merged: {merged_n + 1} documents agree"
            field_rows.append(
                "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                    html.escape(row["field_id"]),
                    html.escape(NOT_READ if failed else (row["value"] or "—")),
                    html.escape(_confidence(row)),
                    html.escape(row.get("source") or "—"),
                    html.escape((row.get("quote") or item["snippets"].get(row["field_id"]) or "—")
                                + "".join(f" | also: {q['quote']} ({q.get('source') or 'file not named'})" for q in row.get("also_quoted") or [])),  # P-036 H1: each quote with its file
                    html.escape(note or "—"),
                )
            )
        conflicts = report["conflicts"] or []
        conflict_html = "<p>No stored conflict.</p>"
        if conflicts:
            conflict_html = "<ul>" + "".join(
                "<li>{}: <ul>{}</ul>{}</li>".format(
                    html.escape(str(prepare.PLAIN.get(item_c["field"], item_c["field"]))),  # P-070: the topic in plain words
                    "".join(  # T-118: each side in words (value, file, cited text), not a JSON blob
                        "<li><b>{}</b> ({}){}{}</li>".format(
                            html.escape(str(v.get("value"))), html.escape(str(v.get("source") or "file not named")),
                            "" if v.get("quote") == v.get("value") else " — cited: " + html.escape(str(v.get("quote") or "—")),  # UI check M: the quote is not repeated when it is the value
                            f' <span class="bad">{side_note(v)}</span>' if side_note(v) else "",  # P-074 (D-132)
                        )
                        for v in (item_c["values"] if isinstance(item_c["values"], list) else [])
                    ),
                    html.escape(f" · RESOLVED by {item_c['resolved_by']}: {item_c['resolved_value']}") if item_c.get("resolution") == "resolved" and item_c.get("resolved_by")
                    else ("" if item_c.get("resolution") == "resolved" else " · OPEN: no send until the underwriter chooses or enters the value"),
                )
                for item_c in conflicts
            ) + "</ul>" + ("" if refused else "".join(resolve_form(item["id"], report, item_c, user) for item_c in conflicts if item_c.get("resolution") != "resolved"))
        address_check = "—"
        for row in report["fields"]:
            if row["field_id"] == "premises_address":
                address_check = row.get("address_check") or "—"
        extraction = "ok"
        manual = report.get("status") == prepare.MANUAL_INTAKE
        if manual:
            extraction = "MANUAL INTAKE — the file was not read for values. No field was filled in. This is not a missing-data file. Sends are blocked."
        elif report.get("status") == "extraction_failed":
            extraction = f"FAILED — {report['error']}. No field was read. This is not a missing-data file. Sends are blocked."
        elif report.get("status") == "all_values_rejected":
            reason = report.get("status_reason") or "every value was rejected by the gate"
            extraction = f"REJECTED — {reason}. No field was accepted. This is not a missing-data file. Sends are blocked."
        unread = report.get("unread") or []
        failed = report.get("status") == "extraction_failed"
        none_ = NOT_READ if failed else MI_NOT_READ if manual else "none"  # D-080 (B-297): a failed card never says "none"; nor does a manual-intake card (T-104a UI H1)
        unread_html = f"<p>Not read: {none_}</p>" if not unread or manual else "<p>Not read:</p><ul>" + "".join(
            "<li>{}, {}: {}</li>".format(
                html.escape(u["file"]),
                "whole file" if u.get("page") is None else f"page {u['page']}",
                html.escape(u["reason"]),
            )
            for u in unread
        ) + "</ul>"
        manifest = item.get("manifest") or ""
        lines = [
            f"<h2>{html.escape(item['id'])}</h2>",
            _msg_for(messages, user, item["id"]),
            (f'<p class="msg bad" role="alert">{package.STALE}. Approve and tick each needs-review value again.</p>' + stale_changes(item["id"], report) if package._decision_problem(item["id"], report.get("saved_hash") or "") == package.STALE else ""),
            f"<p>Saved run: status {html.escape(str(report.get('status')))} · hash check: ok · manifest check: "
            + (f'<span class="bad">FAILED — {html.escape(manifest)}. A send will be refused.</span>' if manifest else "ok")
            + "</p>",
            review_pending_html(report),
            manual_intake_html(report),
            scope_html(item, report),
            (f'<p class="msg bad" role="alert"><b>Send blocked</b> — {html.escape(item["scope_now"])}. Nothing on this file can be sent. '
             "Do not chase the missing items. Next step: re-run extraction on this file; the scope check then makes it manual intake, "
             "and an underwriter reads the whole file by hand.</p>" if item.get("scope_now") and not refused else ""),  # P-063, T-109a UI check H1
            f"<p>Files: {html.escape(', '.join(item['files']) or 'none')}</p>",
            f"<p>Not read by extraction: {html.escape(none_ if manual else ', '.join(item['ignored']) or none_)}</p>",
        ]
        lines += score_html(item, report, user)
        if item.get("scope_now") and not refused:  # P-063 (T-109a UI check H1): no route or hold wording on an out-of-scope file
            lines.append("<p>Carrier match: none — out of pilot scope at send time (see the alert above)</p>")
        elif not refused:
            lines.append(f"<p>Carrier match: {html.escape(item['route'])}{html.escape(' · ' + item['note']) if item.get('note') else ''} · "
                         + ("Suggestion only — not a decision" if pilot.active() else "recommendation only") + "</p>")
            if item.get("provisional"):  # P-048 (c) (D-095): routing always runs; the send stays blocked until the hold clears
                pv = item["provisional"]
                lines.append(f"<p>Provisional route: <b>{html.escape(pv['provisional'] or 'none yet')}</b>{html.escape(' · ' + pv['provisional_note']) if pv['provisional_note'] else ''}"
                             f" ({html.escape(pv['provisional_label'])}) · No send until the hold clears</p>")
            if item["route"] == "senior_referral":  # B-264: only a senior referral names a market
                lines.append(f"<p>Suggested market: <b>{html.escape(item.get('suggested') or 'none')}</b> · recommendation only; the underwriter decides</p>")
                lines.append(confirm_html(item, report, user))
        lines += [
            f"<p>Extraction: {html.escape(extraction)}</p>",
            unread_html,
            f"<p>Needs human read: {html.escape(none_ if manual else ', '.join(report.get('needs_human') or []) or none_)}</p>",
            f"<p>Address check: {html.escape(address_check)}</p>",
            f"<p>Locations: {html.escape('; '.join(('primary ' if row.get('primary') else 'other ') + row['address'] for row in report['locations']) or 'one premises') if report.get('locations') is not None else 'not stored in the saved run'}</p>",
            "<h3>Extracted fields</h3>",
            "<p>Nothing filled in: a person reads the file.</p>" if manual else (
                ("<p class='banner'>AI proposal — verify against the source.</p>" if pilot.active() else "")
                + f"<table><tr><th>Field</th><th>{'Value (AI proposal — verify)' if pilot.active() else 'Value'}</th><th>Confidence</th><th>Source</th><th>Cited text</th><th>Review note</th></tr>{''.join(field_rows)}</table>"
            ),
            f"<h3>Conflicts</h3>{conflict_html}",
            quotes.html_for(item["id"], user),
        ]
        if not refused:
            missing = report["missing"] + report.get("extra", [])
            lines += ["<h3>Missing</h3>", f"<p>{html.escape(', '.join(missing) or 'none')}</p>"]
        # T-071: on a refused card there is no approve option. Edit and decline stay so a person decides.
        options = "<option>decline</option>" if manual else "<option>edit</option><option>decline</option>" if refused else (
            "<option>confirm</option><option>edit</option><option>decline</option>" if pilot.active()
            else "<option>approve</option><option>edit</option><option>decline</option>")
        acks = "".join(
            '<label><input type="checkbox" name="ack" value="{0}"> I checked {0}: {1} (cited: {2})</label><br>'.format(
                html.escape(row["field_id"]), html.escape(row["value"]), html.escape(row.get("quote") or "—")
            )
            for row in report["fields"]
            if row.get("value") and (pilot.active() or row.get("needs_review"))
        )
        cook = (report.get("cooking") or {}).get("equipment") or {}
        if cook.get("state") == "needs_review":  # P-029 (D-072): the same acknowledgment; no cooking points either way
            acks += '<label><input type="checkbox" name="ack" value="cooking_equipment"> I checked cooking equipment: needs review; points only after the cooking call (cited: {})</label><br>'.format(html.escape(cook.get("quote") or "—"))
        if acks and not refused:
            legend = "Confirm every value with its cited text" if pilot.active() else "Needs-review values: acknowledge each to approve"
            acks = f"<fieldset><legend>{legend}</legend>{acks}</fieldset>"
        else:
            acks = ""
        lines.append(
            f"""<form method="post" action="/decision">
<input type="hidden" name="submission" value="{html.escape(item['id'])}">
<input type="hidden" name="run_hash" value="{html.escape(report.get('saved_hash') or '')}">
{acks}
{f'<input type="hidden" name="csrf" value="{html.escape(auth.csrf_for(user))}"><span class="actor">Signed in as {html.escape(user.name)} ({html.escape(user.id)})</span>' if user is not None else '<label>Underwriter id <input name="underwriter_id" required></label>'}
<label>Action
<select name="action">{options}</select>
</label>
<label>Edited field <input name="field_id" placeholder="e.g. year_built"></label>
<label>New value <input name="new_value"></label>
<label>Reason <input name="reason"></label>
<button type="submit">{"Record confirmation" if pilot.active() and not refused and not manual else "Record decision"}</button>
</form>"""
        )
        sid = html.escape(item["id"])
        draft = PENDING / f"{item['id']}.md"
        if draft.is_file() and not manual:  # P-055: a manual-intake file has no automated missing-info draft
            lines.append(
                f"<h3>Missing-info draft for the producer (not sent)</h3><pre>{html.escape(draft.read_text())}</pre>"
                + (f'<p class="bad">No send to producer: {html.escape(item["scope_now"])}.</p>' if item.get("scope_now") else  # P-063
                   ('<p class="bad">No producer request: assist-only pilot — producer requests are disabled.</p>' if pilot.active() else
                    f'<form method="post" action="/approve-draft"><input type="hidden" name="submission" value="{sid}">'
                    + (f'<input type="hidden" name="csrf" value="{html.escape(auth.csrf_for(user))}">' if user is not None else "")
                    + '<label>Reason (optional) <input name="reason"></label> '
                    '<button type="submit">Approve and send to producer (user override)</button></form>'))
            )
        if (TO_PRODUCER / f"{item['id']}.md").is_file():
            lines.append("<p>Producer request on file in to-producer.</p>")
        lines.append(_send_html(item, report, refused, manifest, user))
        lines.append(history_html(item["id"], report.get("saved_hash") or "", item.get("marks") or []))
        lines.append(pilot_corrections_html(item["id"]))
        blocks.append(
            f'<article id="{html.escape(item["id"])}">\n' + "\n".join(lines) + "\n</article>"
        )
    ids = {q["id"] for q in queue}
    loose = "".join(_msg(messages, k) for k in messages if k not in ids and (user is None or k.startswith(f"{user.id}|") or "|" not in k))
    identity = (
        f'<p class="identity">Signed in as <b>{html.escape(user.name)}</b> ({html.escape(user.id)})'
        f'{" · senior underwriter" if user.senior else ""}'
        f'<form method="post" action="/logout"><input type="hidden" name="csrf" value="{html.escape(auth.csrf_for(user))}">'
        '<button type="submit">Sign out</button></form></p>'
        if user is not None else '<p class="identity">Not signed in. No decision or send is accepted.</p>'
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Underwriter workbench</title>
<style>
body {{ font: 15px/1.4 sans-serif; margin: 2rem; }}
article {{ border-top: 1px solid #ccc; padding: 1rem 0; }}
table {{ border-collapse: collapse; }}
td, th {{ border: 1px solid #ddd; padding: 0.3rem 0.5rem; text-align: left; }}
.msg {{ padding: 0.5rem 0.75rem; border-left: 4px solid; font-weight: 600; }}
.msg.ok {{ border-color: #1a7f37; background: #e9f7ee; }}
.msg.bad, .bad {{ border-color: #b42318; color: #b42318; }}
.msg.bad {{ background: #fdecea; }}
.banner {{ background: #fff3bf; border: 2px dashed #b08900; padding: 0.5rem 0.75rem; font-weight: 700; }}
form.mark {{ margin: 0.2rem 0; }}
pre {{ background: #f6f6f6; padding: 0.5rem; white-space: pre-wrap; }}
details {{ margin: 0.5rem 0; }}
footer {{ border-top: 1px solid #ccc; margin-top: 2rem; color: #555; }}
.identity {{ background: #eef3f8; border-left: 4px solid #1f4e79; padding: 0.5rem 0.75rem; }}
.identity form {{ display: inline; margin-left: 1rem; }}
.actor {{ color: #1f4e79; font-weight: 600; margin-right: 0.5rem; }}
</style></head><body>
{f'<p class="banner">{html.escape(BANNER)}</p>' if BANNER else ''}
<h1>Underwriter workbench</h1>
{identity}
{loose}
{'<p class="banner">ASSIST-ONLY PILOT — AI proposals only. Nothing is routed, sent or drafted. You decide.</p>' if pilot.active() else ''}
{pilot_summary_html(queue)}
<details open><summary><b>What's new</b> (latest {min(5, len(WHATS_NEW))} of {len(WHATS_NEW)})</summary><ul>{whats_new_items(WHATS_NEW[:5])}</ul>{f"<details><summary>Show all {len(WHATS_NEW)}</summary><ul>{whats_new_items(WHATS_NEW[5:])}</ul></details>" if len(WHATS_NEW) > 5 else ""}</details>
<p>Synthetic queue. A decision is logged only with an id on the underwriter list. Decline and edit need a reason, and so does an approve after a decline. Approve, edit, and decline are saved with that reason. This page shows saved runs only. It never binds. A carrier send needs the typed line and passes the send gate.</p>
<p>Decisions so far: {counts['approve']} approved, {counts['edit']} edited, {counts['decline']} declined. Corrections: {corrections}.</p>
{''.join(blocks)}
{_folded(unsaved)}
{footer_html(queue)}
</body></html>
"""


def sandbox(tmp: Path) -> None:
    """B-252 (D-069): copy the real inputs into tmp and point every path the page can write at the copy.

    Covers the page, the decision/sends/closure logs, the three outboxes, the saved runs, the inbox and the model cache
    (token log). Nothing real is written afterwards. Call before serve() or any test that posts an action."""
    global PAGE, LOG, INBOX, PENDING, TO_PRODUCER, TO_CARRIER, BANNER
    tmp = Path(tmp)
    if auth.audit_path().is_file():
        shutil.copy2(auth.audit_path(), tmp / "auth-audit.jsonl")
    if marks_path().is_file():
        shutil.copy2(marks_path(), tmp / "code_marks.jsonl")
    if calls_path().is_file():
        shutil.copy2(calls_path(), tmp / "cooking_calls.jsonl")
    for name, src in (("inbox", INBOX), ("extractions", prepare.EXTRACT_DIR), ("pending", PENDING), ("to-producer", TO_PRODUCER),
                      ("to-carrier", TO_CARRIER), ("from-carrier", quotes.FROM_CARRIER), ("cache", llm_extract.CACHE)):
        if src.is_dir() and name != "cache":  # the cache starts empty: a sandbox never reads or grows the real token log
            shutil.copytree(src, tmp / name, dirs_exist_ok=True)
        (tmp / name).mkdir(exist_ok=True)
    logs = {"market_confirms.jsonl": package.confirms_path(), "decisions.jsonl": package.DECISIONS_LOG, "sends.jsonl": package.SENDS_LOG, "closures.jsonl": quotes.CLOSURES}
    for name, src in logs.items():
        if src.is_file():
            shutil.copy2(src, tmp / name)
    PAGE, LOG, INBOX = tmp / "workbench.html", tmp / "decisions.jsonl", tmp / "inbox"
    PENDING, TO_PRODUCER, TO_CARRIER = tmp / "pending", tmp / "to-producer", tmp / "to-carrier"
    package.DECISIONS_LOG, package.SENDS_LOG, package.INBOX = LOG, tmp / "sends.jsonl", INBOX
    quotes.CLOSURES, quotes.TO_CARRIER, quotes.FROM_CARRIER = tmp / "closures.jsonl", TO_CARRIER, tmp / "from-carrier"
    prepare.EXTRACT_DIR, prepare.INBOX_DIR, llm_extract.CACHE = tmp / "extractions", INBOX, tmp / "cache"
    auth.AUDIT_LOG = tmp / "auth-audit.jsonl"
    pilot.CORRECTIONS, pilot.EVENTS = tmp / "pilot-corrections.jsonl", tmp / "pilot-events.jsonl"
    BANNER = f"SANDBOX COPY in {tmp}: nothing here is real; no real log, outbox or page is written"


def make_handler(only: str | None = None):
    """The HTTP handler, separate from serve() so tests can bind an ephemeral port. Every route needs sign-in."""
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: str, *, content_type: str = "text/html; charset=utf-8", headers: dict | None = None) -> None:
            raw = body.encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(raw)

        def _redirect(self, location: str, cookies: list[str] | None = None) -> None:
            self.send_response(303)
            self.send_header("Location", location)
            self.send_header("Cache-Control", "no-store")
            for cookie in cookies or []:
                self.send_header("Set-Cookie", cookie)
            self.end_headers()

        def _user(self) -> tuple[auth.User | None, str]:
            try:
                return auth.session_from_cookie(self.headers.get("Cookie")), ""
            except auth.AuthError as exc:
                return None, str(exc)

        def _config_or_page(self) -> auth.Config | None:
            try:
                return auth.config()
            except auth.AuthError as exc:
                self._send(503, auth.config_error_page(str(exc)))
                return None

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path == "/favicon.ico":
                self.send_error(404)
                return
            cfg = self._config_or_page()
            if cfg is None:
                return
            if path == "/login":
                query = {k: v[0] for k, v in parse_qs(self.path.split("?", 1)[1] if "?" in self.path else "").items()}
                try:
                    target, cookie = auth.sign_in_url(query.get("next") or "/")
                except auth.AuthError as exc:
                    self._send(502, auth.sign_in_page(f"Sign-in could not start: {exc}"), headers={"Set-Cookie": auth.clear_cookie(auth.STATE_COOKIE)})
                    return
                self._redirect(target, [cookie])
                return
            if path == "/auth/callback":
                query = {k: v[0] for k, v in parse_qs(self.path.split("?", 1)[1] if "?" in self.path else "").items()}
                try:
                    user, session, next_path = auth.complete_sign_in(query, self.headers.get("Cookie"))
                    auth.audit(user, "login", outcome="ok", reason="OIDC sign-in")
                except (auth.AuthError, OSError) as exc:
                    self._send(403, auth.sign_in_page(f"Sign-in failed: {exc}"), headers={"Set-Cookie": auth.clear_cookie(auth.STATE_COOKIE)})
                    return
                self._redirect(next_path, [auth.clear_cookie(auth.STATE_COOKIE), auth.cookie_header(auth.SESSION_COOKIE, session, auth.SESSION_TTL, auth._secure(cfg))])
                return
            user, problem = self._user()
            if user is None:
                self._send(200, auth.sign_in_page(problem, self.path))
                return
            queue = load_queue(only)
            try:
                for item in queue:
                    report = item.get("report") or {}
                    auth.audit(user, "view", item["id"], run_hash=report.get("saved_hash") or "")
            except (OSError, auth.AuthError) as exc:
                self._send(503, auth.sign_in_page(f"Audit log unavailable: {exc}", self.path))
                return
            shown = {k: v for k, v in MESSAGES.items() if k.startswith(f"{user.id}|")}
            for key in list(shown):
                MESSAGES.pop(key, None)
            body = render(queue, correction_counts(LOG), shown, user)
            try:  # T-027 C5 display log: one row per file shown, with the run hash and model. B-190 supplies the user.
                for item in queue:
                    report = item.get("report")
                    if not report:
                        continue
                    pilot.record_event(action="view", submission=item["id"], actor=user.id, outcome="view",
                                       message=f"prompt={report.get('prompt_version') or 'not recorded'} "
                                               f"model={report.get('model_version') or 'not recorded'}",
                                       run_hash=str(report.get("saved_hash") or ""))
            except OSError as exc:
                body = body.replace("<body>", f'<body><p class="bad">Pilot view log failed: {html.escape(str(exc))}</p>', 1)
            self._send(200, body)

        def do_POST(self):
            path = self.path.split("?", 1)[0]
            cfg = self._config_or_page()
            if cfg is None:
                return
            user, _ = self._user()
            if path == "/logout":
                if user is None:
                    self._send(401, auth.sign_in_page("Sign-in required: sign out was not recorded."))
                    return
                try:
                    auth.check_origin(self.headers.get("Origin"), self.headers.get("Host"))
                    size = int(self.headers.get("Content-Length", "0") or 0)
                    if size > auth.MAX_FORM_BYTES:
                        raise auth.AuthError("the form is too large")
                    form = parse_qs(self.rfile.read(size).decode())
                    auth.check_csrf(user, (form.get("csrf") or [""])[0])
                    auth.audit(user, "logout", outcome="ok", reason="signed out")
                except (auth.AuthError, ValueError, OSError) as exc:
                    self._send(403, auth.sign_in_page(f"Sign out refused: {exc}"))
                    return
                self._redirect("/", [auth.clear_cookie(auth.SESSION_COOKIE)])
                return
            label = REFUSED_AS.get(path)
            if label is None:
                self.send_error(404)
                return
            if user is None:
                self._send(401, auth.sign_in_page(f"Sign-in required: {label.lower()} was not recorded."))
                return
            try:
                auth.check_origin(self.headers.get("Origin"), self.headers.get("Host"))
                size = int(self.headers.get("Content-Length", "0") or 0)
                if size > auth.MAX_FORM_BYTES:
                    raise auth.AuthError("the form is too large")
                form = parse_qs(self.rfile.read(size).decode())
                payload = {k: v[0] for k, v in form.items()}
                payload["ack"] = form.get("ack", [])
                auth.check_csrf(user, payload.get("csrf", ""))
                payload.pop("csrf", None)
                posted_actor = (payload.pop("underwriter_id", "") or "").strip()
                if posted_actor and posted_actor != user.id:
                    payload["_posted_actor_ignored"] = posted_actor
                payload["underwriter_id"] = user.id
                sub, ok, text = act(path, payload)
                outcome, reason = ("ok" if ok else "refused"), text
                try:
                    auth.audit(user, path.strip("/"), sub, outcome=outcome, reason=reason)
                except OSError as exc:
                    text, ok = f"Audit log failed after the action: {exc}. Check the decision log before relying on this screen.", False
            except (auth.AuthError, ValueError, OSError) as exc:
                self._send(403, auth.sign_in_page(f"{label}: {exc}"))
                return
            MESSAGES[f"{user.id}|{sub}"] = (ok, text)
            self._redirect("/" + (f"#{sub}" if sub else ""))

    return Handler


def serve(port: int = 8765, only: str | None = None, sandbox_dir: Path | None = None) -> None:
    if sandbox_dir is not None:
        sandbox(sandbox_dir)
    try:
        auth.config()
        PAGE.write_text(auth.sign_in_page("", "/"))
    except auth.AuthError as exc:
        PAGE.write_text(auth.config_error_page(str(exc)))
    ThreadingHTTPServer(("127.0.0.1", port), make_handler(only)).serve_forever()


if __name__ == "__main__":
    if "--serve" in sys.argv:
        chosen = next((arg for arg in sys.argv if arg.startswith("SUB-")), None)
        box = None  # --sandbox [DIR]: every write goes to a temporary copy (B-252)
        if "--sandbox" in sys.argv:
            after = sys.argv[sys.argv.index("--sandbox") + 1 :][:1]
            box = Path(after[0]) if after and not after[0].startswith(("-", "SUB-")) else Path(tempfile.mkdtemp(prefix="workbench-sandbox-"))
            print(f"sandbox: {box}", flush=True)
        serve(only=chosen, sandbox_dir=box)
    else:
        def save(ext: Path, submission: str, status: str, fields=None) -> None:
            """A saved run shaped like prepare.write_drafts() writes, no model call. The hash is the reader's."""
            payload = {
                "submission": submission,
                "status": status,
                "error": "model call failed: HTTP 429 rate limit" if status == "extraction_failed" else None,
                "complete": status == "complete",
                "conflicts": [],
                "needs_human": [],
                "sprinklers": None,
                "fields": fields or [],
            }
            payload["hash_algorithm"] = prepare.HASH_ALGORITHM
            payload["saved_hash"] = prepare.hash_payload(payload)
            ext.mkdir(parents=True, exist_ok=True)
            (ext / f"{submission}.json").write_text(json.dumps(payload))

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            check = tmp / "decisions.jsonl"
            ext = tmp / "extractions"
            saved_dir = prepare.EXTRACT_DIR
            prepare.EXTRACT_DIR = ext
            try:
                try:
                    record_decision({"action": "decline"}, check)
                    raise SystemExit("missing id should fail")
                except ValueError:
                    pass
                try:
                    record_decision(
                        {"underwriter_id": "UW-001", "action": "decline", "submission": "SUB-000"},
                        check,
                    )
                    raise SystemExit("decline without reason should fail")
                except ValueError:
                    pass

                # T-071 (4): an approve with nothing saved is refused.
                try:
                    record_decision(
                        {"underwriter_id": "UW-001", "action": "approve", "submission": "SUB-000", "reason": "self-check"},
                        check,
                    )
                    raise SystemExit("an approve with no saved run should fail")
                except ValueError:
                    pass

                # A normal file: the approve is recorded.
                save(ext, "SUB-000", "complete")
                record_decision(
                    {
                        "underwriter_id": "UW-001",
                        "action": "approve",
                        "submission": "SUB-000",
                        "reason": "self-check",
                    },
                    check,
                )
                logged = json.loads(check.read_text().splitlines()[-1])

                # D-039: needs-review values must each be acknowledged at approve; the log names them.
                nr = lambda extra: {"field_id": "year_built", "value": "1942", "needs_review": True, "quote": "Built 1942", "reason": "number or date read from a scan", **extra}
                save(ext, "SUB-020", "complete", [nr({}), {"field_id": "operations", "value": "office", "needs_review": False}, {"field_id": "roof", "value": None, "needs_review": True}])
                ap = {"underwriter_id": "UW-001", "action": "approve", "submission": "SUB-020", "reason": "checked"}
                for ack in (None, []):
                    try:
                        record_decision({**ap, "ack": ack}, check)
                        raise SystemExit("an approve without the acknowledgment should fail")
                    except ValueError:
                        pass
                n = len(check.read_text().splitlines())
                assert record_decision({**ap, "ack": ["year_built"]}, check)["acknowledged"] == ["year_built"]
                assert len(check.read_text().splitlines()) == n + 1
                assert "acknowledged" not in logged  # a report with no needs-review value approves as before

                # T-071 (4): an approve is refused on either refused status; edit and decline are still recorded.
                for sub, status in (("SUB-010", "extraction_failed"), ("SUB-011", "all_values_rejected")):
                    save(ext, sub, status)
                    try:
                        record_decision(
                            {"underwriter_id": "UW-001", "action": "approve", "submission": sub, "reason": "self-check"},
                            check,
                        )
                        raise SystemExit(f"an approve on {status} should fail")
                    except ValueError:
                        pass
                    record_decision(
                        {"underwriter_id": "UW-001", "action": "edit", "submission": sub, "reason": "corrected by hand"},
                        check,
                    )
                    record_decision(
                        {"underwriter_id": "UW-001", "action": "decline", "submission": sub, "reason": "not bindable as read"},
                        check,
                    )
                record_decision(
                    {"underwriter_id": "UW-001", "action": "edit", "submission": "SUB-000", "reason": "square feet were 4500"},
                    check,
                )
                assert correction_counts(check) == {"approve": 2, "edit": 3, "decline": 2}, correction_counts(check)
                save(ext, "SUB-013", prepare.MANUAL_INTAKE)  # P-055: an approve is refused on a manual-intake file, with its reason
                try:
                    record_decision({"underwriter_id": "UW-001", "action": "approve", "submission": "SUB-013", "reason": "self-check"}, check)
                    raise SystemExit("an approve on manual_intake should fail")
                except ValueError as exc:
                    assert "manual intake" in str(exc), exc
                try:
                    record_decision({"underwriter_id": "UW-001", "action": "edit", "submission": "SUB-013", "reason": "x", "field_id": "year_built", "new_value": "1990"}, check)
                    raise SystemExit("an edit on manual_intake should fail")
                except ValueError as exc:
                    assert "manual intake" in str(exc) and "edit is refused" in str(exc), exc
                record_decision({"underwriter_id": "UW-001", "action": "decline", "submission": "SUB-013", "reason": "a person decided"}, check)  # decline stays
                assert correction_counts(check)["decline"] == 3

                # D-055: seq rises by one per entry; an unlisted id or an AI role cannot log.
                seqs = [json.loads(line)["seq"] for line in check.read_text().splitlines()]
                assert seqs == list(range(1, len(seqs) + 1)), seqs
                for who in ("UW-999", "senior-underwriter", "@compliance"):
                    try:
                        record_decision({"underwriter_id": who, "action": "edit", "submission": "SUB-000", "reason": "x"}, check)
                        raise SystemExit(f"{who} should not be able to log")
                    except ValueError:
                        pass

                # D-053: an approve after a decline needs a written reason at the workbench.
                save(ext, "SUB-012", "complete")
                record_decision({"underwriter_id": "user", "action": "decline", "submission": "SUB-012", "reason": "first look"}, check)
                try:
                    record_decision({"underwriter_id": "user", "action": "approve", "submission": "SUB-012"}, check)
                    raise SystemExit("an approve after a decline without a reason should fail")
                except ValueError:
                    pass
                record_decision({"underwriter_id": "user", "action": "approve", "submission": "SUB-012", "reason": "loss runs arrived"}, check)
                assert package.decisions("SUB-012", check)[-1]["action"] == "approve"

                # D-056 (B-139): an edit row stores its field and new value; a half edit or a non-edit with them is refused.
                record_decision({"underwriter_id": "user", "action": "edit", "submission": "SUB-012", "reason": "loss run", "field_id": "year_built", "new_value": " 1987 "}, check)
                last = json.loads(check.read_text().splitlines()[-1])
                assert last["field_id"] == "year_built" and last["new_value"] == "1987"
                before = len(check.read_text().splitlines())
                for bad in (
                    {"action": "edit", "field_id": "year_built"},
                    {"action": "edit", "new_value": "1987"},
                    {"action": "edit", "field_id": "not_a_field", "new_value": "1"},
                    {"action": "decline", "field_id": "year_built", "new_value": "1"},
                ):
                    try:
                        record_decision({"underwriter_id": "user", "submission": "SUB-012", "reason": "x", **bad}, check)
                        raise SystemExit(f"{bad} should fail")
                    except ValueError:
                        pass
                assert len(check.read_text().splitlines()) == before
            finally:
                prepare.EXTRACT_DIR = saved_dir

        # T-071 (3): the refused card hides approve, Missing, the carrier match, and the score.
        def card(status: str, status_reason: str | None = None, needs_human=None, fields=None) -> dict:
            rep_ = {
                    "status": status,
                    "status_reason": status_reason,
                    "error": "model call failed: HTTP 429 rate limit" if status == "extraction_failed" else None,
                    "complete": status == "complete",
                    "fields": fields or [{"field_id": "operations", "value": None}],
                    "conflicts": [],
                    "needs_human": needs_human or [],
                    "missing": ["named_insured"],
                    "extra": [],
                    "locations": [],
            }
            return {"id": f"SUB-{status}", "report": rep_, "files": ["application.md"], "ignored": [], "route": "hold", "score": points.score_run(rep_), "snippets": {}}

        for item in (
            card("extraction_failed"),
            card("all_values_rejected", status_reason=prepare.REJECT_REASON, needs_human=["scan.jpg"]),
        ):
            page = render([item], {"approve": 0, "edit": 0, "decline": 0})
            assert "<option>approve</option>" not in page
            assert "<h3>Missing</h3>" not in page
            assert "Carrier match:" not in page
            assert "Score:" not in page and "Not scored — " in page
            if "FAILED" in page:  # D-079 (B-295): nothing was read
                card_html = page.split("<article", 1)[1]  # the card only; What's new may quote old wording
                assert "Cooking: Not read — extraction failed" in card_html and "none stated" not in card_html and "not stated" not in card_html
                for label in ("Not read", "Not read by extraction", "Needs human read"):  # D-080 (B-297)
                    assert f"<p>{label}: {NOT_READ}</p>" in card_html and f"<p>{label}: none</p>" not in card_html, label
                assert page.count(f"<td>{NOT_READ}</td>") >= 2 * len(item["report"]["fields"]), "value and note say not read on every field"
            else:
                assert "Loss history: not scored" in page and "Cooking: not scored" in page
            assert "<option>edit</option>" in page and "<option>decline</option>" in page
        assert "REJECTED" in render([card("all_values_rejected", status_reason=prepare.REJECT_REASON)], None)
        # P-055 (D-105, D-065): a manual-intake card lists every reason, shows no route, no draft, no approve, and the send refusal says why.
        mi = card(prepare.MANUAL_INTAKE)
        mi["report"].update(scope=prepare.scope.detect([{"name": "application.jpg", "text": "", "needs_human": True}, {"name": "schedule.csv", "text": "loc,address\n1,1 A St\n2,2 B St"}]),
                            fields=[{"field_id": "operations", "value": None}], sprinklers=None)
        want_reasons = ["Manual intake: scanned application", "Manual intake: multiple locations"]
        assert all(t in [r["text"] for r in mi["report"]["scope"]["reasons"]] for t in want_reasons)
        m = match(mi["report"])
        assert m["route"] == "manual_intake" and "provisional" not in m and m["suggested"] == "" and "hold" not in m["route"], m
        mi.update(route=m["route"], note=m["note"], suggested=m["suggested"], score=points.score_run(mi["report"]))
        real_pending, tmp_pending = PENDING, Path(tempfile.mkdtemp(prefix="wb-pending-"))
        (tmp_pending / f"{mi['id']}.md").write_text("Please send the following. Nothing has been declined.")
        PENDING = tmp_pending
        try:
            mi_page = render([mi], {"approve": 0, "edit": 0, "decline": 0}).split("<article", 1)[1]
        finally:
            PENDING = real_pending
            shutil.rmtree(tmp_pending)
        for label in ("Not read", "Not read by extraction", "Needs human read"):  # T-104a UI H1: never "none" under the manual-intake banner
            assert f"<p>{label}: {MI_NOT_READ}</p>" in mi_page and f"<p>{label}: none</p>" not in mi_page, label
        assert "Manual intake</b>" in mi_page and all(f"<li>{t}</li>" in mi_page for t in want_reasons), mi_page[:900]
        assert "<option>edit</option>" not in mi_page and "<th>Cited text</th>" not in mi_page and "Nothing filled in: a person reads the file." in mi_page
        assert "<option>approve</option>" not in mi_page and "Carrier match:" not in mi_page and "Provisional route" not in mi_page and "Suggested market" not in mi_page
        assert "Missing-info draft" not in mi_page and "approve-draft" not in mi_page and "<h3>Missing</h3>" not in mi_page
        assert html.escape(f"No send: this file's status is {prepare.status_refusal(mi['report'])}; it cannot be sent.") in mi_page and "scanned application; multiple locations" in mi_page, mi_page[-1500:]
        assert "Cooking: not read (manual intake)" in mi_page and "no cooking equipment stated" not in mi_page and "Hood and suppression: not stated" not in mi_page
        assert "MANUAL INTAKE" in mi_page and prepare.status_refusal(mi["report"]) in mi_page
        # P-041 (D-088): review pending says what is pending, keeps approve with the tick, and routes as complete did.
        rp = card(prepare.REVIEW_PENDING, fields=[{"field_id": "operations", "value": "accounting office"},
                                                  {"field_id": "sales_or_payroll", "value": "2100000", "needs_review": True, "reason": "check against the email"}])
        rp["report"]["missing"] = []
        rp_page = render([rp], None).split("<article", 1)[1]
        assert "Complete — review pending: values to review: sales_or_payroll" in rp_page and "<option>approve</option>" in rp_page, rp_page[:600]
        assert 'name="ack" value="sales_or_payroll"' in rp_page
        assert prepare.ready_to_route(rp["report"]) and not prepare.ready_to_route({**rp["report"], "conflicts": [{"field": "square_feet", "resolution": "unresolved"}]})
        assert "review pending" not in render([card("incomplete")], None).split("<article", 1)[1]
        # B-324 (D-089): an open conflict shows a resolve form with both sides and an entered value, and the no-send line says why.
        rpc = card(prepare.REVIEW_PENDING, fields=[{"field_id": "operations", "value": "accounting office"}])
        rpc["report"].update(missing=[], conflicts=[{"field": "square_feet", "values": [{"value": "16800", "source": "email.md"}, {"value": "14200", "source": "application.md"}], "resolution": "unresolved"}])
        rpc_page = render([rpc], None).split("<article", 1)[1]
        assert 'name="action" value="resolve"' in rpc_page and 'value="16800"' in rpc_page and 'name="entered_value"' in rpc_page, rpc_page[:400]
        assert "OPEN: no send until the underwriter chooses or enters the value" in rpc_page and "No send: open conflict on square footage" in rpc_page
        rpc["report"]["conflicts"][0].update(resolution="resolved", resolved_value="14200", resolved_by="UW-001")
        assert "RESOLVED by UW-001: 14200" in render([rpc], None) and 'value="resolve"' not in render([rpc], None).split("<article", 1)[1]
        normal = card("complete", fields=[{"field_id": "operations", "value": "accounting office"}])
        normal["report"]["missing"] = []
        page_ok = render([normal], None)
        assert "<option>approve</option>" in page_ok
        assert "<h3>Missing</h3>" in page_ok and "Carrier match:" in page_ok and "Score:" in page_ok
        # P-016 R1/D-039: the card shows reason, quote, unread rows, and a checkbox per needs-review value.
        lowc = render([card("complete", fields=[{"field_id": "tiv_building", "value": "220000", "needs_review": True, "quote": "TIV 220,000", "reason": "Low-confidence scan read — check against the page"}])], None)
        assert "NEEDS REVIEW: Low-confidence scan read — check against the page" in lowc and needs_review_ids({"fields": [{"field_id": "tiv_building", "value": "220000", "needs_review": True}]}) == ["tiv_building"], "P-025 label and approve list"
        flagged = card("complete", fields=[{"field_id": "year_built", "value": "1942", "needs_review": True, "quote": "Built 1942", "reason": "number or date read from a scan"}])
        flagged["report"]["unread"] = [{"file": "a.pdf", "page": 2, "reason": "blank"}, {"file": "b.docx", "page": None, "reason": "file type .docx is not read"}]
        pf = render([flagged], None)
        assert "NEEDS REVIEW: number or date read from a scan" in pf and "Built 1942" in pf and 'name="ack" value="year_built"' in pf
        assert "a.pdf, page 2: blank" in pf and "b.docx, whole file:" in pf
        # B-428 (D-113): the "Not read by extraction" list comes from the saved run's unread rows, never from the file name.
        assert not_read_by_extraction({"unread": []}, ["application.pdf", "loss-runs.jpg", "email.md"]) == [], "a read pdf or jpg is not 'not read' (SUB-184, SUB-127/133)"
        assert not_read_by_extraction({"unread": [{"file": "a.pdf", "page": 2, "reason": "blank"}]}, ["a.pdf"]) == [], "a partly read file belongs on the Not read line, not here"
        assert not_read_by_extraction({"unread": [{"file": "b.docx", "page": None, "reason": "file type .docx is not read"}]}, ["b.docx"]) == ["b.docx"]
        assert not_read_by_extraction(None, ["a.pdf", "a.md"]) == ["a.pdf"], "only a run with no unread rows at all falls back to the name test"
        flagged["ignored"] = not_read_by_extraction(flagged["report"], [])
        pf_unread = render([flagged], None).split("<article", 1)[1]
        assert "<p>Not read by extraction: b.docx</p>" in pf_unread and "<p>Not read by extraction: a.pdf</p>" not in pf_unread, pf_unread[:900]
        assert 'name="ack"' not in page_ok
        # T-087: the card shows the quote status per carrier and SUB-002's open subjectivity.
        sub2 = card("complete", fields=[{"field_id": "operations", "value": "restaurant"}])
        sub2["id"] = "SUB-002"
        page2 = render([sub2], None)
        assert "carrier_b: quoted, subjectivities open" in page2 and "confirm hood and suppression on the inspection [open]" in page2 and "not bound" in page2
        assert "No carrier reply on file" in page_ok
        # D-058: the open subjectivity has a close form posting to /close-subjectivity (listed id + reason, logged)
        assert 'action="/close-subjectivity"' in page2

        assert logged["sent_to_carrier"] is False
        assert logged["reason"] == "self-check"
        assert logged["ai_version"].endswith("+rules-d015")
        fake = {
            "complete": True,
            "fields": [{"field_id": "operations", "value": "office building, no cooking"}, {"field_id": "tiv_building", "value": "$900,000"}],
        }
        assert route(fake) == "carrier_a"
        held = {
            "complete": True,
            "sprinklers": "no",
            "fields": [{"field_id": "operations", "value": "habitational, 8 units, no commercial cooking"}, {"field_id": "tiv_building", "value": "$3,000,000"}],
        }
        ready = dict(held)
        ready["sprinklers"] = "yes"
        assert route(held) == "senior_referral"  # D-059 item 6: sprinklers "no" (AG:37, AG:62; D-096 citation fix)
        assert route({**held, "sprinklers": None}) == "hold"
        # P-048 (c): a held file still routes, provisionally; route stays "hold" so no send gate opens.
        waiting = {**ready, "complete": False, "status": "incomplete"}
        m = match(waiting)
        assert (m["route"], m["provisional"], m["provisional_label"]) == ("hold", "senior_referral", "provisional — file on hold: missing information"), m
        assert match({**held, "complete": False, "status": "incomplete"})["provisional"] == "senior_referral" and match({**waiting, "sprinklers": None})["provisional"] is None
        assert "provisional" not in match(ready) and package._route(waiting) == "hold" and not package._overridable(waiting), "no send, no override on a held file"
        # P-050 (D-096): TIV missing gives a class-based provisional route; the send stays blocked. SUB-142 and SUB-144 shapes (dev reports).
        notiv = lambda ops, **kw: {"complete": False, "status": "incomplete", "fields": [{"field_id": "operations", "value": ops}, {"field_id": "tiv_building", "value": None}], **kw}
        m142 = match(notiv("Roofing contractor, 5 employees, shop and yard"))
        assert (m142["route"], m142["provisional"], m142["provisional_label"]) == ("hold", "senior_referral", PROVISIONAL_TIV) and "AG:38" in m142["provisional_note"], m142
        m144 = match(notiv("outpatient pediatric physical and speech therapy, treatment rooms, waiting room, offices, no overnight, no beds"))
        assert (m144["route"], m144["provisional"], m144["provisional_note"]) == ("hold", "senior_referral", "lab or medical occupancy - not Carrier A (R14; AG:29)") and not package._overridable(notiv("x")), m144
        # P-049 (d) (D-097): a referral word always wins over class words. SUB-138 and SUB-144 shapes.
        r = lambda ops, tiv="$1,000,000": {"complete": True, "fields": [{"field_id": "operations", "value": ops}, {"field_id": "tiv_building", "value": tiv}]}
        for ops, why in (("Wholesale and retail of animal feed, seed and fertilizer bags. Warehouse with loading dock", "AG:31"), ("pediatric therapy offices", "AG:29"),
                         ("cold storage warehouse, wholesale", "AG:31"), ("retail liquor store", "AG:30"), ("vacant office building", "AG:40")):
            assert route(r(ops)) == "senior_referral" and why in match(r(ops))["note"], (ops, match(r(ops)))
        assert route(r("lab-grown diamonds retail")) == "senior_referral" and "P-053" in match(r("labrador breeder office"))["note"], "whole words only (P-053: breeder is not an office word)"
        assert route(r("office, no liquor")) == "carrier_a", "a negated referral word does not refer"
        assert "R10" in match(r("cafe, Type I hood with wet chemical suppression"))["note"] and "AG:31" in match(r("chemical supply wholesale"))["note"], "SUB-130: wet chemical hood"
        assert {route(r(x)) for x in ("wet chemicals wholesale", "wet chemical wholesale", "wet-chemical retail supply")} == {"senior_referral"}, "security review: the exemption never opens Carrier A"
        assert match(notiv("sprinklered apartments", sprinklers="yes"))["provisional"] == "senior_referral" and match(notiv("apartments"))["provisional"] is None, "R12; a missing sprinkler answer still gives no route"
        assert "TIV" not in match(notiv("office"))["provisional_note"] and "TIV" not in match(notiv("restaurant"))["provisional_note"], "no TIV cap note is guessed"
        assert match(ready) == {"route": "senior_referral", "note": "habitational (R12; AG:37, AG:62); suggested market: Carrier C, underwriter confirms", "suggested": "carrier_c", "overridable": False}, "D-097: D-059 item 6 replaced"
        assert "AG:61 knock-out candidate" in match({**held, "cooking": {"equipment": {"state": "yes"}}})["note"] and "AG:61" not in match(held)["note"], "AG:61 only with cooking, never a decline"
        assert "no sprinklers" in match(held)["note"] and "no sprinklers" not in match(ready)["note"], "code-review: the sprinkler fact stays on the card"
        worded = {"complete": True, "fields": [{"field_id": "operations", "value": "apartments with no sprinklers"}, {"field_id": "tiv_building", "value": "$1,000,000"}]}
        assert route(worded) == "senior_referral" and "no sprinklers" in match(worded)["note"], "code-review: a 'no sprinklers' phrase is read before negation is dropped"
        R10 = "restaurant / cooking occupancy (R10; AG:39, AG:62); suggested market: Carrier B, underwriter confirms; its 3 clean loss years are not checked"
        # T-083: D-059 + D-060, written to the temp-free in-memory report only.
        def r(ops, tiv="$1,000,000", **kw):
            f = [{"field_id": "operations", "value": ops}]
            if tiv is not None:
                f.append({"field_id": "tiv_building", "value": tiv})
            return {"complete": True, "fields": f, **kw}

        m = match(r("barber shop"))
        assert m["route"] == "no_match" and m["overridable"]
        assert match(r("Barbecue Restaurant")) == {"route": "senior_referral", "note": "restaurant / cooking occupancy (R10; AG:39, AG:62); suggested market: Carrier B, underwriter confirms; its 3 clean loss years are not checked", "suggested": "carrier_b", "overridable": False}
        m = match(r("accounting office", "$8,000,000"))
        assert m["route"] == "senior_referral" and m["note"] == "outside pilot TIV limit (R13; AG:16)"
        for ops in ("cannabis dispensary retail", "armed security office", "sprinklered student housing", "Bar and grill", "fireworks"):
            m = match(r(ops, sprinklers="yes"))
            assert m["route"] == "no_match" and not m["overridable"], ops
        m = match(r("roofing contractor"))
        assert m["route"] == "senior_referral" and m["suggested"] == "carrier_b" and "R11" in m["note"]
        assert {route(r(f"{w} services")) for w in ("hvac", "glazier", "mason")} == {"senior_referral"}, "R11 words"
        assert match(r("office and restaurant"))["route"] == "senior_referral"
        assert route(r("office", "$5,000,000")) == "carrier_a" and route(r("office", "$5,000,001")) == "senior_referral"
        assert match(r("restaurant", "$2,000,001"))["note"] == match(r("restaurant", "$2,000,000"))["note"], "R15: no Carrier B cap"
        # D-061: the existing normalizer; missing or unreadable TIV holds; over $5M is senior referral, no $10M rule.
        assert match(r("office", "$8M"))["note"] == OUT_TIV and route(r("office", "$12,000,000")) == "senior_referral"
        assert route(r("office", "750K")) == "carrier_a" and route(r("office", "$1.2M")) == "carrier_a"
        assert route(r("office", "$1.2MM")) == "carrier_a" and route(r("office", "$5.1MM")) == "senior_referral"  # P-021
        for bad in ("", "TBD", None, "$0", "0", "-$5,000",  # B-203: 0 or negative holds
                    "50,000 sq ft", "50000 SF", "12,000 square feet", "8,000 sq. ft.", "9000sqft", "1 square foot"):  # B-209
            m = match(r("office", bad))
            assert m == {"route": "hold", "note": "TIV missing or unreadable", "suggested": "", "overridable": False, "provisional": "carrier_a", "provisional_note": match(r("office"))["note"],
                         "provisional_label": PROVISIONAL_TIV}, (bad, m)  # P-050: class-based, TIV needed to confirm
        assert route(r("oficina")) == "carrier_a" and route(r("")) == "hold"
        # D-078 (B-286): cuisine and ethnic words never decide the class. Alone they give the same no_match; with generic evidence the same carrier_b.
        cuisines = ("taqueria", "panadería", "pho house", "diner", "pizzeria", "soul food", "curry house", "halal cart", "bbq")  # "deli" is food service (D-079); bar words: see below
        assert {route(r(c)) for c in cuisines} == {"no_match"} and all(match(r(c))["overridable"] for c in cuisines)
        assert {match(r(f"{c} restaurant"))["note"] for c in cuisines} == {R10}, "D-078: the same route for every cuisine"
        assert {route(r(f"{c}, food service")) for c in cuisines} == {"senior_referral"} and match(r("catering kitchen"))["note"] == R10
        assert match(r("pho house", cooking={"equipment": {"state": "yes"}, "hood_suppression": {"state": "not_stated"}}))["note"] == R10, "stated cooking equipment is generic evidence"
        # D-079 (B-290): bar words with restaurant evidence go to a person; without it, as before. (B-293): bakery, coffee shop, deli are food service.
        bar_ref = {"route": "senior_referral", "note": "possible bar/liquor exposure — confirm liquor sales (R2; AG:46, AG:39)", "suggested": "", "overridable": False}
        for ops in ("sushi bar restaurant", "bar-b-q restaurant", "pub and kitchen"):
            assert match(r(ops)) == bar_ref, (ops, match(r(ops)))
        # T-107a (D-112) P-061 / P-062: dev-shaped cases; no hold-out file or gold was opened. cl = the application's two class lines.
        cl = lambda lob=None, cook=None: {"line_of_business": lob, "cooking_operations": cook}
        R1 = lambda m: m["route"] == "no_match" and m["note"].startswith("prohibited class (R1; AG:45-50): ") and not m["overridable"] and not m["suggested"]  # UI check H1: the note names the word
        lob_office = "commercial property and general liability, office"
        m = match(r("Consulting firm", class_lines=cl(lob_office)))  # SUB-174 shape: office only on the line of business
        assert m["route"] == "senior_referral" and m["suggested"] == "carrier_a" and "P-061" in m["note"], m  # never carrier_a: the class came from the line of business only
        m = match(r("and", class_lines=cl(lob_office)))
        assert m["route"] == "senior_referral" and "P-061" in m["note"], "a class read only from the line of business never routes to Carrier A"
        assert route(r("Consulting firm")) == "no_match", "no line of business: as before"
        assert route(r("office", class_lines=cl(lob_office))) == "carrier_a", "office on both: unchanged"
        assert route(r("sub and deli shop", class_lines=cl("commercial property, retail food", "Two fryers, flat-top, 8-burner range"))) == "senior_referral"  # SUB-182 shape
        assert match(r("sandwich shop", class_lines=cl(None, "Flat-top griddle, 2 fryers, 6-burner range")))["note"] == R10, "cooking equipment on the Cooking operations line is R9 evidence"
        assert match(r("sandwich shop, convection oven"))["note"] == R10, "cooking equipment in operations is R9 evidence"
        assert route(r("sandwich shop", class_lines=cl(None, "None (tenant electric ranges only)"))) == "no_match" and route(r("sandwich shop", class_lines=cl(None, "not listed"))) == "no_match", "none is not evidence"
        assert match(r("Dining venue", class_lines=cl("commercial property and general liability, restaurant and bar", "Two fryers, flat-top")))["note"] == bar_ref["note"], "SUB-186 shape: bar on the line of business, fryers"
        for cook in ("Fryer: none", "Fryers: 0", "Oven not used", "no fryer", "Fryers: n/a"):  # M1 (D-112): a negated appliance is not cooking evidence, so a bar file is never made softer by it
            assert R1(match(r("pub", class_lines=cl(None, cook)))), cook
        assert match(r("pub", class_lines=cl(None, "Two fryers, oven not used")))["note"] == bar_ref["note"], "a real fryer still counts"
        assert R1(match(r("Nightclub and lounge. Small kitchen, pre-packaged snacks only.", class_lines=cl(None, "Snack warmer")))), "SUB-201 shape: snacks only is not restaurant evidence"
        assert R1(match(r("pub, small kitchen, snack warmer"))) and R1(match(r("tavern, kitchen, snacks only")))
        assert R1(match(r("restaurant and lounge, full kitchen", class_lines=cl(None, "Two fryers, flat-top, 8-burner range")))), "P-062 (a): a lounge is never softened by real cooking"
        assert R1(match(r("nightclub with restaurant"))) and R1(match(r("hotel lounge with catering"))) and R1(match(r("hookah restaurant")))
        assert R1(match(r("bar and grill"))), "bar and grill: no restaurant word, as before"
        assert match(r("restaurant with a bar", class_lines=cl(None, "Two fryers"))) == bar_ref == match(r("pub, restaurant, full kitchen")), "R2 stays for bar, tavern, pub beside real evidence"
        assert route(r("restaurant", class_lines=cl("restaurant and bar"))) == "senior_referral" and "R2" in match(r("restaurant", class_lines=cl("restaurant and bar")))["note"]
        assert match(r("Pre-packaged snacks only, no cooking", class_lines=cl("restaurant")))["route"] == "no_match", "snacks only blocks the word evidence"
        assert route(r("Pizzeria, two fryers, snacks only")) == "senior_referral", "stated equipment still counts"
        assert match(r("bbq restaurant"))["note"] == R10
        for ops in ("sports bar", "tavern", "nightclub"):
            assert R1(match(r(ops))) and f'"{ops.split()[-1]}" in operations' in match(r(ops))["note"], ops
        assert {route(r(w)) for w in ("hookah lounge", "recycling yard", "sawmill", "bail bonds office")} == {"no_match"}, "W1 additions; prohibited wins over office"
        assert R1(match(r("pub"))) and R1(match(r("nail lounge"))), "P-051 (d): pubs, lounges are W1 (AG:46), never overridable"
        for ops in ("bar, no deep fryer", "tavern, no flat-top griddle"):  # T-107a code review: a negated equipment phrase is not restaurant evidence
            assert R1(match(r(ops))), ops
        assert R1(match(r("bar", class_lines=cl(None, "No gas burners"))))
        assert match(r("leased offices", class_lines=cl("office - nightclub")))["note"].endswith('"nightclub" in the Line of business line (P-061)')
        # P-051: the four @model-risk P-049 H1 phrases never reach Carrier A. T-107a (D-112): a bar word beside a non-food operation is R1 (stricter of W1 and W1b);
        # changed from senior_referral R16: "office building with ground-floor pub", "retail store and cocktail lounge", "office building with ground-floor bar".
        for ops in ("office building with ground-floor pub", "retail store and cocktail lounge", "office building with ground-floor bar", "wholesale tavern", "gym and nightclub"):
            assert R1(match(r(ops))), (ops, match(r(ops)))
        for ops in ("office building, no utilities", "office, unoccupied", "office and retail storefront", "retail store with a nail salon", "vacant office building"):
            assert route(r(ops)) == "senior_referral", (ops, match(r(ops)))
        assert "AG:51" in match(r("office building, no utilities"))["note"]
        assert route({"complete": True, "fields": [{"field_id": "operations", "value": "Office building", "quote": "Operations: office building. No utilities connected."}, {"field_id": "tiv_building", "value": "$1,000,000"}]}) == "senior_referral", "P-051 (c): read before the negation drop"
        for ops in ("Clothing boutique retail store", "clothing store tienda de ropa", "Office, 2nd floor, clients by appointment", "office suite, LLC",
                    "thrift shop", "office building, no food, no alcohol"):
            assert route(r(ops)) == "carrier_a", (ops, match(r(ops)))  # P-051 (a): AG:29-31 allow-list (SUB-143); P-054 (a): only non-occupancy words beside it
        # P-054 (a) (D-100): shop, store, gift, home, goods and trade words are occupancy words, never neutral (B-389).
        for ops in ("Used book and thrift shop, donated goods sorted on site", "Dry retail gift shop", "Financial advisory and tax office, 2nd floor",
                    "office and shop", "office with back shop", "office and store", "office and gift shop", "home office", "bookkeeping office"):
            m = match(r(ops))
            assert (m["route"], m["suggested"]) == ("senior_referral", "carrier_a"), (ops, m)
        assert route(r("office, utilities on")) == "senior_referral" and route(r("gym")) == "no_match", "P-053: utilities is not a listed word; a non-target class alone is R8"
        # P-053 (D-099): the @model-risk check-P-051-P-052 probe phrases (H1 and M1) all go to senior_referral with Carrier A suggested.
        for ops in ("office and warehouse", "office and auto body shop", "retail and tattoo parlor", "retail and pawn shop", "office with veterinary practice",
                    "office with indoor shooting range", "office and data center", "office and kennel", "office and casino", "retail with bowling alley",
                    "retail and brewery taproom", "retail and winery tasting room", "retail and cbd", "retail smoke shop", "retail - vape shop",
                    "office tenants; second floor event hall", "office and storage of tires", "lumber wholesale", "steel wholesale", "scrap metal wholesale",
                    "tire wholesale", "wholesale firearms", "office, under renovation", "Light wholesale of electrical supplies"):
            m = match(r(ops))
            assert (m["route"], m["suggested"]) == ("senior_referral", "carrier_a") and "P-053" in m["note"], (ops, m)
        # check-P-054 H2: cooking beside an allow-list word is not neutral; the empty "Cooking: none" label is.
        for ops in ("office with cooking", "office, cooking", "office, back room cooking", "retail store, cooking on the ground floor"):
            m = match(r(ops))
            assert (m["route"], m["suggested"]) == ("senior_referral", "carrier_a"), (ops, m)
        assert route(r("office building. Cooking: none")) == route(r("office building, cooking operations - none")) == "carrier_a"
        # P-054 (b): vacancy variants are W2e (AG:51), so no market confirm.
        for ops in ("office, no tenants", "retail, building empty", "office, utilities shut off", "office, power disconnected", "oficina desocupada",
                    "local vacante", "edificio vacío", "retail, power off", "office, vacancy", "oficina, sin servicios", "office, utilities are off",
                    "office, no power", "office, no electricity", "abandoned retail", "oficina abandonada", "office, not occupied", "local sin ocupar"):
            assert "AG:51" in match(r(ops))["note"] and route(r(ops)) == "senior_referral", (ops, match(r(ops)))
        assert route(r("cannabis dispensary restaurant")) == "no_match", "other prohibited words are unchanged"
        assert route(r("restaurant bar", None)) == "hold", "holds come before the referral"
        # P-047 (c): the cited text is read too, so a dropped "and bar" still refers; a negated word does not.
        quoted = lambda ops, quote: {"complete": True, "fields": [{"field_id": "operations", "value": ops, "quote": quote}, {"field_id": "tiv_building", "value": "$1,000,000"}]}
        assert match(quoted("Full-service restaurant", "Operations: Full-service restaurant and bar, 180 seats, full liquor license")) == bar_ref
        assert match(quoted("Mexican restaurant", "Operations: Mexican restaurant, 70 seats, beer and wine only, no bar."))["note"] == R10
        assert route(quoted("Dry retail", "Operations: Dry retail. No food, no alcohol.")) == "carrier_a"
        assert route(quoted("Financial advisory and tax office, 2nd floor", "Operations: Financial advisory and tax office, 2nd floor. Clients by appointment. No inventory, no goods held for sale.")) == "senior_referral", "SUB-127: P-054"
        assert route(quoted("Dry retail gift shop: candles, home goods, greeting cards, gift wrap.", "No food, no alcohol, no repackaging.")) == "senior_referral", "SUB-128: P-054"
        lined = quoted("Mexican restaurant", "Operations: Mexican restaurant, 70 seats.")
        lined["fields"][0]["context"] = "Liquor: full bar, 35% of sales"
        assert match(lined) == bar_ref, "P-047 H1: a separate liquor line still refers"
        for ops in ("bakery", "coffee shop", "deli"):
            assert match(r(ops))["note"] == R10, ops
        assert match(r("sprinklered apartments", "$4,000,000"))["suggested"] == "carrier_c" and route(r("sprinklered apartments", "$4,000,000")) == "senior_referral"
        assert match(r("sprinklered apartments", "$6,000,000"))["note"].endswith(OUT_TIV)
        assert route(r("office")) == "carrier_a" and route(r("barley mill")) == "no_match"
        assert "COOKING" not in points.score_run({**fake, "status": "complete"})["reason_codes"]

        # D-066 items 10, 2/4/8, 1, 13: saved run only on load, refusals as plain messages, typed send, draft approve.
        import llm_extract

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            ext, inbox, dlog = tmp / "extractions", tmp / "inbox", tmp / "decisions.jsonl"
            old = (prepare.EXTRACT_DIR, prepare.INBOX_DIR, INBOX, LOG, PENDING, TO_PRODUCER, TO_CARRIER, package.DECISIONS_LOG, package.SENDS_LOG, package.INBOX, llm_extract._post, prepare.process_submission)

            APP_OK = ("Named insured: Example Roofing LLC\nPremises address: 100 Main St, Austin, TX 78701\nEffective date: 2027-01-01\nYears in business: 9\n"
                       "Operations: General office work for the business, no public visits, and the staff are all on site.\nConstruction: masonry\n")  # in scope for the P-063 send-time re-check

            def stored(sub: str, status: str, fields=None, complete=True, conflicts=None, app=APP_OK) -> None:
                folder = inbox / sub
                folder.mkdir(parents=True, exist_ok=True)
                (folder / "application.md").write_text(f"SYNTHETIC application {sub}\n{app}")
                payload = {"submission": sub, "status": status, "error": None, "complete": complete, "conflicts": conflicts or [], "needs_human": [], "unread": [], "sprinklers": "no", "fields": fields or [],
                           "input_manifest": prepare.folder_manifest(folder), "hash_algorithm": prepare.HASH_ALGORITHM}
                payload["saved_hash"] = prepare.hash_payload(payload)
                ext.mkdir(exist_ok=True)
                (ext / f"{sub}.json").write_text(json.dumps(payload))

            def boom(*_a, **_k):
                raise SystemExit("page load must not extract or call a model")

            try:
                prepare.EXTRACT_DIR, prepare.INBOX_DIR, INBOX, LOG = ext, inbox, inbox, dlog
                PENDING, TO_PRODUCER, TO_CARRIER = tmp / "pending", tmp / "to-producer", tmp / "to-carrier"
                package.DECISIONS_LOG, package.SENDS_LOG, package.INBOX = dlog, tmp / "sends.jsonl", inbox
                good = [{"field_id": f, "value": "x", "source": "application.md", "start": 0, "end": 3} for f in prepare.FIELDS]
                good = [{**r, "value": {"operations": "office building", "tiv_building": "$1,000,000"}.get(r["field_id"], "x")} for r in good]
                stored("SUB-901", "complete", good)
                stored("SUB-903", "complete", good)
                stored("SUB-910", "extraction_failed", complete=False)
                stored("SUB-929", "incomplete", [{**r, "value": None} if r["field_id"] == "effective_date" else r for r in good], complete=False)
                (inbox / "SUB-902").mkdir()  # no saved run
                (inbox / "SUB-903" / "application.md").write_text("changed after extraction\n")
                # item 10: page load with the model call and extraction both patched to raise.
                llm_extract._post, prepare.process_submission = boom, boom
                q = load_queue()
                pg = render(q, None)
                assert "No usable saved run: no saved run for SUB-902" in pg and "does not run extraction" in pg
                assert "hash check: ok · manifest check: ok" in pg and "changed since extraction" in pg
                llm_extract._post, prepare.process_submission = old[-2:]

                # items 2/4/8: refusals come back as (submission, False, plain words), never an exception.
                def refused(path, **kw):
                    sub, ok, text = act(path, {"submission": "SUB-901", **kw})
                    assert not ok and sub == "SUB-901", text
                    return text

                assert "Decision refused: only an id on underwriters.json" in refused("/decision", underwriter_id="UW-999", action="approve")
                assert refused("/send", user_line="send to carrier SUB-901").startswith("Send refused: no logged decision")
                assert "changed since extraction" in act("/send", {"submission": "SUB-903", "user_line": "send to carrier SUB-903"})[2]
                assert "Send refused: this file's status is extraction_failed" in act("/send", {"submission": "SUB-910", "user_line": "send to carrier SUB-910"})[2]
                assert act("/send", {"submission": "../x"})[2].startswith("Send refused: no such submission")
                # P-063 (B-432): a SUB-233-shaped file saved complete is refused at send time and its card says why, whatever the status
                stored("SUB-933", "complete", good, app=APP_OK.replace("100 Main St, Austin, TX 78701", "Loc 1: 3412 S Georgia St, Amarillo, TX 79109; Loc #2: 6901 Bell St, Amarillo, TX 79106"))
                msg933 = act("/send", {"submission": "SUB-933", "user_line": "send to carrier SUB-933"})[2]
                assert msg933.startswith("Send refused: out of pilot scope at send time (multiple locations, " + prepare.scope.VERSION), msg933
                card933 = render(load_queue("SUB-933"), None)
                assert html.escape("No send: out of pilot scope at send time (multiple locations, " + prepare.scope.VERSION) in card933 and 'action="/send"' not in card933, card933[-2000:]
                (PENDING / "SUB-933.md").parent.mkdir(parents=True, exist_ok=True)
                (PENDING / "SUB-933.md").write_text("Nothing has been declined")
                card933 = render(load_queue("SUB-933"), None)
                assert "<b>Send blocked</b> — out of pilot scope" in card933 and "Next step: re-run extraction" in card933 and "Provisional route: <b>" not in card933 and "· No send until the hold clears" not in card933
                assert "No send to producer: out of pilot scope at send time" in card933 and 'action="/approve-draft"' not in card933
                assert act("/approve-draft", {"submission": "SUB-933"})[2].startswith("Request not approved: out of pilot scope at send time"), "the gate refuses too"
                shutil.rmtree(PENDING)  # later checks make their own
                pg = render(load_queue(), None, {"SUB-901": (False, "Send refused: x")})
                assert 'class="msg bad"' in pg and "Send refused: x" in pg and "Approve first" in pg and 'action="/send"' not in pg  # B-249

                # item 1: a recorded approve, then the typed line. A wrong line is refused; the right one writes the package.
                assert act("/decision", {"submission": "SUB-901", "underwriter_id": "user", "action": "approve", "reason": "ok"})[1]
                assert "exact line" in refused("/send", user_line="yes")
                assert not TO_CARRIER.exists()
                sub, ok, text = act("/send", {"submission": "SUB-901", "user_line": "send to carrier SUB-901"})
                assert ok and text.startswith("Sent:") and (TO_CARRIER / "SUB-901.md").is_file(), text
                assert json.loads((tmp / "sends.jsonl").read_text().splitlines()[-1])["actor"] == "user"

                # B-231/B-232/B-233 (D-067): folding with a count, carrier named, second send refused, resend logged.
                pg = render(load_queue(), None)
                assert "No saved run (1)" in pg and pg.index('id="SUB-901"') < pg.index("No saved run (1)") < pg.index('id="SUB-902"')
                assert "<details><summary><b>No saved run" in pg  # closed by default
                assert "carrier_a" in pg and "Already sent on" in pg and "to carrier_a" in pg and "Resend reason" in pg
                assert "No send: the carrier match is hold" in pg or "No send: the file is incomplete" in pg  # SUB-929
                held_card = pg[pg.index('id="SUB-929"') :]  # P-048 (c): the held file shows its provisional route and stays blocked
                assert "Provisional route: <b>" in held_card and "(provisional — file on hold: missing information) · No send until the hold clears" in held_card, held_card[:3000]
                assert "No send: this file&#x27;s status is extraction_failed" in pg
                line = "send to carrier SUB-901"
                assert act("/send", {"submission": "SUB-901", "user_line": line})[2].startswith("Send refused: already sent on")
                assert "written reason" in act("/send", {"submission": "SUB-901", "user_line": line})[2]
                sub, ok, text = act("/send", {"submission": "SUB-901", "user_line": line, "resend_reason": "carrier lost it"})
                assert ok and json.loads((tmp / "sends.jsonl").read_text().splitlines()[-1])["resend_reason"] == "carrier lost it", text
                stored("SUB-904", "complete", good)
                assert act("/decision", {"submission": "SUB-904", "underwriter_id": "user", "action": "approve", "reason": "ok"})[1]
                assert "The package goes to <b>carrier_a</b>" in render(load_queue(), None)
                assert "SUB-901.md, SUB-901-resend-2.md" in render(load_queue(), None)  # B-247 card lists each file
                # B-244: an approve logged before the run held low-confidence values does not cover them.
                stored("SUB-905", "complete", [{**r, "needs_review": True} if r["field_id"] == "named_insured" else r for r in good])
                with dlog.open("a") as h:
                    h.write(json.dumps({"seq": 9000, "submission": "SUB-905", "action": "approve", "underwriter_id": "user", "reason": "ok", "run_hash": package._current_hash("SUB-905")}) + "\n")
                assert "Send refused: 1 value needs review and is not acknowledged (named_insured)" in render(load_queue(), None)
                assert "not acknowledged (named_insured)" in act("/send", {"submission": "SUB-905", "user_line": "send to carrier SUB-905"})[2]

                # item 13: the draft shows on the card; the user approves it (D-050); refused files cannot be approved.
                PENDING.mkdir()
                (PENDING / "SUB-929.md").write_text("Submission SUB-929\nNothing has been declined. Nothing has been bound.\n\nMissing:\n- effective date\n")
                (PENDING / "SUB-910.md").write_text("Submission SUB-910\nNothing has been declined.\n")
                pg = render(load_queue(), None)
                assert "Missing-info draft for the producer (not sent)" in pg and "- effective date" in pg and 'action="/approve-draft"' in pg
                assert act("/approve-draft", {"submission": "SUB-910"})[2].startswith("Request not approved: this file's status is extraction_failed")
                sub, ok, text = act("/approve-draft", {"submission": "SUB-929", "reason": "producer asked"})
                assert ok and (TO_PRODUCER / "SUB-929.md").read_text().startswith("Approved-by: user (override)"), text
                assert "Producer request on file" in render(load_queue(), None)
                assert not act("/approve-draft", {"submission": "SUB-901"})[1]  # no draft file: plain refusal, not a crash

                # P-026 (D-069): approve, re-save with a changed value -> re-review message and refused send; approve again -> allowed.
                def art(page: str, sub: str) -> str:
                    start = page.index(f'<article id="{sub}">')
                    return page[start : page.index("</article>", start)]

                stored("SUB-906", "complete", good)
                assert act("/decision", {"submission": "SUB-906", "underwriter_id": "user", "action": "approve", "reason": "ok", "run_hash": "0ld"})[2].startswith("Decision refused: the saved run changed since this card was opened")
                assert act("/decision", {"submission": "SUB-906", "underwriter_id": "user", "action": "approve", "reason": "ok"})[1]
                first = json.loads(dlog.read_text().splitlines()[-1])
                assert first["run_hash"] == package._current_hash("SUB-906") and first["at"] and "Re-review needed" not in art(render(load_queue(), None), "SUB-906")
                stored("SUB-906", "complete", [{**r, "value": "Different Co"} if r["field_id"] == "named_insured" else r for r in good])
                pg = render(load_queue(), None)
                assert "Re-review needed: file changed since your approval" in art(pg, "SUB-906") and 'action="/send"' not in art(pg, "SUB-906")
                assert act("/send", {"submission": "SUB-906", "user_line": "send to carrier SUB-906"})[2] == "Send refused: Re-review needed: file changed since your approval"
                assert "not the current run" in art(pg, "SUB-906")
                assert act("/decision", {"submission": "SUB-906", "underwriter_id": "user", "action": "approve", "reason": "ok again"})[1]
                pg = render(load_queue(), None)
                assert "Re-review needed" not in art(pg, "SUB-906") and 'action="/send"' in art(pg, "SUB-906")
                assert act("/send", {"submission": "SUB-906", "user_line": "send to carrier SUB-906"})[1]

                # History panel: decisions, acknowledgments, sends and resends with who, why, when, short run hash.
                h = art(render(load_queue(), None), "SUB-901")
                cur = package._current_hash("SUB-901")[:8]
                assert "<h3>History</h3>" in h and "send SUB-901.md" in h and "resend SUB-901-resend-2.md" in h and "carrier lost it" in h
                assert f"run {cur} (current run)" in h and "approve" in h and "user" in h
                ack = art(render(load_queue(), None), "SUB-905")
                assert "approve" in ack and "no run hash" not in ack
                assert "No decision or send logged" in art(render(load_queue(), None), "SUB-929")

                stored("SUB-908", "complete", [{**r, "needs_review": True, "quote": "Acme", "reason": "r"} if r["field_id"] == "named_insured" else r for r in good])
                assert act("/decision", {"submission": "SUB-908", "underwriter_id": "user", "action": "approve", "reason": "checked", "ack": ["named_insured"]})[1]
                assert "acknowledged 1: named_insured" in art(render(load_queue(), None), "SUB-908")
                # B-324 (D-089): a resolve names an open conflict of this run, is logged with the run hash, and the card then shows it resolved.
                sq = {"field": "square_feet", "values": [{"value": "16800", "source": "email.md"}, {"value": "14200", "source": "application.md"}], "resolution": "unresolved"}
                stored("SUB-909", prepare.REVIEW_PENDING, good, complete=False, conflicts=[sq])
                assert "No send: open conflict on square footage" in art(render(load_queue(), None), "SUB-909")
                base = {"submission": "SUB-909", "underwriter_id": "user", "action": "resolve", "conflict_field": "square_feet"}
                assert act("/decision", {**base, "conflict_field": "sales_or_payroll", "chosen_value": "1"})[2] == "Decision refused: no open conflict on sales_or_payroll in this run"
                assert act("/decision", base)[2] == "Decision refused: choose one of the values or enter the value"
                assert act("/decision", {**base, "chosen_value": "16800", "run_hash": "0ld"})[2].startswith("Decision refused: the saved run changed")
                assert act("/decision", {**base, "chosen_value": "16800", "entered_value": "14200"})[1]
                last = json.loads(dlog.read_text().splitlines()[-1])
                assert (last["action"], last["conflict_field"], last["new_value"], last["run_hash"]) == ("resolve", "square_feet", "14200", prepare.read_saved_run("SUB-909")["saved_hash"]), last
                assert "RESOLVED by user: 14200" in art(render(load_queue(), None), "SUB-909")

                # Suggested market is its own field; the footer shows model and prompt version, never a key or a host.
                stored("SUB-907", "complete", [{**r, "value": "roofing contractor"} if r["field_id"] == "operations" else r for r in good])
                card = art(render(load_queue(), None), "SUB-907")
                assert "Suggested market: <b>carrier_b</b>" in card and 'action="/confirm-market"' in card and "UW-001 Dana Reyes" in card and "UW-002" not in card.split("/confirm-market")[1].split("</form>")[0]
                assert "No send: a senior referral needs a senior underwriter to confirm the market first" in card  # P-052: the plain reason
                assert 'class="bad">Account-manager check: refused, a senior referral needs a senior underwriter' in card and "in appetite" not in card.split("Account-manager check")[1]  # T-107c
                assert "Send refused: a senior referral needs a senior underwriter to confirm the market first" in act("/send", {"submission": "SUB-907", "user_line": "send to carrier SUB-907"})[2]  # T-107c (B-412): the card's order
                assert not str(package.confirms_path()).startswith(str(ROOT)), "D-069: the confirm log is the sandbox copy"
                h907 = prepare.read_saved_run("SUB-907")["saved_hash"]
                assert "Market confirm refused: only a senior" in act("/confirm-market", {"submission": "SUB-907", "underwriter_id": "UW-002", "carrier": "carrier_b", "reason": "x", "run_hash": h907})[2]
                assert act("/confirm-market", {"submission": "SUB-907", "underwriter_id": "UW-001", "carrier": "carrier_b", "reason": "roofing only, no hot work", "run_hash": h907})[1]
                card = art(render(load_queue(), None), "SUB-907")
                assert "Market confirmed: <b>carrier_b</b> by UW-001 Dana Reyes" in card and "roofing only, no hot work" in card and 'action="/confirm-market"' not in card
                assert "Approve first" in card, "P-052: a confirm opens no send gate"
                assert "Account-manager check: passes" in card and "appetite" not in card.split("Account-manager check")[1], "T-107c: confirmed carrier passes the AM check"
                pg = render(load_queue(), None)
                assert pg.count("<details><summary>Show all") == 1 and pg.split("<details><summary>Show all")[0].split("<summary><b>What's new</b>")[1].count("<li>") == 5, "T-107d: latest 5, then show all"
                stored("SUB-907", "complete", [{**r, "value": "office building with ground-floor pub"} if r["field_id"] == "operations" else r for r in good])
                card = art(render(load_queue(), None), "SUB-907")
                assert 'action="/confirm-market"' not in card and "prohibited class (R1; AG:45-50)" in card, "T-107a (D-112): office + pub is now no_match R1, no market confirm offered (was senior_referral R16; the old text asserted here was the prohibited-word refusal)"
                # @compliance M1 (D-099): the excluded carrier is not offered, the card says why, and a posted confirm for it is refused.
                stored("SUB-961", "complete", [{**r, "value": "office with a medical clinic"} if r["field_id"] == "operations" else r for r in good])
                card = art(render(load_queue(), None), "SUB-961")
                form = card.split('action="/confirm-market"')[1].split("</form>")[0]
                assert "Not offered: carrier_a. A note on the file excludes it (carrier match note:" in form and "<option>carrier_a</option>" not in form and "<option>carrier_b</option>" in form, form
                m1_reply = act("/confirm-market", {"submission": "SUB-961", "underwriter_id": "UW-001", "carrier": "carrier_a", "reason": "x", "run_hash": prepare.read_saved_run("SUB-961")["saved_hash"]})[2]
                assert "Market confirm refused: the file's notes exclude carrier_a" in m1_reply, m1_reply
                stored("SUB-962", "complete", [{**r, "value": "office and casino"} if r["field_id"] == "operations" else r for r in good])
                card = art(render(load_queue(), None), "SUB-962")
                assert "Suggested market: <b>carrier_a</b>" in card and "words not on the Carrier A allow-list: casino" in card and "Not offered" not in card  # P-053
                assert "Suggested market" not in art(render(load_queue(), None), "SUB-901")  # B-264: senior referrals only
                env_old = {k: os.environ.get(k) for k in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL")}
                try:
                    for k in env_old:
                        os.environ.pop(k, None)
                    assert "no saved run on this page" in render([], None)
                    os.environ.update(LLM_MODEL="test-model", LLM_API_KEY="sk-SECRET", LLM_BASE_URL="https://user:pw@host.example/v1")
                    foot = render(load_queue(), None)
                    # B-265: the footer shows the saved run's model and prompt (here none recorded), never the environment's, a key or a host.
                    assert "Model (saved run): not recorded" in foot and "test-model" not in foot and "SECRET" not in foot and "host.example" not in foot and "pw@" not in foot
                    stored("SUB-901", "complete", good)
                    raw = json.loads((ext / "SUB-901.json").read_text())
                    raw.update(model_version="model-A", prompt_version="v7")
                    raw["saved_hash"] = prepare.hash_payload(raw)
                    (ext / "SUB-901.json").write_text(json.dumps(raw))
                    foot = render([q for q in load_queue() if q["id"] == "SUB-901"], None)
                    assert "Model (saved run): model-A · Prompt version (saved run): v7" in foot and "test-model" not in foot
                    foot = render(load_queue(), None)
                    assert "(they differ)" in foot and "SUB-901: model model-A · prompt v7" in foot and "SUB-907: model not recorded" in foot
                    # E2: the decision row holds the saved run's versions and does not follow LLM_MODEL.
                    stored("SUB-901", "complete", good)
                    raw = json.loads((ext / "SUB-901.json").read_text())
                    raw.update(model_version="model-A", prompt_version="v7")
                    raw["saved_hash"] = prepare.hash_payload(raw)
                    (ext / "SUB-901.json").write_text(json.dumps(raw))
                    row1 = record_decision({"underwriter_id": "user", "submission": "SUB-901", "action": "edit", "reason": "e2 check"}, dlog)
                    os.environ["LLM_MODEL"] = "changed"
                    row2 = record_decision({"underwriter_id": "user", "submission": "SUB-901", "action": "edit", "reason": "e2 again"}, dlog)
                    keys = ("points", "not_scored_reason", "reason_codes", "points_version", "model_version", "prompt_version", "cache_key")
                    assert all(k in row1 for k in keys) and all(row1[k] == row2[k] for k in keys) and row1["model_version"] == "model-A" and row1["prompt_version"] == "v7" and row1["cache_key"] is None
                    assert record_decision({"underwriter_id": "user", "submission": "SUB-910", "action": "decline", "reason": "x"}, dlog)["points"] is None
                    assert row1["points"] == 0 and row1["not_scored_reason"] is None
                    # P-015: a failed, incomplete and empty saved run shows Not scored and no number; the three lines show on every card.
                    pg = render(load_queue(), None)
                    for sid_ in ("SUB-910", "SUB-929"):
                        a = art(pg, sid_)
                        assert "Not scored — " in a and "Score:" not in a and "Hood and suppression:" in a, sid_
                        assert ("Cooking: Not read — extraction failed" in a) if "FAILED" in a else ("Loss history: not scored" in a and "Cooking: not scored" in a), sid_
                    assert "Score: 0" in art(pg, "SUB-901") and "Cooking: not scored" in art(pg, "SUB-901")
                    # W1: a mark with no reason, an unknown id or an unknown code is refused; a mark leaves match() and the points unchanged.
                    stored("SUB-950", "complete", [{**r, "value": "restaurant, 2 stories"} if r["field_id"] == "operations" else {**r, "value": "Frame"} if r["field_id"] == "construction" else r for r in good])
                    q0 = {i["id"]: i for i in load_queue()}["SUB-950"]
                    assert q0["score"]["reason_codes"] == ["FRAME_CONSTRUCTION"], q0["score"]
                    mk = {"submission": "SUB-950", "code": "FRAME_CONSTRUCTION", "underwriter_id": "user", "reason": "brick veneer"}
                    for bad in ({"reason": ""}, {"underwriter_id": "UW-999"}, {"code": "COOKING"}, {"code": "MADE_UP"}):
                        ok_, = [act("/mark-code", {**mk, **bad})[1]]
                        assert not ok_
                    assert act("/mark-code", {**mk, **{"reason": ""}})[2].startswith("Mark refused: a reason is required")
                    assert not marks_path().exists() or code_marks("SUB-950") == []
                    assert act("/mark-code", mk)[1]
                    q1 = {i["id"]: i for i in load_queue()}["SUB-950"]
                    assert q1["score"] == q0["score"] and q1["route"] == q0["route"] and match(q1["report"]) == match(q0["report"])
                    m1 = json.loads(marks_path().read_text().splitlines()[-1])
                    assert m1["points_version"] == points.POINTS_VERSION and m1["run_hash"] == q1["report"]["saved_hash"] and m1["reason"] == "brick veneer" and m1["at"]
                    a = art(render(load_queue(), None), "SUB-950")
                    assert "marked wrong by user: brick veneer" in a and "marked FRAME_CONSTRUCTION wrong" in a and 'action="/mark-code"' in a
                    assert "Score: 15" in a and "add a code" not in a.lower()
                    assert package.decisions("SUB-950", dlog) == []  # a mark is not a decision
                    # B-278 (D-073): a needs-review cooking line is provisional; a listed underwriter records the call for this run; then points apply.
                    stored("SUB-951", "complete", good)
                    p951 = ext / "SUB-951.json"
                    j = json.loads(p951.read_text()); j.pop("saved_hash")
                    j["cooking"] = {"equipment": {"state": "needs_review", "terms": [], "negated": [], "quote": "fryer, none", "reason": prepare.REASON_COOKING},
                                    "hood_suppression": {"state": "not_stated"}}
                    j["saved_hash"] = prepare.hash_payload(j); p951.write_text(json.dumps(j))
                    a = art(render(load_queue(), None), "SUB-951")
                    assert "Provisional — cooking not scored" in a and "Score:" not in a and 'action="/cooking-call"' in a and 'value="cooking_equipment"' in a, a
                    cc = {"submission": "SUB-951", "call": "present", "underwriter_id": "user", "reason": "fryer on the photos", "run_hash": j["saved_hash"]}
                    for bad in ({"reason": ""}, {"underwriter_id": "UW-999"}, {"call": "maybe"}, {"run_hash": "stale"}):
                        assert not act("/cooking-call", {**cc, **bad})[1], bad
                    assert not calls_path().exists() or cooking_call_for("SUB-951", j) is None
                    assert act("/cooking-call", cc)[1]
                    q951 = {i["id"]: i for i in load_queue()}["SUB-951"]["score"]
                    assert q951["scored"] and "COOKING" in q951["reason_codes"] and q951["points"] is not None, q951
                    _a = art(render(load_queue(), None), "SUB-951")
                    assert "underwriter recorded present (user: fryer on the photos)" in _a
                    assert json.loads(calls_path().read_text().splitlines()[-1])["run_hash"] == j["saved_hash"]
                    # B-266: a stale card lists changed fields, old to new.
                    assert act("/decision", {"submission": "SUB-908", "underwriter_id": "user", "action": "approve", "reason": "again", "ack": ["named_insured"]})[1]
                    stored("SUB-908", "complete", [{**r, "value": "Other Co", "needs_review": True, "quote": "Acme", "reason": "r"} if r["field_id"] == "named_insured" else r for r in good])
                    a = art(render(load_queue(), None), "SUB-908")
                    assert "Re-review needed" in a and "named_insured: x → Other Co" in a, a
                    assert "year_built:" not in a.split("Changed since")[1].split("</ul>")[0]
                    assert "senior_referral" not in a or "Suggested market" in a
                    assert "not recorded for this earlier approval" in art(render(load_queue(), None), "SUB-906") or "Re-review needed" not in art(render(load_queue(), None), "SUB-906")
                finally:
                    for k, v in env_old.items():
                        os.environ.pop(k, None)
                        if v is not None:
                            os.environ[k] = v
            finally:
                (prepare.EXTRACT_DIR, prepare.INBOX_DIR, INBOX, LOG, PENDING, TO_PRODUCER, TO_CARRIER, package.DECISIONS_LOG, package.SENDS_LOG, package.INBOX, llm_extract._post, prepare.process_submission) = old

        # B-252 (D-069): a sandbox run writes only inside its temp directory; the real files' bytes stay the same.
        import hashlib

        real = [PAGE, package.DECISIONS_LOG, package.SENDS_LOG, quotes.CLOSURES, llm_extract.CACHE / "token_log.jsonl"]
        real_dirs = [PENDING, TO_PRODUCER, TO_CARRIER, prepare.EXTRACT_DIR]

        def fingerprint() -> dict:
            files = [f for f in real if f.is_file()] + [f for d in real_dirs if d.is_dir() for f in sorted(d.rglob("*")) if f.is_file()]
            return {str(f): hashlib.sha256(f.read_bytes()).hexdigest() for f in files} | {str(d): sorted(x.name for x in d.iterdir()) for d in real_dirs if d.is_dir()} | {f"exists {f}": f.is_file() for f in real}

        before_real = fingerprint()
        names = ("PAGE", "LOG", "INBOX", "PENDING", "TO_PRODUCER", "TO_CARRIER", "BANNER")
        saved_mod = {n: globals()[n] for n in names}
        saved_other = (package.DECISIONS_LOG, package.SENDS_LOG, package.INBOX, quotes.CLOSURES, quotes.TO_CARRIER, quotes.FROM_CARRIER, prepare.EXTRACT_DIR, prepare.INBOX_DIR, llm_extract.CACHE, pilot.CORRECTIONS, pilot.EVENTS)
        saved_audit = auth.AUDIT_LOG
        with tempfile.TemporaryDirectory() as box_dir:
            box_dir = Path(box_dir)
            try:
                sandbox(box_dir)
                assert PAGE.parent == box_dir and "SANDBOX COPY" in BANNER
                PAGE.write_text(render(load_queue(), correction_counts(LOG)))  # what serve() writes first
                sid = next(p.name for p in INBOX.iterdir() if p.name.startswith("SUB-") and (prepare.EXTRACT_DIR / f"{p.name}.json").is_file())
                act("/decision", {"submission": sid, "underwriter_id": "user", "action": "approve", "reason": "sandbox check"})
                act("/send", {"submission": sid, "user_line": f"send to carrier {sid}"})
                act("/close-subjectivity", {"submission": "SUB-002", "carrier": "carrier_b", "subjectivity": "x", "underwriter_id": "user", "reason": "sandbox check"})
                assert LOG.is_file() and (box_dir / "workbench.html").is_file() and "SANDBOX COPY" in PAGE.read_text()
            finally:
                for n, v in saved_mod.items():
                    globals()[n] = v
                (package.DECISIONS_LOG, package.SENDS_LOG, package.INBOX, quotes.CLOSURES, quotes.TO_CARRIER, quotes.FROM_CARRIER, prepare.EXTRACT_DIR, prepare.INBOX_DIR, llm_extract.CACHE, pilot.CORRECTIONS, pilot.EVENTS) = saved_other
                auth.AUDIT_LOG = saved_audit
        assert fingerprint() == before_real, "a sandbox run changed a real file"

        # P-066 regression (2026-10-20): REFUSED_AS was deleted while two uses stayed, so every refusal
        # raised NameError instead of a plain-words reason. This check fails if a refusal route has no
        # reason here, or if the set of POST routes and REFUSED_AS ever drift apart. Runs in a sandbox,
        # so nothing real is written.
        with tempfile.TemporaryDirectory() as ref_box:
            ref_box = Path(ref_box)
            try:
                sandbox(ref_box)
                posted = {"/confirm-market", "/decision", "/mark-code", "/cooking-call", "/close-subjectivity", "/send", "/approve-draft"}
                assert set(REFUSED_AS) == posted, ("refusal reasons and POST routes must match", set(REFUSED_AS) ^ posted)
                for ref_path, ref_reason in REFUSED_AS.items():
                    sub, ok, text = act(ref_path, {})  # an empty form is refused by every action
                    assert ok is False, (ref_path, "an empty form must be refused")
                    assert text.startswith(f"{ref_reason}: "), (ref_path, "plain-words reason missing", text)
            finally:
                for n, v in saved_mod.items():
                    globals()[n] = v
                (package.DECISIONS_LOG, package.SENDS_LOG, package.INBOX, quotes.CLOSURES, quotes.TO_CARRIER, quotes.FROM_CARRIER, prepare.EXTRACT_DIR, prepare.INBOX_DIR, llm_extract.CACHE, pilot.CORRECTIONS, pilot.EVENTS) = saved_other
                auth.AUDIT_LOG = saved_audit

        # P-075 (code review 4): a rule-copied cooking none-line, whatever its body, routes exactly as the value did before the copy.
        for body in sorted(prepare.COOKING_NONE_BODIES):
            line_ = f"Cooking operations: {body}"
            plain_row = {"field_id": "operations", "value": "Insurance agency office, 48 seats", "quote": "Operations: Insurance agency office, 48 seats"}
            copied_row = {**plain_row, "value": f"{plain_row['value']}; {line_}", "rule_copied": True, "also_quoted": [{"quote": line_, "source": "application.md"}]}
            assert _ops({"fields": [copied_row]}) == _ops({"fields": [plain_row]}) and _unlisted(_ops({"fields": [copied_row]})) == _unlisted(_ops({"fields": [plain_row]})), body
        print("workbench ok")
