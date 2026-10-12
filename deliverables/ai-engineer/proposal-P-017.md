# Proposal P-017 — The commit hash in every score file and memo, and a status that says exactly what happened

- Author: @ai-engineer-assistant
- Date: 2026-10-11
- For: @user (the AI Engineer)
- Task: T-088. Decisions: D-034, D-037, D-038 items 4 and 6. Works with P-011 (D-029, approved, not built, T-072).
- Status: PROPOSAL. Not approved. Not implemented.
- No code, scorer, or score file was changed to write this. No model call was made. No scorer was run.
- Synthetic data only. Not a production approval.
- Published scores are not recounted or rewritten.

Where a point is your choice, the options are lettered and none is picked.

## Why

D-034, your words: "Rule from now: commit the code before every scored run and record the git commit hash in each score file and memo. A scorer status must say exactly what happened, e.g. "not sent: no readable text", never "Call: ok" when no call was made."

What the code does today:

- No score file and no memo holds a commit hash. The hash is written in a memo by hand.
- `prepare.process_submission`, lines 518 to 520: when a folder has no readable text, no model call is made and `error` stays `None`.
- Six scorers then print `Call: {row['error'] or 'ok'}`. So a folder that was never sent reads "Call: ok". That is my T-039 finding (B-145): on SUB-057 through SUB-066, four rows (SUB-057, 058, 064, 065) show "Call: ok" with no model reply behind them.
- A reply read from the cache also prints "Call: ok", although no call was made in that run.

## The change

### Part 1. The status

`prepare.process_submission` adds one key to the report, `call`, a plain sentence. It is set where the thing happens. `error` and `status` stay as they are.

Every value a row can show:

| `call` | When |
|---|---|
| `not sent: no files in the folder` | the folder holds no file the reader returns |
| `not sent: no readable text` | files exist, and none has text a model can be given |
| `called: reply used` | a model call was made in this run and its reply was used |
| `from cache: saved reply used, no call in this run` | the saved reply for these exact files was used |
| `call failed: <reason>` | the call raised: HTTP 429, a timeout, HTTP 401, another HTTP error. The reason is today's `error` text, with the key removed as today |
| `called: reply not usable` | the host answered and the reply was empty or not JSON |
| `called: every value rejected by the gate` | P-010's `all_values_rejected`, once T-070 is built. Until then this case prints as `called: reply not usable`, as it is labelled today |

A host the provider guard refuses stops the whole run and writes no row, as today.

How `prepare.py` knows a reply came from the cache: `llm_extract.USAGE` already gets one row per extraction with `cached: True` for a saved reply. `process_submission` reads the last row. Nothing in `llm_extract.py` changes.

The scorers print the sentence in place of "ok":

- `Call: {row['call']}.` in the six scorers that print a Call line.
- "Call: ok" is never printed again by any scorer.

No mark changes. A row that was not sent keeps the marks it gets today (misses, and not-credited where the gold says missing). A failed call is still `call_failed` and is still counted apart (D-021).

### Part 2. The commit hash

One helper, in `underwriting_pipeline/ai/score_out.py`, the file P-011 adds: `commit()` returns the output of `git rev-parse HEAD` and the list of changed paths from `git status --porcelain` for the checked paths.

- Every score JSON gets two top-level keys: `"commit": "<hash>"` and `"uncommitted": [paths]`.
- Every memo a scorer writes gets one header line: `- Commit: <hash>.` When the list is not empty the line reads `- Commit: <hash>, with uncommitted changes in: <paths>. This is not a score of that commit.`
- `regression_dev.py` writes the same two keys in the quick-15 file and the full-60 file.
- A memo written by hand still names the hash, copied from the score file.

### Part 3. A run with uncommitted changes in the pipeline paths

D-038 item 6: the orchestrator makes the commit before each scored run (pipeline, deliverables, and team paths, on `ai-team`, `src/insureflow` left out, no push). No role commits, and no run commits. A run only looks.

Your choices:

- U, what a run does when the checked paths have uncommitted or untracked changes.
  - U1: a `--publish` run refuses before any scoring and names the paths. A scratch run goes on and records the hash and the paths, with the "not a score of that commit" line.
  - U2: every run that scores refuses, scratch runs included. Nothing is scored on uncommitted code. Each trial during a build then needs a commit from the orchestrator first.
  - U3: no run refuses. Every run records the hash and the paths. The rule is held by the task and the review.
