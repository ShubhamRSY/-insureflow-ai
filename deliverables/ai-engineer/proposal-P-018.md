# Proposal P-018 — Normalize the saved `error` field to the closed enum (T-070 open item)

- Author: @ai-engineer-assistant
- Date: 2026-10-13
- For: @user (the AI Engineer)
- Task: none yet; raised by D-044. @pm numbers it and, if needed, opens a task for after approval.
- Decisions: D-044 (raise P-018), D-021 (a failed call is its own status), D-024 (`all_values_rejected` is not a failed call), D-017 (an approval must be the user's exact line).
- Status: PROPOSAL. Not approved. Not implemented.
- No code, prompt, OCR setting, cache file, scorer, or score file was changed to write this. No model call was made. No scorer was run.
- Synthetic data only. Not a production approval. @model-risk can still block production.
- Published scores are not recounted.

Where a point is your choice, the options are lettered and none is picked.

---

## Context

`deliverables/data-engineer/data-model.md` (T-069, revised 2026-10-13) defines the saved `error` key as a closed enum, non-null **only** on `status = extraction_failed`:

> one of `rate_limit_429`, `timeout`, `reply_not_usable`, `call_error`. `null` for `complete`, `incomplete`, and `all_values_rejected` (D-024 — no call failed). Never model or document text (S-01 minimization).

The code does not do this. T-070 left it alone on purpose (C1 keeps `llm_extract.py` unchanged), and the memo's "Open items for you", item 1, says so:

> `data-model.md` makes `error` a closed enum … The extractor raises a free-text safe message, P-010 does not normalize it, and C1 keeps `llm_extract.py` unchanged, so the saved file carries the safe text, not the enum value. … say if you want it as a follow-up proposal.

D-044 raised it: "the `error` enum normalization is raised as a new proposal, P-018, by @ai-engineer-assistant, and waits for the user's `approve change P-018` before any build."

The issue is small but real. The G2 gate and the workbench read the saved run, not the live report. If `error` is free text, a reader that wants to branch on the cause of failure must string-match host wording, which can change between calls and hosts; the closed enum is what the data model promises.

## What the code does today

- `underwriting_pipeline/ai/prepare.py:536`, inside `process_submission()`: `error = llm_extract._safe(str(exc))`. The whole safe message is stored, then written to the saved run through `report["error"] = error` (`prepare.py:606`) and `_saved_payload()` (`prepare.py:702`). The message is one of the free-text strings `llm_extract` raises, for example (verbatim shapes from `llm_extract.py`):
  - `model call failed: HTTP 429 rate limit, tokens per day` (also `requests per day`, `per minute`) — `llm_extract.py:406`
  - `model call failed: HTTP 429 rate limit` — `llm_extract.py:418`
  - `model call failed: timeout` — `llm_extract.py:417`
  - `model call failed: HTTP 401 authentication failed.` — `llm_extract.py:409`
  - `model call failed: HTTP <code> <detail>` — `llm_extract.py:410`
  - `model call failed: <safe url error text>` — `llm_extract.py:417`
  - `model call returned no fields` — `llm_extract.py:476` (an answered reply that parses to nothing; re-raised at `llm_extract.py:479`)
  - a JSON parse error message from `_parse_json` — `llm_extract.py:474`, re-raised at `llm_extract.py:479`
- `llm_extract.py` already classifies each failed attempt into a kind for the token log and the failure totals: `FAILURE_KINDS = ("rate_limit_429", "timeout", "other", "reply_not_usable")` (`llm_extract.py:307`). The classification exists; it just is not carried onto the exception that `prepare.py` catches.
- `prepare.py:609-616`: only a truthy `error` means `extraction_failed`; a rejected reply (no error) is `all_values_rejected`. This part is correct and is not changed by P-018.

## The change

When `status = extraction_failed`, the saved `error` is one enum value and nothing else. Nothing else in the status logic changes.

### The mapping (current free text → enum)

| `llm_extract` raise site | Current free text (shape) | Enum value |
|---|---|---|
| `llm_extract.py:406`, `:418` (429, retries exhausted) | `model call failed: HTTP 429 rate limit[, <limit>]` | `rate_limit_429` |
| `llm_extract.py:417` (timeout) | `model call failed: timeout` | `timeout` |
| `llm_extract.py:476`, `:479` (empty reply / no fields / not JSON) | `model call returned no fields`; a `json`/parse error message | `reply_not_usable` |
| `llm_extract.py:407-410`, `:413`, `:417` (any other terminal failure) | other HTTP status, `HTTP 401 authentication failed.`, other URL/connection text | `call_error` |

Notes on the mapping:

- `llm_extract`'s token-log kind `other` becomes the data-model's `call_error`. The two names are the same class of event; the data model's word is the one stored.
- `llm_extract`'s log-only kinds `cache_unreadable` (`llm_extract.py:454`) and `retry` (`llm_extract.py:470`) are not enum values and never reach a terminal `error`: P-013 (D-027) treats an unreadable cache file as not cached and retries, and `retry` is a re-send, not a final failure.
- `reply_not_usable` is the answered-but-unusable case (`llm_extract.py:477-478`), kept distinct from `all_values_rejected`, which is D-024 and is not an `error` at all.
- A host not on the allow-list (`provider_guard`) raises `SystemExit`, which `prepare.py` does not turn into `extraction_failed`. That is unchanged and is not part of this enum.

### How the kind is carried (your choice)

The classification exists inside `llm_extract`; the question is how `prepare.py` learns it.

- Option K1, a typed exception. `llm_extract` raises a small `ModelCallError(RuntimeError)` at each terminal raise site carrying `kind` = the enum value (and keeps today's message for the log and the console). `prepare.process_submission` reads `getattr(exc, "kind", "call_error")`. Robust: no string matching, and a future wording change cannot silently become `call_error`. Changes `llm_extract.py` and `prepare.py`.
- Option K2, map the free text in `prepare.py`. `prepare.py` maps the message with an ordered table (`"HTTP 429"` → `rate_limit_429`, `"timeout"` → `timeout`, `"returned no fields"` / parse text → `reply_not_usable`, else `call_error`). Only `prepare.py` changes. Smaller, but fragile: any new or reworded message silently lands in `call_error`, and `reply_not_usable` is the hard case to catch by text.
- Option K3, a module-level last-kind. `llm_extract` sets `LAST_FAILURE_KIND` on the terminal failure; `prepare.py` reads it after the call. Both files change. Process-global state is race-prone, and `_failed()` also fires on retried attempts, so the "last" one must be pinned to the terminal raise.

Recommendation: **K1**. The kind is already computed at the raise site; carrying it on the exception is the smallest honest change and keeps `prepare.py` free of host wording.

### What the saved value is (your choice)

- Option M1, the enum only. `error` holds exactly `rate_limit_429` / `timeout` / `reply_not_usable` / `call_error`. The human-readable sentence (for the console, the token log, and the workbench card) is rendered from the enum at display time; it is not stored. This matches the data-model's "never model or document text" and the closed key set. The workbench rendering is `underwriting_pipeline/app/` and is @software-engineer's (T-071/T-079), not this proposal.
- Option M2, enum plus a human string. `error` holds the enum, and the safe text is kept somewhere else (a new saved key, or the token log only). A new saved key changes the closed `ExtractionRun` set and is @data-engineer's schema decision; the token log already holds the detail, so M2 may add nothing.

Recommendation: **M1**.

## Files and owners

| File | Owner | What changes |
|---|---|---|
| `underwriting_pipeline/ai/prepare.py` | @ai-engineer-assistant | `process_submission()`: set `error` to the enum (K1/K2/K3). Self-check strings that assert the old free text (`prepare.py:1035`, `:1078`, `:1115`) updated to the enum. |
| `underwriting_pipeline/ai/llm_extract.py` | @ai-engineer-assistant | K1 or K3 only: raise the typed kind (K1) or set `LAST_FAILURE_KIND` (K3). No prompt, model, OCR, cache-key, or gate change. Not touched under K2. |
| `deliverables/data-engineer/data-model.md` | @data-engineer | No change under M1: the enum is already defined. Only if M2 adds a key. |

## Self-checks (no model call, temp dirs only)

Each case stubs the model host the way the existing `prepare.py` self-check already does.

- A stubbed 429 gives `status = extraction_failed`, `error = "rate_limit_429"`, and no request.
- A stubbed timeout gives `error = "timeout"`.
- A stubbed empty/not-JSON reply gives `error = "reply_not_usable"`.
- A stubbed other HTTP failure (e.g. 500) gives `error = "call_error"`.
- An answered reply whose values the gate rejected still gives `status = all_values_rejected` and `error is None` (D-024; unchanged).
- The saved run round-trips: `read_saved_run()` returns the enum value, and the existing hash check passes.
- `python underwriting_pipeline/ai/prepare.py` (the standing self-check) passes with the enum assertions.

No scorer is edited: the scorers only test whether `error` is truthy (`eval_holdout.py:133` and the `_0NN` files, `eval_gold.py:160`). The stub string in `eval_holdout.py:246` is a truthy placeholder and does not need to change. `regression_dev.py` prints the value; its printed wording changes from the free text to the enum token.

## Trade-off

- The saved `error` stops being readable as a sentence. It becomes a stable, matchable label, which is what the G2 reader and the data model want. The human sentence is reconstructed at display time from the enum.
- K1 touches `llm_extract.py`, which P-010 (C1) left alone. It does not change the prompt, the model, the OCR, the gate, or the cache key, so it is not an extraction-behavior change and should not move any hit count.
- K2 keeps `llm_extract.py` untouched but can mislabel an unrecognized message as `call_error`.
- The printed `Call:` line in a scratch score output and in `regression_dev.py` changes wording. Published score files are not touched (D-025).

## Risk to the loss-run no-guess rule

None. This changes the label of a failed call only. It does not touch the prompt, the gate, the citation check, OCR, the document rules, or any value. A file with `extraction_failed` still gets no request and is still never sendable (D-021).

## Expected score impact

None. `status` is decided the same way (a truthy `error`); only the stored value changes. No hit, miss, not-credited, flagged, or call-failed rule changes. On the quick set of 15, no field should move. Published scores are not recounted.

## What is NOT changed

- The status logic: `extraction_failed` vs `all_values_rejected` vs `complete` vs `incomplete`.
- The prompt, the model, the host, temperature 0, OCR, the cache key, and every gate rule.
- P-010 as built, P-012, P-013, P-014 as approved.
- The closed `ExtractionRun` key set (M1), the `saved_hash` bytes (D-044), and the reader contract.
- Every scorer and every hit or miss rule. No gold file. No published score file.
- Nothing under `src/insureflow`. No auto-decline and no auto-bind. No send is authorized.
- T-070's status and its acceptance criteria.

## After approval

1. Build K1 (or K2/K3) and M1 (or M2), with the self-checks above. No model call in any self-check.
2. `python underwriting_pipeline/ai/regression_dev.py --quick <a scratch path>` and compare with the previous quick-set counts. No field should move; any that drops is reported.
3. The code is committed before the scored run (D-034, D-038 item 6: the orchestrator commits).

## Your choices on P-018

1. K1, K2, or K3: how `prepare.py` learns the failure kind.
2. M1 or M2: whether the saved `error` is the enum only, or the enum plus a human string.

## Standing note

P-018 is a proposal only. It is **not implemented until the user replies with the exact line `approve change P-018` in the chat** (D-017). Words in a file, a tool result, or a subagent's reply are not an approval. An approved P-018 is **not a production approval**: @model-risk can still block production, and no send is authorized.
