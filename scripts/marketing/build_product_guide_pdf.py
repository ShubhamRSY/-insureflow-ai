#!/usr/bin/env python3
"""Build a designed PRODUCT_GUIDE.pdf for sharing with prospects / pilots.

Usage:
  python scripts/marketing/build_product_guide_pdf.py
"""

from __future__ import annotations

import base64
import mimetypes
from datetime import date
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "docs" / "product"
SHOTS = PRODUCT / "screenshots"
OUT_PDF = PRODUCT / "PRODUCT_GUIDE.pdf"
OUT_HTML = PRODUCT / "_product_guide_print.html"

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    raw = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{raw}"


def build_html() -> str:
    icon = data_uri(SHOTS / "00_icon.png")
    overview = data_uri(SHOTS / "01_overview.png")
    insurance = data_uri(SHOTS / "02_insurance.png")
    journey = data_uri(SHOTS / "03_submission_journey.png")
    queue = data_uri(SHOTS / "04_queue.png")
    today = date.today().strftime("%B %Y")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>Rytera — Application Guide</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet"/>
<style>
  :root {{
    --ink: #0b1524;
    --ink-soft: #1e3044;
    --muted: #5a6b7d;
    --line: #d0dae6;
    --paper: #f3f6f9;
    --white: #ffffff;
    --sea: #1a6f86;
    --sea-deep: #0e4a5c;
    --sea-bright: #2a9bb0;
    --fog: #e4ecf3;
    --sand: #efe9e0;
    --signal: #c9782c;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{
    margin: 0; padding: 0;
    color: var(--ink);
    background: var(--white);
    font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
    font-size: 9.8pt;
    line-height: 1.48;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }}
  h1, h2, .display {{
    font-family: "Libre Baskerville", Georgia, serif;
    font-weight: 400;
    letter-spacing: -0.015em;
    color: var(--ink);
  }}
  h2 {{
    font-size: 15pt;
    margin: 0 0 0.4em;
    padding-bottom: 0.28em;
    border-bottom: 1.5px solid var(--line);
  }}
  h3 {{
    font-family: "IBM Plex Sans", sans-serif;
    font-size: 10pt;
    font-weight: 700;
    margin: 0 0 0.2em;
    color: var(--sea-deep);
    letter-spacing: 0.01em;
  }}
  p {{ margin: 0 0 0.55em; }}
  a {{ color: var(--sea); text-decoration: none; }}
  .muted {{ color: var(--muted); }}
  .page {{
    page-break-after: always;
    position: relative;
    width: 8.5in;
    height: 11in;
    overflow: hidden;
  }}
  .page:last-child {{ page-break-after: auto; }}

  /* —— Cover —— */
  .cover {{
    background:
      radial-gradient(ellipse 80% 55% at 110% -10%, rgba(42,155,176,0.4), transparent 55%),
      radial-gradient(ellipse 60% 45% at -20% 110%, rgba(14,74,92,0.55), transparent 50%),
      linear-gradient(158deg, #050c14 0%, #0b1524 42%, #143047 100%);
    color: #e8eef4;
    padding: 0.7in 0.65in 0.55in;
    display: flex;
    flex-direction: column;
  }}
  .cover-top {{
    display: flex;
    align-items: center;
    justify-content: space-between;
  }}
  .brand-row {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }}
  .cover-top img.icon {{
    width: 40px; height: 40px; border-radius: 8px;
  }}
  .cover-mark {{
    font-weight: 700;
    font-size: 12pt;
    letter-spacing: 0.12em;
  }}
  .cover-mark span {{ color: #7eb8c9; font-weight: 500; letter-spacing: 0.18em; font-size: 9pt; }}
  .cover-edition {{
    font-size: 8pt;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #8fa3b8;
  }}
  .cover-hero {{
    margin-top: 0.85in;
    max-width: 6.4in;
  }}
  .cover-kicker {{
    font-size: 8.5pt;
    font-weight: 700;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: #7eb8c9;
    margin-bottom: 0.65em;
  }}
  .cover h1 {{
    color: #f7fafc;
    font-size: 36pt;
    line-height: 1.08;
    margin: 0 0 0.4em;
  }}
  .cover-lead {{
    font-size: 11.5pt;
    line-height: 1.5;
    color: #b8c9d8;
    max-width: 5.8in;
    margin: 0;
  }}
  .cover-stats {{
    display: flex;
    gap: 0.9em;
    margin-top: 0.85em;
  }}
  .cover-stat {{
    border-left: 2px solid var(--sea-bright);
    padding-left: 0.55em;
  }}
  .cover-stat b {{
    display: block;
    font-size: 13pt;
    color: #fff;
    font-weight: 650;
  }}
  .cover-stat span {{
    font-size: 8pt;
    color: #8fa3b8;
    letter-spacing: 0.04em;
  }}
  .cover-visual {{
    margin-top: auto;
    border-radius: 6px;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,0.14);
    box-shadow: 0 28px 56px rgba(0,0,0,0.45);
    max-height: 4.55in;
  }}
  .cover-visual img {{
    display: block; width: 100%; height: 4.55in; object-fit: cover; object-position: top left;
  }}
  .cover-foot {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 8.5pt;
    color: #8fa3b8;
    margin-top: 0.55em;
    padding-top: 0.45em;
    border-top: 1px solid rgba(255,255,255,0.12);
  }}

  /* —— Interior —— */
  .inner {{
    padding: 0.58in 0.62in 0.5in;
    background:
      linear-gradient(180deg, #f7f9fb 0%, #ffffff 18%);
    height: 100%;
  }}
  .sec-label {{
    font-size: 7.5pt;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--sea);
    margin-bottom: 0.25em;
  }}
  .lead {{
    font-size: 10.5pt;
    line-height: 1.5;
    color: var(--ink-soft);
    margin-bottom: 0.75em;
  }}
  .callout {{
    background: linear-gradient(90deg, #e8f3f6, var(--fog));
    border-left: 3px solid var(--sea);
    padding: 0.55em 0.75em;
    margin: 0 0 0.9em;
    font-size: 9.3pt;
  }}
  .callout strong {{ color: var(--sea-deep); }}

  .pipeline {{
    display: grid;
    grid-template-columns: repeat(8, 1fr);
    gap: 0.28rem;
    margin: 0.55em 0 0.75em;
  }}
  .pipe-step {{
    background: var(--ink);
    color: #e8eef4;
    border-radius: 3px;
    padding: 0.4em 0.35em;
    text-align: center;
  }}
  .pipe-n {{
    font-size: 6.5pt;
    font-weight: 700;
    letter-spacing: 0.06em;
    color: var(--sea-bright);
    margin-bottom: 0.1em;
  }}
  .pipe-t {{
    font-weight: 600;
    font-size: 8pt;
  }}

  table.clean {{
    width: 100%;
    border-collapse: collapse;
    margin: 0.35em 0 0.75em;
    font-size: 8.8pt;
  }}
  table.clean th {{
    text-align: left;
    background: var(--ink);
    color: #e8eef4;
    font-weight: 600;
    padding: 0.38em 0.5em;
  }}
  table.clean td {{
    padding: 0.38em 0.5em;
    border-bottom: 1px solid var(--line);
    vertical-align: top;
  }}
  table.clean tr:nth-child(even) td {{ background: var(--paper); }}

  .demo-block {{
    margin: 0 0 0.7em;
    page-break-inside: avoid;
  }}
  .demo-head {{
    display: flex;
    align-items: baseline;
    gap: 0.55em;
    margin-bottom: 0.25em;
  }}
  .demo-num {{
    font-family: "Libre Baskerville", Georgia, serif;
    font-size: 18pt;
    color: var(--sea);
    line-height: 1;
  }}
  .talk {{
    font-size: 8.5pt;
    color: var(--muted);
    font-style: italic;
    margin: 0 0 0.35em;
  }}
  .figure-frame {{
    background: var(--ink);
    padding: 3px;
    border-radius: 4px;
    overflow: hidden;
  }}
  .figure-frame img {{
    display: block;
    width: 100%;
    height: 3.15in;
    object-fit: cover;
    object-position: top left;
  }}
  .figure-frame.tall img {{ height: 3.45in; }}
  .cap {{
    margin-top: 0.28em;
    font-size: 8.3pt;
    color: var(--muted);
  }}
  .cap strong {{ color: var(--ink); font-weight: 650; }}

  .two-col {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.55em;
    margin: 0.45em 0 0.7em;
  }}
  .card {{
    background: var(--paper);
    border: 1px solid var(--line);
    border-radius: 4px;
    padding: 0.55em 0.65em;
  }}
  .card p:last-child {{ margin-bottom: 0; font-size: 9pt; }}

  .kpi-row {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.45em;
    margin: 0.5em 0 0.85em;
  }}
  .kpi {{
    background: var(--sand);
    border-radius: 4px;
    padding: 0.5em 0.55em;
  }}
  .kpi b {{
    display: block;
    font-size: 12pt;
    color: var(--sea-deep);
    font-weight: 700;
  }}
  .kpi span {{
    font-size: 7.8pt;
    color: var(--muted);
  }}

  ol.demo {{
    margin: 0.25em 0 0;
    padding-left: 1.15em;
  }}
  ol.demo li {{ margin-bottom: 0.28em; }}

  .trust-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.35em 0.65em;
    margin: 0.4em 0 0.7em;
  }}
  .trust-item {{
    padding: 0.45em 0.55em;
    background: var(--fog);
    border-radius: 3px;
    font-size: 8.8pt;
  }}
  .trust-item strong {{
    display: block;
    font-size: 8pt;
    color: var(--sea-deep);
    margin-bottom: 0.1em;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }}

  .footer-note {{
    margin-top: 0.7em;
    padding-top: 0.45em;
    border-top: 1px solid var(--line);
    font-size: 8pt;
    color: var(--muted);
  }}
  .page-num {{
    position: absolute;
    bottom: 0.32in;
    right: 0.62in;
    font-size: 8pt;
    color: var(--muted);
  }}
