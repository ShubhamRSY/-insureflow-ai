# Proposals P-010 and P-011

- Author: @ai-engineer-assistant
- Date: 2026-10-11
- For: @user (the AI Engineer)
- Not implemented. No code, prompt, scorer, or score file was changed to write this. No model call was made. No scorer was run.
- Synthetic data only. Neither proposal is a production approval. @model-risk can still block production.
- Published scores are not recounted by either proposal.

Where a point is your choice, the options are listed and none is picked.

---

# P-010 — Fix T-059: send gates, the all_values_rejected status, and the SUB-017–026 scorer

## Why

T-059 has three verdicts, all on 2026-10-11 in `team/DISCUSSION.md`, `Re: T-059`:

- @model-risk, OBJECTION: NOT APPROVED. Criteria 3 and 4 fail.
- @software-engineer, REVIEW: REJECT. Criterion 3 fails.
- @account-manager, REVIEW: REJECT. Criterion 3 fails.

What they found is true in the code today:

- `prepare.approve()` checks the report only for the account manager. As the user it writes to `to-producer` whatever the status is.
- `package.send_to_carrier()` checks the status only `if report`. With no report it sends.
- `prepare.py --approve` on the command line never passes a report.
- `write_drafts()` writes a draft only when there is a request. On a failed file it writes nothing, so the old draft stays. It deletes an unresolved conflict file. It saves nine null fields with no status and no error.
- The workbench card prints FAILED and still lists Missing, a carrier match, a score, and the approve option. `record_decision()` never looks at the status.
- `eval_holdout.py` (SUB-017 through SUB-026) prints `k/10` with failed files inside the 10.
- `llm_extract.py` saves the model's reply to the cache before the gate runs. If the gate then rejects every value, `prepare.py` labels it "model call returned no fields", the same words used for a truly empty reply. The two cases cannot be told apart in any past file.

## The change

### Part 1. Your five points ("Re: T-059", 2026-10-11)

Your words, then what the code would do.

1. "send gates refuse extraction_failed and all_values_rejected for every actor including user"
   Both `prepare.approve()` and `package.send_to_carrier()` refuse when the file's status is `extraction_failed` or `all_values_rejected`. The check runs before the actor is looked at. There is no override for these two statuses. The user's override stays for every other block (incomplete, open conflict, out of appetite, unread page), as D-017 says.

2. "gates read the file's current status themselves, never trust a passed-in report"
   One small function in `prepare.py` returns the current status of a submission. Both gates and `record_decision()` call it. The `report` argument is no longer a source of truth for the status, and the account manager's agency check (complete, conflicts, unread pages, appetite) uses the same self-read report. If the status cannot be read, the gate refuses. How "current" is read is your choice:

   - Option G1, run it again at the gate. The gate calls `process_submission()` on the inbox folder. A file with a saved model result makes no model call. A file with no saved result (every failed file, because a failed call is never cached) calls the model at send time. Always current. Costs tokens and seconds on uncached files, and a send can wait on the rate limit.
   - Option G2, read the last saved run. `write_drafts()` saves the status, the error, and the rest of the report next to the extraction file. The gate reads that file. No model call at send time. It is as current as the last `write_drafts()` run: if a document was added to the inbox after that run, the gate does not know. No saved file means refuse.

3. "old drafts are removed or marked failed when extraction fails"
   When a run ends in `extraction_failed` or `all_values_rejected`, `write_drafts()` deals with the draft already in `simulation/pending-approval/`. It also keeps the conflict file and saves the status and the error (see Part 2). Which of your two words applies is your choice:

   - Option D1, remove. The old draft file is deleted. Nothing is left to approve. The old text is lost unless it is in git.
   - Option D2, mark. The old draft stays with a first line that says extraction failed and it must not be sent. The text is kept for the human. The gate in point 1 still refuses it.

4. "workbench hides approve on failed files"
   On a card with either status the approve option is not shown. See Part 2 for the rest of the card.

5. "a self-check for each case"
   See Part 4.

### Part 2. What each reviewer said would resolve it

