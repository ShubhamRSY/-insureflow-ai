# P-014 — A token log that survives a killed run and can rebuild a run's totals, host and temperature in the cache key, log and cache out of git

- Author: @ai-engineer-assistant
- Date: 2026-10-11
- For: @user (the AI Engineer)
- Status: APPROVED by @user, D-033 item 1: "approve change P-014 with U1 R2 H1 O1 L1 T2 S1 G1". With D-030 item 1 it also includes "include host and temperature in the cache key" and "gitignore token_log.jsonl and the cache folder". Built under T-078. Not a production approval.
- Brought up to what was approved on 2026-10-11, before any code was edited (T-078, first box). The first draft said "Not approved", said the cache key was unchanged, and had no G choice.
- Source: @ml-engineer's review of T-063, Medium-1 and Medium-2.
- Synthetic data only. Not a production approval. @model-risk can still block production.

## Why

D-026 makes `underwriting_pipeline/cache/token_log.jsonl` the evidence for failed-call claims. @ml-engineer found two ways it falls short of that.

**Medium-1. One half-written line breaks the log.** I repeated it in a scratch folder, with no model call:

- A log whose last line is cut short (a run killed during the write) makes `budget()` stop with `JSONDecodeError`. `regression_dev.py` calls `budget()` when it reports, so the report fails.
- The next row is written straight after the cut line with no line break. Two rows become one unreadable line. The second row, a real call, is lost.

**Medium-2. A run cannot be rebuilt from the file.** "This run" totals exist only in memory while the run is alive. A row has no run id, no cache key, and no host. A result served from the cache writes no row. So after a run ends, the file cannot say which rows belonged to it, how many files came from the cache, or which host answered.

## The change, in simple words

Three files: `underwriting_pipeline/ai/llm_extract.py`; the `failed_attempts` block of `regression_dev.py` (T2); `.gitignore`. Plus one change to the git index (G1).

1. **Skip a line that cannot be read.** `budget()` no longer stops on a bad line. It also skips a line that is JSON but has no `epoch` or `model`.
2. **Start every row on a new line.** Before a row is written, if the log does not end with a line break, one is written first. A cut line stays as it is, on its own line, and the new row is whole.
3. **The log is never rewritten.** A bad line is not repaired and not deleted. It stays as a record that a write was cut.
4. **Three new keys on every new row:** `run` (one id for the process), `key` (the cache key of the files), `host` (the host name from LLM_BASE_URL, no path, never the API key).
5. **One row for each result served from the cache**, with `event: cache_hit` and 0 tokens. The 24-hour budget already ignores every row that has an `event`, so a cache hit is not counted as a call.
6. **A reader:** `python underwriting_pipeline/ai/llm_extract.py --budget` also prints, for each run id in the file, calls, cache hits, failed attempts by cause, and tokens. Read from the file only.
7. **The 13 old rows are left as they are.** They have no run id. The reader shows them under "no run id".
8. **Include host and temperature in the cache key** (D-030). The key was made from the prompt version, the model, and the files. It is now made from the prompt version, the model, the host, the temperature, and the files. The host is the host name from LLM_BASE_URL, the same value as `host` on a log row (O1). The temperature is the one number sent to the model, 0; it is now a named constant used for both the request and the key, so the two cannot differ. The value sent is unchanged.
9. **Gitignore token_log.jsonl and the cache folder** (D-030). Two lines in `.gitignore`: `underwriting_pipeline/cache/token_log.jsonl` and `underwriting_pipeline/cache/`.
10. **Untrack what git already tracks there** (G1). See below.

## What the new key does to the 13 saved results

- Every one of the 13 saved results in `underwriting_pipeline/cache/extractions/` becomes unreachable. A file's name is its key. The new key hashes two more values, so no file can have a name the new code looks for. 13 of 13, none kept.
- The 13 files are not deleted, not renamed, and not rewritten. They stay on disk as they are. They are still the saved replies that earlier reviews and the P-016 estimate read.
- The 13 rows already in the token log stay as they are and are still read (item 7).
- Cost: the first run after this change calls the model for every file. The quick set is 15 fresh calls; before, 3 of its 15 had a saved result (SUB-027, 029, 038). The ten SUB-077 to SUB-086 results are also not reused.
- Nothing is pruned. The old files are never read again by the pipeline and are never removed by it.

## What G1 does to files git already tracks

Git tracked the token log and 9 of the 13 saved results (10 paths). 4 saved results were never tracked.

- G1, as D-033 records it: "G1 untracks them as a staged change with no commit". The ignore lines are added, and `git rm --cached` is run on exactly those 10 paths. The files stay on disk, byte for byte. Nothing is committed by this task; the orchestrator commits (D-038 item 6).
- After the commit, a run no longer shows as a change in git. The log and the saved results are then on this machine only: a fresh clone has neither, and git no longer keeps their history from that commit on. Earlier commits still hold the 10 files as they were.
- The G choice was put to the user in the chat by the orchestrator (D-031 item 2), not in this file. D-033 lists "G1 or G2" and records only G1's meaning. G2's wording is not in any team file, so it is not restated here.

## Self-check that would be added

All in temporary folders with a temporary log. No model call. The real log must be byte-identical after.

- A log ending in a cut line: `budget()` returns, the next row is on its own line and is readable, and the cut line is still in the file.
- A line that is JSON with no `epoch`: skipped, not a crash.
- A stubbed run with one call, one cache hit, one 429, and one unusable reply: the totals rebuilt from the file equal the in-memory totals.
- Two runs into one log: each run's rows carry its own id and the totals do not mix.
- A cache hit is not counted as a call in the 24-hour budget.
- No row holds the API key.
- A different host, or a different temperature, is a different key and a new call. The old key formula and the new one never give the same name.
- A cache-hit row that cannot be written stops the run and is not reported as a failed extraction.
- `LLM_RUN_ID` names the run; without it the id is made from the start time and the process id.

