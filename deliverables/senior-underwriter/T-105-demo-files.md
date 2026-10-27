# T-105 demo files (D-110, criterion 1)

Author: @senior-underwriter, 2026-10-18. Synthetic data only. Not a production approval; T-027 veto stands.
Code: worktree `insureflow-ai-team`, branch `ai-team`, HEAD 069691c; `git diff 6e7cfa2 HEAD -- underwriting_pipeline` is empty (frozen code 6e7cfa2). No code changed.

## Result in one view

| Step | File | Result |
|---|---|---|
| (a) messy in-scope file to a quote | **SUB-133** (backup: SUB-131) | Clean, with a gap: it reaches a quote only through senior referral, not Carrier A direct and not through the account-manager gate. See "Problem 1". |
| (b) out-of-scope to manual intake | **SUB-129** | Clean |
| (c) senior referral confirmed by a senior (P-052) | **SUB-127** | Clean |

All three are dev data (SUB-127 to SUB-153, the D-097 to D-100 dev set). Hold-outs avoided: SUB-017 to 126, 154 to 173 and 174 to 205 (T-104). SUB-001 to 016 have no saved replies, so they were not used.
0 live model calls: 27 files read, 21 served from saved replies (token log: 21 `cache_hit`, 0 calls, 0 tokens), 6 manual-intake files need no call. A blocking stub on the model post was in place; 0 attempts.

## Problem 1 (affects the guide): no dev file reaches Carrier A direct

On frozen code no file in the dev set with saved replies routes to `carrier_a`. P-051/P-053/P-054 tightened the Carrier A allow-list after the dev files were written. The old direct files are now: SUB-127, 128, 135 senior referral (words off the allow-list, or loss run missing), SUB-129 manual intake (scanned application). Every complete in-scope file is `senior_referral`.
Consequences:
- The account-manager send gate refuses every one of them: "the file is not in appetite" (checked live on SUB-127 and SUB-133). The only send path is a senior market confirm, an approve, then the user's typed line.
- (a) and (c) therefore use the same mechanism. The guide should say so: "Carrier A direct" is not shown, because the written rules now send almost everything to a person.
- Wording: "not in appetite" is misleading for a senior referral, which is in appetite and needs a senior. Backlog item for @software-engineer (reason text only, no logic).
- Alternative if the user wants a direct route: a new in-scope file with only office/retail words (T-104 has SUB-179 and SUB-184, but they are hold-out and must not be used).

## (a) SUB-133 — messy in-scope file to a quote

