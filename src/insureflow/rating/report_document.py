"""Professional underwriting report HTML generator for PDF export."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _render_conditions(conditions: list[str]) -> str:
    """Render conditions list as HTML."""
    if not conditions:
        return '<div style="margin-top:6px;font-size:11px;color:#94a3b8;">No conditions</div>'
    items = "".join(f"<li style='padding:2px 0;font-size:11px;color:#475569;'>&mdash; {c}</li>" for c in conditions)
    return f"<div class='mt-8'><div class='findings-category' style='margin-top:0;'>Conditions</div><ul style='list-style:none;padding:0;'>{items}</ul></div>"


def generate_report_html(results: dict[str, Any], job_id: str) -> str:
    """Build a professional, client-facing HTML report from pipeline results.

    Works with the raw dict stored in the job store (not model objects)
    so it can render any completed job without re-running the pipeline.
    """
    r = results
    memo = r.get("memo") or {}
    quote_full = r.get("quote_full") or {}
    quote = r.get("quote") or {}
    recon = r.get("reconciliation") or {}
    now = datetime.now(tz=timezone.utc).strftime("%B %d, %Y at %H:%M UTC")

    insured = memo.get("insured_name") or r.get("insured_name") or "Named Insured"
    decision = (r.get("ai_decision") or memo.get("decision") or "pending").upper()
    risk_score = memo.get("overall_risk_score")
    risk_pct = round(risk_score * 100) if risk_score is not None else None
    severity = memo.get("overall_risk_severity") or memo.get("severity") or "—"
    triage_score = r.get("triage_score")
    document_checklist = r.get("document_checklist") or {}
    base_premium = quote.get("base_premium") or quote_full.get("base_premium") or 0
    adjusted_premium = quote.get("adjusted_premium") or quote_full.get("adjusted_premium") or 0
    policy_ref = quote.get("policy_admin_reference") or quote_full.get("policy_admin_reference") or "—"
    valid_until = quote.get("quote_valid_until") or quote_full.get("quote_valid_until") or "30 days"
    meta = quote_full.get("metadata") or {}
    insurance_line = str(r.get("insurance_line") or r.get("product_line") or meta.get("insurance_line") or "").lower()
    is_life = insurance_line == "life" or bool(meta.get("personal_lines") and "life" in str(meta.get("product") or "").lower())
    key_findings = memo.get("key_findings") or []
    # Dedupe findings by title+description prefix
    _seen_f: set[tuple[str, str]] = set()
    deduped_findings: list[dict[str, Any]] = []
    for f in key_findings:
        if not isinstance(f, dict):
            continue
        key = (str(f.get("title") or "").strip().lower(), str(f.get("description") or "")[:120].strip().lower())
        if key in _seen_f:
            continue
        _seen_f.add(key)
        deduped_findings.append(f)
    key_findings = deduped_findings
    recommendation = memo.get("recommendation") or {}
    oracle_findings_count = r.get("oracle_findings_count") or 0
    premiums_mods = quote_full.get("schedule_modifications") or []
    executive_summary = memo.get("summary") or memo.get("executive_summary") or ""

    # ── Colors ──
    decision_colors = {
        "ACCEPT": "#16a34a",
        "CONDITIONAL_ACCEPT": "#d97706",
        "REFER": "#d97706",
        "DECLINE": "#dc2626",
    }
    decision_color = decision_colors.get(decision, "#64748b")

    if risk_pct is not None:
        if risk_pct >= 75:
            risk_color = "#dc2626"
        elif risk_pct >= 50:
            risk_color = "#d97706"
        else:
            risk_color = "#16a34a"
    else:
        risk_color = "#64748b"

    sev_colors = {
        "critical": "#dc2626",
        "high": "#dc2626",
        "moderate": "#d97706",
        "low": "#16a34a",
    }
    cat_labels = {
        "risk": "Risk Assessment",
        "loss_history": "Loss History",
        "compliance": "Compliance",
        "coverage": "Coverage",
        "fraud": "Fraud Detection",
        "external_oracle": "External Data",
    }

    # ── Document checklist ──
    present_docs = document_checklist.get("present_documents") or []
    missing_docs = document_checklist.get("missing_documents") or []
    completeness_raw = document_checklist.get("completeness_pct")
    # completeness_pct is stored as 0-1 float; convert to display percentage
    completeness_display = f"{round(completeness_raw * 100)}%" if completeness_raw is not None else "—"

    doc_rows = ""
    for d in present_docs:
        label = d.replace("_", " ").title()
        doc_rows += f'<tr><td class="doc-name">{label}</td><td class="doc-status present">&#10003; Present</td></tr>'
    for d in missing_docs:
        label = d.replace("_", " ").title()
        doc_rows += f'<tr><td class="doc-name">{label}</td><td class="doc-status missing">&#10007; Missing</td></tr>'
    if not doc_rows:
        doc_rows = '<tr><td class="doc-name" style="color:#94a3b8;">No document data available</td></tr>'

    # ── Key findings ──
    findings_by_cat: dict[str, list[dict[str, Any]]] = {}
    for f in key_findings:
        cat = f.get("category", "other")
        findings_by_cat.setdefault(cat, []).append(f)

    findings_html = ""
    for cat, findings in findings_by_cat.items():
        label = cat_labels.get(cat, cat.replace("_", " ").title())
        findings_html += f'<h3 class="findings-category">{label}</h3>'
        for f in findings:
            sev = (f.get("severity") or "moderate").lower()
            sc = sev_colors.get(sev, "#64748b")
            findings_html += f"""
            <div class="finding-item" style="border-left-color:{sc};">
              <div class="finding-title">{f.get("title", "Finding")}</div>
              <div class="finding-desc">{f.get("description", "")}</div>
              <div class="finding-severity" style="color:{sc};">{sev.upper()}</div>
            </div>"""

    if not findings_html:
        findings_html = '<p style="color:#94a3b8;font-size:12px;padding:8px 0;">No findings recorded.</p>'

    # ── Premium breakdown ──
    premium_rows = ""
    premium_rows += _row("Base Premium", f"${base_premium:,.2f}")
    for mod in premiums_mods:
        pct = mod.get("modifier_pct", 0)
        label = mod.get("name", "").replace("_", " ").title()
        color = "#dc2626" if pct > 0 else "#16a34a" if pct < 0 else "#64748b"
        sign = "+" if pct > 0 else ""
        premium_rows += _row(label, f"{sign}{pct:.1f}%", color=color)
    premium_rows += _row(
        "Indicated Premium",
        f"${adjusted_premium:,.2f}",
        bold=True,
        color="#0f172a",
        border_top=True,
    )

    # ── Reconciliation ──
    match_rate = recon.get("match_rate")
    match_pct = round(match_rate * 100) if match_rate is not None else None
    recon_status = (recon.get("overall_status") or "—").upper()

    # ── Recommendation — always align action with the persisted decision badge ──
    rec_action = decision
    rec_from_memo = (recommendation.get("action") or "").upper()
    if rec_from_memo and rec_from_memo != decision and rec_from_memo != "—":
        # Prefer the pipeline decision; note divergence was a historical bug
        rec_action = decision
    rec_conditions = recommendation.get("conditions") or memo.get("conditions") or []

    # Life vs commercial modifier cards
    if is_life:
        medical = meta.get("medical") or {}
        modifiers_html = f"""
  <div class="card">
    <div class="findings-category" style="margin-top:0;">Life Rating</div>
    <div class="kv-row"><span class="kv-label">Filing</span><span class="kv-value">{meta.get("filing_id") or "—"}</span></div>
    <div class="kv-row"><span class="kv-label">UW Class</span><span class="kv-value">{(medical.get("underwriting_class") or "—")}</span></div>
    <div class="kv-row"><span class="kv-label">Tobacco</span><span class="kv-value">{"Yes" if medical.get("tobacco") else "No"}</span></div>
    <div class="kv-row"><span class="kv-label">Face Amount</span><span class="kv-value">${float(meta.get("face_amount") or meta.get("tiv") or 0):,.0f}</span></div>
  </div>"""
        base_rate_html = f"""
  <div class="card">
    <div class="findings-category" style="margin-top:0;">Premium</div>
    <div class="kv-row"><span class="kv-label">Base</span><span class="kv-value">${base_premium:,.2f}</span></div>
    <div class="kv-row"><span class="kv-label">Indicated</span><span class="kv-value" style="font-weight:700;">${adjusted_premium:,.2f}</span></div>
    <div class="kv-row"><span class="kv-label">Line</span><span class="kv-value">Life</span></div>
  </div>"""
    else:
        modifiers_html = f"""
  <div class="card">
    <div class="findings-category" style="margin-top:0;">Modifiers</div>
    <div class="kv-row"><span class="kv-label">COPE Schedule</span><span class="kv-value">{meta.get("cope_mod_pct", 0):+.1f}%</span></div>
    <div class="kv-row"><span class="kv-label">Market Cycle</span><span class="kv-value">{meta.get("market_mod_pct", 0):+.1f}%</span></div>
    <div class="kv-row"><span class="kv-label">Deductible</span><span class="kv-value">{meta.get("deductible_credit", 0):+.1f}%</span></div>
    <div class="kv-row"><span class="kv-label">Loss Experience</span><span class="kv-value">{meta.get("loss_experience_mod_pct", 0):+.1f}%</span></div>
    <div class="kv-row"><span class="kv-label">Years in Business</span><span class="kv-value">{meta.get("years_in_business_mod_pct", 0):+.1f}%</span></div>
  </div>"""
        base_rate_html = f"""
  <div class="card">
    <div class="findings-category" style="margin-top:0;">Base Rate</div>
    <div class="kv-row"><span class="kv-label">ISO Loss Cost</span><span class="kv-value">${meta.get("loss_cost", 0):.4f}/$100</span></div>
    <div class="kv-row"><span class="kv-label">Rate per $100 TIV</span><span class="kv-value">{quote_full.get("rate_per_100_tiv") or meta.get("rate_per_100_tiv") or "—"}</span></div>
  </div>"""

    summary_block = ""
    if executive_summary:
        summary_block = f"""
