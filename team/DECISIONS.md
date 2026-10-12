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

## D-021 — A failed model call is not "no data"
- Date / Owner: 2026-10-10 / @user
- Context: Eight files came back with no fields on the regression before P-002 and P-003b, and that run did not save the error. One of them, SUB-051, scored 10 of 10 when it was called again alone. The model host refused a call on 2026-10-10 with HTTP 429, tokens per day: limit 200,000, used 198,304. The old code waited at most 60 seconds on a 429, tried six times, and then stored an empty file with every field missing.
- Options considered: Keep an empty file as an incomplete file. Or give it its own status, block the send, and count it apart from a miss.
- Decision: (1) A failed or empty model call gets the status "extraction_failed" with the error. The workbench shows it. No missing-information request is drafted for that file. No send is allowed for that file, by the account manager or by the user. Every scorer counts it apart: hit, miss, not credited, flagged, call failed. (2) SUB-077 through SUB-086 is scored again with the retry and with no extraction change. If a call failed in the original run, the rerun replaces the original score. Both are kept in the memo. (3) Every failed call is counted by cause: rate limit 429, timeout, or other. Calls are paced to the host's token limit. (4) P-006 is approved. It is implemented only after (1), (2), and (3) are done. The regression runs again after it.
- Rationale: The user said this directly.
- Dissent: none
- Follow-up tasks: T-059, T-060, T-061, T-062
- Status: ACCEPTED
- Amends: how every score is counted from now on. Does not restore auto-decline or auto-bind. Does not authorize a send. Published scores before this decision are not recounted.

## D-022 — Extraction cache, a quick regression set, and a token log
- Date / Owner: 2026-10-10 / @user
- Context: Every score run called the model again for every file. The model host allows 200,000 tokens a day. One day of scoring used all of it, and the next runs waited on the limit or failed.
- Options considered: Keep calling the model on every run. Or save each model result and call the model only when the files, the prompt, the OCR settings, or the model change.
- Decision: P-007 is approved and in the code. (1) Each model result is saved under a key made from the file contents, the prompt version, the OCR settings, and the model name. A matching key is reused. Rules that run after the model, such as the gates, validation, status, conflicts, and carrier match, run again on the saved result with no model call. (2) An interrupted score continues from the saved results. (3) A failed or empty call is never saved. It stays "extraction_failed" and is called again on the next run. (4) The check after each change is a quick set of 15 development files. The full 60 files run only at milestones. (5) Tokens are logged for each call and each run. (6) The order after P-007 is: finish the SUB-077 through SUB-086 rerun, check P-002 and P-003b on saved results, then P-006.
- Rationale: The user said this directly.
- Dissent: none
- Follow-up tasks: T-063, T-064
- Status: ACCEPTED
- Amends: D-020 item 8. The check after each approved change is the quick set of 15. The full regression runs at milestones. Does not change a hit or miss rule. Does not authorize a send.

