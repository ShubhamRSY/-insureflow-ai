# Check of P-048 (D-095) and the T-103 hold-out mix — @model-risk, 2026-10-16

**P-048 verdict: APPROVE WITH CHANGES. H1 open (item e). P-048 is not done until H1 closes.** Items (a)–(d) meet the acceptance criteria. An approved P-048 is not a production approval; the T-027 veto stands.

**T-103 mix verdict: APPROVED WITH CONDITIONS** (below). Do not build or run SUB-154–173 until H1 is closed, because T-103 requires live and cache outputs kept apart.

## What I re-ran
No model calls. A temporary copy of `underwriting_pipeline/cache` was used, `llm_extract._post` was replaced with a function that raises an error, `LLM_PACE_SECONDS=0`, and all outputs went to my scratchpad. `git status` was clean for `underwriting_pipeline/`, `simulation/`, `deliverables/` and `team/` before I wrote this file. HEAD is d08dbec.
- Self-checks with `.venv/bin/python <file> --self-check`: prepare, llm_extract, eval_holdout_v2, regression_dev and workbench all pass.
- Dev re-score of SUB-127–146 (20 of 20 files from the cache, 0 calls): counts identical to the committed `SUB-127-146-dev-v2-cache-rescore.json`, and every file's checks match. Loss runs: 8 hit, 0 miss, 12 not credited. Operations: 19/20. Route: 16/20. 0 false completes, 0 silent errors. senior_referral: 6 of 7 gold. carrier_c: 1 of 1.
- The 3 loss-run misses from before P-048 (P-047-dev: 5/3/12) were SUB-129 (image-only PDF, Carrier A), SUB-131 (JPG, Carrier B) and SUB-133 (rotated JPG, Carrier C). In each case OCR broke the strict carrier layout, so `carrier_run_check` returned `no_date` and the date was dropped with "loss run found but no valued-as-of date" (file held). With P-048 (b), scans are left out of the undated hold. All three now keep 2026-09-30 with "loss run from scan/spreadsheet: check it". 129 is held on its own sales conflict. 131 and 133 are complete — review pending. **The dev deliverable does not contain this explanation; it is given here (M4).**
- Route misses (4): SUB-135 provisional no_match, gold carrier_a (thrift/books, no "retail" in ops). SUB-138 provisional carrier_a, gold hold (M2). SUB-142 provisional none, gold senior_referral (M3). SUB-144 provisional none, gold no_match.
- (a) probes: the "Fwd:", "> " and "#" forms, a forwarded note with letter words and a valued date, and the same note inside an email. Each result is "unclear" (not a recognised carrier loss run), the value is kept and review is required. It is never a letter and never accepted. A forwarded run that is fully in layout is still accepted, as specified.
- (c): the screenshot shows "Provisional route: senior_referral … (provisional — file on hold: open conflict) · No send until the hold clears". In the self-check, `package._route` stays "hold" and the file cannot be overridden. (d): the self-check reads two non-adjacent lines; the line between them is not quoted. A part that is not found rejects the whole quote.

## H1 (open) — B-363: a cache re-score with any non-cached file overwrites the live run's score file
`eval_holdout_v2.main` picks the `-cache-rescore` name only when **every** row's call starts with "from cache" (`cache_only`). If any row is "call failed: …", "called: …" or "not sent: no readable text", the re-score writes the live run's `<name>.json/.md`. Failed calls are never cached (D-021/D-022), so the case the criterion targets breaks the rule: a live run with a 429 or failed file, then re-scored from cache, overwrites the live file and its per-file retry record. The re-score also tries a live call for the missing file; nothing in the re-score path forbids that call.
**Reproduced:** I made a temporary cache copy without SUB-128's entry, pre-wrote `live.json` and `live.md`, and ran `HOLDOUT_IDS=127-128 HOLDOUT_OUT=<scratch>/live` with calls blocked. SUB-127 came "from cache". SUB-128 tried a call, which failed, so `cache_only` was False, and `live.json` and `live.md` were overwritten.
**Remediation (closes H1):** choose re-score mode from an explicit setting (for example `HOLDOUT_RESCORE=1`), not from the row outcomes. In that mode, make no model call: a cache miss is counted as `call_failed` and kept apart, and the output always goes to `-cache-rescore.*`. A live run also refuses to overwrite an existing score file (it writes a new name or stops). Add a self-check for a re-score with one cache miss: it writes `-cache-rescore`, leaves the live file byte-identical, and makes 0 calls. This is a scorer and pipeline change under P-048; I do not make it.

