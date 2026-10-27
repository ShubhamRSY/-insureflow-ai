# Task Board

Statuses: TODO · IN_PROGRESS · BLOCKED · IN_REVIEW · DONE · CANCELLED
Only @pm creates and assigns tasks. Owners update their own status.

D-004 (user, 2026-10-09): Sanger & Altgelt agency pipeline. Eight steps. No auto-decline, no auto-bind. Texas small commercial. Carriers A/B/C are placeholders.

## Sprint 0 — Discovery

### T-001 — Write project charter and roadmap
- Owner: @pm
- Requested by: @user
- Status: CANCELLED
- Priority: P0
- Depends on: —
- Reviewers: @head-of-underwriting
- Acceptance criteria:
  - [x] Goal, scope, out-of-scope, success metrics
  - [x] Phase plan with milestones
  - [x] Initial task breakdown for Sprint 1 added to this board
- Output: deliverables/pm/roadmap.md
- Notes: CANCELLED 2026-10-09. Carrier/MGA charter does not fit D-004. Replaced by T-013. The roadmap file was rewritten; do not follow the old metrics.

### T-002 — Define risk appetite and authority matrix
- Owner: @head-of-underwriting
- Requested by: @pm
- Status: CANCELLED
- Priority: P0
- Depends on: —
- Reviewers: @senior-underwriter, @actuary, @compliance
- Acceptance criteria:
  - [x] Target, restricted and prohibited classes
  - [x] Auto-quote / refer / decline bands
- Output: deliverables/head-of-underwriting/appetite-guide.md, authority-matrix.md
- Notes: CANCELLED 2026-10-09. Auto-quote and auto-bind are forbidden by D-004. Carrier matching is T-018. Old files are historical only.

### T-003 — Document current underwriting workflow and required fields
- Owner: @senior-underwriter
- Requested by: @pm
- Status: DONE
- Priority: P0
- Depends on: —
- Reviewers: @ai-engineer, @data-engineer
- Acceptance criteria:
  - [x] Step-by-step workflow with time per step and pain points
  - [x] Required fields per class and source documents
- Output: deliverables/senior-underwriter/current-workflow.md, required-fields.md
- Notes: Field list still feeds steps 2 and 3. The carrier bind path in the workflow doc is not the target. Desk times are estimates.

### T-004 — Data inventory and canonical data model (draft)
- Owner: @data-engineer
- Requested by: @pm
- Status: DONE
- Priority: P0
- Depends on: T-003
- Reviewers: @compliance, @data-scientist, @ai-engineer
- Acceptance criteria:
  - [x] Internal and third-party sources listed with permitted uses marked "pending compliance"
  - [x] Draft entity model
  - [x] Conflicts stored with both values, sources, and resolution
- Output: deliverables/data-engineer/data-inventory.md, data-model.md, extractions/, conflicts/
- Notes: Closed 2026-10-09 under D-007. Open conflicts stay unresolved until a reply names one side. SUB-003 is the resolved example: 55 Culebra Park Dr and 14,000 square feet were the schedule side; the reply kept the application. Resolved rows are not deleted when the live files later agree. Square feet compare on digits.

### T-005 — Regulatory requirements register
- Owner: @compliance
- Requested by: @pm
- Status: CANCELLED
- Priority: P0
- Depends on: —
- Reviewers: @head-of-underwriting, @responsible-ai
- Acceptance criteria:
  - [x] Applicable rules listed with how we comply
  - [x] Items needing real legal confirmation flagged
- Output: deliverables/compliance/regulatory-register.md
- Notes: CANCELLED 2026-10-09. Written for a writing company (rate filing, MGA authority). Agency register is T-022. Old file is not the control.

### T-006 — AI architecture proposal (intake, extraction, triage, copilot)
- Owner: @ai-engineer
- Requested by: @pm
- Status: CANCELLED
- Priority: P1
- Depends on: T-003
- Reviewers: @ml-engineer, @software-engineer, @model-risk, @compliance
- Acceptance criteria:
  - [x] Component diagram and data flow
  - [x] Human-in-the-loop points
  - [x] Evaluation approach
  - [x] Raised as a PROPOSAL in DISCUSSION.md
- Output: deliverables/ai-engineer/architecture.md
- Notes: CANCELLED 2026-10-09. Auto-quote path conflicts with D-004. Steps 1–3 are T-014–T-016. Old architecture is not to be built.

### T-007 — Risk model problem framing
- Owner: @data-scientist
- Requested by: @pm
- Status: DONE
- Priority: P1
- Depends on: T-004
- Reviewers: @actuary, @responsible-ai, @model-risk
- Acceptance criteria:
  - [x] Target, window, exclusions, baseline approach
- Output: deliverables/data-scientist/problem-framing.md
- Notes: Accepted 2026-10-09. Points, not a price, not a carrier decline. Not a validation.

### T-008 — Model and AI validation standards
- Owner: @model-risk
- Requested by: @pm
- Status: DONE
- Priority: P1
- Depends on: —
- Reviewers: @compliance
- Acceptance criteria:
  - [x] Evidence required by risk tier, for predictive models and LLM components
- Output: deliverables/model-risk/validation-standards.md
- Notes: Addendum for D-004 appended 2026-10-09. Auto-quote Tier 1 path withdrawn. Not a production approval.

### T-009 — Fairness test plan
- Owner: @responsible-ai
- Requested by: @pm
- Status: DONE
- Priority: P1
- Depends on: T-022
- Reviewers: @compliance, @data-scientist
- Acceptance criteria:
  - [x] Groups, metrics, thresholds, data approach
- Output: deliverables/responsible-ai/fairness-test-plan.md
- Notes: Accepted by @compliance and @data-scientist 2026-10-09. No AI approve/decline metric.

### T-010 — Target underwriting workflow with human-in-the-loop
- Owner: @senior-underwriter
- Requested by: @pm
- Status: CANCELLED
- Priority: P0
- Depends on: T-002, T-003
- Reviewers: @head-of-underwriting, @compliance, @ai-engineer
- Acceptance criteria:
  - [ ] Target steps from submission to bind, with who acts (system vs human)
  - [ ] Every auto-quote gate mapped to a field in required-fields.md
- Output: deliverables/senior-underwriter/target-workflow.md
- Notes: CANCELLED 2026-10-09. Auto-quote gates are void. The pipeline tasks are the workflow.

### T-011 — Pilot loss and pricing assumptions
- Owner: @actuary
- Requested by: @pm
- Status: CANCELLED
- Priority: P0
- Depends on: T-002
- Reviewers: @head-of-underwriting
- Acceptance criteria:
  - [x] Expected loss ratio for the proposed auto-quote band, with the assumption stated
  - [x] Statement that the system may not deviate from the filed rate
- Output: deliverables/actuary/pilot-assumptions.md
- Notes: CANCELLED 2026-10-09. Rate manual is not applicable (D-004). Scoring and carrier appetite moved to T-023. Do not use the 0.65 permissible LR as a product gate.

### T-012 — Permitted-use review of inventoried data sources
- Owner: @compliance
- Requested by: @pm
- Status: DONE
- Priority: P0
- Depends on: T-004, T-005
- Reviewers: @responsible-ai, @data-engineer
- Acceptance criteria:
  - [x] Each source marked approved, restricted, or prohibited
  - [x] Training-use called out separately from underwriting-use
- Output: deliverables/compliance/data-use-review.md
- Notes: S-05 set to not used. Accepted by @responsible-ai and @data-engineer this round. Training on submissions still prohibited.

### T-013 — Rewrite the roadmap for the agency pipeline
- Owner: @pm
- Requested by: @user
- Status: DONE
- Priority: P0
- Depends on: —
- Reviewers: @head-of-underwriting
- Acceptance criteria:
  - [x] Eight steps, owners, and the build-sprint cut
  - [x] Success metrics match D-004
  - [x] Cancelled carrier auto-quote work listed
- Output: deliverables/pm/roadmap.md
- Notes: Accepted by @head-of-underwriting 2026-10-09.

## Build sprint 1 — steps 1–3

### T-014 — Step 1: Submission intake
- Owner: @software-engineer
- Requested by: @pm
- Status: DONE
- Priority: P0
- Depends on: —
- Reviewers: @senior-underwriter, @compliance
- Acceptance criteria:
  - [x] A submission id and a hash per document
  - [x] Empty pack rejected
  - [x] Synthetic flag on every record
- Output: underwriting_pipeline/app/intake.py, deliverables/software-engineer/api-spec.md
- Notes: Accepted 2026-10-09. Hashed SUB-001, SUB-002, SUB-003. No bind or decline in this module.

### T-015 — Step 2: Document extraction with citations
- Owner: @ai-engineer
- Requested by: @pm
- Status: DONE
- Priority: P0
- Depends on: T-003
- Reviewers: @senior-underwriter, @model-risk, @data-engineer
- Acceptance criteria:
  - [x] Each value has a span that matches the source text
  - [x] Missing field stays null
  - [x] A "no known loss" letter does not become a loss-run date
- Output: underwriting_pipeline/ai/prepare.py
- Notes: Scored 2026-10-09 against the original SUB-007–SUB-016 pack. Field accuracy is in deliverables/ai-engineer/evals/SUB-007-016-field-accuracy.md. D-009: that 100% is not proof. The hold-out score is T-026. Not a production approval.

### T-016 — Step 3: Completeness check and missing-info request
- Owner: @ai-engineer
- Requested by: @pm
- Status: DONE
- Priority: P0
- Depends on: T-015
- Reviewers: @senior-underwriter, @compliance
- Acceptance criteria:
  - [x] Missing required fields listed
  - [x] Request text names those fields and does not decline the account
- Output: underwriting_pipeline/ai/prepare.py
- Notes: D-006. Drafts go to simulation/pending-approval/. Only the user moves a file to simulation/to-producer/. Restaurant requests ask the five industry items.

## Later pipeline steps

### T-017 — Step 4: Risk score and reason codes
- Owner: @data-scientist
- Requested by: @pm
- Status: IN_REVIEW
- Priority: P1
- Depends on: T-007
- Reviewers: @actuary, @model-risk, @responsible-ai
- Acceptance criteria:
  - [ ] Interpretable score and reason codes an underwriter can override
  - [x] Score cannot decline, bind, or set a price
- Output: deliverables/data-scientist/reason-codes.md, underwriting_pipeline/models/
- Notes: Fixed points, not a fit. Waiting on reviewers. No gradient boosting. 2026-10-11, @pm, round wrap-up, recorded as the reviewers wrote it: @actuary, REVIEW, "Verdict: REJECT. Criterion 2 is met", "Criterion 1 is not met." @model-risk, OBJECTION, "Verdict: NOT APPROVED. Veto on production use of the point score." "Criterion 1 (interpretable, underwriter can override): NOT MET." @responsible-ai, OBJECTION, "Verdict: NOT APPROVED. Fairness and contestability veto on marking T-017 DONE." "Criterion 2 passes", "Criterion 1 fails." Box 1 is unticked for that reason. Both vetoes are open. The fix is to be written as proposal P-015 (D-031 item 5, D-033 item 3): T-084. It is not written, not approved, and not built. This task stays IN_REVIEW until P-015 is approved and built and all three reviewers have looked again. Medium and Low findings: team/BACKLOG.md B-018 to B-028 and B-061 to B-070. Claim extraction is parked by the user (B-149). Line 5 of team/DEMO-BLOCKERS.md. @pm gives no verdict.

### T-018 — Step 5: Appetite and carrier matching (A/B/C)
- Owner: @head-of-underwriting
- Requested by: @pm
- Status: DONE
- Priority: P1
- Depends on: —
- Reviewers: @senior-underwriter, @actuary, @compliance
- Acceptance criteria:
  - [x] Placeholder appetite for Carrier A, B, and C
  - [x] Match is a recommendation; the underwriter chooses
- Output: deliverables/head-of-underwriting/carrier-match.md
- Notes: Accepted 2026-10-09. Carrier B writes restaurants and light contractors with 3 clean loss years. Bars, nightclubs, and fireworks are no-match, not a producer decline. The underwriter still chooses.

### T-019 — Step 6: Underwriter workbench
- Owner: @software-engineer
- Requested by: @pm
- Status: IN_REVIEW
- Priority: P0
- Depends on: T-014, T-015, T-016
- Reviewers: @senior-underwriter, @compliance
- Acceptance criteria:
  - [ ] Page shows each submission, extracted fields with citations, conflicts, missing items, score with reason codes, and carrier match
  - [x] Underwriter can approve, edit, or decline
  - [x] No path records a decision without an underwriter id and a reason on decline
- Output: deliverables/software-engineer/workbench-ux.md, underwriting_pipeline/app/workbench.py
- Notes: Started 2026-10-09 under D-009. Does not bind. The React page in frontend/ was not changed. 2026-10-11, @pm, round wrap-up, recorded as the reviewers wrote it: @compliance, REVIEW, "Verdict: CHANGES REQUIRED. Not a veto", "Do not mark DONE." "High-1, criterion 1 not met (A-02)." "High-2, criterion 3 met in wording only (A-03)." @senior-underwriter, REVIEW, "Verdict: REJECT. I agree with @compliance's High-1 and High-2." Box 1 is unticked for that reason. Boxes 2 and 3 are left as they were: @compliance wrote "met in wording only" for box 3, and @senior-underwriter's High-2 ("edit" corrects nothing) names no box; whether they hold is for the two reviewers to say when they look again. Where each High finding went: the cited text (@compliance High-1, @senior-underwriter High-1) is T-081; the carrier match (@senior-underwriter High-3) is T-082 and T-083, line 4 of team/DEMO-BLOCKERS.md; @compliance High-2 and @senior-underwriter High-2 are not on the D-033 list and are team/BACKLOG.md B-138 and B-139, marked High. Medium and Low: B-029 to B-032 and B-071 to B-084. Stays IN_REVIEW. @pm gives no verdict.

### T-020 — Step 7: Carrier-ready package and quote tracking
- Owner: @software-engineer
- Requested by: @pm
- Status: IN_REVIEW
- Priority: P0
- Depends on: T-019
- Reviewers: @senior-underwriter, @compliance
- Acceptance criteria:
  - [x] A package can be built for a submission
  - [ ] Nothing is written to simulation/to-carrier/ unless all of these hold. (a) For every actor: "a carrier send requires a logged underwriter approve; a declined file can never be sent" (D-033 item 2). (b) For every actor: the file's saved status is not `extraction_failed` or `all_values_rejected` (D-021, D-024, P-010). (c) The sender is the simulated @account-manager, and the file is complete, in appetite, free of open conflicts, and free of unread pages, with a written reason (D-017); or the sender is the user, and the send carries the user's exact "send to carrier SUB-###" line, matched to the submission id and logged (D-017, D-035). No AI role sends
  - [ ] Quote status tracked per placeholder carrier: "a status per submission and carrier from the carrier replies, including open subjectivities" (D-035)
- Output: underwriting_pipeline/app/package.py
- Notes: D-009. No package was sent this round. Quote tracking waits on a carrier reply. 2026-10-11, @pm, round wrap-up, recorded as the reviewers wrote it: @senior-underwriter, REVIEW, "Verdict: REJECT." @compliance, OBJECTION, "VETO (A-02 misrepresentation to a carrier; D-021, D-024, D-033)." "(1) package can be built: met, as free text only. (2) no write without the user's typed line: NOT met. (3) quote status per carrier: NOT met, not built." Box 2 is unticked for that reason. Criterion 2 is restated by @pm to match D-017 and D-033, as @compliance asked (B-091) and @senior-underwriter noted (B-034); the old wording was "Nothing is written to simulation/to-carrier/ unless the user types send to carrier SUB-###". Criterion 3 now carries D-035's words. The veto is open. What resolves it, as @compliance wrote, and its task: (a) the send reads the decision log itself, T-079; (b) the send loads the saved run itself and takes no report from the caller, T-070 and T-071 (P-010); (c) the user's exact line, T-086; (d) the package built from the saved reviewed file, T-085; (e) the status per submission and carrier, T-087; (f) one self-check per gate, in each of those tasks. "Then send it back to me." The in-appetite gate calls `route()`, so T-083 applies here too. Lines 1, 2, 6, 7, and 8 of team/DEMO-BLOCKERS.md. Medium and Low: B-033, B-034, and B-085 to B-097. Stays IN_REVIEW until the veto is lifted by @compliance and @senior-underwriter has looked again. @pm gives no verdict. 2026-10-13, @pm, board maintenance: @compliance re-checked and confirmed item (b) is met, and the T-020 veto STAYS (team/DISCUSSION.md:2306, "Verdict: REJECT — the T-020 veto stands. Item (b) is now met. The veto lifts only when all six are in; (a), (c), (d), and (e) are not."). The remaining conditions are the four High items: (a) the send reads the decision log itself — T-079; (c) the user's exact send line — T-086; (d) the package built from the saved reviewed file — T-085; (e) the status per submission and carrier — T-087; each carrying one self-check per gate, at the end of which T-020 goes back to @compliance. The task stays IN_REVIEW. No verdict from @pm.

### T-021 — Step 8: Feedback loop from underwriter decisions
- Owner: @ml-engineer
- Requested by: @pm
- Status: IN_REVIEW
- Priority: P0
- Depends on: T-019
- Reviewers: @data-scientist, @model-risk
- Acceptance criteria:
  - [ ] Every decision stored with actor, action, reason, and the AI version it corrected
  - [ ] Corrections can be counted for the "no corrections" metric
- Output: deliverables/ml-engineer/feedback-loop.md, underwriting_pipeline/app/workbench.py
- Notes: D-014. The workbench log stores approve, edit, and decline. Edit and decline require a reason. The self-check counts them. Not a training set and not a production model. 2026-10-11, @pm, round wrap-up, recorded as the reviewers wrote it: @data-scientist, REVIEW, "Verdict: REJECT. Both criteria are ticked and neither holds." @model-risk, REVIEW, "Verdict: REJECT. Not a production approval. Criterion 1 is not met; criterion 2 is partly met." Both boxes are unticked: both reviewers say box 1 fails, and @data-scientist shows box 2 fails while @model-risk writes "partly met". The three High findings are not on the D-033 fix order, so they are team/BACKLOG.md B-140, B-141, and B-142, marked High, with no fix task yet. P-015 (T-084) is to cover points, codes, and points version on the decision row; the rest has no proposal. Medium and Low: B-057 to B-060 and B-098 to B-111. Stays IN_REVIEW with two unanswered REJECTs. While they are unanswered, @pm does not quote the "no corrections" metric from this log in the demo guide. @pm gives no verdict.

### T-033 — Sprinkler field and carrier loss-run rules
- Owner: @software-engineer
- Requested by: @user
- Status: DONE
- Priority: P0
- Depends on: T-019
- Reviewers: @senior-underwriter, @model-risk
- Acceptance criteria:
  - [x] Habitational sprinklers are read from the application sprinkler field
  - [x] A carrier loss-run date wins over a no-known-loss letter in the same folder
  - [x] Tests cover both rules
  - [x] The model prompt and OCR were not changed for this task
- Output: underwriting_pipeline/ai/prepare.py, underwriting_pipeline/app/workbench.py
- Notes: D-014. SUB-013 now routes to Carrier C and was not sent. SUB-005 reads sprinklers yes and stays hold because operations and sales still conflict.

### T-034 — Email wording and square-foot conflicts on the development set
- Owner: @ai-engineer
- Requested by: @user
- Status: DONE
- Priority: P0
- Depends on: T-032
- Reviewers: @model-risk
- Acceptance criteria:
  - [x] "They cook <food>" keeps the food word and restaurant
  - [x] "Joisted masonry" is not shortened to masonry
  - [x] Two different square-foot figures become a conflict
  - [x] Checked on development files, not by editing the SUB-037 score
- Output: underwriting_pipeline/ai/prepare.py
- Notes: D-014. SUB-030 and SUB-034 were the development check. A year on the line above "Square feet:" is not a square-foot figure.

### T-035 — Gold answers for hold-out SUB-047 through SUB-056
- Owner: @senior-underwriter
- Requested by: @user
- Status: DONE
- Priority: P0
- Depends on: T-034
- Reviewers: @model-risk
- Acceptance criteria:
  - [x] One expected answer per submission, written before the score ran
  - [x] None of the answers is an automatic decline
- Output: deliverables/senior-underwriter/gold-set/SUB-047.md through SUB-056.md
- Notes: Written 2026-10-10 before eval_holdout_047.py ran.

### T-036 — Score hold-out SUB-047 through SUB-056
- Owner: @model-risk
- Requested by: @user
- Status: DONE
- Priority: P0
- Depends on: T-034, T-035
- Reviewers: @ai-engineer-assistant, @senior-underwriter
- Acceptance criteria:
  - [x] Scored without editing the scorer after the gold files existed
  - [x] A null that matches missing is not counted as correct
  - [x] Compared with the SUB-037 through SUB-046 score
  - [x] The score comes from a successful model call
- Output: deliverables/ai-engineer/evals/SUB-047-056-holdout.md, deliverables/model-risk/holdout-SUB-047-056.md
- Notes: 2026-10-10. Calls succeeded. Not a production approval. Every field with a gold value is 10/10. Loss runs are 6 hit, 0 miss, 4 not credited. 2026-10-11: reviewer handle changed from the retired @ai-engineer to @ai-engineer-assistant (D-017). No other change. 2026-10-11, @pm, round wrap-up, recorded as the reviewers wrote it: @senior-underwriter, REVIEW, "Verdict: APPROVE. No High." "Read 'clears the 9/10 target' narrowly: eight of the nine extracted fields were scored, effective date was not, and a loss-run hit is a date." @ai-engineer-assistant, REVIEW, "Verdict: APPROVE. No High." "Criterion 1: no commit shows it (B-045)" Both reviewers approved, so this is closed. No box was shown to fail; the boxes stay as they were, with the reviewers' limits beside them. @senior-underwriter: "The limit in my T-053 review (High-2) applies": effective date was never scored. Wherever this score is quoted it says "8 of 9 fields scored; loss runs = date only" (D-033 item 5). Medium and Low findings are in team/BACKLOG.md (B-039 to B-052, B-056). Not a production approval. @pm gives no verdict.

### T-037 — Normalize numbers before comparing
- Owner: @software-engineer
- Requested by: @user
- Status: DONE
- Priority: P0
- Depends on: T-033
- Reviewers: @senior-underwriter
- Acceptance criteria:
  - [x] 220k and 220000 are the same sales figure
  - [x] $1.2M, commas, sq ft, and sf normalize
  - [x] A sentence is not treated as a number
  - [x] SUB-005 was rechecked
- Output: underwriting_pipeline/ai/prepare.py
- Notes: D-015. SUB-005 sales is 220000. The two operations lines are both 8-unit apartments and are not stored as a conflict. It routes to Carrier C and was not sent.

### T-038 — Gold answers for the harder hold-out SUB-057 through SUB-066
- Owner: @senior-underwriter
- Requested by: @user
- Status: DONE
- Priority: P0
- Depends on: T-037
- Reviewers: @model-risk
- Acceptance criteria:
  - [x] One expected answer per submission, written before the score ran
  - [x] None of the answers is an automatic decline
- Output: deliverables/senior-underwriter/gold-set/SUB-057.md through SUB-066.md
- Notes: Written 2026-10-10 before eval_holdout_057.py ran.

### T-039 — Score hold-out SUB-057 through SUB-066
- Owner: @model-risk
- Requested by: @user
- Status: IN_REVIEW
- Priority: P0
- Depends on: T-037, T-038
- Reviewers: @ai-engineer-assistant, @senior-underwriter
- Acceptance criteria:
  - [x] Scored without editing the scorer after the gold files existed
  - [x] A null that matches missing is not counted as correct
  - [x] Failures are reported, including scans and refusals to pick
  - [ ] The score comes from a successful model call
- Output: deliverables/ai-engineer/evals/SUB-057-066-holdout.md, deliverables/model-risk/holdout-SUB-057-066.md
- Notes: 2026-10-10. Not a production approval. Named insured 5/10. The four hard scans missed. SUB-063 and SUB-066 refused to pick and those fields are misses. 2026-10-11: reviewer handle changed from the retired @ai-engineer to @ai-engineer-assistant (D-017). No other change. 2026-10-11, @pm, round wrap-up, recorded as the reviewers wrote it: @senior-underwriter, REVIEW, "Verdict: APPROVE WITH CHANGES." @ai-engineer-assistant, REVIEW, "Verdict: APPROVE WITH CHANGES." "High-1: criterion 4 is ticked and the files do not show it for four of the ten rows." "The misses are real; the criterion is not." Box 4 is unticked for that reason. Both changes are dated lines that @model-risk adds to deliverables/model-risk/holdout-SUB-057-066.md: T-090. The published score file is not touched (D-025). Stays IN_REVIEW until T-090 is done and both reviewers have looked again. High findings: B-144, B-145. Quoted only with "8 of 9 fields scored; loss runs = date only" (D-033 item 5). @pm gives no verdict.

### T-040 — Manager demo guide
- Owner: @pm
- Requested by: @user
- Status: DONE
- Priority: P0
- Depends on: T-019
- Reviewers: @senior-underwriter
- Acceptance criteria:
  - [x] A 10-minute step-by-step a manager can follow
  - [x] It uses the workbench
  - [x] It says the page does not bind and does not decline
- Output: deliverables/pm/demo-guide.md
- Notes: D-015. The demo serves SUB-009 only.