<div class="section-title">Executive Summary</div>
<div class="card"><p style="font-size:13px;color:#334155;line-height:1.55;">{executive_summary}</p></div>
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Underwriting Report — {insured}</title>
<style>
  @page {{
    size: A4;
    margin: 18mm 16mm 20mm 16mm;
    @bottom-center {{
      content: "Page " counter(page) " of " counter(pages);
      font-size: 9px;
      color: #94a3b8;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }}
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    color: #1e293b;
    font-size: 11px;
    line-height: 1.55;
    background: white;
    -webkit-font-smoothing: antialiased;
  }}

  /* ── Header ── */
  .report-header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding-bottom: 14px;
    border-bottom: 2px solid #0f172a;
    margin-bottom: 18px;
  }}
  .report-header h1 {{
    font-size: 20px;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 2px;
  }}
  .report-meta {{
    font-size: 10px;
    color: #64748b;
    margin-top: 2px;
  }}
  .report-header-right {{
    text-align: right;
  }}
  .decision-badge {{
    display: inline-block;
    padding: 5px 14px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
  }}

  /* ── Sections ── */
  .section-title {{
    font-size: 12px;
    font-weight: 700;
    color: #0f172a;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin: 20px 0 8px 0;
    padding-bottom: 4px;
    border-bottom: 1px solid #e2e8f0;
  }}

  /* ── Cards ── */
  .card {{
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 10px 12px;
    margin-bottom: 8px;
  }}

  /* ── Grids ── */
  .grid-3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }}
  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}

  /* ── Stats ── */
  .stat {{ text-align: center; padding: 8px 4px; }}
  .stat-value {{ font-size: 22px; font-weight: 700; line-height: 1.2; }}
  .stat-label {{ font-size: 9px; color: #64748b; text-transform: uppercase; letter-spacing: 0.04em; margin-top: 2px; }}

  /* ── Key-value rows ── */
  .kv-row {{
    display: flex;
    justify-content: space-between;
    padding: 4px 0;
    border-bottom: 1px solid #f1f5f9;
  }}
  .kv-row:last-child {{ border-bottom: none; }}
  .kv-label {{ color: #64748b; min-width: 130px; }}
  .kv-value {{ font-weight: 500; text-align: right; }}

  /* ── Tables ── */
  table {{ width: 100%; border-collapse: collapse; }}
  th {{
    text-align: left;
    font-size: 9px;
    text-transform: uppercase;
    color: #64748b;
    letter-spacing: 0.05em;
    padding: 5px 8px;
    border-bottom: 2px solid #e2e8f0;
    font-weight: 600;
  }}
  td {{
    padding: 5px 8px;
    border-bottom: 1px solid #f1f5f9;
    font-size: 11px;
  }}
  .doc-name {{ font-weight: 500; }}
  .doc-status {{ text-align: right; font-weight: 600; font-size: 10px; }}
  .doc-status.present {{ color: #16a34a; }}
  .doc-status.missing {{ color: #dc2626; }}

  /* ── Findings ── */
  .findings-category {{
    font-size: 11px;
    font-weight: 700;
    color: #334155;
    margin: 14px 0 6px 0;
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }}
  .finding-item {{
    border-left: 3px solid #e2e8f0;
    padding: 6px 10px;
    margin-bottom: 6px;
    background: #f8fafc;
    border-radius: 0 4px 4px 0;
  }}
  .finding-title {{
    font-weight: 600;
    font-size: 11px;
    color: #1e293b;
  }}
  .finding-desc {{
    font-size: 10px;
    color: #64748b;
    margin-top: 2px;
    line-height: 1.4;
  }}
  .finding-severity {{
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.04em;
    margin-top: 2px;
  }}

  /* ── Footer ── */
  .report-footer {{
    margin-top: 24px;
    padding-top: 12px;
    border-top: 1px solid #e2e8f0;
    text-align: center;
    font-size: 9px;
    color: #94a3b8;
  }}
  .report-footer p {{ margin-bottom: 1px; }}

  /* ── Utility ── */
  .text-muted {{ color: #64748b; }}
  .text-right {{ text-align: right; }}
  .mt-8 {{ margin-top: 8px; }}
  .mb-4 {{ margin-bottom: 4px; }}
  .inline-badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 600;
  }}
</style>
</head>
<body>

<!-- ═══════════════════════════════════════════ HEADER ═══════════════════════════════════════════ -->
<div class="report-header">
  <div>
    <h1>{insured}</h1>
    <div class="report-meta">Underwriting Report &mdash; {now}</div>
    <div class="report-meta">Job ID: {job_id}</div>
  </div>
  <div class="report-header-right">
    <div class="decision-badge" style="background:{decision_color}12;color:{decision_color};border:1px solid {decision_color}30;">{decision}</div>
    <div class="report-meta" style="margin-top:6px;">Quote #{policy_ref}</div>
    <div class="report-meta">Expires {valid_until}</div>
  </div>
</div>

<!-- ═══════════════════════════════════════════ SUMMARY ═══════════════════════════════════════════ -->
<div class="section-title">Submission Summary</div>
<div class="grid-3">
  <div class="card stat">
    <div class="stat-value" style="color:{risk_color};">{risk_pct if risk_pct is not None else "—"}</div>
    <div class="stat-label">Risk Score</div>
  </div>
  <div class="card stat">
    <div class="stat-value" style="color:#0f172a;">${adjusted_premium:,.0f}</div>
    <div class="stat-label">Indicated Premium</div>
  </div>
  <div class="card stat">
    <div class="stat-value" style="color:#0f172a;">{completeness_display}</div>
    <div class="stat-label">Doc Completeness</div>
  </div>
</div>

<div class="grid-2">
  <div class="card">
    <div class="kv-row"><span class="kv-label">Decision</span><span class="kv-value" style="color:{decision_color};font-weight:700;">{decision}</span></div>
    <div class="kv-row"><span class="kv-label">Severity</span><span class="kv-value">{severity.title()}</span></div>
    <div class="kv-row"><span class="kv-label">Triage Score</span><span class="kv-value">{triage_score if triage_score is not None else "—"}</span></div>
    <div class="kv-row"><span class="kv-label">Risk Score</span><span class="kv-value" style="color:{risk_color};">{risk_pct}%</span></div>
  </div>
  <div class="card">
    <div class="kv-row"><span class="kv-label">Base Premium</span><span class="kv-value">${base_premium:,.2f}</span></div>
    <div class="kv-row"><span class="kv-label">Indicated Premium</span><span class="kv-value" style="font-weight:700;">${adjusted_premium:,.2f}</span></div>
    <div class="kv-row"><span class="kv-label">Oracle Checks</span><span class="kv-value">{oracle_findings_count}</span></div>
    <div class="kv-row"><span class="kv-label">Reconciliation</span><span class="kv-value">{match_pct or 0}% match</span></div>
  </div>
</div>

<!-- ═══════════════════════════════════════════ DOCUMENTS ═══════════════════════════════════════════ -->
<div class="section-title">Document Checklist</div>
<div class="card" style="padding:0;">
  <table>
    <thead><tr><th style="text-align:left;">Document</th><th style="text-align:right;width:90px;">Status</th></tr></thead>
    <tbody>{doc_rows}</tbody>
  </table>
</div>
<div class="report-meta mt-8" style="margin-top:6px;">Completeness: {completeness_display} &mdash; {len(present_docs)} of {len(present_docs) + len(missing_docs)} required documents present</div>

<!-- ═══════════════════════════════════════════ PRICING ═══════════════════════════════════════════ -->
<div class="section-title">Premium Breakdown</div>
<div class="card" style="padding:0;">
  <table>
    <thead><tr><th style="text-align:left;">Component</th><th style="text-align:right;width:100px;">Amount / Factor</th></tr></thead>
    <tbody>{premium_rows}</tbody>
  </table>
</div>

<div class="grid-2 mt-8">
  {base_rate_html}
  {modifiers_html}
</div>

<!-- ═══════════════════════════════════════════ RECONCILIATION ═══════════════════════════════════════════ -->
<div class="section-title">Reconciliation</div>
<div class="card">
  <div class="kv-row">
    <span class="kv-label">Status</span>
    <span class="kv-value">
      <span class="inline-badge" style="background:{"#dcfce7" if recon_status == "RECONCILIED" else "#fef3c7"};color:{"#16a34a" if recon_status == "RECONCILIED" else "#d97706"};">{recon_status}</span>
    </span>
  </div>
  <div class="kv-row"><span class="kv-label">Field Match Rate</span><span class="kv-value">{match_pct or 0}%</span></div>
</div>

{summary_block}

<!-- ═══════════════════════════════════════════ RECOMMENDATION ═══════════════════════════════════════════ -->
<div class="section-title">Underwriting Recommendation</div>
<div class="card">
  <div class="kv-row">
    <span class="kv-label">Action</span>
    <span class="kv-value" style="font-weight:700;color:{decision_color};">{rec_action}</span>
  </div>
  {_render_conditions(rec_conditions)}
</div>

<!-- ═══════════════════════════════════════════ KEY FINDINGS ═══════════════════════════════════════════ -->
<div class="section-title">Key Findings</div>
{findings_html}

<!-- ═══════════════════════════════════════════ FOOTER ═══════════════════════════════════════════ -->
<div class="report-footer">
  <p>This report is generated by the Rytera AI Underwriting Platform for informational purposes only.</p>
  <p>It does not constitute a binder of insurance or a binding agreement.</p>
  <p style="margin-top:4px;font-weight:600;">Rytera &bull; {now}</p>
</div>

</body>
</html>"""


def _row(
    label: str,
    value: str,
    *,
    color: str = "#1e293b",
    bold: bool = False,
    border_top: bool = False,
) -> str:
    """Build a single premium breakdown table row."""
    border = "border-top:2px solid #e2e8f0;" if border_top else ""
    weight = "font-weight:700;" if bold else ""
    return f'<tr><td style="padding:5px 8px;{border}">{label}</td><td style="padding:5px 8px;text-align:right;color:{color};{weight}{border}">{value}</td></tr>'


def _fmt_money(value: Any) -> str:
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "—"


def _fmt_pct(value: Any) -> str:
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return "—"


_REPORT_CSS = """\
@page {
    size: A4;
    margin: 18mm 16mm 20mm 16mm;
    @bottom-center {
      content: "Page " counter(page) " of " counter(pages);
      font-size: 9px;
      color: #94a3b8;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
  }
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    color: #1e293b; font-size: 11px; line-height: 1.55; background: white;
    -webkit-font-smoothing: antialiased;
  }}
  .report-header {{
    display: flex; justify-content: space-between; align-items: flex-start;
    padding-bottom: 14px; border-bottom: 2px solid #0f172a; margin-bottom: 18px;
  }}
  .report-header h1 {{ font-size: 20px; font-weight: 700; color: #0f172a; margin-bottom: 2px; }}
  .report-meta {{ font-size: 10px; color: #64748b; margin-top: 2px; }}
  .report-header-right {{ text-align: right; }}
  .decision-badge {{
    display: inline-block; padding: 5px 14px; border-radius: 6px;
    font-size: 13px; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase;
  }}
  .section-title {{
    font-size: 12px; font-weight: 700; color: #0f172a; text-transform: uppercase;
    letter-spacing: 0.04em; margin: 20px 0 8px 0; padding-bottom: 4px;
    border-bottom: 1px solid #e2e8f0;
  }}
  .card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px 12px; margin-bottom: 8px; }}
  .grid-3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }}
  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
  .stat {{ text-align: center; padding: 8px 4px; }}
  .stat-value {{ font-size: 22px; font-weight: 700; line-height: 1.2; }}
  .stat-label {{ font-size: 9px; color: #64748b; text-transform: uppercase; letter-spacing: 0.04em; margin-top: 2px; }}
  .kv-row {{ display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #f1f5f9; }}
  .kv-row:last-child {{ border-bottom: none; }}
  .kv-label {{ color: #64748b; min-width: 130px; }}
  .kv-value {{ font-weight: 500; text-align: right; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{
    text-align: left; font-size: 9px; text-transform: uppercase; color: #64748b;
    letter-spacing: 0.05em; padding: 5px 8px; border-bottom: 2px solid #e2e8f0; font-weight: 600;
  }}
  td {{ padding: 5px 8px; border-bottom: 1px solid #f1f5f9; font-size: 11px; }}
  .findings-category {{ font-size: 11px; font-weight: 700; color: #334155; margin: 14px 0 6px 0; text-transform: uppercase; letter-spacing: 0.03em; }}
  .finding-item {{ border-left: 3px solid #e2e8f0; padding: 6px 10px; margin-bottom: 6px; background: #f8fafc; border-radius: 0 4px 4px 0; }}
  .finding-title {{ font-weight: 600; font-size: 11px; color: #1e293b; }}
  .finding-desc {{ font-size: 10px; color: #64748b; margin-top: 2px; line-height: 1.4; }}
  .finding-severity {{ font-size: 9px; font-weight: 700; letter-spacing: 0.04em; margin-top: 2px; }}
  .report-footer {{ margin-top: 24px; padding-top: 12px; border-top: 1px solid #e2e8f0; text-align: center; font-size: 9px; color: #94a3b8; }}
  .report-footer p {{ margin-bottom: 1px; }}
  .mt-8 {{ margin-top: 8px; }}
  .inline-badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 600; }}
  .checklist-badge {{ display: inline-block; padding: 1px 7px; border-radius: 4px; font-size: 9px; font-weight: 700; }}
"""

_SEVERITY_COLORS = {"critical": "#dc2626", "high": "#dc2626", "moderate": "#d97706", "low": "#16a34a"}


def _findings_html(findings: list[dict[str, Any]]) -> str:
    out = ""
    for f in findings:
        sev = (f.get("severity") or "moderate").lower()
        sc = _SEVERITY_COLORS.get(sev, "#64748b")
        out += (
            '<div class="finding-item" style="border-left-color:%s;">'
            '<div class="finding-title">%s</div>'
            '<div class="finding-desc">%s</div>'
            '<div class="finding-severity" style="color:%s;">%s</div>'
            "</div>"
        ) % (sc, f.get("title", "Finding"), f.get("description", ""), sc, sev.upper())
    if not out:
        out = '<p style="color:#94a3b8;font-size:12px;padding:8px 0;">No findings recorded.</p>'
    return out


def _checklist_rows(checklist: Any) -> str:
    if isinstance(checklist, dict):
        present = checklist.get("present_documents") or []
        missing = checklist.get("missing_documents") or []
    elif isinstance(checklist, list):
        present = [i.get("document") or i for i in checklist if isinstance(i, dict) and i.get("status") == "present"]
        missing = [i.get("document") or i for i in checklist if isinstance(i, dict) and i.get("status") == "missing"]
    else:
        present, missing = [], []
    rows = ""
    for d in present:
        label = str(d).replace("_", " ").title()
        rows += f'<tr><td style="font-weight:500;">{label}</td><td style="text-align:right;font-weight:600;font-size:10px;color:#16a34a;">&#10003; Present</td></tr>'
    for d in missing:
        label = str(d).replace("_", " ").title()
        rows += f'<tr><td style="font-weight:500;">{label}</td><td style="text-align:right;font-weight:600;font-size:10px;color:#dc2626;">&#10007; Missing</td></tr>'
    if not rows:
        rows = '<tr><td style="color:#94a3b8;">No document data available</td></tr>'
    return rows


def generate_mortgage_report_html(results: dict[str, Any], job_id: str) -> str:
    """Professional mortgage underwriting report (residential / commercial CRE)."""
    memo = results.get("memo") or {}
    rate = results.get("rate_quote") or memo.get("rate_quote") or {}
    now = datetime.now(tz=timezone.utc).strftime("%B %d, %Y at %H:%M UTC")

    borrower = results.get("borrower") or memo.get("borrower_name") or (results.get("summary") or {}).get("borrower") or "Borrower"
    decision = (results.get("decision") or memo.get("decision") or "pending").upper()
    decision_colors = {"APPROVE": "#16a34a", "SUSPEND": "#d97706", "REFER": "#d97706", "DENY": "#dc2626"}
    decision_color = decision_colors.get(decision, "#64748b")

    rate_val = rate.get("adjusted_rate") or rate.get("note_rate") or rate.get("interest_rate")
    payment = rate.get("monthly_pi") or rate.get("monthly_payment") or rate.get("pitia")
    dti = results.get("dti_ratio") or memo.get("dti_ratio")
    ltv = results.get("ltv_ratio") or memo.get("ltv_ratio")
    product_line = (results.get("product_line") or memo.get("product_line") or "residential_mortgage").replace("_", " ").title()
    risk_score = results.get("risk_score")
    risk_pct = round(float(risk_score) * 100) if risk_score is not None else None
    risk_color = "#dc2626" if risk_pct is not None and risk_pct >= 75 else "#d97706" if risk_pct is not None and risk_pct >= 50 else "#16a34a" if risk_pct is not None else "#64748b"

    findings = memo.get("key_findings") or results.get("key_findings") or []
    violations = results.get("compliance_violations") or memo.get("compliance_violations") or []
    recon_issues = results.get("reconciliation_issues") or []
    conditions = memo.get("conditions") or results.get("conditions") or []
    eligible = rate.get("eligible")
    ineligible = rate.get("ineligibility_reasons") or []

    doc_rows = _checklist_rows(results.get("package_checklist"))
    findings_html = _findings_html(findings)

    violation_rows = ""
    for v in violations:
        message = v.get("message") or v.get("description") or v.get("rule_id") or str(v)
        sev = (v.get("severity") or "moderate").lower()
        sc = _SEVERITY_COLORS.get(sev, "#64748b")
        violation_rows += f'<tr><td>{message}</td><td style="text-align:right;color:{sc};font-weight:600;">{sev.upper()}</td></tr>'
    if not violation_rows:
        violation_rows = '<tr><td style="color:#16a34a;">No compliance violations</td></tr>'

    recon_rows = ""
    for i in recon_issues:
        msg = getattr(i, "get", lambda k: None)("rule_id") or str(i)
        recon_rows += f"<li>{msg}</li>"
    if recon_rows:
        recon_rows = f"<ul style='padding-left:16px;'>{recon_rows}</ul>"
    else:
        recon_rows = '<p style="color:#16a34a;font-size:11px;">No reconciliation issues — cross-document data consistent.</p>'

    condition_items = ""
    for c in conditions:
        condition_items += f"<li>{c}</li>"
    if condition_items:
        condition_items = f"<ul style='padding-left:16px;'>{condition_items}</ul>"
    else:
        condition_items = '<p style="color:#94a3b8;font-size:11px;">No conditions</p>'

    eligibility_note = ""
    if eligible is False and ineligible:
        eligibility_note = '<p style="color:#dc2626;font-size:11px;margin-top:6px;">' + "Ineligible: " + "; ".join(str(i) for i in ineligible) + "</p>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Mortgage Underwriting Report — {borrower}</title>
<style>{_REPORT_CSS}</style>
</head>
<body>

<div class="report-header">
  <div>
    <h1>{borrower}</h1>
    <div class="report-meta">Mortgage Underwriting Report &mdash; {now}</div>
    <div class="report-meta">Job ID: {job_id}</div>
    <div class="report-meta">{product_line}</div>
  </div>
  <div class="report-header-right">
    <div class="decision-badge" style="background:{decision_color}12;color:{decision_color};border:1px solid {decision_color}30;">{decision}</div>
  </div>
</div>

<div class="section-title">Loan Summary</div>
<div class="grid-3">
  <div class="card stat"><div class="stat-value" style="color:{risk_color};">{risk_pct if risk_pct is not None else "—"}</div><div class="stat-label">Risk Score</div></div>
  <div class="card stat"><div class="stat-value" style="color:#0f172a;">{_fmt_pct(rate_val)}</div><div class="stat-label">Interest Rate</div></div>
  <div class="card stat"><div class="stat-value" style="color:#0f172a;">{_fmt_money(payment)}</div><div class="stat-label">Monthly P&amp;I</div></div>
</div>

<div class="grid-2 mt-8">
  <div class="card">
    <div class="kv-row"><span class="kv-label">Decision</span><span class="kv-value" style="color:{decision_color};font-weight:700;">{decision}</span></div>
    <div class="kv-row"><span class="kv-label">Debt-to-Income (DTI)</span><span class="kv-value">{_fmt_pct(dti)}</span></div>
    <div class="kv-row"><span class="kv-label">Loan-to-Value (LTV)</span><span class="kv-value">{_fmt_pct(ltv)}</span></div>
    <div class="kv-row"><span class="kv-label">Product Line</span><span class="kv-value">{product_line}</span></div>
  </div>
  <div class="card">
    <div class="kv-row"><span class="kv-label">Adjusted Rate</span><span class="kv-value">{_fmt_pct(rate_val)}</span></div>
    <div class="kv-row"><span class="kv-label">Monthly P&amp;I</span><span class="kv-value">{_fmt_money(payment)}</span></div>
    <div class="kv-row"><span class="kv-label">Documents Reviewed</span><span class="kv-value">{results.get("document_count") or 0}</span></div>
    <div class="kv-row"><span class="kv-label">Eligible</span><span class="kv-value">{("Yes" if eligible else "No") if eligible is not None else "—"}</span></div>
  </div>
</div>
{eligibility_note}

<div class="section-title">Document Checklist</div>
<div class="card" style="padding:0;">
  <table><thead><tr><th style="text-align:left;">Document</th><th style="text-align:right;width:90px;">Status</th></tr></thead><tbody>{doc_rows}</tbody></table>
</div>

<div class="section-title">Compliance</div>
<div class="card" style="padding:0;">
  <table><thead><tr><th style="text-align:left;">Check</th><th style="text-align:right;width:100px;">Severity</th></tr></thead><tbody>{violation_rows}</tbody></table>
</div>

<div class="section-title">Reconciliation</div>
<div class="card">{recon_rows}</div>

<div class="section-title">Underwriting Recommendation</div>
<div class="card">
  <div class="kv-row"><span class="kv-label">Action</span><span class="kv-value" style="font-weight:700;">{decision}</span></div>
  {condition_items}
</div>

<div class="section-title">Key Findings</div>
{findings_html}

<div class="report-footer">
  <p>This report is generated by the Rytera AI Underwriting Platform for informational purposes only.</p>
  <p>It does not constitute a commitment to lend or a binding agreement.</p>
  <p style="margin-top:4px;font-weight:600;">Rytera &bull; {now}</p>
</div>

</body>
</html>"""


def generate_lending_report_html(results: dict[str, Any], job_id: str) -> str:
    """Professional lending (business/consumer) underwriting report."""
    now = datetime.now(tz=timezone.utc).strftime("%B %d, %Y at %H:%M UTC")
    decision = (results.get("decision") or "pending").upper()
    decision_colors = {"APPROVE": "#16a34a", "SUSPEND": "#d97706", "REFER": "#d97706", "DENY": "#dc2626", "REFERRED": "#d97706"}
    decision_color = decision_colors.get(decision, "#64748b")

    risk_score = results.get("risk_score")
    risk_pct = round(float(risk_score) * 100) if risk_score is not None else None
    risk_color = "#dc2626" if risk_pct is not None and risk_pct >= 75 else "#d97706" if risk_pct is not None and risk_pct >= 50 else "#16a34a" if risk_pct is not None else "#64748b"

    product_type = (results.get("product_type") or "—").replace("_", " ").title()
    approved_rate = results.get("approved_rate")
    approved_amount = results.get("approved_amount")
    requested = results.get("requested_amount")
    conditions = results.get("conditions") or []
    review_reasons = results.get("human_review_reasons") or []
    violations = results.get("compliance_violations") or []

    condition_items = "".join(f"<li>{c}</li>" for c in conditions)
    condition_html = f"<ul style='padding-left:16px;'>{condition_items}</ul>" if condition_items else '<p style="color:#94a3b8;font-size:11px;">No conditions</p>'

    review_html = ""
    if review_reasons:
        review_html = "<div class='section-title'>Human Review Required</div><div class='card'><ul style='padding-left:16px;'>" + "".join(f"<li>{r}</li>" for r in review_reasons) + "</ul></div>"

    violation_rows = ""
    for v in violations:
        message = v.get("message") or v.get("description") or v.get("rule_id") or str(v)
        sev = (v.get("severity") or "moderate").lower()
        sc = _SEVERITY_COLORS.get(sev, "#64748b")
        violation_rows += f'<tr><td>{message}</td><td style="text-align:right;color:{sc};font-weight:600;">{sev.upper()}</td></tr>'
    if not violation_rows:
        violation_rows = '<tr><td style="color:#16a34a;">No compliance violations</td></tr>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Lending Underwriting Report — {results.get("application_id", "Application")}</title>
<style>{_REPORT_CSS}</style>
</head>
<body>

<div class="report-header">
  <div>
    <h1>{results.get("application_id", "Loan Application")}</h1>
    <div class="report-meta">Lending Underwriting Report &mdash; {now}</div>
    <div class="report-meta">Job ID: {job_id}</div>
  </div>
  <div class="report-header-right">
    <div class="decision-badge" style="background:{decision_color}12;color:{decision_color};border:1px solid {decision_color}30;">{decision}</div>
  </div>
</div>

<div class="section-title">Application Summary</div>
<div class="grid-3">
  <div class="card stat"><div class="stat-value" style="color:{risk_color};">{risk_pct if risk_pct is not None else "—"}</div><div class="stat-label">Risk Score</div></div>
  <div class="card stat"><div class="stat-value" style="color:#0f172a;">{_fmt_pct(approved_rate) if approved_rate is not None else "—"}</div><div class="stat-label">Approved Rate</div></div>
  <div class="card stat"><div class="stat-value" style="color:#0f172a;">{_fmt_money(approved_amount) if approved_amount is not None else "—"}</div><div class="stat-label">Approved Amount</div></div>
</div>

<div class="grid-2 mt-8">
  <div class="card">
    <div class="kv-row"><span class="kv-label">Decision</span><span class="kv-value" style="color:{decision_color};font-weight:700;">{decision}</span></div>
    <div class="kv-row"><span class="kv-label">Product Type</span><span class="kv-value">{product_type}</span></div>
    <div class="kv-row"><span class="kv-label">Requested Amount</span><span class="kv-value">{_fmt_money(requested) if requested else "—"}</span></div>
    <div class="kv-row"><span class="kv-label">Risk Rating</span><span class="kv-value">{results.get("risk_rating") or "—"}</span></div>
  </div>
  <div class="card">
    <div class="kv-row"><span class="kv-label">Approved Rate</span><span class="kv-value">{_fmt_pct(approved_rate) if approved_rate is not None else "—"}</span></div>
    <div class="kv-row"><span class="kv-label">Approved Amount</span><span class="kv-value">{_fmt_money(approved_amount) if approved_amount is not None else "—"}</span></div>
    <div class="kv-row"><span class="kv-label">Documents Reviewed</span><span class="kv-value">{results.get("document_count") or 0}</span></div>
    <div class="kv-row"><span class="kv-label">Human Review</span><span class="kv-value">{results.get("human_review_required") or False}</span></div>
  </div>
</div>

<div class="section-title">Compliance</div>
<div class="card" style="padding:0;">
  <table><thead><tr><th style="text-align:left;">Check</th><th style="text-align:right;width:100px;">Severity</th></tr></thead><tbody>{violation_rows}</tbody></table>
</div>

<div class="section-title">Decision Conditions</div>
<div class="card">{condition_html}</div>

{review_html}

<div class="section-title">Lender Notes</div>
<div class="card"><p style="font-size:11px;">{results.get("lender_notes") or "—"}</p></div>

<div class="report-footer">
  <p>This report is generated by the Rytera AI Underwriting Platform for informational purposes only.</p>
  <p>It does not constitute a commitment to lend or a binding agreement.</p>
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
        from weasyprint import HTML

        pdf: bytes = HTML(string=html).write_pdf()
        return pdf
    except (ImportError, OSError):
        return html.encode("utf-8")
