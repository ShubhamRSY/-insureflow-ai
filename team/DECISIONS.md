# Decision Log

Format: see `.cursor/rules/00-team-protocol.mdc`. Never delete; supersede instead.

## D-001 — Team operating model
- Date / Owner: 2026-10-09 / @user
- Context: Simulated cross-functional team running as Cursor agents.
- Options considered: Free-form chat vs file-based coordination.
- Decision: Coordinate only through team/ files using the shared protocol.
- Rationale: Agents in separate chats share no memory; files give a single source of truth and an audit trail.
- Dissent: none
- Follow-up tasks: T-001
- Status: ACCEPTED

## D-002 — v1 appetite and authority bands
- Date / Owner: 2026-10-09 / @head-of-underwriting
- Context: Pilot needs a written appetite and a hard line on what the system may quote or decline before anyone designs the workflow or the model.
- Options considered: (A) Auto-quote and auto-decline inside broad bands. (B) Auto-quote only on a tight target class; all declines human. (C) No automated quote or decline; AI is a copilot only.
- Decision: PROPOSED option B. Package property + GL only. No auto-decline. Auto-quote only if every gate in authority-matrix.md passes (target class, TIV ≤ $1M, premium ≤ $10k, one location, zero claims on currently valued runs, complete COPE, filed rate, no schedule credit). Habitational and restaurants are senior referrals. Coastal wind is out of appetite. Not accepted until @actuary provides an expected loss ratio and the objections below are resolved.
- Rationale: Profitability before speed. A wrong auto-quote binds coverage. A wrong decline is a market-conduct event. Referral is the failure mode we can afford.
- Dissent (who, why): @senior-underwriter — habitational ≤9 units must not be labeled "target"; a no-known-loss letter must not count as zero claims. @compliance — support conditional on human declinations, no external consumer data, filed rate only. @model-risk — auto-quote rules are Tier 1 and are not approved for use. @actuary — not yet heard.
- Follow-up tasks: T-002, T-011
- Status: SUPERSEDED by D-003

## D-003 — v1 auto-quote band narrowed
- Date / Owner: 2026-10-09 / @head-of-underwriting
- Context: @senior-underwriter objected to habitational being labeled target and to no-known-loss letters counting as zero claims. @actuary's planning LR puts artisan contractors on or above permissible. @compliance supported D-002 only with human declines, no consumer data, and the filed rate.
- Options considered: (A) Keep D-002 as proposed. (B) Drop habitational and artisan from auto-quote; keep office, dry retail, and light wholesale. (C) No auto-quote at all until we have our own triangle.
- Decision: Option B. Auto-quote only for office, dry retail, and light wholesale, and only if every gate in the revised authority matrix passes, including carrier loss runs (a no-known-loss letter is Incomplete). All habitational, all contractors, and all restaurants are senior referrals. Student housing and subsidized housing are prohibited. Planning permissible LR 0.65; a segment must sit at or under 0.60 to be eligible for auto-quote. Those LR figures are planning assumptions, not company experience. No auto-decline. Filed rate only. This is not a production approval of the rules as a Tier 1 model.
- Rationale: Profitability first. Artisan does not clear the margin @actuary set. Habitational labeled "target" would be implemented as eligible. Referral is an acceptable cost.
- Dissent (who, why): @model-risk — auto-quote rules remain an unapproved Tier 1 model; D-003 does not authorize shadow or production. @actuary — adopted, not dissent, on artisan. @senior-underwriter — objection adopted; confirmation of the edited guide still open.
- Follow-up tasks: T-002, T-010
- Status: SUPERSEDED by D-004

