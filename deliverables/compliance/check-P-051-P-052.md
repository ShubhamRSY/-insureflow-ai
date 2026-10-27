# @compliance check: P-051 and P-052 (D-098)

Date: 2026-10-16. Reviewer: @compliance (simulated advisor). Code at d53e250; read `workbench.py` (`_match`, word lists, `confirm_html`, `_no_send_reason`, `_send_html`, `act`), `package.py` (`seniors`, `confirm_problem`, `market_confirmation`, `confirm_market`, `build_package`, `send_to_carrier`), `underwriters.json`, `carrier-match.md`, `appetite-guide.md`. The check was run in memory only (`.venv/bin/python`, nothing written; D-069).

## Verdict: OBJECTION (scoped to the P-052 confirm path on AG:51 files). This is not a production approval, and the T-027 veto stands.

P-051 passes all of 1(a) to 1(d). P-052 passes everything except one gap, H1.

## What I re-ran (synthetic reports, $1,000,000 TIV, every field filled)

| Operations text | Route | Market confirm offered? |
|---|---|---|
| office building with ground-floor pub | senior_referral | No (W1 word) |
| retail store and cocktail lounge | senior_referral | No (W1 word) |
| office building, no utilities | senior_referral | **Yes** |
| office, unoccupied | senior_referral | **Yes** |
| fully vacant building | senior_referral | **Yes** |
| office building, utilities disconnected | senior_referral | **Yes** |
| thrift shop / clothing store | carrier_a | No (not a referral) |
| office and retail | senior_referral | Yes (correct) |

## High

**H1. A senior can confirm a market for a file the written guide prohibits (no utilities, full vacancy), and that file can then be sent to a carrier.**
- Rule: AG:51 lists "Fully vacant property, and buildings with no utilities" under **Prohibited**. Knock-out 1 says a prohibited class is declined only by a human. D-098 2 says the confirm is "never available for prohibited words". D-057/D-060 say prohibited is never overridable.
- Defect: `confirm_problem()` checks only `PROHIBITED` (W1). The W2e words (`vacant`, `unoccupied`, `NO_UTILITIES`) are left out, so the confirm form appears. `build_package()` then names whichever carrier the senior picked, Carrier A included.
- Risk: placing a risk the written guidelines prohibit, through a path presented as compliant. That means the guidelines are not applied consistently, the audit trail is inconsistent, and the agency may be in breach of its carrier agreement. [NEEDS LEGAL CONFIRMATION] on the state unfair-discrimination and consistent-application exposure, and on the agency-agreement terms.
- Routing to senior_referral matches the user's words in D-098 1(c) and is not the defect. The defect is that a confirm is offered on these files.
- What would resolve it:
  1. `confirm_problem()` refuses when the raw operations text matches `NO_UTILITIES`, or contains "vacant", "vacío" or "unoccupied". The card shows a plain-language reason: "No market confirm: vacant or no utilities is prohibited (AG:51) unless under renovation with a signed GC contract (AG:40); a person decides."
  2. Add one self-check over the four phrases above.
  3. Any future AG:40 exception (renovation with a signed GC contract) needs its own rule from @head-of-underwriting, with documentary evidence, before a confirm is offered. A typed reason alone is not enough.

## Medium / Low (backlog, one line each)
- M1: The senior can pick carrier_a on a W2 file whose rule note says "not Carrier A" (R14). The package label discloses the confirm, but criterion 1(a) "never Carrier A" and "they pick the carrier" read against each other. @user to say whether carrier_a is allowed in the confirm.
- M2: B-383 (self-asserted `underwriter_id`, no CSRF on `/confirm-market`) means anyone with the page can confirm as UW-001. Audit-trail integrity under the NAIC AI bulletin's governance expectations. This must be fixed before pilot.
- L1: The senior attribute is read from an editable repo JSON with no change log. Record who set "senior" and when, before pilot.
- L2: `market_confirms.jsonl` has no retention rule in `ai-governance.md`. Add it with the decisions and sends logs.