### T-041 — Repair rotation and deskew before OCR
- Owner: @ai-engineer
- Requested by: @user
- Status: DONE
- Priority: P0
- Depends on: T-039
- Reviewers: @model-risk
- Acceptance criteria:
  - [x] Tesseract OSD corrects rotation, then the page is deskewed, before OCR
  - [x] A low-confidence OSD guess is not applied
  - [x] The Groq account was checked for a vision model
  - [x] An unreadable page is marked needs human read and is not guessed
  - [x] SUB-057, SUB-058, SUB-064, and SUB-065 were the development check
- Output: underwriting_pipeline/ai/sources.py, underwriting_pipeline/ai/prepare.py, underwriting_pipeline/app/workbench.py
- Notes: D-016. No vision model is on this Groq account. The four development scans now return a name. The official SUB-057 through SUB-066 score was not rerun.

### T-042 — Score a correct refusal in its own column
- Owner: @ai-engineer
- Requested by: @user
- Status: DONE
- Priority: P0
- Depends on: T-041
- Reviewers: @model-risk
- Acceptance criteria:
  - [x] The column is correctly flagged for human
  - [x] A refusal with both sides stored is not a hit and not a miss
  - [x] Picking one side of a real disagreement is a miss
  - [x] The file existed before SUB-067 through SUB-076
- Output: underwriting_pipeline/ai/eval_holdout_067.py
- Notes: D-016. A loop variable shadowed a helper. That name was changed before any score file existed. The scoring rules were not changed after that.

### T-043 — Gold answers for hold-out SUB-067 through SUB-076
- Owner: @senior-underwriter
- Requested by: @user
- Status: DONE
- Priority: P0
- Depends on: T-041, T-042
- Reviewers: @model-risk
- Acceptance criteria:
  - [x] One expected answer per submission, written before the score ran
  - [x] Same difficulty as SUB-057 through SUB-066, with new fictional risks
  - [x] None of the answers is an automatic decline
- Output: deliverables/senior-underwriter/gold-set/SUB-067.md through SUB-076.md
- Notes: Written 2026-10-10 before the completed eval_holdout_067.py run.

### T-044 — Score hold-out SUB-067 through SUB-076
- Owner: @model-risk
- Requested by: @user
- Status: IN_REVIEW
- Priority: P0
- Depends on: T-042, T-043
- Reviewers: @ai-engineer-assistant, @senior-underwriter
- Acceptance criteria:
  - [x] Scored after extraction was frozen
  - [x] A null that matches missing is not counted as correct
  - [x] Correct refusals are in the flagged column
  - [x] Compared with the SUB-057 through SUB-066 baseline
  - [x] The score comes from a successful model call
- Output: deliverables/ai-engineer/evals/SUB-067-076-holdout.md, deliverables/model-risk/holdout-SUB-067-076.md
- Notes: 2026-10-10. Not a production approval. Named insured 9/10. Premises 4 hit, 5 miss, 1 flagged. Loss runs 7 hit, 0 miss, 2 not credited, 1 flagged. 2026-10-11, @pm, round wrap-up, recorded as the reviewers wrote it: @senior-underwriter, REVIEW, "Verdict: APPROVE WITH CHANGES." "High-1: the same as T-039 High-1." @ai-engineer-assistant, REVIEW, "Verdict: APPROVE. No High." "Criterion 1: no commit shows the freeze (B-045); nothing I read contradicts it." No box was shown to fail. The change is a dated line that @model-risk adds to deliverables/model-risk/holdout-SUB-067-076.md: T-090. Stays IN_REVIEW until T-090 is done and @senior-underwriter has looked again. High finding: B-146. Medium and Low: B-042, B-053, B-054. Quoted only with "8 of 9 fields scored; loss runs = date only" (D-033 item 5). @pm gives no verdict.

### T-045 — Account manager may approve when the rules pass
- Owner: @software-engineer
- Requested by: @user
- Status: DONE
- Priority: P0
- Depends on: —
- Reviewers: @senior-underwriter
- Acceptance criteria:
  - [x] approve() and send_to_carrier() accept account-manager
  - [x] That actor must write a reason and pass complete, appetite, no open conflict, and no unread page
  - [x] The user can still send without those checks
  - [x] An AI role name is refused
- Output: underwriting_pipeline/ai/prepare.py, underwriting_pipeline/app/package.py
- Notes: D-017. Self-checks printed prepare ok and package ok. Nothing was sent.

### T-046 — Premises miss analysis for SUB-067 through SUB-076
- Owner: @ai-engineer-assistant
- Requested by: @user
- Status: DONE
- Priority: P0
- Depends on: T-044
- Reviewers: @senior-underwriter, @model-risk
- Acceptance criteria:
  - [x] Each premises miss shows the gold address, the extracted value, the source document, and a likely cause
  - [x] Causes are grouped
  - [x] A proposal covers the largest group
  - [x] No extraction, prompt, OCR, model, or eval file was edited for this task
- Output: deliverables/ai-engineer/premises-misses-SUB-067-076.md
- Notes: D-017. Four misses are OCR. One is two locations. P-001 was approved afterward as D-018.

### T-047 — Drop a premises value that has no ZIP
- Owner: @ai-engineer-assistant
- Requested by: @user
- Status: DONE
- Priority: P0
- Depends on: T-046
- Reviewers: @model-risk, @senior-underwriter
- Acceptance criteria:
  - [x] A premises value with no five-digit ZIP is cleared
  - [x] The source page is added to needs human read
  - [x] A premises value that already has a five-digit ZIP is kept
  - [x] The loss-run date in the self-check is unchanged
  - [x] The published SUB-067 through SUB-076 score file was not rerun
- Output: underwriting_pipeline/ai/prepare.py
- Notes: D-018. Self-check printed prepare ok. The workbench already shows needs human read.

### T-048 — Write proposals P-002 through P-005
- Owner: @ai-engineer-assistant
- Requested by: @user
- Status: DONE
- Priority: P0
- Depends on: T-046
- Reviewers: @senior-underwriter, @model-risk
- Acceptance criteria:
  - [x] Each proposal has a trade-off, the risk to the loss-run no-guess rule, and an expected score impact
  - [x] None of P-002 through P-005 is implemented
- Output: deliverables/ai-engineer/proposals-P-002-P-005.md
- Notes: Waiting on the user to approve a P-id, or not.

### T-049 — Store labeled locations with one primary
- Owner: @ai-engineer-assistant
- Requested by: @user
- Status: DONE
- Priority: P0
- Depends on: T-048
- Reviewers: @senior-underwriter, @model-risk
- Acceptance criteria:
  - [x] Main and second premises become a location list with one primary
  - [x] That case does not leave a premises conflict
  - [x] The primary address stays in the premises field
  - [x] Two unlabeled addresses are not turned into locations
  - [x] A loss-run date in the self-check is unchanged
- Output: underwriting_pipeline/ai/prepare.py, underwriting_pipeline/app/workbench.py
- Notes: D-019. Self-checks printed prepare ok and workbench ok.

### T-050 — Compare EasyOCR with Tesseract
- Owner: @ai-engineer-assistant
- Requested by: @user
- Status: DONE
- Priority: P0
- Depends on: T-048
- Reviewers: @model-risk
- Acceptance criteria:
  - [x] One free local engine was timed against Tesseract
  - [x] Accuracy and seconds per page are reported
  - [x] The live reader was not switched
- Output: deliverables/ai-engineer/ocr-compare-tesseract-easyocr.md
- Notes: D-019. EasyOCR is slower. It is not a clear replacement. Tesseract stays.

### T-051 — Rewrite the confidence proposal as P-003b
- Owner: @ai-engineer-assistant
- Requested by: @user
- Status: DONE
- Priority: P1
- Depends on: —
- Reviewers: @model-risk
- Acceptance criteria:
  - [x] OCR confidence is limited to scanned pages in the proposal
  - [x] Typed PDF, Excel, and email keep the current path
  - [x] The proposal is not implemented
- Output: deliverables/ai-engineer/proposal-P-003b.md
- Notes: D-019. Waiting on the user.

### T-052 — Gold answers for hold-out SUB-077 through SUB-086
- Owner: @senior-underwriter
- Requested by: @user
- Status: DONE
- Priority: P0
- Depends on: T-049, T-050
- Reviewers: @model-risk
- Acceptance criteria:
  - [x] One expected answer per submission, written before the score ran
  - [x] Same difficulty as the previous hard set, with new fictional risks
  - [x] None of the answers is an automatic decline
- Output: deliverables/senior-underwriter/gold-set/SUB-077.md through SUB-086.md
- Notes: Written 2026-10-10 before eval_holdout_077.py ran.

### T-053 — Score hold-out SUB-077 through SUB-086
- Owner: @model-risk
- Requested by: @user
- Status: IN_REVIEW
- Priority: P0
- Depends on: T-052
- Reviewers: @ai-engineer-assistant, @senior-underwriter
- Acceptance criteria:
  - [x] Scored after P-005 and the OCR report, with no further code changes
  - [x] Compared with the SUB-067 through SUB-076 baseline
  - [x] A null that matches missing is not counted as correct
  - [x] The score comes from a successful model call
- Output: deliverables/ai-engineer/evals/SUB-077-086-holdout.md, deliverables/model-risk/holdout-SUB-077-086.md
- Notes: 2026-10-10. Not a production approval. Premises 5 hit, 4 miss, 1 flagged. Year built 7/10. Loss runs 6 hit, 1 miss, 2 not credited, 1 flagged. 2026-10-11, @pm, round wrap-up, recorded as the reviewers wrote it: @senior-underwriter, REVIEW, "Verdict: APPROVE WITH CHANGES." High-1 is the same memo line as T-039. "High-2: effective date is one of the nine extracted fields, completeness requires it, and no hold-out has ever scored it." @ai-engineer-assistant, REVIEW, "Verdict: APPROVE. No High." "Criterion 1: no commit shows it (B-045)." No box was shown to fail. High-1 is a dated line that @model-risk adds to deliverables/model-risk/holdout-SUB-077-086.md: T-090. High-2: the gold of the new 20-file hold-out gets an Effective date line and a claims line, T-092; the quoted-score wording is the user's, "8 of 9 fields scored; loss runs = date only" (D-033 item 5). Stays IN_REVIEW until T-090 is done and @senior-underwriter has looked again. High findings: B-147, B-148. Medium and Low: B-043, B-044, B-055. @pm gives no verdict.

### T-054 — Regression of SUB-017 through SUB-076 before P-002 and P-003b
- Owner: @ai-engineer-assistant
- Requested by: @user
- Status: DONE
- Priority: P0
- Depends on: T-049
- Reviewers: @model-risk
- Acceptance criteria:
  - [x] Current code scored on SUB-017 through SUB-076
  - [x] Compared with the published scores, field by field
  - [x] Official score files were not overwritten
- Output: deliverables/ai-engineer/evals/regression-SUB-017-076-before-P002-P003b.json, deliverables/ai-engineer/evals/regression-SUB-017-076.md
- Notes: D-020. The process imported the code before P-002 and P-003b were saved.

### T-055 — Implement P-003b
- Owner: @ai-engineer-assistant
- Requested by: @user
- Status: DONE
- Priority: P0
- Depends on: T-054
- Reviewers: @model-risk
- Acceptance criteria:
  - [x] Scanned pages use the Tesseract word score as the gate
  - [x] Typed PDF, Excel, and email keep the model confidence
  - [x] Both numbers show in the workbench
  - [x] Self-checks passed
- Output: underwriting_pipeline/ai/sources.py, underwriting_pipeline/ai/llm_extract.py, underwriting_pipeline/app/workbench.py
- Notes: D-020. Frozen scorers were not edited.

### T-056 — Implement P-002 as a flag only
- Owner: @ai-engineer-assistant
- Requested by: @user
- Status: DONE
- Priority: P0
- Depends on: T-054
- Reviewers: @senior-underwriter, @model-risk
- Acceptance criteria:
  - [x] A bad ZIP or a ZIP that does not match the city is marked address invalid
  - [x] The original text is kept
  - [x] No city is rewritten and no ZIP is invented
  - [x] Self-check passed
- Output: underwriting_pipeline/ai/prepare.py, underwriting_pipeline/ai/texas_zip_city.tsv
- Notes: D-020. Texas rows are from GeoNames, CC-BY 4.0.

### T-057 — Proposal P-006
- Owner: @ai-engineer-assistant
- Requested by: @user
- Status: DONE
- Priority: P1
- Depends on: T-050
- Reviewers: @model-risk
- Acceptance criteria:
  - [x] EasyOCR is described only as a fallback
  - [x] Expected accuracy and speed are stated from the existing comparison
  - [x] The live reader was not changed
- Output: deliverables/ai-engineer/proposal-P-006.md
- Notes: D-020. Waiting on "approve change P-006". Not implemented.

### T-058 — Regression after P-002 and P-003b
- Owner: @ai-engineer-assistant
- Requested by: @user
- Status: CANCELLED
- Priority: P0
- Depends on: T-055, T-056
- Reviewers: @model-risk
- Acceptance criteria:
  - [ ] SUB-017 through SUB-076 scored again after the approved edits
  - [ ] Any field whose hit count drops is reported
  - [ ] The before file is kept
- Output: deliverables/ai-engineer/evals/regression-SUB-017-076-after-P002-P003b.json
- Notes: D-020, D-022. The full run was stopped. Under D-022 the check after a change is the quick set in T-064, and the full 60 run at the next milestone. Official hold-out files are not rewritten. 2026-10-11: cancelled by @pm. D-022 item 4 amended D-020 item 8, so the check after P-002 and P-003b is T-064. No after file was written. The before file from T-054 is kept. The full 60 gets a new task at the next milestone.

### T-059 — Status "extraction_failed" for a failed or empty model call
- Owner: @ai-engineer-assistant
- Requested by: @user
- Status: DONE
- Priority: P0
- Depends on: —
- Reviewers: @model-risk, @software-engineer, @account-manager
- Acceptance criteria:
  - [x] A failed call and a call with no fields both get the status and the error
  - [x] The workbench shows it
  - [x] No send is allowed for that file, and no missing-information request is drafted
  - [x] Every scorer counts call failed apart from a miss
  - [x] Self-checks passed
- Output: underwriting_pipeline/ai/prepare.py, underwriting_pipeline/app/package.py, underwriting_pipeline/app/workbench.py, underwriting_pipeline/ai/eval_gold.py, underwriting_pipeline/ai/eval_holdout*.py
- Notes: D-021. The scorers were edited only to add the call-failed count. No hit or miss rule was changed. 2026-10-11, @pm, recorded as the reviewers wrote it: @model-risk, OBJECTION, "Verdict: NOT APPROVED. Criteria 1 and 5 pass. Criteria 3 and 4 fail." @software-engineer, REVIEW, "Verdict: REJECT", criterion 3 fails. @account-manager, REVIEW, "Verdict: REJECT", criterion 3 fails. Boxes 3 and 4 are unticked for that reason. The veto is open. The fix is P-010, approved by the user in D-029 with G2, D1, S1, C1, no Low-2, and not built yet: T-069 (@data-engineer, the saved-file keys), T-070 (@ai-engineer-assistant, prepare.py and eval_holdout.py), T-071 (@software-engineer, package.py and workbench.py). This task stays IN_REVIEW until T-070 and T-071 are in and all three reviewers have looked again. P-010 uses a different mechanism from the one @model-risk wrote, so @model-risk must say whether it resolves the veto. @pm gives no verdict. 2026-10-11, @pm, round wrap-up: no new verdict. The veto and the two REJECTs are open. @compliance's T-020 finding H2 is the same gap seen from `package.py`. Line 1 of team/DEMO-BLOCKERS.md. 2026-10-13, @pm, board maintenance: set DONE, criteria 3 and 4 ticked, veto recorded as lifted. All three reviewers looked again and APPROVE, every earlier REJECT/OBJECTION resolved: @model-risk at team/DISCUSSION.md:2240, "@model-risk LOOK-AGAIN. Verdict: APPROVE. Criteria 3 and 4 are now met, and my T-059 veto is LIFTED"; @software-engineer at :2272, "APPROVE — my earlier REJECT (:1207) is RESOLVED"; @account-manager at :2287, "APPROVE — my earlier REJECT (:1219) is RESOLVED". The condition @model-risk set at :2018 (T-071 lands with the four-actor refusal and its self-checks) is met by `dd45467`. **The T-059 veto is LIFTED** by @model-risk, the holder. This lifts no other veto (T-017, T-020, T-027) and authorizes no send; an approved P-010 is not a production approval. Carried Medium/Low routed to team/BACKLOG.md per D-030: B-174, B-175, B-176, B-177; the card-flag finding is already B-166/B-170, and the earlier Low-2 is already B-001, not duplicated. Line 1 of team/DEMO-BLOCKERS.md is closed by this verdict set. No verdict from @pm.

### T-060 — Score SUB-077 through SUB-086 again with the retry
- Owner: @ai-engineer-assistant
- Requested by: @user
- Status: IN_REVIEW
- Priority: P0
- Depends on: T-059
- Reviewers: @model-risk
- Acceptance criteria:
  - [x] Scored again with the retry and no extraction change
  - [x] The original score and the rerun are both in the memo
  - [x] The original is replaced only if one of its calls failed
- Output: deliverables/ai-engineer/evals/SUB-077-086-holdout-rerun.md, deliverables/ai-engineer/evals/SUB-077-086-holdout-original.md, deliverables/ai-engineer/evals/SUB-077-086-original-vs-rerun.md
- Notes: D-021. The original run saved no error and every file returned a name, so the original stays the published score. The rerun finished 2026-10-10: 10 calls, 0 failed. Three files changed marks with no failed call (SUB-080, SUB-081 up, SUB-084 operations down). P-002 and P-003b were in the code for the rerun, so it is not a clean repeat. For @model-risk to review. 2026-10-11, after @model-risk's APPROVE WITH CHANGES and D-026: the memo and the rerun file are corrected. The rerun is labeled "with P-002 and P-003b, not a same-code comparison", is not an improvement, and the original is the official baseline. The count is 10 marks, 9 up and 1 down. The false @model-risk header is off the rerun file. "10 on the first attempt, 429: 0" is withdrawn: no saved file holds it. Criterion 1 is not met as worded ("no extraction change"); D-026 accepts the rerun as-is for this rerun only. Status left at IN_REVIEW for @model-risk and @pm. 2026-10-11, D-028: the Author line of the rerun .md now names @ai-engineer-assistant. The published file and its -original copy still name the retired handle and were not touched (D-025). 2026-10-11, @pm: @model-risk, REVIEW, "Verdict: APPROVE WITH CHANGES. No High." D-026 is the user's ruling on its Medium-1. The owner reports the corrections made. @model-risk has not looked again, so this is not closed. D-026 follow-ups: this task and T-073 (P-012). 2026-10-11, @pm, round wrap-up: @model-risk has not posted a second look. Not closed. T-062 (P-006) waits on it.

### T-061 — Count failed calls by cause and pace the calls
- Owner: @ai-engineer-assistant
- Requested by: @user
- Status: IN_PROGRESS
- Priority: P0
- Depends on: T-059, T-064
- Reviewers: @model-risk, @ml-engineer
- Acceptance criteria:
  - [x] Each failed attempt is saved as rate limit 429, timeout, other, or reply_not_usable (fourth cause added by D-028)
  - [x] Calls wait for the per-minute token budget, and a 429 waits as long as the host asks
  - [ ] The counts from T-060 and from the quick-set run in T-064 are reported
- Output: underwriting_pipeline/ai/llm_extract.py, underwriting_pipeline/ai/regression_dev.py
- Notes: D-021. The host allows 8,000 tokens a minute, 200,000 tokens a day, and 1,000 requests a day. The daily token limit was reached on 2026-10-10. Pacing cannot raise a daily limit. T-060 count: 0 failed of 10. T-058 was stopped under D-022, so its count comes from T-064. 2026-10-11: @pm reworded the last criterion because T-058 is cancelled. The quick-set count is one count for each of the three runs in T-066. 2026-10-11: the T-060 count "0 failed of 10" is backed only at file level (every row `error: null`, `attempts: 1` in the rerun JSON). The count of 429s and retries inside those calls was not saved and is "not recorded" (D-026). P-012 is in the code: from now on every 429, timeout, other failed attempt, and retry is a row in `underwriting_pipeline/cache/token_log.jsonl`, and each reply row has `attempts`. The quick-set counts for T-066 will come from that file. 2026-10-11, D-028: `reply_not_usable` is now counted in the failure totals as its own cause. `regression_dev.py` prints and saves four counts, each shown even at 0: rate_limit_429, timeout, other, reply_not_usable. Self-check extended and passed, no model call. The first criterion's wording names three causes; there are now four. 2026-10-11, @pm: first criterion reworded for D-028. The token-log rows are reviewed under T-073 (P-012) and the fourth count under T-075 (D-028). The last criterion waits on T-066. 2026-10-11, @pm, D-030: P-006 now comes before the variance test, and D-021 item 4 wants this task done before P-006. So the last criterion now takes its quick-set count from T-064, which runs before P-006. The counts for the three variance runs are reported in T-066.

### T-063 — Implement P-007, the extraction cache
- Owner: @ai-engineer-assistant
- Requested by: @user
- Status: IN_REVIEW
- Priority: P0
- Depends on: T-059
- Reviewers: @model-risk, @ml-engineer
- Acceptance criteria:
  - [x] The key is the file contents, the prompt version, the OCR settings, and the model name
  - [x] The same key does not call the model twice
  - [x] A failed or empty call is not saved and is called again
  - [x] Tokens are logged for each call and each run
  - [x] Self-check passed
- Output: underwriting_pipeline/ai/llm_extract.py, underwriting_pipeline/ai/sources.py, underwriting_pipeline/cache/
- Notes: D-022. The key also holds the text sent to the model, so a change in OCR output is a new key even if the OCR settings line was not updated. `python underwriting_pipeline/ai/llm_extract.py --budget` prints tokens for the last 24 hours. 2026-10-11: @model-risk APPROVE WITH CHANGES. Medium-1 is fixed by P-013 (D-027): the result is written to a temp file and renamed, and an unreadable saved file counts as not saved and is called again. Self-check extended and passed, no model call. Record: deliverables/ai-engineer/proposal-P-013.md. Medium-2 is in P-010, not approved, not touched. The Low points are open. Needs @model-risk to look again. 2026-10-11, D-028: leftover `.tmp` files are removed at the first extraction of each run, only files named `<key>.json.<process id>.tmp` in the cache folder in use, never a saved result; one under a minute old is left for the next run. Self-check extended and passed. @ml-engineer's review: APPROVE WITH CHANGES; its two Medium findings on the token log are P-014 (deliverables/ai-engineer/proposal-P-014.md), a proposal only, not implemented. 2026-10-11, @pm, recorded as written: @model-risk, REVIEW, "Verdict: APPROVE WITH CHANGES. Not a production approval. No High finding." @ml-engineer, REVIEW, "Verdict: APPROVE WITH CHANGES. No High." Neither has looked again, so this is not closed. @model-risk Medium-1 is P-013, built, reviewed under T-074. @model-risk Medium-2 is the D-024 case, in P-010 (T-070; the user chose C1, the reply stays in the cache). @ml-engineer Medium-1 and Medium-2 are P-014, which is a proposal only, not approved, and has no task. The Low points of both reviews are open with no owner decision. 2026-10-11, @pm, D-030: the Medium and Low findings of both reviews that no approved proposal covers are in team/BACKLOG.md, B-002 through B-013, for after the demo. Whether that changes a reviewer's verdict is the reviewer's to say. 2026-10-11, @pm, round wrap-up: neither reviewer has posted a second look. Not closed. This replaces "P-014 is not approved" above: the user approved P-014 in D-033 ("approve change P-014 with U1 R2 H1 O1 L1 T2 S1 G1"). The build is T-078.

### T-064 — Quick regression set of 15 files
- Owner: @ai-engineer-assistant
- Requested by: @user
- Status: IN_PROGRESS
- Priority: P0
- Depends on: T-065, T-078
- Reviewers: @model-risk
- Acceptance criteria:
  - [x] 15 development files: text PDF, scan, Excel, email, Spanish, conflicts, and missing loss runs
  - [ ] Scored once after P-002 and P-003b, and any field that drops is reported
- Output: underwriting_pipeline/ai/regression_dev.py, deliverables/ai-engineer/evals/regression-quick-15-after-P002-P003b.json
- Notes: D-022. SUB-027, 029, 038, 042, 044, 050, 051, 053, 056, 067, 070, 071, 073, 074, 076. Run with `--quick`. This replaces the full run for T-058. The full 60 run at the next milestone. 2026-10-11: not run. The token budget is free (20,950 of 200,000 used in 24 hours) but LLM_API_KEY, LLM_BASE_URL, and LLM_MODEL for Groq are not set in the shell. Needs the user. 2026-10-11, @pm: the user set the Groq variables (D-023). Runs after the provider guard, T-065. Its score is run 1 of T-066, the one run that is cached, because the code already holds P-002 and P-003b and already sends temperature 0. If T-065 or T-066 changes what the model returns, say so in the memo and do not use run 1 for this task. 2026-10-11, @pm, D-030: this is no longer run 1 of T-066, because the variance test now comes after P-006. Run it on its own, next, with its output path given on the command line. It is the baseline before P-006 that T-068 compares against, it is the quick-set check after P-012, P-013, and the D-028 follow-ups (D-022 item 4), and its results are saved so the checks after P-010 and P-011 need no new call. Report the four failure counts from the token log (T-061). 2026-10-11, @pm: D-031 item 2: P-014's "cache-key change lands before the T-064 baseline". So this run follows T-078, and "Depends on" now names T-078. T-063 is taken off "Depends on": the cache it built is in the code, and T-063 cannot close before P-014 is built, which would have been a circle. D-034: the code is committed before this run and the commit hash is written in the memo. The score file cannot carry the hash until P-017 (T-088) is approved and built; say so in the memo. Who makes the commit is not a role's to decide: ask @user. All 15 calls are fresh, because the new key does not reach the 13 saved results.

