# P-088 — Loss basis for student and subsidized housing

- Author: @actuary (Pricing Actuary)
- Date: 2026-11-05
- Re: P-088, T-082 item 5, D-169 item 5, D-170
- Status: Statement only. No code, prompt, scorer, gold, or frozen file changed. Not a filing or a rate indication.

## Direct answer

**None.**

No loss basis exists for treating student housing or subsidized housing differently from other habitational risk. I have no company experience, no external loss study, and no segmented loss estimate that supports a stricter treatment for either class. The only figure on file is a single planning loss ratio for all habitational risk, and it does not distinguish these classes.

## Sources and exact figures

- `deliverables/actuary/pilot-assumptions.md:40` — "Habitational, any unit count | Referral | 0.70 | 0.62–0.82 | Do not auto-quote". This is one band for all habitational risk. It has no student-housing or subsidized-housing split.
- `deliverables/actuary/pilot-assumptions.md:7` — "These are **planning assumptions**. They are not this company's experience. T-004 is not done. There is no triangle. Do not quote these as an indication."
- `deliverables/actuary/pilot-assumptions.md:53` — a pilot "will not have a credible LR"; the leading checks run until "24 months or 200 earned exposures in the band, whichever comes first".
- `deliverables/actuary/pilot-assumptions.md:59` — "There is no catastrophe model output."
- `deliverables/responsible-ai/proxy-review.md:31` — finding F3: "No separate loss estimate exists for student or subsidized housing ... no loss basis sets these classes apart from other habitational risk, which the guide routes to senior referral (AG:37), not prohibition."
- `deliverables/head-of-underwriting/carrier-match.md:43` (R12) — habitational, 1 unit or more, "senior_referral, suggested carrier_c".
- `deliverables/head-of-underwriting/carrier-match.md:16` — `student housing` and `subsidized housing` sit in W1 at `no_match R1, never overridable`.
- `deliverables/head-of-underwriting/appetite-guide.md:37` — "All habitational and lessor's risk, including 1–9 units. Senior referral."
- `deliverables/head-of-underwriting/appetite-guide.md:45` — "Student housing and subsidized housing" listed as prohibited.
- `deliverables/head-of-underwriting/appetite-guide.md:57` (KO 1) — decline "reason = class name".
- `deliverables/head-of-underwriting/appetite-guide.md:61` (KO 5) — habitational + cooking + no sprinklers is a decline; this is a risk-fact rule, not a housing-program rule.
- `team/DECISIONS.md:1677` (D-169 item 5) — P-088 is to route these classes to senior referral "with a documented reason instead of a non-overridable no_match"; real company compliance must sign before any pilot.
- `team/DECISIONS.md:1684` (D-170) — P-088 approved "as drafted, conditional: not used in any pilot until real company compliance signs it"; @actuary to state in writing "whether any loss basis exists".

## What the sources cover and do not cover

Covered:

- A planning permissible loss ratio of 0.65 (`pilot-assumptions.md:28`), built from planning expense deductions, and a planning LR of 0.70 (range 0.62–0.82) for all habitational risk (`pilot-assumptions.md:40`).
- A rule-based reason to refer all habitational risk (`AG:37`, `carrier-match.md:43`), and rule-based prohibitions that name these classes (`AG:45`, `carrier-match.md:16`).
- A fairness finding that no separate loss estimate exists (`proxy-review.md:31`).

Not covered:

- Any loss cost, frequency, severity, trend, or catastrophe load specific to student housing or subsidized housing.
- Any credible company loss experience, development triangle, or segmented relativity for these classes.
- Any external actuarial study or carrier loss data segmented by these classes. None is on file, and I am not importing one.
- Any evidence that the planning LR of 0.70 differs for these two classes. It does not; the figure is one habitational band.

The underwriting rules and the fairness review are not loss evidence. A rule citing a class name (AG:57) and a prohibited-class list entry (AG:45) say what the guide does, not what the losses are.

## Is the planning assumption company experience?

No. The 0.70 (range 0.62–0.82) habitational planning LR is an assumption, not this company's experience. `pilot-assumptions.md:7` states this directly: "These are **planning assumptions**. They are not this company's experience. T-004 is not done. There is no triangle. Do not quote these as an indication." A pilot is not expected to produce a credible LR (`pilot-assumptions.md:53`).

## What would change the answer

A loss basis would need at least one of: (a) company experience with enough earned exposures and claim counts for each class, or (b) a credible external loss study or carrier data segmented for these classes, reviewed for relevance to Texas small commercial habitational risk. Until then the answer stays "none", and any differential treatment of these classes must rest on a written non-loss business reason signed by real company compliance (D-170), not on an actuarial basis.