## Trade-offs

- **The log grows.** Before, a cached file wrote nothing. After P-014 it writes one row. The quick set is 15 rows a run and the full set is 60. The log is no longer tracked in git (item 9, G1), so a run does not show as a change.
- **The saved results are paid for again.** All 13 are unreachable under the new key. See the section above.
- **The host in the key is the host name only.** Two servers on one machine at different ports, serving the same model name, share a key. The user's words are "host"; the port is not in it.
- **The log and cache are local only** once the G1 change is committed. A lost disk loses the evidence D-026 relies on.
- **A skipped line is not counted.** If the cut line was a real call, the 24-hour token total is short by that one call. The host's own limit still applies, so the worst case is a 429 that the log did not predict.
- **A cache-only run starts writing.** Today a run served only from the cache writes nothing. With cache-hit rows it writes to the log. If the cache folder cannot be written, that run would now meet a write error. See choice L.
- **The file is evidence, not proof.** A row can still be lost if the machine stops in the moment between the model's reply and the write. P-014 does not close that.
- **Old and new rows differ.** Anything reading the log must accept rows with and without the new keys.

## Risk to the loss-run no-guess rule

None found. P-014 changes what is written to the log and how the log is read. It does not touch the prompt, the files sent to the model, the reply, or the gate. A loss-run date is still dropped unless the model returned it with an exact quote from a file at 0.75 or more, and a no-known-loss letter is still not a loss-run date.

One indirect point, and the reason for choice L: logging now happens on the cache path too. If a log write failed there and the code turned that into a failed extraction, a file with a good saved result would show as `extraction_failed`. That is a wrong status, not a guessed value. It cannot create a loss-run date.

## Expected score

No score should move. No hit or miss rule changes and no model reply changes. No published score is recounted. The quick set of 15 runs after the change, as the role file says. It is T-064, it runs after the orchestrator's commit (D-034), and all 15 calls are fresh. Fresh calls at temperature 0 can still differ from an earlier reply, so a mark that moves is the model's variance or an earlier change, not P-014; T-064 reports any field that drops.

## Not changed

The prompt and prompt version, OCR, the temperature sent to the model (0), the saved result files on disk, the gate, every hit and miss rule, every scorer, `prepare.py`, the provider guard, the pacing, the retry count, and the 13 rows already in the log.

Changed by the D-030 additions: the cache key (item 8), and what git tracks (items 9 and 10).

Not part of P-014, still open from the same review: the message layout is not in the cache key; missing usage is logged as 0; a read-only cache folder discards a paid reply; a saved `{"parsed": {}}` is trusted; nothing is pruned. The all-values-rejected case is in P-010.

## Choices, and what the user chose

The user chose **U1 R2 H1 O1 L1 T2 S1 G1** (D-033). The options are kept below as they were put.

**U. A line that cannot be read**
- U1: skip it, and `budget()` reports how many lines it skipped.
- U2: skip it and say nothing.

**R. The run id**
- R1: made by the code at the start of each process, from the start time and the process id.
- R2: taken from a variable the user sets (for example `LLM_RUN_ID=T-066-run-2`), and made as in R1 when it is not set. The three runs of T-066 could then be named.

**H. Where cache-hit rows go**
- H1: in `token_log.jsonl` with every other row. One file tells the whole run. The log grows as above.
- H2: in a second file beside it. The token log stays small. A run's story is in two files.
- H3: no row per hit. One summary row at the end of the run. A killed run writes no summary, which is the case Medium-2 is about.

**O. What `host` holds**
- O1: the host name only, for example `api.groq.com`.
- O2: the whole LLM_BASE_URL.
Neither holds the key.

**L. A log write that fails on the cache path**
- L1: the run stops. The log is complete or the run does not go on.
- L2: one warning line is printed and the saved result is used. The run goes on with a gap in the log.

**T. Where per-run totals are shown**
- T1: only in `--budget`.
- T2: also in the `failed_attempts` block that `regression_dev.py` writes, so each regression file carries its run id.

**S. Submission id on a row** (@model-risk's Low on T-063)
- S1: not in P-014. `llm_extract` receives files, not a submission id; the `key` and `files` identify the call.
- S2: add it. This means passing the id in from `prepare.py`, a second file and a wider change.

**G. Files git already tracks in the cache folder** (added with the D-030 additions; put to the user in the chat)
- G1: add the ignore lines and untrack the token log and the tracked saved results as a staged change, with no commit, the files left on disk. Chosen.
- G2: not chosen. Its wording is not recorded in a team file.

How each chosen letter is built:
- U1: `budget()` returns `skipped_lines`, and `--budget` prints it.
- R2: the run id is `LLM_RUN_ID` when set, else the start time and the process id.
- H1: one `cache_hit` row per result served from the cache, in `token_log.jsonl`.
- O1: `host` is the host name only.
- L1: if the `cache_hit` row cannot be written, the run stops (SystemExit, as the provider guard does). It is not turned into `extraction_failed`.
- T2: the `failed_attempts` block also holds `run` and `run_totals`, read from the file.
- S1: no submission id on a row.

## How it would be checked

`python underwriting_pipeline/ai/llm_extract.py` prints "llm gate ok". Altered copies in a scratch folder must each fail the new checks. Published score files, the saved results, and the real token log are compared byte for byte before and after.

Approved: "approve change P-014 with U1 R2 H1 O1 L1 T2 S1 G1" (D-033). The build record is on T-078 in team/TASKS.md.