## D-023 — Provider guard, temperature 0, a variance run, a name-swap test, and a review round
- Date / Owner: 2026-10-11 / @user
- Context: The role file for @ai-engineer-assistant still told it to run the full SUB-017 through SUB-076 regression after each change, which D-022 replaced. The repo `.env` holds a paid OpenAI key and D-011 forbids a paid API. Fifteen tasks sat in IN_REVIEW with no verdict. R-014: the same files score differently from one run to the next.
- Options considered: Leave the provider to whatever the environment holds. Or refuse to run unless the host is the expected Groq URL. Keep the default temperature. Or set it to 0 and measure the spread over three runs.
- Decision: (1) The @ai-engineer-assistant role file says to use the quick 15-file regression set after each change, in both `.claude/agents/` and `.cursor/rules/`. This is an explicit exception to "the Cursor files stay unchanged", for that one line. (2) P-008 is approved. The pipeline must never load `.env` for LLM settings. At the start of every eval or extraction run it prints the provider URL and the model name, and it refuses to run if LLM_BASE_URL is not the expected Groq URL unless the user sets ALLOW_PROVIDER=<name>. `.env` was checked on 2026-10-11: it is in `.gitignore`, it is not tracked, and it was never committed on any ref. (3) A review round: all 15 tasks in IN_REVIEW, including T-060, get verdicts from independent reviewer subagents. (4) P-009 is approved. Temperature is 0. The quick 15-file set runs 3 times on openai/gpt-oss-120b with fresh calls, and each field's mean and min–max are reported. Only the first run is cached. (5) A name-swap counterfactual test runs on cached extractions with no model calls. The risk score and the carrier match must not change. (6) Then P-006, the EasyOCR fallback, starts, and the quick set is rerun. The user's uncommitted changes in `src/insureflow` are left alone.
- Rationale: The user said this directly, and typed "approve change P-008" and "approve change P-009".
- Dissent: none
- Follow-up tasks: T-065 (P-008), T-066 (P-009 and the three runs), T-067 (name-swap test), T-068 (quick set after P-006). Carried over: T-064, T-062. Order: T-065, T-066 with T-064, T-067, T-062, T-068.
- Status: ACCEPTED
- Amends: nothing about auto-decline or auto-bind. Does not authorize a send. Does not rewrite a published hold-out score. P-008 and P-009 are not production approvals.
- Amended by @user, 2026-10-11, same day: "P-008: allow Groq and localhost (Ollama) without ALLOW_PROVIDER; block everything else." Item (2) now reads: the run is allowed when LLM_BASE_URL is the Groq URL or a localhost (Ollama) URL. Any other host is refused unless the user sets ALLOW_PROVIDER=<name>.
- Amended again by @user, 2026-10-11: "P-008 follow-up: ALLOW_PROVIDER must name the exact allowed host; cache-only runs with zero model calls skip the guard." ALLOW_PROVIDER lets a host through only when its value is exactly that host. A run that makes no model call, because every result comes from the cache, is not refused.


## D-024 — A reply whose values are all rejected is not a failed call
- Date / Owner: 2026-10-11 / @user
- Context: @model-risk's review of T-059 (Medium-1) found that a model reply whose values are all rejected by the gate is labelled "model call returned no fields", is counted as call failed in every scorer, and was saved to the cache. That hides model errors from the score. @model-risk asked the user to rule on whether it is a miss or a failed call.
- Options considered: Keep it as a failed call. Or treat it as an answered call whose fields are misses.
- Decision: All values rejected is not a failed call. The fields are counted as misses. The file status is "all_values_rejected". The file goes to human review. It is never sendable.
- Rationale: The user said this directly: "Ruling on Medium-1: all values rejected = not a failed call. Count fields as misses, file status all_values_rejected, goes to human review, never sendable."
- Dissent: none
- Follow-up tasks: T-070, T-071 (P-010). T-069 for the saved-file keys. T-059 stays open until its reviewers look again.
- Status: ACCEPTED
- Amends: D-021 item 1, for the case where the model answered and the gate rejected every value. A call that failed or returned nothing stays "extraction_failed". This ruling is not an "approve change P-###". The code and scorer change still needs a numbered proposal and the user's approval of it. Published scores are not recounted. Does not authorize a send.

## D-025 — Published score files are read-only
- Date / Owner: 2026-10-11 / @user
- Context: During T-065 a test run of `regression_dev.py --holdout eval_holdout_077` made no model call but overwrote the two published SUB-077 through SUB-086 score files, because that scorer writes to the published path on every run. Both were restored from the last commit. A check on 2026-10-11 found nothing lost: the two files were unchanged against the commit before the run, they are byte-identical to the `-original` copies, and the uncommitted rerun files (`SUB-077-086-holdout-rerun.json`, `.md`, and `SUB-077-086-original-vs-rerun.md`) are separate files that the scorer does not write.
- Options considered: Keep relying on a restore from git. Or make published score files read-only and send test output elsewhere.
- Decision: From now on, published score files are read-only. Tests write only to a scratch folder.
- Rationale: The user said this directly: "Rule from now: published score files are read-only; tests write only to a scratch folder."
- Dissent: none
- Follow-up tasks: T-072 (P-011)
- Status: ACCEPTED
- Amends: nothing about auto-decline or auto-bind. The frozen scorers still write to the published paths in code. Changing where they write is a scorer edit and needs a numbered proposal and the user's approval. Until then, nobody runs a scorer's main against its published path.

