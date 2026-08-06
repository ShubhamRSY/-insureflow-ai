"""Issuance document HTML generators — binder, policy worksheet, certificate.

All three documents are rendered from a single structured context so the
binder (temporary coverage), the policy worksheet (data entry package for
the policy unit), and the certificate of insurance (proof-of-coverage
for third parties) stay consistent with one another.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

_STYLE = """\
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f1f5f9; color: #0f172a; padding: 32px 16px; font-size: 12px; line-height: 1.5; }
  .page { max-width: 800px; margin: 0 auto; background: #ffffff; border-radius: 8px; box-shadow: 0 2px 12px rgba(15,23,42,0.08); padding: 40px 48px; }
  h1 { font-size: 20px; font-weight: 700; margin-bottom: 2px; }
  h2 { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #64748b; margin: 24px 0 10px; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; }
  .subtitle { color: #475569; font-size: 13px; margin-bottom: 20px; }
  .brand { text-align: right; }
  .brand p { font-weight: 700; font-size: 15px; }
  .brand span { color: #64748b; font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; }
  .doc-id { text-align: right; color: #64748b; font-size: 11px; margin-top: 4px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
  table { width: 100%; border-collapse: collapse; margin: 8px 0 4px; }
  td, th { padding: 7px 10px; text-align: left; border-bottom: 1px solid #e2e8f0; vertical-align: top; }
  th { font-size: 10px; text-transform: uppercase; letter-spacing: 0.06em; color: #64748b; background: #f8fafc; }
  .row { display: flex; justify-content: space-between; padding: 7px 0; border-bottom: 1px solid #f1f5f9; }
  .label { color: #64748b; }
  .total { display: flex; justify-content: space-between; padding: 10px 0; font-weight: 700; font-size: 14px; border-top: 2px solid #0f172a; margin-top: 6px; }
  .box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 14px 16px; margin: 10px 0; }
  .box .box-title { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #64748b; margin-bottom: 6px; }
  ul { padding-left: 18px; }
  li { padding: 2px 0; }
  .muted { color: #64748b; }
  .footer { margin-top: 28px; padding-top: 14px; border-top: 1px solid #e2e8f0; font-size: 10px; color: #64748b; text-align: center; }
  .badge { display: inline-block; background: #e0f2fe; color: #0369a1; padding: 2px 10px; border-radius: 999px; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 0 24px; }
  .signature { margin-top: 40px; display: flex; justify-content: space-between; gap: 24px; }
  .signature div { flex: 1; }
  .signature .line { border-top: 1px solid #0f172a; margin-top: 36px; padding-top: 4px; font-size: 10px; color: #64748b; text-align: center; }
  @media print { body { background: white; padding: 0; } .page { box-shadow: none; border-radius: 0; } }
"""


def _shell(title: str, badge: str, content_html: str, footer_html: str, doc_id: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>{_STYLE}</style>
</head>
<body>
<div class="page">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <div>
      <h1>{title}</h1>
      <p class="subtitle">Rytera &middot; {badge}</p>
    </div>
    <div class="brand">
      <p>Rytera</p>
      <span>AI Underwriting</span>
      {f'<div class="doc-id">{doc_id}</div>' if doc_id else ""}
    </div>
  </div>
  {content_html}
  <div class="footer">{footer_html}</div>
</div>
</body>
</html>"""


def _coverages_html(coverages: list[dict[str, Any]]) -> str:
    if not coverages:
        return '<div class="box"><div class="box-title">Coverages</div><p class="muted">Coverage schedule not available — see policy form.</p></div>'
    rows = ""
    for c in coverages:
        sublimits = "".join(f"<tr><td class='muted'>&nbsp;&nbsp;&nbsp;{k}</td><td style='text-align:right;'>${float(v):,.0f}</td></tr>" for k, v in (c.get("sublimits") or {}).items())
        deductible = c.get("deductible")
        ded_text = f"${float(deductible):,.0f}" if deductible else "—"
        rows += f"""<tr>
      <td><strong>{c.get("coverage_type") or "Coverage"}</strong></td>
      <td style='text-align:right;'>${float(c.get("limit_amount") or 0):,.0f}</td>
      <td style='text-align:right;'>{ded_text}</td>
      <td style='text-align:right;'>${float(c.get("premium") or 0):,.0f}</td>
    </tr>{sublimits}"""
    return f"""<table>
    <tr><th>Coverage</th><th style='text-align:right;'>Limit</th><th style='text-align:right;'>Deductible</th><th style='text-align:right;'>Premium</th></tr>
    {rows}
  </table>"""


def _conditions_html(conditions: list[str]) -> str:
    if not conditions:
        return '<li class="muted">Standard policy terms and conditions apply.</li>'
    return "".join(f"<li>{c}</li>" for c in conditions)


def generate_binder_html(ctx: dict[str, Any]) -> str:
    """Temporary binder of insurance — puts coverage into effect immediately.

    Bound automatically at bind time; superseded by the issued policy.
    """
    insured = ctx.get("insured_name") or "Named Insured"
    policy_number = ctx.get("policy_number") or "—"
    effective = ctx.get("effective_date") or "—"
    expiry = ctx.get("expiry_date") or "—"
    premium = float(ctx.get("premium") or 0)
    tiv = float(ctx.get("tiv") or 0)
    bound_by = ctx.get("bound_by") or ""
    bound_at = ctx.get("bound_at") or ""
    line = (ctx.get("line_of_business") or "insurance").replace("_", " ").title()

    header = f"""<div class="box">
    <div class="box-title">Binder of Insurance &mdash; Temporary Coverage</div>
    <div class="grid-2">
      <div><div class="row"><span class="label">Named Insured</span><span>{insured}</span></div>
      <div class="row"><span class="label">Producer / Broker</span><span>{ctx.get("broker_name") or "—"}</span></div>
      <div class="row"><span class="label">Line of Business</span><span>{line}</span></div>
      <div class="row"><span class="label">Policy Number</span><span>{policy_number}</span></div></div>
      <div><div class="row"><span class="label">Effective Date</span><span>{effective}</span></div>
      <div class="row"><span class="label">Expiry Date</span><span>{expiry}</span></div>
      <div class="row"><span class="label">Total Insured Value</span><span>${tiv:,.0f}</span></div>
      <div class="row"><span class="label">Bound Premium</span><span>${premium:,.2f}</span></div></div>
    </div>
  </div>"""

    content = f"""
  {header}

  <h2>Coverages Under Binder</h2>
  {_coverages_html(ctx.get("coverages") or [])}

  <h2>Binder Conditions</h2>
  <ul>{_conditions_html(ctx.get("conditions") or [])}</ul>

  <h2>Effective Terms</h2>
  <div class="box">
    <p>This binder confirms that coverage is in force from <strong>{effective}</strong> through <strong>{expiry}</strong> on the terms
    and conditions described above and in the underlying underwriting file. It is a temporary contract of insurance and will be
    superseded by the formal policy issued by the carrier. Coverage may be cancelled by either party on written notice in
    accordance with the policy form.</p>
  </div>

  <div class="signature">
    <div><div class="line">Licensed Underwriter / Binder Signatory — {bound_by or ""}</div></div>
    <div><div class="line">Date — {bound_at or ""}</div></div>
  </div>"""

    return _shell(
        "Binder of Insurance",
        "Temporary Coverage in Effect",
        content,
        f"Rytera &middot; Generated {datetime.now(tz=timezone.utc).strftime('%B %d, %Y')} &middot; This binder does not amend the policy form.",
        doc_id=f"Binder {policy_number}",
    )


def generate_policy_worksheet_html(ctx: dict[str, Any]) -> str:
    """Policy worksheet for the policy unit — data entry + statistical coding."""
    insured = ctx.get("insured_name") or "Named Insured"
    policy_number = ctx.get("policy_number") or "—"
    effective = ctx.get("effective_date") or "—"
    expiry = ctx.get("expiry_date") or "—"
    premium = float(ctx.get("premium") or 0)
    tiv = float(ctx.get("tiv") or 0)

    rows = ""
    for k, v in [
        ("Named Insured", insured),
        ("Producer / Broker", ctx.get("broker_name") or "—"),
        ("Policy Number", policy_number),
        ("Line of Business", (ctx.get("line_of_business") or "insurance").replace("_", " ").title()),
        ("Effective Date", effective),
        ("Expiry Date", expiry),
        ("Total Insured Value", f"${tiv:,.0f}"),
        ("Annual Premium", f"${premium:,.2f}"),
        ("Policy Admin Reference", ctx.get("policy_admin_reference") or "—"),
        ("Primary State", ctx.get("primary_state") or "—"),
        ("NAICS Code", ctx.get("naics_code") or "—"),
        ("Bound By", ctx.get("bound_by") or ""),
    ]:
        rows += f'<tr><td class="label">{k}</td><td>{v}</td></tr>'

    content = f"""
  <h2>Policy Data Entry Record</h2>
  <table>
    {rows}
  </table>

  <h2>Coverage Schedule</h2>
  {_coverages_html(ctx.get("coverages") or [])}

  <h2>Accounting &amp; Statistical Coding Notes</h2>
  <div class="box">
    <p>Enter the policy in the policy administration system using the policy number above and the premium indicated. Code the
    account for statutory and statistical filing (ISO / NCCI as applicable) using the line of business, primary state, and NAICS
    code shown. Route the binder to the policy unit for formal policy issuance before the binder expiry date.</p>
  </div>

  <h2>Underwriting Conditions Carried Into the Policy</h2>
  <ul>{_conditions_html(ctx.get("conditions") or [])}</ul>
  """

    return _shell(
        "Policy Worksheet",
        "Policy Unit Package",
        content,
        f"Rytera &middot; Generated {datetime.now(tz=timezone.utc).strftime('%B %d, %Y')}",
        doc_id=f"Worksheet {policy_number}",
    )


def generate_certificate_html(ctx: dict[str, Any]) -> str:
    """Certificate of insurance — proof of coverage for third parties."""
    insured = ctx.get("insured_name") or "Named Insured"
    policy_number = ctx.get("policy_number") or "—"
    effective = ctx.get("effective_date") or "—"
    expiry = ctx.get("expiry_date") or "—"
    tiv = float(ctx.get("tiv") or 0)

    rows = ""
    for c in ctx.get("coverages") or []:
        rows += f"""<tr>
      <td>{c.get("coverage_type") or "Coverage"}</td>
      <td>${float(c.get("limit_amount") or 0):,.0f}</td>
      <td>{c.get("deductible") and f"${float(c.get('deductible')):,.0f}" or "—"}</td>
    </tr>"""
    if not rows:
        rows = '<tr><td class="muted" colspan="3">Coverage schedule not available.</td></tr>'

    content = f"""
  <div class="box">
    <div class="box-title">Certificate of Insurance</div>
    <div class="grid-2">
      <div><div class="row"><span class="label">Named Insured</span><span>{insured}</span></div>
      <div class="row"><span class="label">Certificate Holder</span><span>{ctx.get("certificate_holder") or "As Requested"}</span></div></div>
      <div><div class="row"><span class="label">Policy Number</span><span>{policy_number}</span></div>
      <div class="row"><span class="label">Policy Period</span><span>{effective} to {expiry}</span></div></div>
    </div>
  </div>

  <h2>Coverages</h2>
  <table>
    <tr><th>Coverage</th><th>Limit</th><th>Deductible</th></tr>
    {rows}
  </table>

  <h2>Notice</h2>
  <div class="box">
    <p>This certificate is issued as a matter of information only and confers no rights upon the certificate holder. This
    certificate does not amend, extend or alter the coverage afforded by the policies below. The insurance afforded is subject
    to the terms, conditions, exclusions, and limits of the policy. Total insured value ${tiv:,.0f}.</p>
  </div>
  """

    return _shell(
        "Certificate of Insurance",
        "Proof of Coverage",
        content,
        f"Rytera &middot; Issued {datetime.now(tz=timezone.utc).strftime('%B %d, %Y')}",
        doc_id=f"Certificate {policy_number}",
    )


def build_issuance_context(summary: dict[str, Any], memo: dict[str, Any], bundle: dict[str, Any] | None, policy: dict[str, Any]) -> dict[str, Any]:
    """Normalize pipeline artifacts into the shared issuance context dict."""
    quote = summary.get("quote") or {}
    locations = (bundle or {}).get("structured", {}).get("locations") or []
    coverages_raw = (bundle or {}).get("structured", {}).get("coverages") or []
    coverages = []
    for c in coverages_raw:
        if not isinstance(c, dict):
            continue
        coverages.append(
            {
                "coverage_type": c.get("coverage_type") or "Coverage",
                "limit_amount": c.get("limit_amount") or 0,
                "deductible": c.get("deductible") or 0,
                "premium": c.get("premium") or 0,
                "sublimits": c.get("sublimits") or {},
            }
        )
    if not coverages and quote:
        coverages.append(
            {
                "coverage_type": (summary.get("insurance_line") or "Coverage").replace("_", " ").title(),
                "limit_amount": summary.get("tiv") or 0,
                "deductible": 0,
                "premium": quote.get("adjusted_premium") or quote.get("base_premium") or 0,
                "sublimits": {},
            }
        )
    conditions = list(memo.get("conditions") or summary.get("open_conditions") or [])
    for f in memo.get("key_findings") or []:
        if isinstance(f, dict) and (f.get("category") in ("compliance", "coverage")) and "exclusion" in (str(f.get("title", "")) + str(f.get("description", ""))).lower():
            conditions.append(f"{f.get('title')}: {f.get('description')}")

    loc = locations[0] if locations else {}
    primary_state = loc.get("state") or ""
    naics = ((bundle or {}).get("structured", {}).get("risk_profile") or {}).get("naics_code") or ""

    return {
        "insured_name": summary.get("insured_name") or (memo.get("insured_name") or "Named Insured"),
        "broker_name": summary.get("broker_name") or "",
        "policy_number": policy.get("policy_number", ""),
        "line_of_business": summary.get("insurance_line") or summary.get("product_line") or "insurance",
        "effective_date": policy.get("effective_date", ""),
        "expiry_date": policy.get("expiry_date", ""),
        "premium": policy.get("premium") or quote.get("adjusted_premium") or quote.get("base_premium") or 0,
        "tiv": summary.get("tiv") or quote.get("tiv") or 0,
        "bound_by": policy.get("bound_by", ""),
        "bound_at": policy.get("bound_at", ""),
        "policy_admin_reference": quote.get("policy_admin_reference") or policy.get("policy_admin_reference", ""),
        "primary_state": primary_state,
        "naics_code": naics,
        "coverages": coverages,
        "conditions": conditions,
        "certificate_holder": policy.get("certificate_holder", ""),
    }
