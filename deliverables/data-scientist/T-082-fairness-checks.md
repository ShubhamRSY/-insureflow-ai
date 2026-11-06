# T-082 fairness checks — items 1, 3, 6 (synthetic, no model call)

Code: `underwriting_pipeline/app/workbench.py` `match()` as on branch `pilot-final`. Script: `deliverables/data-scientist/t082_fairness_checks.py`.

## Item 1 — EN↔ES same match: 498 of 498 pairs equal, 0 differ

Compared: route, rule ids in the note, suggested market, overridable. Each pair is the same text in both languages, sprinklers yes/no, TIV $1,000,000.


### Item 1b — Spanish plurals: 19 of 19 equal, 0 differ

| Spanish | English | Spanish result | English result |
|---|---|---|---|

Reading: every listed Spanish plural now gets the same route, ids, suggested market and overridable flag as its English plural (P-087 part B, built). `pintores`, `carpinteros`, `cafés`, `dispensarios` are equal because the English plurals are missing too; the pairs are unchanged.

Reading: `cantina`/`taberna` now follow `bar`/`tavern` (R1 alone, R2 senior referral beside restaurant evidence); `antro`/`discoteca` now follow `nightclub` (R1 even beside restaurant evidence). Both languages give the same route, ids and suggested market (P-087 part A, built).

## Item 3 — B-197 Spanish→English mapping: 83 Spanish entries, 0 problems

- Every Spanish entry is in its list and its English twin is in the same list; no entry maps to two words.

## Item 6 — route by housing class: 198 matched files (3 TIVs × 2 sprinkler answers per class)

| Class text | Group | n | Route split [rule] |
|---|---|---|---|
| `student housing` | housing program | 6 | senior_referral [P-088] ovr=False: 6 |
| `subsidized housing` | housing program | 6 | senior_referral [P-088] ovr=False: 6 |
| `affordable housing` | housing program | 6 | senior_referral [P-088] ovr=False: 6 |
| `low-income housing` | housing program | 6 | senior_referral [P-088] ovr=False: 6 |
| `low income housing` | housing program | 6 | senior_referral [P-088] ovr=False: 6 |
| `low-income apartments` | housing program | 6 | senior_referral [P-088] ovr=False: 6 |
| `low income apartments` | housing program | 6 | senior_referral [P-088] ovr=False: 6 |
| `section 8` | housing program | 6 | senior_referral [P-088] ovr=False: 6 |
| `public housing` | housing program | 6 | senior_referral [P-088] ovr=False: 6 |
| `senior housing` | housing program | 6 | senior_referral [P-088] ovr=False: 6 |
| `dormitory` | housing program | 6 | senior_referral [P-088] ovr=False: 6 |
| `dormitories` | housing program | 6 | senior_referral [P-088] ovr=False: 6 |
| `alojamiento estudiantil` | housing program | 6 | senior_referral [P-088] ovr=False: 6 |
| `vivienda subsidiada` | housing program | 6 | senior_referral [P-088] ovr=False: 6 |
| `vivienda asequible` | housing program | 6 | senior_referral [P-088] ovr=False: 6 |
| `vivienda de bajos ingresos` | housing program | 6 | senior_referral [P-088] ovr=False: 6 |
| `vivienda para personas de bajos ingresos` | housing program | 6 | senior_referral [P-088] ovr=False: 6 |
| `sección 8` | housing program | 6 | senior_referral [P-088] ovr=False: 6 |
| `vivienda pública` | housing program | 6 | senior_referral [P-088] ovr=False: 6 |
| `vivienda para personas mayores` | housing program | 6 | senior_referral [P-088] ovr=False: 6 |
| `vivienda para adultos mayores` | housing program | 6 | senior_referral [P-088] ovr=False: 6 |
| `dormitorio` | housing program | 6 | senior_referral [P-088] ovr=False: 6 |
| `dormitorios` | housing program | 6 | senior_referral [P-088] ovr=False: 6 |
| `residencia estudiantil` | housing program | 6 | senior_referral [P-088] ovr=False: 6 |
| `residencias estudiantiles` | housing program | 6 | senior_referral [P-088] ovr=False: 6 |
| `vivienda para estudiantes` | housing program | 6 | senior_referral [P-088] ovr=False: 6 |
| `vivienda estudiantil` | housing program | 6 | senior_referral [P-088] ovr=False: 6 |
| `vivienda de interés social` | housing program | 6 | senior_referral [P-088] ovr=False: 6 |
| `seccion 8` | housing program | 6 | senior_referral [P-088] ovr=False: 6 |
| `apartments` | habitational | 6 | senior_referral [R12] ovr=False: 6 |
| `multifamily` | habitational | 6 | senior_referral [R12] ovr=False: 6 |
| `duplex` | habitational | 6 | senior_referral [R12] ovr=False: 6 |
| `habitational` | habitational | 6 | senior_referral [R12] ovr=False: 6 |

Reading: every wording of the housing program is now one senior referral with one note (P-088; ids P-088), never a carrier and never a decline; plain `apartments`, `multifamily`, `duplex` and `habitational` keep R12. No TIV or sprinkler answer changes any of them. This closes T-082 item 5; P-088 is conditional on real company compliance sign-off (D-170).

Not measured: the impact on occupants' protected groups. That needs pilot data (or an approved inference method).