## D-004 — Agency underwriting pipeline
- Date / Owner: 2026-10-09 / @user
- Context: The team had been building a carrier/MGA auto-quote system. The user reset the product.
- Options considered: Continue the carrier auto-quote design (D-003) vs. an agency pipeline that prepares submissions for a panel of carriers.
- Decision: The product is an automated underwriting pipeline for Sanger & Altgelt underwriters (8 steps above). The AI never auto-binds or auto-declines; the underwriter decides. Writing company: carrier panel, placeholders Carrier A/B/C. Pilot: Texas, small commercial. Rate manual: not applicable; @actuary focuses on risk scoring and carrier appetite. Protection-class vendor: not used in v1. Synthetic data only.
- Rationale: Sanger & Altgelt places business. It does not write it. Final authority stays with the agency underwriter.
- Dissent: none recorded at decision time.
- Follow-up tasks: T-013 and the pipeline tasks that replace the carrier auto-quote work.
- Status: ACCEPTED
- Amended in part by: D-005 (missing-info requests are drafted, not sent, until an account manager approves). The rest of D-004 stands.

## D-005 — Account manager approves missing-info requests
- Date / Owner: 2026-10-09 / @user
- Context: @senior-underwriter objected to emailing a producer with no person checking the request. D-004 had automated step 3, including the send.
- Options considered: (A) Keep sending as soon as the draft is written. (B) AI drafts; an account manager approves each request before it is sent.
- Decision: Missing-info requests are drafted by the AI but an account manager must approve each one before it is sent.
- Rationale: A wrong email to a producer looks bad for the agency. Approval is one click, not a second underwriting review.
- Dissent: none.
- Follow-up tasks: T-016
- Status: ACCEPTED
- Amends: D-004. Does not restore auto-decline or auto-bind.
- Amended in part by: D-006 (where drafts sit, what a restaurant request must ask, and that carrier appetite guides are shared).

## D-006 — Appetite guide, industry requests, conflict records, approval queue, eval set
- Date / Owner: 2026-10-09 / @user
- Context: Four gaps in the pipeline, plus requests that reached the producer without the user's approval.
- Options considered: Leave carrier appetite internal and unknown; keep sending drafts from an account-manager click; store conflicts only in the email; test on three files.
- Decision: (1) Carrier appetite guides are shared with the agency, as in real life. Copy simulation/carriers.md to deliverables/head-of-underwriting/carrier-appetite.md and use it for carrier matching. Carrier B accepts restaurants and light contractors. (2) Missing-info requests must be industry-specific. Restaurants must ask about cooking equipment, hood and fire suppression, sprinklers, liquor sales, and hours. (3) Conflicts between documents are stored as data with both values and their sources, never just written in an email. (4) Account manager approval: requests go to simulation/pending-approval/ first. Move them to simulation/to-producer/ only after the user approves. Move the existing SUB-002 and SUB-003 requests back to pending-approval now. (5) Eval set: @producer sends 10 new submissions this round with the same realism mix, and @senior-underwriter writes the expected correct answer for each in deliverables/senior-underwriter/gold-set/.
- Rationale: Real agencies receive appetite guides. A wrong or thin producer email is worse than a one-click hold. An eval set needs expected answers, not three demos.
- Dissent: none.
- Follow-up tasks: T-015, T-016, T-018, T-024
- Status: ACCEPTED
- Amends: D-004 and D-005. The user, not a simulated click, is the approver who moves a request from pending-approval to to-producer. No auto-decline and no auto-bind.
- Amended in part by: D-007 (no AI role may approve; conflicts also record how they were resolved).

## D-007 — The user is the only approver
- Date / Owner: 2026-10-09 / @user
- Context: A simulated account manager had approved SUB-002 and SUB-005. The user is the account manager. Conflicts were stored without a resolution. T-004 was still open.
- Options considered: Keep the role click. Or hold every draft until the user types "approve SUB-###".
- Decision: The user is the account manager. No AI role may approve a missing-info request. Drafts wait in simulation/pending-approval/ and are listed at the end of each round. The user approves by typing "approve SUB-###". SUB-002 was already answered by the producer, so that reply stays. SUB-005 was not answered, so it stays in pending-approval. Carrier B accepts restaurants and light contractors; bars and nightclubs stay no-match. Conflicts are stored in the extraction output with both values, their sources, and how they were resolved. @data-engineer closed T-004. The eval set is the 10 submissions SUB-007 through SUB-016, with expected answers already in deliverables/senior-underwriter/gold-set/.
- Rationale: The user said this directly.
- Dissent: none.
- Follow-up tasks: T-004 closed. T-015 scored under D-008.
- Status: ACCEPTED
- Amends: D-005 and D-006. Does not restore auto-decline or auto-bind.
- Amended in part by: D-008 (the user then approved seven drafts and withdrew SUB-003).