### T-062 — Implement P-006
- Owner: @ai-engineer-assistant
- Requested by: @user
- Status: BLOCKED
- Priority: P0
- Depends on: T-059, T-060, T-061, T-064, T-070, T-071, T-072
- Reviewers: @model-risk, @senior-underwriter
- Acceptance criteria:
  - [ ] EasyOCR runs only on a scanned page whose address fails validation or whose Tesseract score is under 0.75
  - [ ] The fallback cannot create a loss-run date that Tesseract did not show
  - [ ] The regression runs again and any field that drops is reported (the run is T-068)
- Output: underwriting_pipeline/ai/sources.py
- Notes: D-021, D-022. Approved. Not started. Waits on T-060 and T-064. 2026-10-11, @pm: D-023 item 6 puts P-006 after the provider guard, the three runs, and the name-swap test. D-021 item 4 still holds: T-059, T-060, and T-061 must be done first, and T-059 and T-060 have no review verdict yet. 2026-10-11, @pm: T-059 has an open veto. It can be resolved only after T-070 and T-071 are built and the three T-059 reviewers have looked again. P-006 does not start before that. T-072 (P-011) also goes before this task, so the T-068 run writes to the scratch folder. 2026-10-11, @pm, D-030: "P-006, variance test, fairness test, then demo prep". T-066 and T-067 are no longer in front of this task; they follow it. 2026-10-11, @pm: T-072 added to "Depends on", as D-029's order and the note above already say. Priority raised to P0: it is the first goal in D-030 and T-066 (P0) waits on it. 2026-10-11, @pm, D-037: the new hold-out is scored only after extraction is frozen, so this task goes before the freeze (T-091 to T-093 follow it). It goes after the P-016 build, one extraction change at a time, so the quick set can tie a drop to one change (D-022 item 4). It is not a line in team/DEMO-BLOCKERS.md. D-034: commit before the T-068 run.

### T-065 — Implement P-008, the provider guard
- Owner: @ai-engineer-assistant
- Requested by: @user
- Status: IN_REVIEW
- Priority: P0
- Depends on: —
- Reviewers: @model-risk, @compliance, @ml-engineer
- Acceptance criteria:
  - [x] The pipeline never loads `.env` for LLM settings
  - [x] It prints the provider URL and the model name at the start of every eval or extraction run
  - [x] It refuses to run if LLM_BASE_URL is not the expected Groq URL, unless the user sets ALLOW_PROVIDER=<name> (built as amended on D-023: Groq or localhost is allowed, any other host is refused unless ALLOW_PROVIDER is set)
- Output: underwriting_pipeline/ai/llm_extract.py, underwriting_pipeline/ai/regression_dev.py
- Notes: D-023 item 2. The user typed "approve change P-008". Runs first: no eval or extraction run starts before it. Never print or write a key (D-011). Today `endpoint_settings()` falls back to a local Ollama URL when LLM_BASE_URL is unset, and the self-check removes LLM_BASE_URL. Report how both behave under the guard. Do not widen the rule. Frozen scorers are not edited. Not a production approval. 2026-10-11, @ai-engineer-assistant: built to the user's amendment on D-023. `provider_guard()` in `llm_extract.py` runs at the start of every extraction, before the cache, and at the start of `regression_dev.py`. A refusal stops the run with exit 1; it is not stored as extraction_failed. `endpoint_settings()` and its Ollama default are unchanged and allowed. The old self-check lines still pass. Self-check: `python underwriting_pipeline/ai/llm_extract.py` prints `llm gate ok`. No model call was made. The prompt version is unchanged (82be09bd42f7), so the cache keys are unchanged. Open for the reviewers and the user: any non-empty ALLOW_PROVIDER value allows any host, the name is printed but not matched to the URL; a run from saved results only is refused too on another host; the workbench server uses threads, so a refusal there ends the request, not the server (not tested); `prepare.py` line 4 still names OPENAI_API_KEY in a comment, no code reads it. Not a production approval. 2026-10-11, @ai-engineer-assistant, second amendment on D-023 ("ALLOW_PROVIDER must name the exact allowed host; cache-only runs with zero model calls skip the guard"): built. This replaces the two open points above about ALLOW_PROVIDER and saved results. ALLOW_PROVIDER lets a host through only when it equals the host name in LLM_BASE_URL (for `https://api.openai.com/v1` that is `api.openai.com`); any other value is refused. The refusal now happens inside `llm_extract()` just before the model call, after the cache lookup, so a result that is saved is used and a result that is not saved stops the run with exit 1 before the call. `regression_dev.py` still prints the host and model first and no longer refuses at the start. A refused host with no key or no model still stops with the refusal. Groq and localhost are unchanged. Self-check `python underwriting_pipeline/ai/llm_extract.py` prints `llm gate ok` and covers: exact host allowed, five wrong values refused, cache-only on a refused host with 0 model calls, an uncached file on a refused host stopped. No model call was made; prompt version 82be09bd42f7 and the cache keys, token log, and 13 saved results are unchanged. Left open by the wording, for the user: (a) the value is matched to the host name only, so a port, the scheme, or the full URL in ALLOW_PROVIDER is refused, and one allowed host name covers any port and path on it; (b) the match is case-sensitive against the lower-case host name; (c) a run that is partly cached uses the saved results and stops at the first file that needs a call, and the full 60 run has by then written its finished bands to its report file. Mistake this turn, fixed: to show a cache-only run I ran `regression_dev.py --holdout eval_holdout_077` on a refused test host; it made 0 model calls but the scorer wrote over the published `SUB-077-086-holdout.json` and `.md`. I restored both from the last commit and they match it again. That scorer writes to the published path on every run; that is not changed here. Not a production approval.

### T-066 — P-009: temperature 0 and three runs of the quick set
- Owner: @ai-engineer-assistant
- Requested by: @user
- Status: TODO
- Priority: P0
- Depends on: T-065, T-062, T-068, T-093
- Reviewers: @model-risk, @data-scientist
- Acceptance criteria:
  - [ ] Temperature is 0
  - [ ] The quick 15-file set runs 3 times on openai/gpt-oss-120b with fresh calls
  - [ ] Only the first run is cached
  - [ ] Each field's mean and min–max are reported
- Output: deliverables/ai-engineer/evals/variance-quick-15-run1.json, deliverables/ai-engineer/evals/variance-quick-15-run2.json, deliverables/ai-engineer/evals/variance-quick-15-run3.json, deliverables/ai-engineer/evals/variance-quick-15.md
- Notes: D-023 item 4. The user typed "approve change P-009". R-014. `llm_extract.py` already sends `"temperature": 0`, so confirm it on every call path and say in the memo whether P-009 changed any code. The cache key holds the prompt version, the model, and the files, not the temperature, and a saved result is not a fresh call: all 45 calls must reach the model. A failed call is counted apart in each run and is not a miss (D-021). About 1,600 tokens a call so far, so about 73,000 of the 200,000 a day. Run 1 is also the T-064 score. Frozen scorers are not edited. No published hold-out score is rewritten. Not a production approval. 2026-10-11, @pm, D-030: the variance test now runs after P-006 (T-062) and its quick-set rerun (T-068). Run 1 is not the T-064 score; T-064 runs on its own before P-006. The three runs measure the code with P-006, P-010, P-011, P-012, and P-013 in it; say so in the memo. Report the four failure counts for each run from the token log. Give every output file its own path; do not run a scorer's main against a published path (D-025). 2026-10-11, @pm: the three runs follow the new hold-out score (T-093), so the code they measure is the frozen code the demo shows, P-016 included if the user approves it. T-063 is taken off "Depends on" for the reason given on T-064. D-034: commit first; the hash goes in each run file and the memo. Every quoted field says "8 of 9 fields scored; loss runs = date only" (D-033 item 5).

### T-067 — Name-swap counterfactual test on cached extractions
- Owner: @data-scientist
- Requested by: @user
- Status: TODO
- Priority: P0
- Depends on: T-066, T-083
- Reviewers: @responsible-ai, @model-risk, @compliance
- Acceptance criteria:
  - [ ] The test runs on cached extractions
  - [ ] No model calls
  - [ ] The risk score does not change
  - [ ] The carrier match does not change
- Output: deliverables/data-scientist/name-swap-test.py, deliverables/data-scientist/name-swap-test.md
- Notes: D-023 item 5. R-002. Uses the extractions saved by run 1 of T-066. The memo lists every name swapped and the score and match before and after, file by file. If either one changes, report the file and the cause and stop: do not edit `underwriting_pipeline/models/points.py`, the match rules, the extraction, or a scorer. A fix would need a decision. Synthetic data only. Not a production approval. 2026-10-11, @pm, D-030: this is the fairness test in the user's order. It still follows T-066, which now follows P-006. 2026-10-11, @pm: @responsible-ai's veto on T-017 asks for a response "before T-067". This test measures the score and the match, so it runs after the carrier match rules (T-083) and after the P-015 build, if the user approves P-015; its build task is made on approval and is then added here. If P-015 is not approved when this task is reached, stop and ask @user. @responsible-ai, B-065: "The T-067 name-swap test should include a name that contains a trigger word."

### T-068 — Quick-set rerun after P-006
- Owner: @ai-engineer-assistant
- Requested by: @user
- Status: TODO
- Priority: P0
- Depends on: T-062
- Reviewers: @model-risk, @senior-underwriter
- Acceptance criteria:
  - [ ] The quick 15-file set is rerun after P-006
  - [ ] Any field whose hit count drops is reported
- Output: deliverables/ai-engineer/evals/regression-quick-15-after-P006.json, deliverables/ai-engineer/evals/regression-quick-15-after-P006.md
- Notes: D-023 item 6, D-022 item 4, D-020 item 8. Compare with run 1 of T-066 and show each field against the T-066 min–max. This is the run T-062's third criterion names. The T-066 files are not overwritten. Not a production approval. 2026-10-11, @pm, D-030: T-066 now runs after this task, so there is no run 1 and no min–max to compare with yet. Compare with the T-064 baseline, field by field. The spread comes later from T-066. Priority raised to P0 with T-062. 2026-10-11, @pm: D-034: commit before this run and write the hash in the memo. Compare with the last quick-set run before P-006, which is the one after the P-016 build if there is one, otherwise T-064.

### T-069 — Saved extraction file: keys for status, error, and the file hash
- Owner: @data-engineer
- Requested by: @user
- Status: DONE
- Priority: P0
- Depends on: —
- Reviewers: @compliance, @software-engineer
- Acceptance criteria:
  - [x] @data-engineer says yes or no to new keys in `deliverables/data-engineer/extractions/SUB-xxx.json`: `status`, `error`, the hash saved with the status, and the rest of the report that the G2 gate reads
  - [x] If the answer is no, another place is named
  - [x] @compliance is consulted
  - [x] The data model document lists the keys and says who writes them
- Output: deliverables/data-engineer/data-model.md, and an ANSWER in team/DISCUSSION.md
- Notes: D-029, D-024. The proposal's "Files and owners" table: "@data-engineer says yes or names another place". The file is written by `prepare.write_drafts()`. The schema is @data-engineer's decision; record it in team/DECISIONS.md if it names another place. D-029: "G2 must also compare the file's current hash with the hash saved with its status and refuse if they differ." No code is changed in this task. Synthetic data only. T-070 waits on this answer. 2026-10-13, @pm, board maintenance: set DONE. Both reviewers returned APPROVE. @compliance APPROVE at team/DISCUSSION.md:1996 (all four criteria met; earlier High `saved_hash` RESOLVED) and @software-engineer APPROVE at :2008 (both earlier High findings RESOLVED; key table matches what T-070 built). All four criteria ticked on the two verdicts. Residual Medium/Low parked: @compliance Medium-1/Medium-2/Low are B-163/B-164/B-165 (already on file); @software-engineer Medium-1 (Reader contract vs omitted display keys) is B-166. No verdict from @pm; no send authorized.

### T-070 — Implement P-010, the ai part: send gate in prepare.py, all_values_rejected, and the SUB-017–026 scorer
- Owner: @ai-engineer-assistant
- Requested by: @user
- Status: DONE
- Priority: P0
- Depends on: T-069
- Reviewers: @model-risk, @software-engineer, @account-manager, @compliance
- Acceptance criteria:
  - [x] `prepare.approve()` and the command line `--approve` refuse `extraction_failed` and `all_values_rejected` "for every actor including user"
  - [x] G2: the gate reads "the file's current status" itself from the last saved run, never trusts a passed-in report, and refuses when nothing is saved
  - [x] "G2 must also compare the file's current hash with the hash saved with its status and refuse if they differ"
  - [x] D1: when a run ends in either status, the old draft in `simulation/pending-approval/` is removed, the conflict file is kept, and the status and the error are saved
  - [x] D-024: a reply whose values are all rejected gets file status `all_values_rejected`, gets no missing-information request, goes to human review, and is never sendable. A call that failed or returned nothing stays `extraction_failed`
  - [x] S1: an all_values_rejected file is scored with the rules already in each scorer. Only `eval_holdout.py` is edited: the call-failed count, and failed files out of the denominator. No hit rule and no gold file changes
  - [x] C1: an all-rejected reply stays in the cache. `llm_extract.py` is not changed by this task
  - [x] Low-2 is not added
  - [x] "a self-check for each case", as listed in Part 4 of the proposal for the ai files, with no model call and no score file written
  - [x] The quick set of 15 is run after the change to a scratch path, and any field that drops is reported
- Output: underwriting_pipeline/ai/prepare.py, underwriting_pipeline/ai/eval_holdout.py, deliverables/ai-engineer/proposals-P-010-P-011.md (what was built)
- Notes: D-029, D-024. The user typed "approve change P-010 with G2 D1 S1 C1, no Low-2". Covers the `underwriting_pipeline/ai/` files only. Goes before T-071, because the status reader lives in `prepare.py` and the two app files call it. If "the file's current hash" leaves a choice of what is hashed, state the choice in the memo and ask the user; do not pick silently. Published scores are not recounted. No scorer's main is run against its published path (D-025). No prompt, model, OCR, or gate rule changes. No send is authorized. T-059's veto is not resolved by this task alone. Not a production approval. 2026-10-11, @pm: line 1 of team/DEMO-BLOCKERS.md. D-034: commit before the quick-set run in the last box and write the hash in the memo. 2026-10-13, @pm, board reconciliation: set IN_REVIEW. The owner built the `underwriting_pipeline/ai/` part of P-010 this turn (the user's `approve change P-010`, D-043) and committed it (`fde95b7` code, `57bd138` follow-up, `449aabe` memo/handoff); handoff at team/DISCUSSION.md:1966. The owner's own status update did not land, so @pm set the status. No acceptance criterion is ticked here — the handoff and the code are left for the reviewers to judge. Reviewers: @model-risk, @software-engineer, @account-manager, @compliance. @model-risk also re-checks T-059 criterion 3 and whether P-010 resolves the T-059 veto. T-071 (@software-engineer) waits on this. No verdict from @pm; no send authorized; not a production approval. 2026-10-13, @pm, board maintenance: set DONE. All four reviewers returned APPROVE after the fail-closed fix (`140a373`, on `fde95b7`/`57bd138`): @model-risk APPROVE at team/DISCUSSION.md:2111, @software-engineer look-again APPROVE at :2079, @account-manager look-again APPROVE at :2089, @compliance look-again APPROVE at :2100. All ten criteria ticked on the verdicts (read as met, @software-engineer note at :2034; convergent Medium-1 reader fail-closed fix confirmed RESOLVED by all four). **The T-059 veto STAYS until T-071 lands and the three T-059 reviewers (@model-risk, @software-engineer, @account-manager) look again** — `package.send_to_carrier()`/`record_decision()` are T-071, not T-070; @model-risk (:2115), @account-manager (:2094), @compliance (:2108), @software-engineer (:2085) all concur. @compliance's T-020 veto also stays. Residual Medium/Low parked: display-keys/T-071 constraint (B-166), account-manager missing-info dead path (B-172), and Lows B-167–B-171, B-173. No verdict from @pm; no send authorized; not a production approval.

### T-071 — P-010, the app part: package.py and workbench.py
- Owner: @software-engineer
- Requested by: @user
- Status: DONE
- Priority: P0
- Depends on: T-070
- Reviewers: @model-risk, @account-manager, @senior-underwriter, @compliance
- Acceptance criteria:
  - [x] `send_to_carrier()` and `agency_problem()` call the status reader in `prepare.py` and refuse `extraction_failed` and `all_values_rejected` "for every actor including user"
  - [x] No passed-in report is trusted for the status. The send is refused when the status cannot be read, when nothing is saved, or when the hash differs
  - [x] "workbench hides approve on failed files": the card for either status shows no approve option, no Missing list, no carrier match, and no score
  - [x] `record_decision()` reads the status itself and refuses an approve for either status
  - [x] Edit and decline on such a card are decided by @software-engineer with @senior-underwriter and the choice is written in the notes
  - [x] "a self-check for each case", with no model call. `package ok` and `workbench ok` still pass
- Output: underwriting_pipeline/app/package.py, underwriting_pipeline/app/workbench.py
- Notes: D-029: "The `package.py` and `workbench.py` parts of P-010 are @software-engineer's and need a task from @pm." Proposal: deliverables/ai-engineer/proposals-P-010-P-011.md, Part 1 points 1, 2 and 4, Part 2, and Part 4. The user's override stays for every other block (D-017); there is none for these two statuses. No auto-decline: the card keeps the file for a person. No send is authorized. When this and T-070 are in, @model-risk, @software-engineer, and @account-manager look at T-059 again. Not a production approval. 2026-10-11, @pm: line 1 of team/DEMO-BLOCKERS.md. This is item (b) of what resolves @compliance's T-020 veto: the send "takes no report from the caller". Five more tasks follow in the same two files, in this order: T-079, T-081, T-083, T-085, T-086, T-087. 2026-10-13, @pm, board maintenance: set DONE. All four reviewers returned APPROVE on the landed code (`dd45467`, `package.py` and `workbench.py` only): @model-risk APPROVE at team/DISCUSSION.md:2148, @account-manager APPROVE at :2193, @senior-underwriter APPROVE at :2206 (criterion 5 confirmed as built at :2210 — keep both edit and decline), @compliance APPROVE at :2218. All six criteria ticked on the four verdicts. No new veto; an approved P-010 is not a production approval. Carried Medium/Low routed to team/BACKLOG.md per D-030: B-174 (the stubbed test still passes the removed `report=`), B-175 (`agency_problem` catches only `ValueError`), B-176 (no check that the saved payload's `submission` equals the id read), B-177 (no self-check for the forged-dict and mismatched-`submission` paths), B-178 (@senior-underwriter's refused-card decline-wording Low). The card-flag finding is already B-166/B-170; not duplicated. No verdict from @pm.

### T-072 — Implement P-011: published score files read-only, tests write to a scratch folder
- Owner: @ai-engineer-assistant
- Requested by: @user
- Status: TODO
- Priority: P0
- Depends on: T-070
- Reviewers: @model-risk, @ml-engineer
- Acceptance criteria:
  - [ ] "published score files are read-only; tests write only to a scratch folder": every score run writes to `deliverables/ai-engineer/evals/scratch/` unless `--publish` is given. This covers the eight scorers, `--holdout`, `--quick`, and the full 60
  - [ ] The scratch folder name is kept, with one `.gitignore` line
  - [ ] W2: only the output-path lines of the eight scorers and one import line in each are edited, and `score_out.py` is added. No `score_one`, `judge`, `hit_*`, gold parsing, or counting line is touched
  - [ ] `--publish` refuses before any scoring if the published name exists, has no force flag, and sets the new files read-only
  - [ ] U2: a publish run happens only after the user says so in the chat for that run
  - [ ] O1: "scored once" is checked in code. `--publish` for a hold-out is refused if a scratch result for that set exists
  - [ ] The files already published are set read-only, the development regression files included. The three T-060 rerun files are locked when T-060 is DONE
  - [ ] Self-check in a temp folder with no model call: a default run writes only to scratch; `--publish` onto an existing name is refused before scoring; `--publish` onto a new name writes the file and leaves it read-only
  - [ ] `regression_dev.py --quick` lands in the scratch folder and no field moves
- Output: underwriting_pipeline/ai/regression_dev.py, underwriting_pipeline/ai/score_out.py, the eight scorers (output-path lines only), .gitignore
- Notes: D-029, D-025. The user typed "approve change P-011 with W2 U2 O1, lock dev files, keep the name." Goes after T-070 so the two edits to `eval_holdout.py` do not cross. No score changes. The content of every published score file stays as it is. Until this is in, D-025 stands as written: nobody runs a scorer's main against its published path. The owner never runs `--publish` on its own word (U2). Not a production approval. 2026-10-11, @pm: P-017 (T-088), if approved, edits the same scorers; it is built after this task so the two edits do not cross. The new hold-out (T-093) is published through this task's `--publish`, once, after the user says so.

### T-073 — Implement P-012: every 429 and retry is saved in the token log
- Owner: @ai-engineer-assistant
- Requested by: @user
- Status: IN_REVIEW
- Priority: P0
- Depends on: —
- Reviewers: @model-risk, @ml-engineer
- Acceptance criteria:
  - [x] "every 429 and retry is saved in the token log so failed-call claims are backed by a file"
  - [x] Nothing else in the extractor changes under P-012
  - [x] Self-check passed with no model call, and the real log is unchanged by it
- Output: underwriting_pipeline/ai/llm_extract.py, underwriting_pipeline/cache/token_log.jsonl
- Notes: D-026 item 4. The user typed "approve change P-012". Built 2026-10-11. The boxes are ticked on the owner's report in team/DISCUSSION.md ("Re: D-026"), not on a review. No reviewer has given a verdict. P-012 has no proposal file; D-026 is its record. The quick set has not run since; it is run 1 of T-066. The log itself can lose a row on a killed run (@ml-engineer on T-063); that is P-014, not approved. Not a production approval.

### T-074 — Implement P-013: atomic cache writes
- Owner: @ai-engineer-assistant
- Requested by: @user
- Status: IN_REVIEW
- Priority: P0
- Depends on: —
- Reviewers: @model-risk, @ml-engineer
- Acceptance criteria:
  - [x] "atomic cache writes (temp file then rename)"
  - [x] "an unreadable cache file counts as not cached and is retried"
  - [x] "Add a self-check with a half-written file"
  - [x] The cache key, the prompt, and every hit or miss rule are unchanged
- Output: underwriting_pipeline/ai/llm_extract.py, deliverables/ai-engineer/proposal-P-013.md
- Notes: D-027. The user typed "approve change P-013". Built 2026-10-11 for @model-risk's Medium-1 on T-063. The boxes are ticked on the owner's report, not on a review. No reviewer has given a verdict on P-013. The quick set has not run since; it is run 1 of T-066. Not a production approval.

### T-075 — D-028 follow-ups to P-012 and P-013
- Owner: @ai-engineer-assistant
- Requested by: @user
- Status: IN_REVIEW
- Priority: P1
- Depends on: T-073, T-074
- Reviewers: @model-risk, @ml-engineer
- Acceptance criteria:
  - [x] "count reply_not_usable in the failure totals"
  - [x] "clean up .tmp files at the start of each run"
  - [x] "fix the old Author handle", only in files that are not published scores (D-025)
- Output: underwriting_pipeline/ai/llm_extract.py, underwriting_pipeline/ai/regression_dev.py, deliverables/ai-engineer/evals/SUB-077-086-holdout-rerun.md, deliverables/ai-engineer/architecture.md
- Notes: D-028. Built 2026-10-11. The boxes are ticked on the owner's report in team/DISCUSSION.md ("Re: D-028"), not on a review. No reviewer has given a verdict. The owner left two points for the user: a temp file under a minute old is left for the next run, and `retry` and `cache_unreadable` rows are not counted as failures. The retired handle is still in 8 published score files, the -original copy, the dev-rerun file, and 8 frozen scorers, left alone under D-025. Not a production approval.

### T-076 — Demo prep
- Owner: @pm
- Requested by: @user
- Status: TODO
- Priority: P0
- Depends on: T-062, T-066, T-067, T-071, T-079, T-081, T-083, T-085, T-086, T-087, T-089, T-090, T-093
- Reviewers: @senior-underwriter, @head-of-underwriting, @software-engineer, @compliance, @model-risk
- Acceptance criteria:
  - [ ] "for my non-technical manager at Sanger & Altgelt, 10 minutes" (D-031 item 3): plain words, and the walk-through is timed at 10 minutes or less
  - [ ] "one messy submission from inbox to carrier quote with citations"
  - [ ] "one failed file safely blocked"
  - [ ] "honest eval scores": the official score is the new 20-file hold-out (D-037), named with its file and its commit hash, and every quoted score says "8 of 9 fields scored; loss runs = date only" (D-033 item 5)
  - [ ] "cost estimate"
- Output: deliverables/pm/demo-guide.md
- Notes: D-030: "then demo prep". The user has not said what the demo must show or who it is for; that is a question to @user, and the criteria above are @pm's assumption until answered. T-040 is the earlier guide and serves SUB-009 only. Synthetic data only. Not a production approval. Does not authorize a send. 2026-10-11, @pm: the five boxes above are the user's brief, D-031 item 3, word for word, with the score wording from D-033 item 5 and the official score from D-037. They replace the five boxes that were @pm's assumption: guide matches the workbench step by step; says the page does not bind or decline and no AI role sends; every score names its file and the T-066 spread and is not called proof; lists what is open on the day; @senior-underwriter walks the steps once. Those stay as how the guide is written, not as acceptance. Standing rules for any score in the guide: T-026 only as "0 of 7 value fields; other hits came from empty output", never for the current extractor (D-036); the SUB-077 through SUB-086 rerun is not quoted as an improvement (D-026); a failed call is counted apart (D-021). The send in the walk-through follows T-020 criterion 2 as restated: a logged underwriter approve, then the simulated @account-manager with a written reason or the user's exact line. No AI role sends. Every line of team/DEMO-BLOCKERS.md is closed before this task starts; the builds of P-015 and P-016 are added to "Depends on" when their tasks exist. The cost estimate is read from the token log run totals (P-014, T-078); what price it is worked out at is a question to @user, because the host is a free tier (D-011). @model-risk is added as reviewer because the guide quotes scores.

### T-077 — Redraft proposal P-014 with the two D-030 additions
- Owner: @ai-engineer-assistant
- Requested by: @user
- Status: CANCELLED
- Priority: P1
- Depends on: —
- Reviewers: @ml-engineer, @model-risk
- Acceptance criteria:
  - [ ] The proposal says: "include host and temperature in the cache key"
  - [ ] The proposal says: "gitignore token_log.jsonl and the cache folder"
  - [ ] It is still P-014, Status "PROPOSAL. Not approved. Not implemented.", and ends by asking for the user's "approve change P-014"
  - [ ] No code, prompt, cache file, token log, `.gitignore`, or scorer is changed by this task, and no model call is made
- Output: deliverables/ai-engineer/proposal-P-014.md
- Notes: D-030 item 1. This is a proposal task only. There is no implementation task for P-014 and none is made until the user types "approve change P-014" (D-017). The current draft says the cache key is unchanged; the redraft changes that, so it must say in plain words what the new key does to the 13 saved results and to files that git already tracks, and leave any choice to the user. It blocks nothing: P-006, the variance test, and the fairness test do not wait on it. Backlog rows B-002, B-003, B-006, B-007, B-008, and B-012 name P-014. The triage rule applies to its review: High in detail, Medium and Low to team/BACKLOG.md. Not a production approval. 2026-10-11, @pm: cancelled, replaced by T-078. The user was shown P-014's choices in the chat (D-031 item 2) and approved it in D-033 before this redraft was written. deliverables/ai-engineer/proposal-P-014.md still says "Not approved", says the cache key is unchanged, and has no G choice. Bringing the file up to what was approved is the first box of T-078.

### T-078 — Implement P-014: a token log that survives a killed run, host and temperature in the cache key, log and cache out of git
- Owner: @ai-engineer-assistant
- Requested by: @user
- Status: IN_REVIEW
- Priority: P0
- Depends on: —
- Reviewers: @model-risk, @ml-engineer
- Acceptance criteria:
  - [x] Before any code is edited, deliverables/ai-engineer/proposal-P-014.md is brought up to what was approved: the status, "include host and temperature in the cache key", "gitignore token_log.jsonl and the cache folder", the G choice, and in plain words what the new key does to the 13 saved results. If the file and D-033 together leave any letter unclear, ask @user; do not pick
  - [x] Built with the user's choices "U1 R2 H1 O1 L1 T2 S1 G1", each letter as the proposal file defines it
  - [x] "include host and temperature in the cache key" (D-030)
  - [x] "gitignore token_log.jsonl and the cache folder" (D-030). G1, as D-033 records it: they are untracked "as a staged change with no commit"
  - [x] Self-check passes with no model call. Altered copies in a scratch folder each fail the new checks. Published score files are byte-identical before and after
  - [x] No prompt, OCR setting, gate, hit or miss rule, or scorer is changed. T2 touches only the `failed_attempts` block of `regression_dev.py`
- Output: underwriting_pipeline/ai/llm_extract.py, underwriting_pipeline/ai/regression_dev.py, .gitignore, deliverables/ai-engineer/proposal-P-014.md
- Notes: D-033 item 1: "approve change P-014 with U1 R2 H1 O1 L1 T2 S1 G1". D-031 item 2: it "lands before the T-064 baseline". D-030 item 1 for the key and the `.gitignore` lines. Covers @ml-engineer's Medium-1 and Medium-2 on T-063 and backlog rows B-002, B-003, B-006, B-007, B-008, B-012. The quick-set check after this change is T-064 itself. No commit is made by this task. Not a production approval. When it is built, @model-risk and @ml-engineer review it together with T-065, T-073, T-074, and T-075, which still have no verdict, and look again at T-063. 2026-10-11, @ai-engineer-assistant: built; boxes ticked by the author, for @model-risk and @ml-engineer to check. The proposal file was brought up to D-033 before any code edit. `llm_extract.py`: a line that cannot be read is skipped and counted (`skipped_lines`); every row starts on a new line; each new row has `run`, `key`, `host`; one `cache_hit` row per saved result used; a cache-hit row that cannot be written stops the run (SystemExit); `run_totals()` and `--budget` rebuild each run from the file; the cache key now holds the host name and the temperature. `regression_dev.py`: `run` and `run_totals` in the `failed_attempts` block, nothing else. `.gitignore`: two lines, edited, not staged. G1: `git rm --cached` on 10 paths (the token log and 9 saved results), staged, no commit, files left on disk. 13 of 13 saved results are unreachable under the new key and are left on disk; the 13 old log rows are read under "no run id". Self-check: "llm gate ok", no model call; 24 altered copies in a scratch folder each failed and a comment-only copy passed. The token log, the 13 saved results, every file under `deliverables/*/evals`, and the eight scorers have the same sha256 before and after. Prompt version still 82be09bd42f7. For the reviewers and @user: (1) the host in the key is the host name only, no port; (2) the token log on disk differs from the last commit, so after G1 is committed those rows and the 4 never-tracked results are in no commit; (3) `.gitignore` must be staged by whoever commits; (4) `budget()` now also returns `run` and `skipped_lines`. The quick set of 15 was not run: it is T-064, after the commit. Not a production approval.

### T-079 — Send rule in package.py: a carrier send requires a logged underwriter approve
- Owner: @software-engineer
- Requested by: @user
- Status: IN_REVIEW
- Priority: P0
- Depends on: T-071
- Reviewers: @compliance, @senior-underwriter, @account-manager, @model-risk
- Acceptance criteria:
  - [x] "a carrier send requires a logged underwriter approve; a declined file can never be sent" (D-033 item 2), "for every actor" (D-033, Amends), the user and the account manager included
  - [x] "the send reads the decision log itself and refuses unless the last decision for the submission is approve, for every actor" (@compliance, T-020 (a)). No decision passed in by the caller is trusted
  - [x] D-017's other send conditions and the P-010 status gate (T-071) are unchanged
  - [x] One self-check, in a temp folder only: no decision is refused; an approve passes this gate; an approve followed by a decline is refused
  - [x] The owner writes in the notes how "last" is ordered, and which ids count as an underwriter, and raises both as a QUESTION if the log cannot answer them. The log row has a date and no time (B-104) and takes any id (B-138, B-100)
- Output: underwriting_pipeline/app/package.py
- Notes: D-033 item 2. Line 2 of team/DEMO-BLOCKERS.md. Found by @compliance (T-020 H1, and the question on T-019) and @senior-underwriter (T-020 High-3). `package.py` is under `underwriting_pipeline/app/`; D-035 names that folder as @software-engineer's, so no P-### is asked for here. Not decided, for @user: a file that was declined and later approved. The user's words are "a declined file can never be sent"; D-033's Amends line says "a logged underwriter approve with no later decline". Do not pick; the code waits for the answer on that one case. No auto-decline: a refused send leaves the file with a person. Does not authorize a send. Not a production approval. 2026-10-13, @pm, board maintenance: confirmed as item (a) of the remaining T-020 veto (@compliance re-look, team/DISCUSSION.md:2306/2311). Not started; TODO. No verdict from @pm. 2026-10-14, @software-engineer: rebuilt to D-053 from the two saved patches (reference only; every line re-checked). `package.py` `_decision_problem()` reads `deliverables/software-engineer/decisions.jsonl` itself inside `send_to_carrier`, after the P-010 status gate and before the actor check, so it applies to every actor; no decision is a parameter (only `log_path`, for the self-check). Sendable only if the latest row for the submission is approve; an approve after any earlier decline needs a non-empty reason on that row; history is never edited. D-052 is not used. "Last" is ordered by line position in the append-only log (a row has a date, no time, B-104); a bad JSON line is skipped and is never an approve. Ids: no id is filtered; any `underwriter_id` the log took counts (B-138, B-100). Both are open for @user (D-053), raised as QUESTIONs in team/DISCUSSION.md; not decided here. Not done in this task: `workbench.record_decision` still lets an approve after a decline be logged without a reason; the send refuses it, so it cannot be sent, but the card does not stop it earlier. Fifth box (QUESTIONs) left to the reviewers as raised, ticked. Self-check (temp folder): `python3 underwriting_pipeline/app/package.py` prints "package ok"; `workbench.py` prints "workbench ok". No commit. 2026-10-14, orchestrator (at @user's instruction, main session, D-055): "last" is the highest `seq` in the one real log; only ids in `underwriting_pipeline/app/underwriters.json` count, AI roles never; `log_path` removed from the send (the @compliance High); the workbench refuses an approve after a decline without a reason and stamps every entry with the next `seq`. Self-checks: package ok, workbench ok. Status stays IN_REVIEW for the @compliance re-check. No verdict from the orchestrator.

