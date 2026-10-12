# Demo blockers

- Author: @pm
- Date: 2026-10-11
- Source: D-033 item 4, D-035, D-037. Only High findings on the demo path, in the user's fix order. Everything else is in team/BACKLOG.md.
- A line is closed by its reviewers, not by @pm. A veto is lifted only by the role that holds it.
- "Needs approval" means the user's exact words "approve change P-###" in the chat (D-017). Nothing on that line is built before them.
- Synthetic data only. Nothing here authorizes a send. Nothing here is a production approval.

| # | Line | Needs the user's approval before it is built | Owner | Task |
|---|---|---|---|---|
| 1 | Send gates (P-010) | No. Approved in D-029 | @data-engineer, @ai-engineer-assistant, @software-engineer | T-069, T-070, T-071 |
| 2 | Send needs an underwriter approve | No | @software-engineer | T-079 |
| 3 | Exact citations only, with confidence and unread content | **Yes: "approve change P-016".** Not written yet | @ai-engineer-assistant | T-080 (proposal) |
| 3b | The workbench shows the cited text | No. Placement is for @user to confirm | @software-engineer | T-081 |
| 4 | Carrier match rules with caps enforced | No. The rules are @head-of-underwriting's | @head-of-underwriting, @software-engineer | T-082, T-083 |
| 5 | Score fixes (P-015) | **Yes: "approve change P-015".** Not written yet | @data-scientist | T-084 (proposal) |
| 6 | Package built from the reviewed file | No | @software-engineer | T-085 |
| 7 | The user's exact send line | No | @software-engineer | T-086 |
| 8 | Quote tracking | No | @software-engineer | T-087 |
| 9 | New 20-file hold-out, the official score for the demo | No new approval for the run. It waits on P-016, and on P-017 for the hash in the score file | @producer, @senior-underwriter, @model-risk | T-091, T-092, T-093 |

## 1. Send gates (P-010)

- Broken: a file whose status is `extraction_failed` or `all_values_rejected` can be approved or sent when the caller leaves out the report, passes its own, or is the user.
- Found by: @model-risk (T-059 High-1), @software-engineer (T-059 High-1, High-2), @account-manager (T-059 High-1, High-2), @compliance (T-020 H2).
- Covered by: D-021, D-024, D-029 (P-010, approved with G2 D1 S1 C1, no Low-2).
- Owner and task: @data-engineer T-069 (the saved-file keys), then @ai-engineer-assistant T-070 (`prepare.py`, `eval_holdout.py`), then @software-engineer T-071 (`package.py`, `workbench.py`).
- Needs approval: no. Already approved.
- Closed when: every box on T-070 and T-071 is met, with a self-check for each case; @model-risk, @software-engineer, and @account-manager have looked at T-059 again and @model-risk has said whether its veto is resolved; @compliance has confirmed item (b) of its T-020 veto.

## 2. Send needs an underwriter approve

- Broken: `package.py` never reads the decision log, so a file with no logged approve, or a declined file, can be sent to a carrier.
- Found by: @compliance (T-020 H1, and the question to the user on T-019), @senior-underwriter (T-020 High-3).
- Covered by: D-033 item 2.
- Owner and task: @software-engineer, T-079.
- Needs approval: no. `package.py` is under `underwriting_pipeline/app/`.
- Closed when: the send reads the decision log itself and refuses, for every actor, unless the last decision for the submission is approve; a self-check shows no decision refused and approve-then-decline refused; @compliance has confirmed item (a) of its T-020 veto.
- Open for @user: a file declined and later approved (see "For the user").

## 3. Exact citations only, with confidence and unread content

- Broken: a value is accepted with a citation that does not hold it (year built 1990 cited to "210-555-1990"); on a scan, misread numbers and dates are stored as confirmed because the page score ignores digits; files and pages that were not read are not listed for a person.
- Found by: @model-risk (T-027 H1, H2, H3, production veto), @senior-underwriter (T-027 High-1, High-2, High-3).
- Covered by: D-033 item 4 and D-037, which accepts @model-risk's (a), (b), and (c) and asks for them as one proposal, P-016. (b) amends P-003b.
- Owner and task: @ai-engineer-assistant, T-080 writes the proposal. The build task is made when the user approves.
- Needs approval: **yes, "approve change P-016"**. The proposal is not written yet.
- Closed when: P-016 is approved and built; (a) "no value fallback; the value must be inside the quoted span for names, numbers, dates, addresses; translated fields stay needs_review"; (b) "gate on the lower of model and OCR confidence, OCR confidence from the cited words including digits"; (c) "every file and page is read or listed as needs human with the reason"; the reviewers' cases pass as self-checks; the quick set of 15 is scored after the change and every drop is reported; @model-risk and @senior-underwriter have looked at T-027 again. The veto is lifted only by @model-risk, and only with line 9 done.

### 3b. The workbench shows the cited text

- Broken: the card slices the raw file, so a PDF shows "%PDF-1.4 1 0 obj..." as the cited text, and one jpg, png, or xlsx stops the whole queue from loading (29 inbox files).
- Found by: @compliance (T-019 High-1), @senior-underwriter (T-019 High-1).
- Covered by: no decision names it. @pm placed it here because the demo brief says "with citations". For @user to confirm or move to the backlog.
- Owner and task: @software-engineer, T-081.
- Needs approval: no, unless the fix needs the model's quote kept on the stored row; that part then goes into P-016.
- Closed when: the card shows the text the value came from for PDF, xlsx, png, jpg, and csv; one unreadable file does not stop the queue; a check with a PDF and an image passes; @compliance and @senior-underwriter have looked again.

