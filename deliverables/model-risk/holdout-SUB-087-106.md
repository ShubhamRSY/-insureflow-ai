# Hold-out score review — SUB-087 through SUB-106 (T-093)

- Reviewer: @model-risk. Decisions: D-013, D-080, D-081.
- **2026-10-14 — Run 1 (run `20261014T214450-13011`, section "Run 1" below) is invalid — wrong Python environment, reader libraries missing. Kept for the record; never quoted as a score.** The official T-093 score is the rerun (D-081).
- **Not published** (no `--publish`). Synthetic. Not a production approval. No send is authorized. P-034 is approved but is not a production approval either.

# Rerun (official score, D-081)

**9 of 9 extracted fields scored; claims not read; loss runs = date only.**

## R0. Run record

- Commit scored: `9e725e3d067d4b1d30725a46b8d284c4678f38bf` (score file `commit`; `uncommitted: []`). `git diff 9e725e3 -- underwriting_pipeline deliverables/senior-underwriter/gold-set simulation/inbox` is empty in the repo tree today, so pipeline, gold and inbox are unchanged since the gold was written.
- Python: `/Users/disastershubz/INSURANCE FLOW AI/-insureflow-ai-1/.venv/bin/python` 3.14.6. pdfplumber 0.11.10, openpyxl 3.1.5, pytesseract 0.3.13, pdf2image 1.17.0, pillow 12.3.0. tesseract 5.5.2 (`/opt/homebrew/bin/tesseract`), poppler pdftoppm 26.10.0 (`/opt/homebrew/bin/pdftoppm`). Source: `deliverables/ai-engineer/evals/SUB-087-106-rerun-env-check.txt` ("ALL CHECKS PASS").
- Model `openai/gpt-oss-120b` on `api.groq.com`. Run `20261014T220544-26932`, 20 model calls, 2 from cache (both SUB-101 retries), 47,883 tokens. Call log `deliverables/ai-engineer/evals/SUB-087-106-holdout-rerun.log` (git-ignored, on disk). Fresh cache: scratchpad `rerun-cache` (20 entries, 23 token-log lines).
- Scorer: frozen `underwriting_pipeline/ai/eval_holdout_087.py`, run once by the run owner. I did not re-run it.

## R1. Per field (frozen scorer output, recounted)

19 scored; SUB-101 is call failed (D-081 item 3), counted apart, not a miss (D-021). No all_values_rejected occurred. D-013 floor = 9/10 (90%). Rate = hit / (hit + miss); flagged and not-credited are neither.

| Field | Hit | Hit (needs review) | Miss | Not credited | Flagged | Call failed | Rate | D-013 floor |
|---|---|---|---|---|---|---|---|---|
| named_insured | 17 | 0 | 2 | 0 | 0 | 1 | 17/19 = 89% | Below (by one: see L1) |
| premises | 7 | 0 | 12 | 0 | 0 | 1 | 7/19 = 37% | Below |
| effective_date | 14 | 0 | 5 | 0 | 0 | 1 | 14/19 = 74% | Below |
| operations | 12 | 0 | 7 | 0 | 0 | 1 | 12/19 = 63% | Below |
| sales | 12 | 0 | 6 | 0 | 1 | 1 | 12/18 = 67% | Below |
| tiv | 13 | 0 | 6 | 0 | 0 | 1 | 13/19 = 68% | Below |
| construction | 13 | 0 | 6 | 0 | 0 | 1 | 13/19 = 68% | Below |
| year_built | 11 | 0 | 7 | 0 | 1 | 1 | 11/18 = 61% | Below |
| loss_runs (date only) | 13 | 0 | 0 | 6 | 0 | 1 | 13/13 = 100% | Meets; no date guessed |
| conflict (check) | 10 | 0 | 7 | 0 | 2 | 1 | 10/17 = 59% | Below |

**1 of 9 extracted fields meets the D-013 floor (loss-run date, on the 13 files whose gold has a date; the 6 correct nulls are not credited).** 8 of 9 are below. Over all 19 (not-credited in the denominator) loss runs is 13/19 = 68%.