### T-080 — Proposal P-016: citations, confidence, and unread content (T-027 (a), (b), (c))
- Owner: @ai-engineer-assistant
- Requested by: @user
- Status: IN_REVIEW
- Priority: P0
- Depends on: —
- Reviewers: @model-risk, @senior-underwriter
- Acceptance criteria:
  - [ ] One proposal, numbered P-016, for (a), (b), and (c) together (D-037: "Draft (a)–(c) as one proposal for my approval"). Status "PROPOSAL. Not approved. Not implemented." It ends by asking for the user's "approve change P-016"
  - [ ] (a), as @model-risk wrote it: "no value fallback; the value must be inside the quoted span for names, numbers, dates, addresses; translated fields stay needs_review". @senior-underwriter: "no quote match, no value"
  - [ ] (b), as D-037 words it: "gate on the lower of model and OCR confidence, OCR confidence from the cited words including digits". @model-risk also asks for "a confidence-versus-hit table". The proposal says in plain words that this amends P-003b (D-020 item 1)
  - [ ] (c), as D-037 words it: "every file and page is read or listed as needs human with the reason". It covers the four cases in @model-risk's H3: unsupported file types, unreadable pages inside a multi-page PDF, scanned pages in a PDF that has 40 typed characters, and text past 120,000 characters
  - [ ] The reviewers' own cases are listed as the tests: year built 1990 cited to "210-555-1990"; TIV 850000 cited to "Policy no. 8500001"; "2021" citing "Year built: 1948"; "10" inside "2010000"; SUB-078 year built 1991 against gold 1981; the effective dates "2O2H-01-O1" and "A2F-O1-O1"
  - [ ] It says what changes in the cache key and the saved results, which quick-set fields may drop, and what it does to the loss-run no-guess rule. Every choice is left to the user as a lettered option. Nothing is picked
  - [ ] It says whether the model's quote is kept on each stored row, because the workbench needs it to show the cited text (T-081) and that is a change under `underwriting_pipeline/ai/`
  - [ ] No code, prompt, OCR setting, cache file, or scorer is changed by this task, and no model call is made
- Output: deliverables/ai-engineer/proposal-P-016.md, and one PROPOSAL message in team/DISCUSSION.md
- Notes: D-033 item 4 and D-037. Line 3 of team/DEMO-BLOCKERS.md. Found by @model-risk (T-027 H1, H2, H3) and @senior-underwriter (T-027 High-1, High-2, High-3). This is a proposal task only. The build task is made by @pm when the user types "approve change P-016" (D-017). (d), the new hold-out, is not in the proposal; it is T-091, T-092, and T-093 and it starts only after (a) to (c) are built, frozen, and committed. An approved proposal is not a production approval; lifting the T-027 veto is @model-risk's call. 2026-10-11, @ai-engineer-assistant: P-016 is written and posted. Not approved, not implemented. Twelve lettered choices for @user. The estimate is from the 13 saved replies with no model call. Waiting on the reviewers and on the user's "approve change P-016".

### T-081 — Workbench shows the text a value was cited from
- Owner: @software-engineer
- Requested by: @pm
- Status: TODO
- Priority: P0
- Depends on: T-071
- Reviewers: @compliance, @senior-underwriter
- Acceptance criteria:
  - [ ] The cited text on the card is the text the value came from, for PDF, xlsx, png, jpg, and csv. Fix, as @compliance wrote it: "cite from the text `sources.read_folder` returns, or keep the quote on the row"
  - [ ] One file that cannot be shown does not stop `load_queue` for the whole queue
  - [ ] "Add a check with a PDF and an image" (@compliance)
  - [ ] Nothing under `underwriting_pipeline/ai/` is edited by this task. If the fix needs the quote kept on the row, that part goes into P-016 (T-080) and waits for the user's approval
- Output: underwriting_pipeline/app/workbench.py
- Notes: Found by @compliance (T-019 High-1: jpg, png, xlsx raise UnicodeDecodeError on 29 files, "which stops `load_queue` for the whole queue"; a PDF shows "%PDF-1.4 1 0 obj..." as the cited text) and @senior-underwriter (T-019 High-1). D-033 item 4 does not name this finding. @pm placed it beside "exact citations only" as line 3b of team/DEMO-BLOCKERS.md, because the user's demo brief says "with citations" and the messy submission is likely a PDF or a scan. That placement is @pm's reading and is for @user to confirm or move to the backlog. Not a production approval.

### T-082 — Carrier match: the class lists and the caps
- Owner: @head-of-underwriting
- Requested by: @user
- Status: IN_REVIEW
- Priority: P0
- Depends on: —
- Reviewers: @senior-underwriter, @actuary, @compliance, @responsible-ai
- Acceptance criteria:
  - [x] For Carrier A, B, and C: the classes each one writes, as whole words or phrases a rule can match, and the classes that are no-match for all three
  - [x] One stated answer for each case @senior-underwriter listed: cannabis dispensary retail, armed security office, sprinklered student housing, roofing contractor, an $8,000,000 office, barbecue restaurant, barber shop, taqueria
  - [x] Each cap as a number, "the $5M cap" included, and what happens at exactly the cap
  - [x] The words shown beside Carrier B while no claim is read: "3 clean years not checked", or other words
  - [ ] @senior-underwriter and @actuary are consulted (decision rights). No class is an automatic decline; no_match is not a decline to the producer
- Output: deliverables/head-of-underwriting/carrier-match.md
- Notes: D-033 item 4: "carrier match rules with caps enforced (@head-of-underwriting supplies class lists)". Line 4 of team/DEMO-BLOCKERS.md. Found by @senior-underwriter (T-019 High-3): "The rules are @head-of-underwriting's." If a rule changes from the accepted T-018 text, @head-of-underwriting records it in team/DECISIONS.md. Carriers are placeholders A, B, and C. No code is changed in this task. T-083 waits on it. 2026-10-13, @head-of-underwriting: deliverable written; criteria 1–4 ticked. Criterion 5 is half met — no class is an automatic decline and no_match is not a producer decline (met in the file) — but the consultation is posted this turn and the replies from @senior-underwriter and @actuary are pending, so it stays unticked until they answer. Rule changes from the accepted T-018 text are recorded as D-041. Set IN_REVIEW and posted a QUESTION/consultation and a REVIEW request to DISCUSSION.md. 2026-10-13 (revised): all four reviewers returned APPROVE WITH CHANGES. Addressed in the file and recorded as D-042 — residual unmatched-class branch defined (@senior-underwriter High-1), `kitchen` removed and the collision rule added (@senior-underwriter High-2), Spanish/variant synonyms added and the EN-vs-ES counterfactual routed to T-067 (@responsible-ai High-1), housing proxy-review entry added and the recommendation-mix test routed to T-067 (@responsible-ai High-2), caps marked provisional pending @actuary's signoff (@actuary High-1), loss gate tightened to a verifiable read loss run (@actuary High-2), consultation record updated (@compliance Medium-1). Criterion 5 stays unticked: @senior-underwriter's reply is on file, but @actuary's cap reply is still pending in team/DISCUSSION.md. The @responsible-ai fairness veto is open and is lifted only by @responsible-ai; T-083 must not be coded against the lists until then. Documentation only; no code, prompt, or scorer changed. Stays IN_REVIEW.

### T-083 — Carrier match rules in `route()`, with the caps enforced
- Owner: @software-engineer
- Requested by: @user
- Status: IN_REVIEW
- Priority: P0
- Depends on: T-082, T-071
- Reviewers: @senior-underwriter, @head-of-underwriting, @compliance, @responsible-ai, @model-risk
- Acceptance criteria:
  - [x] `route()` matches the lists in carrier-match.md by whole word, not by substring
  - [x] The no-match classes, roofing, and every cap from T-082 are enforced (per D-059/D-060)
  - [x] The Carrier B line from T-082 is shown on the card
  - [x] "one test each" (@senior-underwriter) for the eight cases listed on T-082
  - [x] The in-appetite check in `package.py` uses the same function, with one self-check that a no-match file is refused
  - [x] The match stays a recommendation. Nothing declines a file
- Output: underwriting_pipeline/app/workbench.py, underwriting_pipeline/app/package.py
- Notes: D-033 item 4. Line 4 of team/DEMO-BLOCKERS.md. @senior-underwriter, T-019 High-3: "`route()` gives: cannabis dispensary retail and armed security office, carrier_a; sprinklered student housing, carrier_c; roofing contractor, carrier_b; an $8,000,000 office, carrier_a; barbecue restaurant and barber shop, no_match; taqueria, hold." T-020: "cannabis retail passes as Carrier A." Backlog rows B-077 and B-090 are the same ground. The name-swap test (T-067) runs after this. Not a production approval. 2026-10-14, @software-engineer: built to D-059 as amended by D-060; D-041/D-042 are void (D-058), so where the criteria cite T-082/D-041/D-042, D-059+D-060 replace them. `workbench.match()` (route, note, suggested, overridable; `route()` returns its route) and `package.py` use it. Outcomes: carrier_a/b/c, no_match, hold, senior_referral (route value `senior_referral`). Prohibited first; caps inclusive (A and pilot TIV $5M, B $2M provisional, over $10M no_match not overridable); roofing is a contractor (senior referral, suggested carrier_b); roofing -> C and over-cap -> C removed; Carrier B shows "3 clean years not checked" (the loss-run gate itself is not built: there is no loss-run field). The D-057 override works only on no_match that D-060 calls overridable (barber shop, readable class on no list), never prohibited, over $10M, hold, or senior referral. The input-document manifest (P-020) is NOT built; waits on "approve change P-020". Spanish entries are translations of sourced classes only; @responsible-ai review is B-197. Housing proxy review is B-198. Self-checks: `python underwriting_pipeline/app/workbench.py`, `package.py`, `quotes.py`. Open ceilings: TIV is read from tiv_building (first number, not "5M"); missing TIV counts as 0. 2026-10-14, orchestrator (at @user's instruction, main session, budget rule 3, D-061): High-1 fix. `_tiv` now uses the existing normalizer `prepare.amount_value()`; a missing, blank, "TBD" or unreadable TIV is hold, "TIV missing or unreadable" ("$1.2MM" is not read by that normalizer and holds). The over-$10M no_match rule is removed; over $5M per location is senior referral, "outside pilot TIV limit (AG:16)". Self-checks added for "$8M", "$1.2MM", "750K", blank, "TBD", and $12,000,000; two older fixtures got a TIV. workbench ok, package ok, quotes ok. Stays IN_REVIEW for the @senior-underwriter re-check. No verdict from the orchestrator.

### T-084 — Proposal P-015: the score fixes
- Owner: @data-scientist
- Requested by: @user
- Status: IN_REVIEW
- Priority: P0
- Depends on: —
- Reviewers: @actuary, @model-risk, @responsible-ai, @compliance
- Acceptance criteria:
  - [ ] Numbered P-015. Status "PROPOSAL. Not approved. Not implemented." It ends by asking for the user's "approve change P-015"
  - [ ] "remove loss-history points and show "Loss history: not scored" (claim extraction goes to backlog)"
  - [ ] "failed or incomplete files show "Not scored" with reason"
  - [ ] "decision rows save points, codes and points version"
  - [ ] "underwriter can mark a code wrong with a logged reason"
  - [ ] "cooking points must come from actual hazards (fryer, open flame, hood/suppression), never from business name or cuisine words" (D-033 item 3)
  - [ ] It says where each hazard fact comes from, and whether that needs a change under `underwriting_pipeline/ai/`. It lists a wording-pair test with a negation ("office, no kitchen") and with @responsible-ai's cases: taco, taqueria, pizzeria, barbecue, steakhouse, "catering, commercial cooking"
  - [ ] A files-and-owners table: `underwriting_pipeline/models/points.py` and reason-codes.md (@data-scientist), `underwriting_pipeline/app/workbench.py` (@software-engineer), anything under `underwriting_pipeline/ai/` (@ai-engineer-assistant)
  - [ ] Every choice is left to the user as a lettered option. No code is changed by this task
- Output: deliverables/data-scientist/proposal-P-015.md, and one PROPOSAL message in team/DISCUSSION.md
- Notes: D-031 item 5 and D-033 item 3; the quoted boxes are the user's words. Line 5 of team/DEMO-BLOCKERS.md. Found by @actuary (T-017 High-1 to High-3), @model-risk (High-1 to High-3, veto), and @responsible-ai (H1 to H4, veto). This is a proposal task only. The build tasks are made by @pm when the user types "approve change P-015" (D-031). The score cannot decline, bind, or set a price; that does not change. The fairness test (T-067) runs after the build. Not a production approval. 2026-10-11, @data-scientist: P-015 is written, deliverables/data-scientist/proposal-P-015.md, and posted as a PROPOSAL. Not approved, not implemented, no code changed, no model call. Eight lettered choices for @user (S, H, M, T, V, W, A, E), none picked. The boxes are left for the reviewers to tick; I do not approve my own work. Found while writing: the cue list in `prepare.py` ("taco", "kitchen", the insured's name included) can make a file incomplete and so "Not scored"; that is choice T and an `ai/` change. The estimate uses gold status, not the pipeline's; SUB-001 to SUB-006 are not computed.

### T-085 — Package built from the reviewed file
- Owner: @software-engineer
- Requested by: @user
- Status: IN_REVIEW
- Priority: P0
- Depends on: T-079, T-083
- Reviewers: @compliance, @senior-underwriter, @account-manager
- Acceptance criteria:
  - [x] "the package is built from the saved reviewed file with citations and the named carrier" (@compliance, T-020 (d)). No free text from the caller is the body
  - [x] "refuse when a required field is empty" (@senior-underwriter)
  - [x] The owner writes in the notes what "the underwriter's edits" are today. An edit stores no field and no new value (B-139, marked High, not on the demo path), so the package cannot carry an edit until that is fixed. Raise it as a QUESTION to @user; do not widen this task
  - [x] The package is labeled synthetic. One self-check in a temp folder
- Output: underwriting_pipeline/app/package.py
- Notes: D-033 item 4: "package built from the reviewed file". Line 6 of team/DEMO-BLOCKERS.md. Found by @senior-underwriter (T-020 High-2: "The sent SUB-002 package has no sales and no year built") and @compliance (T-020 H4, A-02). Does not authorize a send. Not a production approval. 2026-10-13, @pm, board maintenance: confirmed as item (d) of the remaining T-020 veto (@compliance re-look, team/DISCUSSION.md:2306/2311). Not started; TODO. No verdict from @pm. 2026-10-14, @software-engineer: built with T-086 under D-056. What "the underwriter's edits" are now: a workbench edit row stores `field_id` and `new_value` (workbench.py), and the package carries the latest edit per field by a listed underwriter, marked EDITED with the original value and citation. Edit rows with no field stay reason-only and are not carried. The carrier is `workbench.route()` on the edited saved run, as `agency_problem` already uses it; T-083 will replace that function and the package follows it. Open: a QUESTION to @user on the out-of-appetite user override (DISCUSSION). Self-check: `python underwriting_pipeline/app/package.py`.
  2026-10-14, @software-engineer: D-057 item 1 built in `package.py`. `send_to_carrier(..., carrier=)` / `build_package(..., carrier_override, override_reason)`: the user's override is allowed only when `route()` returns no_match, never hold (a hold, or a carrier named on any other match, is refused); the send must name carrier_a, carrier_b or carrier_c and give a written reason; the package carries "Outside matched appetite — placed by underwriter override" and the reason; the sends.jsonl row records `carrier_override` and `override_reason`. The account manager cannot override. Every other gate (decision log, saved run, user line, empty field) still applies. Self-check in package.py -> package ok. B-185 and B-191 unchanged (D-057 items 2 and 3).

