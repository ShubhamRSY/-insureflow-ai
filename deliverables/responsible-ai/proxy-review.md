# Proxy review — housing classes (student and subsidized housing)

- Author: @responsible-ai. Date: 2026-11-05. Task: T-082 item 4; B-198 (required before pilot, D-060).
- Data: synthetic only. No model call. No pilot data exists, so no occupant group can be measured.
- Scope: the W1 words `student housing`, `subsidized housing`, `alojamiento estudiantil`, `vivienda subsidiada` (`workbench.py:174`) and the near-synonyms that reach other routes.
- Status of the route: today R1 `no_match`, never overridable (`workbench.py:314-317`). @user asked for P-088 (senior_referral with a documented reason, not built; real company compliance signs before any pilot; D-169 item 5).

## 1. What the rule does today
| Class text | Route (item 6, n = 6 each, 3 TIVs × sprinklers yes/no) |
|---|---|
| student housing, subsidized housing (EN and ES) | no_match R1, not overridable: 6/6 each |
| affordable housing, senior housing | no_match R8, overridable with a reason: 6/6 each |
| low-income apartments, section 8 apartments | senior_referral R12, suggested Carrier C: 6/6 each |
| apartments, multifamily, duplex, habitational | senior_referral R12, suggested Carrier C: 6/6 each |
Source: `deliverables/data-scientist/T-082-fairness-checks.md` item 6. No TIV or sprinkler answer changes any route.

Finding F1 (High). The same occupancy gets three outcomes by wording. "Section 8 apartments" is subsidized housing by definition, yet it gets a senior referral with Carrier C, while "subsidized housing" gets a no_match nobody can override. The rule reads the producer's label, not the risk. That is not a consistent business rule, and it means the outcome depends on how a producer describes the tenants.

## 2. Proxy risk
- Subsidized housing describes the tenants' income and funding source, not the building. Tenants of subsidized housing are, on public data, more often members of groups the Fair Housing Act protects (race, national origin, disability, familial status). Some states and cities also protect source of income. Risk: high.
- Student housing describes the tenants' age and status. Age and student status are not FHA classes, but national origin (international students) and familial status can follow. Risk: medium.
- Neither word describes construction, protection, sprinklers, cooking, unit count or loss history: the facts the guide already uses for habitational risk (AG:37, AG:61-62).

## 3. Neutral business reason (from @head-of-underwriting's written rules)
- AG:45 lists "Student housing and subsidized housing" as prohibited. AG:57 (KO 1) says decline "reason = class name". carrier-match.md line 16 cites AG:45-50. D-059 item 5 cites AG:45.
- None of these gives a reason. AG:9 sets the standard: "A class is in appetite only if we can explain a decline in one sentence a regulator can read." That sentence is not written for these two classes.
- Finding F2 (High). No neutral business reason exists in the written rules. "Class name" is a label, not a reason. @head-of-underwriting must write one (a risk fact, e.g. occupancy turnover, cooking in units, unit density) or the prohibition has no stated basis.

## 4. Loss basis (from @actuary)
- `deliverables/actuary/pilot-assumptions.md`: "Habitational, any unit count" planning LR 0.70 (range 0.62-0.82), route "Referral". These are planning assumptions, "not this company's experience"; there is no triangle.
- No separate loss estimate exists for student or subsidized housing. Finding F3 (High): no loss basis sets these classes apart from other habitational risk, which the guide routes to senior referral (AG:37), not prohibition. @actuary should confirm "none" in writing or supply a source.

## 5. Less discriminatory alternatives considered
| Option | What changes | Fairness effect | Accuracy / workload trade-off |
|---|---|---|---|
| A. Keep R1 never overridable (today) | nothing | F1-F3 stay; highest proxy risk | none measured; no loss basis to lose |
| B. P-088: senior_referral, documented reason (D-169 item 5) | a person decides with the reason on the card | decision on risk facts, contestable | more senior-underwriter files; no measured LR change (no basis either way) |
| C. Route as habitational R12: suggested Carrier C when sprinklered, hold if sprinkler answer missing (`workbench.py:350-354`) | same path as "apartments" today | same building risk gets same route | Carrier C "accepts habitational with sprinklers" (carrier-appetite.md:7); higher price, underwriter confirms |
| D. One route for every subsidy or student word (adds affordable housing, low-income, section 8, senior housing) | fixes F1 | wording no longer decides the outcome | small word-list change; none to accuracy |
Recommendation: B + C + D together. Keep the neutral risk checks that already exist (KO 5: habitational + cooking + no sprinklers is a knock-out candidate a person decides). This loosens a W1 rule, so it is @user's call (P-088), and it is not built.