Recheck: I recounted the 19 x 11 marks from the score file's per-submission checks: they equal the table. I rebuilt all 19 reports from the rerun cache (`.venv/bin/python`, `env -u LLM_API_KEY`, network replaced by a raise, cache copied to a temp dir): 0 cache misses outside SUB-101, which fails again with `'str' object has no attribute 'get'`. Null fields in my rebuild match the scorer's misses (e.g. premises null on 089, 092, 094, 095, 096, 097, 099, 102, 103).

## R2. Status accuracy

10 of 19 (53%); call failed 1. All 9 misses: gold "complete", system "incomplete" (087, 089, 092, 096, 098, 099, 102, 103, 104). 0 false completes: all 8 gold-incomplete files were held. The system called only SUB-091 and SUB-105 complete.

## R3. Carrier-route accuracy (my analysis, outside the frozen scorer)

`deliverables/model-risk/route_holdout_087.py` (now takes `LLM_CACHE_DIR`), run with `.venv/bin/python`, on a temp copy of the rerun cache; `prepare.process_submission` then `workbench.route()`, against gold "Expected carrier route". Token log mtime and git status unchanged after the run.

**9 of 19 (47%); call failed 1 (SUB-101, expected senior_referral).**

| Expected route | n | Hit | System gave |
|---|---|---|---|
| hold | 8 | 8 | hold x8 |
| senior_referral | 5 (+1 call failed) | 1 (105) | hold x3 (092, 098, 103), no_match x1 (091) |
| carrier_a | 2 | 0 | hold x2 (096, 099) |
| carrier_b | 2 | 0 | hold x2 (087, 102) |
| carrier_c | 1 | 0 | hold (104) |
| no_match | 1 | 0 | hold (089) |

Confusion list (misses): 087 carrier_b→hold; 089 no_match→hold; 091 senior_referral→no_match "prohibited class (AG:45-49)"; 092 senior_referral→hold; 096 carrier_a→hold; 098 senior_referral→hold; 099 carrier_a→hold; 102 carrier_b→hold; 103 senior_referral→hold; 104 carrier_c→hold. Every hold miss says "missing information". **0 of 5 carrier routes were reached.**

## R4. Files still not read in the rerun

Yes: 3 of 3 scans. `report["unread"]` lists SUB-088 `scan.jpg`, SUB-097 `scan.jpg`, SUB-101 `loss-runs-scan.jpg` as "could not be opened". All PDFs (11) and xlsx (5) were read. See H1.

## R5. High findings

**RH1 — Every scan in the hold-out failed in the OCR code and was reported as "could not be opened".** Owner: @ai-engineer-assistant.
- Evidence (re-run by me in `.venv`): `sources._ocr_image` on each of the three JPEGs raises `TypeError: color must be int or single-element tuple`. The images are greyscale (mode L). `sources._fill` (line 19) returns an RGB tuple for any image; `_deskew` (line 63) passes it to `image.rotate(..., fillcolor=...)`, which Pillow 12.3.0 rejects for mode L. The bare `except Exception` in `read_folder` (line 230) turns this code error into "could not be opened". The environment check passed because it OCR'd a converted PDF page, not an inbox JPEG through `_ocr_image`.
- Effect: the rotated, dark/tilted and scanned-loss-run cases D-080 asked for were never seen by the model; this score says nothing about scans. P-034 (stop on a missing library) does not catch this, because the library is present.
- Resolve: a P-### (user `approve change`) that (a) gives `rotate` a fill valid for the image mode, (b) stops the run or labels the file "reader error" when a reader raises anything other than a damaged-file error, never "could not be opened", (c) a self-check that runs `_ocr_image` on a mode-L and an RGB JPEG; then the scan cases scored on a new hold-out, not on this one.