### T-086 — A user send carries the user's exact line
- Owner: @software-engineer
- Requested by: @user
- Status: IN_REVIEW
- Priority: P0
- Depends on: T-085
- Reviewers: @compliance, @account-manager
- Acceptance criteria:
  - [x] "a user send must carry my exact "send to carrier SUB-###" line, matched to the submission id and logged" (D-035)
  - [x] A call with actor "user" and no such line, or a line for another submission, writes nothing
  - [x] The line gives no way past T-079 or the P-010 status gate
  - [x] One self-check in a temp folder
- Output: underwriting_pipeline/app/package.py
- Notes: D-035. Line 7 of team/DEMO-BLOCKERS.md. Found by @compliance (T-020 H3): "Any role that calls with actor "user" writes to to-carrier." Item (c) of what resolves the T-020 veto. No role writes that line for the user; it comes only from the user's own message in the chat. Does not authorize a send. 2026-10-13, @pm, board maintenance: confirmed as item (c) of the remaining T-020 veto (@compliance re-look, team/DISCUSSION.md:2306/2311). Not started; TODO. No verdict from @pm. 2026-10-14, @software-engineer: built with T-085 under D-056. `send_to_carrier(submission, actor, out_dir, reason, user_line)`; the caller body is gone. The user's line is checked after the status gate, T-079, and the actor check, so it opens none. Each user send is logged in `deliverables/software-engineer/sends.jsonl` (a separate file, so a send row never reads as a decision) and in the package header.


### T-087 — Quote tracking from the carrier replies
- Owner: @software-engineer
- Requested by: @user
- Status: IN_REVIEW
- Priority: P0
- Depends on: T-086
- Reviewers: @compliance, @senior-underwriter, @account-manager
- Acceptance criteria:
  - [x] "quote tracking shows a status per submission and carrier from the carrier replies, including open subjectivities" (D-035)
  - [x] "per submission and carrier, store sent date, status, premium, deductible, and each subjectivity as open or closed" (@senior-underwriter)
  - [x] The nine replies now in simulation/from-carrier/ are read, and SUB-002's subjectivity "confirm hood and suppression" shows as open
  - [x] Nothing is written into simulation/from-carrier/ or simulation/inbox/. Nothing binds. One self-check in a temp folder
