# Reason codes — point score v2

- Author: @data-scientist
- Date: 2026-10-14 (v1 written 2026-10-09)
- Status: In review (T-017). Built per P-015, D-040 (S3 H1 M1 T2 V3 W1 A1 E2), D-070. Synthetic. Not a production approval.
- Code: `underwriting_pipeline/models/points.py`. Run `.venv/bin/python underwriting_pipeline/models/points.py` (LLM_* unset).
- Points version: `POINTS_VERSION` in that file, now `points-<12-hex hash>+git:not-recorded` (see "Points version").

The number is a hazard rank. It is not a premium, not a decline, and not a carrier. Range 0 to 80.

| Code | Points | When |
|---|---|---|
| COOKING | 25 | A fryer or an open flame is stated on the file's "Cooking equipment:" line, not negated. Nothing else gives it. |
| FRAME_CONSTRUCTION | 15 | Frame construction |
| HABITATIONAL | 15 | Apartments or other habitational (words: habitational, apartment, flats) |
| CONTRACTING | 15 | Contracting operations (words: contractor, painting) |
| TIV_OVER_1M | 10 | Building TIV over $1,000,000 |

Weights are placeholders until losses exist. Nothing is refit. Nothing in this function binds, declines, prices or picks a carrier.

## Loss history: not scored

LOSS_HISTORY is removed (P-015). No claim fact is extracted, and a loss-run date is not a claim count. Every file, scored or not, shows the line "Loss history: not scored". The line does not mean no losses. A missing loss run adds no points and does not mean zero claims. Claim extraction is in the backlog (B-149). Until a cited claim fact exists, loss history is not a driver.

## Not scored

`points.score_run(saved_run)` returns a score or "Not scored — <reason>", never a number for a file that is not scored.

| Status in the saved run | Shown |
|---|---|
| `complete` with at least one value | the number and codes |
| `extraction_failed` | Not scored — extraction failed: <error> |
| `incomplete` | Not scored — file incomplete: missing <fields>; open conflict on <field>; asked of the producer: <item> |
| `all_values_rejected` (D-024) | Not scored — every value was rejected |
| `complete` with no values, no status, or any other status | Not scored — file complete but holds no values / unknown status |

Unknown never becomes a number. A resolved conflict does not block a score.

## Cooking

Where the facts come from (S3): `prepare.py` reads the labelled lines "Cooking equipment:" and "Hood and fire suppression:" (also "Hood and suppression:", "Hood:", "Suppression:") from the source text, with a citation (source, character span, quote), and saves them in the run as `run["cooking"]["equipment"]` and `["hood_suppression"]`. A run saved before P-015 has no such key and reads as not_stated. `points.py` reads only that fact. It does not read the `operations` value, the insured's name, a class word, or a cuisine word.

Term list (whole words, English and Spanish; the list lives in `prepare.HAZARD_TERMS`, and `points.py` hashes it into the version): fryer, fryers, freidora, freidoras, open flame, llama abierta, charbroiler, grill, parrilla. "Campana" and "supresión" are not hazards: hood and suppression is its own fact.

Negation: a line that starts with no, none, not, without, sin, ninguno, ninguna, or n/a is "stated none". It gives no points. A line holding no hazard term (for example "microwave") is "other".

Three outcomes are shown, never a silent zero (M1: a complete file with no cooking fact still shows its number):

| State | Line on the page | Points |
|---|---|---|
| equipment `yes` | COOKING +25 — fryer stated: "<the cited text>" | 25 |
| equipment `none` | Cooking: stated none | 0 |
| equipment `other` | Cooking: not scored — equipment stated is not a fryer or open flame: "<text>" | 0 |
| equipment `not_stated` | Cooking: not scored — no cooking equipment stated in the file | 0 |

Hood and suppression (H1): shown beside the code as "Hood and suppression: stated / stated none / not stated" with the quoted text. It gives no points either way.

Wording-pair test (in the `points.py` self-check): for 16 `operations` texts (taco, taqueria, pizzeria, restaurant, "office, no kitchen", "office with fryer", "childhood education office", Spanish texts and the rest of the P-015 list), points are 0 with no stated fact, 0 with "none", and 25 with a stated fryer. The class and cuisine word never moves the points; the stated fact does. The name test (T-067) is `deliverables/data-scientist/name-swap-T-067.md`.

## The override: mark a code wrong (W1)

An underwriter can mark any code shown wrong. A reason is required; no reason, no mark. The log saves the code, the reason, the underwriter id, the date, and the points version. A mark does not change the number, the carrier match, a send gate, or the file's status (W1): it is shown beside the code and counted to find bad rules. It is never a training label. A code cannot be added (A1). The total is a rank, and the underwriter decides: the earlier sentence "An underwriter can ignore the total" is replaced by this.

## Points version (V3)

`POINTS_VERSION = points-<hash>+git:<commit or not-recorded>`. The hash is the first 12 hex of a sha256 over the table, the habitational and contracting word lists, `prepare.HAZARD_TERMS`, and the negation pattern, computed in code as `PROMPT_VERSION` is. It changes when the table or a term list changes. The git slot is `GIT_COMMIT = None` today, because P-017 (the commit hash in the score file) is not built, so the id reads `+git:not-recorded`. Nothing shells out to git; an environment change (for example `LLM_MODEL`) cannot move the id (self-checked). When P-017 is built, set `GIT_COMMIT` in one place. Scores under different versions are not comparable.

## Known limits

Weights are not fitted, and there is no Tier 2 evidence (B-027); the model-risk production veto stands. HABITATIONAL and CONTRACTING keep their known faults (B-021, B-026, B-061 to B-064): "apartamentos" is not read. The wording of a Spanish "Hood:" line is shown but not interpreted ("Hood: not installed" reads as none).
