# Standup Log (append only)

Format:
```
### YYYY-MM-DD — @role
- Done:
- Doing next:
- Blocked by / need from:
```

### 2026-10-09 — @pm
- Done: Charter and Sprint 1 breakdown (T-001). Closed T-001 after @head-of-underwriting's review. Opened T-010–T-012. Left D-002 PROPOSED.
- Doing next: Chase the open reviews. Do not open Build tasks.
- Blocked by / need from: @actuary on loss ratio; reviewers named in the round-close note.

### 2026-10-09 — @head-of-underwriting
- Done: Supported T-001 with conditions. Drafted appetite guide, authority matrix, and D-002 (no auto-decline; tight auto-quote).
- Doing next: Answer @senior-underwriter on habitational wording and no-known-loss letters after @actuary's loss ratio. Review T-005.
- Blocked by / need from: @actuary (T-011 / D-002).

### 2026-10-09 — @senior-underwriter
- Done: Workflow and required fields (T-003). Objected to habitational-as-target and no-known-loss letters.
- Doing next: T-010 only after T-002 is accepted and T-003 review is back.
- Blocked by / need from: @ai-engineer and @data-engineer review of T-003. @head-of-underwriting confirmation on student and subsidized housing.

### 2026-10-09 — @compliance
- Done: Regulatory register (T-005). Supported D-002 with conditions. No veto.
- Doing next: Review T-008. T-012 after the data inventory exists.
- Blocked by / need from: Real counsel on writing entity, pilot states, rate manual, declination content. @head-of-underwriting and @responsible-ai review of T-005.

### 2026-10-09 — @model-risk
- Done: Validation standards (T-008). Classed auto-quote as Tier 1. Approved nothing.
- Doing next: Open the model inventory when T-006 exists. Review whatever claims it is "not a model."
- Blocked by / need from: @compliance review of T-008. T-006 for the inventory.

### 2026-10-09 — @pm
- Done: Opened round 2 on the unanswered reviews. Closed T-003, T-005, T-008, and T-011 after the reviewers signed. Left T-002 open for @senior-underwriter.
- Doing next: Get T-002 confirmed so T-010 can start. Chase T-004, T-006, and T-012 reviews.
- Blocked by / need from: @senior-underwriter on the D-003 edit. User or counsel on R-006 before any live quote.

### 2026-10-09 — @actuary
- Done: Planning permissible LR 0.65 and segment ranges (T-011). Objected to artisan in auto-quote. Accepted by @head-of-underwriting.
- Doing next: Review a loss model only after T-004 is accepted and @data-scientist frames it. Nothing to price beyond the filed rate.
- Blocked by / need from: Our own triangle. These numbers are not an indication.

### 2026-10-09 — @ai-engineer
- Done: Accepted T-003. Proposed architecture (T-006): LLM extracts, rules triage, humans decline. Extraction held at Tier 2.
- Doing next: Answer reviewer findings on T-006. No prompts or code until the proposal is accepted.
- Blocked by / need from: @ml-engineer, @software-engineer, @model-risk, @compliance on T-006.

### 2026-10-09 — @data-engineer
- Done: Accepted T-003. Draft inventory and canonical model (T-004), with null vs zero and a conflict entity.
- Doing next: Revise the model from review. No historical extract yet.
- Blocked by / need from: @compliance, @data-scientist, @ai-engineer on T-004. @responsible-ai and me on T-012.

### 2026-10-09 — @responsible-ai
- Done: Accepted T-005 with a proxy concern on territory and protection class. No veto.
- Doing next: Fairness test plan (T-009) and review of T-012.
- Blocked by / need from: Nothing on T-009. Proxy review of the auto-quote gates is part of that plan.

### 2026-10-09 — @compliance
- Done: Accepted T-008. Permitted-use review (T-012): S-08 prohibited, training prohibited, S-03 cannot mean zero claims.
- Doing next: Answer T-006 when it is my review turn. Hold S-05 until counsel confirms the vendor is not a consumer report.
- Blocked by / need from: @responsible-ai and @data-engineer on T-012. Counsel on R-006 and S-05.

### 2026-10-09 — @head-of-underwriting
- Done: Accepted D-003. Narrowed auto-quote to office, dry retail, and light wholesale. Adopted the habitational, no-known-loss, and artisan objections. Accepted T-011 and T-005.
- Doing next: Nothing until @senior-underwriter confirms the edited guide. Then review T-010.
- Blocked by / need from: @senior-underwriter confirmation. Counsel on the writing entity and rate manual before any bind.

### 2026-10-09 — @pm
- Done: Re-planned the board under D-004. Cancelled the carrier auto-quote tasks. Wrote the agency roadmap (T-013).
- Doing next: Close reviews on steps 1–3 before opening the workbench.
- Blocked by / need from: Reviewers on T-014, T-015, T-016, T-018, T-007, T-009.

### 2026-10-09 — @compliance
- Done: Agency register (T-022). S-05 set to not used on T-012.
- Doing next: Review step 1–3 code for a bind or an applicant-facing decline.
- Blocked by / need from: Counsel on A-01, A-03, A-07, A-08 before any real submission.

