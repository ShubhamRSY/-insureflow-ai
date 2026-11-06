# @model-risk — build check: T-082 / P-087 (A+B) and P-088 on `pilot-final` (D-170)

- Date: 2026-11-06. Reviewer: @model-risk (independent). Build: worktree `insureflow-pilot-final`, uncommitted changes on `3b6986fc`.
- Verdict: **APPROVE WITH CHANGES.** P-087 (A+B): approved as built. P-088: **OBJECTION — not approved until H1 and H2 are closed.**
- Not a production approval. P-088 is not used in any pilot until the real company compliance signs the rule and its reason (D-170); the team's simulated @compliance does not count.

## What I re-ran (0 model calls, temp copies only, D-069)

| Check | Result |
|---|---|
| `workbench.py` self-checks | ok |
| `tests/pipeline` | 94 passed |
| `t082_fairness_checks.py` (output written to scratch, not the repo) | item 1: 492/492 equal; 1b: 19/19; item 3: 82 Spanish entries, 0 problems. Matches the author's numbers. Repo unchanged by the run. |
| T-128 replay, `3b6986fc` (git archive to temp) vs this build, temp copy of the `T-128-live` cache, `urlopen` blocked | 32/32 files, **0 changed** (outputs byte-identical). Mix: manual_intake 12, hold 10, carrier_a 4, senior_referral 4, no_match 2. No `extraction_failed`. 0 changes is intended: no T-128 file uses a changed word. |
| `pilot-integration` (`insureflow-integration`, `c72726ea`) | clean, not changed. |
| My own pair probes (`match()` on synthetic text, sprinklers yes/no) | 2 failures below. |

## High findings

### H1 — P-088: a housing word skips the multi-class rule (R7/R16), so wording changes the suggested market and hides the second class

The housing branch runs before the class words, so it returns before R7 ("class matches more than one carrier") and R16. Same occupancy, different words:

| Text (sprinklers yes, TIV $1M) | Route | Suggested | Note |
|---|---|---|---|
| "apartments with ground floor restaurant" | senior_referral | none | R7: b, habitational |
| "low-income apartments with ground floor restaurant" / "student housing with …" | senior_referral | **carrier_c** | P-088 housing note; restaurant not named |
| "apartments above offices" vs "affordable housing above offices" | same split | none vs **carrier_c** | R7 vs P-088 |
| "apartments and roofing contractor yard" vs "senior housing and …" | same split | none vs **carrier_c** | R7 vs P-088 |

- This fails the acceptance line "every wording must match". It is also looser for the housing wording: a single market is suggested for a mixed use, and the restaurant (R10) or contractor (R11) fact drops off the card. P-088 said "the same habitational rule as R12"; R12 only applies to a single class.
- Not caught because the T-082 pairs test single-class texts only.
- **Resolve:** treat a housing-program word as the habitational class, and use the P-088 note and hold only where R12 would apply (habitational is the only class). Mixed files go to R7/R16 as their plain twins do (the housing note may be added). Add the four pairs above to `t082_fairness_checks.py` and the self-checks. This is stricter only.

### H2 — P-088: `dormitorio(s)` ("bedroom") labels plain Spanish apartments as a housing program

| Text | Route / suggested | Note |
|---|---|---|
| "2 bedroom apartments" | senior_referral / carrier_c | habitational (R12) |
| "apartamentos de 2 dormitorios" | senior_referral / carrier_c | **housing program (P-088)** |
| "apartment building, 3 bedrooms per unit" vs "edificio de apartamentos, 3 dormitorios por unidad" | same split | R12 vs P-088 |

- Route matches, but the card wording does not. The senior underwriter sees a protected-class proxy label ("housing program … occupants are not a reason to decline") on a file only because it is written in Spanish. That is a language-correlated label on the record, and it fails "every pair and wording must match".
- The as-built note says removing `dormitorio(s)` waits for @user because bare `dormitorio` would fall to an overridable no_match. That is one option, not the only one.
- **Resolve (either):** (a) stricter only: `dormitorio(s)` counts as a housing-program word only when no plain habitational word (apartamento(s), multifamiliar, …) is present; with one, R12 applies. Bare `dormitorio` stays a senior referral. Or (b) @user decides to remove the words. Add both pairs above to the T-082 script.

## Medium / Low (backlog, one line each)

- M1: the T-082 item 1 test compares single words, not notes and not mixed or in-context use; add an in-context pair set (how H1 and H2 got past it).
- M2: "stores" → no_match, overridable, but "tiendas" → senior referral. The pair differs (the Spanish is stricter). Make English bare "stores" refer as well (stricter), or record the difference as accepted.
- L1: "section 8" anywhere in the class text ("see section 8 of the lease") relabels plain apartments as housing program. Route unchanged; this is a known limit.
- L2: "clothing stores" vs "tiendas de ropa": same route and market, different note text.