## D-008 — User approved seven requests and withdrew SUB-003
- Date / Owner: 2026-10-09 / @user
- Context: D-007 put every missing-info draft in simulation/pending-approval/. The user then named the ones to send and one to drop.
- Options considered: Leave the queue untouched. Or send only the named drafts and withdraw SUB-003.
- Decision: The user approved SUB-002, SUB-005, SUB-011, SUB-012, SUB-013, SUB-014, and SUB-015. Those drafts moved to simulation/to-producer/ with Approved-by: user (the account manager). No AI role approved any other request. SUB-003 is withdrawn because the producer had already answered it; it was not sent, and it is removed from pending-approval. The file is complete: nothing else is missing. Carrier B still accepts restaurants and light contractors with 3 clean loss years. Bars and nightclubs stay no-match, not a producer decline. The rest of D-004 stands: no auto-decline and no auto-bind.
- Rationale: The user typed the approvals and the withdrawal in the same instruction as D-007.
- Dissent: none.
- Follow-up tasks: T-015, T-024
- Status: ACCEPTED
- Amends: D-007's queue note. Does not supersede D-004.

## D-009 — Hold-out is the proof, and the next sprint is the desk
- Date / Owner: 2026-10-09 / @user
- Context: The SUB-007 through SUB-016 score was 100% on the fields that were scored. The same team wrote the files, the gold answers, and the extractor. The user also started the next build sprint.
- Options considered: Treat the 100% as proof. Or freeze the extractor and score a new hold-out in formats it was not written for. Ship carrier packages for every complete in-appetite file now, or wait for an explicit send line.
- Decision: The 100% score is not accepted as proof. @producer sends 10 new hold-out submissions (SUB-017 through SUB-026) in different formats: a text PDF, a scanned-style PDF, an Excel schedule, an email whose data is only in the body, and one in Spanish, mixed across the ten. @senior-underwriter writes the gold answers before anyone runs extraction. Nobody may change prepare.py before that hold-out score is recorded. @model-risk reports the score honestly, including failures. The build sprint starts this round. On the D-004 list, the carrier package is step 7 (T-020): a package may go to simulation/to-carrier/ for a complete in-appetite submission only after the user types "send to carrier SUB-###". The workbench is step 6 (T-019): a web page that shows each submission, extracted fields with citations, conflicts, missing items, the score with reason codes, and the carrier match. The user called these step 5 and step 6 in the instruction. The board keeps the D-004 numbers.
- Rationale: The user said this directly.
- Dissent: none at the time of the decision. @model-risk's later finding is a review of the score, not a dissent from running the hold-out.
- Follow-up tasks: T-019, T-020, T-025, T-026
- Status: ACCEPTED
- Amends: the use of the T-015 score as proof. Does not restore auto-decline or auto-bind. The user, not an AI role, releases a carrier package.