### 2026-10-09 — @senior-underwriter
- Done: Objected to sending the missing-info request with no account manager, and to treating a complete ACORD as carrier-ready.
- Doing next: Review T-014, T-015, T-016, and the Carrier A/B/C rules.
- Blocked by / need from: Real carrier supplementals. Placeholders do not have them.

### 2026-10-09 — @actuary
- Done: Score-use note (T-023). Blocked training on carrier declines and on underwriter clicks.
- Doing next: Review the point-score framing and the carrier match.
- Blocked by / need from: Loss labels we may never receive.

### 2026-10-09 — @head-of-underwriting
- Done: Accepted the roadmap, T-022, and T-023. Drafted Carrier A/B/C match. Left D-004 closed.
- Doing next: Nothing until reviewers mark up the match rules.
- Blocked by / need from: The real panel. A/B/C are placeholders.

### 2026-10-09 — @data-engineer
- Done: Removed the protection-class vendor from the inventory. Accepted the T-012 change.
- Doing next: Adjust the model if extraction field ids drift.
- Blocked by / need from: @data-scientist and @ai-engineer on T-004.

### 2026-10-09 — @ai-engineer
- Done: Cited extraction and completeness on synthetic text (T-015, T-016). No-known-loss stays null.
- Doing next: Address review. Do not call an LLM until a reviewer asks for that failure mode.
- Blocked by / need from: @senior-underwriter, @model-risk, @data-engineer, @compliance.

### 2026-10-09 — @software-engineer
- Done: Intake hashes a pack and rejects an empty one (T-014).
- Doing next: Workbench only after steps 1–3 are accepted.
- Blocked by / need from: Reviews of T-014.

### 2026-10-09 — @data-scientist
- Done: Framed a point score. Dropped carrier-refusal as the label.
- Doing next: Reason-code table only after T-007 is accepted.
- Blocked by / need from: @actuary, @responsible-ai, @model-risk.

### 2026-10-09 — @responsible-ai
- Done: Accepted the agency register. Wrote the fairness plan. No AI approve/decline metric.
- Doing next: Name-swap test once a score exists.
- Blocked by / need from: @compliance and @data-scientist on T-009.

### 2026-10-09 — @model-risk
- Done: Withdrew auto-quote from the standards. Tier 2 while a human decides. Approved nothing.
- Doing next: Review extraction and the framing.
- Blocked by / need from: Nothing. I am the reviewer next round.

### 2026-10-09 — @ml-engineer
- Done: Left step 8 blocked. No serving work.
- Doing next: Feedback log spec when the workbench stores decisions.
- Blocked by / need from: T-019.

### 2026-10-09 — @producer
- Done: Dropped SUB-001 (office, complete), SUB-002 (restaurant, thin file, claims to be a resend), SUB-003 (powder coating, address and area disagree). No open requests were waiting.
- Doing next: Answer simulation/to-producer/ when the next turn starts. Some answers will be partial.
- Blocked by / need from: Nothing inside the agency. I do not read their files.

### 2026-10-09 — @pm
- Done: Pointed intake and extraction at the inbox. Kept carrier send shut. Closed T-014, T-007, and T-009 after reviews.
- Doing next: Hold T-019 until extraction and completeness clear review.
- Blocked by / need from: @ai-engineer on the restaurant questions and a real eval set. @head-of-underwriting on where a restaurant can be marketed.

### 2026-10-09 — @software-engineer
- Done: Hashed SUB-001 through SUB-003. T-014 accepted.
- Doing next: Workbench only after T-015 and T-016 close.
- Blocked by / need from: Those two reviews.

### 2026-10-09 — @ai-engineer
- Done: Extracted the three submissions. Wrote requests for SUB-002 and SUB-003.
- Doing next: Add fryer and sprinkler questions. Keep conflicts from collapsing to one value.
- Blocked by / need from: @senior-underwriter, @model-risk, @data-engineer.

### 2026-10-09 — @senior-underwriter
- Done: Accepted the clean office. Rejected the restaurant request as too thin. Held T-018 open.
- Doing next: Read whatever the producer sends back.
- Blocked by / need from: A restaurant market, or a written no-match.

### 2026-10-09 — @compliance
- Done: Confirmed the requests do not decline or bind. Accepted T-014 and T-009. No veto.
- Doing next: Re-read the restaurant request after it asks about cooking.
- Blocked by / need from: Nothing legal on this batch. Still no real submissions.

### 2026-10-09 — @model-risk
- Done: Refused to close T-015 on three files. Accepted T-007 as framing only.
- Doing next: Review the point table when it exists. Approve nothing.
- Blocked by / need from: A labeled set, not another demo.

### 2026-10-09 — @data-engineer
- Done: Confirmed nulls on SUB-002. Flagged the missing Conflict row on SUB-003.
- Doing next: Add that row when @ai-engineer stops storing the fight only in the email.
- Blocked by / need from: That change. T-004 stays open.

### 2026-10-09 — @data-scientist
- Done: Framing and fairness plan accepted by the reviewers who owed them.
- Doing next: T-017 point table and reason codes.
- Blocked by / need from: Nothing on the start. Weights need @actuary before anyone calls them final.

### 2026-10-09 — @actuary
- Done: Accepted the framing. Refused to let the score pick a carrier. Flagged the restaurant hole in T-018.
- Doing next: Review point weights when they exist.
- Blocked by / need from: @head-of-underwriting on the restaurant market.

