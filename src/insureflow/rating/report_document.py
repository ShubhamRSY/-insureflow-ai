"""Full submission report HTML generator for PDF export."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def generate_report_html(results: dict[str, Any], job_id: str) -> str:
    """Build a comprehensive HTML report from pipeline results dict.

    Works with the raw dict stored in the job store (not model objects)
    so it can render any completed job without re-running the pipeline.
    """
    r = results
    memo = r.get("memo") or {}
    quote_full = r.get("quote_full") or {}
    quote = r.get("quote") or {}
    recon = r.get("reconciliation") or {}
    provenance = r.get("provenance") or {}
    now = datetime.now(tz=timezone.utc).strftime("%B %d, %Y at %H:%M UTC")

    insured = memo.get("insured_name") or r.get("insured_name") or "Named Insured"
    decision = (r.get("ai_decision") or memo.get("decision") or "pending").upper()
    risk_score = memo.get("overall_risk_score")
    risk_pct = round(risk_score * 100) if risk_score is not None else None
    severity = memo.get("severity") or "—"
    triage_score = r.get("triage_score")
    triage_priority = r.get("triage_priority") or "normal"
    doc_count = r.get("document_count") or 0
    document_checklist = r.get("document_checklist") or {}
    base_premium = quote.get("base_premium") or quote_full.get("base_premium") or 0
    adjusted_premium = quote.get("adjusted_premium") or quote_full.get("adjusted_premium") or 0
    policy_ref = quote.get("policy_admin_reference") or quote_full.get("policy_admin_reference") or "—"
    valid_until = quote.get("quote_valid_until") or quote_full.get("quote_valid_until") or "30 days"
    meta = quote_full.get("metadata") or {}
    key_findings = memo.get("key_findings") or []
    recommendation = memo.get("recommendation") or {}
    oracle_findings_count = r.get("oracle_findings_count") or 0
    premiums_mods = quote_full.get("schedule_modifications") or []

    # Decision badge colour
    decision_colors = {
        "ACCEPT": "#22c55e",
        "REFER": "#f59e0b",
        "DECLINE": "#ef4444",
    }
    decision_color = decision_colors.get(decision, "#64748b")

    # Risk score color
    if risk_pct is not None:
        if risk_pct >= 75:
            risk_color = "#ef4444"
        elif risk_pct >= 50:
            risk_color = "#f59e0b"
        else:
            risk_color = "#22c55e"
    else:
        risk_color = "#64748b"

    # ── Findings by category ──
    findings_by_cat: dict[str, list[dict[str, Any]]] = {}
    for f in key_findings:
        cat = f.get("category", "other")
        findings_by_cat.setdefault(cat, []).append(f)

    # ── Build HTML sections ──

    # Document checklist
    present_docs = document_checklist.get("present_documents") or []
    missing_docs = document_checklist.get("missing_documents") or []
    completeness = document_checklist.get("completeness_pct")
    doc_rows = ""
    for d in present_docs:
        doc_rows += f'<tr><td style="padding:4px 8px;color:#16a34a;">&#10003; {d}</td><td style="padding:4px 8px;text-align:right;color:#16a34a;">Present</td></tr>'
    for d in missing_docs:
        doc_rows += f'<tr><td style="padding:4px 8px;color:#dc2626;">&#10007; {d}</td><td style="padding:4px 8px;text-align:right;color:#dc2626;">Missing</td></tr>'
    if not doc_rows:
        doc_rows = '<tr><td style="padding:4px 8px;color:#94a3b8;">No document data available</td></tr>'

    # Findings rows
    findings_html = ""
    sev_colors = {"critical": "#dc2626", "high": "#ea580c", "moderate": "#d97706", "low": "#64748b"}
    cat_labels = {
        "risk": "Risk Assessment",
        "loss_history": "Loss History",
        "compliance": "Compliance",
        "coverage": "Coverage",
        "fraud": "Fraud Detection",
        "external_oracle": "External Oracle",
    }
    for cat, findings in findings_by_cat.items():
        label = cat_labels.get(cat, cat.replace("_", " ").title())
        findings_html += f'<h3 style="font-size:13px;font-weight:600;margin:16px 0 6px;color:#334155;">{label}</h3>'
        for f in findings:
            sev = (f.get("severity") or "moderate").lower()
            sc = sev_colors.get(sev, "#64748b")
            findings_html += f"""
            <div style="border-left:3px solid {sc};padding:6px 12px;margin-bottom:8px;background:#f8fafc;border-radius:0 6px 6px 0;">
              <div style="font-weight:600;font-size:12px;color:#1e293b;">{f.get("title", "Finding")}</div>
              <div style="font-size:11px;color:#64748b;margin-top:2px;">{f.get("description", "")}</div>
              <div style="font-size:10px;color:{sc};margin-top:2px;text-transform:uppercase;font-weight:600;">{sev}</div>
            </div>"""

    if not findings_html:
        findings_html = '<p style="color:#94a3b8;font-size:12px;">No findings recorded.</p>'

    # Premium breakdown
    premium_rows = f'<tr><td style="padding:5px 8px;">Base Premium</td><td style="padding:5px 8px;text-align:right;font-weight:600;">${base_premium:,.2f}</td></tr>'
    for mod in premiums_mods:
        pct = mod.get("modifier_pct", 0)
        label = mod.get("name", "").replace("_", " ").title()
        color = "#dc2626" if pct > 0 else "#16a34a" if pct < 0 else "#94a3b8"
        sign = "+" if pct > 0 else ""
        premium_rows += f'<tr><td style="padding:5px 8px;">{label}</td><td style="padding:5px 8px;text-align:right;color:{color};">{sign}{pct:.1f}%</td></tr>'
    premium_rows += (
        '<tr><td style="padding:8px;border-top:2px solid #e2e8f0;font-weight:700;">Indicated Premium</td>'
        f'<td style="padding:8px;border-top:2px solid #e2e8f0;text-align:right;font-weight:700;font-size:16px;color:#16a34a;">${adjusted_premium:,.2f}</td></tr>'
    )

    # Reconciliation
    match_rate = recon.get("match_rate")
    match_pct = round(match_rate * 100) if match_rate is not None else None
    discrepancies = recon.get("discrepancies") or []
    recon_status = recon.get("overall_status") or "—"

    recon_bg = "#dcfce7" if recon_status == "reconciled" else "#fef3c7"
    recon_fg = "#16a34a" if recon_status == "reconciled" else "#d97706"
    recon_html = f'<div style="display:inline-block;padding:4px 12px;border-radius:6px;font-size:12px;font-weight:600;background:{recon_bg};color:{recon_fg};">{recon_status.upper()}</div>'
    if match_pct is not None:
        recon_html += f' <span style="margin-left:8px;color:#64748b;">{match_pct}% field match rate</span>'
    recon_html += f'<span style="margin-left:8px;color:#64748b;">{len(discrepancies)} discrepancy(ies)</span>'

    # Provenance
    prov_fields = provenance.get("fields") or []
    prov_count = provenance.get("total_fields") or len(prov_fields)
    verified = provenance.get("verified_fields") or 0

    # Oracle findings
    oracle_findings = memo.get("key_findings") or []
    oracle_findings = [f for f in oracle_findings if f.get("category") == "external_oracle"]

    # Recommendation
    rec_action = recommendation.get("action") or "—"
    rec_conditions = recommendation.get("conditions") or []
    conditions_html = "".join(f"<li>{c}</li>" for c in rec_conditions) if rec_conditions else "<li>No conditions</li>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Underwriting Report — {insured}</title>
<style>
  @page {{
    size: A4;
    margin: 20mm 15mm;
    @bottom-center {{ content: "Page " counter(page) " of " counter(pages); font-size: 10px; color: #94a3b8; }}
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif; color: #1e293b; font-size: 12px; line-height: 1.5; background: white; }}
  h1 {{ font-size: 20px; font-weight: 700; margin-bottom: 2px; }}
  h2 {{ font-size: 14px; font-weight: 700; margin: 20px 0 8px; color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 4px; }}
  h3 {{ margin-bottom: 4px; }}
  .header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; padding-bottom: 16px; border-bottom: 3px solid #0f172a; }}
  .meta {{ font-size: 11px; color: #64748b; }}
  .badge {{ display: inline-block; padding: 4px 12px; border-radius: 6px; font-size: 13px; font-weight: 700; letter-spacing: 0.03em; }}
  .row {{ display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid #f1f5f9; }}
  .row .label {{ color: #64748b; min-width: 140px; }}
  .row .value {{ font-weight: 500; text-align: right; }}
  .card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin-bottom: 10px; }}
  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
  .grid-3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  table th {{ text-align: left; font-size: 10px; text-transform: uppercase; color: #64748b; letter-spacing: 0.05em; padding: 4px 8px; border-bottom: 2px solid #e2e8f0; }}
  .section-label {{ font-size: 10px; text-transform: uppercase; color: #64748b; letter-spacing: 0.05em; margin-bottom: 4px; font-weight: 600; }}
  .footer {{ margin-top: 24px; padding-top: 12px; border-top: 1px solid #e2e8f0; font-size: 10px; color: #94a3b8; text-align: center; }}
  ul {{ list-style: none; padding: 0; }}
  ul li {{ padding: 3px 0; font-size: 11px; }}
  ul li::before {{ content: "— "; color: #cbd5e1; }}
  .stat {{ text-align: center; }}
  .stat-value {{ font-size: 22px; font-weight: 700; }}
  .stat-label {{ font-size: 10px; color: #64748b; text-transform: uppercase; }}
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>{insured}</h1>
    <div class="meta">Underwriting Report &mdash; Generated {now}</div>
    <div class="meta">Job ID: {job_id}</div>
  </div>
  <div style="text-align:right;">
    <div class="badge" style="background:{decision_color}15;color:{decision_color};border:1px solid {decision_color}40;">{decision}</div>
    <div style="margin-top:6px;" class="meta">Quote #{policy_ref}</div>
    <div class="meta">Expires {valid_until}</div>
  </div>
</div>

<h2>Submission Overview</h2>
<div class="grid-3">
  <div class="card stat">
    <div class="stat-value" style="color:{risk_color};">{risk_pct if risk_pct is not None else "—"}/100</div>
    <div class="stat-label">Risk Score</div>
  </div>
  <div class="card stat">
    <div class="stat-value" style="color:#0f172a;">${adjusted_premium:,.0f}</div>
    <div class="stat-label">Indicated Premium</div>
  </div>
  <div class="card stat">
    <div class="stat-value" style="color:#0f172a;">{doc_count}</div>
    <div class="stat-label">Documents</div>
  </div>
</div>

<div class="grid-2">
  <div>
    <div class="row"><span class="label">Decision</span><span class="value" style="color:{decision_color};font-weight:700;">{decision}</span></div>
    <div class="row"><span class="label">Severity</span><span class="value">{severity.title()}</span></div>
    <div class="row"><span class="label">Triage Score</span><span class="value">{triage_score if triage_score is not None else "—"} ({triage_priority})</span></div>
    <div class="row"><span class="label">Risk Score</span><span class="value" style="color:{risk_color};">{risk_pct}%</span></div>
  </div>
  <div>
    <div class="row"><span class="label">Base Premium</span><span class="value">${base_premium:,.2f}</span></div>
    <div class="row"><span class="label">Indicated Premium</span><span class="value" style="font-weight:700;">${adjusted_premium:,.2f}</span></div>
    <div class="row"><span class="label">Oracle Checks</span><span class="value">{oracle_findings_count}</span></div>
    <div class="row"><span class="label">Reconciliation</span><span class="value">{recon_status.title()} ({match_pct or 0}% match)</span></div>
  </div>
</div>

<h2>Document Checklist</h2>
<div class="card" style="padding:0;">
  <table>
    <thead><tr><th style="text-align:left;">Document</th><th style="text-align:right;">Status</th></tr></thead>
    <tbody>{doc_rows}</tbody>
  </table>
</div>
<div class="meta" style="margin-top:4px;">Completeness: {completeness if completeness is not None else "—"}%</div>

<h2>Key Findings</h2>
{findings_html}

<h2>Premium Breakdown</h2>
<div class="card" style="padding:0;">
  <table>
    <tbody>{premium_rows}</tbody>
  </table>
</div>

<h2>Pricing Modifiers</h2>
<div class="grid-2">
  <div class="card">
    <div class="section-label">Base Rate</div>
    <div class="row"><span class="label">ISO Loss Cost</span><span class="value">${meta.get("loss_cost", 0):.4f}/$100</span></div>
    <div class="row"><span class="label">Rate per $100 TIV</span><span class="value">{quote_full.get("rate_per_100_tiv") or meta.get("rate_per_100_tiv") or "—"}</span></div>
  </div>
  <div class="card">
    <div class="section-label">Modifiers</div>
    <div class="row"><span class="label">COPE</span><span class="value">{meta.get("cope_mod_pct", 0):+.1f}%</span></div>
    <div class="row"><span class="label">Market</span><span class="value">{meta.get("market_mod_pct", 0):+.1f}%</span></div>
    <div class="row"><span class="label">Deductible</span><span class="value">{meta.get("deductible_credit", 0):+.1f}%</span></div>
    <div class="row"><span class="label">Loss Experience</span><span class="value">{meta.get("loss_experience_mod_pct", 0):+.1f}%</span></div>
    <div class="row"><span class="label">Tenure</span><span class="value">{meta.get("years_in_business_mod_pct", 0):+.1f}%</span></div>
  </div>
</div>

<h2>Reconciliation</h2>
<div style="margin-bottom:8px;">{recon_html}</div>
{"<p style='font-size:11px;color:#64748b;'>No discrepancies found.</p>" if not discrepancies else ""}

<h2>Underwriting Recommendation</h2>
<div class="card">
  <div class="row"><span class="label">Action</span><span class="value" style="font-weight:700;">{rec_action.title()}</span></div>
  <div style="margin-top:8px;">
    <div class="section-label">Conditions</div>
    <ul>{conditions_html}</ul>
  </div>
</div>

<h2>Provenance</h2>
<div class="grid-2">
  <div class="card">
    <div class="row"><span class="label">Fields Tracked</span><span class="value">{prov_count}</span></div>
    <div class="row"><span class="label">Verified</span><span class="value">{verified}</span></div>
  </div>
  <div class="card">
    <div class="section-label">Encryption</div>
    <div class="row"><span class="label">At Rest</span><span class="value">{"Yes" if r.get("encryption_at_rest") else "No"}</span></div>
    <div class="row"><span class="label">Audit Trail</span><span class="value">{r.get("audit_trail_entries", 0)} entries</span></div>
  </div>
</div>

<div class="footer">
  <p>This report is generated by Rytera AI Underwriting Platform for informational purposes only.</p>
  <p style="margin-top:2px;">It does not constitute a binder of insurance or a binding agreement.</p>
  <p style="margin-top:4px;font-weight:600;">Rytera &bull; {now}</p>
</div>

</body>
</html>"""


def html_to_pdf(html: str) -> bytes:
    """Convert HTML string to PDF bytes using WeasyPrint.

    Falls back to returning the raw HTML encoded as UTF-8 if WeasyPrint
    is not installed, so the endpoint never hard-fails.
    """
    try:
        from weasyprint import HTML  # type: ignore[import-untyped]

        return HTML(string=html).write_pdf()
    except (ImportError, OSError):
        return html.encode("utf-8")
