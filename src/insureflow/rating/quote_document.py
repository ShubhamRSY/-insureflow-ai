from __future__ import annotations

from datetime import datetime, timezone

from insureflow.models.agents import UnderwritingMemo
from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.models import QuoteResult


def generate_quote_html(
    bundle: SubmissionBundle,
    memo: UnderwritingMemo,
    quote: QuoteResult,
) -> str:
    insured = bundle.structured.named_insured.legal_name if bundle.structured and bundle.structured.named_insured else "Named Insured"
    today = datetime.now(tz=timezone.utc).strftime("%B %d, %Y")
    valid_until = quote.quote_valid_until or "30 days from issuance"

    # Coverages
    coverages_html = ""
    if bundle.structured and bundle.structured.coverages:
        for c in bundle.structured.coverages:
            sublimits = "".join(f"<tr><td class='pl-8'>{k}</td><td class='text-right'>${v:,.0f}</td></tr>" for k, v in c.sublimits.items())
            endorsements = "".join(f"<li>{e}</li>" for e in c.endorsements) if c.endorsements else "<li class='text-slate-400'>None</li>"
            coverages_html += f"""
            <div class="card">
              <div class="card-header">{c.coverage_type}</div>
              <table>
                <tr><td>Limit</td><td class='text-right'>${c.limit_amount:,.0f}</td></tr>
                <tr><td>Deductible</td><td class='text-right'>${c.deductible:,.0f}</td></tr>
                <tr><td>Premium</td><td class='text-right'>${c.premium:,.0f}</td></tr>
                {sublimits}
              </table>
              <div class="section-title">Endorsements</div>
              <ul class="list">{endorsements}</ul>
            </div>"""
    else:
        coverages_html = '<p class="text-slate-400">Coverage details not available — see quote breakdown below.</p>'

    # Exclusions from memo conditions + compliance findings
    exclusions: list[str] = []
    if memo.recommendation and memo.recommendation.conditions:
        exclusions.extend(memo.recommendation.conditions)
    for f in memo.key_findings:
        if f.category in ("compliance", "coverage") and "exclusion" in (f.title + f.description).lower():
            exclusions.append(f"{f.title}: {f.description}")
    if not exclusions:
        exclusions.append("Standard policy exclusions apply. See policy form for full details.")
    exclusions_html = "".join(f"<li>{e}</li>" for e in exclusions)

    # Premium breakdown
    components_html = ""
    for rc in quote.schedule_modifications:
        pct = rc.modifier_pct
        label = rc.name.replace("_", " ").title()
        if pct > 0:
            components_html += f"<tr><td>{label}</td><td class='text-right text-red-400'>+{pct:.1f}%</td></tr>"
        elif pct < 0:
            components_html += f"<tr><td>{label}</td><td class='text-right text-green-400'>{pct:.1f}%</td></tr>"
        else:
            components_html += f"<tr><td>{label}</td><td class='text-right text-slate-400'>{pct:.1f}%</td></tr>"

    # Metadata
    meta = quote.metadata or {}
    cope_grade = meta.get("cope_grade", "N/A")
    market_phase = meta.get("market_phase", "N/A")
    tiv = sum((l.building_value or 0) + (l.contents_value or 0) + (l.bi_value or 0) for l in (bundle.structured.locations if bundle.structured else [])) or quote.metadata.get("tiv", 0)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Insurance Quote — {insured}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0f; color: #e2e8f0; padding: 40px 20px; font-size: 13px; line-height: 1.5; }}
  .container {{ max-width: 800px; margin: 0 auto; background: #14141f; border-radius: 12px; padding: 32px; box-shadow: 0 4px 24px rgba(0,0,0,0.4); }}
  h1 {{ font-size: 22px; font-weight: 700; margin-bottom: 4px; }}
  h2 {{ font-size: 15px; font-weight: 600; margin: 24px 0 8px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; }}
  .subtitle {{ color: #64748b; font-size: 13px; margin-bottom: 20px; }}
  .row {{ display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.04); }}
  .label {{ color: #94a3b8; }}
  .total {{ font-size: 20px; font-weight: 700; color: #4ade80; text-align: right; margin-top: 12px; padding-top: 12px; border-top: 2px solid rgba(255,255,255,0.08); }}
  .card {{ background: rgba(255,255,255,0.03); border-radius: 8px; padding: 16px; margin-bottom: 12px; }}
  .card-header {{ font-weight: 600; font-size: 14px; margin-bottom: 8px; color: #f1f5f9; }}
  table {{ width: 100%; border-collapse: collapse; }}
  td {{ padding: 4px 0; }}
  .section-title {{ font-size: 11px; text-transform: uppercase; color: #64748b; letter-spacing: 0.05em; margin-top: 12px; margin-bottom: 4px; }}
  .list {{ list-style: none; padding: 0; }}
  .list li {{ padding: 3px 0; color: #cbd5e1; font-size: 12px; }}
  .list li::before {{ content: "— "; color: #64748b; }}
  .footer {{ margin-top: 24px; padding-top: 16px; border-top: 1px solid rgba(255,255,255,0.06); font-size: 11px; color: #64748b; text-align: center; }}
  .badge {{ display: inline-block; background: rgba(74,222,128,0.12); color: #4ade80; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }}
  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
  @media print {{ body {{ background: white; color: #1e293b; }} .container {{ box-shadow: none; background: white; }} .card {{ background: #f8fafc; }} .label {{ color: #64748b; }} .subtitle {{ color: #64748b; }} h2 {{ color: #475569; }} .total {{ color: #16a34a; }} .list li {{ color: #334155; }} .footer {{ color: #94a3b8; }} td {{ color: #1e293b; }} }}
</style>
</head>
<body>
<div class="container">
  <div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:4px;">
    <div>
      <h1>{insured}</h1>
      <p class="subtitle">Commercial Insurance Quote &mdash; Issued {today}</p>
    </div>
    <div style="text-align:right;">
      <div class="badge">Quote #{quote.policy_admin_reference or "N/A"}</div>
      <p style="color:#f59e0b;font-size:12px;margin-top:4px;">Expires {valid_until}</p>
    </div>
  </div>

  <div class="row"><span class="label">Line of Business</span><span>{quote.line.value.replace("_", " ").title()}</span></div>
  <div class="row"><span class="label">Total Insured Value</span><span>${tiv:,.0f}</span></div>
  <div class="row"><span class="label">COPE Risk Grade</span><span>{cope_grade.replace("_", " ").title()}</span></div>
  <div class="row"><span class="label">Market Phase</span><span>{market_phase.replace("_", " ").title()}</span></div>
  <div class="row"><span class="label">Policy Admin Ref</span><span>{quote.policy_admin_reference or "N/A"}</span></div>

  <h2>Coverages</h2>
  {coverages_html}

  <h2>Exclusions & Conditions</h2>
  <ul class="list">{exclusions_html}</ul>

  <h2>Premium Breakdown</h2>
  <div class="card">
    <div class="row"><span class="label">Base Premium</span><span>${quote.base_premium:,.2f}</span></div>
    {components_html}
    <div class="total">${quote.adjusted_premium:,.2f}</div>
  </div>

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
  </div>

  <div class="footer">
    <p>This quote is for informational purposes only and does not constitute a binder of insurance.</p>
    <p style="margin-top:4px;">InsureFlow AI &bull; Generated {today}</p>
  </div>
</div>
</body>
</html>"""
