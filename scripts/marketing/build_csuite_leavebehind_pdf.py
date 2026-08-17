#!/usr/bin/env python3
"""One-page PDF leave-behind for C-suite / investor meetings.

Output: marketing/assets/Rytera_CSuite_LeaveBehind.pdf

Usage:
  python scripts/marketing/build_csuite_leavebehind_pdf.py
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from csuite_deck_shared import (
    ASSETS,
    BASELINE_LABOR_MO,
    BASELINE_MIN,
    COMPANY_FY,
    FY1_NET,
    FY1_ROI,
    LOADED_UW_HR,
    QUARTERLY,
)

OUT_PDF = ASSETS / "Rytera_CSuite_LeaveBehind.pdf"
OUT_HTML = ASSETS / "_csuite_leavebehind_print.html"

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def build_html() -> str:
    today = date.today().strftime("%B %Y")
    q_rows = "".join(
        f"<tr><td>{r['q']}</td><td>{r['phase']}</td><td class='num'>{r['memos_mo']}</td>"
        f"<td class='num'>{r['min_saved']} min</td><td class='num'>${r['net_benefit_mo']:,.0f}</td>"
        f"<td class='num roi'>{r['roi_pct']:.0f}%</td></tr>"
        for r in QUARTERLY
    )
    fy3_arr = COMPANY_FY[2]["arr"]

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>Commercial Underwriting ROI — One-Page Summary</title>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet"/>
<style>
  @page {{ size: letter landscape; margin: 0.45in; }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: "IBM Plex Sans", sans-serif;
    font-size: 8.2pt;
    line-height: 1.35;
    color: #0b1524;
    margin: 0;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }}
  .page {{
    display: grid;
    grid-template-columns: 1.05fr 0.95fr;
    grid-template-rows: auto auto 1fr auto;
    gap: 10px 14px;
    height: 100%;
  }}
  header {{
    grid-column: 1 / -1;
    border-bottom: 2px solid #1a6f86;
    padding-bottom: 8px;
  }}
  h1 {{
    font-size: 17pt;
    margin: 0 0 4px;
    letter-spacing: -0.02em;
  }}
  .tagline {{ color: #5a6b7d; font-size: 9pt; margin: 0; }}
  .meta {{ float: right; text-align: right; font-size: 7.5pt; color: #5a6b7d; }}
  h2 {{
    font-size: 9.5pt;
    margin: 0 0 5px;
    color: #0e4a5c;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }}
  .box {{
    background: #f3f6f9;
    border: 1px solid #d0dae6;
    border-radius: 6px;
    padding: 8px 10px;
  }}
  .explain {{
    background: #e8f4f8;
    border-left: 3px solid #1a6f86;
    padding: 6px 10px;
    font-size: 7.8pt;
    color: #1e3044;
    margin-bottom: 6px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 7.6pt;
  }}
  th, td {{
    border: 1px solid #d0dae6;
    padding: 4px 6px;
    text-align: left;
  }}
  th {{ background: #0e4a5c; color: #fff; font-weight: 600; }}
  tr:nth-child(even) td {{ background: #fff; }}
  tr:nth-child(odd) td {{ background: #f8fafc; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .roi {{ font-weight: 700; color: #0d7a52; }}
  .stats {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 6px;
    margin: 6px 0;
  }}
  .stat {{
    background: #fff;
    border: 1px solid #d0dae6;
    border-radius: 5px;
    padding: 6px;
    text-align: center;
  }}
  .stat b {{ display: block; font-size: 11pt; color: #0e4a5c; }}
  .stat span {{ font-size: 6.8pt; color: #5a6b7d; }}
  ul {{ margin: 4px 0; padding-left: 14px; }}
  li {{ margin-bottom: 2px; }}
  footer {{
    grid-column: 1 / -1;
    font-size: 7pt;
    color: #5a6b7d;
    border-top: 1px solid #d0dae6;
    padding-top: 6px;
  }}
  .pill {{
    display: inline-block;
    background: #0e4a5c;
    color: #fff;
    font-size: 6.5pt;
    padding: 2px 6px;
    border-radius: 3px;
    margin-right: 4px;
  }}
</style>
</head>
<body>
<div class="page">
  <header>
    <div class="meta">{today}<br/>Confidential · Planning model labeled</div>
    <h1>Commercial underwriting that pays for itself</h1>
    <p class="tagline">B2B enterprise SaaS · Property · D&O · WC · Trade credit · E&O · Key person · Priced per bind-ready memo</p>
  </header>

  <section>
    <h2>What we are</h2>
    <div class="explain">
      <strong>Not B2C. Not premium share.</strong> Cloud workbench for carriers &amp; MGAs: broker package in →
      decision + quote worksheet + audit trail out. Licensed underwriter still signs. Bind optional in shadow pilot.
    </div>
    <div class="box">
      <p><span class="pill">B2B</span><span class="pill">Enterprise SaaS</span><span class="pill">Full-stack</span></p>
      <ul>
        <li><strong>Six live lines</strong> — each with correct exposure base (limit vs payroll vs TIV)</li>
        <li><strong>Fail closed</strong> — no fake CLUE/NCCI; their SERFF book on Desk+; Guidewire bind or refused</li>
        <li><strong>Pricing</strong> — Pilot $0 · Desk $799/mo · Book $2,490/mo · Enterprise from $6,500/mo</li>
      </ul>
    </div>
    <h2 style="margin-top:8px">Status quo cost (why they buy)</h2>
    <div class="stats">
      <div class="stat"><b>{BASELINE_MIN} min</b><span>Baseline first pass / file</span></div>
      <div class="stat"><b>${LOADED_UW_HR}/hr</b><span>Loaded UW cost</span></div>
      <div class="stat"><b>40 / mo</b><span>Typical desk volume</span></div>
      <div class="stat"><b>${BASELINE_LABOR_MO:,.0f}</b><span>Monthly first-pass labor</span></div>
    </div>
  </section>

  <section>
    <h2>Customer ROI — by quarter (year one)</h2>
    <div class="explain">
      <strong>Net/mo</strong> = (minutes saved × files × $175/hr) − software bill.
      <strong>ROI</strong> = net ÷ software cost. Planning model — replace with pilot KPIs at day 30.
    </div>
    <table>
      <thead>
        <tr><th>Q</th><th>Phase</th><th>Files</th><th>Saved</th><th>Net / mo</th><th>ROI</th></tr>
      </thead>
      <tbody>{q_rows}</tbody>
    </table>
    <div class="stats" style="margin-top:8px">
      <div class="stat"><b>{FY1_ROI:.0f}%</b><span>FY1 ROI on Desk</span></div>
      <div class="stat"><b>${FY1_NET:,.0f}</b><span>FY1 net profit to buyer</span></div>
      <div class="stat"><b>${QUARTERLY[3]["net_benefit_mo"]:,.0f}</b><span>Q4 net / mo</span></div>
      <div class="stat"><b>&lt; 25%</b><span>Override target d30</span></div>
    </div>
  </section>

  <section>
    <h2>How ROI is calculated</h2>
    <div class="box">
      <table>
        <tr><th>Line</th><th>Formula</th></tr>
        <tr><td>Labor value</td><td>min saved ÷ 60 × files/mo × ${LOADED_UW_HR}/hr × 12</td></tr>
        <tr><td>Software cost</td><td>Monthly plan + overage × 12</td></tr>
        <tr><td>Net profit</td><td>Labor value − software cost</td></tr>
        <tr><td>ROI %</td><td>Net profit ÷ software cost × 100</td></tr>
      </table>
    </div>
    <h2 style="margin-top:8px">Pilot success criteria</h2>
    <ul>
      <li>p95 first-pass cycle ≤ <strong>15 minutes</strong></li>
      <li>Override rate &lt; <strong>25%</strong> by day 30</li>
      <li>Missing-doc / conflict catch ≥ <strong>90%</strong></li>
    </ul>
  </section>

  <section>
    <h2>Company plan (investor — illustrative)</h2>
    <div class="explain">Replace with live pipeline when fundraising. Recurring SaaS + $15–40K onboarding.</div>
    <table>
      <thead><tr><th>FY</th><th>Customers</th><th>ARR</th><th>Gross margin</th></tr></thead>
      <tbody>
        <tr><td>FY1</td><td class="num">8</td><td class="num">${COMPANY_FY[0]["arr"]:,.0f}</td><td class="num">72%</td></tr>
        <tr><td>FY2</td><td class="num">22</td><td class="num">${COMPANY_FY[1]["arr"]:,.0f}</td><td class="num">78%</td></tr>
        <tr><td>FY3</td><td class="num">48</td><td class="num">${fy3_arr:,.0f}</td><td class="num">82%</td></tr>
      </tbody>
    </table>
    <h2 style="margin-top:8px">Next step</h2>
    <div class="box">
      <strong>Buyer:</strong> 30-day shadow pilot · your book · bind off · measured ROI<br/>
      <strong>Investor:</strong> 10-slide cut + full deck available<br/>
      <strong>Contact:</strong> hello@ryterainc.com · ryterainc.com/dashboard
    </div>
  </section>

  <footer>
    All ROI figures use planning assumptions ({BASELINE_MIN}-min baseline, ${LOADED_UW_HR}/hr loaded UW, published list pricing).
    Not a customer guarantee. Full deck: Rytera_CSuite_Investor_Deck.pptx
  </footer>
</div>
</body>
</html>"""


def build_pdf() -> Path:
    html = build_html()
    OUT_HTML.write_text(html, encoding="utf-8")
    ASSETS.mkdir(parents=True, exist_ok=True)

    from playwright.sync_api import sync_playwright

    chrome = CHROME if Path(CHROME).exists() else None
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=chrome)
        page = browser.new_page()
        page.goto(OUT_HTML.as_uri(), wait_until="networkidle")
        page.pdf(
            path=str(OUT_PDF),
            format="Letter",
            landscape=True,
            print_background=True,
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
        )
        browser.close()
    return OUT_PDF


if __name__ == "__main__":
    print(build_pdf())