### 2026-10-09 — @responsible-ai
- Done: Accepted the framing. Names stay out. Gulf Coast is a test slice, not an input.
- Doing next: Name-swap once the point table exists.
- Blocked by / need from: The table.

### 2026-10-09 — @carrier-underwriter
- Done: Read simulation/to-carrier/. No submission packages were there.
- Doing next: Quote, decline, or ask questions when a package shows up.
- Blocked by / need from: A package. I do not help the agency write one.

### 2026-10-09 — @producer
- Done: Answered SUB-003 in full (application address and 8,000 sq ft). Answered SUB-002 only partly, and sent a no-known-loss letter instead of carrier runs. Dropped SUB-004 (gift shop), SUB-005 (8-plex, no runs), SUB-006 (bar).
- Doing next: Answer the new SUB-002 and SUB-005 requests if they are actually sent.
- Blocked by / need from: Those requests. I do not read the agency's files.

### 2026-10-09 — @pm
- Done: Put D-005 on the sprint. Closed T-016 after the approver gate was reviewed.
- Doing next: Keep T-019 shut until extraction review closes.
- Blocked by / need from: @model-risk on T-015. @actuary and @model-risk on the point weights.

### 2026-10-09 — @ai-engineer
- Done: Drafts no longer auto-send. Restaurant questions added. Blank approver cannot send.
- Doing next: Nothing on step 3 unless a reviewer reopens it.
- Blocked by / need from: Eval set for T-015. Conflict entity for @data-engineer.

### 2026-10-09 — @software-engineer
- Done: Documented the one-click approve command. Did not build the screen.
- Doing next: Workbench after T-015.
- Blocked by / need from: T-015.

### 2026-10-09 — @senior-underwriter
- Done: Approved SUB-002 and SUB-005. Left the bar alone. Dropped the fryer objection.
- Doing next: Read the producer's next reply on Rio Patio. Loss runs are still a letter.
- Blocked by / need from: Real carrier runs.

### 2026-10-09 — @head-of-underwriting
- Done: Wrote an explicit no-match for restaurants, bars, and nightclubs. Not a decline.
- Doing next: Rewrite that section when the real panel is named.
- Blocked by / need from: The real panel. Reviewers still have T-018.

### 2026-10-09 — @data-scientist
- Done: Point score and reason codes, in review.
- Doing next: Change weights only if @actuary replaces them. I will not invent a loss fit.
- Blocked by / need from: @actuary and @model-risk.

### 2026-10-09 — @compliance
- Done: Accepted the approval gate. No veto. T-016 closed.
- Doing next: Watch that a no-match never becomes a producer-facing decline.
- Blocked by / need from: Nothing on this batch.

### 2026-10-09 — @model-risk
- Done: Refused the point weights and kept T-015 open. Approved nothing.
- Doing next: Same, until there is a labeled set and a stated limit on the points.
- Blocked by / need from: That evidence.

### 2026-10-09 — @data-engineer
- Done: Confirmed the conflict file is not the entity we asked for.
- Doing next: Keep T-004 open.
- Blocked by / need from: A Conflict record that survives after the draft email is gone.

### 2026-10-09 — @actuary
- Done: Accepted the restaurant no-match as "we don't know," not as Carrier B's rule. Rejected the point weights as an indication.
- Doing next: Replace the weights when there is something to replace them with.
- Blocked by / need from: Loss labels.

### 2026-10-09 — @responsible-ai
- Done: Accepted the reason codes. No name or ZIP score.
- Doing next: Correction rate once overrides exist.
- Blocked by / need from: The workbench.

### 2026-10-09 — @carrier-underwriter
- Done: No new package in simulation/to-carrier/. No quote and no decline.
- Doing next: Answer when a package arrives.
- Blocked by / need from: A package.

### 2026-10-09 — @producer
- Done: No open producer requests were waiting. Sent SUB-007 through SUB-016. Mix: four clean, three missing pieces, two conflicts, one fireworks risk.
- Doing next: Answer only what actually arrives in simulation/to-producer/.
- Blocked by / need from: The user's approval. I do not read agency files.

### 2026-10-09 — @pm
- Done: Assigned D-006. Parked the old sends. Closed nothing that is not scored.
- Doing next: Wait for the user on pending-approval. Then score T-015 against the gold set.
- Blocked by / need from: The user. @model-risk will not close extraction without the score.

### 2026-10-09 — @head-of-underwriting
- Done: Replaced the no-restaurant rule. Carrier B takes restaurants and light contractors with 3 clean loss years.
- Doing next: Nothing until reviewers sign T-018.
- Blocked by / need from: Those reviews. The real panel later.

### 2026-10-09 — @ai-engineer
- Done: Restaurant questions are the five required items. Conflicts are JSON. Drafts stop in pending-approval.
- Doing next: Score the extractor against the gold set. Do not send mail.
- Blocked by / need from: @model-risk's bar. The user's approval.

### 2026-10-09 — @data-engineer
- Done: Checked SUB-014 keeps both addresses and both sources.
- Doing next: Leave the files as the conflict store until a table exists.
- Blocked by / need from: Nothing else on this shape.

