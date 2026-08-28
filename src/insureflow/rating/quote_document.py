from __future__ import annotations

from datetime import datetime, timezone
from html import escape

from insureflow.models.agents import UnderwritingMemo
from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.models import InsuranceLine, QuoteResult, line_display_name
from insureflow.rating.report_theme import (
    PDF_FONT_STACK,
    SEVERITY_COLORS,
    WORDMARK_CSS_PRINT,
    decision_color,
    wordmark_html,
)
from insureflow.underwriting.lob_rating import _derived_modifier_pct


def _esc(value: object) -> str:
    return escape(str(value if value is not None else ""))


def _detail_item(label: str, value: str, *, accent: str | None = None) -> str:
    """One label/value pair in the two-column details grid below the hero —
    short-value fields (Face Amount, UW Class, Tobacco, DOB, State, ...) read
    far better two-up than stacked one-per-line, and this is the single place
    that markup is built so every field in the grid stays visually uniform."""
    style = f' style="color:{accent};font-weight:700;"' if accent else ""
    return f'<div class="detail-item"><div class="detail-label">{_esc(label)}</div><div class="detail-value"{style}>{value}</div></div>'


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
    today = datetime.now(tz=timezone.utc).strftime("%B %d, %Y")
    valid_until = quote.quote_valid_until or "30 days from issuance"
    meta = quote.metadata or {}
    is_life = quote.line == InsuranceLine.LIFE or str(meta.get("insurance_line") or "").lower() == "life"
    date_of_birth = (named_insured.date_of_birth if named_insured else None) or meta.get("date_of_birth") or ""
    state_of_residence = (named_insured.state_of_residence if named_insured else None) or meta.get("issue_state") or ""
    line_label = line_display_name(quote.line.value)
    subtitle = f"{'Life' if is_life else 'Commercial'} Insurance Quote — Issued {today}"
    # The page headline must always be a fixed document title, never a data
    # field — "Named insured not provided" must not itself BE the headline.
    # The identity-gap callout box below (built after date_of_birth/
    # state_of_residence are known, so it can describe all three gaps
    # consistently with the Report) carries that fact instead.
    headline = insured if not insured_missing else (f"{line_label} Quote" if "insurance" in line_label.lower() else f"{line_label} Insurance Quote")
    identity_gaps: list[str] = []
    if insured_missing:
        identity_gaps.append("named insured")
    if is_life and not date_of_birth:
        identity_gaps.append("date of birth")
    if is_life and not state_of_residence:
        identity_gaps.append("state of residence")
    identity_gap_note = (
        "<div class='finding' style=\"border-left-color:#dc2626;\"><div class='finding-top'>"
        "<span class=\"finding-title\">Identity verification incomplete</span></div><p class='finding-desc'>"
        f"Missing: {_esc(', '.join(identity_gaps))}. Confirm with the producer before bind.</p></div>"
        if identity_gaps
        else ""
    )
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
            endorsements = "".join(f"<li>{_esc(e)}</li>" for e in c.endorsements) if c.endorsements else "<li class='muted-item'>None</li>"
            coverages_html += f"""
            <div class="card">
              <div class="card-header">{_esc(c.coverage_type)}</div>
              <table>
                <tr><td>Limit</td><td class='text-right'>${c.limit_amount:,.0f}</td></tr>
                <tr><td>Deductible</td><td class='text-right'>${c.deductible:,.0f}</td></tr>
                <tr><td>Premium</td><td class='text-right'>${c.premium:,.0f}</td></tr>
                {sublimits}
              </table>
              <div class="micro-label">Endorsements</div>
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
        coverages_html = '<p class="muted-item">Coverage details not available — see quote breakdown below.</p>'

    iso_forms = list(meta.get("iso_forms") or [])
    if iso_forms:
        rows = "".join(f"<tr><td>{_esc(f.get('number'))}</td><td>{_esc(f.get('title'))}</td><td class='text-right'>{_esc(f.get('edition'))}</td></tr>" for f in iso_forms)
        forms_html = f"<div class='section-header'>ISO / Form Schedule</div><div class='card'><table>{rows}</table><p class='muted-item' style='margin-top:8px;'>Jacket map only — not a filed edition date until the carrier book supplies one.</p></div>"
    else:
        forms_html = ""
    sl = meta.get("surplus_lines") or {}
    if sl:
        forms_html += (
            f"<div class='section-header'>Admitted / E&amp;S</div><div class='card'><p>{_esc(sl.get('market_status') or sl.get('status') or 'unknown')} — {_esc(sl.get('reason') or '')}</p></div>"
        )

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

    # Same 4 columns as the in-app Premium Build-up table (Rating component |
    # Applied to | Factor | Adjustment %), using the same _derived_modifier_pct()
    # function that table uses, so the PDF and in-app view can never show
    # different numbers for the same row.
    components_html = ""
    for rc in quote.schedule_modifications:
        label = _esc(rc.name.replace("_", " ").title())
        basis = _esc(rc.basis or "—")
        amount = getattr(rc, "amount", None)
        factor_display = _esc(amount) if amount is not None else "—"
        derived_pct = _derived_modifier_pct(rc)
        if derived_pct is None:
            adj_display, adj_class = "n/a", "muted-cell"
        else:
            sign = "+" if derived_pct > 0 else ""
            adj_display = f"{sign}{derived_pct:.1f}%"
            adj_class = "text-up" if derived_pct > 0 else "text-down" if derived_pct < 0 else "muted-cell"
        components_html += f"<tr><td>{label}</td><td class='basis-cell'>{basis}</td><td class='text-right'>{factor_display}</td><td class='text-right {adj_class}'>{adj_display}</td></tr>"

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
            border_color = SEVERITY_COLORS.get(sev.upper(), "#94a3b8")
            findings_html += f"""
            <div class="finding" style="border-left-color:{border_color};">
              <div class="finding-top">
                <span class="sev-chip sev-{_esc(sev)}">{_esc(sev.upper())}</span>
                <span class="finding-title">{_esc(f.title)}</span>
                <span class="finding-category">{_esc((f.category or "general").replace("_", " "))}</span>
              </div>
              <p class="finding-desc">{_esc(f.description or "")}</p>
            </div>"""
        if overflow:
            findings_html += f'<p class="muted-item">+ {len(overflow)} more lower-severity finding(s) — see the full Underwriting Report.</p>'
    else:
        findings_html = '<p class="muted-item">No underwriting findings recorded for this quote.</p>'

    review_reasons = list(memo.human_review_reasons or [])
    review_html = ""
    if review_reasons:
        items = "".join(f"<li>{_esc(r)}</li>" for r in review_reasons)
        review_html = f"""
  <div class="section-header">Referral Basis</div>
  <ul class="list">{items}</ul>"""

    if is_life:
        face = float(meta.get("face_amount") or meta.get("tiv") or 0)
        medical = meta.get("medical") or {}
        details_grid = "".join(
            [
                _detail_item("Line of Business", _esc(line_label)),
                _detail_item("Decision", _esc(decision), accent=decision_color_hex),
                _detail_item("Date of Birth", _esc(date_of_birth) or "Not provided"),
                _detail_item("State of Residence", _esc(state_of_residence) or "Not provided"),
                _detail_item("Face Amount", f"${face:,.0f}"),
                _detail_item("UW Class", _esc((medical.get("underwriting_class") or "—").replace("_", " ").title())),
                _detail_item("Tobacco", "Yes" if medical.get("tobacco") else "No"),
                _detail_item("Policy Admin Ref", _esc(quote.policy_admin_reference or "N/A")),
            ]
        )
        modifiers_block = f"""
  <div class="section-header">Life Rating Factors</div>
  <div class="card">
    <div class="kv-row"><span class="kv-label">Filing</span><span class="kv-value">{_esc(meta.get("filing_id") or "—")}</span></div>
    <div class="kv-row"><span class="kv-label">Product</span><span class="kv-value">{_esc(meta.get("product") or "—")}</span></div>
    <div class="kv-row"><span class="kv-label">UW hint</span><span class="kv-value">{_esc(meta.get("uw_decision_hint") or decision.lower())}</span></div>
  </div>"""
    else:
        cope_grade = str(meta.get("cope_grade", "N/A"))
        market_phase = str(meta.get("market_phase", "N/A"))
        tiv = sum((loc.building_value or 0) + (loc.contents_value or 0) + (loc.bi_value or 0) for loc in (bundle.structured.locations if bundle.structured else [])) or meta.get("tiv", 0)
        details_grid = "".join(
            [
                _detail_item("Line of Business", _esc(line_label)),
                _detail_item("Decision", _esc(decision), accent=decision_color_hex),
                _detail_item("Total Insured Value", f"${float(tiv):,.0f}"),
                _detail_item("COPE Risk Grade", _esc(cope_grade.replace("_", " ").title())),
                _detail_item("Market Phase", _esc(market_phase.replace("_", " ").title())),
                _detail_item("Risk Score", f"{risk_pct if risk_pct is not None else '—'}/100 &middot; {_esc(severity)}"),
                _detail_item("Policy Admin Ref", _esc(quote.policy_admin_reference or "N/A")),
            ]
        )
        modifiers_block = f"""
  <div class="section-header">Rate Components</div>
  <div class="grid-2">
    <div class="card">
      <div class="card-header">Base Rate</div>
      <div class="kv-row"><span class="kv-label">ISO Loss Cost</span><span class="kv-value">${meta.get("loss_cost", 0):.4f}/$100</span></div>
      <div class="kv-row"><span class="kv-label">Rate per $100 TIV</span><span class="kv-value">${quote.rate_per_100_tiv:.4f}</span></div>
    </div>
    <div class="card">
      <div class="card-header">Modifiers</div>
      <div class="kv-row"><span class="kv-label">COPE</span><span class="kv-value">{meta.get("cope_mod_pct", 0):+.1f}%</span></div>
      <div class="kv-row"><span class="kv-label">Market</span><span class="kv-value">{meta.get("market_mod_pct", 0):+.1f}%</span></div>
      <div class="kv-row"><span class="kv-label">Deductible</span><span class="kv-value">{meta.get("deductible_credit", 0):+.1f}%</span></div>
      <div class="kv-row"><span class="kv-label">Loss Exp</span><span class="kv-value">{meta.get("loss_experience_mod_pct", 0):+.1f}%</span></div>
      <div class="kv-row"><span class="kv-label">Tenure</span><span class="kv-value">{meta.get("years_in_business_mod_pct", 0):+.1f}%</span></div>
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
<title>{_esc(headline) if insured_missing else f"Insurance Quote — {_esc(headline)}"}</title>
<style>
  @page {{
    size: A4;
    margin: 18mm 16mm 20mm 16mm;
    @bottom-center {{
      content: "Page " counter(page) " of " counter(pages);
      font-size: 8pt;
      color: #94a3b8;
      font-family: {PDF_FONT_STACK};
    }}
  }}

  /* ── Type scale: 9pt body / 11pt subheader / 14pt section header / 18pt title ── */
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: {PDF_FONT_STACK};
    background: #ffffff;
    color: #1e293b;
    padding: 0;
    font-size: 9pt;
    line-height: 1.55;
    -webkit-font-smoothing: antialiased;
  }}
  h1 {{ font-size: 18pt; font-weight: 700; color: #0f172a; }}
  .subtitle {{ color: #64748b; font-size: 9pt; margin-top: 2px; }}

  /* ── Document header ── */
  .doc-header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding-bottom: 12px;
    border-bottom: 2px solid #0f172a;
    margin-bottom: 14px;
  }}
  .doc-header-right {{ text-align: right; }}
  .quote-ref {{ font-size: 9pt; font-weight: 700; color: #0f172a; }}
  .quote-meta {{ font-size: 8pt; color: #64748b; margin-top: 2px; }}

  /* ── Hero: decision / face amount / premium, scannable before anything else ── */
  .hero {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    border: 1.5px solid {decision_color_hex}55;
    background: {decision_color_hex}0d;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 16px;
  }}
  .hero-decision-block {{ min-width: 140px; }}
  .hero-eyebrow {{ font-size: 8pt; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: #64748b; }}
  .hero-decision {{ font-size: 22pt; font-weight: 800; letter-spacing: -0.01em; color: {decision_color_hex}; text-transform: uppercase; line-height: 1.15; margin-top: 2px; }}
  /* display:table, not flex — WeasyPrint's flexbox can collapse the gap
     between nested flex children (two hero numbers rendered on top of each
     other); table-cell spacing is unambiguous and well-supported. */
  .hero-stats {{ display: table; border-collapse: separate; border-spacing: 28px 0; }}
  .hero-stat {{ display: table-cell; text-align: right; white-space: nowrap; }}
  .hero-stat-value {{ font-size: 16pt; font-weight: 700; color: #0f172a; line-height: 1.2; }}
  .hero-stat-label {{ font-size: 8pt; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 2px; }}

  /* ── Section headers: uniform spacing + weight for every major section ── */
  .section-header {{
    font-size: 14pt;
    font-weight: 700;
    color: #0f172a;
    margin: 22px 0 10px 0;
    padding-bottom: 5px;
    border-bottom: 1.5px solid #e2e8f0;
    break-after: avoid;
  }}
  .section-header:first-of-type {{ margin-top: 0; }}

  /* ── Two-column details grid for short-value fields ── */
  .details-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0 24px;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 4px 16px;
    margin-bottom: 4px;
  }}
  .detail-item {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding: 7px 0;
    border-bottom: 1px solid #f1f5f9;
  }}
  .detail-item:nth-last-child(-n+2) {{ border-bottom: none; }}
  .detail-label {{ color: #64748b; font-size: 9pt; }}
  .detail-value {{ font-weight: 500; font-size: 9pt; text-align: right; }}

  /* ── Cards ── */
  .card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 14px; margin-bottom: 10px; break-inside: avoid; page-break-inside: avoid; }}
  .card-header {{ font-weight: 600; font-size: 11pt; margin-bottom: 8px; color: #0f172a; }}
  .summary-text {{ color: #1e293b; font-size: 9pt; line-height: 1.6; white-space: pre-wrap; }}
  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}

  /* ── kv rows (inside cards) ── */
  .kv-row {{ display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #f1f5f9; }}
  .kv-row:last-child {{ border-bottom: none; }}
  .kv-label {{ color: #64748b; }}
  .kv-value {{ font-weight: 500; text-align: right; }}

  /* ── Tables ── */
  table {{ width: 100%; border-collapse: collapse; font-size: 9pt; }}
  td {{ padding: 6px 4px; border-bottom: 1px solid #f1f5f9; }}
  tr:last-child td {{ border-bottom: none; }}
  .pl-8 {{ padding-left: 8px; color: #64748b; }}
  .micro-label {{ font-size: 8pt; text-transform: uppercase; color: #64748b; letter-spacing: 0.05em; margin-top: 10px; margin-bottom: 4px; }}

  /* ── Premium breakdown table: ruled + shaded rows, wide "Applied To" column ── */
  .premium-table th {{
    text-align: left; font-size: 8pt; text-transform: uppercase; letter-spacing: 0.04em;
    color: #64748b; font-weight: 600; padding: 6px 4px; border-bottom: 2px solid #cbd5e1;
  }}
  .premium-table col.col-component {{ width: 26%; }}
  .premium-table col.col-basis {{ width: 38%; }}
  .premium-table col.col-factor {{ width: 16%; }}
  .premium-table col.col-adjustment {{ width: 20%; }}
  .premium-table th.text-right, .premium-table td.text-right {{ text-align: right; }}
  .premium-table tbody tr:nth-child(even) {{ background: #f8fafc; }}
  .premium-table td {{ padding: 7px 4px; }}
  .basis-cell {{ color: #64748b; font-size: 8.5pt; }}
  .muted-cell {{ color: #94a3b8; }}
  .premium-total {{ display: flex; justify-content: space-between; align-items: baseline; font-size: 16pt; font-weight: 700; color: #15803d; margin-top: 12px; padding-top: 12px; border-top: 2px solid #0f172a; }}
  .premium-total-label {{ font-size: 9pt; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.04em; }}

  /* ── Lists ── */
  .list {{ list-style: none; padding: 0; }}
  .list li {{ padding: 3px 0; color: #1e293b; font-size: 9pt; }}
  .list li::before {{ content: "\\2014\\a0"; color: #94a3b8; }}
  .muted-item {{ color: #64748b; font-size: 9pt; }}

  /* ── Findings: severity chip + bold title + lighter body, real spacing ── */
  .finding {{ border-left: 3px solid #94a3b8; padding: 9px 12px; margin-bottom: 8px; background: #f8fafc; border-radius: 0 6px 6px 0; break-inside: avoid; page-break-inside: avoid; }}
  /* Plain inline flow, not flex — WeasyPrint's flexbox can drop the
     margin-left:auto push (the category tag lands with no gap after the
     title); ordinary inline-box spacing is unambiguous and well-supported. */
  .finding-top {{ line-height: 1.6; }}
  .finding-title {{ font-weight: 600; font-size: 11pt; color: #0f172a; margin-left: 6px; }}
  .finding-category {{ font-size: 8pt; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.03em; float: right; padding-top: 3px; }}
  .finding-desc {{ margin-top: 4px; font-size: 9pt; color: #475569; line-height: 1.5; font-weight: 400; }}
  .sev-chip {{ display: inline-block; font-size: 7.5pt; font-weight: 700; letter-spacing: 0.05em; padding: 2px 7px; border-radius: 4px; }}
  .sev-critical {{ background: #fee2e2; color: #b91c1c; }}
  .sev-high {{ background: #ffedd5; color: #c2410c; }}
  .sev-moderate {{ background: #fef3c7; color: #b45309; }}
  .sev-low, .sev-info {{ background: #dcfce7; color: #166534; }}

  /* ── Footer ── */
  .footer {{ margin-top: 26px; padding-top: 14px; border-top: 1px solid #e2e8f0; font-size: 8pt; color: #94a3b8; text-align: center; }}
  .footer p {{ margin-bottom: 2px; }}

  .text-up {{ color: #b91c1c; }}
  .text-down {{ color: #15803d; }}
  {WORDMARK_CSS_PRINT}
</style>
</head>
<body>
<!-- ═══════ Document header ═══════ -->
<div class="doc-header">
  <div>
    <h1>{_esc(headline)}</h1>
    <p class="subtitle">{_esc(subtitle)}</p>
  </div>
  <div class="doc-header-right">
    <div class="quote-ref">Quote #{_esc(quote.policy_admin_reference or "N/A")}</div>
    <p class="quote-meta">Expires {_esc(valid_until)}</p>
  </div>
</div>

<!-- ═══════ Hero: decision + face amount + premium, scannable before findings/rating factors ═══════ -->
<div class="hero">
  <div class="hero-decision-block">
    <div class="hero-eyebrow">Underwriting Decision</div>
    <div class="hero-decision">{_esc(decision)}</div>
  </div>
  <div class="hero-stats">
    <div class="hero-stat">
      <div class="hero-stat-value">${float(meta.get("face_amount") or meta.get("tiv") or 0):,.0f}</div>
      <div class="hero-stat-label">Face Amount</div>
    </div>
    <div class="hero-stat">
      <div class="hero-stat-value">${quote.adjusted_premium:,.0f}</div>
      <div class="hero-stat-label">Indicated Premium</div>
    </div>
  </div>
</div>

<div class="details-grid">{details_grid}</div>
{identity_gap_note}
{summary_note}

<div class="section-header">Coverages</div>
{coverages_html}

{forms_html}

<div class="section-header">Premium Breakdown</div>
<div class="card">
  <div class="kv-row"><span class="kv-label">Base Premium</span><span class="kv-value">${quote.base_premium:,.2f}</span></div>
  <table class="premium-table" style="margin-top:8px;">
    <colgroup>
      <col class="col-component"><col class="col-basis"><col class="col-factor"><col class="col-adjustment">
    </colgroup>
    <thead>
      <tr><th>Rating Component</th><th>Applied To</th><th class="text-right">Factor</th><th class="text-right">Adjustment</th></tr>
    </thead>
    <tbody>
      {components_html}
    </tbody>
  </table>
  <div class="premium-total"><span class="premium-total-label">Adjusted Premium</span><span>${quote.adjusted_premium:,.2f}</span></div>
</div>

{modifiers_block}

<div class="section-header">Key Underwriting Findings</div>
{findings_html}
{review_html}

<div class="section-header">Exclusions &amp; Conditions</div>
<ul class="list">{exclusions_html}</ul>

<div class="footer">
  <p>This quote is for informational purposes only and does not constitute a binder of insurance.</p>
  <p style="margin-top:8px;">{wordmark_html(11)} <span class="muted-item">&bull; Generated {_esc(today)}</span></p>
</div>
</body>
</html>"""
