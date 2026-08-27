from __future__ import annotations

from datetime import datetime, timezone
from html import escape

from insureflow.models.agents import UnderwritingMemo
from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.models import InsuranceLine, QuoteResult, line_display_name
from insureflow.rating.report_theme import WORDMARK_CSS_DARK, WORDMARK_CSS_PRINT, decision_color, wordmark_html


def _esc(value: object) -> str:
    return escape(str(value if value is not None else ""))


def generate_quote_html(
    bundle: SubmissionBundle,
    memo: UnderwritingMemo,
    quote: QuoteResult,
) -> str:
    named_insured = bundle.structured.named_insured if bundle.structured else None
    insured = named_insured.legal_name if named_insured and named_insured.legal_name else (memo.insured_name or "")
    insured_missing = not str(insured or "").strip()
    if insured_missing:
        insured = "Named insured not provided"
    identity_gap_note = (
        "<div class='finding' style=\"border-left-color:#dc2626;\"><div class='finding-top'>"
        "<strong>Identity verification incomplete</strong></div><p class='finding-desc'>"
        "Named insured not on file. Confirm with the producer before bind.</p></div>"
        if insured_missing
        else ""
    )
    today = datetime.now(tz=timezone.utc).strftime("%B %d, %Y")
    valid_until = quote.quote_valid_until or "30 days from issuance"
    meta = quote.metadata or {}
    is_life = quote.line == InsuranceLine.LIFE or str(meta.get("insurance_line") or "").lower() == "life"
    date_of_birth = (named_insured.date_of_birth if named_insured else None) or meta.get("date_of_birth") or ""
    state_of_residence = (named_insured.state_of_residence if named_insured else None) or meta.get("issue_state") or ""
    line_label = line_display_name(quote.line.value)
    subtitle = f"{'Life' if is_life else 'Commercial'} Insurance Quote — Issued {today}"
    decision = (memo.decision.value if hasattr(memo.decision, "value") else str(memo.decision or "")).upper()
    decision_color_hex = decision_color(decision)
    risk = memo.overall_risk_score
    risk_pct = round(float(risk) * 100) if risk is not None else None
    severity = (memo.overall_risk_severity.value if hasattr(memo.overall_risk_severity, "value") else str(memo.overall_risk_severity or "—")).upper()

    # Coverages
    coverages_html = ""
    if bundle.structured and bundle.structured.coverages:
        for c in bundle.structured.coverages:
            sublimits = "".join(f"<tr><td class='pl-8'>{_esc(k)}</td><td class='text-right'>${v:,.0f}</td></tr>" for k, v in c.sublimits.items())
            endorsements = "".join(f"<li>{_esc(e)}</li>" for e in c.endorsements) if c.endorsements else "<li class='muted'>None</li>"
            coverages_html += f"""
            <div class="card">
              <div class="card-header">{_esc(c.coverage_type)}</div>
              <table>
                <tr><td>Limit</td><td class='text-right'>${c.limit_amount:,.0f}</td></tr>
                <tr><td>Deductible</td><td class='text-right'>${c.deductible:,.0f}</td></tr>
                <tr><td>Premium</td><td class='text-right'>${c.premium:,.0f}</td></tr>
                {sublimits}
              </table>
              <div class="section-title">Endorsements</div>
              <ul class="list">{endorsements}</ul>
            </div>"""
    elif is_life:
        face = meta.get("face_amount") or meta.get("tiv") or 0
        medical = meta.get("medical") or {}
        coverages_html = f"""
            <div class="card">
              <div class="card-header">Term / Life Coverage</div>
              <table>
                <tr><td>Face amount</td><td class='text-right'>${float(face):,.0f}</td></tr>
                <tr><td>UW class</td><td class='text-right'>{_esc(medical.get("underwriting_class") or meta.get("uw_decision_hint") or "—")}</td></tr>
                <tr><td>Tobacco</td><td class='text-right'>{"Yes" if medical.get("tobacco") else "No"}</td></tr>
              </table>
            </div>"""
    else:
        coverages_html = '<p class="muted">Coverage details not available — see quote breakdown below.</p>'

    iso_forms = list(meta.get("iso_forms") or [])
    if iso_forms:
        rows = "".join(f"<tr><td>{_esc(f.get('number'))}</td><td>{_esc(f.get('title'))}</td><td class='text-right'>{_esc(f.get('edition'))}</td></tr>" for f in iso_forms)
        forms_html = f"<h2>ISO / form schedule</h2><div class='card'><table>{rows}</table><p class='muted' style='margin-top:8px;'>Jacket map only — not a filed edition date until the carrier book supplies one.</p></div>"
    else:
        forms_html = ""
    sl = meta.get("surplus_lines") or {}
    if sl:
        forms_html += f"<h2>Admitted / E&amp;S</h2><div class='card'><p>{_esc(sl.get('market_status') or sl.get('status') or 'unknown')} — {_esc(sl.get('reason') or '')}</p></div>"

    exclusions: list[str] = []
    if memo.recommendation and memo.recommendation.conditions:
        exclusions.extend(memo.recommendation.conditions)
    exclusions.extend(memo.conditions or [])
    for f in memo.key_findings:
        if f.category in ("compliance", "coverage") and "exclusion" in (f.title + f.description).lower():
            exclusions.append(f"{f.title}: {f.description}")
    seen: set[str] = set()
    uniq_excl: list[str] = []
    for e in exclusions:
        if e not in seen:
            seen.add(e)
            uniq_excl.append(e)
    if not uniq_excl:
        uniq_excl.append("Standard policy exclusions apply. See policy form for full details.")
    exclusions_html = "".join(f"<li>{_esc(e)}</li>" for e in uniq_excl)

    components_html = ""
    for rc in quote.schedule_modifications:
        pct = rc.modifier_pct
        label = rc.name.replace("_", " ").title()
        amount = getattr(rc, "amount", None)
        if is_life and amount is not None and pct == 0:
            components_html += f"<div class='row'><span class='label'>{_esc(label)}</span><span>{_esc(amount)}</span></div>"
        elif pct > 0:
            components_html += f"<div class='row'><span class='label'>{_esc(label)}</span><span class='text-up'>+{pct:.1f}%</span></div>"
        elif pct < 0:
            components_html += f"<div class='row'><span class='label'>{_esc(label)}</span><span class='text-down'>{pct:.1f}%</span></div>"
        else:
            components_html += f"<div class='row'><span class='label'>{_esc(label)}</span><span class='muted'>{pct:.1f}%</span></div>"

    # Detailed findings for the quote package — CRITICAL/HIGH first so a cap
    # (if ever reached) never drops the findings that matter most.
    _sev_order = {"critical": 0, "high": 1, "moderate": 2, "low": 3}
    findings = sorted(
        list(memo.key_findings or []),
        key=lambda f: _sev_order.get((f.severity.value if hasattr(f.severity, "value") else str(f.severity or "moderate")).lower(), 4),
    )
    findings_html = ""
    if findings:
        shown, overflow = findings[:40], findings[40:]
        for f in shown:
            sev = (f.severity.value if hasattr(f.severity, "value") else str(f.severity or "moderate")).lower()
            findings_html += f"""
            <div class="finding">
              <div class="finding-top">
                <span class="sev sev-{_esc(sev)}">{_esc(sev.upper())}</span>
                <strong>{_esc(f.title)}</strong>
                <span class="muted"> · {_esc((f.category or "general").replace("_", " "))}</span>
              </div>
              <p class="finding-desc">{_esc(f.description or "")}</p>
            </div>"""
        if overflow:
            findings_html += f'<p class="muted">+ {len(overflow)} more lower-severity finding(s) — see the full Underwriting Report.</p>'
    else:
        findings_html = '<p class="muted">No underwriting findings recorded for this quote.</p>'

    review_reasons = list(memo.human_review_reasons or [])
    review_html = ""
    if review_reasons:
        items = "".join(f"<li>{_esc(r)}</li>" for r in review_reasons)
        review_html = f"""
  <h2>Referral Basis</h2>
  <ul class="list">{items}</ul>"""

    if is_life:
        face = float(meta.get("face_amount") or meta.get("tiv") or 0)
        medical = meta.get("medical") or {}
        header_rows = f"""
  <div class="row"><span class="label">Line of Business</span><span>{_esc(line_label)}</span></div>
  <div class="row"><span class="label">Date of Birth</span><span>{_esc(date_of_birth) or "Not provided"}</span></div>
  <div class="row"><span class="label">State of Residence</span><span>{_esc(state_of_residence) or "Not provided"}</span></div>
  <div class="row"><span class="label">Face Amount</span><span>${face:,.0f}</span></div>
  <div class="row"><span class="label">UW Class</span><span>{_esc((medical.get("underwriting_class") or "—").replace("_", " ").title())}</span></div>
  <div class="row"><span class="label">Tobacco</span><span>{"Yes" if medical.get("tobacco") else "No"}</span></div>
  <div class="row"><span class="label">Decision</span><span style="color:{decision_color_hex};font-weight:700;">{_esc(decision)}</span></div>
  <div class="row"><span class="label">Policy Admin Ref</span><span>{_esc(quote.policy_admin_reference or "N/A")}</span></div>"""
        modifiers_block = f"""
  <h2>Life Rating Factors</h2>
  <div class="card">
    <div class="row"><span class="label">Filing</span><span>{_esc(meta.get("filing_id") or "—")}</span></div>
    <div class="row"><span class="label">Product</span><span>{_esc(meta.get("product") or "—")}</span></div>
    <div class="row"><span class="label">UW hint</span><span>{_esc(meta.get("uw_decision_hint") or decision.lower())}</span></div>
  </div>"""
    else:
        cope_grade = str(meta.get("cope_grade", "N/A"))
        market_phase = str(meta.get("market_phase", "N/A"))
        tiv = sum((loc.building_value or 0) + (loc.contents_value or 0) + (loc.bi_value or 0) for loc in (bundle.structured.locations if bundle.structured else [])) or meta.get("tiv", 0)
        header_rows = f"""
  <div class="row"><span class="label">Line of Business</span><span>{_esc(line_label)}</span></div>
  <div class="row"><span class="label">Total Insured Value</span><span>${float(tiv):,.0f}</span></div>
  <div class="row"><span class="label">COPE Risk Grade</span><span>{_esc(cope_grade.replace("_", " ").title())}</span></div>
  <div class="row"><span class="label">Market Phase</span><span>{_esc(market_phase.replace("_", " ").title())}</span></div>
  <div class="row"><span class="label">Risk Score</span><span>{risk_pct if risk_pct is not None else "—"}/100 · {_esc(severity)}</span></div>
  <div class="row" style="border-bottom:none;"><span class="muted" style="font-size:10.5px;">0&ndash;49 Low &middot; 50&ndash;74 Moderate &middot; 75&ndash;100 High</span></div>
  <div class="row"><span class="label">Decision</span><span style="color:{decision_color_hex};font-weight:700;">{_esc(decision)}</span></div>
  <div class="row"><span class="label">Policy Admin Ref</span><span>{_esc(quote.policy_admin_reference or "N/A")}</span></div>"""
        modifiers_block = f"""
  <h2>Rate Components</h2>
  <div class="grid-2">
    <div class="card">
      <div class="card-header">Base Rate</div>
      <div class="row"><span class="label">ISO Loss Cost</span><span>${meta.get("loss_cost", 0):.4f}/$100</span></div>
      <div class="row"><span class="label">Rate per $100 TIV</span><span>${quote.rate_per_100_tiv:.4f}</span></div>
    </div>
    <div class="card">
      <div class="card-header">Modifiers</div>
      <div class="row"><span class="label">COPE</span><span>{meta.get("cope_mod_pct", 0):+.1f}%</span></div>
      <div class="row"><span class="label">Market</span><span>{meta.get("market_mod_pct", 0):+.1f}%</span></div>
      <div class="row"><span class="label">Deductible</span><span>{meta.get("deductible_credit", 0):+.1f}%</span></div>
      <div class="row"><span class="label">Loss Exp</span><span>{meta.get("loss_experience_mod_pct", 0):+.1f}%</span></div>
      <div class="row"><span class="label">Tenure</span><span>{meta.get("years_in_business_mod_pct", 0):+.1f}%</span></div>
    </div>
  </div>"""

    summary_note = ""
    if memo.summary:
        summary_note = f"""
  <div class="card summary-card">
    <div class="card-header">Underwriting Summary</div>
    <p class="summary-text">{_esc(memo.summary)}</p>
  </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Insurance Quote — {_esc(insured)}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0f; color: #e2e8f0; padding: 40px 20px; font-size: 13px; line-height: 1.55; }}
  .container {{ max-width: 860px; margin: 0 auto; background: #14141f; border-radius: 12px; padding: 32px; box-shadow: 0 4px 24px rgba(0,0,0,0.4); }}
  h1 {{ font-size: 22px; font-weight: 700; margin-bottom: 4px; color: #f8fafc; }}
  h2 {{ font-size: 15px; font-weight: 600; margin: 24px 0 8px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; }}
  .subtitle {{ color: #94a3b8; font-size: 13px; margin-bottom: 20px; }}
  .row {{ display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.06); color: #e2e8f0; }}
  .label {{ color: #94a3b8; }}
  .muted {{ color: #94a3b8; }}
  .total {{ font-size: 20px; font-weight: 700; color: #4ade80; text-align: right; margin-top: 12px; padding-top: 12px; border-top: 2px solid rgba(255,255,255,0.08); }}
  .card {{ background: rgba(255,255,255,0.04); border-radius: 8px; padding: 16px; margin-bottom: 12px; border: 1px solid rgba(255,255,255,0.06); }}
  .card-header {{ font-weight: 600; font-size: 14px; margin-bottom: 8px; color: #f1f5f9; }}
    .summary-text {{ color: #e2e8f0; font-size: 13px; line-height: 1.6; white-space: pre-wrap; }}
  table {{ width: 100%; border-collapse: collapse; color: #e2e8f0; }}
  td {{ padding: 4px 0; color: #e2e8f0; }}
  .section-title {{ font-size: 11px; text-transform: uppercase; color: #94a3b8; letter-spacing: 0.05em; margin-top: 12px; margin-bottom: 4px; }}
  .list {{ list-style: none; padding: 0; }}
  .list li {{ padding: 3px 0; color: #e2e8f0; font-size: 12px; }}
  .list li::before {{ content: "— "; color: #94a3b8; }}
  .footer {{ margin-top: 24px; padding-top: 16px; border-top: 1px solid rgba(255,255,255,0.06); font-size: 11px; color: #94a3b8; text-align: center; }}
  .badge {{ display: inline-block; background: rgba(74,222,128,0.12); color: #4ade80; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }}
  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
  .text-up {{ color: #f87171; }}
  .text-down {{ color: #4ade80; }}
  .finding {{ border-left: 3px solid #64748b; padding: 8px 10px; margin-bottom: 8px; background: rgba(255,255,255,0.03); border-radius: 0 6px 6px 0; }}
  .finding-top {{ font-size: 12px; color: #f1f5f9; }}
  .finding-desc {{ margin-top: 4px; font-size: 12px; color: #cbd5e1; line-height: 1.5; }}
  .sev {{ display: inline-block; font-size: 10px; font-weight: 700; letter-spacing: 0.04em; margin-right: 6px; }}
  .sev-critical, .sev-high {{ color: #f87171; }}
  .sev-moderate {{ color: #fbbf24; }}
  .sev-low, .sev-info {{ color: #4ade80; }}
  {WORDMARK_CSS_DARK}
  @media print {{
    {WORDMARK_CSS_PRINT}
    body {{ background: white !important; color: #0f172a !important; }}
    .container {{ box-shadow: none; background: white !important; }}
    h1, .card-header, .finding-top, td, .row, .list li, .summary-text {{ color: #0f172a !important; }}
    h2, .label, .muted, .subtitle, .section-title, .footer, .finding-desc {{ color: #334155 !important; }}
    .card, .finding {{ background: #f8fafc !important; border-color: #e2e8f0 !important; }}
    .total {{ color: #15803d !important; }}
    .text-up {{ color: #b91c1c !important; }}
    .text-down {{ color: #15803d !important; }}
    .sev-critical, .sev-high {{ color: #b91c1c !important; }}
    .sev-moderate {{ color: #b45309 !important; }}
    .sev-low, .sev-info {{ color: #15803d !important; }}
    .badge {{ background: #dcfce7 !important; color: #166534 !important; }}
  }}
</style>
</head>
<body>
<div class="container">
  <div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:4px;">
    <div>
      <h1>{_esc(insured)}</h1>
      <p class="subtitle">{_esc(subtitle)}</p>
    </div>
    <div style="text-align:right;">
      <div class="badge">Quote #{_esc(quote.policy_admin_reference or "N/A")}</div>
      <p class="muted" style="font-size:12px;margin-top:4px;">Expires {_esc(valid_until)}</p>
    </div>
  </div>

  {header_rows}
  {identity_gap_note}
  {summary_note}

  <h2>Coverages</h2>
  {coverages_html}

  {forms_html}

  <h2>Exclusions & Conditions</h2>
  <ul class="list">{exclusions_html}</ul>

  <h2>Premium Breakdown</h2>
  <div class="card">
    <div class="row"><span class="label">Base Premium</span><span>${quote.base_premium:,.2f}</span></div>
    {components_html}
    <div class="total">${quote.adjusted_premium:,.2f}</div>
  </div>

  {modifiers_block}

  <h2>Key Underwriting Findings</h2>
  {findings_html}
  {review_html}

  <div class="footer">
    <p>This quote is for informational purposes only and does not constitute a binder of insurance.</p>
    <p style="margin-top:8px;">{wordmark_html(14)} <span class="muted">&bull; Generated {_esc(today)}</span></p>
  </div>
</div>
</body>
</html>"""