### 2026-10-09 — @senior-underwriter
- Done: Wrote gold answers for SUB-007 through SUB-016. No declines.
- Doing next: Review a score report when it exists.
- Blocked by / need from: @ai-engineer running the set. @model-risk.

### 2026-10-09 — @model-risk
- Done: Refused to treat the written answers as a passed test.
- Doing next: Read the score report. Approve nothing today.
- Blocked by / need from: That report.

### 2026-10-09 — @actuary
- Done: Supported the Carrier B correction. Three clean years means runs, not a letter.
- Doing next: Nothing on price for Carrier C.
- Blocked by / need from: A filing we do not have.

### 2026-10-09 — @compliance
- Done: Confirmed the producer folder is empty. No veto.
- Doing next: Read whatever the user approves before it is treated as sent.
- Blocked by / need from: The user.

### 2026-10-09 — @carrier-underwriter
- Done: No package in simulation/to-carrier/.
- Doing next: Quote or decline only a package that names my carrier.
- Blocked by / need from: A package.

### 2026-10-09 — @producer
- Done: Left SUB-007 through SUB-016 in place. Did not invent a second batch.
- Doing next: Answer only a request the user releases.
- Blocked by / need from: An empty to-producer folder.

### 2026-10-09 — @data-engineer
- Done: Closed T-004. Conflicts now include resolution.
- Doing next: Leave resolved and unresolved rows as they are.
- Blocked by / need from: Nothing.

### 2026-10-09 — @senior-underwriter
- Done: Left the gold set. Did not approve SUB-002 or SUB-005.
- Doing next: Wait for your approve line.
- Blocked by / need from: You.

### 2026-10-09 — @head-of-underwriting
- Done: Confirmed Carrier B and the bar/nightclub no-match.
- Doing next: Nothing until a package is ready for the workbench.
- Blocked by / need from: T-015 still open.

### 2026-10-09 — @ai-engineer
- Done: Blocked every approve() caller.
- Doing next: Score the extractor against the gold set when asked.
- Blocked by / need from: That ask.

### 2026-10-09 — @model-risk
- Done: Left T-015 in review.
- Doing next: Read a score report. There isn't one.
- Blocked by / need from: The score.

### 2026-10-09 — @carrier-underwriter
- Done: Still no package.
- Doing next: Wait.
- Blocked by / need from: simulation/to-carrier/.

### 2026-10-09 — @pm
- Done: Recorded D-007. Closed the round.
- Doing next: List the pending drafts for you.
- Blocked by / need from: approve SUB-###.

### 2026-10-09 — @producer
- Done: Answered the seven user-approved requests. Did not duplicate SUB-007 through SUB-016.
- Doing next: Answer only what is actually in simulation/to-producer/.
- Blocked by / need from: The three new drafts, until you approve them.

### 2026-10-09 — @pm
- Done: Recorded D-008. Moved only the seven named drafts. Withdrew SUB-003.
- Doing next: Wait on the three residual drafts.
- Blocked by / need from: You.

### 2026-10-09 — @ai-engineer
- Done: Scored the original gold pack. approve() accepts only the user.
- Doing next: Nothing sends until you type approve.
- Blocked by / need from: @model-risk will not call this a validation.

### 2026-10-09 — @senior-underwriter
- Done: Accepted the gold comparison. Did not approve the new drafts.
- Doing next: Read a real loss run on SUB-002 and SUB-013 if you release those asks.
- Blocked by / need from: You.

### 2026-10-09 — @data-engineer
- Done: Kept T-004 closed. Corrected SUB-003's schedule area to 14000. Resolved rows stay.
- Doing next: Leave SUB-015 square feet unresolved.
- Blocked by / need from: Nothing.

### 2026-10-09 — @head-of-underwriting
- Done: Closed T-018. Carrier B recommendation on SUB-011 is not a submission.
- Doing next: Nothing until the workbench exists.
- Blocked by / need from: The real panel, later.

### 2026-10-09 — @model-risk
- Done: Accepted that the gold set was scored. Approved nothing.
- Doing next: Keep T-017 unapproved.
- Blocked by / need from: A larger set before anyone says validated.

### 2026-10-09 — @compliance
- Done: Confirmed the seven sends are not declines. SUB-003 was not sent. No veto.
- Doing next: Watch the next approve line.
- Blocked by / need from: Nothing legal on this batch.

### 2026-10-09 — @actuary
- Done: Supported closing T-018. Refused the point weights again.
- Doing next: Nothing to price.
- Blocked by / need from: Loss labels.

### 2026-10-09 — @data-scientist
- Done: Left the point table alone.
- Doing next: Change weights only if @actuary replaces them.
- Blocked by / need from: That replacement.

### 2026-10-09 — @responsible-ai
- Done: No new fairness fail. Names stay out.
- Doing next: Correction rate after the workbench.
- Blocked by / need from: T-019.

### 2026-10-09 — @software-engineer
- Done: Left the workbench unbuilt. Confirmed a role name cannot send.
- Doing next: T-019 next round.
- Blocked by / need from: Nothing on the start.

### 2026-10-09 — @ml-engineer
- Done: Left step 8 blocked.
- Doing next: Feedback log when decisions exist.
- Blocked by / need from: T-019.

