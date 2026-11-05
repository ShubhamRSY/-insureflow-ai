# T-082 fairness checks — items 1, 3, 6 (synthetic, no model call)

Code: `underwriting_pipeline/app/workbench.py` `match()` as on branch `pilot-final`. Script: `deliverables/data-scientist/t082_fairness_checks.py`.

## Item 1 — EN↔ES same match: 404 of 408 pairs equal, 4 differ

Compared: route, rule ids in the note, suggested market, overridable. Each pair is the same text in both languages, sprinklers yes/no, TIV $1,000,000.

| List | Spanish text | English text | Sprinklers | Spanish result | English result |
|---|---|---|---|---|---|
| PROHIBITED | `restaurante con cantina` | `restaurant with bar` | yes | no_match R1 sugg=- ovr=False | senior_referral R2 sugg=- ovr=False |
| PROHIBITED | `restaurante con cantina` | `restaurant with bar` | no | no_match R1 sugg=- ovr=False | senior_referral R2 sugg=- ovr=False |
| PROHIBITED | `restaurante con taberna` | `restaurant with tavern` | yes | no_match R1 sugg=- ovr=False | senior_referral R2 sugg=- ovr=False |
| PROHIBITED | `restaurante con taberna` | `restaurant with tavern` | no | no_match R1 sugg=- ovr=False | senior_referral R2 sugg=- ovr=False |

### Item 1b — Spanish plurals: 5 of 18 equal, 13 differ

| Spanish | English | Spanish result | English result |
|---|---|---|---|
| `cantinas` | `bars` | no_match D-078/KO 8/R8 ovr=True | no_match R1 ovr=False |
| `tabernas` | `taverns` | no_match D-078/KO 8/R8 ovr=True | no_match R1 ovr=False |
| `antros` | `nightclubs` | no_match D-078/KO 8/R8 ovr=True | no_match R1 ovr=False |
| `discotecas` | `nightclubs` | no_match D-078/KO 8/R8 ovr=True | no_match R1 ovr=False |
| `clínicas` | `clinics` | no_match D-078/KO 8/R8 ovr=True | senior_referral R14 ovr=False |
| `laboratorios` | `laboratories` | no_match D-078/KO 8/R8 ovr=True | senior_referral R14 ovr=False |
| `contratistas` | `contractors` | no_match D-078/KO 8/R8 ovr=True | senior_referral R11 ovr=False |
| `cocinas` | `kitchens` | no_match D-078/KO 8/R8 ovr=True | senior_referral R10 ovr=False |
| `comedores` | `eateries` | no_match D-078/KO 8/R8 ovr=True | senior_referral R10 ovr=False |
| `hornos` | `ovens` | no_match D-078/KO 8/R8 ovr=True | senior_referral R10 ovr=False |
| `multifamiliares` | `multifamily` | no_match D-078/KO 8/R8 ovr=True | senior_referral R12 ovr=False |
| `tiendas minoristas` | `retail stores` | no_match D-078/KO 8/R8 ovr=True | senior_referral P-053 ovr=False |
| `restaurantes con cantinas` | `restaurants with bars` | senior_referral R10 ovr=False | senior_referral R2 ovr=False |

Reading: the lists hold Spanish singulars only, so a Spanish plural falls to R8 (overridable no_match). For the bar words that is looser than English (overridable where `bars` is never overridable); for clinics, contractors, kitchens and multifamily it skips the senior referral English gets. `pintores`, `carpinteros`, `cafés`, `dispensarios` are equal only because the English plurals are missing too. Fix options are in P-087 part B.

Reading: Spanish bar words beside restaurant evidence are R1 (never overridable) where the English bar words are R2 (senior referral); `cantina`/`taberna` are in PROHIBITED but not in BAR_WORDS (`workbench.py`). Alone, both languages are R1. `antro`/`discoteca` match `nightclub` (R1 in both). This is T-082 item 2; the fix is P-087 (a rule change, not built).

## Item 3 — B-197 Spanish→English mapping: 68 Spanish entries, 0 problems

- Every Spanish entry is in its list and its English twin is in the same list; no entry maps to two words.

## Item 6 — route by housing class: 72 matched files (3 TIVs × 2 sprinkler answers per class)

| Class text | Group | n | Route split [rule] |
|---|---|---|---|
| `student housing` | W1 housing (EN) | 6 | no_match [R1] ovr=False: 6 |
| `subsidized housing` | W1 housing (EN) | 6 | no_match [R1] ovr=False: 6 |
| `alojamiento estudiantil` | W1 housing (ES) | 6 | no_match [R1] ovr=False: 6 |
| `vivienda subsidiada` | W1 housing (ES) | 6 | no_match [R1] ovr=False: 6 |
| `affordable housing` | near-synonym, not listed | 6 | no_match [D-078/KO 8/R8] ovr=True: 6 |
| `low-income apartments` | near-synonym, not listed | 6 | senior_referral [R12] ovr=False: 6 |
| `section 8 apartments` | near-synonym, not listed | 6 | senior_referral [R12] ovr=False: 6 |
| `senior housing` | other housing | 6 | no_match [D-078/KO 8/R8] ovr=True: 6 |
| `apartments` | habitational | 6 | senior_referral [R12] ovr=False: 6 |
| `multifamily` | habitational | 6 | senior_referral [R12] ovr=False: 6 |
| `duplex` | habitational | 6 | senior_referral [R12] ovr=False: 6 |
| `habitational` | habitational | 6 | senior_referral [R12] ovr=False: 6 |

Reading: the same occupancy gets three outcomes by wording. `student/subsidized housing` (EN or ES) is R1, never overridable; `affordable housing` and `senior housing` are R8, overridable; `low-income apartments` and `section 8 apartments` are R12 senior referrals. No TIV or sprinkler answer changes any of them. Every difference traces to a named list (W1, R8, R12) and nothing else. This is T-082 item 5; P-088 drafts the route.

Not measured: the impact on occupants' protected groups. That needs pilot data (or an approved inference method).