Quoted from their messages. Nothing here is made weaker. Where your rule is stricter than a reviewer's words, your rule is used and that is said.

@model-risk, OBJECTION, Re: T-059: "Resolves it: both send functions require the report and refuse `extraction_failed` for every actor; `eval_holdout.py` gets a call-failed count and excludes failed files from the denominator; a self-check for each."

- Refuse for every actor: point 1.
- "require the report": your point 2 is stricter. The gate reads the status itself, so a missing, empty, or stale report cannot open it. This is a different mechanism from the one @model-risk wrote. @model-risk must review it again.
- `eval_holdout.py`: Part 3.
- A self-check for each: Part 4.
- Medium-1 (all values rejected): D-024, Part 3.
- Medium-2 (old draft left, conflict file deleted, all-null file with no status): point 3 and the two items below.
- Medium-3 (card lists nine Missing and offers approve; no self-check on the failed path): point 4, the items below, and Part 4.

@software-engineer, REVIEW, Re: T-059: "Changes required: (a) both send functions take the report as required and refuse `extraction_failed` for every actor, the user included; the CLI loads it. (b) `write_drafts` removes the draft, keeps the conflict file, and writes status and error. (c) The workbench hides Missing, match, and score on a failed file and `record_decision` refuses approve for it. (d) `eval_holdout.py` gets the count and leaves failed files out of the denominator. (e) One self-check for each."

- (a): point 1 and point 2. The CLI `--approve` goes through the same gate, so it cannot skip the check. Your point 2 replaces "take the report as required".
- (b): `write_drafts()` keeps the conflict file when the status is one of the two, and writes `status` and `error` into the saved extraction file. For the draft, @software-engineer asked for removal. You wrote "removed or marked". That is options D1 and D2 above.
- (c): the card hides Missing, the carrier match, and the score, and `record_decision()` refuses an approve after reading the status itself.
- (d): Part 3.
- (e): Part 4.
- Low-2 (a folder whose only file has no text makes no call, is "incomplete", and gets a request for all nine fields): not in the changes @software-engineer required and not in your five points. It is not in this proposal. Say so if you want it added.

@account-manager, REVIEW, Re: T-059: "Changes required: (a) both send functions refuse `extraction_failed` for every actor and read the status from the current run, not from an optional argument; (b) a failed run removes or marks the old draft, keeps the conflict file, and saves status and error; (c) the card hides Missing, match, and approve on a failed file; (d) a self-check for each."

- (a): points 1 and 2. "from the current run" is met fully by option G1. Under option G2 it is the last saved run, which answers Medium-1 ("A report from an earlier good run passes for a file that has since failed") only as long as the failed run was saved. @account-manager must say whether G2 is enough for that seat.
- (b): point 3 and the conflict file and status items above.
- (c): the card hides Missing, the match, the score, and approve.
- (d): Part 4.

The card after the change, for both statuses: the files, the FAILED or REJECTED line with the reason, the unread pages, and the edit and decline options. Edit and decline are left as they are today. That is my assumption, and the workbench is @software-engineer's to decide with @senior-underwriter.

### Part 3. D-024, the all_values_rejected status

Your ruling: "all values rejected = not a failed call. Count fields as misses, file status all_values_rejected, goes to human review, never sendable."

Status. In `process_submission()`, a model call that answered and whose values were all rejected by the gate gets the status `all_values_rejected`. `error` stays empty, because no call failed. The reason is stored in a new key on the report. A call that raised, or a reply with nothing in it, stays `extraction_failed`, as D-021 says. The two cases are already separate in the code: an empty reply raises inside `llm_extract.py`, and only an answered reply reaches the gate.

Human review and sends. No missing-information request is drafted for the file, because the data may be in the documents and the gate refused it. The file is shown on the workbench with its own line. Both send gates refuse it for every actor (point 1). It is never sendable.

How it is scored. Seven of the eight scorers and `regression_dev.py` decide "call failed" from `report["error"]`. With `error` empty, an all_values_rejected file is no longer counted as call failed, with no scorer edit. What it is counted as is your choice:

