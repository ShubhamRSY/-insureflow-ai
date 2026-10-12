# Pilot loss and pricing assumptions

- Author: @actuary
- Date: 2026-10-09
- Status: In review (@head-of-underwriting)
- Re: T-011, D-002
- These are **planning assumptions**. They are not this company's experience. T-004 is not done. There is no triangle. Do not quote these as an indication.

## Pricing rule

v1 does not map a score to a price. Premium is the **filed rate** for the class, territory, construction, protection, and limits. No schedule credit, no schedule debit, no model relativity.

If a later model changes price or a rating factor, that is a new filing (@compliance C-05), not a config change.

## Permissible loss ratio (planning)

\[
\text{Permissible LR} = 1 - c - a - t - p - f
\]

| Item | Planning value | What it is |
|---|---|---|
| Commission \(c\) | 0.15 | Broker |
| Other acquisition \(a\) | 0.05 | Not commission |
| Premium tax and fees \(t\) | 0.03 | Blend, not a state filing |
| Profit provision \(p\) | 0.05 | |
| Fixed expense \(f\) | 0.07 | Treated as a ratio only at this premium size |
| **Permissible LR** | **0.65** | Sum of deductions = 0.35 |

The 0.65 is only as good as those expense inputs. @head-of-underwriting should replace them with the actual filing expense provisions before a live quote. Until then I will not bless a number tighter than this.

## Expected loss ratio by band (planning ranges)

I will not put office and artisan on one expected LR. The zero-claim, one-location, TIV ≤ $1M gate is a different risk than "small package."

| Segment | In proposed auto-quote? | Planning LR | Range | vs 0.65 permissible |
|---|---|---|---|---|
| Office, dry retail, light wholesale, all auto-quote gates | Yes, as drafted | 0.58 | 0.52–0.64 | Inside, about 7 pts of margin |
| Artisan contractors, even with no roofing and zero claims | Draft says yes | 0.72 | 0.65–0.85 | Fails |
| Habitational, any unit count | Referral | 0.70 | 0.62–0.82 | Do not auto-quote |
| Restaurant / cooking | Senior referral | Not estimated | — | Do not auto-quote |

Artisan fails because class-code contamination and liability severity dominate a thin premium. A point estimate of 0.72 is not credible. The range sits on or above permissible. That is enough to refuse auto-quote.

## Rule I need in D-002

Auto-quote only where the planning LR is at least **5 points under** permissible. With permissible 0.65, the cap is **0.60**. The office / dry retail / light wholesale band passes (0.58). Artisan does not. Habitational does not.

## Adverse selection

The gates keep the clean office risks in the machine and push claims, contractors, and habitational to humans. The human queue will look worse even if both underwrite correctly. Report LR **separately** for auto-quoted vs referred business. Do not score underwriters on the residual book.

A pilot will not have a credible LR. Do not pretend 30 quotes are an indication. Leading checks until we have either 24 months or 200 earned exposures in the band, whichever comes first:

- Quoted premium vs the filed manual premium for the same rating factors (must match).
- Share of auto-quotes that fail a re-check at bind.
- Claim counts, not LR.

No PML cap from me this round. There is no catastrophe model output. Wildfire and convective storm stay a referral, as the appetite draft says.

## Review of D-002

SUPPORT the no-auto-decline rule, the filed-rate rule, and coastal wind out of the pilot.

OBJECTION to artisan contractors inside auto-quote.

CONCERN: one expected LR for the whole auto-quote band would hide the artisan result. I will not sign that number.