## D-010 — Real extraction, then a fresh hold-out
- Date / Owner: 2026-10-09 / @user
- Context: The user sent SUB-001, SUB-002, and SUB-004 to carriers. The label scanner is not accepted as extraction. SUB-017 through SUB-026 were written by the same team as the code.
- Options considered: Keep the label scanner and tune it. Or replace it with a model call over PDF, Excel, OCR, prose, and Spanish, then score a new hold-out the code was not tuned on.
- Decision: T-027 starts now, owned by @ai-engineer. Pattern matching is replaced by reading PDFs with pdfplumber, Excel with openpyxl, scanned pages with OCR, and an LLM that returns structured JSON. Every field has a source citation and a confidence. Low confidence is left for the underwriter and is not guessed. The API key is read from the environment variable OPENAI_API_KEY. It is never written into a file. SUB-017 through SUB-026 are a development set. After T-027, @producer sends SUB-027 through SUB-036, @senior-underwriter writes gold answers first, and @model-risk scores that set without further code changes. A null that matches "missing" does not count as a correct answer in any score.
- Rationale: The user said this directly.
- Dissent: none.
- Follow-up tasks: T-027, T-028, T-029
- Status: ACCEPTED
- Amends: how T-015 and T-026 scores may be used. Does not restore auto-decline or auto-bind.

## D-011 — Local model, no paid API
- Date / Owner: 2026-10-09 / @user
- Context: The paid API key was rejected. The user does not want a paid API for now. Ollama is already running with qwen2.5:7b.
- Options considered: Wait for a paid key. Or call the local OpenAI-compatible endpoint and keep a paid API as an environment change only.
- Decision: No paid API for now. The extractor uses http://localhost:11434/v1 and model qwen2.5:7b. Those are the defaults for LLM_BASE_URL and LLM_MODEL. The API key is the dummy value ollama unless LLM_API_KEY is set. A later switch to a paid API changes only those environment variables. No real key is written into a file. @model-risk reruns the SUB-027 through SUB-036 score after this extractor change and does not change any other code. Carrier B's hood and fire suppression question for SUB-002 is drafted into simulation/pending-approval/ and is not sent until the user approves it.
- Rationale: The user said this directly.
- Dissent: none.
- Follow-up tasks: T-027, T-029
- Status: ACCEPTED
- Amends: the key and endpoint in D-010. Does not restore auto-decline or auto-bind.
- Amended in part by: D-012 (the live host is Groq; localhost stays on Ollama).

## D-012 — Groq for speed, Ollama if the host is local
- Date / Owner: 2026-10-10 / @user
- Context: Local qwen2.5:7b was too slow. The user set LLM_API_KEY, LLM_BASE_URL, and LLM_MODEL for Groq's free API.
- Options considered: Stay on Ollama. Or call Groq from those environment variables and keep Ollama when the base URL is localhost.
- Decision: The extractor reads LLM_API_KEY, LLM_BASE_URL, and LLM_MODEL. The key is never written to a file and never printed. If LLM_BASE_URL points at localhost, Ollama remains the fallback and the dummy key ollama is used when LLM_API_KEY is empty. A 429 waits and retries. @model-risk reruns SUB-027 through SUB-036 after this change and does not change any other code. The SUB-002 hood and fire suppression draft stays in simulation/pending-approval/ until the user approves it.
- Rationale: The user said this directly.
- Dissent: none.
- Follow-up tasks: T-027, T-029
- Status: ACCEPTED
- Amends: D-011's "no paid API" line. Groq's free tier is allowed. Does not restore auto-decline or auto-bind.

## D-013 — Extraction sprint, new hold-out, and a send list
- Date / Owner: 2026-10-10 / @user
- Context: The first gpt-oss-120b score on SUB-027 through SUB-036 was a useful baseline. The user called it a good first result and approved the Carrier B reply for SUB-002.
- Options considered: Keep tuning on that same hold-out. Or freeze a development pass on SUB-017 through SUB-036, then score a new hold-out with no further code changes.
- Decision: (1) @ai-engineer improves scanned-page OCR, Spanish forms, facts that appear only in email text, and loss runs, using SUB-017 through SUB-036 as the development set only. (2) After that work is frozen, @producer sends SUB-037 through SUB-046, @senior-underwriter writes the gold answers first, and @model-risk scores that set with no code changes and compares it with the first SUB-027 through SUB-036 score. (3) The target before pilot is 9/10 or better on every field, and a loss-run date is never guessed. (4) The remaining complete in-appetite submissions are processed and listed for the user's "send to carrier" approval. An AI role does not send them.
- Rationale: The user said this directly.
- Dissent: none
- Follow-up tasks: T-030, T-031, T-032
- Status: ACCEPTED
- Amends: how the D-012 score is used. It is the baseline to beat, not a production sign-off. Does not restore auto-decline or auto-bind. Does not authorize sending the ready list.