- Option S1, score it with the rules already in each scorer. No scorer is edited for D-024. A null where the gold has a value is a miss. A null where the gold says the item is missing is "not credited" in the six newer scorers, and counts as correct in `eval_holdout.py` and `eval_gold.py`, as it does today for any file. A value put in after the model by the document rules is judged as usual.
- Option S2, every field of the file is a miss. This is your sentence read word for word. It adds one line to each of the eight scorers (`eval_gold.py`, `eval_holdout.py`, `eval_holdout_027.py`, `_037.py`, `_047.py`, `_057.py`, `_067.py`, `_077.py`): when the status is `all_values_rejected`, every check for that file is set to miss. No hit rule for any other file changes. A loss run that the gold says is missing is then also a miss for that file.

How it is cached. Today the reply is saved before the gate, so an all-rejected reply is already in the cache and is not called again. Your choice:

- Option C1, keep it cached. No change to `llm_extract.py`. D-022 item 3 bars only a failed or empty call from the cache, and D-024 says this is neither. A later change to the gate is applied to the saved reply with no model call. The miss stays a miss until the files, the prompt, the OCR settings, or the model change.
- Option C2, do not cache it. `llm_extract.py` runs the gate before it saves and skips the save when nothing survives. The file is called again on every run. That costs tokens on every run, and a second try can turn a miss into a hit by chance, which is the masking @model-risk's Medium-1 was about.

The `eval_holdout.py` edit (SUB-017 through SUB-026). This is the one frozen scorer edited under every option. Exactly:

- In `main()`: count the files whose checks are `call_failed`. The denominator `n` becomes the number of files minus that count.
- The JSON gets one new key, `call_failed`, with the count. `n` is the new denominator.
- The Markdown gets one new line, "Call failed, not scored: k", and the table prints `hits/n` with the new `n`.
- In `score_one()`: a failed file reports `scored: 0` in place of `scored: 10`.
- No `hit_*` function changes. No gold file changes. `score_one()` marks every other file as before.

`eval_gold.py` and the six `eval_holdout_0NN.py` files already count call failed apart. They are edited only under option S2.

### Part 4. Self-checks

Each one stubs the model, uses a temp folder, makes no model call, and writes no score file.

- `approve()` refuses `extraction_failed`: as user, as account manager, with no report, and with a good report from an earlier run passed in.
- `approve()` refuses `all_values_rejected`: the same four ways.
- `send_to_carrier()` refuses each of the two statuses: the same four ways.
- Both gates refuse when no status can be read.
- The command line `--approve` is refused on a failed file.
- `process_submission()`: a raised call and an empty reply give `extraction_failed` with the error and no request. A reply whose values are all rejected gives `all_values_rejected`, an empty `error`, the reason, and no request.
- `write_drafts()` on each of the two statuses: the old draft is removed or marked (your choice), the unresolved conflict file is still there, and the saved file holds the status and the error.
- Workbench: the card for each status has no approve option, no Missing list, no carrier match, and no score. `record_decision()` refuses approve and still records edit and decline.
- `eval_holdout.py`: with stubbed rows, a failed file is left out of the denominator and shown in the count. The check writes to a temp folder only.
- Under S2: one check per scorer that an all_values_rejected file is all misses and another file's marks do not move.
- Under C2: an all-rejected reply is not saved and is called again.
- The existing checks (`llm gate ok`, `package ok`, `workbench ok`, and the `prepare.py` check) still pass.

## Files and owners

