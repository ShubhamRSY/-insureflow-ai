# Requirements register — Sanger & Altgelt insurance pilot

- Task: T-097. Requested by @user on 2026-10-13.
- Author: @pm.
- Date: 2026-10-13.
- Status: IN_REVIEW. Reviewers: @software-engineer, @model-risk, @compliance, @head-of-underwriting, @responsible-ai. The author does not approve it.
- Scope: the Sanger & Altgelt agency underwriting pipeline only, as fixed by D-004 — Texas small commercial package (BOP / property / GL), eight pipeline steps, Carriers A/B/C as placeholders, synthetic data only, no auto-decline, no auto-bind. It does **not** cover the mortgage or lending verticals of the wider Rytera product, and it does not cover the cancelled carrier/MGA auto-quote design (D-002, D-003, replaced by D-004; the `deliverables/head-of-underwriting/authority-matrix.md` auto-quote band is withdrawn by D-004 and is **not** a requirement here).

**What this document is not.** It describes what the system is required to do. It gives no verdict on any task, decides nothing, authorizes no send, and is not a production approval. Where the system does not meet a requirement today, the State column says so and cites the architecture section or the open proposal, task, or veto. Where no owner or no number is recorded, the row says so and names the role that must decide (protocol decision-rights table); it does not choose.

## How to read this register

- **Ids are stable and never reused.** Functional requirements are `FR-001` onward; non-functional requirements are `NFR-001` onward. A new requirement takes the next free number. A superceded requirement is not deleted; it is marked, and the replacement takes a new number.
- **Priority.**
  - `MUST` — required for the pilot to be correct, legal, or safe. The demo/pilot cannot go ahead without it.
  - `SHOULD` — expected, but a gap may be accepted with a written reason and an owner.
  - `COULD` — useful, not required for the pilot; may sit in the backlog.