- Output: underwriting_pipeline/app/package.py, or a new file under underwriting_pipeline/app/ that the owner names (named: quotes.py; shown on the workbench card by workbench.py)
- Notes: D-035. Line 8 of team/DEMO-BLOCKERS.md. Found by @senior-underwriter (T-020 High-1) and @compliance (T-020 H5). Item (e) of what resolves the T-020 veto, and T-020's third criterion. When T-071, T-079, T-085, T-086, and this task are in, T-020 goes back to @compliance and @senior-underwriter. 2026-10-13, @pm, board maintenance: confirmed as item (e) of the remaining T-020 veto (@compliance re-look, team/DISCUSSION.md:2306/2313) and T-020's third criterion. T-071 is now DONE; this task and T-079, T-085, T-086 remain. Not started; TODO. No verdict from @pm.
  2026-10-14, @software-engineer (owner's check, not an approval): built `underwriting_pipeline/app/quotes.py`; `workbench.py` shows it on each card ("Quote tracking"). Read: the nine replies in simulation/from-carrier/ give eight (submission, carrier) rows; SUB-002 carrier_b shows premium 9800, deductible 2500, "confirm hood and suppression on the inspection" [open]. Judgment for review: the later SUB-002 reply says the subjectivity is "satisfied", but it cites an agency reply and criterion 3 requires open, so a carrier statement is shown as a note and does not close it; a subjectivity closes only when a listed underwriter with a written reason calls `close_subjectivity` (subjectivity_closures.jsonl). Sent date = mtime of simulation/to-carrier/SUB-###.md, else "not recorded" (replies carry no date). Nothing written to simulation/from-carrier/ or inbox/ (self-check compares mtimes). Nothing binds (`bound` is False). Self-check: `python3 underwriting_pipeline/app/quotes.py` -> quotes ok; `workbench.py` -> workbench ok. Reviewers @compliance, @senior-underwriter, @account-manager to look; T-020 goes back to @compliance. No model call.

### T-088 — Proposal P-017: the commit hash and the literal status in score output
- Owner: @ai-engineer-assistant
- Requested by: @user
- Status: IN_REVIEW
- Priority: P0
- Depends on: —
- Reviewers: @model-risk, @ml-engineer
- Acceptance criteria:
  - [ ] Numbered P-017. Status "PROPOSAL. Not approved. Not implemented." It ends by asking for the user's "approve change P-017"
  - [ ] "record the git commit hash in each score file and memo" (D-034). It says what a run does when the tree has uncommitted changes under the pipeline paths
  - [ ] "A scorer status must say exactly what happened, e.g. "not sent: no readable text", never "Call: ok" when no call was made" (D-034). It lists every status a row can show
  - [ ] It names each scorer line and each `regression_dev.py` line that changes, and says how the edit sits with P-011's output-path edits to the same files (T-072). No hit or miss rule changes
  - [ ] It says what the scorer for the new 20-file hold-out is (T-093): a copy with the ids changed, or one with rules for the Effective date line and the claims line that the gold will carry (T-092). Any new rule is a lettered choice for the user
  - [ ] No published score file is rewritten or recounted. No code is changed by this task
- Output: deliverables/ai-engineer/proposal-P-017.md, and one PROPOSAL message in team/DISCUSSION.md
- Notes: D-034: "Writing the hash and the new status wording into score output changes the scorers and `regression_dev.py`, so that part needs a numbered proposal and the user's approval before it is built." Backlog rows B-045, B-047, and B-145 are the findings behind it. Not a line in team/DEMO-BLOCKERS.md, but the new hold-out's score file (T-093) must carry the hash (D-037), so the build goes before T-093. The build task is made by @pm when the user types "approve change P-017". Until then, the commit is still made before every scored run and the hash is written in the memo by hand. 2026-10-11, @ai-engineer-assistant: P-017 is written and posted. Not approved, not implemented. D-038 item 4 is written as decided, not as a choice. One point is raised for @user on the count in the label "9 of 10". Waiting on the reviewers and on the user's "approve change P-017".

### T-089 — Model inventory
- Owner: @model-risk
- Requested by: @user
- Status: IN_REVIEW
- Priority: P0
- Depends on: —
- Reviewers: @ai-engineer-assistant, @data-scientist, @compliance
- Acceptance criteria:
  - [x] deliverables/model-risk/model-inventory.md exists (D-031 item 5: "Also create deliverables/model-risk/model-inventory.md")
  - [x] The label-scanner extractor scored on SUB-017 through SUB-026 is recorded as retired under D-010, with its score quoted only as "0 of 7 value fields; other hits came from empty output" and a line that it is never cited for the current extractor (D-036)
  - [x] One entry for each component in use: the LLM extractor, the point score, the carrier match. Each has its owner, its tier under validation-standards.md, its version id, its open vetoes, and what it may not do
  - [x] Each entry lists the score files that belong to it and the rule for quoting them
  - [x] @model-risk says in team/DISCUSSION.md whether the T-026 veto on the retired extractor is lifted
- Output: deliverables/model-risk/model-inventory.md
- Notes: D-031 item 5 and D-036. The published score files are not edited (D-025). The inventory is a record; it approves nothing for production. The reviewers check that their own component is described correctly; they do not review @model-risk's verdicts. 2026-10-13, @model-risk: written. C-1 LLM extractor (Tier 2, prompt `82be09bd42f7` + `openai/gpt-oss-120b`, open vetoes T-027 and T-059), C-2 point score (Tier 2, no version id, open T-017 vetoes from @model-risk and @responsible-ai plus @actuary REJECT), C-3 carrier match (Tier 2, D-041, no open veto). R-1 label-scanner extractor recorded retired under D-010, score quoted only as "0 of 7 value fields; other hits came from empty output", never cited for the current extractor. The T-026 veto is lifted (moot: the component is retired), stated in team/DISCUSSION.md. No score file edited or recounted. IN_REVIEW for @ai-engineer-assistant, @data-scientist, @compliance.

### T-090 — Dated lines in three hold-out memos
- Owner: @model-risk
- Requested by: @pm
- Status: IN_REVIEW
- Priority: P0
- Depends on: —
- Reviewers: @senior-underwriter, @ai-engineer-assistant
- Acceptance criteria:
  - [x] deliverables/model-risk/holdout-SUB-057-066.md gets a dated line: "loss runs = valued-through date only; claims are not read or scored" (@senior-underwriter, T-039 High-1)
  - [x] The same memo gets a dated line: "SUB-057, 058, 064, 065: OCR returned no text and no model reply was scored; 'Call: ok' means no error was raised. Six of ten rows come from a model reply." (@ai-engineer-assistant, T-039 High-1)
  - [x] deliverables/model-risk/holdout-SUB-067-076.md gets the loss-runs line (T-044 High-1)
  - [x] deliverables/model-risk/holdout-SUB-077-086.md gets the loss-runs line (T-053 High-1)
  - [x] No published score file is touched (D-025). No score is recounted
- Output: the three memos named above
- Notes: Asked for by the reviewers of T-039, T-044, and T-053; backlog rows B-144 to B-147. The memos are @model-risk's own files, so the wording is @model-risk's to accept or to answer with an OBJECTION. When the lines are in, @senior-underwriter looks again at T-039, T-044, and T-053 and @ai-engineer-assistant at T-039. D-033 item 5 sets the wording for every quoted score: "8 of 9 fields scored; loss runs = date only". 2026-10-13, @model-risk: the two dated lines are added to holdout-SUB-057-066.md under a "Dated lines — 2026-10-13" heading, and the loss-runs line to holdout-SUB-067-076.md and holdout-SUB-077-086.md; each also carries D-033 item 5's standing wording. No file under deliverables/ai-engineer/evals/ was touched and no score was recounted (D-025). IN_REVIEW for @senior-underwriter and @ai-engineer-assistant.

### T-091 — Build the new hold-out, SUB-087 through SUB-106
- Owner: @producer
- Requested by: @user
- Status: BLOCKED
- Priority: P0
- Depends on: T-062, T-068, T-072
- Reviewers: @senior-underwriter, @model-risk
- Acceptance criteria:
  - [ ] 20 new synthetic submissions, SUB-087 through SUB-106, in simulation/inbox/ (D-020 item 9, D-037: "a new 20-file hold-out")
  - [ ] Built only after (a) to (c) are "frozen and committed" (D-037): P-016 is approved and built, P-006 (T-062) is in, and the commit hash of the frozen code is posted in team/DISCUSSION.md
  - [ ] Every file is labeled synthetic. No real applicant
  - [ ] Each submission has an effective date and, where it has a loss run, claims with a count and paid and open amounts, so the gold can carry both lines (T-092)
- Output: simulation/inbox/SUB-087 through SUB-106
- Notes: D-037 (d). Line 9 of team/DEMO-BLOCKERS.md. The extractor is not run on these files, by anyone, before the gold exists. After the gold exists no code changes until the score is published. Blocked until the freeze; the builds of P-016 and, if approved, P-017 are added to "Depends on" when their tasks exist. P-006 changes extraction, so it goes before the freeze; that is @pm's reading of "frozen" and is in the list for @user. Open, for @user: @ai-engineer-assistant's B-052 says "The next 20-file set should hold shapes that are in no development set." It is a Medium in the backlog and is not made a criterion here.

### T-092 — Gold answers for hold-out SUB-087 through SUB-106
- Owner: @senior-underwriter
- Requested by: @user
- Status: BLOCKED
- Priority: P0
- Depends on: T-091
- Reviewers: @model-risk
- Acceptance criteria:
  - [ ] One expected answer per submission, written before any score runs ("gold first", D-037)
  - [ ] Each answer has an Effective date line and a claims line (count, paid, open), as @senior-underwriter's own review of T-053 said: "I add Effective date and a claims line (count, paid, open) to the gold of the next 20-file hold-out before it is scored"
  - [ ] None of the answers is an automatic decline
- Output: deliverables/senior-underwriter/gold-set/SUB-087.md through SUB-106.md
- Notes: D-037 (d). Line 9 of team/DEMO-BLOCKERS.md. Backlog row B-148. Whether the scorer scores the two new lines is a choice in P-017 (T-088); the gold carries them either way. Backlog rows B-036 and B-041 are @senior-underwriter's own open points on gold wording; they are Medium and are not made criteria here.

### T-093 — Score hold-out SUB-087 through SUB-106, once
- Owner: @model-risk
- Requested by: @user
- Status: BLOCKED
- Priority: P0
- Depends on: T-092, T-072
- Reviewers: @ai-engineer-assistant, @senior-underwriter
- Acceptance criteria:
  - [ ] "gold first, commit hash saved, scored once" (D-037). The commit hash is in the score file and the memo, and the call log for the run is saved
  - [ ] No code change after the gold exists (D-020, D-022). The commit that is scored is the one posted at the freeze
  - [ ] The score is published once through `--publish`, after the user says so in the chat for that run (D-029, U2). No other published file is touched
  - [ ] A failed call is counted apart and is not a miss (D-021). `all_values_rejected` fields are misses (D-024). A null that matches missing is not counted as correct
  - [ ] The memo says which fields were scored and quotes the score in the form D-033 item 5 sets
- Output: deliverables/ai-engineer/evals/SUB-087-106-holdout.json, deliverables/ai-engineer/evals/SUB-087-106-holdout.md, deliverables/model-risk/holdout-SUB-087-106.md
- Notes: D-037: "this is the official score for the demo". Line 9 of team/DEMO-BLOCKERS.md. Found by @model-risk (T-027 H4): "No hold-out score exists for the current prompt and gate." About 20 fresh calls against a 200,000-token day; do not start it on a day another run has used the budget. Not a production approval. Lifting the T-027 veto is @model-risk's call. If the user's wording "8 of 9 fields scored; loss runs = date only" stops being true for this set because P-017 adds a rule, say so and ask @user for the wording; do not change it.

### T-094 — architecture.md: what exists
- Owner: @software-engineer
- Requested by: @user
- Status: IN_REVIEW
- Priority: P1
- Depends on: —
- Reviewers: @model-risk, @compliance
- Acceptance criteria:
  - [x] System context: producers, carriers, underwriters, account manager, LLM provider, OCR, our app
  - [x] Components with one owner each: intake, OCR/text reading, extraction, validation gates, cache, risk score, carrier match, missing-info drafts, workbench, decision log, package/send, quote tracking, eval harness
  - [x] Trust and data boundaries: what data leaves our system (LLM calls), where PII lives, where humans must act
  - [x] Data flow and the submission lifecycle as a state machine (received → extracted → needs_human / extraction_failed / all_values_rejected → ready → approved/declined → sent → quoted)
  - [x] Contracts between components: input/output schema for each stage, status enums, error contract
  - [x] Data stores and what each holds
  - [x] Decision index: link each architecture choice to its D-### and P-###
  - [x] The document has Mermaid diagrams
  - [x] The document separates "As-is (code today)" from "Target (production)"
  - [x] Every claim about current code cites file and line
  - [x] Every number is labeled measured (with source file) or assumed (with reasoning)
  - [x] Known gaps from DEMO-BLOCKERS.md and open vetoes are listed honestly, not hidden
  - [x] Documentation only: no pipeline code changes, no model calls
  - [x] @software-engineer reconciles all citations in architecture.md and low-level-design.md to the current commit before review (D-046)
- Output: deliverables/architecture/architecture.md
- Notes: Requested by @user on 2026-10-13, title "WHAT EXISTS". The criteria are the user's bullets and the user's rules for all three documents, copied; @pm added none. Priority: P1, below every demo blocker (all P0). The user: "It runs alongside the demo blockers and must not delay them." @software-engineer owns seven blocker tasks (T-071, T-079, T-081, T-083, T-085, T-086, T-087); those come first, and this task is worked only in a turn where none of them can move. No status on a blocker task changes because of this one. Lead: @software-engineer. With, as the user named them: @ai-engineer-assistant and @data-engineer. Sections by role are @pm's split from the decision-rights table, for the lead to adjust: @ai-engineer-assistant gives OCR/text reading, extraction, validation gates, cache, missing-info drafts, eval harness, and what leaves our system in an LLM call; @data-engineer gives the data stores, the schemas in the contracts, and where PII lives; @software-engineer gives the rest and the single document. "One owner each" for a component is recorded from the decisions and the task board as they stand; where no owner is recorded, the document says so and the role that decides is asked, it is not chosen in the document. The document describes; it decides nothing, authorizes no send, and is not a production approval. New folder deliverables/architecture/ is shared by T-094, T-095, and T-096; each lead writes only its own file. Reviewers get the task id, these criteria, and the path, nothing else. 2026-10-13, @pm: one criterion added from the user's words in D-046 (citations reconciled to the current commit before review); it is unticked and the owner ticks it. The citations were written at `d5750fd`; T-070 and T-071 were committed since. The user's decisions answer this document's open questions, and the owner (@software-engineer) updates the document to state them as decided, not open: D-048 (how a file leaves `all_values_rejected`; section 4.2, Q12), D-049 (accuracy floor: D-013 is the pilot floor on synthetic data, the production floor is set later by @head-of-underwriting and @model-risk; Q13), D-050 ("complete" applies to carrier sends only; Q9; the app-side build is T-098, not this task), D-051 (real client data never goes into git; 3.1, 3.2, Q14). The task is not closed and its status is not changed by this edit; no existing box was ticked or unticked. Reviewers look again at the updated document; @pm gives no verdict. 2026-10-13, @software-engineer (owner's check, not an approval): the citation criterion is ticked. Both documents now describe commit `dd45467`. Measured with one script, 2026-10-13: `architecture.md` 1,105 file-and-line citations, 0 out of range, 0 naming a missing file (of the 985 before, 473 pointed into the four changed files: 68 unmoved, 315 re-pointed by script as byte-identical lines, 90 read and rewritten by the lead); `low-level-design.md` 1,770 citations, 0 out of range, 0 naming a missing file (of the 1,424 before, 747 pointed into the four changed files: 139 unmoved, 562 re-pointed by script, 46 read and re-pointed or rewritten by the lead). Limits, stated in each document: the script checks range, not meaning; in the co-lead's sections of `low-level-design.md` the 469 citations that only moved were not re-read; citations into `team/` files were checked for range only. D-045, D-048, D-049, D-050, D-051 are quoted where they apply (document section 13.4); Q9, Q12, Q13, Q14 are marked answered. All five diagrams render without error (Mermaid CLI 12.0.0, 2026-10-13). The document changed after both reviewers approved; section 13 lists every change and an UPDATE asks them to look again. Status stays IN_REVIEW; closing is @pm's. No file under `underwriting_pipeline/` or `simulation/` changed; no model call; no commit.

### T-095 — system-design.md: how it behaves at scale
- Owner: @ml-engineer
- Requested by: @user
- Status: IN_REVIEW
- Priority: P1
- Depends on: —
- Reviewers: @software-engineer, @model-risk, @compliance
- Acceptance criteria:
  - [x] Requirements and SLOs: target time per submission, throughput, availability, accuracy floor
  - [x] Load model at 300 / 1,000 / 3,000 submissions per month and a peak hour; pages and tokens per submission (measured from token_log where possible)
  - [x] Capacity and bottlenecks: today's Groq limits (measured) vs enterprise quotas (assumed)
  - [x] Latency budget per stage
  - [x] Failure modes table: LLM 429/timeout/bad reply, OCR failure, unreadable or partial files, duplicate submissions, crash mid-write, stale cache, provider outage. For each: detection, retry/backoff, idempotency, what the underwriter sees, and whether a send can ever happen
  - [x] Reliability design: queue and workers, idempotent sends, exactly-once carrier send, dead-letter handling
  - [x] Observability: metrics, logs, alerts, audit trail
  - [x] Scaling plan and cost model per submission at each volume (measured tokens, list prices labeled with date)
  - [x] Security, privacy, backup and disaster recovery
  - [x] Test plan for reliability, traffic, latency, failure and cost: load test, failure injection, cost test. Run only the tests that need no model calls now (stubbed model), report results; list the rest as planned
  - [x] The document has Mermaid diagrams
  - [x] The document separates "As-is (code today)" from "Target (production)"
  - [x] Every claim about current code cites file and line
  - [x] Every number is labeled measured (with source file) or assumed (with reasoning)
  - [x] Known gaps from DEMO-BLOCKERS.md and open vetoes are listed honestly, not hidden
  - [x] Documentation only: no pipeline code changes, no model calls
- Output: deliverables/architecture/system-design.md
- Notes: Requested by @user on 2026-10-13, title "HOW IT BEHAVES AT SCALE". The criteria are the user's bullets and the user's rules for all three documents, copied; @pm added none. Priority: P1, below every demo blocker (all P0); "It runs alongside the demo blockers and must not delay them." @ml-engineer reviews T-078 first. Lead: @ml-engineer. With, as the user named them: @pm and @actuary. Sections by role are @pm's split from the decision-rights table, for the lead to adjust: @pm gives the requirements list and the three volumes and peak hour as the user set them; @actuary gives the cost model per submission and the reasoning behind assumed numbers; @ml-engineer gives the rest and the single document. Targets nobody has decided (time per submission, availability, accuracy floor) are written as assumed with the reasoning and the role that decides them named; the accuracy floor is an eval matter and is @user's. No dependency on T-094 is set because the user stated none; the two documents use the same component names, and @ml-engineer says so in DISCUSSION.md if that needs T-094 first. @pm's reading, for the lead: the tests that run now use a stubbed model and live outside `underwriting_pipeline/` (no pipeline code changes), touch no eval scorer and no published score file (D-017, D-025), make no model call, and write nothing into simulation/. The token log and the cache are read, not written. Not asked of this task and not added: @compliance is not a reviewer though the document covers security and privacy; that is in the list for @user. Not a production approval. Reviewers get the task id, these criteria, and the path, nothing else. Owner's check, 2026-10-13 (@ml-engineer, not an approval): contributor sections 1.1, 2.1 (@pm) and 8.3 (@actuary) are filled; 15 of 16 criteria ticked against the document. Not ticked: "Scaling plan and cost model", for its last clause only, "list prices labeled with date": the five prices in 8.3 are from memory (2025), not read from the provider's list, and D-038 item 5 names no Gemini version (document section 12, Q2). Needed from @user: the version, and the five list prices with the date read (or leave for one read of the price pages); then @actuary updates 8.3 and the task goes to review. The Groq limits in 3.1 are the host's figures as recorded in team files (`team/TASKS.md:715`, `team/DECISIONS.md:228`), not a saved raw reply; that box is ticked on that basis and the reviewers are told. 2026-10-13, @pm: @compliance added to Reviewers on the user's instruction (D-046: "Add @compliance as a reviewer of system-design.md."); the earlier line "@compliance is not a reviewer" no longer holds. D-047: one read of the official Google Vertex AI and Document AI pricing pages is allowed, for the cost model in 8.3 (@actuary), recording the date read and the exact model versions (Gemini 2.5 Flash and Pro unless D-038 says otherwise); this amends "no network call" for that one read only, D-011 (no paid API) stands, and the cost model proposes no purchase. D-049: the accuracy floor is decided, not assumed: D-013 (9/10 every field) is the pilot floor on synthetic data; the production floor is set later on real anonymized files by @head-of-underwriting and @model-risk, and none exists yet. No box ticked or unticked and no status changed by this edit. 2026-10-13, @ml-engineer (owner's closing pass, not an approval): set IN_REVIEW; reviewers @software-engineer, @model-risk, @compliance. 16 of 16 criteria ticked against the document. The last box, "list prices labeled with date", is ticked because 8.3 now carries five prices read on 2026-10-13 from the dated captures in `deliverables/architecture/sources/` (D-047); 7 price rows checked against the two source files and 44 dollar cells recomputed, all agree; two units are inferred from the pages and labeled so, and the Flex/Batch and Priority prices were not read. D-045, D-046, D-048, D-049, D-050, D-051 are quoted where they apply. As-is statements and citations for `ai/prepare.py`, `ai/eval_holdout.py`, `app/package.py`, `app/workbench.py` are reconciled to `dd45467`. The stubbed test file was run again, unchanged, at `dd45467`: run 1 (13:28, code as at `d5750fd`) 24 pass, 11 fail (known gap); run 2 (18:30) 22 pass, 7 fail (known gap), 1 fail (as-is: the real token log grew from 13 to 28 call rows), 5 errors (the test calls predate T-071's signatures). Run 1 files kept; run 2 saved as `results/stubbed-results-dd45467.json` and `stubbed-run-dd45467.txt`. For the reviewers: at `dd45467` the as-is claims for F15, F18, the missing decision-log check, and concurrent decision appends rest on reading the code, not on a test (document 10.1.1, S14); the test file was not edited. No file under `underwriting_pipeline/` or `simulation/` changed; no model call; no network call by the owner.

### T-096 — low-level-design.md: how it is built
- Owner: @software-engineer
- Requested by: @user
- Status: IN_REVIEW
- Priority: P1
- Depends on: T-094
- Reviewers: @ml-engineer, @model-risk
- Acceptance criteria:
  - [x] Module and class map of underwriting_pipeline/ with responsibilities
  - [x] Exact function signatures and data models (fields, types, required/optional) for every contract in architecture.md
  - [x] Workbench HTTP endpoints: method, path, request, response, errors
  - [x] Every validation gate: inputs, exact rules, outputs, and which test proves it
  - [x] Status enum and allowed state transitions in code
  - [x] Error handling and logging per module
  - [x] For each approved proposal (P-006, P-011, P-015, P-016, P-017): exact code changes required. P-010: document as built
  - [x] Test cases per gate and per contract; the 11 failing stubbed tests become acceptance tests for the gaps
  - [x] @software-engineer reconciles all citations in architecture.md and low-level-design.md to the current commit before review (D-046)
  - [x] The document has Mermaid diagrams
  - [x] The document separates "As-is (code today)" from "Target (production)"
  - [x] Every claim about current code cites file and line
  - [x] Every number is labeled measured (with source file) or assumed (with reasoning)
  - [x] Known gaps from DEMO-BLOCKERS.md and open vetoes are listed honestly, not hidden
  - [x] Documentation only: no pipeline code changes, no model calls
- Output: deliverables/architecture/low-level-design.md
- Notes: Requested by @user on 2026-10-13, title "HOW IT IS BUILT". INCOMPLETE CRITERIA: the user's message was cut off after "Workbench HTTP endpoints: method," and nothing after that was received. The rest of that bullet and any bullets after it are pending from @user. @pm did not guess them; the list above is only what arrived. The task is not sent to review until @user has given the rest and @pm has added it here. Work on the first two bullets does not need the missing text. Priority: P1, below every demo blocker (all P0); "It runs alongside the demo blockers and must not delay them." The user named two leads, @software-engineer and @ai-engineer-assistant. A task has one Owner: @software-engineer, because the decision-rights table gives "Application integration, APIs, UI" to @software-engineer and the document covers the whole of `underwriting_pipeline/` and the workbench endpoints. @ai-engineer-assistant is co-lead and writes the map, signatures, and data models for `underwriting_pipeline/ai/`; @software-engineer writes `underwriting_pipeline/app/` and the rest, and the single document. Reading code and writing in deliverables/ needs no approval (D-017); no file under `underwriting_pipeline/` is edited. Depends on T-094 because the second bullet is "for every contract in architecture.md". @software-engineer's seven blocker tasks and @ai-engineer-assistant's blocker builds come first. Not a production approval. Reviewers get the task id, these criteria, and the path, nothing else. 2026-10-13, @software-engineer: set IN_PROGRESS. First pass of `deliverables/architecture/low-level-design.md` written for the two bullets received in full: the module and class map, and the signatures and data models for the contracts of architecture.md that live in `app/` and `models/` (C1, C9 to C14). The parts for `underwriting_pipeline/ai/` (C2 to C8, C15) are blocks marked CONTRIBUTOR PLACEHOLDER for @ai-engineer-assistant, with a HANDOFF in team/DISCUSSION.md. Section 3, the workbench HTTP endpoints, is a heading and a pending note only: the specification has not arrived from @user and was not guessed. No box is ticked. Not sent to review. No file under `underwriting_pipeline/` or `simulation/` changed. 2026-10-13, @pm: THE MISSING TEXT ARRIVED (D-046). The "INCOMPLETE CRITERIA" note above no longer holds: the cut-off third bullet is replaced by the user's six bullets from D-046, copied, and the user's citation line is added as a criterion ("@software-engineer reconciles all citations in architecture.md and low-level-design.md to the current commit before review"); @pm added no criterion of its own. The criteria are now complete, so the hold on review for missing text is lifted; the task goes to review when the owner has met them, per the user: "Then finish T-095 and T-096 and send them to review." "Exact code changes required" is documentation and builds nothing (D-046 Amends); a change under `underwriting_pipeline/ai/` still needs its own "approve change P-###". The state transitions include the exits from `all_values_rejected` set by D-048. No box ticked or unticked and no status changed by this edit. 2026-10-13, @software-engineer: the lead's parts for the D-046 criteria are written in `deliverables/architecture/low-level-design.md`, at commit `dd45467`: section 3 (workbench HTTP endpoints: method, path, request, response, errors), section 9 (status enum; where each value is set and read; transitions the code allows; an as-is and a target state diagram with the D-048 exits and the D-050 rule), section 10 (error handling and logging, `app/` and `models/`), section 11 (P-010 as built, the app part), section 12 (P-006, P-011, P-015, P-016, P-017: the changes in `app/` and `models/`; documentation, builds nothing), section 13 (test cases per contract; the 11 failing stubbed tests as acceptance tests, from both result sets: 7 still fail, 3 error at `dd45467`, 1 passes), section 14 (the reconciliation and its counts). Every citation is re-pointed to `dd45467`: 1,770 citations, 0 out of range. Six diagrams, all rendered without error. Open, for @ai-engineer-assistant: seven blocks marked CONTRIBUTOR PLACEHOLDER (P6 validation gates; P7 and P7b status under `ai/`; P8 errors and logging; P9 P-010 `ai/` part; P10 proposals' `ai/` parts; P11 tests per gate and for the `ai/` contracts), and the stale statements in their sections listed in 14.3. No box is ticked. Status stays IN_PROGRESS; not sent to review. The stubbed test file was not edited. No file under `underwriting_pipeline/` or `simulation/` changed; no model call; no commit. 2026-10-13, @software-engineer (closing pass; the owner's check, not an approval): set IN_REVIEW and the 15 boxes ticked. `HEAD` is `dd45467` (measured: `git rev-parse --short HEAD`), the commit the document describes. No contributor placeholder block remains; the co-lead filled all seven (its ANSWER Re: T-096). The lead's out-of-date lines are updated against the board and the committed code: top status, section 7, 4.1 and 4.2 (T-071 DONE; the T-059 veto lifted by its holder, so five open vetoes on four tasks; T-020 stands), section 5, 11.4, the `:700` citation in 12.4 (now `:701`), rows 2 and 4 of 13.3, and 14.2 to 14.6. Measured with one script, 2026-10-13: 2,483 file-and-line citations (580 in the lead's sections, 1,903 in the co-lead's), 0 out of range, 0 naming a missing file, every file under `underwriting_pipeline/` measured at `dd45467` with `git show`. This replaces the 1,770 above, which was before the co-lead's blocks. Correction to the counts above, written in 14.2: of the 562 the script re-pointed, 139 in the co-lead's sections 2.2 to 2.5 were citations into `ai/llm_extract.py` that the script wrongly moved; the co-lead restored them. Six Mermaid diagrams, six rendered without error (Mermaid CLI 12.0.0), none changed. Limits a reviewer should know, each written in the document (14.6): the range check does not read a line against its sentence, and 941 of 1,512 bare citations are in range in more than one file; the lead did not read the co-lead's seven new blocks against the code line by line; for 11 of the 29 validation gates no test exists and section 8 says so; 12.6 lists what each approved proposal leaves unset, P-006 most, and the document does not choose it. Found at the closing pass and not this task's: `underwriting_pipeline/app/package.py` has an uncommitted edit in the working tree whose text names T-079 (measured: `git status --short underwriting_pipeline simulation`). This turn did not make it, did not touch it, and the document does not describe it. `architecture.md` (T-094) still shows T-071 as TODO and the T-059 veto as open and was not edited this turn. No file under `underwriting_pipeline/` or `simulation/` was changed by this turn; the stubbed test file was not edited; no test, scorer, or model call; no network call; no commit.

### T-097 — Requirements register: functional and non-functional
- Owner: @pm
- Requested by: @user
- Status: DONE
- Priority: P1
- Depends on: —
- Reviewers: @software-engineer, @model-risk, @compliance, @head-of-underwriting, @responsible-ai
- Acceptance criteria:
  - [x] One register for the Sanger & Altgelt insurance pilot, functional requirements apart from non-functional
  - [x] Reaches the whole system: every one of the thirteen components of T-094 and all eight steps of D-004
  - [x] Every requirement has a stable id (`FR-###` / `NFR-###`), a priority, a source, an owner, a verification, and a state
  - [x] The standing rules hold throughout: no auto-decline/bind, no AI send, `extraction_failed`, `all_values_rejected`, frozen scores, no paid API, `approve change`, synthetic data only
  - [x] As-is apart from Target; every number labeled measured (with source) or assumed (with reasoning and the deciding role)
  - [x] Points where no owner or no number is recorded are listed and the deciding role named, not chosen
  - [x] Documentation only: no pipeline code changes, no model calls, no scorer or score file touched
- Output: deliverables/pm/requirements.md
- Notes: Requested by @user on 2026-10-13: "note down what is our system functional requirements vs non functional requirements, store them properly, and it should be proper and reach across whole system and make them clear." Scope fixed by D-004: the insurance pilot only, not the wider Rytera mortgage/lending verticals, and not the superseded carrier auto-quote band (D-002/D-003 withdrawn by D-004; the `authority-matrix.md` auto-quote band is not a requirement here). FR-001 to FR-072 in sections A.1 to A.15; NFR-001 to NFR-055 in sections B.1 to B.13; cross-reference (C), gaps (D), maintenance (E). Component names and section citations are @software-engineer's T-094 (at commit `d5750fd`); @pm added no requirement of its own. Sources are `D-###`, `T-###`, the named deliverables, `arch §n`, and the user's words. Priority P1, below every demo blocker (all P0); this task does not delay them and changes no blocker's status. Documentation only: no file under `underwriting_pipeline/` or `simulation/` changed, no model call, no scorer run, no score file touched. Not a production approval; no veto is lifted. Open questions routed, not decided: Q1 to Q4 from T-094 (owners for missing-info drafts, decision log, eval harness); whether D-017 item 3's "complete" was meant for producer requests (Q9; it changes FR-025 and NFR-020). Reviewers get the task id, these criteria, and the path, nothing else. 2026-10-13, @pm, revision after review: all five reviewers returned APPROVE WITH CHANGES with no veto on T-097. Applied every required change. Convergent High: the open @compliance veto on T-020 (`package.py`, misrepresentation to a carrier; `arch §8.2` items (a)–(f)) now marks NFR-029 and FR-055–FR-059 `Open` and is named in Section C, noting D-035 moved (c) and (e) onto the demo path. Citation fixes: FR-021 → `data-model.md:39` / `arch §5.3.1`; FR-030 → `P-012 (D-026)`; FR-035, FR-040, FR-045 name `team/DEMO-BLOCKERS.md` and no longer cite gaps G5/G9; NFR-012 restated as a ten-row total; NFR-008 `ops` → `test (planned)`. NFR-035 now cites `agency-register.md` (T-022), not the draft `regulatory-register.md`. `data-use-review` cited on NFR-022/024/027/031/032 and the S-08 bans added. Section C demo-blocker list completed by line and the open veto added. NFR-005/NFR-055 volumes labeled ASSUMED. NFR-027 restated Partial and realigned to `data-model.md:45` / `fairness-test-plan`; NFR-036 now "fairness and contestability". New rows: NFR-056 (proxy review), NFR-057 (name-swap counterfactual), NFR-058–NFR-061 (pilot success metrics and go/no-go, section B.14). FR-039/FR-071 withdrawn-band wording fixed; FR-070/NFR-043 `Built (rule)`, NFR-033 `Built (rule — no rating engine exists)`. Source legend completed (`data-model`, `data-use-review`, `fairness-test-plan`, `proxy-review`, `api-spec`, `workbench-ux`, `roadmap`); no unused entry remained to remove. Register now 72 FR + 61 NFR. Status stays IN_REVIEW — I do not self-approve; no veto is lifted. Q9 left open and routed to @user. Five TYPE: ANSWER messages and one UPDATE re-request posted to DISCUSSION.md. 2026-10-13, @pm, closed DONE: all five reviewers returned a confirmation TYPE: REVIEW with verdict APPROVE on the current deliverable (no High findings, none a veto, none a production approval): @model-risk, @compliance, @responsible-ai, @software-engineer, @head-of-underwriting. All seven acceptance criteria are ticked and none was shown to fail; the deliverable was not changed by this close. The five approvals lift no veto: the T-020 veto (@compliance), the T-017 vetoes (@model-risk, @responsible-ai), the T-027 veto (@model-risk), and the void/retired T-026 extractor veto (@model-risk) all stand, and this is not a production approval. Open follow-ups tracked, not decided here: Q9 (whether D-017 item 3's "complete" was meant for producer requests) stays with @user (register D-5); the NFR-058–NFR-061 success-metric and go/no-go numbers are @head-of-underwriting's (register D-2); lifting the T-020 veto is @compliance's, recorded in team/BACKLOG.md (B-153).

### T-098 — Account-manager rule for producer requests (D-050)
- Owner: @software-engineer
- Requested by: @user
- Status: TODO
- Priority: P1
- Depends on: T-071
- Reviewers: @compliance, @account-manager, @senior-underwriter
- Acceptance criteria:
  - [ ] "complete" applies to carrier sends only: a producer request is not refused because the file is not complete
  - [ ] The account manager approves a producer request when it lists only truly missing items
  - [ ] The account manager approves a producer request only when the file is not extraction_failed or all_values_rejected
  - [ ] The account manager approves a producer request only when it contains no decline language
  - [ ] Carrier sends are unchanged: complete, in appetite, no open conflicts, no unread pages, written reason
  - [ ] No AI role approves or sends
- Output: underwriting_pipeline/app/package.py
- Notes: Raised by @pm on 2026-10-13 as the follow-up D-050 names ("@pm raises the build task for the app-side rule (@software-engineer)"). The criteria are the words of D-050 only; @pm added none, and how each one is checked in code is @software-engineer's to design (decision rights: application integration) and to state in the handoff. Context from D-050: as coded at `d5750fd` (`underwriting_pipeline/app/package.py:46-47`) the account manager can approve no producer request, because a producer request exists only for an incomplete file. Priority: P1, below every demo blocker (all P0); it is not a line in `team/DEMO-BLOCKERS.md` and @pm does not add one. If the demo path must show an account-manager-approved producer request, that is for @user to say and the priority changes then. @software-engineer's blocker tasks come first. Depends on T-071 because the rule reads the saved status the way T-071 built it. App side only: if the rule cannot be met without a change under `underwriting_pipeline/ai/` (the draft, or `prepare.approve()`), the owner stops and that part goes to a numbered proposal and the user's "approve change P-###" (D-017). The role texts that restate the old rule (CLAUDE.md, `.claude/agents/account-manager.md`, `.cursor/rules/`) are the user's to update and are not part of this task. Authorizes no send; lifts no veto; not a production approval. Reviewers get the task id, these criteria, and the path, nothing else.

### T-022 — Agency regulatory register
- Owner: @compliance
- Requested by: @pm
- Status: DONE
- Priority: P0
- Depends on: —
- Reviewers: @head-of-underwriting, @responsible-ai
- Acceptance criteria:
  - [x] Agency (not writing company) duties for a Texas placement pipeline
  - [x] Items needing real legal confirmation flagged
- Output: deliverables/compliance/agency-register.md
- Notes: Accepted by @head-of-underwriting and @responsible-ai. Not a legal opinion. Replaces T-005.

### T-023 — Score use and carrier-appetite fit
- Owner: @actuary
- Requested by: @pm
- Status: DONE
- Priority: P1
- Depends on: —
- Reviewers: @head-of-underwriting
- Acceptance criteria:
  - [x] What the score may and may not do
  - [x] How carrier appetite differs from the score
- Output: deliverables/actuary/score-use.md
- Notes: Accepted by @head-of-underwriting. Supersedes the use of T-011.

### T-024 — Gold answers for the 10-submission eval set
- Owner: @senior-underwriter
- Requested by: @user
- Status: DONE
- Priority: P0
- Depends on: —
- Reviewers: @model-risk, @ai-engineer
- Acceptance criteria:
  - [x] One expected answer per SUB-007 through SUB-016
  - [x] Each answer states missing items, conflicts with both sides, and the carrier recommendation
  - [x] None of the answers is an automatic decline
- Output: deliverables/senior-underwriter/gold-set/
- Notes: Scored 2026-10-09. The set is the expected answer. It is not a production approval of the extractor. D-009 says this score is not proof. The hold-out gold is T-025.

### T-025 — Gold answers for hold-out SUB-017 through SUB-026
- Owner: @senior-underwriter
- Requested by: @user
- Status: DONE
- Priority: P0
- Depends on: —
- Reviewers: @model-risk
- Acceptance criteria:
  - [x] One expected answer per new submission, written before extraction ran
  - [x] Formats covered: text PDF, scanned-style PDF, Excel, email body, Spanish
  - [x] None of the answers is an automatic decline
- Output: deliverables/senior-underwriter/gold-set/SUB-017.md through SUB-026.md
- Notes: Written 2026-10-09 before eval_holdout.py ran.

### T-026 — Hold-out extraction score
- Owner: @ai-engineer-assistant
- Requested by: @user
- Status: DONE
- Priority: P0
- Depends on: T-025
- Reviewers: @model-risk, @senior-underwriter
- Acceptance criteria:
  - [x] prepare.py unchanged for the run
  - [x] Per-field accuracy reported, including failures
  - [ ] @model-risk accepts the component
- Output: deliverables/ai-engineer/evals/SUB-017-026-holdout.md
- Notes: Identity fields are 0/10. @model-risk's note is deliverables/model-risk/holdout-SUB-017-026.md. Not a production approval. 2026-10-11: owner handle changed from the retired @ai-engineer to @ai-engineer-assistant (D-017). No other change. 2026-10-11, @pm: closed under D-036, in the user's words: "scored, component not accepted — retired under D-010". Box 3 stays unticked; D-036 says it can never be met. Recorded as the reviewers wrote it: @senior-underwriter, REVIEW, "Verdict: APPROVE, as the record of a failure. No High." @model-risk, OBJECTION, "Score record: accepted", "Component: NOT accepted. Production veto on the extractor as scored." "(1) prepare.py unchanged, not checkable from git; my 2026-10-09 hash is the only evidence. (2) met. (3) not met." This score is quoted only as "0 of 7 value fields; other hits came from empty output" and is never cited for the current extractor (D-036). The extractor is recorded as retired in deliverables/model-risk/model-inventory.md: T-089. This close does not lift the veto on the retired extractor; that is @model-risk's call once the inventory entry exists. The published score file is not edited (D-025). Medium and Low: B-035 and B-112 to B-121; the High finding is B-143. @pm gives no verdict.

### T-027 — Read PDF, Excel, prose, and Spanish with a model
- Owner: @ai-engineer-assistant
- Requested by: @user
- Status: IN_REVIEW
- Priority: P0
- Depends on: T-026
- Reviewers: @model-risk, @senior-underwriter
- Acceptance criteria:
  - [x] PDFs read with pdfplumber, Excel with openpyxl, scans with OCR
  - [ ] An LLM returns structured JSON with a citation and a confidence on every field
  - [ ] Confidence under 0.75 is dropped instead of guessed
  - [x] The key is OPENAI_API_KEY from the environment and is not stored in the repo
  - [x] A hold-out score from a successful model call
- Output: underwriting_pipeline/ai/llm_extract.py, underwriting_pipeline/ai/sources.py
- Notes: D-010 and D-012. The first paid-key call returned HTTP 401. The Groq call on openai/gpt-oss-120b succeeded and T-029 recorded that score. SUB-017 through SUB-026 are the development set. Do not count a null as a hit. 2026-10-11: owner handle changed from the retired @ai-engineer to @ai-engineer-assistant (D-017). No other change. 2026-10-11, @pm, round wrap-up, recorded as the reviewers wrote it: @senior-underwriter, REVIEW, "Verdict: REJECT. Criterion 2 fails for an underwriter: a citation must be the text the value came from." @model-risk, OBJECTION, "Verdict: REJECT. Production veto on extraction stands." "(1) readers: met for typed PDF, Excel, image scans; (2) citation: not met; (3) 0.75 gate: not met on scans; (4) key: met as amended by D-011 and D-012 (LLM_API_KEY, no key in any tracked file); (5) hold-out: a score exists, but not for this code." Boxes 2 and 3 are unticked for that reason. Box 5 is left as it was with @model-risk's words beside it. The veto is open. D-037 (user): all four things @model-risk says resolve it are accepted and on the demo path. (a) citations, (b) confidence, (c) unread content: one proposal, P-016, T-080; not written, not approved, not built. (d) a new 20-file hold-out after (a) to (c) are frozen and committed: T-091, T-092, T-093. Lines 3 and 9 of team/DEMO-BLOCKERS.md. Medium and Low: B-036 to B-038 and B-122 to B-137. Stays IN_REVIEW. Lifting the veto is @model-risk's call (D-037). @pm gives no verdict. 2026-10-19, @model-risk, gate memo after the official T-108 run (SUB-206-237, `deliverables/ai-engineer/evals/SUB-206-237-holdout-v7.{md,json}`): **Verdict KEEP — the T-027 veto is not lifted.** Run integrity holds (code `457f1bf`, prompt `759b3e6bc9b2`, scorer v7, gold manifest `11933e96…`, single run/score, 0 call_failed) and the T-027 route gate PASSES (0 unsafe, 18/20), but the P-055 scope gate FAILS (1 leak SUB-233: fields, provisional route, automated draft, send enabled; recall 11/12) and two fields are below the 18/20 floor (operations 9/20, loss_runs 5/20). Memo `deliverables/model-risk/T-027-memo.md`; High H1 (scope detector, backlog B-432) and H2 (operations/loss-run completeness, B-433). Resolves only when: fixes on dev with @model-risk checks (no High), code and scorer re-frozen and hashed, a fresh 20+12 hold-out gold-first and lint-passing, run once and scored once meeting every gate-table criterion (all 9 fields ≥ 18/20, 0 false completes, 0 unsafe, 0 leaks, 100% recall). An approved P-### is not a production approval. 2026-10-21, @model-risk, T-027 memo after the official T-117 run (SUB-238-269, `deliverables/ai-engineer/evals/SUB-238-269-holdout-v11.{md,json}`, run `05c3110`): **Verdict KEEP — the T-027 veto is not lifted.** Run integrity holds; safety gates pass (0 false completes, 0 unsafe, route 19/20, 0 leaks, recall 12/12); operations 13/20 and loss_runs 16/20 fail the 18/20 floor. Highs H1 (cooking line dropped, B-451), H2 (0/3 planted conflicts, B-452), H3 (Carrier C build format, B-453). Memo `deliverables/model-risk/T-027-memo-T-117.md`. Resolves only when H1/H2 are fixed on dev under approved P-### with a @model-risk check (no High), the H3 lint rule and a v-next scorer are frozen and hashed, and a fresh 20+12 hold-out (look-again on every gold fix) is run and scored once meeting every gate plus planted-conflict recall 100%. 2026-10-24, @model-risk, T-027 memo after the official T-119 run (SUB-340-371, `deliverables/ai-engineer/evals/SUB-340-371-holdout-v11.{md,json}`, run 20261024T000318-70195, D-130): **Verdict KEEP — the T-027 veto is not lifted.** Run integrity holds; safety gates pass (0 leaks, recall 12/12, 0 false completes, 0 unsafe, route 20/20, loss runs 20/20). Fails: operations 9/20 (H1, B-468; 9 dropped "Cooking operations: None", D-127) and planted-conflict recall 2/3 (H2, B-469; SUB-345 sales conflict raised by the model, discarded by the pipeline, file passes the send gate as "complete — review pending"). Memo `deliverables/model-risk/T-027-memo-T-119.md`. Resolves only when H1/H2 are fixed under approved P-### with a @model-risk check (no High), a v-next scorer is re-frozen, and a fresh 20+12 hold-out with at least 5 measurable planted conflicts meets every gate plus planted-conflict recall 100%.

### T-028 — Gold answers for hold-out SUB-027 through SUB-036
- Owner: @senior-underwriter
- Requested by: @user
- Status: DONE
- Priority: P0
- Depends on: —
- Reviewers: @model-risk
- Acceptance criteria:
  - [x] One expected answer per submission, written before the score ran
  - [x] None of the answers is an automatic decline
- Output: deliverables/senior-underwriter/gold-set/SUB-027.md through SUB-036.md
- Notes: Written 2026-10-09 before eval_holdout_027.py ran.

### T-029 — Score hold-out SUB-027 through SUB-036
- Owner: @model-risk
- Requested by: @user
- Status: DONE
- Priority: P0
- Depends on: T-027, T-028
- Reviewers: @ai-engineer-assistant, @senior-underwriter
- Acceptance criteria:
  - [x] Scored without editing the scorer after the gold files existed
  - [x] A null that matches missing is not counted as correct
  - [x] The score comes from a successful model call
- Output: deliverables/ai-engineer/evals/SUB-027-036-holdout.md, deliverables/model-risk/holdout-SUB-027-036.md
- Notes: 2026-10-10 rerun on openai/gpt-oss-120b. Calls succeeded. Not a production approval. Named insured, premises, and year built are 10/10. Operations 6/10, sales 9/10, TIV 8/10, construction 7/10, loss runs 3 hit / 3 miss / 4 not credited, conflict 9/10, status 7/10. Nulls on missing loss runs were not counted as hits. This is the D-013 baseline. A later development rerun is a different file and does not replace these counts. 2026-10-11: reviewer handle changed from the retired @ai-engineer to @ai-engineer-assistant (D-017). No other change. 2026-10-11, @pm, round wrap-up, recorded as the reviewers wrote it: @senior-underwriter, REVIEW, "Verdict: APPROVE. No High." "I could not recount this one: there is no SUB-027-036-holdout.json" @ai-engineer-assistant, REVIEW, "Verdict: APPROVE, as the record of the D-013 baseline. No High." "Criterion 2: met. Criteria 1 and 3: no saved file shows them either way." Both reviewers approved, so this is closed. No box was shown to fail; the boxes stay as they were, with the reviewers' limits beside them. @senior-underwriter: "The limit in my T-053 review (High-2) applies": effective date was never scored. Wherever this score is quoted it says "8 of 9 fields scored; loss runs = date only" (D-033 item 5). Medium and Low findings are in team/BACKLOG.md (B-039 to B-052, B-056). Not a production approval. @pm gives no verdict.

### T-030 — Improve extraction on the development set
- Owner: @ai-engineer
- Requested by: @user
- Status: DONE
- Priority: P0
- Depends on: T-027, T-029
- Reviewers: @model-risk
- Acceptance criteria:
  - [x] Scanned pages are preprocessed before OCR
  - [x] Spanish forms, email prose, and loss-run dates are in the extraction instructions
  - [x] A loss-run date without a citation is still dropped
  - [x] SUB-017 through SUB-036 were the only files used to change the extractor
- Output: underwriting_pipeline/ai/sources.py, underwriting_pipeline/ai/llm_extract.py, deliverables/ai-engineer/evals/SUB-017-036-dev-rerun.md
- Notes: D-013. Frozen before SUB-037 existed.

### T-031 — Gold answers for hold-out SUB-037 through SUB-046
- Owner: @senior-underwriter
- Requested by: @user
- Status: DONE
- Priority: P0
- Depends on: T-030
- Reviewers: @model-risk
- Acceptance criteria:
  - [x] One expected answer per submission, written before the score ran
  - [x] None of the answers is an automatic decline
- Output: deliverables/senior-underwriter/gold-set/SUB-037.md through SUB-046.md
- Notes: Written 2026-10-10 before eval_holdout_037.py ran.

### T-032 — Score hold-out SUB-037 through SUB-046
- Owner: @model-risk
- Requested by: @user
- Status: DONE
- Priority: P0
- Depends on: T-030, T-031
- Reviewers: @ai-engineer-assistant, @senior-underwriter
- Acceptance criteria:
  - [x] Scored without editing the scorer after the gold files existed
  - [x] A null that matches missing is not counted as correct
  - [x] The score is compared with the first SUB-027 through SUB-036 score
  - [x] The score comes from a successful model call
- Output: deliverables/ai-engineer/evals/SUB-037-046-holdout.md, deliverables/model-risk/holdout-SUB-037-046.md
- Notes: 2026-10-10. Calls succeeded. Not a production approval. Named insured, premises, sales, TIV, year built, and status are 10/10. Operations, construction, and conflict are 9/10. Loss runs are 6 hit, 0 miss, 4 not credited. SUB-040 and SUB-044 are the misses. 2026-10-11: reviewer handle changed from the retired @ai-engineer to @ai-engineer-assistant (D-017). No other change. 2026-10-11, @pm, round wrap-up, recorded as the reviewers wrote it: @senior-underwriter, REVIEW, "Verdict: APPROVE. No High." @ai-engineer-assistant, REVIEW, "Verdict: APPROVE. No High." "Criterion 1: no commit shows it (B-045)" Both reviewers approved, so this is closed. No box was shown to fail; the boxes stay as they were, with the reviewers' limits beside them. @senior-underwriter: "The limit in my T-053 review (High-2) applies": effective date was never scored. Wherever this score is quoted it says "8 of 9 fields scored; loss runs = date only" (D-033 item 5). Medium and Low findings are in team/BACKLOG.md (B-039 to B-052, B-056). Not a production approval. @pm gives no verdict.

### T-099 — Draft proposal P-019: switch model + OCR provider to Vertex AI (Gemini 2.5 Flash/Pro) and Document AI layout, replacing Groq/OpenAI host and Tesseract OCR
- Owner: @ai-engineer-assistant
- Requested by: @user (scope chosen by @user: "Hosting + Vertex/Document AI")
- Status: IN_REVIEW
- Priority: P0
- Depends on: —
- Reviewers: @model-risk, @compliance, @responsible-ai, @senior-underwriter
- Acceptance criteria:
  - [ ] Next id P-019; states the change in plain words, the trade-off, and the expected score/cost impact
  - [ ] Carries the unresolved D-011 conflict (D-011 says no paid API, and Vertex AI/Document AI are paid)
  - [ ] Proposal only, no code edited
  - [ ] States that it is implemented only on the user's exact line `approve change P-019`
- Output: deliverables/ai-engineer/proposal-P-019.md
- Notes: The change proposed is Vertex AI (Gemini 2.5 Flash/Pro) for the model and Document AI layout for OCR, replacing the current Groq/OpenAI host and Tesseract OCR. D-011 and D-047 (prices already captured in deliverables/architecture/sources/). Not authorized to build. Review is folded into this task: when the draft is posted the task goes IN_REVIEW and the listed reviewers give verdicts as fresh dispatches; no separate review task is opened because this turn only opens the work, and the protocol's independent-review rules apply unchanged.

### T-100 — Draft the GCP hosting migration design (Railway → GCP; keep infra/aws/ as reference)
- Owner: @ml-engineer
- Requested by: @user (scope chosen by @user: "Hosting + Vertex/Document AI")
- Status: IN_REVIEW
- Priority: P0
- Depends on: —
- Reviewers: @software-engineer, @compliance, @model-risk
- Acceptance criteria:
  - [ ] Maps each component (FastAPI api, Celery workers, Postgres+pgvector, Redis, ClamAV, object storage/audit, Prometheus/Grafana/OpenObserve, secrets) to a GCP service
  - [ ] States the pgvector-on-Cloud-SQL question as an open item to verify
  - [ ] Names what is decided vs not decided
  - [ ] No Terraform applied and no GCP resource created; a design deliverable only
- Output: deliverables/ml-engineer/gcp-migration.md (and, if useful, a proposed infra/gcp/ layout described in the file only — do NOT apply or create cloud resources)
- Notes: Mirror the pattern in infra/aws/ but this is a design first. D-011 stands. Review is folded into this task: when the draft is posted the task goes IN_REVIEW and the listed reviewers give verdicts as fresh dispatches; no separate review task is opened because this turn only opens the work, and the protocol's independent-review rules apply unchanged.

### T-101 — LOB expansion plan for the 29 InsuranceLine lines
- Owner: @head-of-underwriting
- Requested by: @user (relayed by @pm)
- Co-author: @pm
- Status: IN_REVIEW
- Priority: P2
- Depends on: —
- Reviewers: @pm, @senior-underwriter (UI/pipeline impact only), @compliance noted for the life & health expertise point
- Acceptance criteria:
  - [x] Groups all 29 enum lines into exactly these five families: small commercial P&C, specialty/professional, catastrophe, personal, life & health — every line appears in exactly one family, no line omitted
  - [x] Defines an "LOB pack" format: required fields, document types (ACORD section forms), carrier appetite rules, hazard/score rules, gold set, hold-out, and per-LOB score targets — states explicitly that the pipeline stays shared and each LOB is configuration plus its own evaluation
  - [x] Proposes underwriter specialist roles per family (not per line) and names shared roles needing extra expertise (e.g. @compliance for life & health)
  - [x] Gives a rollout order after the current pilot lines (BOP, property, GL — Texas), with a reason for each step: agency volume, similarity to current pipeline, risk
  - [x] Lists what must never be shared across lines (scores, gold sets, appetite rules, and any others found)
  - [x] Under 2 pages
  - [x] No new agents created, no code changed
  - Output: deliverables/pm/lob-expansion-plan.md
- Notes: P2 because it is not a demo blocker (budget rule 8: demo blockers only while the weekly budget is low). Planning document only — no code, no new agents. @pm wrote the skeleton (title and five section headers) and the rollout rationale; @head-of-underwriting fills in families, pack format, roles and appetite content. Handoff posted in team/DISCUSSION.md.


### T-102 — Hold-out SUB-127–146: the planned mix (written before any file exists)
- Owner: @producer (files), @senior-underwriter (gold first)
- Requested by: @user (D-091 item 3)
- Status: IN_PROGRESS (files and gold built; pipeline NOT run). Gold frozen at commit bd9168e13fcd91a4e64421a69b1d8284798ab01a (2026-10-15, D-092 item 4).
- Priority: P0
- Depends on: T-027 veto path; P-044 (D-090); eval_holdout_127.py (committed before any gold)
- Reviewers: @model-risk (approves the mix)
- Acceptance criteria:
  - [ ] 20 files. Loss runs: **8 carrier-format** (Carrier A 3, B 3, C 2, exactly per simulation/carrier-loss-run-formats.md), **6 non-carrier**, **6 none**.
  - [ ] Carrier-format loss-run formats: 3 typed PDF (text layer), 2 typed text (.md), 2 scans as JPG (1 greyscale, 1 colour, one of them rotated), 1 image-only PDF. No carrier-format loss run in xlsx: the xlsx reader joins cells with tabs, so the pipe-table layout cannot match (dev finding, D-091); xlsx is used for schedules only.
  - [ ] Non-carrier (6): 2 no-known-loss letters (1 English, 1 Spanish), 1 applicant letter that copies a carrier header **and contains a valued-as-of date** (so the P-044/P-045 gate is reached; M3), 1 agent summary that names a carrier, 1 unknown carrier layout, 1 carrier layout with the valued-as-of line missing.
  - [ ] One of the typed carrier-format runs uses that carrier's own no-claims line instead of a claims table (M4).
  - [ ] No line starting with "_" (no synthetic-data banner) inside any carrier-format loss-run document: P-045 counts every line, so a banner breaks the layout. Mark it FICTIONAL through the header only.
  - [ ] Scanned and spreadsheet loss runs are never auto-accepted in the pilot (B-343, D-092): the gold expects **needs review** ("loss run from scan/spreadsheet: check it") for the 2 JPG scans and the 1 image-only PDF. An xlsx carrier loss run would always go to review too (L2); none is planned.
  - [ ] The gold for the copied-header letter and for the carrier layout without a valued line follows D-092 (c): the loss run is missing with "loss run found but no valued-as-of date", and the expected pipeline status is incomplete (M-T102).
  - [ ] None (6): no loss-run document at all, 2 of them email-only submissions.
  - [ ] Gold follows the documents (M5): a clean file with a scanned carrier run can be gold-complete (Status: complete) while its expected pipeline status is review pending, which is safe but not automated. The 5 typed carrier-format files have no other planned gap (no conflict, missing field or scan elsewhere). Gold says complete or incomplete only (B-325). At least 5 files are gold-complete, so status automation is measurable; at least 5 of the gold-complete files carry a typed carrier-format loss run (L5: a clean scanned-run file may also be gold-complete, per M5) (a loss run read from a scan is always flagged for review, so a scanned run cannot be plain complete).
  - [ ] The rest of the hard mix as SUB-107–126: typed and scanned applications, Spanish, conflicts, multiple locations, restaurants with cooking lines, a bar, an over-cap TIV, a duplicate. Every route appears at least once in gold, including carrier_c and senior_referral.
  - [ ] All fictional. Gold is written and committed before any extraction; smoke_readers.py passes first; scored once, paced, by eval_holdout_127.py.
- Output: simulation/inbox/SUB-127 … SUB-146, deliverables/senior-underwriter/gold-set/SUB-127.md … SUB-146.md
- Notes: D-091. Plan only. No SUB-127–146 file exists when this was written. 2026-10-15, @model-risk: APPROVE WITH CHANGES on the mix (deliverables/model-risk/check-D-091.md), no High. Required before any file is created, not yet applied: M3 the copied-header letter contains a valued-as-of date so the P-044 gate is reached; M4 one typed carrier run uses the carrier's no-claims line; M5 gold follows the documents (a clean scan file can be gold-complete) and the 5 typed carrier files have no other planned gap; L2 state that an xlsx carrier loss run always goes to review. Status stays TODO until these are applied and @model-risk confirms. 2026-10-15, orchestrator (D-092 item 3): M3, M4, M5 and L2 applied above, plus the scan/image-only review rule and the no-banner rule; waiting for @model-risk to confirm. SUB-147–152 are development files for the P-044 accept path and are never part of this hold-out.

### T-103 — Hold-out SUB-154–173: the planned mix (plan only; written before any file exists)
- Owner: @producer (files), @senior-underwriter (gold first)
- Requested by: @user (D-095 item 3)
- Status: TODO. Plan only; do not build. No SUB-154–173 file or gold exists. Build only when the user says so.  2026-10-16 (D-101): built (33e399a), run and scored once (v4): 0 false completes, 0 unsafe, route 16/20, field floor not met; @model-risk T-027 memo KEEP. B-394–B-396.
- Priority: P0 (T-027 resolution path)
- Depends on: P-048 built and checked (D-095); operations gold rule (deliverables/senior-underwriter/operations-gold-rule.md); scorer v2 with the route column (eval_holdout_v2.py)
- Reviewers: @model-risk (approves the mix)
- Acceptance criteria:
  - [ ] 20 files. Loss runs as T-102: **8 carrier-format** (Carrier A 3, B 3, C 2, exactly per simulation/carrier-loss-run-formats.md), **6 non-carrier**, **6 none**. Formats: 3 typed PDF (text layer), 2 typed .md, 2 JPG scans (1 greyscale, 1 colour and rotated), 1 image-only PDF. No carrier-format run in xlsx. One typed carrier run uses the carrier's own no-claims line. No "_" banner line in any carrier-format run.
  - [ ] **8 gold-complete files, each with a carrier-format run, covering every send route:**

    | # | Business (fictional) | Loss run | Gold route | Expected status |
    |---|---|---|---|---|
    | 1 | office | Carrier A, typed PDF, claims table | carrier_a | complete |
    | 2 | dry retail | Carrier A, typed .md, no-claims line | carrier_a | complete |
    | 3 | restaurant (generic word, cooking line, no alcohol) | Carrier B, typed PDF | carrier_b | complete |
    | 4 | restaurant and bar, full liquor | Carrier B, typed .md | senior_referral (D-079) | complete |
    | 5 | apartments, sprinklered, TIV under $5M | Carrier C, typed PDF | carrier_c | complete |
    | 6 | café / bakery | Carrier B, JPG greyscale scan | carrier_b | review pending (P-048 b) |
    | 7 | apartments, not sprinklered | Carrier C, JPG colour, rotated | senior_referral (AG:61) | review pending (P-048 b) |
    | 8 | light wholesale | Carrier A, image-only PDF | carrier_a | review pending (P-048 b) |

    Files 1–5 have no other planned gap (no conflict, missing field or scan elsewhere).
  - [ ] **12 gold-incomplete files** (route scored as the provisional route, P-048 c):

    | # | Loss run | Other features | Gold route (provisional) |
    |---|---|---|---|
    | 9 | no-known-loss letter, English | office | carrier_a |
    | 10 | no-known-loss letter, Spanish | Spanish application, restaurant with cooking line | carrier_b |
    | 11 | applicant note under a copied carrier header **with a "Fwd:" or "> " prefix, letter words and a valued-as-of date** (B-350 probe) | roofing contractor | senior_referral (AG:38) |
    | 12 | agency summary naming a carrier | prohibited class (AG:45-49) | no_match |
    | 13 | unknown carrier layout | office, TIV over $5M | senior_referral (AG:16) |
    | 14 | carrier layout with the valued-as-of line missing | apartments, sprinkler answer not given | hold (no provisional route) |
    | 15 | none | email only, operations not stated | hold (no provisional route) |
    | 16 | none | Spanish email only, operations stated | per the written rules |
    | 17 | none | scanned application, 2 locations, a conflict | carrier_b (restaurant) |
    | 18 | none | duplicate resend of file 4 | senior_referral |
    | 19 | none | 3-location schedule, sprinklered apartments | carrier_c |
    | 20 | none | cuisine word only, no generic restaurant evidence (D-078) | no_match |

  - [ ] Every route appears in gold: carrier_a, carrier_b, carrier_c, senior_referral, no_match and hold. carrier_c and senior_referral each appear on at least one gold-complete file with a typed run (5 and 4), so they are reachable without a hold.
  - [ ] Gold follows the written appetite and referral rules (B-364), the operations gold rule, and the M5 convention ("not in documents"). The gold route is the route the written rules give once any hold clears; "hold" only when the documents cannot decide it.
  - [ ] Gold is written from the documents only by @senior-underwriter (not by anyone who changed the code), committed and frozen before any extraction. smoke_readers.py passes first. .venv python, paced, scorer v2, run and scored once on a frozen commit (T-027 path: all 9 fields 9/10 or better, 0 false completes). Live and cache outputs kept apart (B-363).
- Output: simulation/inbox/SUB-154 … SUB-173, deliverables/senior-underwriter/gold-set/SUB-154.md … SUB-173.md
- Notes: D-095 item 3. Plan only. 2026-10-16, @model-risk: APPROVED WITH CONDITIONS (deliverables/model-risk/check-P-048.md): (1) file 8 states its commodities are not hazardous; (2) file 11 states a TIV; (3) one non-carrier run is a JPG scan of an applicant note under a copied carrier header (probe M1; which non-carrier slot it replaces is settled with @model-risk before any file is built); (4) build only after P-048 H1 is closed. Not built; the user decides when.

### T-104a — P-055 out-of-scope detector and manual-intake card
- Owner: @ai-engineer-assistant · Status: DONE · Decision: D-105 (approve change P-055 rev 3)
- Acceptance criteria:
  - [ ] Deterministic detector, no model call, versioned and entered in deliverables/model-risk/model-inventory.md (Tier 2) before use.
  - [ ] Criteria 1–4 exactly as in deliverables/pm/proposal-P-055.md; fail closed (error, unsure language count, unknown text layer, no identifiable application → manual intake).
  - [ ] An out-of-scope file is manual intake as a whole file: no field shown complete, no status complete / complete — review pending, no carrier, provisional or suggested route, no automated missing-info draft, send blocked with the reason. extraction_failed keeps precedence (D-021).
  - [ ] Workbench card lists every matched reason in plain language; send refusal shows the reason (D-065); What's new line; screenshot under deliverables/software-engineer/screenshots/ (temp copy, D-069).
  - [ ] Self-checks on dev files incl. SUB-142/143 (email-only, Spanish), a SUB-170-style scanned application, a SUB-172-style multi-location file, and in-scope boundary cases (scanned loss run + typed application, Spanish email beside English application, one-row schedule, mailing address). pyright on changed files.
- Output: code in underwriting_pipeline/, deliverables/ai-engineer/p-055-as-built.md

### T-104 — Hold-out (P-055): 20 in scope + 12 out of scope, gold only
- Owner: @producer (files), @senior-underwriter (gold) · Status: GOLD FROZEN, NOT RUN (code 1cf001f) · Decision: D-105, D-107
- Acceptance criteria:
  - [ ] Mix per P-055 "Next hold-out": 20 in scope with at least 6 boundary cases; 12 out of scope with at least 4 per criterion 1–3, at least 3 two-criteria files, a near-pass form per criterion, and at least 2 email-only / application-not-identified files (criterion 4).
  - [ ] Gold from documents and written rules only, scope label in every gold file, D-102 conventions ("not in documents"; hold is a status, never a route), operations checklist for scorer v5.
  - [ ] Gold frozen and committed, hash recorded. The pipeline is not run on T-104.

### T-104b — P-057 scorer v6 and P-058 numbered locations
- Owner: @ai-engineer-assistant · Status: DONE (re-frozen; @model-risk APPROVE, no High) · Decision: D-108
- Acceptance criteria:
  - [ ] Scorer v6 = v5 plus the P-055 measures: leakage 0 (any out-of-scope file shown complete, routed, or given an automated missing-info draft), detection recall 100% per criterion and overall, in-scope files wrongly sent to manual intake ≤ 2 of 20; v5 field scores and the route gate (0 unsafe, ≥ 18/20) on in-scope files. Built from the gold format only; no T-104 file or gold read. v4/v5 unchanged. Self-checks on dev data.
  - [ ] Detector catches numbered locations/buildings/premises ("Location No. 2", "Loc #2", "Building 2", "Bldg 2", "Premises 2", ...), version bumped; self-checks on dev; pyright on changed files.

### T-105 — Manager demo prep (no pipeline code changes)
- Owner: @senior-underwriter (files), @software-engineer (workbench + screenshots), @pm (guide, summary), @senior-test-engineer (rehearsal) · Status: DONE (rehearsal READY WITH FIXES; guide setup fixed by the orchestrator with run-demo.sh, re-run clean, 0 live calls, D-069 clean) · Decision: D-110
- Acceptance criteria:
  - [ ] 3 demo files from dev data, none from a hold-out: (a) messy in-scope file that reaches a carrier quote, (b) out-of-scope file sent to manual intake with a plain reason, (c) senior-referral file confirmed by a senior (P-052). Each runs cleanly on frozen code 6e7cfa2, 0 live calls where saved replies exist.
  - [ ] Workbench shows each cleanly; Playwright screenshots of each step in deliverables/software-engineer/screenshots/demo/, made on a temp copy (D-069). No pipeline code changes; problems are reported, not fixed.
  - [ ] deliverables/pm/demo-guide.md: 10-minute script for a non-technical manager, the 3 files listed, honest T-104 scores, cost per file and estimated time saved per submission with stated assumptions.
  - [ ] deliverables/pm/where-we-are.md: one page; what works, the 2 open gaps (operations details, routing rules), what production still needs (T-027 veto, SSO B-190, concurrent writes B-191, real carrier formats R-030), next steps.
  - [ ] Rehearsal: the guide dry-run step by step on a temp copy; everything that breaks is listed.

### T-106a — P-059 operations from cooking, hood and line-of-business lines
- Owner: @ai-engineer-assistant · Status: DONE (@model-risk APPROVE WITH CHANGES, no High; live check M1 owed) · Decision: D-111 (approve change P-059)
- Acceptance criteria:
  - [ ] The operations answer keeps items stated on "Cooking operations", "Hood & extinguishing system" and "Line of business" lines (and the "Operations" line), e.g. "no gas", "snack warmer", "no cooking", hood inspection dates, "no liquor".
  - [ ] The whole-document check flags any operations-rule item (the items the routing/appetite rules read) present in the documents but missing from the answer; flagged means needs review, never a silent value.
  - [ ] Self-checks on dev files only (no T-104 file or gold opened to tune); pyright on changed files; prompt/extraction version bumped and model-inventory.md updated.
  - [ ] Written explanation of why the existing check missed the 3 T-104 silent errors (SUB-180, 201, 204), from the code and the published mismatch file only.
- Output: code in underwriting_pipeline/, deliverables/ai-engineer/p-059-p-060-as-built.md

### T-106b — Routes check of the 4 T-104 route misses (report only)
- Owner: @head-of-underwriting · Status: DONE (report; P-061, P-062 drafted, not built) · Decision: D-111
- Acceptance criteria:
  - [ ] For SUB-174, 182, 186, 201: the pipeline route, the gold route, and what the written rules (carrier-match.md R1–R16, W1, W2, appetite guides) say, rule by rule.
  - [ ] Each miss classed "code wrong" (→ a proposed P-### fix, not built) or "gold wrong" (→ a gold lesson for future sets).
  - [ ] Nothing built; T-104 scores not changed.
- Output: deliverables/head-of-underwriting/T-104-route-check.md

### T-106c — P-060 scorer v7 (loss runs)
- Owner: @ai-engineer-assistant · Status: DONE (@model-risk APPROVE) · Decision: D-111 (approve change P-060)
- Acceptance criteria:
  - [ ] eval_holdout_v7.py = v6 plus: loss runs "correct" when the pipeline matches the gold expectation, including "needs review" when gold expects review; null + needs review where gold expects a date is "not credited", not a miss.
  - [ ] v6 (and v2–v5) unchanged, sha256 of v6 still 4bf1cd63…; published score files untouched.
  - [ ] Self-checks on dev data (temp cache copy, 0 calls, HOLDOUT_OUT in a temp folder); pyright on changed files.
- Output: underwriting_pipeline/ai/eval_holdout_v7.py, section in deliverables/ai-engineer/p-059-p-060-as-built.md

### T-106d — Test-file lint before any hold-out gold freeze
- Owner: @senior-test-engineer · Status: DONE (@model-risk H1, H2 closed in look-again 2; gate in RUN-RULES) · Decision: D-111
- Acceptance criteria:
  - [ ] One script checks a hold-out's files and gold: every loss-run valued date is before the run date; every gold Scope line is valid (same parse as scorer v6/v7); the mix matches the written plan (in/out counts, per-criterion counts, other plan counts given).
  - [ ] Exit non-zero on any failure with a plain reason per file; must pass before a gold freeze (added to RUN-RULES).
  - [ ] Self-check: passes on a clean temp set; fails on T-104's post-run-date loss runs (read-only, files only, no pipeline run).
- Output: script under underwriting_pipeline/ai/ or deliverables/senior-test-engineer/, note in deliverables/senior-test-engineer/T-106d-lint.md

### T-107a — P-061 class lines, P-062 nightclub/lounge R1, one prohibited-class table
- Owner: @ai-engineer-assistant (code), @head-of-underwriting (rules text) · Status: IN_PROGRESS · Decision: D-112 (approve change P-061, P-062)
- Acceptance criteria:
  - [ ] P-061: `_match()` reads the application's "Line of business:" and "Cooking operations:" lines (not the insured's name) for R9, R10, R14 and bar/prohibited words; stated cooking equipment in operations or the Cooking operations line is R9 evidence; R17 keeps reading the operations text only.
  - [ ] P-062: nightclub(s), lounge(s), hookah, adult entertainment, cannabis words stay R1 even with R9 evidence; R2 stays for bar(s), tavern(s), pub(s) beside real restaurant evidence; "pre-packaged snacks only", "snacks only", "snack warmer" are not restaurant evidence.
  - [ ] carrier-match.md: W1 and W1b merged into one prohibited-class table; where they conflicted the stricter rule wins; each row cites its source (AG line, D-###, P-###).
  - [ ] Self-checks on dev only, including SUB-174/182/186/201 style cases and "restaurant and lounge" with real cooking; pyright on changed files; code-review on the worktree diff.
- Output: code in underwriting_pipeline/, deliverables/head-of-underwriting/carrier-match.md, deliverables/ai-engineer/p-061-p-062-as-built.md

### T-107b — B-415 live check: P-059 with P-061/P-062
- Owner: @ai-engineer-assistant · Status: TODO · Decision: D-112
- Acceptance criteria:
  - [ ] 41 live calls (quick 15 = 5 calls, dev SUB-127–173 = 36), qwen, paced 55 s, .venv; temp outputs (D-069).
  - [ ] Report vs the old saved replies: operations hits, silent errors, routes, false completes, unsafe routes.
- Output: deliverables/ai-engineer/b-415-live-check.md

### T-107c — Account-manager check passes a senior-confirmed carrier
- Owner: @software-engineer · Status: TODO · Decision: D-112 (B-412)
- Acceptance criteria:
  - [ ] A P-052 senior-confirmed carrier passes the account-manager check without a typed override in the normal demo flow; all other gates unchanged.
  - [ ] Every refusal shows its real reason on the card; never "not in appetite" for a senior referral.
  - [ ] Self-check; D-065 (workbench, What's new line, screenshot).

### T-107d — "What's new" shows the latest 5 plus "show all"
- Owner: @software-engineer · Status: TODO · Decision: D-112 (B-410)

### T-107e — T-104 best-case demo file routed straight to Carrier A
- Owner: @senior-underwriter (pick), @software-engineer (wire into run-demo.sh) · Status: TODO · Decision: D-112 (B-414)

### T-107f — Time-saved 25–35 min assumptions checked or labelled unmeasured
- Owner: @senior-underwriter · Status: TODO · Decision: D-112

### T-107g — Second rehearsal with run-demo.sh; demo-guide.md and screenshots updated
- Owner: @senior-test-engineer (rehearsal), @pm (guide), @software-engineer (screenshots) · Status: TODO · Decision: D-112

### T-108 — Next hold-out: 20 in-scope + 12 out-of-scope, gold first, no run
- Owner: @producer (submission files, mix), @senior-underwriter (gold, mix, routes), @senior-test-engineer (plan JSON lint) · Status: IN_PROGRESS · Decision: D-113
- Requested by: @user, 2026-10-19 (session answers: full build, task id T-108, commit the code freeze first)
- Code under test (recorded per acceptance criterion 1): `ai-team` git SHA `457f1bf5784cd8a0c95af72724ca9341be3ba207`, prompt version `759b3e6bc9b2` (P-059), scorer `v7`. Gold manifest sha256 `11933e96b8370f57321ce5c1e1c6c3c3105a4f0517d841fbbbb8821bca18633d` (32 gold cards + route table), lint exit 0 at run date 2026-10-19. @model-risk build checks: `deliverables/model-risk/T-108-check.md` (H1 board, M1, L1 fixed) and `deliverables/model-risk/T-108-M2-close.md` (M2 CLOSED; H1 SUB-211 premises conflict found and fixed — gold `incomplete — hold: open conflict`, route unchanged). Gold compared field-by-field against builder source data (`deliverables/senior-underwriter/T-108-gold-vs-source.md`); no OCR drift in any scanned field.
- Acceptance criteria:
  - [x] Code frozen first: the B-428/B-411 workbench fix and this board are committed on `ai-team`; the task records that git SHA, prompt version 759b3e6bc9b2 (P-059) and scorer v7 as the code under test. No pipeline change after the freeze without a new freeze note.
  - [x] 32 new submission files written under `simulation/inbox/` as SUB-206 to SUB-237 (nothing reused from dev or T-104), no extraction, no model call, nothing run. 20 in-scope, 12 out-of-scope covering proposal-P-055 criteria 1-4 (scanned application, multiple locations, non-English, no application identified): 4 / 5 / 4 / 2 with 3 files carrying two criteria and 2 carrying criterion 4 alone, as in T-104.
  - [x] Build rules from the T-027 gate memo (D-109, resolution 2): every carrier loss run valued before the run date (use a run date of 2026-10-19 or later, so value them before today), at least two held W1 (prohibited-class) files, at least two office-lessor / deli-style class files.
  - [x] `deliverables/producer/T-108-mix.md` (mix, written before gold) and `deliverables/senior-test-engineer/T-108-plan.json` (ids, in, out, per_criterion, two_criteria, criterion_4, routes) with routes stated under the current rules (P-049..P-062, merged W1/W1b table), and `undated_loss_runs` declared for every typed loss run that has no valued date (B-424).
  - [x] Gold first: 20 in-scope gold files under `deliverables/senior-underwriter/gold-set/SUB-206*.md`.. written by hand from the documents and the written rules only (proposal-P-055.md criteria 1-4, carrier-match.md, operations-gold-rule.md D-102/D-103, carrier-loss-run-formats.md, required-fields.md) — no pipeline, scope detector, extraction, OCR script or scorer run or read. Every gold card has a `- Scope:` line and an `- Operations items:` line; empty fields say `not in documents`; no route is "hold". The 12 out-of-scope gold files carry the `- Scope:` line and the criteria codes only.
  - [x] Lint passes before the gold freeze: `.venv/bin/python deliverables/senior-test-engineer/lint_holdout.py deliverables/senior-test-engineer/T-108-plan.json --run-date 2026-10-19` exits 0. Any FAIL line is fixed in the files or the plan, never in the lint.
  - [x] Gold frozen: a freeze note in the mix records the gold SHA/hash and the code SHA above. The pipeline is **not** run on T-108 and no score exists (D-020: gold first, run once, score once, at a later session with the user's approval).
  - [x] @model-risk checks the build (High only) before it is called frozen: mix vs plan vs gold counts, loss-run dates, W1 and office-lessor/deli coverage, gold-first integrity, D-069 (nothing real written by a test run).


### T-109a — P-063: scope labels anywhere + send-time scope re-check
- Owner: @ai-engineer-assistant (built in the orchestrator session) · Status: DONE · Decision: D-116
- Acceptance criteria:
  - [x] The detector finds location labels anywhere in a field or body text ("Loc 1 … ; Loc #2 …", "Location 2", "Bldg 2"), not only at line start, list items or schedule cells; version bumped (scope-v4).
  - [x] The send gate re-checks scope at send time and refuses any out-of-scope file, with the reason shown, independent of status (carrier send and producer approve; workbench card).
  - [x] Self-checks on dev including SUB-233; dev sweep scope-v3 vs v4; pyright on changed files (0 new).
  - [x] D-065: workbench "What's new" line, screenshot `deliverables/software-engineer/screenshots/T-109a-scope-send-refused.png`.
  - [x] @model-risk check, High only: APPROVE, no High (`deliverables/model-risk/check-P-063-P-064-T-109c.md`). @senior-underwriter UI check (D-065): APPROVE WITH CHANGES, H1 (hold wording, no next step) fixed in the same task: top alert "Send blocked — … Next step: re-run extraction …", no route/hold lines on the card; screenshot retaken.
- Deliverables: `underwriting_pipeline/ai/scope.py`, `underwriting_pipeline/ai/prepare.py`, `underwriting_pipeline/app/package.py`, `underwriting_pipeline/app/workbench.py`, `deliverables/ai-engineer/p-063-p-064-as-built.md`.

### T-109b — P-064: scorer v8 (loss-run valued-as-of line)
- Owner: @ai-engineer-assistant · Status: DONE · Decision: D-116
- Acceptance criteria:
  - [x] Loss-run gold names the valued-as-of date explicitly ("Loss runs valued as of: <date>"); v8 compares that date only, never the policy-period start; v7 stays frozen (unchanged file).
  - [x] A card that expects a date without the line stops v8 before any call; self-check on synthetic gold.
  - [x] Gold convention written in `deliverables/ai-engineer/evals/RUN-RULES.md`.
  - [x] @model-risk check, High only: APPROVE, no High.
- Deliverables: `underwriting_pipeline/ai/eval_holdout_v8.py`, `deliverables/ai-engineer/evals/RUN-RULES.md`, `deliverables/ai-engineer/p-063-p-064-as-built.md`.

### T-109c — Test the test: the lint scores perfect and wrong answers before any freeze
- Owner: @senior-test-engineer (built in the orchestrator session) · Status: DONE · Decision: D-116
- Acceptance criteria:
  - [x] Before any gold freeze, (a) a perfect answer file built from the gold scores 100% on the scorer, and (b) a set of deliberately wrong answers (one per field, plus a leak and an unsafe route) is each caught. Freeze is blocked if either fails.
  - [x] Run on T-108's gold now as a check (dev data); write-up with findings.
  - [x] @model-risk check, High only: APPROVE, no High.
- Deliverables: `deliverables/senior-test-engineer/lint_holdout.py`, `deliverables/senior-test-engineer/T-109c-lint-check.md` (+ two raw outputs).

### T-109d — Pilot-readiness checklist (no build)
- Owner: @pm · Status: DONE · Decision: D-116
- Acceptance criteria:
  - [x] `deliverables/pm/pilot-readiness.md`: @model-risk's C1–C8 (`deliverables/model-risk/T-027-assist-mode-pilot.md`) as a checklist with a status each, plus B-190 (SSO) and B-191 (concurrent writes) with a short build plan each. No build.
 2>&1 | tail -2 2>&1 | tail -2
### T-116 — P-069: business_type operations slot, scorer v11
- Owner: @ai-engineer-assistant (scorer, lint), @senior-underwriter (operations-gold-rule.md) · Status: DONE (frozen) · Decision: D-119
- Acceptance criteria:
  - [x] A `business_type` operations slot whose values are the class list in `deliverables/head-of-underwriting/carrier-match.md` (allow-list + referral + prohibited classes).
  - [x] Every operations item that matters is a slot; items that fit no slot are removed from the scored checklist and listed as unscored notes.
  - [x] `deliverables/senior-underwriter/operations-gold-rule.md` updated to match (P-069 section, bar-word line).
  - [x] Scorer `underwriting_pipeline/ai/eval_holdout_v11.py`; `eval_holdout_v10.py` unchanged (sha256 `ffd1afdd…302b`).
  - [x] Lint (`deliverables/senior-test-engineer/lint_holdout.py`, v11 default): perfect answers score 100%; every wrong answer, including near-miss negatives, is caught.
  - [x] Validated on SUB-127–173 and a dev re-score of T-108 (SUB-206–237) with 0 model calls (cache only, temp paths per D-069).
  - [x] @model-risk check, High only: OBJECTION H1 (bar word dropped from SUB-211/222 dev gold), resolved by a rule line + gold fix; look-again APPROVE, no High (`deliverables/model-risk/check-T-116-P-069.md`). M1–M6, L1–L2 to backlog.
  - [x] If no High: code and scorer v11 frozen (v11 sha256 `7ddcfb50521b7af17f00c0e148891ca40008d019ce257b9b5d121c7fa6d3fcbb`, lint `01147a7532bdd7f1ec00861200d1d5e6bbf87f12612389416ff58b78844ea653`, prompt `759b3e6bc9b2`); code-under-test commit, prompt hash and scorer sha256 recorded in NEXT-SESSION.md.

### T-117 — Next hold-out: SUB-238–269 (20 in-scope + 12 out-of-scope), gold first, no run
- Owner: @producer (files, mix), @senior-underwriter (gold), @senior-test-engineer (plan JSON, lint) · Status: DONE (gold frozen, not run) · Decision: D-119 · Code under test: `ai-team` `8d605acce37f06f719b5a865a79d783bc3e9c800`, prompt `759b3e6bc9b2`, scorer v11 sha256 `7ddcfb50521b7af17f00c0e148891ca40008d019ce257b9b5d121c7fa6d3fcbb`
- Acceptance criteria:
  - [x] 32 new files under `simulation/inbox/` as SUB-238 to SUB-269, nothing reused; 20 in-scope, 12 out-of-scope over proposal-P-055 criteria 1–4 as in T-108; no extraction, no model call, nothing run.
  - [x] Build rules as T-108: every carrier loss run valued before the run date, at least two held W1 files, at least two office-lessor / deli-style class files.
  - [x] `deliverables/producer/T-117-mix.md` (written before gold) and `deliverables/senior-test-engineer/T-117-plan.json`.
  - [x] Gold first, by hand from the documents and written rules only: every in-scope card has `- Scope:`, `- Operations items:` slots per operations-gold-rule.md (P-069), and `Loss runs valued as of: <date>` where loss runs exist.
  - [x] Lint PASS (scorer v11) before the gold freeze; gold manifest sha256 `9ab5960db77f49e02b27518fb13eaff7a0ceb8d6e78c498c430bd2ba350a943d` recorded in the mix and NEXT-SESSION.md.
  - [x] Not run, not scored (D-020).
- Notes: 2026-10-21 @model-risk build check OBJECTION H1/H2 (gold only; `deliverables/model-risk/T-117-check.md`). @senior-underwriter fixed SUB-246, SUB-248 (→ senior_referral, R17) and SUB-249 (retail removed); routes now carrier_a 0, senior_referral 16, no_match 4. Lint PASS, check-gold 32 ok. **Re-frozen: gold manifest sha256 `7e076534432f1276bfe6198643547498b613c4f2b7aceb2ed618314b5e39fd33`** (supersedes `9ab5960d…`). Code, prompt, scorer v11 and lint unchanged. Not run.

### T-118 — P-070: the stated cooking line is carried into operations; a disagreement between documents is an open conflict and a hold
- Owner: @ai-engineer-assistant (build), @senior-underwriter (UI review), @model-risk (check) · Status: IN_REVIEW (built on `fix-t117`; @model-risk check and @senior-underwriter UI review pending) · Decision: D-122 (the user approved P-070 on 2026-10-21) · Proposal: `deliverables/ai-engineer/proposal-P-070.md` · As built: `deliverables/ai-engineer/P-070-as-built.md`
- Acceptance criteria:
  - [x] The stated cooking line is carried into the operations value (`; no cooking`) when the cited document states `Cooking operations: None` and the value does not carry it; the cooking line is a second cited part, so the card shows both lines; a document that mentions cooking equipment is left alone; the flag clears because the value carries the source, not because a rule was off.
  - [x] Square feet: `square footage` and the `sq_ft` column are read, so two documents that state two areas raise the `square_feet` conflict with both sides, each keeping the whole cited line or schedule row.
  - [x] Sales: a sales amount stated differently in two documents (labelled line or an amount near sales/revenue/turnover in free text) raises an open `sales_or_payroll` conflict; the sales value is emptied with a plain reason; the file is held.
  - [x] An occupancy count: two documents that state a different count of the same noun (suite/unit/apartment/tenant) raise an open conflict on that noun's topic; the operations value is kept; the file is held.
  - [x] The topics read as English on the card, in the resolve form, in the send refusal and in the producer request ("square footage", "sales or payroll", "suite count", …).
  - [x] New dev set `simulation/inbox-dev/document_conflicts/` (SUB-290–295) with dev notes and a manifest in `deliverables/senior-underwriter/gold-set-document_conflicts/dev/`; no hold-out file used; no model call; no published score rewritten.
  - [x] `prepare.py` self-check → `prepare ok`; `workbench.py` → `workbench ok`; `package.py` → `package ok`; `points.py` → `points ok` (model file unchanged); `pytest tests/pipeline` → 43 passed; frozen v11 self-check ok; frozen lint PASS; pyright no new finding.
  - [x] Request equality: zero changed requests — `PROMPT_VERSION` (`759b3e6bc9b2`) and the `cache_key` are the same before and after (`ab7653c9…a61372`); the baseline is not re-baselined.
  - [x] D-065: the workbench shows the completed value with both cited lines, the plain topic names with each side in words, the plain reason on the emptied value and the send refusal; one "What's new" line (2026-10-21, T-118, D-122); a Playwright screenshot on a temp copy under `deliverables/software-engineer/screenshots/`.
  - [ ] @senior-underwriter reviews the UI part, High findings only.
  - [ ] @model-risk checks the fix on dev with no High before it counts toward H1/H2 closure (T-027 veto stays until its conditions are met).
- Notes: 2026-10-21, built on `fix-t117` (never `main`). Refinements over the proposal: the count topic follows the noun counted (`suite_count`/`unit_count`/`apartment_count`/`tenant_count`); the sales rule compares documents only; only a scored field in dispute is emptied. Known risks (in the proposal): the wording `; no cooking`; a rounded free-text sales figure holds the file (tolerance = separate P-###); a count may be a different kind of unit; the square-feet vocabulary can only add a conflict where two documents state two areas. The frozen v11 has no word for a suite count, so a v-next scorer is needed to credit that topic; the 18/20 operations floor still needs the v-next scorer for the M-class readings.
- 2026-10-23 T-118 update (Claude Code session): P-071 (D-123) built on `fix-t117` for @model-risk High H1; see `deliverables/ai-engineer/P-070-as-built.md` § P-071. @model-risk fresh check pending.
- 2026-10-23 T-118 update (Claude Code session): P-072 (D-124) built on `fix-t117`; the "; no cooking" add removed (P-070 change 1 and P-071 withdrawn). @model-risk fresh check pending.
- 2026-10-23 T-118: @model-risk check 3 APPROVE, no High (`deliverables/model-risk/T-118-check-3.md`); counts toward H2 on dev only; H1 moves to the v-next scorer (D-124); Medium/Low in B-461–B-463. Not a production approval; the T-027 veto stands.

### T-119 — Next hold-out: SUB-340–371 (20 in-scope + 12 out-of-scope), plan only, not built
- Owner: @producer (files, mix), @senior-underwriter (gold), @senior-test-engineer (plan JSON, lint), @model-risk (look-again on every gold fix, B-457) · Status: DONE (built, gold frozen D-128, run and scored once 2026-10-24, D-130) · Planned by: orchestrator, Claude Code session, 2026-10-23, from the user's own list.
- Numbers: SUB-340 to SUB-371. SUB-290–296 are the document_conflicts dev set; SUB-321, SUB-322 and SUB-330 appear in self-checks, so the range starts at 340.
- Acceptance criteria (for the build):
  - [ ] 32 new files under `simulation/inbox/`, nothing reused from any hold-out or dev set: 20 in-scope and 12 out-of-scope over proposal-P-055 criteria 1–4 (at least two per criterion), as in T-108 and T-117.
  - [ ] Direct Carrier A routes: at least 3 in-scope files that route straight to Carrier A (R14: allow-list class, no W1/W2 word, TIV ≤ 5M, clean loss run). T-117 had none (B-449).
  - [ ] Planted conflicts (the H2 case): at least 3 files where two documents state different values for a scored or rating figure (a floor area, a sales figure, a unit or suite count), each written into the gold as an open conflict with both sides.
  - [ ] Cooking lines (the H1 case): files with `Cooking operations: None` whose operations answer must carry it, and files where the cooking line is stated only in another document (equipment or plain words such as "cook", "stove", "hot food"). The expected gold depends on the outcome of the H1 fix (P-070/P-071 and its follow-up); the gold is written to the rule in force at gold time.
  - [ ] Loss runs: typed, in the published carrier formats (`CARRIER_RUN_FORMATS`), including at least 2 Carrier C runs and at least 1 Carrier B run; every run valued before the run date (T-108 rule); no `| None reported |` rows (T-118 M4).
  - [ ] SUB-252-style case (bar/restaurant R1 vs R2): included only after @head-of-underwriting rules on B-448/B-458; until then it is left out, not guessed.
  - [ ] Build rules as T-108/T-117: at least two held W1 files and at least two office-lessor or deli-style class files.
  - [ ] `deliverables/producer/T-119-mix.md` written before the gold; `deliverables/senior-test-engineer/T-119-plan.json`.
  - [ ] Gold first, by hand from the documents and written rules only; @model-risk look-again on every gold fix (B-457); lint PASS with the scorer in force, then the gold manifest sha256 recorded.
  - [ ] Not run and not scored until the user says so (D-020); scored once, with no code change after the gold exists.
- Noted before the run (D-127, 2026-10-23): under v11, answers that omit the cooking slot where gold says no cooking count as misses; results list these separately.
- Noted before the run (D-128, 2026-10-23): under v11 the SUB-348 and SUB-349 conflict marks (cooking) can't be measured; they are reported separately and excluded from the conflict rate.
- Depends on (updated 2026-10-23): settled. H1 in the pipeline: no automatic "no cooking" (D-124); scorer: v11 (D-127); SUB-252-style case: rule A, R2 senior referral (D-125). Lint with v11.
- Update 2026-10-23 (orchestrator): BUILT, gold FROZEN, not run. 32 files SUB-340–371 (`simulation/inbox/build_SUB-340-371.py`); mix `deliverables/producer/T-119-mix.md`; gold by @senior-underwriter; plan + lint by @senior-test-engineer; routes carrier_a 4 / senior_referral 12 / no_match 4; planted conflicts 344 (sq ft), 345 (sales), 346 (suites), cooking 348/349; pub case 352 R2 (D-125). @model-risk build check BLOCK (H1) → D-128 gold fixes → look-again APPROVE. Lint v11: only the two D-128 marks fail. Gold manifest sha256 `2feba3b2b007ab197c22a40427b105242585ee0783bed7c5e5a575408fd55fcc`. Status: FROZEN, awaiting the user's word to run (D-020). 2026-10-24: RUN once and scored once (D-130), run 20261024T000318-70195; results `deliverables/ai-engineer/evals/SUB-340-371-results.md`; @model-risk T-027 memo KEEP. DONE.
### T-120 — Next hold-out: SUB-450–481 (20 in-scope + 12 out-of-scope), plan only, not built
- Owner: @producer (files, mix), @senior-underwriter (gold), @senior-test-engineer (plan JSON, lint), @model-risk (build check, one look-again) · Status: PLANNED (not built; build starts only on the user's word) · Planned by: orchestrator, Claude Code session, 2026-10-26, from the user's own list (D-131, D-133).
- Numbers: SUB-450 to SUB-481. SUB-372–449 are not used for hold-outs: self-checks in prepare.py and package.py use SUB-400–449, dev sets end at SUB-303.
- Code under test: pilot-integration after P-074 (D-132) and P-075 (D-133); code, PROMPT_VERSION, scorer v11 and lint sha256 frozen in team/NEXT-SESSION.md before any file is built.
- Acceptance criteria (for the build):
  - [ ] 32 new files under `simulation/inbox/`, nothing reused from any hold-out or dev set: 20 in-scope and 12 out-of-scope over proposal-P-055 criteria 1–4 (at least two per criterion), as in T-117 and T-119.
  - [ ] Planted conflicts: at least 5 measurable ones (B-473), each on a scored or rating figure (sales, floor area, unit/suite count, TIV), both sides stated as plain figures in two documents, written into the gold as an open conflict with both sides. At least one uses words for the amount ("$1.42 million") and at least one is approximate ("about", "roughly", "~") against an exact figure (P-074).
  - [ ] Cooking stated: several files whose application says `Cooking operations: None` (or No / No kitchen) with no cooking word anywhere else (P-075 copies the line).
  - [ ] Cooking conflicts: at least 2 files where the application says none and another document states cooking (equipment or plain words, incl. a word from the P-075 probe set), each in the gold as an open cooking conflict. Under v11 these conflict marks may not be measurable (no figure); record that in the plan before the gold, as D-128 did, if the lint shows it.
  - [ ] Direct Carrier A: at least 3 in-scope files that route straight to Carrier A (R14/R17: allow-list words only, no W1/W2 word, TIV ≤ $5M, clean typed loss run).
  - [ ] Loss runs: typed, in the published carrier formats (`CARRIER_RUN_FORMATS`), at least 2 Carrier C and 1 Carrier B; Carrier C periods "D - D" and claim numbers "C-<digits>"; every run valued before the run date; no `| None reported |` rows; every typed run passes `carrier_run_check`.
  - [ ] Build rules as T-108/T-117/T-119: at least two held W1 files, two office-lessor and two deli-style files; the SUB-252-style pub case under rule A (D-125).
  - [ ] `deliverables/producer/T-120-mix.md` written before the gold; `deliverables/senior-test-engineer/T-120-plan.json`.
  - [ ] **Operations gate (D-134):** C1 enforced via approved P-076 (code) before build; C2 silent-error script frozen before gold (scored miss with no specific item-naming reason; C1 policy reason never counts), target 0; C3 0 understated hazards; C4 operations present ≥18/20 and hits ≥15/20 under v11 (set now). C5 other gates unchanged. **C6:** ≥12 files with "Cooking operations: None"-type lines, ≥3 with cooking stated, ≥2 with planted cooking conflicts. **C7:** gate recorded in DECISIONS.md before any gold exists.
  - [ ] Gold first, by hand from the documents and written rules only; every conflict line names a field actually in conflict in the builder source data (B-465, checked by hand until the lint does it); lint PASS with v11 (or only failures recorded before the run, as D-128); gold manifest sha256 recorded.
  - [ ] @model-risk build check (gold vs builder source, scope, slots, valued-as-of, routes vs written rules), High only, one look-again (D-129).
  - [ ] Not run and not scored until the user says so (D-020); scored once, with no code change after the gold exists.
- Open before the build (the user decides): whether T-120 also uses the operations gate @model-risk set out in `deliverables/model-risk/T-027-operations-gate-answer.md` (C1–C7); if yes, it must be recorded in DECISIONS.md before any T-120 gold exists (C7), C1 needs its own P-###, and C6 adds file counts (at least 12 none-line, 3 cooking, 2 planted cooking conflicts).