| File | Owner | What changes | When |
|---|---|---|---|
| `underwriting_pipeline/ai/prepare.py` | @ai-engineer-assistant | The `all_values_rejected` status. The function that reads the current status. The gate in `approve()` and `--approve`. `write_drafts()`: old draft, conflict file, saved status and error. Self-checks. | After `approve change P-010` |
| `underwriting_pipeline/ai/eval_holdout.py` | @ai-engineer-assistant (frozen scorer) | The call-failed count and the denominator, as written in Part 3. Under S2, one more line. | After `approve change P-010` |
| `underwriting_pipeline/ai/eval_gold.py` and `eval_holdout_027.py`, `_037.py`, `_047.py`, `_057.py`, `_067.py`, `_077.py` | @ai-engineer-assistant (frozen scorers) | Nothing under S1. One line each under S2. | Only if you choose S2 |
| `underwriting_pipeline/ai/llm_extract.py` | @ai-engineer-assistant | Nothing under C1. Gate before save under C2. | Only if you choose C2 |
| `underwriting_pipeline/app/package.py` | @software-engineer | `send_to_carrier()` and `agency_problem()` call the status reader and refuse both statuses for every actor. Self-check. | A task from @pm |
| `underwriting_pipeline/app/workbench.py` | @software-engineer | The card and `record_decision()`. Self-check. | A task from @pm |
| `deliverables/data-engineer/extractions/SUB-xxx.json` | @data-engineer decides the schema | Two new keys, `status` and `error` (more under G2). The file is written by `prepare.write_drafts()`. | @data-engineer says yes or names another place |

My part goes first, because the status reader lives in `prepare.py` and the two app files call it. `approve change P-010` covers the `underwriting_pipeline/ai/` files only. The two app files are @software-engineer's and need a task from @pm. T-059 criterion 3 is not met until both parts are in and the three reviewers have looked again.

## Trade-off

- The user loses the override on these two statuses. That is what D-021 and D-024 say. The override stays for every other block.
- G1 makes a send slower and can spend tokens. G2 is cheap and can be one run behind.
- D1 loses the old draft text. D2 leaves a file in pending-approval that must never be sent.
- S2 edits eight frozen scorers. S1 edits one.
- A file that used to read "call failed" will read as misses. Scores from before and after this change are not like for like on those files.
- A gate change that is too strict now shows as misses and a blocked file, not as a failed call that is retried.

## Risk to the loss-run no-guess rule

- The prompt, the gate, the citation check, OCR, and the document rules are not touched. Nothing in this proposal can create a loss-run date.
- An all_values_rejected file gets no missing-information request, so a missing loss run on that file is not asked for until a person reviews it. No value is guessed in the meantime and nothing is sent.
- Under S2, a loss run that is correctly left empty scores as a miss on such a file. That is a scoring effect only. It must not be read as a reason to loosen the gate.
- Under C2, the model gets another try on every run. A different reply could carry a loss-run date. It passes the same gate and citation check as any other reply, but the score for that file can move between runs.

## Expected score impact

- Extraction does not change, and the cache keys do not change. On the quick set of 15 no field's hit count should move. Any field that drops will be reported.
- From now on, a file whose values are all rejected moves out of "call failed" and into misses (S2), or into misses and not-credited (S1). Miss counts can go up and call-failed counts go down. How many past files this would have been is not known, because both cases were saved with the same error text.
- `eval_holdout.py`: on a future run with a failed file, the denominator is smaller than 10. With no failed file its numbers are the same as today.
- Published scores are not recounted. `SUB-017-026-holdout.md` and `.json`, and every other published file, stay as they are.

## What is NOT changed

- No prompt text. No model. No OCR. No change to what the gate accepts or rejects.
- No hit or miss rule for any file that is not `extraction_failed` or `all_values_rejected`.
- No gold file. No published score file. No scorer's `main` is run against its published path (D-025).
- The cache key. The provider guard (P-008). Temperature 0 (P-009).
- Nothing under `src/insureflow`.
- No auto-decline and no auto-bind. No send is authorized. The account manager's rules and the written reason stay.
- T-059 stays IN_REVIEW. Its status is not changed by this proposal.

## After approval

`python underwriting_pipeline/ai/regression_dev.py --quick <a path in the scratch folder>`, the quick set of 15 (D-022). `--quick` calls `score_one` only and does not run a scorer's `main`. The output path is given on the command line so that nothing in the published folder is written.

## Your choices on P-010

1. G1 or G2: how the gate reads the current status.
2. D1 or D2: remove the old draft or mark it.
3. S1 or S2: how an all_values_rejected file is scored.
4. C1 or C2: whether an all-rejected reply stays in the cache.
5. Whether @software-engineer's Low-2 (a folder with no readable text) is added.