- **Source.** A decision id (`D-###`), a task id (`T-###`), a deliverable (`agency-register`, `validation-standards`, `appetite-guide`, `carrier-match`, `authority-matrix`, `required-fields`, `data-model`, `data-use-review`, `fairness-test-plan`, `proxy-review`, `api-spec`, `workbench-ux`, `roadmap`), the architecture document (`arch §n`), or the user's words of 2026-10-13. The source is the authority; the requirement is derived from it. Every deliverable named here is cited on at least one row.
- **Owner.** Copied from the task board and the decision-rights table as they stand on 2026-10-13. Where the board records no single owner, the row says so and names the role that must decide or that @pm is asked to record (`arch §10` Q1 to Q3).
- **Verification.** How the requirement is checked: `test` (a self-check or unit test in the repo), `eval` (a scorer on a gold/hold-out set), `review` (a named reviewer's verdict), `manual-UW` (an underwriter action at the desk), `measured` (a command over the files).
- **State.**
  - `Built` — met today, with the code citation in `arch`.
  - `Partial` — met in part, with what is missing.
  - `Not built` — fixed by an approved proposal or decision but no code exists (P-### / T-###).
  - `Not decided` — needed for production, no decision or number exists; the role that decides is named. These are labeled **ASSUMED** where this register states a stand-in.
  - `Open` — blocked by an open veto or an unresolved review.
- **Numbers.** A number is `MEASURED` (from a file or a command, named here) or `ASSUMED` (with the reasoning and the deciding role) or a code constant (cited by file and line in `arch`). No measured number is invented. This register sets no target of its own except where a decision already set one.
- **As-is vs Target.** The State column separates what the code does today (`Built`, `Partial`) from what production requires (`Not built`, `Not decided`, `Open`). The descriptions come from `deliverables/architecture/architecture.md` (T-094, at commit `d5750fd`); where that document and the code disagree, the code is what runs.

## Standing rules that hold across every requirement

These are non-negotiable and are repeated in the rows where they apply.

1. **No auto-decline, no auto-bind.** The underwriter makes every final decision (D-004).
2. **No AI role approves or sends.** Only the simulated @account-manager (agency rules + a written reason) or the user (override) approves a producer request or a carrier send (D-017 item 3; D-033 item 2).
3. **A failed model call is not "no data".** Status `extraction_failed`, counted apart, never cached, no missing-info draft, never sent (D-021, D-022 item 3).
4. **A reply whose values are all rejected is its own status** `all_values_rejected`, its fields count as misses, it goes to a person, and it is never sendable (D-024, D-029).
5. **Published hold-out scores are never rewritten and frozen scorers are not edited** (D-020, D-025).
6. **No paid API.** The model host comes from the shell and is free-tier or local (D-011, D-012).
7. **Changes to extraction, prompts, OCR, models, or eval scorers** are built only after the user types the exact words `approve change P-###` (D-017).
8. **Synthetic data only.** No real applicant file is read, sent, cached, or stored without a decision that covers it (protocol; `agency-register` A-07; `arch §3.2`).

---

## A. Functional requirements

The pipeline is the eight steps of D-004. The component names are the thirteen of T-094 (`arch §0`): intake, OCR/text reading, extraction, validation gates, cache, risk score, carrier match, missing-info drafts, workbench, decision log, package/send, quote tracking, eval harness.

### A.1 Intake (step 1)

| ID | Requirement | Priority | Source | Owner | Verification | State |
|---|---|---|---|---|---|---|
| FR-001 | Intake accepts one submission as one or more documents from the (simulated) producer and assigns a stable submission id used end-to-end. | MUST | D-004 step 1; `api-spec`; arch §2.2 | @software-engineer (T-014) | test | Partial — `intake()` exists but nothing calls it; the flow runs on folder names (`arch §2.2`, gap G1) |
| FR-002 | Intake records when a submission arrived and whether it is a duplicate of one already seen; a duplicate is detected, not silently merged. | SHOULD | D-004 step 1; arch §2.2, §4.2; T-095 | @software-engineer | test | Not met — no arrival record, no duplicate detection (`arch §2.2`, gap G1) |
| FR-003 | Every intake record is marked synthetic, and the intake path accepts only synthetic files in this build. | MUST | protocol; D-004; arch §2.2, §3.2 | @software-engineer | measured | Partial — `"synthetic": True` exists but is stored nowhere and no code checks it (gap G25) |
| FR-004 | An empty submission is refused with an error and no id is issued. | MUST | arch §2.2 | @software-engineer | test | Built |

### A.2 Document reading / OCR (step 2)

| ID | Requirement | Priority | Source | Owner | Verification | State |
|---|---|---|---|---|---|---|
| FR-005 | The reader returns text for each supported file type: `.md`, `.txt`, `.csv`, `.xlsx`, `.pdf`, and images (`.png`, `.jpg`, `.jpeg`, `.tif`, `.tiff`). | MUST | D-010; arch §2.3 | @ai-engineer-assistant (T-027); @user on changes | test | Built |
| FR-006 | Every file and every page is either read or listed for a person with the reason; nothing is skipped silently (an unsupported type, a sub-folder, an unreadable page, or text past the length limit). | MUST | D-037 (c); P-016 (c) (D-039); arch §2.3, §3.1 | @ai-engineer-assistant | test | Not built — gap G15; P-016 (c) approved, no build task on the board |
| FR-007 | A scanned page that cannot be read reliably is marked "needs human" and its values are never guessed. | MUST | D-016 item 1; arch §2.3 | @ai-engineer-assistant | test | Partial — met for images; on this machine `pdftoppm` is absent so a scanned PDF is marked needs-human and is never read (gap G16) |
| FR-008 | On a scanned file, the OCR score used by the gate is taken from the words that hold the cited value, digits included. | MUST | D-037 (b); P-016 (b) (D-039, amends P-003b) | @ai-engineer-assistant | test | Not built — the page score ignores digits (gap G17, T-027 H2) |
| FR-009 | A file that cannot be opened is listed, and the other files of the submission are still read; one bad file does not stop the submission. | MUST | P-016 (c) option E1 (D-039); arch §2.3 | @ai-engineer-assistant | test | Not built — a damaged file raises out of `process_submission` (gap G14) |

### A.3 Extraction with citations (step 2)

| ID | Requirement | Priority | Source | Owner | Verification | State |
|---|---|---|---|---|---|---|
| FR-010 | Extraction sends the readable documents in one model call and receives structured JSON with one row per extracted field. | MUST | D-010; arch §2.4.1 | @ai-engineer-assistant | test | Built — one call per submission |
| FR-011 | Every extracted value carries its source document, a citation (character span), and a confidence. | MUST | D-010; arch §2.4 | @ai-engineer-assistant | test | Partial — a citation does not prove the value (gap G17, T-027 H1); P-016 (a) approved, not built |
| FR-012 | The stored value must lie inside the quoted span for names, addresses, numbers, and dates; the value is never accepted as its own citation. | MUST | P-016 (a) (D-037, D-039) | @ai-engineer-assistant | test | Not built |
| FR-013 | A value below the confidence line (0.75) is dropped and left for a person, never guessed. | MUST | D-010; arch §2.4.2 | @ai-engineer-assistant | test | Partial — met on typed files; on a scan the OCR score replaces the model's number (T-027 H2) |
| FR-014 | On a scan, the gate uses the **lower** of the model confidence and the OCR confidence of the cited words. | MUST | P-016 (b) (D-039) | @ai-engineer-assistant | test | Not built |
| FR-015 | Numbers are normalized before comparing: `220k` = `220000`, `$1.2M` = `1200000`, commas do not make a new number, `sq ft` = `sf`. | MUST | D-015 item 1; arch §2.4.2 | @ai-engineer-assistant | test | Built |
| FR-016 | The prompt, model, temperature, and OCR settings are versioned so a result is reproducible and any change makes a new version. | MUST | D-017 (change rule); D-022 item 1 (key); D-023 item 4 (temperature 0); arch §2.4.3 | @ai-engineer-assistant | test | Built — prompt version is the first 12 chars of its sha256; temperature 0 |

### A.4 Validation gates and conflicts (steps 2–3)

| ID | Requirement | Priority | Source | Owner | Verification | State |
|---|---|---|---|---|---|---|
| FR-017 | When two documents disagree on a field, both values and their sources are stored as a conflict; no side is silently picked. | MUST | D-006 item 3; D-007; arch §2.4.2, §5.3.1 | @ai-engineer-assistant | test | Built — but conflict rows have no ids and are not joined to observations (gap G29) |
| FR-018 | A conflict is resolved only by a later document or a producer reply that names the winner, and both original values stay on the row. | MUST | D-007; arch §2.4.2 | @ai-engineer-assistant | test | Built |
| FR-019 | A "no known loss" letter never counts as a clean loss history or as zero claims; a carrier loss run wins over a no-known-loss letter. | MUST | D-014 item 1; `appetite-guide` knock-out 3; arch §2.4.2 | @ai-engineer-assistant | test | Built (rule) |
| FR-020 | A premises value with no five-digit ZIP is dropped and the page is listed for a person; a ZIP not in the Texas table, or a city that does not match the ZIP, is flagged "address invalid" without rewriting the text. | MUST | D-018 (P-001); D-020 item 2 (P-002); arch §2.4.2 | @ai-engineer-assistant | test | Built |
| FR-021 | The gate confirms `class_code` only by a human; the model may write only `class_code_suggested`. | MUST | `data-model.md:39`; `arch §5.3.1` (gap G29) | @ai-engineer-assistant | test | Not built — `class_code` is not one of the nine extracted fields (gap G29) |

### A.5 Completeness and missing-info drafts (step 3)

| ID | Requirement | Priority | Source | Owner | Verification | State |
|---|---|---|---|---|---|---|
| FR-022 | The system lists the required fields that are missing or in conflict, per `required-fields.md`. | MUST | D-004 step 3; `required-fields`; arch §2.7 | **No single owner recorded** — @pm to record (`arch §10` Q1); @ai-engineer-assistant edits | test | Partial — met for the nine extracted fields; the wider list (`class_code`, `protection_class`, `unit_count`, `subsidized`, `student_housing`, and more) is not extracted (gap G29) |
| FR-023 | A file with a missing required field is `incomplete`: the system does not quote and does not decline it. | MUST | `required-fields`; D-004; arch §2.4.2 | **No single owner recorded** — @pm to record (Q1) | test | Built |
| FR-024 | A missing-info request is a draft that names the submission, lists the missing/disagreeing fields in plain words, and states "Nothing has been declined. Nothing has been bound." | MUST | D-005; D-006 item 2; arch §2.7 | **No single owner recorded** — @pm to record (Q1) | test | Partial — the restaurant questions are triggered by cue words including the insured's name (P-015 option T2, approved not built) |
| FR-025 | No missing-info request is sent until a person approves it: the simulated @account-manager (agency rules + a written reason) or the user (override). No AI role approves. | MUST | D-017 item 3; arch §2.7, §3.3 | @ai-engineer-assistant (code); @account-manager/@user (authority) | test, review | Partial — the actor is a caller-supplied string; as coded the account-manager can approve no request the code builds (`arch §10` Q9) |
| FR-026 | An `extraction_failed` or `all_values_rejected` file gets no missing-info request, and any older draft in `pending-approval` is removed. | MUST | D-021 item 1; D-024; P-010 option D1 (D-029); arch §2.7, §4.2 | @ai-engineer-assistant (T-070) | test | Not built — gap G21 |

### A.6 Cache and token log (support for step 2)

| ID | Requirement | Priority | Source | Owner | Verification | State |
|---|---|---|---|---|---|---|
| FR-027 | A successful model reply is saved under a key built from the file contents (hashes), prompt version, OCR settings, model, host, and temperature; a matching key is reused with no model call. | MUST | D-022 item 1; P-014 (D-033); arch §2.4.3 | @ai-engineer-assistant (T-063, T-074, T-078) | test | Built — key includes host and temperature |
| FR-028 | A failed or empty call is never cached and is called again on the next run. | MUST | D-022 item 3; arch §2.4.3, §4.2 | @ai-engineer-assistant | test | Built |
| FR-029 | A reply whose values are all rejected is kept in the cache (reproducible) but is never sendable. | MUST | D-024; P-010 option C1 (D-029); arch §2.4.3 | @ai-engineer-assistant | test | Partial — the `all_values_rejected` status does not exist in code yet (T-070) |
| FR-030 | Every model call, failed attempt (429, timeout, other, `reply_not_usable`), retry, and cache hit is written to an append-only token log. | MUST | D-022 item 5; D-026 item 4; P-012 (D-026); D-028; arch §2.4.3 | @ai-engineer-assistant | test | Built |
| FR-031 | Log rows and saved replies carry the run id, host, and cache key; writes are atomic and a killed run is recoverable. | MUST | P-013 (D-027); P-014 (D-033); D-028; arch §2.4.3 | @ai-engineer-assistant | test | Built |
| FR-032 | The saved replies and the token log are kept out of git (they hold document text and call history). | MUST | D-030 item 1; P-014 option G1 (D-033); arch §2.4.3, §6.2 | @ai-engineer-assistant | measured | Built |
| FR-033 | A saved reply can be tied to the submission and the file hash it came from. | SHOULD | P-010 option G2 (D-029); arch §5.3.1 | @data-engineer (T-069) | test | Not built — T-069, TODO |

### A.7 Risk score and reason codes (step 4)

| ID | Requirement | Priority | Source | Owner | Verification | State |
|---|---|---|---|---|---|---|
| FR-034 | The system computes a hazard score with reason codes from the submitted facts; the score is a recommendation and never a decline, bind, price, or carrier choice. | MUST | D-004; `validation-standards` addendum; arch §2.5 | @data-scientist (T-017); @software-engineer on the wiring | test | Partial — computed as a recommendation; P-015 approved, not built |
| FR-035 | Loss-history points are removed and the page shows "Loss history: not scored" (claim extraction is deferred to the backlog). | MUST | D-031 item 5; P-015 option H1 (D-040); arch §2.5 | @data-scientist; @software-engineer | test | Not built — `LOSS_HISTORY` can never fire today (`team/DEMO-BLOCKERS.md` line 5) |
| FR-036 | A failed or incomplete file shows "Not scored" with the reason, not "Score: 0 · none". | MUST | D-031 item 5; P-015 option S3 (D-040); arch §2.5 | @data-scientist; @software-engineer | test | Not built |
| FR-037 | Cooking points come only from stated hazards (fryer, open flame, hood/suppression), never from a business name or a cuisine word. | MUST | D-033 item 3; P-015 option T2 (D-040); arch §2.5 | @data-scientist | test | Not built |
| FR-038 | Each decision row saves the points, reason codes, and points version, and an underwriter can mark a code wrong with a logged reason. | MUST | D-031 item 5; P-015 options V3/W1 (D-040); arch §2.5, §2.9 | @software-engineer | test | Not built |

### A.8 Appetite and carrier match (step 5)

| ID | Requirement | Priority | Source | Owner | Verification | State |
|---|---|---|---|---|---|---|
| FR-039 | Appetite is applied from the written guide (target, restricted, prohibited, and the knock-out rules); the system may recommend in-appetite / refer / out-of-appetite but never quotes, declines, or binds on its own. | MUST | D-004; `appetite-guide`; `validation-standards` | @head-of-underwriting (rules) | review | Not built — the guide's target/restricted/prohibited and knock-out rules are not applied in code; the only appetite test today is `route()` against `carrier-appetite.md` (`workbench.py:38-52`, `package.py:48`). The auto-quote band in `authority-matrix.md` is withdrawn by D-004 and is not a requirement. |
| FR-040 | The carrier match recommends one of Carrier A, B, C, or "no match" from the shared guide; the underwriter chooses the carrier, and the system never sends or declines the producer on a match. | MUST | D-006 item 1; T-018; `carrier-match`; arch §2.6 | @head-of-underwriting (rules) | test, review | Partial — `route()` contradicts the guide: no caps, no whole-word match, missing no-match classes (`team/DEMO-BLOCKERS.md` line 4) |
| FR-041 | The match uses whole-word class lists and every cap as a number, enforced in `route()`, and the send gate's in-appetite check uses the same function. | MUST | D-033 item 4; T-082, T-083; arch §2.6 | @head-of-underwriting (T-082), @software-engineer (T-083) | test | Not built |
| FR-042 | A decline reason comes only from the prohibited list or the knock-out rules; the system must not invent a reason that is not on that list, and a human sends the notice. | MUST | `appetite-guide`; `authority-matrix` | @head-of-underwriting | test, review | Not built — no reason-from-list gate in code |
| FR-043 | Carriers are placeholders A/B/C until the real panel is confirmed. | MUST | D-004; protocol; arch §1, §6.1 | @head-of-underwriting | review | Built (placeholders) |

### A.9 Underwriter workbench (step 6)

| ID | Requirement | Priority | Source | Owner | Verification | State |
|---|---|---|---|---|---|---|
| FR-044 | A web page lists the queue and, per submission, shows the fields, the citations, the conflicts, the missing items, the score with reason codes, and the carrier match. | MUST | D-009; `workbench-ux`; arch §2.8 | @software-engineer (T-019) | test | Partial — built, with the defects below |
| FR-045 | The card shows the exact text a value was cited from, for PDF, xlsx, png, jpg, and csv; one unreadable file does not stop the queue loading. | MUST | D-038 item 2 (line 3b stays); T-081; arch §2.8 | @software-engineer | test | Not built — the card slices the raw file and one unreadable file stops the queue (`arch §2.8`; `team/DEMO-BLOCKERS.md` line 3b, T-081) |
| FR-046 | At approve, the workbench lists every value that needs review and the underwriter acknowledges them; the acknowledgment is logged. | MUST | D-039 (P-016 acknowledgment); arch §2.8, §4.2 | @software-engineer | test | Not built |
| FR-047 | An underwriter edit stores the corrected value, and the package uses it. | MUST | D-038 item 3 (B-139); arch §2.8, §2.9 | @software-engineer | test | Not built |
| FR-048 | The decision is always a person's — approve, edit, or decline — and an approve requires no reason while edit and decline do. | MUST | D-004; arch §2.8, §2.9 | @software-engineer | test, review | Built |

### A.10 Decision log (steps 6 and 8)

| ID | Requirement | Priority | Source | Owner | Verification | State |
|---|---|---|---|---|---|---|
| FR-049 | Every decision appends a row holding the submission, the action, the underwriter id, the reason, the date, and the AI/rules version. | MUST | D-014 item 3; arch §2.9 | **No single owner recorded** — @pm to record (`arch §10` Q2); @software-engineer + @ml-engineer list it | test | Built in code — the log file does not exist on disk (gap G9) |
| FR-050 | The log accepts only real underwriter ids tied to the user's session; a missing or non-session id is refused. | MUST | D-038 item 3 (B-138); arch §2.8, §2.9 | @software-engineer | test | Not built — the mechanism is undefined (`arch §10` Q5) |
| FR-051 | A file is sendable only if its latest logged decision is approve; an approve after a decline requires a reason; full history stays in the log. | MUST | D-033 item 2; D-038 item 1; arch §2.9, §4.2 | @software-engineer (T-079) | test | Not built |
| FR-052 | Each row is stamped with the model, prompt version, and cache key of the extraction that was shown, and with the points/rules version. | MUST | T-021 rejections (B-140, B-142); arch §2.9 | @software-engineer | test | Not built — `ai_version` is the shell value at click time |
| FR-053 | The feedback counts are the roadmap metric per submission: decided, zero field edits, declined, with failed/all-rejected files reported apart. | MUST | D-014 item 3; roadmap; `arch §2.9`; T-021 | @ml-engineer (T-021) | test | Partial — counts rows, not the metric (T-021 rejections) |
| FR-054 | The decision log is not a training set and submissions are not used for training or evaluation until a separate permitted-use decision exists. | MUST | `arch §3.2`; `agency-register` A-07; T-021 review | @compliance | review | Built (rule) |

### A.11 Package and send (step 7)

| ID | Requirement | Priority | Source | Owner | Verification | State |
|---|---|---|---|---|---|---|
| FR-055 | A carrier package is built from the saved, reviewed file, with citations and the named carrier, and is refused when a required field is empty. | MUST | D-033 item 4; T-085; arch §2.10 | @software-engineer | test | Open — @compliance T-020 veto (misrepresentation to a carrier, `arch §8.2`); not built (`team/DEMO-BLOCKERS.md` line 6) |
| FR-056 | The send reads the decision log itself and refuses unless the latest decision is approve, for every actor. | MUST | D-033 item 2; D-038 item 1; T-079; arch §2.10 | @software-engineer | test | Open — @compliance T-020 veto; not built (`team/DEMO-BLOCKERS.md` line 2) |
| FR-057 | The send loads the saved extraction status itself (no caller-supplied report), refuses when nothing is saved, when the file's current hash differs from the saved hash, or when the status is `extraction_failed` or `all_values_rejected`. | MUST | D-021; D-024; P-010 option G2 + hash check (D-029); T-071; arch §2.10 | @software-engineer | test | Open — @compliance T-020 veto; not built (`team/DEMO-BLOCKERS.md` line 1) |
| FR-058 | A user send carries the user's exact line `send to carrier SUB-###`, matched to the submission id and logged. | MUST | D-035; T-086; arch §2.10, §3.3 | @software-engineer | test | Open — @compliance T-020 veto; not built (`team/DEMO-BLOCKERS.md` line 7) |
| FR-059 | Only the simulated @account-manager (agency rules + a written reason) or the user (override) may send or approve; no AI role may, and every send writes a record that cannot be silently repeated. | MUST | D-017 item 3; D-035; arch §2.10 | @software-engineer (code); @account-manager/@user (authority) | test, review | Open — @compliance T-020 veto; a name check only; a second send overwrites; no send record (gap G10) |
| FR-060 | The package carries the two fixed sentences "Nothing has been declined" and "Nothing has been bound". | MUST | arch §2.10 | @software-engineer | test | Built |

### A.12 Quote tracking (step 7)

| ID | Requirement | Priority | Source | Owner | Verification | State |
|---|---|---|---|---|---|---|
| FR-061 | A status per submission and carrier is derived from the carrier replies, with each subjectivity open or closed. | MUST | D-035; T-087; arch §2.11 | @software-engineer | test | Not built (`team/DEMO-BLOCKERS.md` line 8) |
| FR-062 | Carrier replies are read and matched to a submission; a reply never itself declines or binds. | MUST | D-004; arch §2.11 | @software-engineer | test | Not built — no code reads `from-carrier` |

### A.13 Feedback loop (step 8)

| ID | Requirement | Priority | Source | Owner | Verification | State |
|---|---|---|---|---|---|---|
| FR-063 | Underwriter decisions and edit reasons are captured so corrections can be counted (see FR-053). | MUST | D-014 item 3; T-021; roadmap | @ml-engineer | test | Partial |
| FR-064 | A correction records the field, the AI value, and the new value. | MUST | T-021 selection (B-139?); arch §2.9; T-019 | @software-engineer | test | Not built — an edit stores a reason only |

### A.14 Eval harness

| ID | Requirement | Priority | Source | Owner | Verification | State |
|---|---|---|---|---|---|---|
| FR-065 | The harness scores extraction against a gold set with the frozen marks (hit, miss, not credited, flagged, call_failed); a failed call is counted apart, and a null is never a hit. | MUST | D-021 item 1; D-010; arch §2.12 | **No single owner recorded** — @pm to record (`arch §10` Q3); @ai-engineer-assistant edits scorers | eval | Built — `all_values_rejected` is not yet scored as misses (D-024, T-070) |
| FR-066 | A reply whose values are all rejected is scored with its fields as misses, not as a failed call. | MUST | D-024; P-010 option S1 (D-029); T-070 | @ai-engineer-assistant | eval | Not built |
| FR-067 | Published hold-out scores are never rewritten, and a scorer is not edited after its gold set exists. | MUST | D-020; D-025; arch §2.12 | @model-risk (hold-out runs); @ai-engineer-assistant (scorer edits) | review, measured | Partial — "frozen" is a rule, not a mechanism; P-011 (T-072) not built |
| FR-068 | Every score run commits the code first and records the commit hash and the literal `call` status in the score file and memo; "Call: ok" is never printed when no call was made. | MUST | D-034; P-017 (D-039); arch §2.12 | @ai-engineer-assistant; orchestrator commits | test | Not built — T-088 proposal approved, built with T-072 |
| FR-069 | After each approved change the quick set of 15 runs; the full 60 only at milestones; a new hold-out is 20 submissions, gold first, scored once. | MUST | D-020 item 9; D-022 item 4; arch §2.12 | @ai-engineer-assistant; @model-risk (hold-out) | eval | Partial — the runner exists; no 20-file hold-out has been scored and the quick-15 baseline file does not exist (T-064) |

### A.15 Human-in-the-loop and authority (cross-cutting)

| ID | Requirement | Priority | Source | Owner | Verification | State |
|---|---|---|---|---|---|---|
| FR-070 | No component auto-declines or auto-binds; the underwriter makes every final decision. | MUST | D-004; arch §4.2 | @head-of-underwriting | review | Built (rule) |
| FR-071 | The authority matrix is reflected in the app: an incomplete file cannot quote; a referral cites the rule that fired and the source document; a senior referral is stored on the file. | MUST | `authority-matrix` (as constrained by D-004); T-018; arch §2.8 | @head-of-underwriting; @software-engineer | test | Not built — the authority matrix is referenced by no code (gap G8) |
| FR-072 | Any change to extraction, prompts, OCR, models, or scorers is built only after the user types `approve change P-###`, and proposals are numbered `P-###` and never reused. | MUST | D-017; protocol | @user (approver); any builder | review | Built (process) |

---

## B. Non-functional requirements

### B.1 Performance and latency

| ID | Requirement | Priority | Source | Owner | Verification | State |
|---|---|---|---|---|---|---|
| NFR-001 | A target time per submission (touch time from workbench open to decision) is set and met. | MUST | T-095; roadmap success metrics; arch §9 | @ml-engineer (T-095); the number is @user's | test (planned) | Not decided — no target number exists; **ASSUMED** TBD by @ml-engineer/@user |
| NFR-002 | A latency budget per stage is set and met. | MUST | T-095 | @ml-engineer | test (planned) | Not decided — **ASSUMED** TBD |
| NFR-003 | One model call per submission; files are packed whole and a file that does not fit is listed for a person, not silently cut. | MUST | arch §2.4.1; P-016 (c) option L1 (D-039) | @ai-engineer-assistant | test | Partial — text is cut silently at 120,000 characters today (`arch §3.1`, gap G15) |
| NFR-004 | OCR and model retries respect the host limits and never exceed the configured wait. | MUST | D-021; D-022; arch §2.4.1 | @ai-engineer-assistant | test | Built — at most 6 posts; `LLM_MAX_WAIT` 60 s default; one request waits at most 120 s (code constants) |

### B.2 Scalability and throughput

| ID | Requirement | Priority | Source | Owner | Verification | State |
|---|---|---|---|---|---|---|
| NFR-005 | The design is sized for **ASSUMED** 300 / 1,000 / 3,000 submissions per month and a peak hour, with a stated capacity plan. | MUST | T-095; arch §9 | @ml-engineer; @actuary on cost | test (planned) | Not decided — the volumes are **ASSUMED**; TBD by @ml-engineer |
| NFR-006 | The model call runs off the request path, behind a queue and workers. | MUST | T-095 | @ml-engineer | test | Not built — the system is scripts run by hand; starting the workbench makes model calls (gap G3) |
| NFR-007 | The extraction cache reduces token use by reusing saved replies; the cache has an expiry, a size limit, and a lock for more than one worker. | SHOULD | D-022; arch §2.4.3 | @ai-engineer-assistant | test | Partial — no expiry, no size limit, no lock (gap G20) |

### B.3 Reliability and availability

| ID | Requirement | Priority | Source | Owner | Verification | State |
|---|---|---|---|---|---|---|
| NFR-008 | A target availability for the workbench and pipeline is set and met. | MUST | T-095 | @ml-engineer | test (planned) | Not decided — **ASSUMED** TBD |
| NFR-009 | A failure-modes table covers LLM 429/timeout/bad reply, OCR failure, unreadable/partial files, duplicate submissions, crash mid-write, stale cache, and provider outage; for each it states detection, retry/backoff, idempotency, what the underwriter sees, and whether a send can ever happen. | MUST | T-095; D-021; D-022; P-013 | @ml-engineer | test | Partial — some cases are handled; others are gaps (G14, G19) |
| NFR-010 | Sends are idempotent / exactly-once: a second send for a submission does not overwrite the first and both are recorded. | MUST | T-095; arch §6.1, §6.2 | @software-engineer; @ml-engineer | test | Not built — a second send overwrites (gap G10) |
| NFR-011 | A failed model call is a distinct first-class state that never becomes "no data". | MUST | D-021; D-024; arch §4.2 | @ai-engineer-assistant | test | Partial — `extraction_failed` built; `all_values_rejected` not |

### B.4 Accuracy and quality floor

| ID | Requirement | Priority | Source | Owner | Verification | State |
|---|---|---|---|---|---|---|
| NFR-012 | Extraction accuracy is 9/10 or better on every scored field before pilot. | MUST | D-013 item 3 (@user) | @ai-engineer-assistant; @model-risk reports | eval | Not met — official baseline SUB-077–086 is 71 cell-hits across the ten scored row types (9+5+8+8+8+9+7+6+6+5, a ten-row total), label "8 of 9 fields scored; loss runs = date only" (`MEASURED`, `SUB-077-086-holdout.md`); premises 5/10, year built 7/10, status 5/10 |
| NFR-013 | The official demo score is a single 20-file hold-out (SUB-087–106): gold first, no code change after the gold exists, scored once, with the label "9 of 9 extracted fields scored; claims not read; loss runs = date only". | MUST | D-020 item 9; D-037 (d); D-038 item 4; D-039 | @producer (T-091), @senior-underwriter (T-092), @model-risk (T-093) | eval | Not built — BLOCKED until P-016 is built and frozen |
| NFR-014 | Every quoted score carries its label and, after P-017, the commit hash; no number is quoted without its source file. | MUST | D-033 item 5; D-036; D-038 item 4; D-034 | @pm; every quoting role | review | Partial — the label is not printed in any score file; it is added by whoever quotes (`arch §2.12`) |
| NFR-015 | An accuracy floor for the score, the carrier match, and the request text is set before pilot. | MUST | arch §9, §2.12; T-095 | @user | review | Not decided — **ASSUMED** TBD by @user |
| NFR-016 | A confidence-versus-hit table supports the confidence line, in place of the fixed 0.75 code constant. | SHOULD | T-027 condition (b); arch §2.4.2, §2.12 | @ai-engineer-assistant; @model-risk | eval | Not built |

### B.5 Security

| ID | Requirement | Priority | Source | Owner | Verification | State |
|---|---|---|---|---|---|---|
| NFR-017 | LLM settings come only from the shell (`LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`); no key is written to or read from a file, and no key is printed or logged. | MUST | D-011; D-012; P-008 (D-023); arch §3.1 | @ai-engineer-assistant | test | Built |
| NFR-018 | The pipeline refuses a host other than the allowed free/local host unless `ALLOW_PROVIDER` names that host exactly; a run that makes no model call is not refused. | MUST | P-008 and the two D-023 amendments | @ai-engineer-assistant | test | Built |
| NFR-019 | The provider guard refuses an `http://` (unencrypted) host that is not this machine. | MUST | arch §3.1 (gap G24) | @user (P-###); @ml-engineer (deployment) | test | Not built — the guard compares the host name only |
| NFR-020 | Login, roles, and permissions aligned to the authority matrix exist, and a real underwriter id is tied to a session. | MUST | D-038 item 3; arch §2.8, §3.3 (gap G8) | @software-engineer | test | Not built — the mechanism is undefined (`arch §10` Q5) |
| NFR-021 | The app runs under an application server with a health check, not a stdlib single-render page. | SHOULD | T-095; arch §2.8 (gaps G3, G4) | @ml-engineer; @software-engineer | test | Not built |

### B.6 Privacy and PII

| ID | Requirement | Priority | Source | Owner | Verification | State |
|---|---|---|---|---|---|---|
| NFR-022 | Only synthetic data is used in this build; no live applicant records are read, sent, cached, or stored. | MUST | protocol; D-004; arch §3.2; `data-use-review` S-01, S-02 | @compliance | measured | Built as a team rule — no code enforces it (gap G25) |
| NFR-023 | Every stored record that could hold applicant facts carries a synthetic flag, and a real document cannot be processed silently. | MUST | arch §3.2 (gap G25) | @data-engineer | test, measured | Not built |
| NFR-024 | The data that leaves in a model call is limited to what is needed; names and contact details are masked where practical. | SHOULD | arch §3.1; `agency-register` A-07; `data-use-review` (the LLM may see S-01 and S-02 only; no training use) | @user; @compliance; @responsible-ai | test, review | Not built — the whole text of every readable file is sent today |
| NFR-025 | A retention period and a deletion rule exist per store; the 7-year figure is a working assumption until counsel confirms it. | MUST | `agency-register` C-09; arch §3.2 | @compliance (period); @data-engineer (rule) | review | Not decided — 7 years **ASSUMED** ("[NEEDS LEGAL CONFIRMATION]") |
| NFR-026 | Access to each store is controlled (who may read the extraction and conflict files, the cache, the log, and the rendered page). | MUST | arch §3.2 | @data-engineer; @software-engineer; @ml-engineer | test | Not built — access is whoever can read the disk or the repo |
| NFR-027 | Protected-class attributes are not collected for underwriting and are not inferred from names; a fairness test (NFR-037) uses region, occupancy, and a name swap only, never a protected-class column. | MUST | `data-model.md:45`; `fairness-test-plan`; `data-use-review`; arch §3.2 | @responsible-ai (asks); @data-engineer (builds) | review | Partial — the no-collection rule is in `data-model.md:45` (rule only); the separate access-controlled extract does not exist and NFR-037 has not run |

### B.7 Regulatory and compliance

| ID | Requirement | Priority | Source | Owner | Verification | State |
|---|---|---|---|---|---|---|
| NFR-028 | The system prepares a submission and never binds, never declines for a carrier, and never sends an applicant-facing adverse-action notice. | MUST | D-004; `agency-register` A-01, A-08; @compliance veto | @compliance | review | Built |
| NFR-029 | A carrier package is built only after the underwriter approves step 6, and extracted fields keep their citations (A-02, misrepresentation to a carrier). | MUST | `agency-register` A-02; D-033 item 4 | @software-engineer; @compliance | review | Open — @compliance T-020 veto (misrepresentation to a carrier, `arch §8.2`); the package is free text today, not from the reviewed file |
| NFR-030 | An audit trail (input, model/version, human decision) is kept for AI recommendations (A-03). | MUST | `agency-register` A-03 | @software-engineer; @compliance | review | Partial — see FR-049, FR-052 |
| NFR-031 | Recommendations use only permitted factors (class, construction, losses, size, Texas location) and never race, religion, or a name as a feature (A-06). | MUST | `agency-register` A-06; `data-use-review` (no S-08 source); D-033 item 3 | @responsible-ai; @data-scientist | review, test | Partial — the cooking rule keys on cuisine words and can read the insured's name (P-015 T2, not built) |
| NFR-032 | No credit pull, no protection-class / consumer-report vendor, and no S-08 source (credit, criminal history, social-media, vendor business-health scores, web scrape) is used (A-05; S-05, S-08). | MUST | `agency-register` A-05; `data-use-review` S-05, S-08; D-004 | @compliance | review | Built (rule) |
| NFR-033 | No rate is made; any quote uses only the filed rate with no schedule credit or debit (A-04). | MUST | D-004; `agency-register` A-04 | @head-of-underwriting | review | Built (rule — no rating engine exists) |
| NFR-034 | Every item flagged `[NEEDS LEGAL CONFIRMATION]` in the agency register is resolved with counsel before any real file is used. | MUST | `agency-register` A-01, A-03, A-07, A-08 | @compliance; @user | review | Open |
| NFR-035 | The agency register (A-01 to A-08) is current for an agency (not a writing company); the separate draft `regulatory-register.md` (C-01 to C-12) is not accepted and still carries open `[NEEDS LEGAL CONFIRMATION]` rows. | MUST | T-022; `agency-register` | @compliance | review | Partial — `agency-register.md` accepted (T-022); the draft `regulatory-register.md` is not |

### B.8 Fairness

| ID | Requirement | Priority | Source | Owner | Verification | State |
|---|---|---|---|---|---|---|
| NFR-036 | No output that can change who is quoted or declined is used in production without a fairness and contestability review; @responsible-ai can veto. | MUST | `validation-standards`; arch §8.2 | @responsible-ai | review | Open — fairness and contestability veto on T-017 |
| NFR-037 | The fairness test plan is run and passed before pilot. | MUST | T-009; D-030 (T-067); `fairness-test-plan`; arch §8.2 | @responsible-ai; @data-scientist | eval | Not met |
| NFR-038 | A business name or a cuisine word must never change a file's outcome. | MUST | D-033 item 3; P-015 option T2 (D-040) | @data-scientist; @ai-engineer-assistant | test | Not built |
| NFR-056 | A proxy review of the score, the carrier match, and the request text is completed before pilot; a proxy found is removed or the reviewer vetoes. | MUST | RISKS R-002; T-009; D-023 item 5 | @responsible-ai | review | Not done — `deliverables/responsible-ai/proxy-review.md` does not exist |
| NFR-057 | A name-swap counterfactual test (D-023 item 5, T-067) runs before pilot; the risk score and the carrier match must not change when the insured name is swapped, including a name that holds a trigger word. | MUST | D-023 item 5; T-067; B-065 | @responsible-ai; @data-scientist | eval | Not done — T-067 awaits a build turn |

### B.9 Auditability and explainability

| ID | Requirement | Priority | Source | Owner | Verification | State |
|---|---|---|---|---|---|---|
| NFR-039 | Every value is explainable: it carries its source document and the quote it was taken from. | MUST | D-010; `validation-standards` Tier 2 | @ai-engineer-assistant | test | Partial — citations do not prove the value (gap G17) |
| NFR-040 | Every recommendation shows the reason codes and the rule that fired, which a reviewer can check. | MUST | `validation-standards`; `authority-matrix` | @data-scientist; @software-engineer | test | Partial |
| NFR-041 | The decision record is complete enough to reconstruct what the AI showed and what the human did. | MUST | T-021 rejections; arch §2.9 | @software-engineer | test | Not built |
| NFR-042 | No component is used in production while a High finding is open; @model-risk's written approval is required for any model. | MUST | `validation-standards`; arch §8.2 | @model-risk | review | Open — 6 vetoes on 5 tasks (`arch §8.2`) |

### B.10 Human-in-the-loop safety

| ID | Requirement | Priority | Source | Owner | Verification | State |
|---|---|---|---|---|---|---|
| NFR-043 | There is no auto-decline and no auto-bind, ever. | MUST | D-004; arch §4.2 | @head-of-underwriting | review | Built (rule) |
| NFR-044 | An `extraction_failed` or `all_values_rejected` file can never be approved or sent, by any actor. | MUST | D-021; D-024; D-029; arch §8.1 line 1 | @software-engineer; @ai-engineer-assistant | test | Not built |
| NFR-045 | A person must resolve unread pages, open conflicts, and needs-review values before a file can become ready. | MUST | D-017 item 3; D-039; arch §4.2 | @software-engineer; @senior-underwriter | test, manual-UW | Partial |
| NFR-046 | Every needs-review value is acknowledged by the underwriter at approve, and the acknowledgment is logged. | MUST | D-039; arch §4.2 | @software-engineer | test | Not built |

### B.11 Data, provenance, and the model

| ID | Requirement | Priority | Source | Owner | Verification | State |
|---|---|---|---|---|---|---|
| NFR-047 | Provenance beats prompting: structured document data outranks AI-extracted fields on critical values. | SHOULD | README design principle; arch §2.4.2 | @ai-engineer-assistant | test | Partial |
| NFR-048 | Extraction lands in a structured observation model, not a free-text blob, with each observation holding field, value, source, page, span, confidence, and model version. | MUST | `data-model.md`; arch §5.3.1 | @data-engineer | test | Partial — no `observation_id`, page, or model version; the model is behind the code (gap G29) |
| NFR-049 | The data model and data inventory are kept current with the code and the decisions. | MUST | arch §5.3.1, §6.2 (gap G29, note 4) | @data-engineer | review | Not built |

### B.12 Maintainability

| ID | Requirement | Priority | Source | Owner | Verification | State |
|---|---|---|---|---|---|---|
| NFR-050 | A README explains how to run `underwriting_pipeline/` locally. | MUST | arch §8.4 (gap G12) | @software-engineer | review | Not built |
| NFR-051 | The self-checks under `underwriting_pipeline/` run in CI, not only by hand. | MUST | arch §8.4 (gap G11) | @ml-engineer; @software-engineer | test | Not built |
| NFR-052 | Statuses and enums have one shared definition, not strings spelled in each file. | SHOULD | arch §5.2 | @data-engineer; @software-engineer | review | Not built |
| NFR-053 | The contracts between components (C1–C15) are fixed and validated against a schema. | SHOULD | arch §5.1, §5.3.1; `api-spec`; `workbench-ux` | @data-engineer; @software-engineer | test | Not built — nothing validates the shapes |

### B.13 Cost

| ID | Requirement | Priority | Source | Owner | Verification | State |
|---|---|---|---|---|---|---|
| NFR-054 | No paid API is used; the model host is free-tier or local; any cost estimate uses public enterprise list prices and is labeled as an estimate. | MUST | D-011; D-012; D-038 item 5 | @user; @actuary | review | Built (free-tier/local host; no paid API) |
| NFR-055 | A cost model per submission (tokens measured from the token log) is set at **ASSUMED** 300 / 1,000 / 3,000 submissions per month. | MUST | T-095; D-038 item 5 | @actuary; @ml-engineer | measured, assumed | Not decided — the volumes and the target are **ASSUMED**; tokens are measurable from the token log today |

### B.14 Pilot success metrics and go/no-go

| ID | Requirement | Priority | Source | Owner | Verification | State |
|---|---|---|---|---|---|---|
| NFR-058 | Carrier first-pass acceptance is defined and measured: the share of packages a placeholder carrier would accept on the rules we wrote (the real hit rate waits on the real panel). | MUST | roadmap success metrics (`roadmap.md:29`); D-004 | @head-of-underwriting | measured | Not decided — **ASSUMED** no target number; the carrier panel is placeholder (FR-043) |
| NFR-059 | Quote turnaround is defined and measured: intake to carrier package ready for the underwriter to release. | MUST | roadmap success metrics (`roadmap.md:30`); D-004 | @head-of-underwriting | measured | Not decided — **ASSUMED** no target number |
| NFR-060 | A target for "auto-prepared with no corrections" (the share of submissions where the underwriter changes no extracted field) is set, beyond the FR-053 count. | MUST | roadmap success metrics (`roadmap.md:28`); D-004 | @head-of-underwriting | measured | Not decided — **ASSUMED** no target number |
| NFR-061 | A pilot go/no-go gate is defined: the evidence required before the pilot starts and who declares it. | MUST | D-004 success metrics; protocol | @head-of-underwriting; @user | review | Not decided — no gate exists |

---

## C. Cross-reference: where each requirement comes from

- **The eight steps of D-004** map to A.1 (step 1), A.2–A.6 (step 2), A.5 (step 3), A.7 (step 4), A.8 (step 5), A.9–A.10 (step 6), A.11–A.12 (step 7), A.13 (step 8). A.14 (eval harness) and A.15 (human-in-the-loop) cut across all steps.
- **The five pillars of D-004** map to: no auto-decline/bind — FR-070, NFR-043; agency prepares, carrier writes — NFR-028, NFR-033; underwriter decides — FR-048, FR-070; placeholders A/B/C — FR-043; synthetic data — FR-003, NFR-022.
- **The open vetoes (`arch §8.2`)** are the reason NFR-036, NFR-042, NFR-044 and 2.4/H1–H3 rows are `Not built` or `Open`. The open @compliance veto on T-020 (misrepresentation to a carrier, `package.py`, `arch §8.2` items (a)–(f)) is the reason NFR-029 and FR-055–FR-059 read `Open`; D-035 moved (c) the user's exact send line and (e) quote tracking onto the demo path, so the veto can be lifted before the demo.
- **The demo blockers (`team/DEMO-BLOCKERS.md`, by line)** are: line 1 send gates (P-010) — FR-057, NFR-044; line 2 send needs an underwriter approve — FR-051, FR-056; line 3 exact citations — FR-006, FR-008, FR-012, FR-014; line 3b the workbench shows the cited text — FR-045; line 4 carrier match with caps — FR-041; line 5 score fixes (P-015) — FR-035–FR-038; line 6 package from the reviewed file — FR-055, NFR-029; line 7 the user's exact send line — FR-058; line 8 quote tracking — FR-061, FR-062; line 9 the new 20-file hold-out — NFR-013; and FR-026 (a failed or all-rejected file gets no request).

## D. Gaps this register surfaces (owners and numbers not recorded)

These are points where a requirement cannot be assigned or measured because no owner or number exists. They are not decided here.

| # | Point | For |
|---|---|---|
| D-1 | No single owner is recorded for missing-info drafts (FR-022 to FR-026), the decision log (FR-049), or the eval harness (FR-065). | @pm records (`arch §10` Q1–Q3) |
| D-2 | No target time per submission (NFR-001), no availability target (NFR-008), no accuracy floor for the score/match/request (NFR-015), no cost model (NFR-055), and no pilot success-metric or go/no-go number (NFR-058–NFR-061). | @ml-engineer (T-095), except NFR-015 which is @user's, and NFR-058–NFR-061 which are @head-of-underwriting's |
| D-3 | Real applicant data has no decision covering it: whether it may be stored (NFR-021, NFR-023), sent to a model host (NFR-019, NFR-024), or retained (NFR-025). | @compliance; @user |
| D-4 | The mechanism for a real underwriter id tied to a session is undefined (FR-050, NFR-020). | @software-engineer proposes; @user decides |
| D-5 | Whether D-017 item 3's "complete" applies to a producer request (FR-025); as coded the account-manager can approve none. | @user, as the owner of D-017 (`arch §10` Q9) |

## E. How this register is maintained

- @pm owns this file. A new requirement takes the next free id in its series (`FR-###` or `NFR-###`); ids are never reused and a superceded requirement is marked, not deleted.
- A requirement's **Source** is the authority. When a decision changes, @pm updates the State of every affected row and, if the requirement itself changed, adds a new row and marks the old one.
- A row becomes `Built` only when the code exists **and** its verification has run; a `review` requirement becomes met only when its named reviewer says so. @pm gives no verdict.
- This register does not replace `team/TASKS.md` (work), `team/DECISIONS.md` (authority), or `deliverables/architecture/architecture.md` (what exists). It is the one place that names, in one list, what the pilot is required to do.
- Nothing here is a production approval or an authorization to send.
