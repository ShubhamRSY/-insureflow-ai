#!/usr/bin/env python3
"""Build full C-suite / sales PowerPoint (18 slides, fixed layout + explanations).

Output: marketing/assets/Rytera_CSuite_Investor_Deck.pptx
Also see: build_csuite_leavebehind_pdf.py (1-page PDF leave-behind)
"""

from __future__ import annotations

from pathlib import Path

from csuite_deck_shared import (
    AMBER,
    ASSETS,
    BASELINE_LABOR_MO,
    BASELINE_MIN,
    BOOK_MO,
    BRAND,
    CARD,
    COMPANY_FY,
    CONTENT_W,
    CYAN,
    FISCAL_YEARS,
    FY1_COST,
    FY1_NET,
    FY1_RETURN,
    FY1_ROI,
    GREEN,
    LOADED_UW_HR,
    MARGIN_L,
    MUTED,
    QUARTERLY,
    QUARTERLY_EXPLAIN,
    RED,
    SOFT,
    VIOLET,
    WHITE,
    add_table,
    bar,
    blank_slide,
    explain_card,
    footer,
    new_presentation,
    notes,
    rect,
    slide_header,
    textbox,
)
from pptx.util import Inches

PPT_PATH = ASSETS / "Rytera_CSuite_Investor_Deck.pptx"