## 6. What cannot be measured now
- The impact on occupants' protected groups (route rates, AIR by group). It needs pilot data or an approved inference method; neither exists.
- Carrier C acceptance and loss experience for these classes.
- The item 6 counts show wording effects only; n = 6 per class is synthetic, not a rate.

## 7. Required actions
1. @head-of-underwriting: write the one-sentence neutral reason (F2), or remove the classes from AG:45.
2. @actuary: confirm no loss basis exists for these classes, or cite one (F3).
3. @compliance: write and sign the legal standard (Fair Housing Act disparate impact) in the last section; real company compliance signs before any pilot (D-169 item 5).
4. @user: decide P-088 (option B, with C and D or not).
5. @data-scientist: re-run item 6 after any build; every row in section 1 should give one route.

## Legal standard — @compliance
- Author: @compliance, the **simulated** team role, 2026-11-05. This is not legal advice and it does not count for real applicants. The real company's compliance/legal must sign before any pilot (D-169 item 5). Context: we are a Texas agency placing small commercial with Carriers A/B/C (team/DECISIONS.md, "Pilot: Texas"; agency-register A-01, A-06).

**Standards that apply (status to be confirmed)**
1. Fair Housing Act, 42 U.S.C. 3604(a)-(b) and 3605 ("otherwise make unavailable"). Courts have applied it to property insurance on rental buildings, including landlord policies refused because tenants use housing vouchers (*NFHA v. Travelers*, D.D.C. 2017; *Viens v. America Empire Surplus Lines*, D. Conn. 2015, both at the motion-to-dismiss stage). Disparate impact is cognizable (*Inclusive Communities*, 2015, with a "robust causality" limit). Whether the FHA reaches an agency's routing rule, and McCarran-Ferguson arguments, are unsettled. `[NEEDS LEGAL CONFIRMATION]`
2. HUD discriminatory-effects rule, 24 CFR 100.500, and its burden-shifting test. Its current status and HUD enforcement position after the 2025 federal disparate-impact directives are not verified here. Courts apply *Inclusive Communities* either way. `[NEEDS LEGAL CONFIRMATION]`
3. Texas Insurance Code ch. 544 subch. A (no refusal or limit of coverage based on race, color, religion, national origin, disability and the other listed traits, unless based on sound actuarial principles or actual/anticipated loss experience) and ch. 541 (unfair practices). Exact wording and whether an agency's referral routing counts as "refuse to insure" are to be confirmed. Texas generally does not protect source of income (Local Gov't Code 250.007); the FHA claim does not depend on it. `[NEEDS LEGAL CONFIRMATION]`

**What the standard asks for (evidence on file)**
- (a) A substantial, legitimate, nondiscriminatory interest, shown with evidence, not assumed. Under Texas ch. 544, an actuarial or loss-experience basis. (b) The rule is needed to serve that interest. (c) No less discriminatory alternative serves it as well. Plus records: the written reason, the version of the rule, and the human decision (C-02; agency-register A-03).

**Option A: keep W1 (R1 no_match, never overridable). Verdict: does not meet the standard on this record. OBJECTION for any pilot.**
- (a) is missing. There is no written reason (F2; AG:45 and carrier-match.md line 16 give only the class name) and no loss basis (F3; the actuary's figure is a planning assumption for all habitational risk).
- (b) fails on our own data. "Section 8 apartments" and "low-income apartments" already go to senior referral (item 6, 6/6). The rule tracks the subsidy label, not a risk fact, which is the pattern in *Travelers*.
- (c) Options B and C exist and are cheap.
- What would resolve the objection: @head-of-underwriting writes a risk-based reason, @actuary supplies a loss source that supports it, the carriers' written appetite is cited if the prohibition comes from them, and real legal signs. Without all four, W1 should not go into a pilot.

**Option B: P-088 (senior_referral with a documented reason). Verdict: meets the standard better and is the less discriminatory alternative. APPROVE WITH CONDITIONS (simulated).**
- Conditions:
  1. The route is the same as R12 habitational: no extra burden compared with "apartments".
  2. The card note says the program or the occupants are not a reason to decline (draft wording OK).
  3. Each senior decision records a neutral risk reason, and a decline citing the class or the tenants is refused.
  4. Referral and decline rates for this group are monitored once pilot data exists. A referral that always ends in a decline is a de facto prohibition.
  5. Option D wording consistency is built with it.
- This is not a production approval. @model-risk checks the build (D-167), and @user decides P-088.

**Not certain:** current HUD rule and enforcement status; whether FHA and ch. 544 reach an agency's routing; whether a carrier's own prohibition shifts the liability; local source-of-income ordinances in the pilot cities.

Sign-off: @compliance (simulated): A objected, B approved with conditions, 2026-11-05. Real company compliance/legal: ______________ (required before any pilot, D-169).