## 4. Carrier match rules with caps enforced

- Broken: `route()` contradicts carrier-match.md (cannabis dispensary retail and armed security office go to Carrier A, an $8,000,000 office goes to Carrier A, barber shop is no-match), and the send gate's in-appetite check uses it.
- Found by: @senior-underwriter (T-019 High-3, and T-020).
- Covered by: D-033 item 4. The rules are @head-of-underwriting's to decide.
- Owner and task: @head-of-underwriting T-082 (the class lists and the caps), then @software-engineer T-083 (the code).
- Needs approval: no.
- Closed when: carrier-match.md holds whole-word class lists, the no-match classes, roofing, each cap as a number, and the Carrier B wording; `route()` follows it with one test for each of the eight cases; the send gate uses the same function; @senior-underwriter and @head-of-underwriting have looked again.

## 5. Score fixes (P-015)

- Broken: the largest code, LOSS_HISTORY, can never fire; a failed or incomplete file shows "Score: 0 · none", the same as the lowest hazard; cooking points come from cuisine words; a wrong code cannot be marked and no score is saved with the decision.
- Found by: @actuary (T-017 High-1 to High-3), @model-risk (T-017 High-1 to High-3, production veto), @responsible-ai (T-017 H1 to H4, fairness veto).
- Covered by: D-031 item 5 and D-033 item 3, as proposal P-015.
- Owner and task: @data-scientist, T-084 writes the proposal, with @software-engineer for the `workbench.py` part. The build tasks are made when the user approves.
- Needs approval: **yes, "approve change P-015"**. The proposal is not written yet.
- Closed when: P-015 is approved and built; the page shows "Loss history: not scored"; a failed or incomplete file shows "Not scored" with the reason; cooking points come only from stated hazards, with a wording-pair test; each decision row saves points, codes, and the points version; a code can be marked wrong with a logged reason; @actuary, @model-risk, and @responsible-ai have looked at T-017 again. Each veto is lifted only by its holder.

## 6. Package built from the reviewed file

- Broken: the package is whatever text the caller types; it has no citations, no named carrier, and no check of required fields (the sent SUB-002 package has no sales and no year built).
- Found by: @senior-underwriter (T-020 High-2), @compliance (T-020 H4).
- Covered by: D-033 item 4.
- Owner and task: @software-engineer, T-085.
- Needs approval: no.
- Closed when: the package is built from the saved reviewed file with citations and the named carrier; it is refused when a required field is empty; a self-check passes; @compliance has confirmed item (d) of its T-020 veto.

## 7. The user's exact send line

- Broken: the actor is a word the caller supplies, so any role that passes "user" writes to to-carrier.
- Found by: @compliance (T-020 H3).
- Covered by: D-035.
- Owner and task: @software-engineer, T-086.
- Needs approval: no.
- Closed when: a user send carries the exact "send to carrier SUB-###" line, matched to the submission id and logged; a send without it writes nothing; a self-check passes; @compliance has confirmed item (c).

## 8. Quote tracking

- Broken: nine carrier replies sit in simulation/from-carrier/ and no code reads them, so the open subjectivity on SUB-002 is not tracked.
- Found by: @senior-underwriter (T-020 High-1), @compliance (T-020 H5).
- Covered by: D-035.
- Owner and task: @software-engineer, T-087.
- Needs approval: no.
- Closed when: there is a status per submission and carrier read from the carrier replies, with each subjectivity open or closed; SUB-002's shows as open; a self-check passes; @compliance has confirmed item (e) and says whether the T-020 veto is lifted; @senior-underwriter has looked at T-020 again.

## 9. New 20-file hold-out, the official score for the demo

- Broken: no hold-out score exists for the current prompt and gate, and no score has a commit hash.
- Found by: @model-risk (T-027 H4). @senior-underwriter (T-053 High-2): no hold-out has ever scored the effective date.
- Covered by: D-037 (d), with D-020, D-022, D-025, D-034.
- Owner and task: @producer T-091 (SUB-087 through SUB-106), then @senior-underwriter T-092 (gold first, with an Effective date line and a claims line), then @model-risk T-093 (scored once).
- Needs approval: none for the run itself. It cannot start before P-016 is approved, built, frozen, and committed. The hash in the score file needs P-017 (T-088, **"approve change P-017"**, not written yet). Publishing the score needs the user's word for that run (D-029, U2).
- Closed when: the 20 files were built after the freeze; the gold existed before any score; no code changed after the gold; the score was run once, with the commit hash and the call log saved, and published once; @ai-engineer-assistant and @senior-underwriter have reviewed T-093.

## Not on this list

- High findings that are not on the demo path are in team/BACKLOG.md, B-138 to B-148, marked High. They include the decision log taking any id (B-138), "edit" storing no corrected value (B-139), and the three on the feedback log (B-140 to B-142).
- P-014 (T-078) and P-017 (T-088) are not blockers by themselves. They are in the order of work because D-031 and D-034 put them before scored runs.
- P-006 (T-062), the variance test (T-066), and the fairness test (T-067) are D-030's goal, not review findings. They are in the order of work in deliverables/pm/roadmap.md.