## D-026 — The SUB-077 through SUB-086 rerun is accepted as-is, and every 429 and retry is saved
- Date / Owner: 2026-10-11 / @user
- Context: @model-risk's review of T-060 was APPROVE WITH CHANGES. P-002 and P-003b went into the code between the original run and the rerun, so "no extraction change" was not met as D-021 item 2 words it. The memo's "0 failed, rate limit 429: 0" was not backed by a saved file. The memo counted nine changed marks where the files show ten. The rerun file carried a header saying @model-risk scored it.
- Options considered: Accept the rerun as it is. Or ask for a rescore of the cached results with P-002 and P-003b off.
- Decision: (1) The rerun is accepted as-is. It is relabeled "with P-002 and P-003b, not a same-code comparison". It is not quoted as an improvement. The original stays the official baseline. (2) The memo's count is fixed to 10 marks, 9 up and 1 down. (3) The false @model-risk header is removed from the rerun file. (4) From now on, every 429 and retry is saved in the token log, so failed-call claims are backed by a file.
- Rationale: The user said this directly: "T-060 ruling: accept the rerun as-is, relabeled "with P-002 and P-003b, not a same-code comparison", not quoted as an improvement; the original stays the official baseline. Fix the count to 10 marks (9 up, 1 down) and remove the false @model-risk header. From now on, every 429 and retry is saved in the token log so failed-call claims are backed by a file."
- Dissent: none
- Follow-up tasks: T-060 (the memo and rerun-file corrections), T-073 (P-012), T-061 (the counts)
- Status: ACCEPTED
- Amends: D-021 item 2, for this rerun only. Item (4) changes `underwriting_pipeline/ai/llm_extract.py`. It is numbered P-012. The user typed "approve change P-012" on 2026-10-11, so P-012 is approved: every 429 and every retry is saved in the token log. Nothing else in the extractor changes under P-012. Does not rewrite a published hold-out score. Does not authorize a send.

## D-027 — Approve change P-013: atomic cache writes
- Date / Owner: 2026-10-11 / @user
- Context: @model-risk's review of T-063 (Medium-1) found that a truncated saved cache file is trusted and returns "extraction_failed" on every later run with no model call. Medium-2 of the same review is the all-values-rejected case.
- Options considered: Leave the plain write. Or write to a temp file and rename it, and treat an unreadable saved file as not saved.
- Decision: P-013 is approved. Cache writes are atomic: a temp file, then a rename. An unreadable cache file counts as not cached and is retried. A self-check with a half-written file is added. Medium-2 is covered by the D-024 ruling in P-010 and is not part of P-013.
- Rationale: The user said this directly: "T-063: fix Medium-1 as P-013 — atomic cache writes (temp file then rename) and an unreadable cache file counts as not cached and is retried. Add a self-check with a half-written file. approve change P-013. Medium-2 is covered by my D-024 ruling in P-010."
- Dissent: none
- Follow-up tasks: T-074 (P-013). T-063 stays open until its reviewers look again.
- Status: ACCEPTED
- Amends: nothing about auto-decline or auto-bind. Does not change the cache key, the prompt, or a hit or miss rule. P-010 and P-011 are still not approved. Not a production approval.

## D-028 — Loose ends on P-012 and P-013
- Date / Owner: 2026-10-11 / @user
- Context: After P-012 and P-013 were built, @ai-engineer-assistant reported three things it had not decided: an unusable reply is logged as "reply_not_usable" but is left out of the failure totals; a killed run can leave a ".tmp" file in the cache folder; the rerun file still names the retired handle @ai-engineer as author.
- Options considered: Leave them. Or close them.
- Decision: Count reply_not_usable in the failure totals. Clean up .tmp files at the start of each run. Fix the old Author handle.
- Rationale: The user said this directly: "Loose ends: count reply_not_usable in the failure totals, clean up .tmp files at the start of each run, fix the old Author handle."
- Dissent: none
- Follow-up tasks: T-075. T-061 for the fourth failure count.
- Status: ACCEPTED
- Amends: P-012 (the failure totals) and P-013 (the .tmp cleanup). These are follow-ups by the user to changes already approved, not new proposals. Published score files stay read-only (D-025); the Author line is corrected only in files that are not published scores. P-010 and P-011 are still not approved.