## D-014 — Rule bugs, the remaining extraction misses, and the decision log
- Date / Owner: 2026-10-10 / @user
- Context: The user sent SUB-009, SUB-010, and SUB-011. SUB-005 stayed on hold because sprinklers were only read from the operations sentence. SUB-013 stayed incomplete because a no-known-loss letter sat next to a real carrier loss run. SUB-040 and SUB-044 were the remaining hold-out misses.
- Options considered: Change the model prompt and rescore SUB-037 through SUB-046. Or keep that score, fix the two routing rules without touching the model, fix the miss types on the development set, and score a new hold-out.
- Decision: (1) Read sprinklers from the application's sprinkler field, not only the operations text, and recheck SUB-005. When a real carrier loss run and a no-known-loss letter are both present, use the carrier loss run, and recheck SUB-013. Both get tests. These are rule fixes. The model prompt and the OCR step stay as they were for the SUB-037 score. (2) Fix email-only operations and construction, and square-foot conflicts, on the development set only. Score that fix on the next new hold-out, not by editing the SUB-037 score. (3) Start step 8. An approve, edit, or decline on the workbench saves the decision and the reason so corrections can be counted.
- Rationale: The user said this directly.
- Dissent: none
- Follow-up tasks: T-021, T-033, T-034, T-035, T-036
- Status: ACCEPTED
- Amends: D-013's freeze only for the model prompt and OCR. Document rules may be added and then frozen before the next hold-out. Does not restore auto-decline or auto-bind. Does not authorize sending SUB-013.

## D-015 — Number normalization, a harder hold-out, and a manager demo
- Date / Owner: 2026-10-10 / @user
- Context: The user sent SUB-013. SUB-005 had been held because 220000 and 220k were stored as a conflict. The SUB-047 through SUB-056 score was 10/10 on every field that has a value, and the user called those tests too easy.
- Options considered: Treat 220k and 220000 as a conflict. Or normalize numbers before comparing, then score a harder hold-out with no further code changes.
- Decision: (1) Normalize numbers before comparing. 220k equals 220000, $1.2M equals 1200000, commas do not make a new number, and "sq ft" equals "sf". 220000 versus 220k is not a conflict. Recheck SUB-005. Keep an operations difference only when it is a real disagreement. (2) @producer builds SUB-057 through SUB-066 harder: handwritten scans, rotated and low-quality pages, multi-page loss runs with several carriers and real claims, multiple locations, ACORD blanks answered in an attachment, contradictory emails, and duplicate resubmissions. @model-risk scores that set with no code changes. (3) @pm writes deliverables/pm/demo-guide.md, a 10-minute demo of the pipeline on the workbench. (4) Commit the work as "Pipeline steps 1-8 working on synthetic data". Do not push.
- Rationale: The user said this directly.
- Dissent: none
- Follow-up tasks: T-037, T-038, T-039, T-040
- Status: ACCEPTED
- Amends: nothing about auto-decline or auto-bind. Does not authorize sending SUB-005.