P-010 is not implemented until the user replies "approve change P-010".

---

# P-011 — D-025: published score files are read-only, tests write to a scratch folder

## Why

Your rule: "Rule from now: published score files are read-only; tests write only to a scratch folder."

Today the code does the opposite:

- Each of the eight scorers has its published path written into it (`OUT_MD`, `OUT_JSON`, and `OUT` in `eval_gold.py`), and its `main()` writes there on every run.
- `regression_dev.py --holdout <scorer>` calls that `main()`. That is how the SUB-077 through SUB-086 files were overwritten during T-065.
- `regression_dev.py` with no path writes `regression-SUB-017-076.json` in the published folder, and `--quick` with no path writes `regression-quick-15.json` there.
- Every file in `deliverables/ai-engineer/evals/` is writable.

## The change

1. A scratch folder: `deliverables/ai-engineer/evals/scratch/`, with one line in `.gitignore` so it is never committed. The name is yours to change.
2. Every score run writes to the scratch folder unless it is told to publish. This covers the eight scorers, `--holdout`, `--quick`, and the full 60.
3. A publish run is asked for with one flag, `--publish`, on the same command that does the scoring. Before any scoring starts it checks the published path. If a file with that name is already there, it refuses and stops. It never overwrites. There is no force flag.
4. After a publish run writes its files, it sets them read-only (`chmod a-w`).
5. One time, the files already published are set read-only: the 22 committed files in `deliverables/ai-engineer/evals/`. The three T-060 rerun files (`SUB-077-086-holdout-rerun.json`, `.md`, and `SUB-077-086-original-vs-rerun.md`) are set read-only when T-060 is DONE, because @model-risk's verdict asks for corrections to that memo first.
6. A self-check, with a temp folder and no model call: a default run writes only to scratch; `--publish` onto an existing name is refused before scoring; `--publish` onto a new name writes the file and leaves it read-only.

How the scorers are pointed at scratch is your choice, because D-025 says changing where they write is a scorer edit:

- Option W1, no frozen scorer is edited. `regression_dev.py` sets the scorer's output paths to the scratch folder before it calls the scorer's `main()`, the same way it already swaps in the retry. `regression_dev.py` becomes the only allowed way to run a scorer. Running a scorer file directly (`python eval_holdout_077.py`) still aims at the published path. It is stopped only by the read-only bit and by the rule. The read-only bit is not stored by git, so it is gone after a checkout or a restore of that file.
- Option W2, the eight scorers are edited, output paths only. Exactly: in `eval_holdout.py`, `eval_holdout_027.py`, `_037.py`, `_047.py`, `_057.py`, `_067.py`, and `_077.py`, the two lines that set `OUT_MD` and `OUT_JSON`; in `eval_gold.py`, the one line that sets `OUT`; plus one import line in each. The paths come from one new small file, `underwriting_pipeline/ai/score_out.py`, which returns the scratch path by default and the published path only with `--publish` and only when no file is there. Running a scorer directly is then safe too. No `score_one`, no `judge`, no `hit_*`, no gold parsing, and no counting line is touched.

Under both options the read-only bit is a second lock, not the main one. The main lock is the check in code that refuses an existing name.

## How an official score still gets published

- A new hold-out (20 submissions, gold first, D-020 and D-022) gets its own scorer file with a new published name, as before. It is scored with `python underwriting_pipeline/ai/regression_dev.py --holdout <scorer> --publish`. The name is new, so the run writes the two files and locks them.
- A milestone run of the full 60, and a quick-set result that a memo will cite, are published the same way under a new file name.
- An existing published file is never replaced by a run. If a decision says a rerun replaces a score (as D-021 item 2 did), the new result is published under a new name and the memo says which file is the score of record. Both files stay.
- A person can still remove the read-only bit by hand. That is a deliberate act by the user, not something a run can do.

Three points are yours:

- Who may run `--publish`. Option U1: only on a task that names the run as the official one. Option U2: only after you say so in the chat for that run.
- "Scored once". A scratch run of a hold-out before its publish run would be a second scoring. Option O1: `--publish` for a hold-out is refused if a scratch result for that set already exists, so the rule is held in code; a first run that crashed then needs you to delete its scratch file. Option O2: no such check; the rule is held by the task and the review, as it is today.
- Which files count as published. Proposed: every file now in `deliverables/ai-engineer/evals/`, the development regressions included. Say so if the development files (`regression-SUB-017-076*.json`, `.md`, and `SUB-017-036-dev-rerun.*`) should stay writable.

## Files and owners

| File | Owner | What changes |
|---|---|---|
| `underwriting_pipeline/ai/regression_dev.py` | @ai-engineer-assistant | Default output is the scratch folder for `--holdout`, `--quick`, and the full run. The `--publish` flag, the refusal, and the read-only step. Self-check. |
| `underwriting_pipeline/ai/score_out.py` (new) | @ai-engineer-assistant | W2 only. The one place that decides scratch or published. |
| The eight scorers | @ai-engineer-assistant (frozen scorers) | Nothing under W1. The output-path lines under W2, as listed above. |
| `.gitignore` | @ai-engineer-assistant, one line | Ignore the scratch folder. |
| `deliverables/ai-engineer/evals/*` | @ai-engineer-assistant | File permission only. No content changes. |

All of it is mine. Nothing for @software-engineer.

## Trade-off

- One more word to type for an official run, and an official run can never be redone under the same name.
- W1 leaves a gap when a scorer file is run directly. W2 closes it and edits eight frozen scorers.
- Under W2, the header that the 067 and 077 scorers print ("Scored by @model-risk with this file unchanged after the gold answers were written") would not be true of any later scratch output from them. The published files are not regenerated, so what they say stays true of them.
- A read-only file must be unlocked by hand to fix a typo in a memo. That is the point of the rule, and it is slower.
- The read-only bit is lost on a git checkout of that file. The code check does not depend on it.

## Risk to the loss-run no-guess rule

None. This changes where score files are written. It does not touch extraction, the gate, the prompt, OCR, or any hit or miss rule.

## Expected score impact

None. No score changes. No published score is recounted or rewritten. A scratch run prints the same counts the same code prints today.

## What is NOT changed

- No hit, miss, not-credited, flagged, or call-failed rule. No gold file. No extraction code, prompt, OCR, or model.
- The content of every published score file.
- The extraction cache and the token log.
- The rule for a new hold-out: 20 submissions, gold first, scored once, no code change after the gold exists.
- Nothing under `src/insureflow`. No send is authorized.
- Until this is approved and in the code, D-025 stands as written: nobody runs a scorer's `main` against its published path.

## After approval

The self-check above, then `python underwriting_pipeline/ai/regression_dev.py --quick`, which now lands in the scratch folder. No field should move, because no scoring line changes.

## Your choices on P-011

1. W1 or W2: redirect from `regression_dev.py` only, or edit the output paths in the eight scorers.
2. U1 or U2: who may run `--publish`.
3. O1 or O2: whether "scored once" is checked in code.
4. Whether the development regression files are locked too.
5. The scratch folder name, if you want another.

P-011 is not implemented until the user replies "approve change P-011".

---

# T-070 — what was built (2026-10-13)

- Author: @ai-engineer-assistant
- Task: T-070, the `underwriting_pipeline/ai/` part of P-010 and its Part 3 `eval_holdout.py` edit.
- Approved by: the user typed exactly `approve change P-010` (D-043). Choices taken from D-029: **G2, D1, S1, C1**; Low-2 not added.
- Synthetic data only. Not a production approval. No send is authorized. @model-risk can still block production.
- Published scores are not recounted. No scorer's `main` was run against its published path (D-025).

## Commits (D-034)

- `fde95b7` — the code: `prepare.py` (status, gate, drafts, saved run) and `eval_holdout.py` (call-failed count). Made before the quick-set run.
- `57bd138` — one follow-up: drop the in-memory `status_reason` from the saved payload so the saved key set stays exactly the closed `ExtractionRun` set. The quick-set result below was re-run on this commit (byte-identical; the cache served every file).

## What changed, by file