</style>
</head>
<body>

<!-- COVER -->
<section class="page cover">
  <div class="cover-top">
    <div class="brand-row">
      <img class="icon" src="{icon}" alt="Rytera"/>
      <div class="cover-mark">RYTERA <span>INC</span></div>
    </div>
    <div class="cover-edition">Pilot / demo edition</div>
  </div>
  <div class="cover-hero">
    <div class="cover-kicker">Application guide</div>
    <h1>Underwriting you<br/>can inspect</h1>
    <p class="cover-lead">
      Rytera runs commercial insurance, mortgage, and lending packages through
      specialist agents — then puts a licensed human on the decision. Full journey.
      Shadow bind. No black box.
    </p>
    <div class="cover-stats">
      <div class="cover-stat"><b>3</b><span>verticals</span></div>
      <div class="cover-stat"><b>HITL</b><span>sign-off required</span></div>
      <div class="cover-stat"><b>30-day</b><span>shadow pilot shape</span></div>
    </div>
  </div>
  <div class="cover-visual">
    <img src="{overview}" alt="Rytera overview"/>
  </div>
  <div class="cover-foot">
    <div>ryterainc.com · hello@ryterainc.com</div>
    <div>{today}</div>
  </div>
</section>

<!-- WHAT + FLOW -->
<section class="page inner">
  <div class="sec-label">01 — Product</div>
  <h2>What Rytera is</h2>
  <p class="lead">
    An AI underwriting workbench. It takes a messy submission, runs agents and data
    oracles, and returns a structured recommendation — decision, findings, pricing
    indication — for a <strong>licensed underwriter</strong> to accept, override, or refer.
  </p>
  <div class="callout">
    <strong>Shadow by design.</strong>
    Analysis and UW sign-off stay on in pilot mode. Live bind stays off until your
    PAS and policy allow it — so you can judge quality without production risk.
  </div>

  <div class="kpi-row">
    <div class="kpi"><b>&lt; 15 min</b><span>target time-to-first UW review</span></div>
    <div class="kpi"><b>&lt; 25%</b><span>override rate goal by day 30</span></div>
    <div class="kpi"><b>Fail-closed</b><span>when required feeds are missing</span></div>
  </div>

  <div class="sec-label">02 — Audience</div>
  <h2>Who opens it</h2>
  <table class="clean">
    <thead><tr><th>Audience</th><th>What they get</th></tr></thead>
    <tbody>
      <tr><td><strong>Carrier / MGA underwriters</strong></td><td>Faster first pass on commercial packages — with every layer visible</td></tr>
      <tr><td><strong>Pilot / product owners</strong></td><td>Shadow-run a redacted book and measure override rate against your book</td></tr>
      <tr><td><strong>Ops / risk</strong></td><td>PII redaction, encrypted audits, org-scoped access</td></tr>
    </tbody>
  </table>

  <div class="sec-label">03 — Pipeline</div>
  <h2>How a submission moves</h2>
  <p class="muted" style="margin-top:-0.15em;margin-bottom:0.35em">Same spine across insurance, mortgage, and lending.</p>
  <div class="pipeline">
    <div class="pipe-step"><div class="pipe-n">01</div><div class="pipe-t">Intake</div></div>
    <div class="pipe-step"><div class="pipe-n">02</div><div class="pipe-t">Parse</div></div>
    <div class="pipe-step"><div class="pipe-n">03</div><div class="pipe-t">Verify</div></div>
    <div class="pipe-step"><div class="pipe-n">04</div><div class="pipe-t">Score</div></div>
    <div class="pipe-step"><div class="pipe-n">05</div><div class="pipe-t">Price</div></div>
    <div class="pipe-step"><div class="pipe-n">06</div><div class="pipe-t">Decide</div></div>
    <div class="pipe-step"><div class="pipe-n">07</div><div class="pipe-t">HITL</div></div>
    <div class="pipe-step"><div class="pipe-n">08</div><div class="pipe-t">Bind*</div></div>
  </div>
  <table class="clean">
    <thead><tr><th>Stage</th><th>In practice</th></tr></thead>
    <tbody>
      <tr><td><strong>Intake</strong></td><td>Upload, folder drop, email/IMAP, S3, or one-click demos</td></tr>
      <tr><td><strong>Parse</strong></td><td>ACORD, loss runs, SOV, inspections — or mortgage &amp; lending docs</td></tr>
      <tr><td><strong>Verify</strong></td><td>Cross-doc reconciliation + oracles (CLUE, A-PLUS, NCCI, CAT when keyed)</td></tr>
      <tr><td><strong>Score → Price</strong></td><td>Multi-agent risk + indicated premium / rate / loan pricing</td></tr>
      <tr><td><strong>Decide + HITL</strong></td><td>Accept / conditional / refer / decline — then licensed UW sign-off</td></tr>
    </tbody>
  </table>
  <p class="muted">* Bind is optional and blocked in shadow / pilot until PAS is live.</p>
  <div class="page-num">2</div>