**RH2 — 8 of 9 fields are below the floor on files that were read.** Owner: @ai-engineer-assistant.
- Evidence: R1. Premises is null on SUB-089, 092, 099 and 103 although the address is plain text in the read application (PDF or md) and the read schedule (xlsx or csv), e.g. SUB-099 `application.pdf` "Premises address 1800 Hewitt Dr, Waco, TX 76705". SUB-098 (md application, fully read) returned null name, operations, sales, tiv, construction and year built.
- Resolve: find why read addresses become null (model reply or the premises merge rule), fix under an approved P-###, and score a new 20-file hold-out, gold first, scored once, with all nine fields at 9/10 or better.

**RH3 — Route accuracy 9/19 and no carrier route reached.** Owner: @ai-engineer-assistant (cause), @head-of-underwriting (rules).
- Evidence: R2, R3. 9 complete files held for "missing information", driven by the RH2 nulls. A system that only holds cannot be shown to place business.
- Resolve: follows RH2; route accuracy reported with the next hold-out, with every carrier route at least once in gold.

## R6. Medium / Low (one line each, to backlog)

- M1 (@ai-engineer-assistant): SUB-101's unusable reply was cached and replayed by both retries (2 from cache); a reply `prepare` cannot consume should not be cached (D-022). Fix is the approved SUB-101 follow-up in D-081 item 6.
- M2 (@ml-engineer): the D-081 environment check should run each reader on one real inbox file of each type (PDF, xlsx, JPEG), not a synthetic page; fold into P-034.
- M3 (@model-risk): pillow 12.3.0 has been in `.venv` since 2026-09-08; any mode-L scan result scored in `.venv` since then may carry the same failure; recheck before citing earlier scan scores.
- M4 (@head-of-underwriting, @senior-underwriter): SUB-091 (cocktail bar) gives non-overridable "prohibited class" where gold says senior decides; reconcile rule or gold.
- L1 (scorer, frozen): named_insured miss on SUB-097 is "and" vs "&"; with that normalisation the field is 18/19 = 95%. The frozen score stands at 17/19.
- L2: the run log is git-ignored (`*.log`); add it on purpose if it must reach the repo.

## R7. T-027 veto

**Stands.** The rerun is valid for typed PDF, xlsx, md, csv and email, but only 1 of 9 extracted fields meets the D-013 floor (RH2), 0 of 5 carrier routes were reached (RH3), and no scan was read (RH1).

What lifts it: RH1 and RH2 fixed under approved P-### changes; then one new 20-file hold-out (this set has now been scored; a third run on it would be tuning on it), gold first, commit saved, scored once in a checked `.venv` with every reader exercised on a real file, all nine extracted fields at 9/10 or better, failed calls counted apart, no loss-run date guessed, and status and route accuracy reported. Lifting T-027 would still not be a production approval: Tier 2 evidence (validation-standards.md) and the other open vetoes remain.

# Run 1 (invalid — wrong Python environment, reader libraries missing; kept for the record, never quoted as a score)

- Reviewer: @model-risk. Date: 2026-10-14. Decisions: D-013, D-039, D-080.
- **9 of 9 extracted fields scored; claims not read; loss runs = date only.**
- Commit scored: `9e725e3d067d4b1d30725a46b8d284c4678f38bf` (gold and inbox added at 21:44:42; run started 21:44:54). Pipeline tree identical to freeze commit `d944583` (`git diff d944583 9e725e3 -- underwriting_pipeline` is empty; working tree clean on the V2 paths; scorer last changed in `d944583`).
- Model: `openai/gpt-oss-120b` on `api.groq.com`. Run `20261014T214450-13011`; call log `deliverables/ai-engineer/evals/SUB-087-106-holdout-run.log`.
- Scored once by the frozen scorer `underwriting_pipeline/ai/eval_holdout_087.py`. I did not re-run it. **Not published** (no `--publish`); this is a run record for the user.
- Synthetic. Not a production approval. No send is authorized.

## 1. Per field (run 1, invalid) (frozen scorer output, verified)

Scored submissions: 19. SUB-101 is "call failed", counted apart, not a miss (D-021). D-013 floor = 9/10 (90%) per field.

