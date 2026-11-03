# @model-risk look-again — T-129 (P-079, P-080, P-081; D-155–D-157, D-159)

- Date: 2026-11-03. Reviewer: @model-risk (independent). The one look-again allowed (D-129/D-159) on the REJECT in `check-T-129.md`.
- Commit c45df9e8 (branch pilot-integration); fixes = diff 8e2e281f..c45df9e8 (scope.py `_bare_label`, package.py `needs_review_ids`, workbench.py `saved_report`, plus self-checks).
- No model call, no hold-out. All runs on a temp copy (`git archive c45df9e8`) in the scratchpad (D-069). The real worktree was still clean afterwards.
- **This is not a production approval. The T-027 veto stands.**

## Verdict: APPROVE WITH CHANGES. H1, H2 and H3 are closed, and the fixes add no new High. The changes asked for are the Medium/Low items below, which go to the backlog and do not block.

## What I re-ran
- Self-checks on the temp copy: `scope ok scope-v6`, `package ok`, `prepare ok`, `workbench ok`.
- My own probe, independent of the author's self-checks. It used a real temp decisions log and real saved runs on disk, written through `prepare.hash_payload` and read back through `read_saved_run`. Three runs, each with operations empty and one operations conflict resolved on this run hash by a listed UW: `extra: []`, `extra: ["hours"]`, and no `extra` (a run saved before P-081).
- Dev re-check `devcheck-after-fixes.txt` is byte-identical to `devcheck-after-scope-v6.txt`. DEV-01..05 stay in scope; DEV-06..12 go to manual intake.
- Quick-17 baseline vs after-fixes: `counted` is equal. The only per-row difference is SUB-036 retry metadata (the baseline had a live retry; the after-fixes run read from cache).
- Screenshot `demo/T-105-SUB-133-06-approve-scan-value-ticked.png` (from a sandbox copy): the approve lists operations and loss_run_valued_through, and the history shows "approve; acknowledged 2: operations, loss_run_valued_through". The account-manager check passes only after that.

## High findings: status
**H1 — closed.** `needs_review_ids` now reads `with_resolutions(report)`. The workbench approve list and the send-gate `ack_problem` therefore use the same list, and that list includes the operations value entered at the resolve (C1).
- Probe on all three runs, after the resolve:
  - with no approve logged, `ack_problem` = "1 value needs review and is not acknowledged (operations)";
  - with an approve that acknowledged `[]`, it still refuses;
  - with an approve that acknowledged `["operations"]` on this run hash, it returns `''` (pass).
- The author's self-check covers an acknowledgment of the wrong field and an acknowledgment on another run hash; both are refused.
- The resolved run resolves to the saved run's `submission` key. prepare writes that key as the folder name, so the lookup matches.
- Applying `with_resolutions` twice gives the same result.
- The change only adds rows to the acknowledgment list, so it is stricter, never looser.

**H2 — closed.** `saved_report` passes the saved `extra` through, and `None` when the run has none. Probe results:

| Saved run | Card | Send gate | Producer draft |
|---|---|---|---|
| `extra: []` | complete — review pending | complete — review pending (`ready_to_route` True) | withdrawn |
| `extra: ["hours"]` | incomplete, Missing "hours" | incomplete | not withdrawn |
| no `extra` (saved before P-081) | incomplete | incomplete | not withdrawn |

- The draft withdrawal in `act()` and the "Withdrawn" text both key on `status_reason == RESOLVED_REASON`, so they follow the same state as the card.

**H3 — closed for the shape I raised.** `_bare_label` now accepts only two kinds of line as a label: a line ending in ":", or a name-only line (no colon, no sentence punctuation, every word capitalised or a joiner such as "of" or "&").
- Probe: `"Carrier A loss run attached.\nWe also keep stock at 2215 Leonard Rd, Bryan."` → caught (`2215 Leonard Rd`). In my first check it was missed.
- "Mailing address:" and "ABC Insurance Agency" are still labels.
- D-155 (c) holds on the dev set, and the self-check now includes four two-line SUB-533 shapes.
- Compared with the first build, the new `_bare_label` hides fewer lines, so it is stricter only (D-156).

## Medium / Low (backlog, one line each)
- M4 (new, residual of H3): a Title Case line with no punctuation and a role word still counts as a label and hides the next line. Two examples: "Carrier A Loss Run Attached" above an address sentence, and an agency name above "We also keep stock at …". My suggested remedy asked for "no verb"; the fix does not check that, and the label hides the whole next line even when that line is a sentence. Either limit the skip to a next line that is only an address, or state it as a known residual in the as-built.
- M1 (open): a role word in the same sentence, or the word "home", still hides a second address; state it as a known residual.
- M2 (open): memo H1 near-pass negatives are still missing from the dev set: a mailing-only or PO Box count of 1, and a null count.
- M3: closed (dev replies saved in `evals/T-129/devcheck-replies/`).
- L3 (new): a run saved before P-081 with every conflict resolved shows "Missing: none" with status incomplete and no reason. It fails closed, but the card should say a re-run is needed.
- L4 (new): the approve log's `approved_values` is `field_values(saved)` (the raw saved run), so the operations value entered at the resolve is not in the approve record; it is only in the resolve row.
- L1, L2 (open, unchanged): "Spur" and lowercase "highway" are not recognised as highway addresses; a count quote that names a second place without a street number still passes `_shows_one_address`.

## Decision
APPROVE WITH CHANGES for T-129 (the code and evidence, as a demo build). On the evidence: D-155 (a)–(f) hold, D-156 holds and is stricter only, D-157 holds, and the D-159 fixes H1–H3 are closed, each with a test. The Medium/Low items go to the backlog.

This is not a production approval. The T-027 veto stands, and an approved P-079/P-080/P-081 does not put anything into production. Merging is @user's decision.

Note: the dispatch said to edit nothing except this report, so the verdict is not appended to `team/DISCUSSION.md`. The orchestrator should append it as TYPE: REVIEW.