## D-029 — Approve change P-010 and P-011, with the options chosen
- Date / Owner: 2026-10-11 / @user
- Context: P-010 (the T-059 fix, including D-024) and P-011 (D-025) are in `deliverables/ai-engineer/proposals-P-010-P-011.md`. Each left choices to the user.
- Options considered: For P-010: G1 or G2, D1 or D2, S1 or S2, C1 or C2, and whether to add Low-2. For P-011: W1 or W2, U1 or U2, O1 or O2, whether to lock the development regression files, and the scratch folder name.
- Decision: P-010 is approved with G2, D1, S1, C1, and without Low-2. G2 must also compare the file's current hash with the hash saved with its status and refuse if they differ. P-011 is approved with W2, U2, O1, the development files locked, and the scratch folder name kept.
- Rationale: The user said this directly: "approve change P-010 with G2 D1 S1 C1, no Low-2; G2 must also compare the file's current hash with the hash saved with its status and refuse if they differ." and "approve change P-011 with W2 U2 O1, lock dev files, keep the name."
- Dissent: none
- Follow-up tasks: T-069 (@data-engineer, saved-file keys), T-070 (P-010, ai part), T-071 (P-010, package.py and workbench.py, @software-engineer), T-072 (P-011). Order: T-069, T-070, T-071, the T-059 reviewers again, T-072, then T-062.
- Status: ACCEPTED
- Amends: nothing about auto-decline or auto-bind. In the proposal's own words: G2 is the gate reads the last saved run and refuses when nothing is saved; D1 is the old draft is removed; S1 is an all_values_rejected file is scored with the rules already in each scorer, and only `eval_holdout.py` is edited; C1 is an all-rejected reply stays in the cache; W2 is the output-path lines of the eight scorers are edited and `score_out.py` is added; U2 is a publish run happens only after the user says so in the chat for that run; O1 is "scored once" is checked in code. The `package.py` and `workbench.py` parts of P-010 are @software-engineer's and need a task from @pm. Published scores are not recounted. Does not authorize a send. Not a production approval.

## D-030 — P-014 additions, a review triage rule, and the goal after this round
- Date / Owner: 2026-10-11 / @user
- Context: Reviews of T-063 found that the host and the temperature are not in the cache key, and that `token_log.jsonl` and part of the cache folder are tracked in git and change on every run. The review round was producing long lists of Medium and Low findings while P-006, the variance test, the fairness test, and the demo waited.
- Options considered: Keep reporting every finding in full. Or report only High findings in detail and park the rest.
- Decision: (1) P-014, when drafted, includes the host and the temperature in the cache key, and puts `token_log.jsonl` and the cache folder in `.gitignore`. (2) Triage rule from now: remaining reviews report only High findings in detail. Medium and Low findings go to `team/BACKLOG.md` for after the demo. (3) The goal after this round is P-006, the variance test, the fairness test, then demo prep, in that order.
- Rationale: The user said this directly: "When P-014 is drafted: include host and temperature in the cache key, and gitignore token_log.jsonl and the cache folder. Triage rule from now: remaining reviews report only High findings in detail; Medium and Low go to team/BACKLOG.md for after the demo. Goal after this round: P-006, variance test, fairness test, then demo prep."
- Dissent: none
- Follow-up tasks: T-076 (demo prep). T-077 (redraft P-014 as a proposal only, with the host and the temperature in the cache key and the `.gitignore` entries). team/BACKLOG.md created, B-001 through B-017. Order after the review round: T-064, T-069, T-070, T-071 and T-072, the T-059 reviewers again, T-062 (P-006), T-068, T-066 (variance), T-067 (fairness), T-076. T-077 blocks nothing. No implementation task for P-014; it is not approved.
- Status: ACCEPTED
- Amends: the order in D-023 items (4) to (6): P-006 now comes before the variance test and the fairness test. P-014 is still a proposal and is not approved by this decision. The triage rule does not remove a veto: a veto is still stated in full with what would resolve it. Does not authorize a send.

