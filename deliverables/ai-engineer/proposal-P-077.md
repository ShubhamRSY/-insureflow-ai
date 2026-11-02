# P-077 — A second location is detected by rules or by a model count; any doubt sends the whole file to manual intake

- Author: @ai-engineer-assistant, drafted 2026-11-02 at @user's request (D-140). **Draft for @user to read. Not approved, not built.** Development data only. Not a production approval; the T-027 veto stands.
- Source: @model-risk memo `deliverables/model-risk/T-027-memo-T-120.md`, H1 and remediation steps 1–3. Cause: SUB-475 (out of scope, a second store stated only in prose) went through as in-scope.
- Direction: **stricter only.** The change can only move a file from in-scope to manual intake, never the other way. No rule is loosened, no gate is relaxed.
- Approval: the user types `approve change P-077` (D-017). Parts A and B can be approved together or A alone (see "Decision for @user").

## Problem

`scope.py` (scope-v4) calls a file multi-location only when it sees one of these:

- two distinct premises addresses in the application;
- a numbered location label (`Loc 2`, `Bldg 2`);
- a "Second/additional location:" line at the start of a line;
- a Locations heading with two list items;
- two address rows in a schedule.

A second place stated only in words matches none of them: "two stores", square footage labelled "(Corpus)" and "(Rockport)", or a second street in the email. The model is never asked how many places it sees.

## Change

A file goes to manual intake (reason code `multiple_locations`) when **either** part A **or** part B fires. When the result is uncertain, the file also goes to manual intake.

### Part A — rules, before any model call (`underwriting_pipeline/ai/scope.py`, `VERSION` scope-v4 → scope-v5)

Each rule reads every in-scope document: application, email, attachments, resubmission letters and loss runs. The card quotes the matched words as evidence, e.g. `Manual intake: multiple locations — "two stores" (application.md)`.

1. **Count of places.** A number word, digit or quantifier next to a place noun:
   - Numbers and quantifiers: `two`–`ten`, `2`–`10`, `both`, `multiple`, `several`, `second`, `2nd`, `third`, `3rd`, `other`, `another`, `additional`, `each of our`.
   - Place nouns: `store(s)`, `shop(s)`, `location(s)`, `site(s)`, `branch(es)`, `outlet(s)`, `premises`, `restaurant(s)`, `storefront(s)`.
   - Examples that fire: "two stores", "both locations", "second shop", "other branch", "our 2 sites", "another store in Rockport".
2. **Place-labelled values.** One field gives two figures, each labelled with a different place name. Example: "Square footage: 3,000 (Corpus), 1,800 (Rockport)".
3. **A different street address in any document.** A street address that the existing `same_address` comparison (units dropped) says differs from the premises line. A town name alone does not fire, because the line has no street number.

**Not counted (near-misses that stay in scope).** Each is a dev self-check:

- Parts of one building: "two floors", "2nd floor", "second floor", "two entrances", "two buildings at one address", "Suite 200", "Unit 2".
- Other counts that are not places: "two fryers", "second shift", "both owners", "two employees".
- An address on a line labelled mailing, billing, prior, former, previous, home, residence or owner's.
- An address belonging to the agency or producer (letterhead or signature), the carrier, an insurer, a supplier, a vendor or a landlord, when its line names that role.
- A past or sold place in the same sentence ("we sold our second store in 2019", "closed the other shop"). This keeps the memo's near-pass negative. See decision 2.

### Part B — a location count reported by the model (prompt change; check in `underwriting_pipeline/ai/prepare.py`)

- **Prompt.** Add one item to the extraction JSON in `underwriting_pipeline/config/lobs/small_commercial.json` (`prompt_system`): `"location_count": {"value": <integer or null>, "quote": "<exact words>", "source": "<file name>"}`. The instruction: count distinct business premises at different addresses (not floors, suites or buildings at one address); quote the words that show it; give null if the documents do not make it clear.
- **Rule in `prepare.py`, after the call.** The whole file goes to manual intake when any of these holds:
  - `value` > 1;
  - `value` is null, missing or not an integer;
  - the quote is not found in the cited document (the existing citation check);
  - the reply has no `location_count`.

  The report becomes the existing manual-intake report: every field empty, no request, sends blocked. Its reason quotes the model's evidence, e.g. `Manual intake: multiple locations (model count 2: "two stores")`.
- A failed call stays `extraction_failed`, as today (D-021). It is never read as a count.
- **PROMPT_VERSION changes.** Today `PROMPT_VERSION` = `759b3e6bc9b2` (`sha256(SYSTEM)[:12]`). The new value is the hash of the edited `prompt_system`, recorded at build time. Effects:
  - Every extraction cache key changes, so every file is re-extracted once (quick-15 and any dev run cost a full set of model calls).
  - The pilot freeze note (C7, `deliverables/pm/pilot/freeze-note.md`) must record the new version.
  - Any `lob_config` snapshot that pins the prompt hash is updated in the same build.

## Tests and self-checks (build step, all on new dev files, never SUB-475)

- **Positives, each alone:** count phrase; place-labelled values; second street in the email; model count 2 with no rule match; model count null.
- **Negatives (stay in scope):** every near-miss listed under Part A, plus a model count of 1 citing the premises line.
- **Request equality.** Part A changes no request for a file that stays in scope. Part B changes every request by design. The build reports how many dev in-scope files move to manual intake under A and under B, file by file, before anything else runs.
- `tests/pipeline` green; `scope.py` and `prepare.py` self-checks green; an @model-risk check with no High (one look-again at most, D-129).
- **UI (D-065):** the evidence quote on the card, a "What's new" line, and a screenshot on a temp copy.

## Risks

- **False manual intake.** Part B's "null → manual" can send single-location files to manual intake when the model is unsure. The T-121 gate allows false manual ≤ 2/20. The dev count above must show this before T-121 gold is written.
- **Agency signatures.** Part A rule 3 can fire on letterheads and signatures that name no role. That is safe (stricter), but it counts toward false manual intake.
- **Cost.** Part B makes the next quick-15 and every dev run a full re-extraction.

## Decision for @user

1. Approve A and B together, or A only. **Recommendation: A and B together.** A alone would have caught SUB-475 ("two stores"). B is the net for wordings no list foresees, and the user asked for it.
2. A past or sold place ("sold our second store"): stay in scope as the memo says, or go to manual intake (stricter still). **Recommendation: stay in scope for rule A1.** Part B still counts only current premises, and a reviewer sees the sentence.
3. To approve, type `approve change P-077`, or `approve change P-077 part A only`.
