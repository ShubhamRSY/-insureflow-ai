# B-448 / B-458 - SUB-252: pub with a fryer beside office suites, R1 or R2? (rule proposal)

Author: @head-of-underwriting, 2026-10-23. A proposal for @user. Nothing here is decided (D-017). FICTIONAL file; not a carrier decision.

## The case in plain words
SUB-252 is a pub with a full bar on the ground floor, food from a fryer and a warmer (no full kitchen), and two office suites upstairs. Frame 1952, no sprinklers, one paid liquor claim ($22,000). Two written rules both apply and point different ways:
- carrier-match.md W1, column "beside a non-food operation": bar/tavern/pub gives **R1 no_match, never overridable** (D-112, stricter wins).
- W1, column "beside restaurant evidence": bar/tavern/pub gives **R2 senior_referral, never confirmable** (D-079, P-062 a, D-112 "R2 kept by name").
Note 2 of W1 says stricter wins except "bar, tavern, pub beside R9 evidence". It does not say what happens when both columns are true at once.
- Gold (@senior-underwriter, written before the run): R1, reading "stricter wins".
- Frozen code (workbench.py _match, around line 296): the check "barred and food" returns R2 before any second-operation test, so R2.
- Both routes are non-carrier, both need a person, neither can be sent. T-117 route gate: 0 unsafe, 19/20 and this is the one miss. Safety is not at stake; consistency and the underwriter message are.

## Options

### A - R2 wins when restaurant evidence is present (recommended)
Rule wording (add to W1 note 2): "A bar, tavern or pub word beside restaurant evidence (R9) is R2 senior_referral even when a second, non-food operation (office, retail, other) is also present. The non-food operation does not make it R1. Nightclub and lounge stay R1 in every column."
- SUB-252: code is right, gold is wrong. Route R2, hold stays (open conflict). The published T-117 score is not rewritten (D-020/D-022): a dated ruling note is added and the next scorer or hold-out uses R2.
- Other cases: no change. Pub plus offices with no food evidence stays R1 (W1 column 3). SUB-201/225/238/239 (lounge, nightclub, snacks only) stay R1. Restaurant plus bar stays R2.
- Risk: a pub that adds offices to dodge R1 gets a human look instead of a no_match recommendation. A senior still sees it and cannot confirm a carrier (never confirmable). Low. A weaker point: the file reads as less strict than "stricter wins".
- Change needed: rules text and a gold ruling note only. No code, no P-###.

### B - R1 wins when a second operation is present (keep gold)
Rule wording: "A bar, tavern or pub word beside a second operation that is not food service is R1 no_match, never overridable, even if restaurant evidence is also present."
- SUB-252: gold is right, code is wrong; route becomes R1.
- Other cases: any restaurant-plus-bar file with a second operation (for example restaurant, bar and a retail shop, hotel with bar and restaurant) flips from R2 to R1. A person no longer sees a liquor-confirm referral for them, only a no_match recommendation.
- Risk: harsher on mixed-use buildings; a landlord-style risk (offices above a pub) is arguably less bar-driven than the pub-alone case, yet is treated the same as a nightclub. Over-rejects, which cuts the human review I want kept when unsure.
- Change needed: code change in _match (add a second-operation test before the "barred and food" branch), so a numbered proposal (P-###) and your "approve change P-###". Frozen hold-out files and scorers stay untouched.

### C - Both routes accepted for this pattern
Rule wording: "Where W1 columns 2 and 3 both apply, R1 and R2 are both safe; the gold may say either and the scorer credits either."
- SUB-252: counts as a hit. Code unchanged.
- Other cases: no change in behaviour.
- Risk: leaves the rule undecided and weakens route accuracy as a measure; the next reader still cannot tell what the system should do.
- Change needed: scorer change (new scorer version, old stays frozen) and a rules note. It is a scorer edit, so it needs an approved P-###.

## Recommendation: A
Reasons. (1) The pub-with-food rule was approved by you by name (D-079, P-062 a) because the fryer is real food evidence and a person must confirm liquor sales. Offices upstairs do not lower or raise the liquor exposure, so they should not change the route. (2) Option B makes a mixed building harsher than a single-use pub with a kitchen, which is backwards. (3) When in doubt I want a human to review, and R2 does that without opening any send gate. (4) A is the only option with no code or scorer change, so no frozen file moves. Underwriting view: the file stays on hold for the suite-count conflict and the open liquor claim either way, and a person decides.
What to say to decide: "A", "B" or "C" (and, for B or C, the matching approve change line once a P-### is written).