## Medium / Low (backlog, one line each)
- M1: A scanned applicant note under a copied carrier header with a date now becomes "complete — review pending" and can be routed. Probe: gate_loss_run on a JPG with value 2025-09-30 keeps the value with only "loss run from scan/spreadsheet: check it". Before P-048 the file was held. When a scan does not match the layout, the reason should say "carrier layout not verified from scan; confirm it is the carrier's own run".
- M2: The provisional route ignores open questions that decide the class. SUB-138 (fertilizer, possibly a hazardous commodity) shows provisional carrier_a, but gold is hold. The send is blocked and the route is labelled provisional, so this is safe.
- M3: The TIV check runs before the class referral. SUB-142 (roofing, AG:38 "whatever the TIV") shows provisional none against gold senior_referral. This is P-049 / routing-order territory.
- M4: The dev deliverable does not explain the 3 former loss-run misses (D-095 asks for it). The explanation is above; add it to the readout.
- M5: The committed cache-rescore JSON lists 13 uncommitted gold files, so it was scored before d08dbec. My re-run at d08dbec gives identical results, but the file is not a score of a commit.
- L1: PREFIX does not strip "RE: Fwd:", "Subject: Fwd:" or "**…**" headers. The error goes in the safe direction (unclear or letter, file held).
- L2: Scorer v2 adds a "route" column. The T-027 path says "all 9 fields 9/10". State whether route is part of that gate before T-103 is scored.
- L3: A re-score with `LLM_API_KEY` unset stalls in retry sleeps at SUB-131, and `endpoint_settings` raises when the header is written. As a result, a cache-only re-score needs a key in the environment. It should not.

## T-103 mix — approved with conditions
Counts checked: 8 carrier-format runs (A 3: files 1, 2, 8; B 3: files 3, 4, 6; C 2: files 5, 7), 6 non-carrier runs (files 9–14), 6 with none (files 15–20). Formats: 3 typed PDF, 2 typed .md, 2 JPG, 1 image-only PDF. Every route appears in gold. carrier_c (file 5) and senior_referral (file 4) are reachable from typed, gold-complete files. The B-350 probe (file 11) and the P-048 (b) scans (files 6–8) are covered.
Conditions:
1. File 8 (light wholesale) states that its commodities are not hazardous. Otherwise the gold is hold (the SUB-138 lesson) and the carrier_a coverage is lost.
2. File 11 (roofing) states a TIV, so the AG:38 referral is tested apart from M3. Alternatively, record that its provisional route depends on M3.
3. One of the 6 non-carrier runs is a JPG scan of an applicant note under a copied carrier header (gold incomplete). This probes M1 and does not change the carrier-format mix.
4. Build and run only after H1 is closed (T-103: "Live and cache outputs kept apart (B-363)"). Settle L2 before scoring.

## LOOK-AGAIN on H1, commit 4b313be (2026-10-16, @model-risk)

**Verdict: H1 CLOSED.** P-048 is approved with changes, and no High finding is open. The M and L items stay in the backlog. This is not a production approval, and the T-027 veto stands. The T-103 mix conditions 1–3 still apply. Condition 4 (build only after H1 closes) is now met.

What I re-ran: `eval_holdout_v2 --self-check` passes. All outputs went to my scratchpad, using a temporary cache copy. `urllib.request.urlopen` was replaced with a function that records any attempt and raises an error; no attempt was recorded.
- Probe 1 (my H1 repro): `HOLDOUT_RESCORE=1`, with a cache copy that lacks SUB-128 and live `live.json`/`live.md` already present. SUB-127 came from the cache. At SUB-128 the run stopped with "re-score refused: a file has no saved reply in the cache … Nothing written". It made no call and wrote no file, and the live files are unchanged.
- Probe 2: a live run whose score file already exists stopped before any file was read ("refused: live.json exists …"). Nothing was scored and nothing was overwritten.
- Probe 3: a full `HOLDOUT_RESCORE=1` re-score of SUB-127–146 wrote only `-cache-rescore.*`. Its counts and every per-file check match the committed file: loss runs 8/0/12, route 16/20, 0 false completes.
- `_no_call` raises SystemExit. No `except BaseException` or bare `except` in llm_extract, prepare, regression_dev or eval_holdout_v2 can swallow it.
- M4 is closed: NOTES.md now explains the 3 former loss-run misses, and the explanation matches mine.

### Backlog (one line each)
- L4: the re-score mode is opt-in. A re-score run without `HOLDOUT_RESCORE=1` is a live run: it makes calls, but it can no longer overwrite a score file. Write the flag into RUN-RULES.md and the T-103 run steps.
- L5: when a re-score is refused, it says only that "a file" has no saved reply. Name the submission id.