| Field | Hit | Hit (needs review) | Miss | Not credited | Flagged | Call failed | Hit rate (of 19) | D-013 floor |
|---|---|---|---|---|---|---|---|---|
| named_insured | 13 | 0 | 6 | 0 | 0 | 1 | 68% | Below |
| premises | 5 | 0 | 14 | 0 | 0 | 1 | 26% | Below |
| effective_date | 9 | 0 | 10 | 0 | 0 | 1 | 47% | Below |
| operations | 9 | 0 | 10 | 0 | 0 | 1 | 47% | Below |
| sales | 8 | 0 | 11 | 0 | 0 | 1 | 42% | Below |
| tiv | 9 | 0 | 10 | 0 | 0 | 1 | 47% | Below |
| construction | 10 | 0 | 9 | 0 | 0 | 1 | 53% | Below |
| year_built | 9 | 0 | 10 | 0 | 0 | 1 | 47% | Below |
| loss_runs (date only) | 10 | 0 | 3 | 6 | 0 | 1 | 53% | Below |
| conflict (check, not an extracted field) | 14 | 0 | 4 | 1 | 0 | 1 | 74% | Below |

**0 of 9 extracted fields meet the D-013 floor.** Counting SUB-101 in the denominator (20) lowers every rate further. Not-credited nulls are not counted as correct.

Verification: I rebuilt the 19 reports from the extraction cache (temp copy, no key, network blocked) and recomputed named_insured, premises, sales and year_built by the scorer's rules: 76 of 76 marks match the frozen JSON, and 19 of 19 cache keys match, so the reports I routed are the ones that were scored. No all_values_rejected status occurred. No loss-run date was guessed: all 3 loss-run misses are nulls.

## 2. Status accuracy

10 of 19 (53%). All 9 misses are the same direction: gold "complete", system "incomplete" (SUB-087, 089, 091, 092, 096, 098, 099, 102, 105). The system never called an incomplete file complete (0 false completes); the 8 gold-incomplete files were all held.

## 3. Carrier-route accuracy (my analysis, outside the frozen scorer)

Method: `deliverables/model-risk/route_holdout_087.py` runs `prepare.process_submission` on a temp copy of the cache with `env -u LLM_API_KEY` and `urlopen` replaced by a raise, then `workbench.route()`; compared with gold "Expected carrier route". No real log, page or outbox was written (git status and token-log mtime unchanged).

**8 of 19 (42%); call failed 1 (SUB-101, expected senior_referral).**

| Expected route | n | Hit | System gave |
|---|---|---|---|
| hold | 8 | 8 | hold x8 |
| senior_referral | 5 (+1 call failed) | 0 | no_match x3 (091, 103, 105), hold x2 (092, 098) |
| carrier_a | 2 | 0 | hold x2 (096, 099) |
| carrier_b | 2 | 0 | hold x2 (087, 102) |
| carrier_c | 1 | 0 | no_match (104) |
| no_match | 1 | 0 | hold (089) |

Confusion list (misses only):
- SUB-087 carrier_b → hold (missing information)
- SUB-089 no_match → hold (missing information)
- SUB-091 senior_referral → no_match, "prohibited class (AG:45-49)", not overridable
- SUB-092 senior_referral → hold (missing information)
- SUB-096 carrier_a → hold (missing information)
- SUB-098 senior_referral → hold (missing information)
- SUB-099 carrier_a → hold (missing information)
- SUB-102 carrier_b → hold (missing information)
- SUB-103 senior_referral → no_match (readable class on no carrier list), overridable
- SUB-104 carrier_c → no_match (readable class on no carrier list), overridable
- SUB-105 senior_referral → no_match, "prohibited class (AG:45-49)", not overridable

Every hit is a hold. 0 of 11 non-hold expectations were met. The only two files the system called complete (SUB-103, SUB-104, all nine fields hit) were both misrouted.

## 4. High findings