## D-031 — Batched reviews, P-014 before the baseline, the demo brief, the append-only rule, and the T-017 fix
- Date / Owner: 2026-10-11 / @user
- Context: 25 reviewer dispatches were left in the review round, 16 of them for two roles. P-014's cache-key change would make the saved results unreachable. T-076 had acceptance criteria that were @pm's assumption. Two roles had edited their own entries in append-only files. All three reviewers rejected T-017, two with vetoes.
- Options considered: One reviewer and one task per dispatch for every role, or one dispatch per role for the two non-independent reviewers with many tasks. Run the quick-set baseline before or after P-014. Fix T-017 now or park it.
- Decision: The user sent these five items and confirmed them by typing "yes". (1) "Yes, batch: one dispatch each for @senior-underwriter and @ai-engineer-assistant; independent reviewers stay one task each." (2) "Show me P-014's short A/B table now; its cache-key change lands before the T-064 baseline." (3) "Demo T-076: for my non-technical manager at Sanger & Altgelt, 10 minutes: one messy submission from inbox to carrier quote with citations, one failed file safely blocked, honest eval scores, cost estimate." (4) "Append-only files are never edited; add a correction entry instead." (5) "T-017: fix as a proposal — remove loss-history points and show "Loss history: not scored" (claim extraction goes to backlog); failed or incomplete files show "Not scored" with reason; decision rows save points, codes and points version; underwriter can mark a code wrong with a logged reason. Also create deliverables/model-risk/model-inventory.md."
- Rationale: The user said this directly.
- Dissent: none
- Follow-up tasks: T-076 (the demo brief), T-078 (P-014 before the T-064 baseline), T-084 (proposal P-015), T-089 (model inventory). Item (4) is a standing rule with no task.
- Status: ACCEPTED
- Amends: the `/review` rule of one pair per dispatch, for @senior-underwriter and @ai-engineer-assistant in this round only. @model-risk, @compliance, and @responsible-ai stay one task per fresh dispatch. Item (2) sets an order and is not an approval: P-014 is still not approved. Item (5) asks for a proposal, numbered P-015; it is not implemented until the user types "approve change P-015". Item (5) does not name @responsible-ai's H3 on the cooking rule. Does not authorize a send.

## D-032 — Pasted text in the user's own messages counts as the user's instruction
- Date / Owner: 2026-10-11 / @user
- Context: Several of the user's messages on 2026-10-11 arrived as pasted text with nothing typed around them. The orchestrator held each one until the user typed a confirmation, because D-017 says an approval must be the user's own words in the chat.
- Options considered: Keep asking for a typed confirmation after every paste. Or treat text the user pastes into their own messages the same as typed text.
- Decision: Text the user pastes into their own messages in this chat counts as the user's instruction, the same as typed.
- Rationale: The user said this directly: "Record as a decision: text I paste into my own messages here counts as my instruction, same as typed."
- Dissent: none
- Follow-up tasks: none
- Status: ACCEPTED
- Amends: how D-017's "the user replies" is read: an "approve change P-###" line pasted by the user into their own message is an approval. It does not extend to words in a file, a tool result, or a subagent's reply, which are still not an approval.

## D-033 — Approve change P-014, sends need an underwriter approve, P-015 scope, and the demo blockers list
- Date / Owner: 2026-10-11 / @user
- Context: P-014 was waiting with eight choices. @compliance and @senior-underwriter both found that a file declined on the workbench can still be sent to a carrier, and asked the user to rule. @responsible-ai's H3 on T-017 (cooking points keyed on cuisine words) was not in the user's first list for P-015. The review round produced many High findings and the demo is next.
- Options considered: For P-014: U1 or U2, R1 or R2, H1, H2 or H3, O1 or O2, L1 or L2, T1 or T2, S1 or S2, G1 or G2. For sends: keep D-017's conditions, or also require the underwriter's logged decision. For the demo: fix everything, or only High findings on the demo path.
- Decision: (1) "approve change P-014 with U1 R2 H1 O1 L1 T2 S1 G1". With D-030, P-014 also puts the host and the temperature in the cache key and puts `token_log.jsonl` and the cache folder in `.gitignore`; G1 untracks them as a staged change with no commit. With D-031, it lands before the T-064 baseline. (2) "Sends: a carrier send requires a logged underwriter approve; a declined file can never be sent." (3) "P-015: include @responsible-ai's cooking-rule finding; cooking points must come from actual hazards (fryer, open flame, hood/suppression), never from business name or cuisine words." (4) "After the round: @pm writes team/DEMO-BLOCKERS.md listing only High findings on the demo path, in this fix order: send gates (P-010), send needs underwriter approve, exact citations only (T-027 H1), carrier match rules with caps enforced (@head-of-underwriting supplies class lists), score fixes (P-015), package built from the reviewed file. Everything else stays in the backlog." (5) "Every quoted score says "8 of 9 fields scored; loss runs = date only"."
- Rationale: The user said this directly, in a message pasted by the user (D-032).
- Dissent: none
- Follow-up tasks: T-078 (P-014), T-079 (send needs an underwriter approve), T-080 (proposal P-016), T-082 and T-083 (carrier match), T-084 (proposal P-015), T-085 (package built from the reviewed file), T-076 (score wording). The list is team/DEMO-BLOCKERS.md.
- Status: ACCEPTED
- Amends: D-017 item 3: a carrier send now also requires a logged underwriter approve with no later decline, for every actor. P-015 is still a proposal to be written; it is not implemented until the user approves it. "Exact citations only" (T-027 H1) changes `underwriting_pipeline/ai/` and needs a numbered proposal and the user's approval before it is built. The carrier match rules are @head-of-underwriting's to decide. Published scores are not recounted. Does not authorize a send. Not a production approval.

