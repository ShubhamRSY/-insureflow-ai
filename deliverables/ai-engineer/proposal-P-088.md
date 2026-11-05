# P-088 — Student and subsidized housing go to a senior underwriter with a documented reason, not a never-overridable no_match (T-082 item 5)

- Author: orchestrator, drafted 2026-11-05 at @user's request (D-169 item 5). **Draft for @user to read. Not approved, not built.**
- Source: @responsible-ai T-082 High-2 and lift items 4–6; measured in `deliverables/data-scientist/T-082-fairness-checks.md` item 6; review `deliverables/responsible-ai/proxy-review.md`.
- Direction: **loosens a gate.** A W1 class (R1, never overridable) becomes a senior referral. It needs your approval, and @model-risk checks it (frozen build, D-167).
- **Before any pilot, the real company's compliance must sign this rule** (D-169). The team's @compliance is simulated, so its sign-off does not count for real applicants.

## Problem (measured, synthetic, no model call)

The same occupancy gets three outcomes depending on the words used. TIV and the sprinkler answer change none of them (n = 6 files per class):

| Wording | Route today | Can a person override? |
|---|---|---|
| "student housing", "subsidized housing", "alojamiento estudiantil", "vivienda subsidiada" | no_match R1 (W1, AG:45-50) | **never** |
| "affordable housing", "senior housing" | no_match R8 (class on no list) | yes |
| "low-income apartments", "section 8 apartments", "apartments", "multifamily" | senior_referral R12, Carrier C suggested | a person decides |

Student and subsidized housing track protected classes: race, national origin, familial status, disability and source of income. A never-overridable outcome keyed to those words is the hardest form of the proxy, and a reworded file escapes it. No loss basis exists for the stricter treatment (`deliverables/actuary/pilot-assumptions.md`: no habitational loss data).

## Change (`underwriting_pipeline/app/workbench.py`, `carrier-match.md`)

1. Remove the four housing phrases from `PROHIBITED` (W1).
2. New referral group `HOUSING_PROGRAM`: "student housing", "subsidized housing", "affordable housing", "low-income housing", "low income housing", "section 8", "public housing", "senior housing", "dormitory", "dormitories", plus the Spanish twins (B-197 rule: translations of the English entries only).
   - Route: **senior_referral**, never a carrier and never a decline. It is the same habitational rule as R12: Carrier C suggested with sprinklers yes; hold when the sprinkler answer is missing.
   - The note gives the documented reason. Draft wording, @head-of-underwriting to confirm: *"Housing program or student housing (P-088): habitational underwriting by a person — occupancy, sprinklers, building age and condition; the program or the occupants are not a reason to decline."*
3. It is checked before the plain habitational words, so "low-income apartments" and "subsidized housing" give the same route and note.
4. `carrier-match.md`: @head-of-underwriting moves the rows from W1 to the referral list and records why this departs from AG:45-50.
5. D-065: card wording, a What's-new line, a screenshot, and the @senior-underwriter UI check.

## Not changed

- Extraction, prompt, scope, scorer v11, the gold. No auto-decline, no auto-bind.
- The send gates: a senior referral still needs a senior underwriter to confirm a market.

## Tests (dev only, no model call)

- Item 6 rerun: every housing wording in the table (EN and ES) gives one route and one note. Group counts are reported with n. With sprinklers missing → hold.
- Item 1: the EN↔ES pairs for the new group are equal.
- Routing self-checks: no housing phrase routes to a carrier directly; none is no_match.

## Open before a pilot (not closed by this change)

- The **real company compliance** signs the rule and the reason.
- Real occupant protected-group impact: this needs pilot data or an approved inference method (@responsible-ai item 6). Language outcome rates need pilot data (item 7).

## Decision for @user

1. `approve change P-088` as drafted (**recommended**), or with a narrower group (only the four phrases in W1 today), or keep W1 and accept the written reason in `proxy-review.md` instead.