## D-016 — Scan repair, a refusal column, and another hard hold-out
- Date / Owner: 2026-10-10 / @user
- Context: The user sent SUB-005. SUB-057 through SUB-066 scored about half on the identity fields. Four scans returned no name. Two correct refusals to pick were counted as misses.
- Options considered: Guess a value from an unreadable page. Or repair rotation and deskew, use a vision model when the account has one, and otherwise send the page to a person. Count a correct refusal in its own column.
- Decision: (1) Auto-detect and fix rotation with Tesseract OSD, then deskew, before OCR. For handwriting and very poor scans, use a vision-capable model if one is on the Groq account. This account has none, so those pages are marked "needs human read" on the workbench. Do not guess from an unreadable page. The development set is SUB-017 through SUB-066, and SUB-057 through SUB-066 are now part of it. (2) Add a column, correctly flagged for human, for a field where the documents disagree and the AI stored both sides without picking one. That result is not a hit and not a miss. (3) After the repair is frozen, @producer builds SUB-067 through SUB-076 at the same difficulty, gold first, and @model-risk scores it with no further extraction changes, compared with the SUB-057 through SUB-066 baseline.
- Rationale: The user said this directly.
- Dissent: none
- Follow-up tasks: T-041, T-042, T-043, T-044
- Status: ACCEPTED
- Amends: how an unreadable page and a refusal to pick are reported. Does not restore auto-decline or auto-bind. The send of SUB-005 was a separate instruction and is already done.

## D-017 — The user is the AI Engineer
- Date / Owner: 2026-10-10 / @user
- Context: The user changed roles. Approval of producer mail and carrier packages had been reserved to the user. Premises is the weak field on SUB-067 through SUB-076.
- Options considered: Leave the assistant free to edit the extractor. Or require a numbered proposal and an exact approval line before any extraction, prompt, OCR, model, or eval change.
- Decision: (1) The AI role is @ai-engineer-assistant. It may run evals and analysis without asking. It may not change extraction, prompts, OCR, models, or evals until the user replies "approve change P-###". A proposal states the trade-off and the expected score impact in simple words. (2) LLM/agent architecture, prompts, and evals are decided by @user, the AI Engineer, after consulting @ai-engineer-assistant, @senior-underwriter, and @model-risk. @model-risk can still block production. (3) A simulated @account-manager approves producer requests and carrier sends only when the file is complete, in appetite, free of open conflicts, and free of unread pages, and writes a reason every time. approve() and send_to_carrier() accept that actor. The user can override any send. No AI role can approve or send. (4) Every round ends with a section "For the AI Engineer": pending proposals, the latest eval scores, and the top failure to fix next.
- Rationale: The user said this directly.
- Dissent: none
- Follow-up tasks: T-045, T-046
- Status: ACCEPTED
- Amends: D-008, where the user was the account manager and the only approver. The user is now the AI Engineer and can still override a send. Does not restore auto-decline or auto-bind.

## D-018 — Approve change P-001
- Date / Owner: 2026-10-10 / @user
- Context: Four premises misses on SUB-067 through SUB-076 stored an address with no five-digit ZIP. The assistant had proposed dropping that value and marking the page for a person.
- Options considered: Correct the city and the ZIP. Or drop the value and leave the page for a person.
- Decision: Approve change P-001. If the premises value has no five-digit ZIP, do not store it, and add the source page to needs human read. Do not rewrite the city. Do not invent a ZIP. Do not change a loss-run date. Do not rescore the published SUB-067 through SUB-076 file.
- Rationale: The user replied "approve change P-001".
- Dissent: none
- Follow-up tasks: T-047
- Status: ACCEPTED
- Amends: nothing about auto-decline or auto-bind. P-002 through P-005 were requested as proposals and are not approved.