## D-034 — Commit before every scored run, and a scorer status says exactly what happened
- Date / Owner: 2026-10-11 / @user
- Context: The batched review of the hold-out scores found two things. No commit shows the scorer or the extraction code as it was when any published set was scored, so "scorer not edited after the gold" and "extraction frozen" rest on the memos. On SUB-057 through SUB-066, four rows show "Call: ok" although OCR returned no text and no model call was made.
- Options considered: Keep relying on the memos. Or tie every score to a commit and make the status literal.
- Decision: From now on, the code is committed before every scored run, and the git commit hash is recorded in each score file and memo. A scorer status must say exactly what happened, for example "not sent: no readable text", never "Call: ok" when no call was made.
- Rationale: The user said this directly: "Rule from now: commit the code before every scored run and record the git commit hash in each score file and memo. A scorer status must say exactly what happened, e.g. "not sent: no readable text", never "Call: ok" when no call was made."
- Dissent: none
- Follow-up tasks: T-088 (proposal P-017). The commit before each scored run is noted on T-064, T-068, T-070, T-066, and T-093.
- Status: ACCEPTED
- Amends: how every score is produced from now on. A commit made under this rule covers the pipeline and team paths only and is not pushed; the user's uncommitted changes under `src/insureflow` are left out of it (D-023). Writing the hash and the new status wording into score output changes the scorers and `regression_dev.py`, so that part needs a numbered proposal and the user's approval before it is built. Published scores are not recounted or rewritten.