Why: Canyon Oaks Apartments LP, 12-unit apartment building. Typed application and schedule, an email, and a rotated JPG scan of a Carrier C loss run. The scan is read at lower confidence, so the value is flagged for a person. This shows "messy input, human checks the one doubtful value, quote comes back".
What the manager sees:
- Saved run: status `complete — review pending`. Hash and manifest checks ok.
- Review note on loss_run_valued_through (2026-09-30): "number or date read from a scan; loss run from scan/spreadsheet: check it (loss-runs.jpg)". Must be ticked at approve.
- Route: `senior_referral`, rule R12 (AG:37, AG:62), "habitational; suggested market: Carrier C, underwriter confirms".
- Send before any approve: "Send refused: no logged decision by a listed underwriter for this file".
- UW-001 (senior) confirms carrier_c with a reason. UW-002 approves with the scan value ticked. Account-manager send: "the file is not in appetite" (see Problem 1). The user types `send to carrier SUB-133`: "Sent: package SUB-133.md written to to-carrier. Not bound."
- Quote tracking: carrier_c, quoted, premium 11800, deductible 2500, not bound. The quote file is a simulated reply I wrote in the temp copy only (FICTIONAL planning figures); in a real demo @carrier-underwriter's reply must be placed in `simulation/from-carrier/` of the temp copy.
Backup (more messy, rougher card): **SUB-131** Ruiz & Pope Plumbing. Scanned Carrier B loss run, square footage 2,100 (application) against 2,800 (schedule), casual email. Hold, open conflict. UW-002 resolves the conflict (logged), route becomes `senior_referral` R7 "class matches more than one carrier: office, contractor", no suggested market; UW-001 confirms carrier_b; send; quote 7300. Issues on its card: the Conflicts panel prints the raw data (`[{"value": "2100", "source": ...}]`) with "RESOLVED by UW-002: 2100"; the producer missing-info draft for the conflict is still shown and still offers "Approve and send to producer" after the conflict is resolved; R7 fires because "Office and shop on premises" counts as a second class (safe direction, but a plumber's office is not a second operation). Use only if the manager wants to see a conflict resolved.

## (b) SUB-129 — out-of-scope file to manual intake

Why: Brazos Electrical Supply Inc., a light-wholesale file that the older dev gold called Carrier A. Its application is a scanned JPG, so the P-055 scope gate sends the whole file to a person. Shows the safe stop: no guessing, no draft, no send.
What the manager sees:
- Status `manual_intake`; route `manual_intake`; rule: scope check scope-v3.
- Reason in plain words: "Manual intake: scanned application — a person reads this whole file."
- "No field is filled in, no carrier route is shown, no missing-info draft is made, and the send is refused."
- Score line "Not scored — manual intake (outside the pilot scope, P-055)". Fields table: "Nothing filled in: a person reads the file."
- Approve: "Decision refused: this file's status is manual intake (scanned application); an approve is refused for it". Send: "Send refused: ... it cannot be sent, for any actor including the user". Approve-draft: "Request not approved: ... cannot be approved or sent, for any actor".
- Other manual-intake dev files if a second is wanted: SUB-142 (email only, application not identified), SUB-143 (Spanish), SUB-140 and 145 (multiple locations), SUB-144 (scanned and multiple locations).

## (c) SUB-127 — senior referral confirmed by a senior (P-052)

Why: Cedar Bend Financial Advisors LLC, Dallas. Complete, clean, typed application, text-layer PDF Carrier A loss run valued 2026-09-30, no review values. The system does not guess a market for the words "financial advisory tax"; a senior decides. This is the human-judgment story.
What the manager sees:
- Status `complete`; route `senior_referral`, "words not on the Carrier A allow-list: financial, advisory, tax (P-053; AG:29-30); suggested market: Carrier A, underwriter confirms".
- UW-002 (not senior) tries to confirm: "Market confirm refused: only a senior underwriter on underwriters.json may confirm a market".
- UW-001 Dana Reyes (senior) confirms carrier_a, reason "financial advisory is an office occupancy; Carrier A office appetite". The card shows who, when, the reason and the run hash.
- Send before approve refused ("no logged decision by a listed underwriter"). UW-002 approves. Account-manager send: "the file is not in appetite". User send with the typed line: "Sent: package SUB-127.md ... Not bound."
- Quote tracking: carrier_a, quoted, premium 5100, deductible 1000, not bound (simulated reply in the temp copy, as above).
Alternative of the same kind: SUB-147 (CPA office, Austin; Carrier A suggested, complete) and SUB-149 (apartments, Carrier C).

## Commands run

All paths under `/private/tmp/claude-501/-Users-disastershubz-INSURANCE-FLOW-AI--insureflow-ai-1/e534a9ad-9fe5-479b-bc47-febd17ffda6a/scratchpad/t105` (called `$T`). `$W` is the worktree. The two driver scripts are outside the repo (`$T/drive.py`, `$T/flow.py`, steps in `$T/steps.py`).

Setup (copies only): `$T/inbox` = copies of `simulation/inbox/SUB-127` to `SUB-153`. `$T/cache/extractions` = copies of saved replies (the repo's `underwriting_pipeline/cache/extractions`, plus copies of dev-session cache folders found in earlier scratchpads). The repo cache and `T-104-live` were not written.

```
export LLM_CACHE_DIR=$T/cache LLM_PACE_SECONDS=0     # LLM_BASE_URL / LLM_MODEL as in the shell (Groq host, qwen/qwen3.8-27b), so cache keys match
cd $T
# 1. Extraction from saved replies. drive.py replaces llm_extract._post with a function that raises, and calls
#    prepare.write_drafts($T/inbox, $T/out/pending, $T/out/conflicts), so saved runs go to $T/out/extractions
$W/.venv/bin/python drive.py $T
# 2. Workbench actions in a sandbox copy. flow.py points every path at $T first, then calls workbench.sandbox($T/box)
#    (page, logs, outboxes, from-carrier all inside $T/box), then drives workbench.act() for
#    /decision, /confirm-market, /send, /approve-draft; package.send_to_carrier("account-manager") for the AM gate;
#    quotes.track() after a simulated reply file is written in $T/box/from-carrier
rm -rf $T/box
$W/.venv/bin/python flow.py $T
```
Sequence per file is in `$T/steps.py` and in the "What the manager sees" lists above. Output kept in `$T/flow.out`.

## Checks that nothing real changed (D-069)

- `git status --short` in the worktree before and after: identical (only `team/DECISIONS.md` and `team/TASKS.md` were modified at the start, by earlier turns).
- `underwriting_pipeline/app/workbench.html`: md5 identical before and after. Real token log: line count identical. `simulation/to-carrier`, `to-producer`, `pending-approval`: no change in `git status`.
- Token log of the run (`$T/cache/token_log.jsonl`): 21 `cache_hit`, 0 model calls, 0 tokens. Blocked-post counter: 0.

## Other things the manager might hit (UI, my view as a senior underwriter)

- After "approve", the card still shows both the approve form and the send form without telling a non-technical viewer the order (confirm market, approve, type the line). The refusal texts are clear; a one-line "next step" on the card would help. Medium, backlog.
- The conflict panel prints raw data (SUB-131 only). Medium, backlog.
- "Score: 25 · not a price" on SUB-133 with codes HABITATIONAL and TIV_OVER_1M: fine, but say in the guide that the score is not a price or a decision.

## Status of criterion 1

Met with one honest gap: (a) cannot be Carrier A direct or account-manager gated on dev data (Problem 1). All three files run cleanly, 0 live calls, nothing real written. The screenshots, guide and rehearsal (other criteria) are not mine.
