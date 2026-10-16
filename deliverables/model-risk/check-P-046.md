# @model-risk check — P-046 (D-093): each loss-run document judged separately

- Date: 2026-10-15. Reviewer: @model-risk. Deliverable: commit 57d56b9 (prepare.py `LOSS_RUN_NAME`, `_run_doc_reason`, `gate_loss_run`, self-checks; workbench.py What's new; dev SUB-153 and its gold; dev-SUB-147-153-D-093.md).
- Evidence read: D-093; `git show 57d56b9`; prepare.py lines 440–607 (carrier layouts, `carrier_run_check`, `loss_run_kind`, `gate_loss_run`); SUB-153 inbox and gold; dev check report. SUB-127–146 and their gold were not opened, listed or run.
- Self-checks: `prepare.py` with LLM_API_KEY, LLM_BASE_URL, LLM_MODEL unset: "prepare ok". No model call.
- Probes: in memory, calling `gate_loss_run` on the real SUB-153 texts and variants (scratchpad `mr-p046/probe.py`). Nothing in the repo was written apart from this file, DISCUSSION.md and STANDUP.md.
- Cached dev re-run: not repeated (the runner for the D-093 dev check is not in the repo). The P-046 gate is deterministic, and probe P0 on the real SUB-153 documents gives the committed result.

## Verdict: REJECT as frozen hold-out code (2 High open)

What works: SUB-153 (A dated, B undated) gives "complete — review pending" with the B reason (P0). Renaming B to carrier-b.md is still caught by its header (P1). The self-check cases pass: undated, COPY, unrecognised `loss-runs-x.md`, csv. A letter beside A stays plain complete (P-040). A alone is plain complete. The What's new line is present.

| Probe (A = accepted Carrier A run, value 2026-09-30) | Result | Expected (D-093) |
|---|---|---|
| P0 SUB-153 A + B undated | review pending, B reason | review pending |
| P1 B undated named carrier-b.md | review pending | review pending |
| **P2** B undated + line "Signed: J. Ortiz, underwriting" | **plain complete** | review pending |
| **P3** B undated + line "Copy provided by agent" | **plain complete** | review pending |
| **P4** B undated, insured "Owner Holdings LLC" | **plain complete** | review pending |
| **P5** unrecognised dated run (Harbor Point Mutual, all loss-run parts) as attachment.md | **plain complete** | review pending |
| **P6** same as resubmission.md | **plain complete** | review pending |
| **P7** scan.jpg (in scans), OCR'd loss run with garbled header | **plain complete** | review pending |
| P8 scan.jpg with clean Carrier B header | review pending (scan reason) | review pending |
| **P9** Carrier B run pasted in email.md | **plain complete** | review pending |
| P10 loss-control-report.md (not a loss run) | review pending | plain (false alarm) |
| P11 A + no-known-loss letter | plain complete | plain complete |

### H1 (High): an undated or copy carrier run is excused as a "letter" when it contains one letter-like word
- Where: `_run_doc_reason` checks `kind == "letter"` before it looks at the carrier state. `loss_run_kind` calls an undated carrier run a letter when it has a no-claims line ("Carrier B certifies no claims…") plus any LETTERISH word ("signed", "agent", "owner", "states", "declared"…), because an undated run never shows all RUN_PARTS (it has no valued line).
- Effect: P2–P4 give plain "complete" with an accepted A run beside them. This is the exact case D-093 names (undated, copy/sample) and it can be routed and sent with no flag.
- Resolution: a document with a carrier header (`check[0]` not None) is a loss-run document whatever `loss_run_kind` says. Only a document with no carrier header may be excused as a letter. Add P2–P4 as self-checks asserting review pending with the B reason.

### H2 (High): an unrecognised or scanned loss run counts only if its file name contains "loss/claim"
- Where: `_run_doc_reason` returns None for any document with no carrier header whose name does not match `LOSS_RUN_NAME`. The D-093 record also reads "loss-run document" as a document that "shows all loss-run parts". The code leaves that part out.
- Evidence that this matters: in the development inbox (not the hold-out), loss runs come in files named `scan.jpg` (14), `scan.png` (6), `scan.pdf` (2), `attachment.md` (3) and `resubmission.md` (3); their gold records a loss run. A second run in any of these beside an accepted A run gives plain complete (P5–P7, P9). D-093 names "scan" and "unrecognised" explicitly.
- Resolution: (a) treat a typed document that shows all RUN_PARTS (folded text) as a loss-run document; (b) treat a scan or spreadsheet that shows any loss-run part (or that the model cited for loss-run facts) as one, giving the scan reason. Add P5–P7 as self-checks asserting review pending, and keep P11, P12 and SUB-153 as they are. The fix may pull a scanned or emailed application into review pending; that is the safe direction.

Both are extraction-code changes. They need a new P-### and the user's `approve change P-###`. Because 57d56b9 is meant to be the frozen hold-out code (D-093), SUB-127–146 should not run on it until H1 and H2 are closed. Closed when the probes above are self-checks that pass and the dev SUB-147–153 re-run still has 0 false completes.

### Medium / Low (backlog, one line each)
- M1: the self-checks cover only clean variants. No case has a letter-like word in a carrier run, and no case has a run in a file without a loss/claim name (see H1, H2).
- L1: any file whose name contains "loss" or "claim" but is not a loss run (e.g. loss-control-report.md) blocks plain complete with "not a recognised carrier loss run". Safe direction.
- L2: the dev report scores SUB-153 "loss run as gold" as a miss only because of the wording of the gold line. Normalise the scorer label or the gold wording before the milestone tally.
- L3: the `ponytail:` comment understates the ceiling: scans and attachments are missed too, not only "doc1.pdf".

This is a development check, not a production approval. An approved P-046 is not a production approval, and the T-027 veto stands.

## LOOK-AGAIN — commit cb7b259 (2026-10-15)

- Evidence: `git show cb7b259 -- underwriting_pipeline/ai/prepare.py`; `carrier_run_check` (prepare.py 488–513); dev-SUB-147-153-D-093b-cached.md. SUB-127–146 and their gold not opened, listed or run.
- Self-checks with LLM_API_KEY, LLM_BASE_URL, LLM_MODEL unset: "prepare ok". No model call.
- Probes: the same in-memory probes P0–P13 on the real SUB-153 texts (scratchpad `mr-p046/probe.py`), plus Q1–Q8 (`mr-p046/probe2.py`). Nothing in the repo written apart from this file and DISCUSSION.md.

### Verdict: REJECT as frozen hold-out code (H1 closed; H2 partly open, restated as H3)

| Probe (A = accepted Carrier A run) | 57d56b9 | cb7b259 | D-093 |
|---|---|---|---|
| P2 B undated + "Signed: J. Ortiz" | plain | review pending, B no-date reason | review pending |
| P3 B undated + "Copy provided by agent" | plain | review pending, copy reason | review pending |
| P4 B undated, insured "Owner Holdings" | plain | review pending | review pending |
| P5 / P6 unrecognised dated run as attachment.md / resubmission.md | plain | review pending | review pending |
| P7 scan.jpg, garbled header | plain | review pending (scan reason) | review pending |
| **P9 SUB-153's undated Carrier B run pasted in email.md under "Hi,"** | plain | **plain** | review pending |
| **Q1 unrecognised undated run as attachment.md** | — | **plain** | review pending |
| **Q7 undated B run under "From agent:" in email.md** | — | **plain** | review pending |
| Q2 same undated run as loss-history.md | — | review pending | review pending |
| Q3 unrecognised run, "As of 2026-09-30" wording, attachment.md | — | plain | review pending |
| Q4 "SAMPLE" unrecognised run, attachment.md | — | review pending | review pending |
| Q5 sov.xlsx with "insurance" and a date | — | review pending (false alarm) | plain |
| Q6 scan.jpg, empty OCR | — | plain | (unread-page rule) |
| P0, P1, P8, P11, P12, P13 | unchanged and correct | unchanged and correct | |

**H1: closed.** A carrier header now always makes a loss-run document; P2–P4 are self-checks and pass.

**H2: partly closed.** P5–P7 pass and are self-checks. P9 does not: the self-check for email.md uses the dated Carrier B run (`b_run`), not the undated run that P9 named, so it passes only because a dated run shows every loss-run part.

### H3 (High, the open part of H2): an undated loss run in a file not named as a loss run gives plain "complete"
- Where: `carrier_run_check` recognises a carrier header only on the first line (`lines[0]`). With any line above it (a greeting, "From:"), state is None. The fallback then needs every RUN_PARTS item, and one of them is the valued-date wording. An undated run lacks that wording by definition, so an undated run can be caught only by its file name.
- Effect: P9, Q1 and Q7 give plain "complete" beside an accepted run. "Undated" is the first case D-093 names, and attachment.md and email-style files carry loss runs in the dev inbox. My H2 remedy (a) asked for "all parts", which cannot catch an undated run. That gap was in my own remedy, so this is restated here instead of being treated as a new defect in the author's work.
- Resolution: (a) look for a carrier header on any line, not only the first, and judge the run from that line down; and (b) for a typed document with no carrier header, count it as a loss-run document when it shows every loss-run part except the valued date (carrier word, policy period, claims), with the no-date reason when the date is missing. The safe direction applies: an application that mentions an insurer, a policy period and claims may go to review pending. Add P9 (undated B under "Hi,"), Q1 and Q7 as self-checks that assert review pending, and keep P11, P12 and SUB-153 as they are. This is extraction code: it needs a new P-### and the user's `approve change P-###`. Closed when those self-checks pass and the cached dev SUB-147–153 re-run still has 0 false completes.

Until H3 is closed, SUB-127–146 should not run on cb7b259 as the frozen hold-out code.

### Medium / Low (backlog, one line each)
- M2: the D-093b dev report header records commit 51143fc, not the fix commit cb7b259, so the report cannot be tied to the code it checks. Record the working-tree hash or a "dirty" flag.
- L4: valued wording "As of <date>" with no "valued" is not a loss-run part (Q3). H3(b) covers the undated reading; add "as of" to the valued part if wanted.
- L5: a spreadsheet with any single part (e.g. an SOV with "insurance" and a date) goes to review pending (Q5). This is the safe direction; watch the false-review rate at the milestone.
- L1 and L2 stand; M1 and L3 closed (self-checks now include letter-word and odd-name cases; ponytail comment replaced).

This is a development check, not a production approval. An approved P-046 is not a production approval, and the T-027 veto stands.

## LOOK-AGAIN 2 — commit 3a77415 (2026-10-15)

- Evidence: `git show 3a77415 -- underwriting_pipeline/` (`_run_doc_reason`, self-checks P9, Q1, Q7, application exclusion); dev-SUB-147-153-D-093c-cached.md. SUB-127–146 and their gold not opened, listed or run (dev-inbox grep skipped those folders).
- Self-checks with LLM_API_KEY, LLM_BASE_URL, LLM_MODEL unset: "prepare ok". No model call.
- Probes: P0–P13 and Q1–Q8 replayed in memory (scratchpad `mr-p046/probe.py`, `probe2.py`), plus new R1–R8 (`probe3.py`). Nothing in the repo written apart from this file and DISCUSSION.md.

### Verdict: APPROVE as frozen hold-out code (H3 closed; no High open)

| Probe (A = accepted Carrier A run) | cb7b259 | 3a77415 | D-093 |
|---|---|---|---|
| P9 undated B under "Hi," in email.md | plain | review pending, no-date reason | review pending |
| Q1 unrecognised undated run, attachment.md | plain | review pending, no-date reason | review pending |
| Q7 undated B under "From agent:" in email.md | plain | review pending, no-date reason | review pending |
| Q3 "As of" wording, attachment.md | plain | review pending (no-date reason) | review pending |
| P0–P8, P10–P13, Q2, Q4, Q5, Q8 | as before | unchanged | |
| P11 A + letter (P-040), P12 A alone | plain | plain | plain |
| R1 undated B quoted with "> " in email.md | — | review pending | review pending |
| R3 undated B under a "# " heading | — | review pending | review pending |
| R8 header in capitals, pasted in email | — | review pending | review pending |
| **R2** "> "-quoted undated B no-claims run + "From agent:" | — | **plain** | review pending |
| **R4** "# " heading undated B no-claims run + "Signed: J. Ortiz" | — | **plain** | review pending |
| **R5** "Fwd: " header undated B no-claims run + "Sent by our agent." | — | **plain** | review pending |
| R6 unrecognised undated no-claims run + "Provided by agent." | — | plain | ambiguous with a P-040 letter |
| R7 undated unrecognised run inside application.md | — | plain | by design (application exclusion) |

**H3: closed.** A carrier header on any line now makes a loss-run document (P9, Q7), and a typed document with every part but the valued date gets the no-date reason (Q1). All three are self-checks that pass, and the cached dev SUB-147–153 re-run reports 0 false completes. No new High: R2, R4 and R5 need three things at once (a carrier header that is not a clean line on its own, a no-claims-only undated run, and a letter word). No dev file has a prefixed carrier header. Rated Medium.

### Medium / Low (backlog, one line each)
- M3: in the content path, `kind == "letter"` still excuses an undated no-claims run whose carrier header has a prefix ("> ", "# ", "Fwd:") when a letter word is present (R2, R4, R5). Fix: find the header with `re.search` on each line, or do not excuse as a letter a document that shows a carrier word and a policy period. This needs a P-### after the hold-out.
- M2 stands: the D-093c report header names cb7b259, but the code it checked is 3a77415 (working tree). Tie the hold-out report to 3a77415.
- L6: the application exclusion (two application words) lets an undated run pasted inside an application give plain complete (R7). This is by design; check it at the milestone.
- L7: SUB-153 email.md (prior-carrier prose) now adds a second no-date reason on the card. Status is unchanged (safe), but the card is noisier for the underwriter.
- L8: R6 (a carrier, a period, no claims and an agent word, with no header) is still read as a P-040 letter. This is ambiguous by design.
- L1, L2, L5 stand; L4 closed by H3(b) (Q3 now review pending).

This is a development check, not a production approval. The frozen hold-out code is commit 3a77415, and SUB-127–146 may run on it once, under D-020/D-022. An approved P-046 is not a production approval, and the T-027 veto stands.