## D-019 — Locations, an OCR test, and a new hold-out
- Date / Owner: 2026-10-10 / @user
- Context: The user approved P-005 and P-004. P-002 was waiting on a ZIP list. P-003 would have applied OCR confidence to typed files. SUB-067 through SUB-076 had been used to study errors.
- Options considered: Switch the live OCR to EasyOCR. Or report the comparison and leave Tesseract in place. Apply the new confidence number to every file. Or limit it to scans and send that as a new proposal.
- Decision: (1) P-005 is approved. A labeled second location is stored as a location list with one primary, and it is not a premises conflict. Two unlabeled addresses stay a conflict. (2) P-004 is approved as a test only. EasyOCR was compared with Tesseract on the development scans. The live reader stays Tesseract. (3) P-002 stays unapproved. The OCR results are now in, and P-002 still waits for "approve change P-002". (4) P-003 is closed. The redesign is P-003b: OCR confidence only on scanned pages; typed PDFs, Excel, and email keep the current path. It is not approved. (5) SUB-067 through SUB-076 are development data. After P-005 and the OCR report, @producer builds SUB-077 through SUB-086, gold first, and @model-risk scores it with no further code changes, compared with the SUB-067 through SUB-076 baseline.
- Rationale: The user said this directly.
- Dissent: none
- Follow-up tasks: T-049, T-050, T-051, T-052, T-053
- Status: ACCEPTED
- Amends: the hold-out boundary. SUB-067 through SUB-076 are no longer the untouched hold-out. Does not restore auto-decline or auto-bind. Does not switch OCR.

## D-020 — Address check, scan confidence, and quieter scores
- Date / Owner: 2026-10-10 / @user
- Context: The user approved P-003b and approved P-002 as a flag only. The user asked for a regression of the current code on SUB-017 through SUB-076 before those two edits, an explanation of the SUB-077 through SUB-086 year-built and status scores, and a proposal for an EasyOCR fallback. The user also set two standing rules.
- Options considered: Rewrite a mismatched city to the ZIP's city. Or keep the text and flag it. Apply OCR confidence to every file. Or apply it only to scans. Switch the live reader to EasyOCR. Or leave Tesseract in place and propose a fallback. Keep scoring 10-file hold-outs. Or use 20 from now on.
- Decision: (1) P-003b is approved and in the code. On a scanned page the gate uses the Tesseract word score. A typed PDF, an Excel file, and an email keep the model's confidence and the 0.75 gate. The workbench shows both numbers. The frozen scorers were not edited. Self-checks passed. (2) P-002 is approved as validation only. A five-digit ZIP that is not in the Texas list, or a city that does not match that ZIP, is marked "address invalid". The original text stays. There is no automatic city correction and no invented ZIP. P-001 still drops a premises value that has no five-digit ZIP before this flag runs. (3) The regression of the code before those two edits is `deliverables/ai-engineer/evals/regression-SUB-017-076-before-P002-P003b.json`, with the comparison in `regression-SUB-017-076.md`. It is not a production approval. (4) On SUB-077 through SUB-086, year built at 7/10 is not P-001 or P-005. SUB-077's OCR year is 1942 against gold 1948. SUB-078's OCR year is 1991 against gold 1981. SUB-081's year is only in the attachment, and that call did not copy the attachment. SUB-084 and SUB-085 OCR years matched gold and were not year misses. (5) Status at 5/10 is SUB-077, SUB-078, SUB-081, SUB-084, and SUB-085. The four scans have no five-digit ZIP in the OCR line, so P-001 drops the premises and the file is incomplete while gold says complete. That status miss is a side effect of the approved P-001 rule on a harder scan. SUB-081's premises had a real ZIP and was not a miss. It is incomplete because the attachment fields were not extracted. (6) SUB-081 is not a code path that skips attachments. SUB-071, the same shape, was clean on its published score. SUB-061, the same shape, was clean on its published score and came back empty on this regression. That is the model failing to copy the attachment on that call. (7) P-006 is a proposal only. EasyOCR is not a fallback in the live reader. Tesseract stays. (8) After every approved change, score SUB-017 through SUB-076 again and report any field whose hit count drops. The run after P-002 and P-003b is in progress and writes a separate file. (9) Future hold-out sets are 20 submissions. SUB-077 through SUB-086 stays a set of 10 and is not expanded.
- Rationale: The user said this directly.
- Dissent: none
- Follow-up tasks: T-054, T-055, T-056, T-057, T-058
- Status: ACCEPTED
- Amends: future hold-out size. Does not restore auto-decline or auto-bind. Does not switch OCR. Does not authorize a send. Does not rewrite a published hold-out score.