**H1 — The scored run could not open 19 of the hold-out's files; a missing library was recorded as a damaged file and the run went on.** Owner: @ai-engineer-assistant (run), @software-engineer / @ml-engineer (environment).
- Evidence: the interpreter that produced the cached reports has no `pdfplumber`, `openpyxl` or `pytesseract` (`/opt/homebrew/bin/python3`; `.venv/bin/python` has all three). With it, `sources.read_folder` marks every PDF (11), every xlsx (5) and every scan (3) "could not be opened". The cache keys of the scored run match this reading for 6 of 6 sampled files and only 1 of 6 under `.venv`, so the scored run had the same blindness. 15 of 20 submissions lost at least one file; only SUB-090, 093, 098, 102, 104 were fully read. `sources.read_folder` catches the `ImportError` in a bare `except Exception` and reports "could not be opened".
- Effect: this score measures the extractor on email, md and csv text only. It says nothing about typed PDFs, Excel schedules or scans, which are most of the hard mix D-080 asked for. Most misses are nulls on files that were never read (premises: 12 of 14 misses are nulls). The honesty controls worked (files listed as needs human, no invented values), but the "could not be opened" reason is false and an underwriter would ask the producer to resend a good file.
- Resolve: (a) a missing reader library stops the run (SystemExit, like `provider_guard`), never becomes a per-file "could not be opened"; (b) the scorer or `regression_dev.py` checks the reader imports before the first submission and writes the interpreter and library versions into the score file; (c) a self-check for (a). Both are changes under `underwriting_pipeline/`, so they need a numbered P-### and the user's `approve change`. (d) Whether this hold-out may be re-run once on the same frozen commit in `.venv`, or a new 20-file hold-out is needed, is @user's call; I can accept either if both results are reported and nothing under `underwriting_pipeline/` changes before the re-run.

**H2 — No extracted field meets the D-013 floor, even on the five files that were fully read.** Owner: @ai-engineer-assistant.
- Evidence: table in section 1, 26% to 68%. On the fully read files alone (090, 093, 098, 102, 104) named_insured is 4 of 5 and SUB-098 returned null name and null operations from a typed md application; SUB-102 returned a list of cooking equipment as "operations".
- Resolve: a hold-out scored once, gold first, in a checked environment (H1), with every one of the nine fields at 9/10 or better and no guessed loss-run date.

## 5. Medium / Low (one line each, to backlog)

- M1 (@head-of-underwriting, @senior-underwriter): route rules and gold disagree on complete files — custom cabinetry with spray finishing (103) and laundromat (104) give no_match, a pure cocktail bar (091) gives non-overridable "prohibited" where gold says senior decides; reconcile rule or gold.
- M2 (@ai-engineer-assistant): SUB-101 reply passed the usability check, was cached, then crashed `prepare` (`'str' object has no attribute 'get'`); the retry replayed the cached reply, so retrying could not recover. Counted correctly as call failed; a reply prepare cannot consume should not be cached (D-022 intent).
- M3 (@ai-engineer-assistant, @model-risk): check whether earlier runs (dev sets, B-222 table, earlier hold-outs) used the same interpreter; any PDF/xlsx/scan result from it is not evidence for those formats.
- L1 (scorer, frozen, no change now): exact match marks "&" vs "and" (091, 097, 105) and a missing comma (093) as misses; at most 4 name and 1 premises marks; does not change the floor result.
- L2 (scorer): when documents disagree but no conflict is stored, a field that picked the gold's side scores hit (SUB-094 tiv, construction, year_built); only the conflict check catches it.
- L3: the run log is git-ignored (`*.log`, .gitignore:44); it is saved on disk but will not reach the repo unless added on purpose.

## 6. T-027 veto

**Stands.** Condition (d) — the 20-file hold-out, gold first, scored once — has been run, but it does not show the extractor is fit: H1 (the run could not read PDFs, Excel or scans) and H2 (0 of 9 fields at the D-013 floor).

What lifts it: H1 resolved under an approved P-###, then one hold-out scored once (a re-run of this one on the frozen commit or a new 20, as @user decides) in a checked environment, with all nine extracted fields at 9/10 or better, failed calls counted apart, and no loss-run date guessed. Lifting the veto would still not be a production approval: Tier 2 evidence (validation-standards.md) and the other open vetoes remain.
