# P-087 (A+B) and P-088 — as built on `pilot-final` (D-170)

- Branch `pilot-final` (worktree `insureflow-pilot-final`). `pilot-integration` (frozen D-167 build) is not changed.
- P-088 is conditional: **not used in any pilot until the real company compliance/legal function signs the rule and its reason** (D-170).
- Only `underwriting_pipeline/app/workbench.py` changed in code. No prompt, extraction, OCR, scorer, gold or frozen file changed.

## What changed (`workbench.py`)

- P-087 A: `cantina`/`taberna` (+ plurals) are in `BAR_WORDS`, so they follow `bar`/`tavern` (R1 alone, R2 senior referral beside restaurant evidence). `antro`/`discoteca` (+ plurals) are in `NEVER_SOFT`, so they follow `nightclub` (R1 even beside restaurant evidence).
- P-087 B: listed Spanish plurals added (`cantinas`, `tabernas`, `antros`, `discotecas`, `fertilizantes`, `pesticidas`, `clínicas`, `laboratorio(s)`, `hornos`, `cocinas`, `comedores`, `contratistas`, `multifamiliares`, `tiendas`). Bare `tiendas` and `tiendas de ropa` are senior referrals (suggested Carrier A), never Carrier A direct.
- P-088: the four housing phrases left `PROHIBITED` (W1). New `HOUSING_PROGRAM` group (12 English + 16 Spanish phrases), checked after W1, the hold gates, R2 and W2, and before the class words. Route: senior_referral with `HOUSING_NOTE` (reason by @head-of-underwriting, `deliverables/head-of-underwriting/P-088-housing-reason.md`; @actuary: no loss basis exists, `deliverables/actuary/P-088-housing-loss-basis.md`). Suggested Carrier C, the underwriter confirms. A missing sprinkler answer holds. Unsprinklered adds "no sprinklers", and with cooking evidence also the R12 "AG:61 knock-out candidate, a person decides" flag (added 2026-11-06 at code review so housing shows the same facts as R12). Over $5M adds the R13 note.
- What's new: two lines (P-087, P-088; D-170).

## Checks (2026-11-06)

- Self-checks: workbench, package, quotes ok. `tests/pipeline`: 94 passed.
- pyright 1.1.390 on workbench.py + t082 script: 28 errors, all pre-existing (40 at `3b6986fc`); none new.
- T-082 (`deliverables/data-scientist/T-082-fairness-checks.md`, script `t082_fairness_checks.py`, synthetic, no model call): item 1 EN↔ES 492/492 equal; item 1b plurals 19/19; item 3 82 Spanish entries, 0 mapping problems; item 6 192 housing files, every housing-program wording is one P-088 senior referral, plain habitational keeps R12; no TIV or sprinkler answer changes the class outcome.
- **T-128 replay from cache** (32 files, temp copy of `insureflow-integration/underwriting_pipeline/cache/T-128-live`, model call blocked, 0 model calls): `3b6986fc` vs this build, compared status, card status, route, note, suggested, overridable, provisional. **0 of 32 changed.** Route mix: manual_intake 12, hold 10, carrier_a 4, senior_referral 4, no_match 2. No T-128 file uses the changed words, so 0 changes is the intended result.
- Screenshots (D-065, synthetic cards from a temp copy, D-069): `deliverables/software-engineer/screenshots/P-087-P-088-cards.png`, `P-087-P-088-whats-new.png`. Script `deliverables/software-engineer/P-088-shot.py`.

## Known limits

- `section 8` is matched as a phrase anywhere in the class text; a non-housing use would send the file to a person (stricter only).
- English bare `stores` stays no_match (overridable) while `tiendas` is a senior referral; both need a person.
- Protected-group impact on occupants is not measured (needs pilot data). T-082 item 7 is open.

## After @responsible-ai check (2026-11-06, APPROVE WITH CHANGES, `deliverables/responsible-ai/T-082-check-P-087-P-088.md`)

- H1 part 1 (stricter only, fast lane D-129): added `residencia estudiantil`, `residencias estudiantiles`, `vivienda para estudiantes`, `vivienda de interés social`; M2: `seccion 8` (unaccented). Pairs added to the T-082 script. Re-run above; T-128 replay again 0 of 32 changed.
- H1 part 2 **not done, @user decision**: removing `dormitorio(s)` ("bedroom" in everyday Spanish) is a loosening (bare `dormitorio` would fall from senior referral to overridable no_match), so it waits for @user.
- @senior-underwriter UI check: APPROVE, no High (`deliverables/senior-underwriter/P-087-P-088-ui-check.md`).

## After @model-risk check (2026-11-06, APPROVE WITH CHANGES; P-088 OBJECTION H1/H2, `deliverables/model-risk/check-P-087-P-088.md`)

- H1 fixed: the separate housing branch is gone. A housing-program word now adds the habitational class, so R7/R16 and the sprinkler hold run exactly as for plain habitational; the P-088 note replaces the R12 note only where R12 would apply. "low-income apartments with ground floor restaurant" now equals "apartments with ground floor restaurant" (R7, with the AG:61 flag when unsprinklered).
- H2 fixed by option (a) (no loosening): `dormitorio(s)` counts as housing only when no plain habitational word is present. "apartamentos de 2 dormitorios" now equals "2 bedroom apartments" (R12); bare "dormitorio" stays P-088. Removing the words entirely stays a @user decision.
- Re-run: self-checks ok; tests/pipeline 94 passed; pyright 28 (none new); T-082 492/492, 19/19, 82/0, 192 files; T-128 replay 0 of 32 changed; cards screenshot retaken.

## @model-risk look-again (2026-11-06): APPROVE WITH CHANGES; P-087 approved; P-088 OBJECTION stands on H2

- H1 closed. H2 closed for the cited pairs but open for Spanish dwellings not on the habitational list ("dúplex/casa/condominios/casas adosadas de N dormitorios" get the P-088 label; English twins R12). The fix failed twice, so per D-129 it goes to @user as options (a) "dormitorio(s)" with a number counts as habitational R12 (recommended, stricter only), (b) remove the words (loosening), (c) add the missing dwelling words with accent folding.
- M3 fixed (stricter only): `vivienda estudiantil` added to HOUSING_PROGRAM and to the T-082 pairs.