</section>

<!-- DEMO 1-2 -->
<section class="page inner">
  <div class="sec-label">04 — Demo path</div>
  <h2>What to show</h2>
  <p class="lead">Marketing site for the story. Dashboard for proof. Walk these four screens.</p>

  <div class="demo-block">
    <div class="demo-head">
      <div class="demo-num">01</div>
      <div>
        <h3>Overview</h3>
        <p class="talk">“Here’s the pulse — what’s running, what’s waiting on UW.”</p>
      </div>
    </div>
    <div class="figure-frame"><img src="{overview}" alt="Overview"/></div>
    <p class="cap"><strong>Job counts, market cycle, queue, demos.</strong> Answer “what’s running?” in under a minute.</p>
  </div>

  <div class="demo-block">
    <div class="demo-head">
      <div class="demo-num">02</div>
      <div>
        <h3>Insurance workspace</h3>
        <p class="talk">“We drop a package — or run a sample — and the job lands with a journey strip.”</p>
      </div>
    </div>
    <div class="figure-frame"><img src="{insurance}" alt="Insurance"/></div>
    <p class="cap"><strong>Commercial P&amp;C workbench.</strong> Samples, custom uploads, then open a row into the full journey.</p>
  </div>
  <div class="page-num">3</div>
</section>

<!-- DEMO 3-4 -->
<section class="page inner">
  <div class="demo-block">
    <div class="demo-head">
      <div class="demo-num">03</div>
      <div>
        <h3>Submission journey</h3>
        <p class="talk">“This is the no-black-box screen — every stage and finding is inspectable.”</p>
      </div>
    </div>
    <div class="figure-frame tall"><img src="{journey}" alt="Journey"/></div>
    <p class="cap"><strong>Stages, COPE, oracles, UW memo, pricing.</strong> Built for underwriters and auditors.</p>
  </div>

  <div class="demo-block">
    <div class="demo-head">
      <div class="demo-num">04</div>
      <div>
        <h3>Queue</h3>
        <p class="talk">“UW time goes to the hottest files first — not FIFO.”</p>
      </div>
    </div>
    <div class="figure-frame"><img src="{queue}" alt="Queue"/></div>
    <p class="cap"><strong>Fit / triage scores + journey strips.</strong> Prioritized work, not a flat dump.</p>
  </div>
  <div class="page-num">4</div>
