# T-107e / T-107f: demo file and time-saved check (D-112)

Author: @senior-underwriter, 2026-10-18. Synthetic data only. Read-only on code, scores, team/. No model call. Not committed.

## T-107e: best-case Carrier A direct file

**Chosen: SUB-184** (Keller Insurance Services PA, one-location office, Pflugerville TX). **Backup: SUB-179** (Pinecrest Tax & Accounting PLLC).

Why 184 over 179: 184 has one typed PDF application, an email and a typed Carrier A loss run, nothing else. 179 adds a one-row CSV schedule and a PO-box mailing address (a boundary case), which is more to explain to a manager.

Evidence (v6 files `deliverables/ai-engineer/evals/SUB-174-205-holdout-v6.md`, `-mismatches.md`, gold `deliverables/senior-underwriter/gold-set/SUB-184.md`):
- Gold: complete, no conflict, route carrier_a, TIV 260000, sprinklered JM 2001, sales 640000, one closed water claim $2,350.
- Score: the only miss is `status` (0 misses on name, operations, conflict, route, loss-run fields). Route is a hit. Same for 179.
- The miss is harmless but visible: pipeline says "complete — review pending" with "valued-as-of date 2027-02-15 is not a real past date; check it" (mismatches line 73, class "gold convention": the fictional loss run is dated after the run date). Presenter line: "the tool flags a date it cannot verify and asks a person to look; here the date is a fictional test date." Do not call it "complete, no review" on screen.
- Call: 1 attempt, 0 retries, 1,725 tokens (run record). Dev data now (D-112), so it may be used.

Saved reply (T-104 run cache, `fresh` folder, from_cache 0 at run time):
`underwriting_pipeline/cache/T-104-live/extractions/3ee3da5c9e4e24bff434b69529f6ad81dbe35b6f8dc2bea34517b39feea74338.json` (files: application.pdf, email.md, loss-runs.md; model qwen/qwen3.8-27b, prompt_version b025802c0dfa).
Backup 179: `.../extractions/943a6bad4cb500b535379e0f1fd9d5407b8beeeb655841d3a0af9e3103f03856.json`.
For run-demo.sh: copy `simulation/inbox/SUB-184` into the temp inbox and that one JSON into `$T/cache/extractions/`. The reply key depends on file contents, prompt version and model, so inbox files must be unchanged and the shell must have the Groq host and model set, as for the existing replies. Not checked: that the key matches under the current frozen code (no run allowed).

Route: **R14 then R17 (carrier-match.md)**. R14: exactly one allow-list group (Office, AG:29), no other class word, no W1/W2 word, TIV 260000 <= 5M. R17: every word of the operations text ("Office, clients by appointment, no food, no alcohol") is an allow-list phrase, a listed negation (no food, no alcohol) or a non-occupancy word (clients, appointment). The name "Insurance Services" is never read; `_match()` reads the extracted operations text only.
Why P-061/P-062 must not change it: the file is the one Carrier A direct case that passes with no off-list word. Any change that reads the name, the line of business or the email, or that adds words to W1/W2, or tightens R17 beyond the listed words, could push it to senior_referral. Ask @software-engineer to run SUB-184 and SUB-179 after the change and expect carrier_a for both. If they fall to senior_referral, the demo loses its only direct route. (If P-061 widens the text read to "Line of business", the file must still pass: that line is an office line, so it should.)

## T-107f: "25 to 35 minutes saved" in demo-guide.md

**Verdict: not defensible as written. Nothing was timed, and the high end is too high.** Label it an unmeasured estimate and lower the range.

Checks, underwriter's view:
- Manual time 45 min for a complete in-scope file: plausible only for a messy file (scanned loss run, conflicts, several documents). A clean one-location file like SUB-184 takes me about 25 to 30 min by hand: key the ACORD fields and premises (10 to 15), read and total the loss run (5), check eligibility against the appetite guide (3 to 5), build the carrier package (5 to 10).
- Human time with the tool 10 min (clean) / 20 (messy): too optimistic. Reading 82% of values correctly means 18% are wrong or missing, and I cannot tell which without checking against the source. Checking every value against the documents is most of the reading I did before. Add review-pending flags, a senior confirmation (P-052) and approve/send.
- What the pipeline removes: typing the values, tallying claims, drafting the missing-info list, a first pass at carrier fit. What the human still does: verify against source, resolve conflicts and flagged dates, judge management quality, unusual exposures and loss-run trends, set price and terms, make the final decision. None of that is in either figure and none is automated (no auto-decline, no auto-bind).
- Out of scope files save about nothing: correct as written.
- The 15 to 22 minute average across a mix is built on the same two assumptions, so it carries the same error.

My defensible range, as an unmeasured judgment: **about 10 to 25 minutes per in-scope file** (lower end clean file, upper end messy file with a scanned loss run), roughly 5 to 15 minutes averaged across a mix like the hold-out. Only a timed pilot (same files, an underwriter by hand vs with the tool, both timed) can confirm it.

Exact wording the guide must use (replace the "Estimated saving" line and the average line, keep the heading "estimate, not measured"):
> Time saved: an unmeasured estimate, not a result. No underwriter has timed this tool. Our estimate, based on an underwriter's judgment of the steps, is roughly 10 to 25 minutes per in-scope file, with the lower end for a clean file and the upper end for a messy one. Averaged over a mix that includes out-of-scope files, roughly 5 to 15 minutes. The underwriter still checks every value against the documents, resolves flags, judges the risk and decides; none of that time is removed. A timed pilot is needed before this number is quoted outside this room.

Also change "Treat it as an upper bound" to "Treat it as unconfirmed" and drop the "about 45 minutes" and "about 10 / 20 minutes" lines or mark them "assumed by @pm, not timed".
