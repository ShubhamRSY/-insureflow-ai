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
