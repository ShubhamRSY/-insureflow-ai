# Authority matrix — v1 pilot

- Author: @head-of-underwriting
- Date: 2026-10-09
- Status: Revised under D-003. @senior-underwriter to confirm.
- Paired with: `appetite-guide.md`

The system recommends. A human is the underwriter of record except in the auto-quote band. **There is no auto-decline in v1.**

## Bands

| Band | Who acts | What the system may do | What a human must do |
|---|---|---|---|
| Incomplete | System routes | List missing fields. No quote, no decline. | Broker chase stays with the submission owner. |
| Auto-quote | System may issue the quote at the **filed rate** | Quote only. It may not bind. | Bind still requires the licensed authority already on the account. Quote is void if any gate below fails on re-check. |
| Refer — underwriter | Human underwriter | Cite the rule that fired and the source document. | Quote, decline, or request more info. |
| Refer — senior | @senior-underwriter or designee | Same, plus flag why it is not a standard referral. | Same. Senior sign-off is stored on the file. |
| Decline | Human only | Draft the reason from the prohibited or knock-out list. | Human confirms the reason is on the list and sends the notice. |

## Auto-quote gates (all must be true)

- Class is office, dry retail, or light wholesale. Not habitational, not contractor, not restaurant.
- TIV per location ≤ $1,000,000 and account premium ≤ $10,000. (Tighter than the appetite ceiling on purpose.)
- 1 location.
- Zero claims in 5 years on currently valued **carrier** loss runs. A no-known-loss letter does not satisfy this gate.
- Year built, construction, protection class, and sprinkler status present and consistent across ACORD and SOV.
- No coastal / wind-pool territory.
- Rating uses the filed rate with no schedule credit and no schedule debit.

If any gate fails → Refer — underwriter. Do not "almost" auto-quote.

## Senior referral (any one is enough)

- Premium > $25,000 or TIV > $2,500,000.
- Any liability claim in 5 years.
- Property claim > $25,000 in 5 years.
- Any habitational or lessor's risk.
- Restaurant or other cooking occupancy.
- Any contractor.
- Request for a schedule credit or debit.
- Underwriter disagrees with the system's class code.

## Decline

- Only from the prohibited list or knock-out rules 1, 2, and 5 in the appetite guide.
- The file stores: rule id, the document or field that triggered it, the person who confirmed, timestamp.
- The system must not invent a reason that is not on that list.

## When this is wrong

- False auto-quote: we are on risk at the filed rate for a risk we did not understand. Mitigation: gates above, no bind from the system, quote re-checked at bind.
- False referral: slow, not fatal.
- False decline draft: a human still sends the notice. If the draft reason is off-list, the human must not send it.

## Not in this matrix

Pricing judgment, coverage-form exceptions, and claims that are open. Those are always senior referrals.