- V, which paths are checked.
  - V1: `underwriting_pipeline/` only. After P-014 (G1) the cache folder and the token log are ignored by git and do not count.
  - V2: also `deliverables/senior-underwriter/gold-set/` and `simulation/inbox/`, so the commit also shows that the gold and the files existed, unchanged, before the score.

Under every option: when git cannot give a hash, the keys hold `"unknown"`, and a `--publish` run refuses. In `regression_dev.py` the full run can continue a file it started earlier; if that file's hash is not the current one, the run stops and names both, so one file never mixes two commits.

### Part 4. The scorer for the new hold-out (SUB-087 through SUB-106)

Decided, not a choice. D-038 item 4, your words: "New hold-out scores effective date but not claims; label becomes "9 of 10 fields scored; loss runs = date only"." Scores published before it keep "8 of 9 fields scored; loss runs = date only" (D-033 item 5, D-038 Amends).

A new file, `underwriting_pipeline/ai/eval_holdout_087.py`: a copy of `eval_holdout_077.py` with these differences and no others.

- The ids are SUB-087 through SUB-106, 20 submissions. The output names are new, so P-011's `--publish` writes them once.
- A new score column, `effective_date`, read from the gold line `- Effective date: YYYY-MM-DD` that T-092 adds. It uses the same `judge` as every other field: a null is never a hit; a null where the gold line says missing is `not_credited`.
- "effective" is added to the topic list, so a real conflict on the effective date with both sides stored is `flagged`, the same as the other fields.
- The claims line in the gold is read by `parse_gold` and not scored. The loss-run rule is the 077 rule: the valued-through date only.
- The memo header and the score JSON carry the label exactly as D-038 has it: "9 of 10 fields scored; loss runs = date only".
- It has Parts 1 and 2 from its first line: the `call` sentence and the commit hash. Its author line names @ai-engineer-assistant, not the retired handle.
- It must be written and committed before @senior-underwriter writes the gold (T-092), because nothing changes after the gold exists. It needs the gold line's exact wording from @senior-underwriter first.

One choice is left, the hit rule for the new line:

- X1: a hit when the extracted effective date equals the gold date exactly.
- X2: a hit when the gold date appears in the extracted value, which is how the loss-run date is judged today.

A point for you on the label. I do not change it. The extractor has nine fields: named insured, premises, effective date, operations, sales or payroll, TIV, construction, year built, loss-run date. The 077 scorer scores eight of them, which is the "8 of 9". The new scorer would score all nine, so by that same count the label would read "9 of 9". "9 of 10" is true if the claims line is counted as a tenth field that is not scored; claims are not a field the extractor has today. The score table will also show two more rows, `conflict` and `status`, as it always has: eleven rows in all. If you want other words, say them; otherwise the scorer prints D-038's label as written.

## Which frozen scorers and which lines change

Line numbers are of the files as they are today. P-010 (T-070) edits `eval_holdout.py` first and may move its lines.

| File | Line today | Change |
|---|---|---|
| `eval_holdout_027.py` | 123 | add `"call": report.get("call")` to the row |
| | 135 | add `commit` and `uncommitted` to the JSON |
| | 139 (header list) | add the Commit line |
| | 160 | `Call: {row['error'] or 'ok'}.` becomes `Call: {row['call']}.` |
| `eval_holdout_037.py`, `_047.py`, `_057.py` | 127, 139, 143, 164 | the same four |
| `eval_holdout_067.py`, `_077.py` | 167, 179, 183, 209 | the same four |
| `eval_holdout.py` (SUB-017–026) | 134 (row), 155 (JSON), 160 (header), 184 | the same four. Line 184 prints `Call failed: yes/no`; it becomes `Call: {row['call']}.` |
| `eval_gold.py` (SUB-007–016) | 287 (header), 293, 333 (JSON) | the Commit line; the "Call failed, not scored" line lists each such file with its `call` sentence. Its JSON is a list, so the two keys go in a small file beside it, or the list is wrapped: choice J below |
| `regression_dev.py` | 68 and 128 (rows) | add `"call"` |
| | 69 and 116 (the `done` dict) | add `commit` and `uncommitted`; the stop when a continued file has another hash |
| | 93 | prints `row.get("error") or "ok"`; becomes the `call` sentence |
| `prepare.py` | 517 to 529, 594 | set `report["call"]` |
| `score_out.py` (new with P-011) | | `commit()` |
| `eval_holdout_087.py` (new) | | Part 4 |

- J, `eval_gold.py`'s JSON, which is a bare list today.
  - J1: leave its shape. The hash goes in the memo only for that scorer.
  - J2: wrap it as `{"commit", "uncommitted", "details": [...]}`. Anything that reads the old shape must change.