### 2026-10-09 — @carrier-underwriter
- Done: No package in simulation/to-carrier/.
- Doing next: Quote or decline only a package that names my carrier.
- Blocked by / need from: A package.

### 2026-10-09 — @pm
- Done: Closed the round. Listed the three drafts still waiting.
- Doing next: Your approve or withdraw line.
- Blocked by / need from: You, on SUB-002, SUB-013, and SUB-015.

### 2026-10-09 — @producer
- Done: Answered SUB-002 and SUB-015. Left SUB-013 for a later turn. Sent hold-out SUB-017 through SUB-026.
- Doing next: Answer SUB-013 when asked again.
- Blocked by / need from: Nothing.

### 2026-10-09 — @senior-underwriter
- Done: Wrote gold for SUB-017 through SUB-026 before extraction.
- Doing next: Review the workbench on a real click.
- Blocked by / need from: Nothing for the gold.

### 2026-10-09 — @ai-engineer
- Done: Recorded the hold-out score without editing prepare.py.
- Doing next: T-027, a reader for PDF, Excel, prose, and Spanish.
- Blocked by / need from: @model-risk's rule that a null is not a hit.

### 2026-10-09 — @model-risk
- Done: Reported the hold-out failures. Rejected the 100% as proof.
- Doing next: Score the next hold-out after T-027.
- Blocked by / need from: A reader change, then a frozen rescore.

### 2026-10-09 — @software-engineer
- Done: Published the workbench page and the carrier send gate. Sent nothing.
- Doing next: Quote tracking after a carrier reply.
- Blocked by / need from: You, for send to carrier SUB-###.

### 2026-10-09 — @head-of-underwriting
- Done: Listed eleven complete in-appetite files and held them.
- Doing next: Release only the ones you name.
- Blocked by / need from: Your send line.

### 2026-10-09 — @compliance
- Done: No veto. Confirmed the page does not bind.
- Doing next: Read the first package you actually release.
- Blocked by / need from: That package.

### 2026-10-09 — @actuary
- Done: Left T-017 unapproved.
- Doing next: Block any use of the points as a price.
- Blocked by / need from: Nothing new.

### 2026-10-09 — @data-scientist
- Done: Did not refit the points.
- Doing next: Wait.
- Blocked by / need from: @actuary, if the weights change.

### 2026-10-09 — @responsible-ai
- Done: Checked that the Spanish miss is not a score feature.
- Doing next: Watch the first logged decline.
- Blocked by / need from: A real decision on the workbench.

### 2026-10-09 — @data-engineer
- Done: Resolved SUB-015 square feet to 4500 and kept both values.
- Doing next: Nothing on T-004.
- Blocked by / need from: T-027 for PDF and Excel.

### 2026-10-09 — @ml-engineer
- Done: Left step 8 blocked.
- Doing next: Count corrections after a logged decision.
- Blocked by / need from: T-019 in use.

### 2026-10-09 — @carrier-underwriter
- Done: No package arrived.
- Doing next: Answer the first file in simulation/to-carrier/.
- Blocked by / need from: That file.

### 2026-10-09 — @pm
- Done: Recorded D-009, filed the hold-out, and held every carrier package.
- Doing next: Your send line, or the next round for T-027.
- Blocked by / need from: You.

### 2026-10-09 — @producer
- Done: Answered SUB-013. Sent SUB-027 through SUB-036.
- Doing next: Nothing until the next request.
- Blocked by / need from: Nothing.

### 2026-10-09 — @senior-underwriter
- Done: Wrote gold for SUB-027 through SUB-036 before the score.
- Doing next: Read a real extract once the key works.
- Blocked by / need from: A successful model call.

### 2026-10-09 — @ai-engineer
- Done: Replaced the label scanner with a cited model call. The live call was rejected.
- Doing next: Nothing until you set OPENAI_API_KEY.
- Blocked by / need from: A key the API accepts.

### 2026-10-09 — @model-risk
- Done: Scored SUB-027 through SUB-036. Zero hits. Nulls were not credited. Reported the 401.
- Doing next: Rerun the same command after the key works. No code change first.
- Blocked by / need from: That key.

### 2026-10-09 — @software-engineer
- Done: Sent the three named packages. Left the other app alone.
- Doing next: Show confidence on the page after a real extract.
- Blocked by / need from: A successful model call.

### 2026-10-09 — @head-of-underwriting
- Done: Confirmed only the three named files were released.
- Doing next: Read the quotes.
- Blocked by / need from: Nothing.

### 2026-10-09 — @compliance
- Done: No veto. The key is not in the repo.
- Doing next: Read the next package you release.
- Blocked by / need from: Nothing.

### 2026-10-09 — @actuary
- Done: Left T-017 unapproved.
- Doing next: Block any use of the points as a price.
- Blocked by / need from: Nothing.

### 2026-10-09 — @data-scientist
- Done: Did not refit the points.
- Doing next: Wait.
- Blocked by / need from: @actuary.

### 2026-10-09 — @responsible-ai
- Done: Confirmed the 401 was not treated as a language penalty.
- Doing next: Watch the first real extract.
- Blocked by / need from: A successful model call.

### 2026-10-09 — @data-engineer
- Done: Left the conflict shape closed.
- Doing next: Check the first real disagreement the model returns.
- Blocked by / need from: That call.

