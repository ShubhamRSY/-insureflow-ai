# T-105 demo screens (D-110, criterion 2)

Author: @software-engineer, 2026-10-18. Synthetic data. No code changed (pipeline, workbench.py, What's new all untouched). 0 live model calls. Not a production approval; T-027 veto stands.
Screenshots: `deliverables/software-engineer/screenshots/demo/` (full-page, 1200 px wide). Prefix `T-105-` omitted below.

## Screenshots

| File | What it shows |
|---|---|
| SUB-127-00-queue-all-three | Queue with the 3 demo cards (127, 129, 133) before any action |
| SUB-127-01-card | Senior referral: complete, "words not on the Carrier A allow-list: financial, advisory, tax", suggested Carrier A, "No send: a senior referral needs a senior underwriter to confirm the market first" |
| SUB-127-02-send-refused-before-approve | Banner "Send refused: no logged decision by a listed underwriter for this file" |
| SUB-127-03-nonsenior-confirm-refused | UW-002 tries market confirm: "only a senior underwriter on underwriters.json may confirm a market" |
| SUB-127-04-senior-confirm | UW-001 Dana Reyes confirms carrier_a with reason; confirmation panel (who, when, reason, run hash) |
| SUB-127-05-approve | UW-002 approve recorded; History row; send form with typed-line box appears |
| SUB-127-06-send-sent | Account-manager check passes with no typed override and sends: "Account-manager check passed, sent: package SUB-127.md written to to-carrier. Not bound." (T-107e; the typed send line is no longer needed) |
| SUB-127-07-quote | Quote tracking: carrier_a quoted, premium 5100, deductible 1000, not bound (simulated reply file in the temp copy) |
| SUB-129-01-card | Manual intake (scanned application): red banner with reason, nothing filled in, not scored, send blocked |
| SUB-129-02-approve-refused | "Decision refused: ... status is manual intake (scanned application); an approve is refused for it" |
| SUB-129-03-send-refused | "Send refused: ... cannot be sent, for any actor including the user" |
| SUB-129-04-draft-approve-refused | "Request not approved: ... cannot be approved or sent, for any actor" |
| SUB-133-01-card | Messy file: complete, review pending (loss_run_valued_through read from rotated JPG scan, confidence 0.8, NEEDS REVIEW); route senior_referral R12 habitational, suggested Carrier C |
| SUB-133-02-send-refused-before-approve | "Send refused: no logged decision by a listed underwriter" |
| SUB-133-03-senior-confirm | UW-001 confirms carrier_c with reason |
| SUB-133-04-send-refused-not-approved | Send again after confirm, still no approve: same refusal |
| SUB-133-05-approve-scan-value-ticked | UW-002 approves with the scan value acknowledged; History row "approve; acknowledged 1: loss_run_valued_through" |
| SUB-133-06-send-sent | Account-manager check passes and sends (same banner, SUB-133) |
| SUB-133-07-quote | Quote tracking: carrier_c quoted, premium 11800, deductible 2500, not bound; History shows approve and send |

### T-107e / T-107g refresh (2026-10-19): best case SUB-184 and new replies

Retaken on HEAD 7cfc959 with the B-415 replies (prompt 759b3e6bc9b2). 0 live calls. All T-105 shots above were retaken; SUB-127, 129, 133 now run on the new-prompt replies. SUB-184's reply is on the old prompt; drive.py re-keys it inside the temp cache only.

| File | What it shows |
|---|---|
| T-107e-SUB-184-00-queue | Queue with SUB-184 (best case, Keller Insurance Services PA) |
| T-107e-SUB-184-01-card-carrier-a | Complete - review pending (loss_run_valued_through), carrier_a R14, recommendation only |
| T-107e-SUB-184-02-approve | UW-002 approve with the review value acknowledged |
| T-107e-SUB-184-03-account-manager-send | Account-manager check passes, package written. Not bound |
| T-107e-SUB-184-04-quote | Quote tracking: carrier_a quoted 3900 / 1000, not bound (simulated reply file) |

The account-manager step is now shown: it is the send (the banner on the SUB-127, 133, 184 "send" shots). The SUB-127 P-052 senior confirm passes the account-manager check with no override. Run: `sh deliverables/software-engineer/T-105-demo/run-demo.sh <new empty folder>`, then `python3 .../snap.py <screens folder> <folder>/shots` (system python has Playwright).

## Commands

`T` = /private/tmp/claude-501/-Users-disastershubz-INSURANCE-FLOW-AI--insureflow-ai-1/e534a9ad-9fe5-479b-bc47-febd17ffda6a/scratchpad/t105 ; `W` = the ai-team worktree. Copies of inbox SUB-127..153 and of the saved-reply cache are in `$T/inbox` and `$T/cache` (made by @senior-underwriter, criterion 1). Driver scripts are outside the repo: `$T/drive.py`, `$T/flow_head.py`, `$T/shotflow.py`, `$T/snap.py`.

```
export LLM_CACHE_DIR=$T/cache LLM_PACE_SECONDS=0     # LLM_BASE_URL / LLM_MODEL from the shell, so cache keys match
cd $T; rm -rf box tc tp fc pend shots; mkdir shots
$W/.venv/bin/python drive.py $T          # saved runs from saved replies; live post replaced by a raiser; "blocked live-call attempts: 0"
$W/.venv/bin/python shotflow.py $T       # points every path at $T, workbench.sandbox($T/box); drives w.act() for /send, /confirm-market, /decision, /approve-draft; renders w.render() to $T/shots/*.html after each step; quotes.track() after a simulated reply file in $T/box/from-carrier
python3 snap.py $W/deliverables/software-engineer/screenshots/demo   # system python Playwright, channel="chrome" (bundled Chromium is not installed); file:// pages, full_page
```
The screenshots are of the page the workbench renders after each action (same render() the server uses), not of a live browser click-through; the account-manager gate is called as package.send_to_carrier("account-manager").

D-069 checks, before and after: workbench.html md5 a7edde5a... unchanged; token log 31 lines unchanged; `git status` shows only the pre-existing team/ edits, the senior-underwriter file and the new screenshots folder; to-carrier / to-producer / pending-approval untouched.

## Problems seen (reported, not fixed)

1. The "What's new" panel is open and about 60 lines long at the top of every page; the card starts far below. A manager opens the page and sees a wall of dev notes first (all screenshots, e.g. SUB-129-01-card). Medium for a demo; suggest collapsed by default.
2. "Not read by extraction: loss-runs.pdf" (SUB-127) and "loss-runs.jpg" (SUB-133) while the card shows loss_run_valued_through read from that same file, and "Loss history: not scored". Contradictory to a lay reader (SUB-127-04-senior-confirm, SUB-133-07-quote).
3. The senior-confirm banner is printed twice on the card: the action message and the stored confirmation panel (SUB-127-04-senior-confirm, SUB-133-03-senior-confirm).
4. (T-107e: the gate now passes for a confirmed senior referral and its result is shown.) The account-manager send gate has no screen of its own. Its refusal "the file is not in appetite" appears only from code, and it is wrong in meaning for a senior referral (in appetite, needs a person). Not shown in any screenshot; the card instead says "No send: a senior referral needs a senior underwriter to confirm the market first".
5. Refusal order is inconsistent: send before approve says "no logged decision by a listed underwriter", while the card's send panel says a senior confirm comes first (SUB-133-02-send-refused-before-approve, SUB-127-02-send-refused-before-approve). SUB-133-04 repeats the same text after the confirm.
6. After approve and send, the card keeps a "Needs-review values: acknowledge each before approve" tick box and the Record decision form (SUB-133-07-quote), and after approve the card does not state the next step (type the send line). Medium.
7. The quote step is simulated: no screen to receive a carrier reply; the demo needs a reply file placed in from-carrier of the temp copy (SUB-127-07-quote, SUB-133-07-quote). Premium and deductible are fictional.
8. Counter line "Decisions so far: N approved" is page-wide and carries across files in one run (differs between SUB-127-04 and SUB-133-07); can confuse if a manager asks "approved what?". Low.
9. Page height: cards are 3,700 to 4,900 px tall; a projected demo needs scrolling to the History and Send areas. Low.
