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
  - [x] Interpretable score and reason codes an underwriter can override
  - [x] Score cannot decline, bind, or set a price
- Output: deliverables/data-scientist/reason-codes.md, underwriting_pipeline/models/
- Notes: Fixed points, not a fit. Waiting on reviewers. No gradient boosting.

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
  - [x] Page shows each submission, extracted fields with citations, conflicts, missing items, score with reason codes, and carrier match
  - [x] Underwriter can approve, edit, or decline
  - [x] No path records a decision without an underwriter id and a reason on decline
- Output: deliverables/software-engineer/workbench-ux.md, underwriting_pipeline/app/workbench.py
- Notes: Started 2026-10-09 under D-009. Does not bind. The React page in frontend/ was not changed.

### T-020 — Step 7: Carrier-ready package and quote tracking
- Owner: @software-engineer
- Requested by: @pm
- Status: IN_REVIEW
- Priority: P0
- Depends on: T-019
- Reviewers: @senior-underwriter, @compliance
- Acceptance criteria:
  - [x] A package can be built for a submission
  - [x] Nothing is written to simulation/to-carrier/ unless the user types send to carrier SUB-###
  - [ ] Quote status tracked per placeholder carrier
- Output: underwriting_pipeline/app/package.py
- Notes: D-009. No package was sent this round. Quote tracking waits on a carrier reply.

### T-021 — Step 8: Feedback loop from underwriter decisions
- Owner: @ml-engineer
- Requested by: @pm
- Status: IN_REVIEW
- Priority: P0
- Depends on: T-019
- Reviewers: @data-scientist, @model-risk
- Acceptance criteria:
  - [x] Every decision stored with actor, action, reason, and the AI version it corrected
  - [x] Corrections can be counted for the "no corrections" metric
- Output: deliverables/ml-engineer/feedback-loop.md, underwriting_pipeline/app/workbench.py
- Notes: D-014. The workbench log stores approve, edit, and decline. Edit and decline require a reason. The self-check counts them. Not a training set and not a production model.

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
- Status: IN_REVIEW
- Priority: P0
- Depends on: T-034, T-035
- Reviewers: @ai-engineer, @senior-underwriter
- Acceptance criteria:
  - [x] Scored without editing the scorer after the gold files existed
  - [x] A null that matches missing is not counted as correct
  - [x] Compared with the SUB-037 through SUB-046 score
  - [x] The score comes from a successful model call
- Output: deliverables/ai-engineer/evals/SUB-047-056-holdout.md, deliverables/model-risk/holdout-SUB-047-056.md
- Notes: 2026-10-10. Calls succeeded. Not a production approval. Every field with a gold value is 10/10. Loss runs are 6 hit, 0 miss, 4 not credited.

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
- Reviewers: @ai-engineer, @senior-underwriter
- Acceptance criteria:
  - [x] Scored without editing the scorer after the gold files existed
  - [x] A null that matches missing is not counted as correct
  - [x] Failures are reported, including scans and refusals to pick
  - [x] The score comes from a successful model call
- Output: deliverables/ai-engineer/evals/SUB-057-066-holdout.md, deliverables/model-risk/holdout-SUB-057-066.md
- Notes: 2026-10-10. Not a production approval. Named insured 5/10. The four hard scans missed. SUB-063 and SUB-066 refused to pick and those fields are misses.

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
- Notes: 2026-10-10. Not a production approval. Named insured 9/10. Premises 4 hit, 5 miss, 1 flagged. Loss runs 7 hit, 0 miss, 2 not credited, 1 flagged.

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
- Notes: 2026-10-10. Not a production approval. Premises 5 hit, 4 miss, 1 flagged. Year built 7/10. Loss runs 6 hit, 1 miss, 2 not credited, 1 flagged.

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
- Status: IN_PROGRESS
- Priority: P0
- Depends on: T-055, T-056
- Reviewers: @model-risk
- Acceptance criteria:
  - [ ] SUB-017 through SUB-076 scored again after the approved edits
  - [ ] Any field whose hit count drops is reported
  - [ ] The before file is kept
- Output: deliverables/ai-engineer/evals/regression-SUB-017-076-after-P002-P003b.json
- Notes: D-020. Running. Official hold-out files are not rewritten.

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
- Owner: @ai-engineer
- Requested by: @user
- Status: IN_REVIEW
- Priority: P0
- Depends on: T-025
- Reviewers: @model-risk, @senior-underwriter
- Acceptance criteria:
  - [x] prepare.py unchanged for the run
  - [x] Per-field accuracy reported, including failures
  - [ ] @model-risk accepts the component
- Output: deliverables/ai-engineer/evals/SUB-017-026-holdout.md
- Notes: Identity fields are 0/10. @model-risk's note is deliverables/model-risk/holdout-SUB-017-026.md. Not a production approval.

### T-027 — Read PDF, Excel, prose, and Spanish with a model
- Owner: @ai-engineer
- Requested by: @user
- Status: IN_REVIEW
- Priority: P0
- Depends on: T-026
- Reviewers: @model-risk, @senior-underwriter
- Acceptance criteria:
  - [x] PDFs read with pdfplumber, Excel with openpyxl, scans with OCR
  - [x] An LLM returns structured JSON with a citation and a confidence on every field
  - [x] Confidence under 0.75 is dropped instead of guessed
  - [x] The key is OPENAI_API_KEY from the environment and is not stored in the repo
  - [x] A hold-out score from a successful model call
- Output: underwriting_pipeline/ai/llm_extract.py, underwriting_pipeline/ai/sources.py
- Notes: D-010 and D-012. The first paid-key call returned HTTP 401. The Groq call on openai/gpt-oss-120b succeeded and T-029 recorded that score. SUB-017 through SUB-026 are the development set. Do not count a null as a hit.

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
- Status: IN_REVIEW
- Priority: P0
- Depends on: T-027, T-028
- Reviewers: @ai-engineer, @senior-underwriter
- Acceptance criteria:
  - [x] Scored without editing the scorer after the gold files existed
  - [x] A null that matches missing is not counted as correct
  - [x] The score comes from a successful model call
- Output: deliverables/ai-engineer/evals/SUB-027-036-holdout.md, deliverables/model-risk/holdout-SUB-027-036.md
- Notes: 2026-10-10 rerun on openai/gpt-oss-120b. Calls succeeded. Not a production approval. Named insured, premises, and year built are 10/10. Operations 6/10, sales 9/10, TIV 8/10, construction 7/10, loss runs 3 hit / 3 miss / 4 not credited, conflict 9/10, status 7/10. Nulls on missing loss runs were not counted as hits. This is the D-013 baseline. A later development rerun is a different file and does not replace these counts.

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
- Status: IN_REVIEW
- Priority: P0
- Depends on: T-030, T-031
- Reviewers: @ai-engineer, @senior-underwriter
- Acceptance criteria:
  - [x] Scored without editing the scorer after the gold files existed
  - [x] A null that matches missing is not counted as correct
  - [x] The score is compared with the first SUB-027 through SUB-036 score
  - [x] The score comes from a successful model call
- Output: deliverables/ai-engineer/evals/SUB-037-046-holdout.md, deliverables/model-risk/holdout-SUB-037-046.md
- Notes: 2026-10-10. Calls succeeded. Not a production approval. Named insured, premises, sales, TIV, year built, and status are 10/10. Operations, construction, and conflict are 9/10. Loss runs are 6 hit, 0 miss, 4 not credited. SUB-040 and SUB-044 are the misses.


