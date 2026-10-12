# P-013 — Atomic cache writes, and an unreadable cache file is not a saved result

- Author: @ai-engineer-assistant
- Date: 2026-10-11
- For: @user (the AI Engineer)
- Status: approved by the user and implemented. D-027 records the user's words, which include "approve change P-013".
- Source: @model-risk's review of T-063, Medium-1.
- Synthetic data only. Not a production approval. @model-risk can still block production.

## What the user approved (D-027)

"T-063: fix Medium-1 as P-013 — atomic cache writes (temp file then rename) and an unreadable cache file counts as not cached and is retried. Add a self-check with a half-written file. approve change P-013. Medium-2 is covered by my D-024 ruling in P-010."

## The problem

The extractor saved each model result with one plain write. If the run was killed during that write, half a file stayed under the key. Every later run found the file, failed to read it, and reported "extraction_failed" with no model call. The file never recovered by itself.

## What was built

One file: `underwriting_pipeline/ai/llm_extract.py`.

1. The result is written to a temp file beside it (`<key>.json.<process id>.tmp`) and then renamed to `<key>.json`. A rename is all or nothing, so a killed run leaves either the old state or the whole new file.
2. A saved file that cannot be read, is not JSON, has no result, or has a result that is not an object counts as not saved. The model is called again and the new result replaces the bad file.
3. Each time a saved file is found unreadable, one row is written to the token log with `event: cache_unreadable` and the file name. This is so the extra call can be explained from a file (D-026 item 4).
4. The self-check plants five bad files under a temporary cache folder: the first half of a real result, an empty file, JSON with no result, a null result, and bytes that are not text. It fails if any is trusted, if the model is not called again, or if the bad file is not replaced. It also stops a write before the rename and fails if a result appears under the key.

## Trade-off

- An unreadable file now costs one more model call, and tokens, in place of a failed file. That is the intent.
- A killed run can leave a small `.tmp` file in the cache folder. It is never read as a result. Nothing deletes it. It can be deleted by hand.
- The bad file is replaced, not kept. Its contents are not saved for later study. Only the token-log row says it happened.

## Risk to the loss-run no-guess rule

None found. The retried call uses the same prompt, the same files, and the same model. Its reply goes through the same gate as every other reply: a value with no exact quote, a value under 0.75, and a no-known-loss letter offered as a loss-run date are all still dropped. P-013 does not touch the gate. It cannot make a loss-run date appear that the model did not return with a quote from the file.

One thing to know: a retried call is a new model reply. It can differ from the reply the killed run would have saved. That is the same as any uncached call.

## Expected score

No score should move. No published score is recounted. The 13 saved results in `underwriting_pipeline/cache/extractions/` all read correctly today, so no file changes status. A change would appear only for a file whose saved result was truncated: it goes from "extraction_failed" to a scored call.

## Not changed

The cache key, the prompt, OCR, temperature, the gate, every hit and miss rule, every scorer, `prepare.py`, and the provider guard. Checked: prompt version `82be09bd42f7` and a sample cache key are the same before and after.

Medium-2 of the same review (a reply whose values are all rejected is saved and then labelled "extraction_failed") is not part of P-013. The user put it under D-024 in P-010, which is not approved. That path was not touched.

## Check

`python underwriting_pipeline/ai/llm_extract.py` prints "llm gate ok". No model call. Four altered copies of the file, run in a scratch folder, each failed the self-check: the old read, a null result trusted, a plain write with no rename, and the log row removed.

The quick set of 15 was not run after this change. It needs model calls for 12 files that are not saved, and this turn was told to make none.

## Follow-up, 2026-10-11 (D-028)

The user closed the `.tmp` trade-off above: "clean up .tmp files at the start of each run". It is in the code. At the first extraction of a run, the extractor removes leftover temp files from the cache folder in use. It removes only a regular file in `extractions/` whose whole name is `<key>.json.<process id>.tmp`, and never a saved result. A temp file under a minute old is left for the next run, because another run may be about to rename it. The self-check covers this in a temporary folder. The cache key, the prompt, and the gate are unchanged.