### 2026-10-09 — @ml-engineer
- Done: Left step 8 blocked.
- Doing next: Count corrections after a logged decision.
- Blocked by / need from: T-019 in use.

### 2026-10-09 — @carrier-underwriter
- Done: Quoted SUB-001, SUB-002, and SUB-004.
- Doing next: Answer the next package only.
- Blocked by / need from: A new file in simulation/to-carrier/.

### 2026-10-09 — @pm
- Done: Recorded D-010 and closed the round on the 401.
- Doing next: You set the key, then the same score command.
- Blocked by / need from: You.

### 2026-10-10 — @ai-engineer
- Done: Pointed the extractor at the environment host and added a 429 wait. The test call returned HTTP 404.
- Doing next: Nothing until LLM_MODEL names a model Groq still serves.
- Blocked by / need from: That model name.

### 2026-10-10 — @model-risk
- Done: Rescored SUB-027 through SUB-036. Zero hits. Nulls were not credited. The model name was rejected.
- Doing next: Rerun the same command after LLM_MODEL changes. No scorer edit first.
- Blocked by / need from: A live model name.

### 2026-10-10 — @senior-underwriter
- Done: Left the hood draft in pending-approval. Noted the kitchen file already answers it.
- Doing next: Your approve or withdraw line.
- Blocked by / need from: You.

### 2026-10-10 — @producer
- Done: Did not answer SUB-002. The request is not in to-producer.
- Doing next: Answer it if you approve the draft.
- Blocked by / need from: That approval.

### 2026-10-10 — @pm
- Done: Recorded D-012 and closed the round on the missing model.
- Doing next: You change LLM_MODEL, or you approve SUB-002.
- Blocked by / need from: You.

### 2026-10-10 — @ai-engineer
- Done: Test call to openai/gpt-oss-120b succeeded. No code change.
- Doing next: Nothing until you want another score.
- Blocked by / need from: Nothing.

### 2026-10-10 — @model-risk
- Done: Rescored SUB-027 through SUB-036. Reported the misses. Did not approve the extractor.
- Doing next: Review the next score only if the code or the model changes.
- Blocked by / need from: Nothing.

### 2026-10-10 — @senior-underwriter
- Done: Withdrew the producer draft. Wrote the Carrier B reply and left it unsent.
- Doing next: Your release of that reply.
- Blocked by / need from: You.

### 2026-10-10 — @pm
- Done: Closed the round. One carrier reply is waiting.
- Doing next: You say whether to send the Carrier B reply.
- Blocked by / need from: You.

### 2026-10-10 — @pm
- Done: Recorded D-013 and assigned T-030, T-031, and T-032.
- Doing next: The new hold-out score, then the send list.
- Blocked by / need from: Nothing.

### 2026-10-10 — @ai-engineer
- Done: Froze OCR and the prompt after the development rerun.
- Doing next: Nothing on the extractor until the new score is in.
- Blocked by / need from: Nothing.

### 2026-10-10 — @carrier-underwriter
- Done: Accepted the SUB-002 hood answer. Quote stands at 9800 / 2500. Not a bind.
- Doing next: Nothing until another package arrives.
- Blocked by / need from: Nothing.

### 2026-10-10 — @producer
- Done: Filed SUB-037 through SUB-046. Did not run extraction.
- Doing next: Nothing until you ask for another batch.
- Blocked by / need from: Nothing.

### 2026-10-10 — @senior-underwriter
- Done: Wrote gold for SUB-037 through SUB-046 before the score.
- Doing next: Your decision on the send list.
- Blocked by / need from: You.

### 2026-10-10 — @model-risk
- Done: Scored SUB-037 through SUB-046. Compared it with the first score. Did not approve the extractor.
- Doing next: Review only if the code changes again.
- Blocked by / need from: Nothing.

### 2026-10-10 — @pm
- Done: Closed three rounds. Listed SUB-009, SUB-010, and SUB-011 for your send approval.
- Doing next: You say which of those to send.
- Blocked by / need from: You.

### 2026-10-10 — @pm
- Done: Recorded D-014. Sent SUB-009, SUB-010, and SUB-011 after you named them.
- Doing next: The new hold-out and the decision log.
- Blocked by / need from: Nothing.

### 2026-10-10 — @software-engineer
- Done: Sprinkler field and carrier loss-run rules, with tests. Rechecked SUB-005 and SUB-013.
- Doing next: Nothing until you send SUB-013.
- Blocked by / need from: You, if you want SUB-013 sent.

### 2026-10-10 — @carrier-underwriter
- Done: Quoted SUB-009, SUB-010, and SUB-011. Nothing bound.
- Doing next: Nothing until another package arrives.
- Blocked by / need from: Nothing.

### 2026-10-10 — @ai-engineer
- Done: Document rules for email wording and square feet, checked on the development files.
- Doing next: Nothing on the model prompt.
- Blocked by / need from: Nothing.

### 2026-10-10 — @producer
- Done: Filed SUB-047 through SUB-056.
- Doing next: Nothing until you ask for another batch.
- Blocked by / need from: Nothing.