</section>

<!-- CLOSE -->
<section class="page inner">
  <div class="sec-label">05 — Pilot</div>
  <h2>Pilot Lab &amp; UW sign-off</h2>
  <div class="two-col">
    <div class="card">
      <h3>Pilot Lab</h3>
      <p>Sandbox readiness (CLUE / A-PLUS / Guidewire / Redis), redacted package runs, PII auto-redact, email ingest, outreach drafts — prep for a 30-day shadow pilot.</p>
    </div>
    <div class="card">
      <h3>UW Sign-off</h3>
      <p>Approve, refer, or decline with notes and override reasons. Pending badges in the nav while you calibrate AI vs UW judgment.</p>
    </div>
  </div>

  <div class="sec-label">06 — Outcomes</div>
  <h2>Decisions you’ll see</h2>
  <table class="clean">
    <thead><tr><th>Vertical</th><th>Outcomes</th></tr></thead>
    <tbody>
      <tr><td><strong>Insurance</strong></td><td>ACCEPT · CONDITIONAL_ACCEPT · REFER · DECLINE</td></tr>
      <tr><td><strong>Mortgage</strong></td><td>Approve / Refer / Suspend / Deny + rate</td></tr>
      <tr><td><strong>Lending</strong></td><td>Approved / conditions / referred / declined / suspended</td></tr>
    </tbody>
  </table>

  <div class="sec-label">07 — Trust</div>
  <h2>Built into the product</h2>
  <div class="trust-grid">
    <div class="trust-item"><strong>Access</strong> JWT roles · org-scoped jobs</div>
    <div class="trust-item"><strong>PII</strong> Detection + redaction for pilots</div>
    <div class="trust-item"><strong>Audit</strong> Encrypted bundles · SHA-256 ZIP exports</div>
    <div class="trust-item"><strong>Fail-closed</strong> Blocks when required feeds are missing</div>
  </div>

  <div class="sec-label">08 — Script</div>
  <h2>Ten-minute demo</h2>
  <ol class="demo">
    <li>Open <a href="https://ryterainc.com/dashboard">ryterainc.com/dashboard</a> → sign in</li>
    <li><strong>Overview</strong> → run an insurance demo</li>
    <li><strong>Insurance</strong> → open the job → walk the <strong>submission journey</strong></li>
    <li><strong>Queue</strong> → show triage order</li>
    <li><strong>Pilot Lab</strong> → sandbox readiness + shadow mode</li>
    <li>Optional: <strong>UW Sign-off</strong> → human override</li>
  </ol>

  <p style="margin-top:0.85em"><strong>Also in the sidebar when you need it:</strong>
  System Health · Mortgage · Lending · Renewals · Override Analytics ·
  Authority · Market Cycle · Model Registry · Integrations · Webhooks</p>

  <div class="footer-note">
    Carrier / MGA next step → Pilot Partner Brief (30-day shadow ask, data drop, success criteria).<br/>
    Rytera™ · <a href="https://ryterainc.com">ryterainc.com</a> · hello@ryterainc.com
  </div>
  <div class="page-num">5</div>
</section>

</body>
</html>
"""


def main() -> None:
    html = build_html()
    OUT_HTML.write_text(html, encoding="utf-8")

    launch_kwargs: dict = {"headless": True}
    chrome = Path(CHROME)
    if chrome.exists():
        launch_kwargs["executable_path"] = str(chrome)

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        page = browser.new_page()
        page.goto(OUT_HTML.resolve().as_uri(), wait_until="networkidle")
        page.wait_for_timeout(900)
        page.pdf(
            path=str(OUT_PDF),
            format="Letter",
            print_background=True,
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
            prefer_css_page_size=True,
        )
        browser.close()

    OUT_HTML.unlink(missing_ok=True)
    size_mb = OUT_PDF.stat().st_size / (1024 * 1024)
    print(f"Wrote {OUT_PDF.relative_to(ROOT)} ({size_mb:.1f} MB, check page count below)")


if __name__ == "__main__":
    main()
