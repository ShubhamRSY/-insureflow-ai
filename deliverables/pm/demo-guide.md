# Manager demo guide: AI underwriting assistant (T-105, D-110)

Audience: a non-technical manager. Length: about 10 minutes. Author: @pm, 2026-10-18.
Synthetic data only. Not a production approval. The T-027 model-risk veto still stands (it says the tool is not yet cleared for real use).

## Words used in this guide

- **Submission (SUB-###)**: one insurance application file from a producer (a broker), with its attachments.
- **Inbox**: the folder where new submissions land.
- **Scope (P-055)**: the pilot covers small commercial policies in Texas, typed or text-readable files, one location. Anything else goes to a person.
- **Manual intake**: a person reads the whole file. The tool fills in nothing and sends nothing.
- **Senior referral**: the tool suggests a carrier, but a senior underwriter must confirm it (P-052).
- **Carrier A / B / C**: placeholder names for insurers. Real names come later.
- **Route**: where the file goes next (a carrier, a senior, or nowhere).
- **Hold-out**: a set of test files kept unseen while the tool was built, used once for an honest score.
- **Gate**: a pass/fail test a change must meet before it is trusted.
- **Quote**: the carrier's price reply. In this demo every quote reply is simulated and every figure is fictional.

## Before you start (5 minutes, the presenter only)

Run the demo on a temporary copy, never on the real workbench or the real logs. One command does the whole setup (copies the dev inbox and the saved model replies into the temp folder, replays the steps, writes the pages):

```
cd "/Users/disastershubz/INSURANCE FLOW AI/insureflow-ai-team"
deliverables/software-engineer/T-105-demo/run-demo.sh /tmp/t105-demo-$(date +%s)
```

- The shell must have `LLM_BASE_URL` and `LLM_MODEL` set to the Groq host and `qwen/qwen3.8-27b`, so the saved replies match. No live model call is made; the scripts block them. Expected output ends with `SUB-133 [('carrier_c', 'quoted', 11800, 2500, False)]`.
- The scripts and saved replies are in `deliverables/software-engineer/T-105-demo/`. They are demo tooling only, not pipeline code.
- The steps are a replay of recorded actions, not a live click-through. Show the rendered pages from the temp folder's `shots/`, or the committed screenshots below (safest for the meeting).
- The demo files are dev data (SUB-127 to SUB-153). None comes from the hold-out.

Screenshots for each step are in `deliverables/software-engineer/screenshots/demo/` (file names start with `T-105-`). The queue screenshot `T-105-SUB-127-00-queue-all-three.png` shows all three demo cards before any action.

## The 10-minute script

| Time | Section | What you show | Screenshot |
|---|---|---|---|
| 0:00–1:00 | Opening | The tool reads a submission and prepares it for a person. It never decides, never binds, never sends by itself. | `T-105-SUB-127-00-queue-all-three.png` |
| 1:00–4:30 | **Demo A: messy in-scope file to a carrier quote** (SUB-133) | Inbox to quote, with one value a person must check | see A1–A6 |
| 4:30–6:00 | **Demo B: out-of-scope file to manual intake** (SUB-129) | The tool stops and says why | see B1–B3 |
| 6:00–8:00 | **Demo C: senior referral confirmed by a senior** (SUB-127) | A senior confirms the carrier, then the file moves on | see C1–C6 |
| 8:00–9:30 | Numbers: T-104 scores, cost, time saved | Honest scores; estimates clearly marked | none (table below) |
| 9:30–10:00 | Gaps and next steps | Two open gaps, what production still needs | none |

### Demo A: SUB-133, messy in-scope file to a quote (3.5 min)

What it is: a 12-unit apartment building. The file has a typed application, a schedule, an email, and a rotated photo of a Carrier C loss run (a loss run is the insurer's list of past claims).

Important, say it out loud: on the frozen code no dev file goes straight to Carrier A. This file reaches a quote only through senior referral. The suggested carrier is Carrier C, and a senior confirms it. The tool does not show a direct route.

1. **A1 (0:30)** Open the card. Status is "complete, review pending". The loss-run date was read from a scan, so a person must check it. Route: senior referral, suggested Carrier C. [`T-105-SUB-133-01-card.png`]
2. **A2 (0:20)** Try to send before anyone approves. The tool refuses: "no logged decision by a listed underwriter". This is the safety stop working. [`T-105-SUB-133-02-send-refused-before-approve.png`]
3. **A3 (0:40)** The senior, Dana Reyes, confirms Carrier C and gives a reason. The record shows who, when, why, and which file version. [`T-105-SUB-133-03-senior-confirm.png`]
4. **A4 (0:40)** The underwriter approves and ticks the scan value as checked. The history shows it. [`T-105-SUB-133-05-approve-scan-value-ticked.png`]
5. **A5 (0:30)** Send. Be clear about who sends: the account manager's automatic check says "not in appetite" for this file (a wording problem, see the box below). The send went through a typed line from the user, which is an override. The package is written to the to-carrier folder and is "not bound". [`T-105-SUB-133-06-send-sent.png`]
6. **A6 (0:30)** Quote back: Carrier C, quoted, premium 11,800, deductible 2,500, not bound. The reply is simulated and the figures are fictional. [`T-105-SUB-133-07-quote.png`]

### Demo B: SUB-129, out-of-scope file to manual intake (1.5 min)

What it is: an electrical-supply wholesaler whose application is a scanned photo. Scope rule P-055 says a person reads the whole file.

1. **B1 (0:40)** The red banner gives the reason in plain words: "Manual intake - a person reads this whole file. Why: Manual intake: scanned application" Nothing is filled in, nothing is scored, no carrier is shown, and no missing-information request is drafted. [`T-105-SUB-129-01-card.png`]
2. **B2 (0:30)** Try to approve. Refused: the file is manual intake, so it cannot be approved. [`T-105-SUB-129-02-approve-refused.png`]
3. **B3 (0:20)** Try to send. Refused for every user, including the user. [`T-105-SUB-129-03-send-refused.png`]

### Demo C: SUB-127, senior referral confirmed by a senior (2 min)

What it is: a financial-advisory firm in Dallas. The file is complete and clean. The words "financial, advisory, tax" are not on the Carrier A office list yet, so the tool does not guess a market. A senior decides.

1. **C1 (0:30)** Route: senior referral, suggested Carrier A, "underwriter confirms". [`T-105-SUB-127-01-card.png`]
2. **C2 (0:20)** A non-senior tries to confirm the market. Refused: only a senior may confirm. [`T-105-SUB-127-03-nonsenior-confirm-refused.png`]
3. **C3 (0:30)** The senior confirms Carrier A with the reason "financial advisory is an office occupancy". [`T-105-SUB-127-04-senior-confirm.png`]
4. **C4 (0:20)** Approve, then send by the user's typed line, as in Demo A. [`T-105-SUB-127-05-approve.png`, `T-105-SUB-127-06-send-sent.png`]
5. **C5 (0:20)** Quote: Carrier A, premium 5,100, deductible 1,000, not bound. Simulated. [`T-105-SUB-127-07-quote.png`]

## The numbers (T-104 hold-out, run 2026-10-17, as published)

Hold-out: 32 files (SUB-174 to SUB-205), never seen before the run. 20 were in scope and 12 out of scope. Scored once, with no code change after the run. Source: `deliverables/ai-engineer/evals/SUB-174-205-holdout-v6.md` and the run record. Model-risk verdict: `deliverables/model-risk/T-027-gate-memo-T-104.md`.

| Check | Result | Target | Met? |
|---|---|---|---|
| Out-of-scope files that leaked past the scope rule | 0 of 12 | 0 | Yes |
| Out-of-scope files caught by the scope rule | 12 of 12 | 100% | Yes |
| In-scope files wrongly sent to manual intake | 0 of 20 | at most 2 | Yes |
| Scope gate (P-055) | PASS | | Yes |
| False completes (marked complete when not) | 0 | 0 | Yes |
| Unsafe routes (a carrier shown where a senior or no-match was right) | 0 | 0 | Yes |
| Route accuracy | 16 of 20 | at least 18 | **No** (T-027 route gate: FAIL) |
| Operations field | 12 of 20 | at least 9 in 10 | **No** (B-406) |
| Loss runs field | 9 of 20 | at least 9 in 10 | **No** (B-408) |
| Other fields (named insured, premises, dates, TIV, construction, year built) | 20 of 20 each | at least 9 in 10 | Yes |
| Sales field | 19 of 20 | at least 9 in 10 | Yes |
| Silent errors (wrong and not flagged), all fields | 3 of 180 (1.7%), all operations | | Not met for operations |
| Values read automatically without a person | 147 of 180 (82%) | | |

- Model-risk verdict (T-027): **KEEP**. The veto is not lifted. The safety checks held. The accuracy checks did not.
- Retries: 5 rate-limit retries, all logged. Failed calls: 0.

### Cost per file (run record, 2026-10-17)

- Tokens measured: 35,455 tokens for 20 model calls, about 1,773 per called file. Averaged over all 32 files, about 1,108 per file. The 12 out-of-scope files used no model call.
- **Actual cost today: $0.** The model ran on the Groq free tier (D-011).
- **Paid-host estimate (estimate, not measured):** the repo's only public price list is for Gemini, not the model we run, and I did not look up the model's own price.
  - At Gemini 2.5 Flash list prices ($0.30 per million input tokens, $2.50 per million output): about $0.002 per called file, about $0.0012 per file averaged over 32.
  - At Gemini 2.5 Pro list prices ($1.25 / $10.00): about $0.008 per called file, about $0.005 averaged.
- Assumptions: one model call per file (no retries); retries carry no tokens in the log and are not counted; the demo files cost $0 because their results were saved.

### Time saved per submission (estimate, not measured)

Nothing here was timed in a real office. These are my assumptions. @senior-underwriter should check them before the manager sees a number.

- Assumed manual time for a complete in-scope file: about 45 minutes (read the application, schedule, loss runs and email; type the values; check them; prepare the carrier package).
- Assumed time a person still spends with the tool: about 10 minutes for a clean file, about 20 for a messy one. This covers checking flagged values (the tool reads 82% of values without a person; operations and loss-run dates are the weak spots), confirming a senior referral, approving, and sending.
- Estimated saving: about 25 to 35 minutes per in-scope file.
- Out-of-scope files save roughly nothing: a person still reads them.
- Across a mix like the hold-out (20 of 32 in scope), that is about 15 to 22 minutes per submission on average. Treat it as an upper bound until a real timed pilot runs.

## Known rough edges on screen

Tell the manager about these before the demo, so the screen does not surprise anyone.

- **"What's new" panel:** open at the top of every page, about 45 entries of developer notes. Collapse it before presenting if the page allows it. If it does not, scroll past it. A fix to collapse it by default is in the backlog.
- **Account-manager send check:** it says "the file is not in appetite" for senior referrals. That is wrong: senior referrals are in appetite and need a senior. There is no screen for this check.
- **Send wording:** the send refusal before approval says "no logged decision by a listed underwriter". The card's own text says a senior must confirm the market first. Both are true, but the order is not clear.
- **"Not read by extraction" line:** on SUB-127 and SUB-133 it says a loss-run file was not read, while the same card shows a date read from that file. The date is from the scan, so the line is a wording bug.
- **Senior confirmation banner:** printed twice on the card.
- **After approval:** the card still shows the approve form and does not say the next step (typing the send line).
- **Counter "Decisions so far":** counts across the whole page, not per file. Do not read it aloud.
- **Card height:** each card is 3,700 to 4,900 pixels tall. Scroll to the history and send areas.
- **Send by typed line:** Demos A and C show the user's typed line sending the file, after the account-manager check refused. Say so out loud. It is the user's override, not an account-manager approval.

## Where to go next

- Read `deliverables/pm/where-we-are.md` (one page) if the manager asks what is left.
- Rehearsal of this guide is a separate T-105 step (@senior-test-engineer). Anything that breaks in it goes to the backlog, not into a fix before the demo.