## D-035 — T-020 (c) and (e) join the demo path
- Date / Owner: 2026-10-11 / @user
- Context: @compliance's veto on T-020 lists six things that resolve it. Four are already on the demo fix order in D-033. Two were not: (c) the user's exact send line, and (e) quote tracking.
- Options considered: Leave (c) and (e) in the backlog and keep the T-020 veto open past the demo. Or add them to the demo path.
- Decision: T-020 (c) and (e) are added to the demo path. A user send must carry the user's exact "send to carrier SUB-###" line, matched to the submission id and logged. Quote tracking shows a status per submission and carrier from the carrier replies, including open subjectivities. In `team/DEMO-BLOCKERS.md` they are placed after "package built from the reviewed file", so the T-020 veto can be lifted before the demo.
- Rationale: The user said this directly: "Add T-020 (c) and (e) to the demo path: a user send must carry my exact "send to carrier SUB-###" line, matched to the submission id and logged; and quote tracking shows a status per submission and carrier from the carrier replies, including open subjectivities. Place them after "package built from the reviewed file" in DEMO-BLOCKERS.md, so the T-020 veto can be lifted before the demo."
- Dissent: none
- Follow-up tasks: T-086 (the user's exact send line), T-087 (quote tracking).
- Status: ACCEPTED
- Amends: the fix order in D-033 item (4), which now ends: package built from the reviewed file, the user's exact send line, quote tracking. Both are in `underwriting_pipeline/app/`, owned by @software-engineer. Lifting the veto is @compliance's call after review. Does not authorize a send.

## D-036 — T-026 closes as scored, component not accepted
- Date / Owner: 2026-10-11 / @user
- Context: T-026 is the hold-out score of the old label scanner on SUB-017 through SUB-026. Its third acceptance criterion is "@model-risk accepts the component". @model-risk's review found seven value fields at 0/10 and showed that the other 17 hits are what an extractor that returns nothing would score. D-010 replaced that extractor. The criterion can never be met.
- Options considered: Leave T-026 open. Or close it as scored with the component not accepted.
- Decision: T-026 closes as "scored, component not accepted — retired under D-010". The extractor is recorded as retired in the model inventory. The score is quoted only as "0 of 7 value fields; other hits came from empty output". It is never cited for the current extractor.
- Rationale: The user said this directly: "T-026 ruling: close as "scored, component not accepted — retired under D-010". Record it as retired in the model inventory, and quote it only as "0 of 7 value fields; other hits came from empty output". Never cite it for the current extractor."
- Dissent: none
- Follow-up tasks: T-026 (closed as worded), T-089 (model inventory).
- Status: ACCEPTED
- Amends: how T-026 closes. The published score file is not edited (D-025). The inventory is `deliverables/model-risk/model-inventory.md`, which @model-risk writes (D-031 item 5). Whether the veto is lifted is @model-risk's call once the inventory entry exists.

## D-037 — T-027: all four of @model-risk's conditions are on the demo path
- Date / Owner: 2026-10-11 / @user
- Context: @model-risk's review of T-027 was REJECT with the production veto standing, and named four things that resolve it: (a) citations, (b) confidence, (c) unread content, (d) a new hold-out. Only (a) was on the demo path under D-033. (b) changes P-003b, which the user approved in D-020.
- Options considered: Put only (a) on the demo path. Or all four.
- Decision: (a), (b), (c), and (d) are accepted, all on the demo path. (b) amends P-003b: gate on the lower of model and OCR confidence, with the OCR confidence taken from the cited words including digits. (c): every file and page is read or listed as needs human with the reason. (d): after (a) to (c) are frozen and committed, a new 20-file hold-out, gold first, commit hash saved, scored once. This is the official score for the demo. (a) to (c) are drafted as one proposal for the user's approval.
- Rationale: The user said this directly: "T-027: accept (a), (b), (c), (d), all on the demo path. (b) amends P-003b: gate on the lower of model and OCR confidence, OCR confidence from the cited words including digits. (c): every file and page is read or listed as needs human with the reason. (d): after (a)–(c) are frozen and committed, a new 20-file hold-out, gold first, commit hash saved, scored once — this is the official score for the demo. Draft (a)–(c) as one proposal for my approval."
- Dissent: none
- Follow-up tasks: T-080 (proposal P-016 for (a), (b), and (c)), T-091 (@producer builds SUB-087 through SUB-106), T-092 (@senior-underwriter, gold first), T-093 (@model-risk scores once). T-088 (proposal P-017) for the hash in the score file.
- Status: ACCEPTED
- Amends: D-033 item (4), where "exact citations only" stood alone: the proposal is P-016 and covers (a), (b), and (c) together. D-020 item (1), P-003b, is amended by (b) once P-016 is approved. P-016 is not implemented until the user approves it. The hold-out in (d) follows D-020 and D-022 (20 submissions, gold first, no code change after the gold exists), D-025 and P-011 (published once), and D-034 (commit first, hash recorded). Published scores are not recounted. Not a production approval; lifting the veto is @model-risk's call.

## D-038 — Five rulings for the demo path, and who commits
- Date / Owner: 2026-10-11 / @user
- Context: @pm's round wrap-up listed points only the user could decide: a file declined and then approved; whether line 3b stays; whether backlog Highs B-138 and B-139 join the demo path; what the new hold-out scores; the price basis for the cost estimate; and who makes the D-034 commits, since no role may commit.
- Options considered: For a declined file: never sendable once declined, or the latest decision wins. For the hold-out: score effective date and claims, one of them, or neither.
- Decision: In the user's words. (1) "Latest decision wins: a file is sendable only if its latest logged decision is approve; an approve after a decline requires a reason, and full history stays in the log." (2) "Keep 3b on the demo path." (3) "Yes, add B-138 and B-139 to the demo path: the decision log accepts only real underwriter ids tied to my session, and edit stores the corrected value, which the package uses." (4) "New hold-out scores effective date but not claims; label becomes "9 of 10 fields scored; loss runs = date only"." (5) "Cost estimate: enterprise list prices (Gemini Flash/Pro on Vertex AI, Document AI layout) with tokens per file measured from our token log; label "estimate from public list prices, Oct 2026; free tier is development only"." (6) "Yes, make the D-034 commits yourself as described, no push." The orchestrator makes each commit before a scored run: pipeline, deliverables, and team paths only, on the ai-team branch, `src/insureflow` left out, no push.
- Rationale: The user said this directly, in a message pasted by the user (D-032).
- Dissent: none
- Follow-up tasks: assigned by @pm
- Status: ACCEPTED
- Amends: D-033 item (2): "a declined file can never be sent" now reads as item (1) here. D-033 item (5): the label "8 of 9 fields scored; loss runs = date only" stays for every score published before the new hold-out; the new hold-out carries the label in item (4). Item (4) settles the scorer choice that P-017 was to list. Item (5) is an estimate for the demo and does not change D-011: no paid API is used. Does not authorize a send. Not a production approval.

## D-039 — Approve change P-016 and P-017, with the options chosen, and the hold-out label
- Date / Owner: 2026-10-11 / @user
- Context: P-016 (T-027 (a), (b), (c)) is in `deliverables/ai-engineer/proposal-P-016.md` with twelve lettered choices. P-017 (D-034) is in `deliverables/ai-engineer/proposal-P-017.md` with four lettered choices and one point on the label, because the extractor has nine fields and the new scorer scores all nine.
- Options considered: For P-016: N1 or N2, H1 or H2, D1 or D2, R1 or R2, Q1 or Q2, C1, C2 or C3, S1 or S2, G1 or G2, L1 or L2, E1 or E2, P1 or P2, K1 or K2. For P-017: U1, U2 or U3, V1 or V2, X1 or X2, J1 or J2. For the label: "9 of 10" as in D-038, or other words.
- Decision: In the user's words. "approve change P-016 with N2 H2 D2 R1 Q1 C3 S2 G2 L1 E1 P1 K1, plus: at approve, the workbench lists every needs-review value and the underwriter acknowledges them; the acknowledgment is logged." "approve change P-017 with U1 V2 X1 J1." "Label: "9 of 9 extracted fields scored; claims not read; loss runs = date only"."
- Rationale: The user said this directly.
- Dissent: none
- Follow-up tasks: assigned by @pm
- Status: ACCEPTED
- Amends: D-020 item 1 (P-003b): on a scanned page the gate is now the lower of the model's confidence and the OCR score of the cited words, digits included, by option C3. D-038 item (4): the new hold-out's label is "9 of 9 extracted fields scored; claims not read; loss runs = date only"; it still scores effective date and not claims. The acknowledgment at approve is in `underwriting_pipeline/app/workbench.py`, owned by @software-engineer, and is on the demo path with P-016. V2 means the commits made before a scored run also cover `deliverables/senior-underwriter/gold-set/` and `simulation/inbox/`. Scores published before the new hold-out keep "8 of 9 fields scored; loss runs = date only" and are not recounted. Does not authorize a send. Not a production approval; lifting the T-027 veto is @model-risk's call.

## D-040 — Approve change P-015 with the options chosen, and the wrap-up for the night
- Date / Owner: 2026-10-11 / @user
- Context: P-015 (the T-017 score fixes) is in `deliverables/data-scientist/proposal-P-015.md` with eight lettered choices. The P-014 build was running and the session was ending for the night.
- Options considered: For P-015: S1, S2, S3 or S4; H1, H2 or H3; M1 or M2; T1 or T2; V1, V2 or V3; W1 or W2; A1 or A2; E1 or E2.
- Decision: In the user's words. "approve change P-015 with S3 H1 M1 T2 V3 W1 A1 E2. A2 (underwriter adds a missed code) goes to the backlog." For the night: the current P-014 build finishes and no new build turn starts after it. The orchestrator makes the D-034 commit (pipeline, deliverables, team, simulation/inbox and gold set; not src/insureflow). A Claude Code command /wrap-up is created: wait for running turns; standup entries; run self-checks; secret scan on everything to be committed (gsk_, sk-, AIza, .env, token_log, cache) and stop if anything is found; show the file list; commit with today's summary and date; push only the ai-team branch to origin, never main, never force; write team/NEXT-SESSION.md with where we stopped, pending decisions, and the first 3 tasks. Before pushing, the orchestrator tells the user whether origin exists and whether the GitHub repo is private. If it is public or missing, it stops and does not push.
- Rationale: The user said this directly, in a message pasted by the user (D-032).
- Dissent: none
- Follow-up tasks: assigned by @pm
- Status: ACCEPTED
- Amends: nothing about auto-decline or auto-bind. With S3 and T2, P-015 includes a change in `underwriting_pipeline/ai/prepare.py`, built by @ai-engineer-assistant. P-015 is not built tonight. Not a production approval; each veto on T-017 is lifted only by its holder. Does not authorize a send.