### 2026-10-10 — @senior-underwriter
- Done: Wrote gold for SUB-047 through SUB-056 before the score.
- Doing next: Your decision on SUB-013.
- Blocked by / need from: You.

### 2026-10-10 — @model-risk
- Done: Scored SUB-047 through SUB-056. Did not approve a production model. Accepted the decision log as a record only.
- Doing next: Review only if the code changes again.
- Blocked by / need from: Nothing.

### 2026-10-10 — @ml-engineer
- Done: Workbench saves approve, edit, and decline with a reason and a version, and counts corrections.
- Doing next: Nothing until an underwriter uses the page.
- Blocked by / need from: Nothing.

### 2026-10-10 — @pm
- Done: Closed three rounds. SUB-013 is listed and not sent.
- Doing next: You say whether to send SUB-013.
- Blocked by / need from: You.

### 2026-10-10 — @pm
- Done: Recorded D-015 and sent SUB-013 after you named it.
- Doing next: The harder hold-out and the demo guide.
- Blocked by / need from: Nothing.

### 2026-10-10 — @software-engineer
- Done: Normalized amounts. Rechecked SUB-005. It now routes to Carrier C and was not sent.
- Doing next: Nothing until you send SUB-005.
- Blocked by / need from: You, if you want SUB-005 sent.

### 2026-10-10 — @carrier-underwriter
- Done: Quoted SUB-013 at 9200 / 5000. Nothing bound.
- Doing next: Nothing until another package arrives.
- Blocked by / need from: Nothing.

### 2026-10-10 — @producer
- Done: Filed the harder SUB-057 through SUB-066.
- Doing next: Nothing until you ask for another batch.
- Blocked by / need from: Nothing.

### 2026-10-10 — @senior-underwriter
- Done: Wrote gold for SUB-057 through SUB-066 before the score.
- Doing next: Your decision on SUB-005.
- Blocked by / need from: You.

### 2026-10-10 — @model-risk
- Done: Scored the harder hold-out and reported the misses. Did not approve the extractor.
- Doing next: Review only if the code changes again.
- Blocked by / need from: Nothing.

### 2026-10-10 — @pm
- Done: Wrote the 10-minute demo guide. Closed three rounds.
- Doing next: You run the demo, or you send SUB-005.
- Blocked by / need from: You.

### 2026-10-10 — @producer
- Done: Filed SUB-067 through SUB-076 after extraction was frozen.
- Doing next: Nothing until you ask for another batch.
- Blocked by / need from: Nothing.

### 2026-10-10 — @pm
- Done: Recorded D-016 and assigned T-041 through T-044. Closed three rounds.
- Doing next: Nothing until you decide.
- Blocked by / need from: You, only if you want another change.

### 2026-10-10 — @ai-engineer
- Done: Repaired rotation and deskew. Confirmed this Groq account has no vision model. Marked unreadable pages for a human. Added the flagged column to the next scorer.
- Doing next: Nothing. Extraction stays frozen.
- Blocked by / need from: Nothing.

### 2026-10-10 — @software-engineer
- Done: Showed "Needs human read" on the workbench.
- Doing next: Nothing.
- Blocked by / need from: Nothing.

### 2026-10-10 — @senior-underwriter
- Done: Wrote gold for SUB-067 through SUB-076 before the scored run.
- Doing next: Nothing.
- Blocked by / need from: Nothing.

### 2026-10-10 — @model-risk
- Done: Scored SUB-067 through SUB-076 and compared it with the 50% baseline. Did not approve the extractor.
- Doing next: Review only if the code changes again.
- Blocked by / need from: Nothing.

### 2026-10-10 — @carrier-underwriter
- Done: Quoted SUB-005 at Carrier C. Fictional premium 10400, deductible 5000. Not a bind.
- Doing next: Nothing until another package arrives.
- Blocked by / need from: Nothing.

### 2026-10-10 — @pm
- Done: Closed the round. Pending-approval is empty. No other package was sent.
- Doing next: Wait for you.
- Blocked by / need from: You.

### 2026-10-10 — @producer
- Done: No new submission.
- Doing next: Nothing until you ask for another batch.
- Blocked by / need from: Nothing.

### 2026-10-10 — @pm
- Done: Recorded D-017. Assigned T-045 and T-046.
- Doing next: Wait for your answer on P-001.
- Blocked by / need from: You.

### 2026-10-10 — @software-engineer
- Done: Let the account manager approve when the agency rules pass. The user can still override. Self-checks passed.
- Doing next: Nothing.
- Blocked by / need from: Nothing.

### 2026-10-10 — @ai-engineer-assistant
- Done: Wrote the premises miss analysis. Sent P-001. Did not change extraction.
- Doing next: Nothing until you approve a proposal.
- Blocked by / need from: You, for P-001.

### 2026-10-10 — @senior-underwriter
- Done: Supported P-001. Pointed out SUB-070 is two locations, not a bad scan.
- Doing next: Nothing.
- Blocked by / need from: Nothing.

### 2026-10-10 — @account-manager
- Done: Checked the queue. Nothing met the rules, so I approved nothing.
- Doing next: Review the next complete in-appetite file.
- Blocked by / need from: Nothing.

### 2026-10-10 — @model-risk
- Done: Confirmed the re-read is not a new score and that P-001 does not make a blank a hit.
- Doing next: Review only if extraction changes.
- Blocked by / need from: Nothing.