Not touched in any scorer: `score_one`'s checks, `judge`, `hit_*`, `sides_stored`, `parse_gold`, `FIELDS`, `IDS`, the gold paths, the counting, and the `- Author: @ai-engineer` lines (D-028 left the frozen scorers' author lines alone).

## How this fits with P-011, so the scorers are edited once

P-011 (W2) edits, in the same eight scorers, the `OUT_MD`, `OUT_JSON`, and `OUT` lines and adds one import of `score_out`. P-017 edits other lines of the same files and puts its helper in the same new file.

- If P-017 is approved before T-072 is built: both are built in one pass. Each scorer is opened once, there is one diff per file, one self-check, and one quick-set run. The task order is @pm's; today T-072's notes put P-017 after it.
- If P-017 is not approved by then: T-072 goes alone, and P-017 would be a second edit of the eight files.
- P-010 (T-070) edits `eval_holdout.py` before both. It adds the `all_values_rejected` case; Part 1's last table row is its sentence.
- The publish flag stays P-011's. P-017 adds only the check in Part 3.

## Trade-off

- Eight frozen scorers are edited, on output lines only. The header some of them print, "Scored by @model-risk with this file unchanged after the gold answers were written", is not true of any later scratch output from an edited file. P-011 already has this trade-off. The published files are not regenerated, so what they say stays true of them.
- Old and new score files differ in shape: new ones have `call`, `commit`, and `uncommitted`. Old ones do not, and are not changed.
- Under U1 or U2 a run can refuse until the orchestrator commits. That is slower, and it is the point of D-034.
- Under U2 each build trial needs a commit, and the branch fills with small commits.
- "from cache" will be the status on most quick-set rows. It is true, and it reads less simply than "ok".
- The hash shows which commit the run saw. It does not show which host answered or what the model replied; that is the token log (P-012, P-014).

## Risk to the loss-run no-guess rule

None. No extraction code, gate, prompt, or OCR step changes, and no hit or miss rule changes. The new scorer keeps the loss-run rule as "date only" and says so in its label. Claims are not scored, and no claim value is extracted.

## Expected score impact

- No count changes on any existing set. A scratch run of an old scorer prints the same marks; only the Call text and the Commit line differ.
- The new hold-out gains one scored field. Its effective-date hits cannot be compared with any earlier set, because no earlier set scored it.
- On scans, expect effective-date misses: the saved replies hold "2O2H-01-O1", "RO2F-O1-01", and "A2F-O1-O1". With P-016 those become nulls, which are misses too.

## What is NOT changed

- No hit, miss, not-credited, flagged, or call-failed rule. No gold file. No extraction code, prompt, OCR, gate, or model. `llm_extract.py` is not edited.
- No published score file or memo. "Call: ok" stays in the files already published. The notes on those rows are @model-risk's dated lines (T-090).
- The label "8 of 9 fields scored; loss runs = date only" on every score published before the new hold-out.
- The cache and the token log. P-010, P-011, and P-014 as approved.
- Who commits: the orchestrator (D-038 item 6). No run and no role commits or pushes.
- The hold-out rules: 20 submissions, gold first, scored once, no code change after the gold exists, published once on your word (U2 of P-011).
- Nothing under `src/insureflow`. Nothing under `underwriting_pipeline/app/`. No send is authorized.

## After approval

1. Build, with P-011 in one pass if @pm orders it so.
2. Self-check, in a temp folder with no model call: a folder with no readable text prints "not sent: no readable text" and never "ok"; a saved reply prints "from cache"; a stubbed failed call prints "call failed"; the hash in the file equals `git rev-parse HEAD`; a changed pipeline file is named in `uncommitted`; the refusal under the U you pick; every published score file is byte-identical before and after.
3. `python underwriting_pipeline/ai/regression_dev.py --quick` to a scratch path. No field should move, because no scoring line changes. Any field that does is reported.

## Your choices on P-017

| Letter | Point | Options |
|---|---|---|
| U | a run with uncommitted changes | U1, U2, U3 |
| V | which paths are checked | V1, V2 |
| X | the hit rule for the Effective date line | X1, X2 |
| J | the shape of `eval_gold.py`'s JSON | J1, J2 |

And one point, not a lettered choice: whether the label stays "9 of 10 fields scored; loss runs = date only" as D-038 has it, given the count above.

P-017 is not implemented until the user replies "approve change P-017".