def build() -> Path:
    prs = new_presentation()
    total = 20
    n = 0

    def slide(accent=BRAND):
        nonlocal n
        n += 1
        return blank_slide(prs), n

    # ── 1 Title ─────────────────────────────────────────────────────────────
    s, i = slide()
    bar(s)
    textbox(s, Inches(0.7), Inches(1.35), Inches(11), Inches(0.32), "C-SUITE & INVESTOR BRIEFING", size=12, color=GREEN, bold=True)
    textbox(s, Inches(0.7), Inches(1.85), Inches(12), Inches(1.3), "Commercial underwriting\nthat pays for itself.", size=38, color=WHITE, bold=True)
    textbox(
        s,
        Inches(0.7),
        Inches(3.55),
        Inches(11.5),
        Inches(0.9),
        "Enterprise AI underwriting workbench for carriers & MGAs.\nProperty · D&O · Workers' comp · Trade credit · E&O · Key person.",
        size=17,
        color=SOFT,
    )
    textbox(
        s,
        Inches(0.7),
        Inches(4.65),
        Inches(11),
        Inches(0.55),
        "This deck shows what the buyer saves (by quarter & fiscal year) and how we charge.",
        size=14,
        color=MUTED,
    )
    footer(s, i, total)
    notes(s, "Open: 'What does one loaded underwriter hour cost you — and what if first pass took 15 minutes?'")

    # ── 2 Executive summary ─────────────────────────────────────────────────
    s, i = slide(GREEN)
    y = slide_header(
        s,
        kicker="Executive summary",
        title="The business in 60 seconds",
        subtitle="B2B enterprise SaaS — we sell software, not insurance.",
        explain="Buyers pay because each bind-ready memo replaces hours of PDF hunting, re-key, and audit prep. "
        f"Planning model: FY1 net ≈ ${FY1_NET:,.0f} ({FY1_ROI:.0f}% ROI on Desk) for a 40-file/mo specialty desk.",
    )
    bullets = [
        ("What we sell", "Cloud workbench: broker package in → decision, quote worksheet, audit trail out. Licensed UW still signs."),
        ("Who buys", "Carriers, MGAs, program managers — 15 to 120+ commercial submissions per month per line desk."),
        ("How we charge", "Monthly subscription + fee per memo (not a cut of premium). Pilot free; Desk from $799/mo."),
        ("Why now", "Messy specialty lines (D&O, WC, trade credit) cannot be priced with a generic chatbot or one building formula."),
    ]
    for j, (h, b) in enumerate(bullets):
        top = Inches(y + j * 1.22)
        rect(s, MARGIN_L, top, CONTENT_W, Inches(1.08), CARD)
        textbox(s, Inches(0.82), top + Inches(0.12), Inches(11.4), Inches(0.28), h, size=14, color=GREEN if j == 2 else BRAND, bold=True)
        textbox(s, Inches(0.82), top + Inches(0.42), Inches(11.4), Inches(0.58), b, size=12, color=SOFT)
    footer(s, i, total)

    # ── 3 Category ──────────────────────────────────────────────────────────
    s, i = slide()
    y = slide_header(
        s,
        kicker="Business model",
        title="Which box are we in?",
        explain="We are B2B enterprise SaaS delivered as a full-stack web app. Not B2C. Not internal tooling. Revenue = subscription + usage; we never take premium risk.",
    )
    matrix = [
        ("B2B", "Primary", "Software for carriers & MGAs to underwrite faster and more defensibly."),
        ("Enterprise SaaS", "Scale", "Multi-org, SSO/VPC, Guidewire bind, SERFF rate books, examiner export."),
        ("Full-stack web", "Shape", "React UI + API + agent pipeline — how we ship, not who pays."),
        ("B2C", "No", "We do not sell policies to consumers."),
    ]
    add_table(
        s,
        MARGIN_L,
        y,
        CONTENT_W,
        [["Category", "Role", "Plain-English meaning"], *matrix],
        col_fracs=[0.18, 0.14, 0.68],
        row_height=0.48,
    )
    footer(s, i, total)

    # ── 4 Problem ───────────────────────────────────────────────────────────
    s, i = slide(RED)
    y = slide_header(
        s,
        kicker="Problem",
        title="The desk bleeds time before it makes a decision",
        explain=f"ROI math starts here: {BASELINE_MIN}-minute first pass × 40 files/mo × ${LOADED_UW_HR}/hr loaded UW "
        f"= ${BASELINE_LABOR_MO:,.0f}/mo on first-pass labor alone — before rework, re-key, and exam packs.",
        accent=RED,
    )
    stats = [
        (f"{BASELINE_MIN} min", "Baseline first-pass time per file (planning assumption)"),
        (f"${LOADED_UW_HR}/hr", "Loaded UW cost (salary + benefits + overhead)"),
        ("40 / mo", "Typical specialty MGA desk volume"),
        (f"${BASELINE_LABOR_MO:,.0f}", "Monthly first-pass labor at baseline"),
    ]
    for j, (num, lbl) in enumerate(stats):
        x = MARGIN_L + Inches((j % 2) * 6.25)
        top = Inches(y + (j // 2) * 2.15)
        rect(s, x, top, Inches(5.95), Inches(1.95), CARD)
        textbox(s, x + Inches(0.28), top + Inches(0.28), Inches(5.4), Inches(0.55), num, size=26, color=RED if j == 3 else AMBER, bold=True)
        textbox(s, x + Inches(0.28), top + Inches(0.92), Inches(5.4), Inches(0.85), lbl, size=12, color=SOFT)
    footer(s, i, total)

    # ── 5 Product ───────────────────────────────────────────────────────────
    s, i = slide(GREEN)
    y = slide_header(
        s,
        kicker="Product",
        title="One pipeline — six live commercial lines",
        explain="Same journey for every line; different checklists and rating bases. D&O uses policy limit — not building TIV. WC uses payroll + e-mod. Property uses COPE + schedule of values.",
        accent=GREEN,
    )
    steps = ["Ingest", "Parse", "Verify", "Score", "Price", "Decide", "UW sign-off", "Bind*"]
    for j, step in enumerate(steps):
        x = Inches(0.42 + j * 1.58)
        rect(s, x, Inches(y), Inches(1.48), Inches(0.72), CARD)
        textbox(s, x + Inches(0.06), Inches(y + 0.18), Inches(1.36), Inches(0.4), step, size=11, color=GREEN if "sign" in step else BRAND, bold=True, align=1)
    y2 = y + 0.85
    lines = [
        ("Property & BI", "COPE, SOV, fire scenarios, business income worksheet"),
        ("D&O", "Governance, runway, Side A/B/C, claims-made continuity"),
        ("Workers' comp", "NCCI class codes, payroll, experience mod, OSHA logs"),
        ("Trade credit", "AR aging, buyer concentration, credit policy"),
        ("E&O", "Contract quality, scope creep, profession-specific apps"),
        ("Key person", "Face amount, medical, succession plan, corp resolution"),
    ]
    for j, (name, detail) in enumerate(lines):
        top = Inches(y2 + j * 0.72)
        textbox(s, Inches(0.75), top, Inches(2.2), Inches(0.55), name, size=12, color=GREEN, bold=True)
        textbox(s, Inches(2.95), top, Inches(9.5), Inches(0.55), detail, size=12, color=SOFT)
    textbox(s, MARGIN_L, Inches(6.55), CONTENT_W, Inches(0.3), "*Bind optional — shadow pilot keeps bind off until licensed UW cutover.", size=10, color=MUTED)
    footer(s, i, total)

    # ── 6 Differentiation ───────────────────────────────────────────────────
    s, i = slide(VIOLET)
    y = slide_header(
        s,
        kicker="Differentiation",
        title="Buyers pay when the data is real",
        explain="Desk-tier customers require three live connections: outside data (CLUE/NCCI), their filed rate book, "
        "and policy-system bind. Without those, we stay on Pilot — we do not fake production.",
        accent=VIOLET,
    )
    gates = [
        ("Fail closed", "Missing oracle → REFER. No invented clean loss history."),
        ("Their rates", "SERFF / carrier filings on Desk+. Not our demo book."),
        ("No re-key", "Full quote to Guidewire — or bind refused."),
        ("Line-correct", "Right exposure base per product (limit vs payroll vs TIV)."),
        ("Zero-token first", "Rules & rating before LLM. Works without API keys."),
        ("Examiner-ready", "Cited fields, encrypted audit, override analytics."),
    ]
    for j, (h, b) in enumerate(gates):
        x = MARGIN_L + Inches((j % 3) * 4.05)
        top = Inches(y + (j // 3) * 2.35)
        explain_card(s, x, top, Inches(3.9), Inches(2.15), h, b, VIOLET)
    footer(s, i, total)

    # ── 7 Pricing ───────────────────────────────────────────────────────────
    s, i = slide(BRAND)
    y = slide_header(
        s,
        kicker="Pricing",
        title="Aligned with how desks already think: files per month",
        explain="A 'memo' = one bind-ready underwriting package (decision + quote worksheet + audit). "
        "We do not take a % of premium. Oracle vendor fees pass through on Pilot/Desk; fair-use included on Book+.",
    )
    add_table(
        s,
        MARGIN_L,
        y,
        CONTENT_W,
        [
            ["Plan", "Monthly", "Memos incl.", "Overage", "Who it's for"],
            ["Pilot", "$0", "5", "$95 / memo", "Shadow pilot · bind off · prove ROI"],
            ["Desk", "$799", "25", "$55 / memo", "One line desk · 15–40 files / mo"],
            ["Book", "$2,490", "80", "$38 / memo", "Full book · 50–120 files / mo"],
            ["Enterprise", "from $6,500", "Custom", "$22–32", "100+ files · VPC · SSO · multi-org"],
        ],
        col_fracs=[0.14, 0.12, 0.12, 0.14, 0.48],
        row_height=0.46,
        right_cols={1, 3},
    )
    footer(s, i, total)

    # ── 8 Quarterly ROI table ─────────────────────────────────────────────────
    s, i = slide(GREEN)
    y = slide_header(
        s,
        kicker="Customer ROI",
        title="Year-one value by quarter (planning model)",
        subtitle="Typical specialty MGA desk ramp: shadow → Desk → Book",
        explain="Net benefit = (minutes saved × files × $175/hr) − software bill. ROI % = net benefit ÷ software cost. Replace with pilot measurements after day 30.",
        accent=GREEN,
    )
    q_rows = [["Q", "Phase", "Files", "Time saved", "Labor value", "SW cost", "Net / mo", "ROI"]]
    for r in QUARTERLY:
        q_rows.append(
            [
                r["q"],
                r["phase"],
                str(r["memos_mo"]),
                f"{r['min_saved']} min",
                f"${r['labor_saved_mo']:,.0f}",
                f"${r['software_mo']:,.0f}",
                f"${r['net_benefit_mo']:,.0f}",
                f"{r['roi_pct']:.0f}%",
            ]
        )
    bottom = add_table(
        s,
        MARGIN_L,
        y,
        CONTENT_W,
        q_rows,
        col_fracs=[0.06, 0.16, 0.08, 0.11, 0.14, 0.13, 0.14, 0.18],
        row_height=0.4,
        font_size=10,
        right_cols={2, 3, 4, 5, 6, 7},
    )
    textbox(
        s,
        MARGIN_L,
        Inches(bottom + 0.08),
        CONTENT_W,
        Inches(0.55),
        f"Baseline: {BASELINE_MIN}-min first pass. 'Time saved' = baseline minus measured first-pass after platform. Planning model — not a guarantee.",
        size=10,
        color=MUTED,
    )
    footer(s, i, total)

    # ── 9 Quarterly explanations ──────────────────────────────────────────────
    s, i = slide(GREEN)
    y = slide_header(
        s,
        kicker="Customer ROI",
        title="What each quarter means in practice",
        explain="Use this slide when a CFO asks 'where does the 400% ROI come from?' Walk Q1→Q4 left to right.",
        accent=GREEN,
    )
    for j, r in enumerate(QUARTERLY):
        x = MARGIN_L + Inches((j % 2) * 6.15)
        top = Inches(y + (j // 2) * 2.55)
        explain_card(
            s,
            x,
            top,
            Inches(5.95),
            Inches(2.35),
            f"{r['q']} · {r['phase']} · ROI {r['roi_pct']:.0f}%",
            f"{QUARTERLY_EXPLAIN[r['q']]}\n\nFiles: {r['memos_mo']}/mo · Saves {r['min_saved']} min/file · Net ${r['net_benefit_mo']:,.0f}/mo after ${r['software_mo']:,.0f} software.",
            GREEN,
        )
    footer(s, i, total)

    # ── 10 Fiscal years ───────────────────────────────────────────────────────
    s, i = slide(GREEN)
    y = slide_header(
        s,
        kicker="Customer ROI",
        title="Three-year view — cumulative profit to the buyer",
        explain="As volume grows and cycle time drops, net profit compounds. FY2–3 assume Book tier and higher file counts — still one specialty desk, not enterprise-wide.",
        accent=GREEN,
    )
    fy_rows = [["Year", "Files / mo", "Cycle ↓", "Labor value (yr)", "SW cost (yr)", "Net profit", "ROI"]]
    for fy in FISCAL_YEARS:
        fy_rows.append(
            [
                fy["fy"],
                str(fy["memos_mo"]),
                f"{fy['pct_cycle_cut']}%",
                f"${fy['return_usd']:,.0f}",
                f"${fy['cost_usd']:,.0f}",
                f"${fy['net_usd']:,.0f}",
                f"{fy['roi_pct']:.0f}%",
            ]
        )
    bottom = add_table(
        s,
        MARGIN_L,
        y,
        CONTENT_W,
        fy_rows,
        col_fracs=[0.08, 0.11, 0.1, 0.18, 0.16, 0.17, 0.2],
        row_height=0.44,
        font_size=10,
        right_cols={1, 2, 3, 4, 5, 6},
    )
    cards = [
        (f"{FY1_ROI:.0f}%", "FY1 ROI", "Return on software spend"),
        (f"${FY1_NET:,.0f}", "FY1 net $", "Labor saved minus Desk bill"),
        ("< 25%", "Override", "UW agrees with AI by day 30"),
        ("≤ 15 min", "Cycle p95", "First-pass target"),
    ]
    for j, (num, title, sub) in enumerate(cards):
        x = MARGIN_L + Inches(j * 3.05)
        top = Inches(bottom + 0.2)
        rect(s, x, top, Inches(2.85), Inches(1.55), CARD)
        textbox(s, x + Inches(0.12), top + Inches(0.18), Inches(2.6), Inches(0.45), num, size=22, color=GREEN, bold=True, align=1)
        textbox(s, x + Inches(0.12), top + Inches(0.68), Inches(2.6), Inches(0.28), title, size=12, color=WHITE, bold=True, align=1)
        textbox(s, x + Inches(0.12), top + Inches(0.98), Inches(2.6), Inches(0.45), sub, size=10, color=MUTED, align=1)
    footer(s, i, total)

    # ── 11 Strategic gains ────────────────────────────────────────────────────
    s, i = slide(CYAN)
    y = slide_header(
        s,
        kicker="Beyond labor",
        title="Book-quality gains (pilot KPI targets)",
        explain="Labor ROI is the easy math. These metrics protect loss ratio and exam outcomes — measure them in every shadow pilot before you claim them in a renewal conversation.",
        accent=CYAN,
    )
    strategic = [
        ("≥ 30%", "Straight-through", "Clean Accept path without unnecessary refer — frees senior UW for hard files."),
        ("≥ 90%", "Catch rate", "Missing docs & cross-file conflicts flagged before bind."),
        ("< 25%", "Override rate", "Licensed UW agrees with AI recommendation by day 30."),
        ("5–10%", "Win rate (upside)", "Faster quote turnaround on competitive submissions — measure in pilot."),
        ("1–3 pts", "Loss ratio (upside)", "Appetite gates + early decline over 12–24 mo — book-dependent."),
    ]
    add_table(
        s,
        MARGIN_L,
        y,
        CONTENT_W,
        [["Target", "Metric", "Why it matters to the C-suite"], *[(a, b, c) for a, b, c in strategic]],
        col_fracs=[0.12, 0.18, 0.70],
        row_height=0.46,
    )
    footer(s, i, total)

    # ── 12 Market ─────────────────────────────────────────────────────────────
    s, i = slide()
    y = slide_header(
        s,
        kicker="Market",
        title="Beachhead → expand on one platform",
        explain="Start with specialty MGAs drowning in PDFs (15–120 files/mo). Expand to regional carriers. Same intake spine later adds mortgage & lending for higher ACV per logo.",
    )
    for j, (tier, head, sub) in enumerate(
        [
            ("Beachhead", "~2,400 US MGAs & program managers", "Property, WC, D&O, credit lines"),
            ("Expand", "Regional carriers & specialty units", "Examiner pressure, Guidewire estates"),
            ("Platform", "Mortgage + lending modules", "One contract, three verticals"),
        ]
    ):
        top = Inches(y + j * 1.55)
        rect(s, MARGIN_L, top, CONTENT_W, Inches(1.38), CARD)
        textbox(s, Inches(0.82), top + Inches(0.14), Inches(2.0), Inches(0.32), tier, size=14, color=BRAND, bold=True)
        textbox(s, Inches(0.82), top + Inches(0.48), Inches(11.2), Inches(0.35), head, size=16, color=WHITE, bold=True)
        textbox(s, Inches(0.82), top + Inches(0.88), Inches(11.2), Inches(0.35), sub, size=12, color=MUTED)
    footer(s, i, total)

    # ── 13 GTM ────────────────────────────────────────────────────────────────
    s, i = slide(AMBER)
    y = slide_header(
        s,
        kicker="Go-to-market",
        title="Land with shadow. Expand with bind.",
        explain="Free Pilot proves ROI on their book with bind off. Desk is first revenue. Book adds Guidewire + portfolio. Enterprise is annual VPC contract.",
        accent=AMBER,
    )
    gtm = [
        ("1 · Shadow (free)", "20–50 redacted files · 30 days · measure override & cycle · bind off"),
        ("2 · Desk ($799/mo)", "Live oracles + SERFF book · 25 memos · first paid conversion"),
        ("3 · Book ($2,490/mo)", "Guidewire bind · 80 memos · onboarding included"),
        ("4 · Enterprise ($6,500+)", "VPC · SSO · multi-org · broker portal · annual"),
    ]
    for j, (h, b) in enumerate(gtm):
        top = Inches(y + j * 1.22)
        rect(s, MARGIN_L, top, CONTENT_W, Inches(1.05), CARD)
        textbox(s, Inches(0.82), top + Inches(0.14), Inches(11.2), Inches(0.32), h, size=14, color=AMBER, bold=True)
        textbox(s, Inches(0.82), top + Inches(0.48), Inches(11.2), Inches(0.48), b, size=12, color=SOFT)
    footer(s, i, total)

    # ── 14 Company revenue ────────────────────────────────────────────────────
    s, i = slide(BRAND)
    y = slide_header(
        s,
        kicker="Company revenue (investor)",
        title="Our ARR plan — illustrative",
        explain="Replace with live pipeline when fundraising. Revenue = recurring SaaS + one-time onboarding ($15–40K). Not a forecast guarantee.",
    )
    rev_rows = [["Year", "Customers", "Avg MRR", "ARR", "Gross margin"]]
    for c in COMPANY_FY:
        rev_rows.append([c["fy"], str(c["customers"]), f"${c['avg_mrr']:,.0f}", f"${c['arr']:,.0f}", f"{c['gm_pct']}%"])
    bottom = add_table(
        s,
        MARGIN_L,
        y,
        CONTENT_W,
        rev_rows,
        col_fracs=[0.12, 0.14, 0.18, 0.22, 0.34],
        row_height=0.44,
        font_size=10,
        right_cols={1, 2, 3, 4},
    )
    chart_y = bottom + 0.35
    max_arr = max(c["arr"] for c in COMPANY_FY)
    for j, c in enumerate(COMPANY_FY):
        x = Inches(1.5 + j * 3.6)
        h_in = 1.6 * (c["arr"] / max_arr)
        bar_top = chart_y + 1.65 - h_in
        rect(s, x, Inches(bar_top), Inches(2.4), Inches(h_in), GREEN if j == 2 else BRAND)
        textbox(s, x, Inches(bar_top - 0.32), Inches(2.4), Inches(0.28), f"${c['arr'] / 1000:.0f}K ARR", size=11, color=WHITE, bold=True, align=1)
        textbox(s, x, Inches(chart_y + 1.72), Inches(2.4), Inches(0.25), c["fy"], size=10, color=MUTED, align=1)
    footer(s, i, total)

    # ── 15 Unit economics ─────────────────────────────────────────────────────
    s, i = slide()
    y = slide_header(
        s,
        kicker="Unit economics",
        title="One Book customer at 80 memos / month",
        explain="LTV:CAC assumes $18K blended CAC and 36-month retention at Book list price. Payback < 6 months because ACV is high relative to cloud + token cost (zero-token architecture).",
    )
    ltv_cac = round(BOOK_MO * 36 / 18_000, 1)
    ue = [
        (f"${BOOK_MO:,.0f}", "MRR · Book list"),
        (f"${BOOK_MO * 12:,.0f}", "ACV"),
        (f"{ltv_cac}x", "LTV : CAC"),
        ("78%", "Gross margin at scale"),
        ("< 6 mo", "CAC payback"),
        ("36 mo", "Retention assumption"),
    ]
    for j, (num, lbl) in enumerate(ue):
        x = MARGIN_L + Inches((j % 3) * 4.05)
        top = Inches(y + (j // 3) * 2.35)
        rect(s, x, top, Inches(3.9), Inches(2.1), CARD)
        textbox(s, x + Inches(0.15), top + Inches(0.35), Inches(3.6), Inches(0.5), num, size=24, color=BRAND, bold=True, align=1)
        textbox(s, x + Inches(0.15), top + Inches(1.0), Inches(3.6), Inches(0.75), lbl, size=11, color=MUTED, align=1)
    footer(s, i, total)

    # ── 16 Moat ───────────────────────────────────────────────────────────────
    s, i = slide(VIOLET)
    y = slide_header(
        s,
        kicker="Moat",
        title="Hard to copy because trust and workflow lock in",
        explain="Generic LLM wrappers cannot pass an exam or price six different exposure bases correctly. PAS bind + override loop creates retention after go-live.",
        accent=VIOLET,
    )
    for j, m in enumerate(
        [
            "Line-specific rating & checklists — not one model for every product",
            "Fail-closed posture — buyers leave vendors that fake oracle data",
            "Citation gates & encrypted audit — examiner-grade, not chat",
            "Guidewire / BriteCore payload — workflow lock-in",
            "Override feedback — book learns from licensed UW decisions",
        ]
    ):
        textbox(s, Inches(0.75), Inches(y + j * 0.95), Inches(11.8), Inches(0.85), f"{j + 1}.  {m}", size=14, color=SOFT)
    footer(s, i, total)

    # ── 17 Pilot KPIs ─────────────────────────────────────────────────────────
    s, i = slide(GREEN)
    y = slide_header(
        s,
        kicker="Proof",
        title="Every pilot replaces projections with measured KPIs",
        explain="Agree these success criteria in week 1. If override > 25% or cycle > 15 min p95 at day 30, we fix — not hand-wave.",
        accent=GREEN,
    )
    add_table(
        s,
        MARGIN_L,
        y,
        CONTENT_W,
        [
            ["KPI", "Target", "What it tells the C-suite"],
            ["Cycle time (p95)", "≤ 15 min", "Desk capacity unlocked — labor ROI is real"],
            ["Override rate", "< 25%", "AI recommendations match UW judgment"],
            ["Bind after Accept", "≥ 40%", "Memo quality converts to bound premium"],
            ["Catch rate", "≥ 90%", "Fewer bound-with-holes policies"],
            ["ROI", "Measured", "(Labor saved − SW cost) ÷ SW cost — use their loaded UW rate"],
        ],
        col_fracs=[0.2, 0.14, 0.66],
        row_height=0.46,
    )
    footer(s, i, total)

    # ── 18 CTA ────────────────────────────────────────────────────────────────
    s, i = slide(BRAND)
    y = slide_header(
        s,
        kicker="Next step",
        title="30 minutes. Your book. Shadow on.",
        explain=f"Buyer: 30-day shadow pilot · planning FY1 ROI {FY1_ROI:.0f}%. Investor: swap illustrative ARR for pipeline deck.",
    )
    for j, (who, what) in enumerate(
        [
            ("Buyer", "Bring 3 messy commercial files. We measure cycle, override, and net $ on your loaded UW rate."),
            ("Investor", "Seed for GTM: 2 AEs, 1 solutions engineer, SOC2 Type I."),
            ("Either", "Leave with a labeled ROI model — not a promise we cannot defend."),
        ]
    ):
        top = Inches(y + j * 1.35)
        rect(s, MARGIN_L, top, CONTENT_W, Inches(1.18), CARD)
        textbox(s, Inches(0.82), top + Inches(0.16), Inches(2.2), Inches(0.35), who, size=14, color=BRAND, bold=True)
        textbox(s, Inches(3.1), top + Inches(0.16), Inches(9.2), Inches(0.85), what, size=13, color=SOFT)
    footer(s, i, total)

    # ── 19 Formula reference ──────────────────────────────────────────────────
    s, i = slide()
    y = slide_header(
        s,
        kicker="Appendix",
        title="How every dollar in this deck is calculated",
        explain="Use this when finance pushes back. All inputs are labeled; change loaded UW rate or baseline minutes in the model.",
    )
    add_table(
        s,
        MARGIN_L,
        y,
        CONTENT_W,
        [
            ["Line item", "Formula", "Example (Desk, 40 files/mo)"],
            ["Labor value", "min saved ÷ 60 × files × $175/hr × 12", f"75 min → ${FY1_RETURN:,.0f}/yr"],
            ["Software cost", "Monthly plan + overage × 12", f"${FY1_COST:,.0f}/yr"],
            ["Net profit", "Labor value − software cost", f"${FY1_NET:,.0f}/yr"],
            ["ROI %", "Net profit ÷ software cost × 100", f"{FY1_ROI:.0f}%"],
        ],
        col_fracs=[0.18, 0.42, 0.40],
        row_height=0.48,
    )
    footer(s, i, total)

    # ── 20 Q&A ────────────────────────────────────────────────────────────────
    s, i = slide()
    textbox(s, Inches(0.7), Inches(1.45), Inches(12), Inches(0.35), "DISCUSSION", size=12, color=BRAND, bold=True)
    textbox(s, Inches(0.7), Inches(1.95), Inches(12), Inches(0.85), "Your book. Your numbers.", size=34, color=WHITE, bold=True)
    rect(s, Inches(0.7), Inches(3.1), Inches(11.9), Inches(3.2), CARD)
    textbox(
        s,
        Inches(1.0),
        Inches(3.35),
        Inches(11.3),
        Inches(2.7),
        f"Planning model recap\n\n"
        f"FY1 customer net: ${FY1_NET:,.0f} ({FY1_ROI:.0f}% ROI on Desk)\n"
        f"Q4 net benefit: ${QUARTERLY[3]['net_benefit_mo']:,.0f}/mo\n"
        f"Company FY3 illustrative ARR: ${COMPANY_FY[2]['arr']:,.0f}\n\n"
        "Swap projections for pilot KPIs when available.\n"
        "hello@ryterainc.com · ryterainc.com",
        size=15,
        color=SOFT,
    )
    footer(s, i, total)

    PPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    prs.save(PPT_PATH)
    return PPT_PATH


if __name__ == "__main__":
    print(build())