### `underwriting_pipeline/ai/prepare.py`

- New `ROOT`, `EXTRACT_DIR = deliverables/data-engineer/extractions/`, `HASH_ALGORITHM = "sha256"`, `REFUSED_STATUSES = ("extraction_failed", "all_values_rejected")`, `REJECT_REASON`.
- `process_submission()`: an answered reply whose values the gate rejected now gets `status = "all_values_rejected"` (D-024) with `error` empty, no request, `complete = False`, and `status_reason` on the in-memory report. A raised call and an empty reply stay `extraction_failed` with the error. The report also now carries the run metadata (model, prompt version, OCR settings, host, temperature).
- New `_run_metadata()`, `hash_payload()` (the `data-model.md` canonical bytes), `read_saved_run()` (the G2 reader: no file, no usable hash, an unknown algorithm, or a digest mismatch all raise), `current_status()`, `_saved_payload()`.
- `write_drafts()`: writes the full `ExtractionRun` payload (every key in the data-model table) with `saved_hash`/`hash_algorithm`; on either refused status it removes the old draft (D1) and keeps the conflict file. It no longer writes nine null fields with no status.
- `approve()`: reads the last saved run and verifies its hash itself (G2) **before the actor is read**; refuses the two statuses for every actor, including the user and the CLI `--approve`; refuses when nothing is saved; the account manager's `agency_problem()` uses the self-read report, never the passed-in one. The `report` argument is kept for callers but is no longer a source of truth.
- Self-check: `python underwriting_pipeline/ai/prepare.py`. Every case above, plus the standing demo. No model call, temp dirs only.

### `underwriting_pipeline/ai/eval_holdout.py` (S1 — the one frozen scorer edited)

- `main()`: counts the files whose checks are `call_failed`, sets `n = files − that count`, adds a `call_failed` key to the JSON, and adds the line `Call failed, not scored: k` to the Markdown; the table prints `hits/n`.
- `score_one()`: a failed file reports `scored: 0`, not `10`.
- No `hit_*` rule and no gold file changed.
- Self-check: `python underwriting_pipeline/ai/eval_holdout.py --self-check`. A stubbed failed file leaves the denominator and shows in the count; the real `score_one` marks a raised call `scored: 0`. Writes to a temp folder only.

## The hash reading — please confirm

"Reads the file's current status" is implemented as: load `deliverables/data-engineer/extractions/SUB-xxx.json`, drop `saved_hash` and `hash_algorithm`, re-serialize with `json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=True)`, UTF-8, sha256, compare to `saved_hash`; then read `status` from that same object. **It is not a hash of the inbox source documents.** This matches the `data-model.md` reader contract and H1/H2. If you meant the digest of the source documents instead, say so and I will change it.

## Quick set of 15 (D-022, D-025)

Command: `python underwriting_pipeline/ai/regression_dev.py --quick deliverables/ai-engineer/evals/scratch/quick-15-after-T-070.json` (a scratch path, so no published file is written).

- All 15 files: no failure, no `call_failed`, no `all_values_rejected`.
- **No field's hit count moved.** Re-running the same 15 on the pre-change code (`d5750fd`) against the warm cache gives byte-identical counts, so this change moves nothing on the set: `named_insured 13, premises 12, operations 13, sales 13, tiv 14, construction 14, year_built 15, loss_runs 9, conflict 13, status 13` of 15.
- Any dropped field: none.

## Open items for you

1. **`error` enum.** `data-model.md` makes `error` a closed enum (`rate_limit_429`, `timeout`, `reply_not_usable`, `call_error`), non-null only on `extraction_failed`. The extractor raises a free-text safe message, P-010 does not normalize it, and C1 keeps `llm_extract.py` unchanged, so the saved file carries the safe text, not the enum value. Mapping the failure kind to the enum is a small `prepare.py` change but is outside P-010; say if you want it as a follow-up proposal.
2. **`status_reason`.** The reason for `all_values_rejected` is on the in-memory report but not in the saved file, because the saved key set is closed and `saved_hash` covers it. G2 stops at the status and the reason is derivable from it. Confirm you are content with this.