## Decision

- P-087 (A+B): **APPROVED** on `pilot-final` (pairs, plurals, R1/R2 by meaning, `tiendas` never Carrier A direct; replay 0 changes).
- P-088: **OBJECTION**, owner @ai-engineer-assistant. Close H1 and H2, re-run T-082 with the new pairs, re-run the T-128 replay. One look-again by @model-risk.
- No DECISIONS.md approval is recorded for P-088 until then. P-088 production use still needs the real company compliance sign-off (D-170).

## Look-again (2026-11-06, the one allowed under D-129)

Verdict: **APPROVE WITH CHANGES.** P-087 (A+B) stays approved. P-088: **H1 closed. H2 still open (the fix failed a second time).** The OBJECTION on P-088 stands. Not a production approval. P-088 still needs the real company compliance sign-off (D-170).

### Re-run (0 model calls, temp copy of the worktree, worktree status hash unchanged)

| Check | Result |
|---|---|
| `workbench.py` self-checks | ok |
| `tests/pipeline` | 94 passed |
| `t082_fairness_checks.py` (output to scratch) | item 1: 492/492 equal; 1b: 19/19; item 3: 82 entries, 0 problems |
| T-128 replay, `3b6986fc` vs build, temp cache, `urlopen` blocked | 32/32, outputs byte-identical, **0 changes**. carrier_a 4, hold 10, manual_intake 12, no_match 2, senior_referral 4. No `extraction_failed`. |
| My H1 pairs (sprinklers yes / no / missing) | all 4 match their plain twins (R7, with AG:61 when unsprinklered + food) → **H1 closed** |
| My H2 pairs | "apartamentos de 2 dormitorios" and "edificio de apartamentos, 3 dormitorios por unidad" now get R12, matching the English → cited pairs closed |

### H2 (still open, High): the same label defect, now on Spanish dwelling words that are not on the habitational list

The fix depends on a plain habitational word being present. The Spanish list is missing common dwelling words and the accented form, so a plain home written in Spanish with "N dormitorios" still gets the housing-program (protected-class proxy) label. This build introduced it: at `3b6986fc` all of these were `no_match`.

| English | Build | Spanish | Build |
|---|---|---|---|
| "duplex 2 bedroom" | R12 habitational, Carrier C | "dúplex de 2 dormitorios" | **P-088 housing program**, Carrier C |
| "3 bedroom house" | no_match, overridable | "casa de 3 dormitorios" | **P-088 housing program** |
| "3 bedroom condos" | no_match, overridable | "condominios de 3 dormitorios" | **P-088 housing program** |
| "townhomes, 3 bedrooms" | no_match, overridable | "casas adosadas de 3 dormitorios" | **P-088 housing program** |

Options (the fix has failed twice, so per D-129 these go to @user rather than another loop):
- (a) Recommended. Stricter only, so it fits the fast lane. `dormitorio(s)` used with a count ("2 dormitorios", "de 3 dormitorios", "dormitorios por unidad") means bedroom: it adds the habitational class (R12 note) and never the P-088 label. Bare or program use ("dormitorio", "dormitorio estudiantil") stays P-088. Add the four pairs above to the T-082 script.
- (b) @user removes `dormitorio(s)` from `HOUSING_PROGRAM`. This loosens the rule: bare `dormitorio` would fall to an overridable no_match.
- (c) Add the missing dwelling words with accent folding (dúplex, casa(s), condominio(s), adosadas) to the habitational class. This is a vocabulary chase and the weakest option. The English twins (house, condos, townhomes) would then also need adding.

### New Medium / Low (backlog)

- M3: "vivienda estudiantil" (the most common Spanish phrase for student housing) → overridable no_match, but "student housing" → P-088 senior referral. The Spanish route is looser. Add it to `HOUSING_PROGRAM` (stricter only). With "sobre tiendas" it currently suggests Carrier A for a habitational file (senior referral, a person decides).
- L3: "student housing above stores" → P-088, Carrier C, while "… above retail stores" → R7. This is the existing M2 bare-"stores" gap.

### Decision

- P-087 (A+B): approved, unchanged.
- P-088: OBJECTION stands, owner @ai-engineer-assistant. It resolves when H2 is closed by option (a), or by (b)/(c) if @user chooses one, with the four pairs above in T-082 and the T-128 replay re-run. No DECISIONS.md approval for P-088 until then.