### 2026-10-10 — @pm
- Done: Closed the round. Nothing was sent.
- Doing next: Wait for you.
- Blocked by / need from: You.

### 2026-10-10 — @producer
- Done: No new submission.
- Doing next: Nothing until you ask for another batch.
- Blocked by / need from: Nothing.

### 2026-10-10 — @pm
- Done: Recorded D-018. Assigned T-047 and T-048.
- Doing next: Wait for you to approve or decline P-002 through P-005.
- Blocked by / need from: You.

### 2026-10-10 — @ai-engineer-assistant
- Done: Implemented P-001. Wrote P-002 through P-005 and did not implement them.
- Doing next: Nothing until you approve another proposal.
- Blocked by / need from: You.

### 2026-10-10 — @senior-underwriter
- Done: Supported P-001. Objected to turning every pair of addresses into locations.
- Doing next: Nothing.
- Blocked by / need from: Nothing.

### 2026-10-10 — @account-manager
- Done: No file was waiting. An unread page still blocks a send.
- Doing next: Review the next complete file.
- Blocked by / need from: Nothing.

### 2026-10-10 — @model-risk
- Done: Accepted the P-001 limit. Asked that the frozen scorer stay frozen.
- Doing next: Review only if you approve another change.
- Blocked by / need from: You.

### 2026-10-10 — @pm
- Done: Closed the round. Nothing was sent.
- Doing next: Wait for you.
- Blocked by / need from: You.

### 2026-10-10 — @producer
- Done: Filed SUB-077 through SUB-086 after P-005 and the OCR report.
- Doing next: Nothing until you ask for another batch.
- Blocked by / need from: Nothing.

### 2026-10-10 — @pm
- Done: Recorded D-019. Closed two rounds.
- Doing next: Wait for P-002 or P-003b.
- Blocked by / need from: You.

### 2026-10-10 — @ai-engineer-assistant
- Done: Implemented P-005. Reported EasyOCR against Tesseract. Sent P-003b. Did not switch OCR and did not implement P-002.
- Doing next: Nothing until you approve another proposal.
- Blocked by / need from: You.

### 2026-10-10 — @senior-underwriter
- Done: Wrote gold for SUB-077 through SUB-086 before the score. Supported the primary-location rule.
- Doing next: Nothing.
- Blocked by / need from: Nothing.

### 2026-10-10 — @account-manager
- Done: Approved nothing. The hold-out files were not sent.
- Doing next: Review the next complete file.
- Blocked by / need from: Nothing.

### 2026-10-10 — @model-risk
- Done: Scored SUB-077 through SUB-086 and compared it with the previous baseline. Did not approve the extractor.
- Doing next: Review only if the code changes again.
- Blocked by / need from: Nothing.

### 2026-10-10 — @pm
- Done: Closed round 2. Nothing was sent.
- Doing next: Wait for you.
- Blocked by / need from: You.

### 2026-10-10 — @ai-engineer-assistant
- Done: Scored SUB-017 through SUB-076 on the code before P-002 and P-003b. Implemented both approved edits. Wrote P-006. Did not switch OCR.
- Doing next: The after-change regression, then report any field that drops.
- Blocked by / need from: "approve change P-006" if you want the fallback.

### 2026-10-10 — @model-risk
- Done: Reviewed the before regression. Did not approve the extractor.
- Doing next: Review the after-change counts when they exist.
- Blocked by / need from: T-058.

### 2026-10-10 — @senior-underwriter
- Done: The address flag keeps the producer's text. "Saw Antonio" must not be rewritten.
- Doing next: Read the after-change report.
- Blocked by / need from: Nothing.

### 2026-10-10 — @account-manager
- Done: Approved nothing. Sent nothing.
- Doing next: Review the next complete file only if you ask.
- Blocked by / need from: Nothing.

### 2026-10-10 — @pm
- Done: Recorded D-020. Left the app repo alone because it already has uncommitted work.
- Doing next: Wait for the after regression and for you on P-006.
- Blocked by / need from: You, for the dirty app repo and for P-006.

### 2026-10-10 — @ai-engineer-assistant
- Done: Added "extraction_failed", the send block, and the call-failed count. Saved the before-change comparison memo. Found the daily token limit on the model host.
- Doing next: Finish the SUB-077 through SUB-086 rerun and the regression, report failed calls by cause, then P-006.
- Blocked by / need from: The model host's daily token limit. A higher limit from you would end the wait.

### 2026-10-10 — @pm
- Done: Recorded D-021. The team folders are in the app repo on ai-team. Removed the duplicate log entries.
- Doing next: Wait for the two score runs.
- Blocked by / need from: T-058 and T-060.

### 2026-10-10 — @ai-engineer-assistant
- Done: Implemented P-007: the cache, the token log, and the quick set of 15. Restarted the SUB-077 through SUB-086 rerun through the cache.
- Doing next: Finish that rerun, score the quick set for P-002 and P-003b, then P-006.
- Blocked by / need from: The model host's daily token limit.

### 2026-10-10 — @pm
- Done: Recorded D-022.
- Doing next: Wait for T-060 and T-064.
- Blocked by / need from: T-060 and T-064.

