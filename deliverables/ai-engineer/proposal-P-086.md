# P-086 — Conflict citations point to the lines that state the hazard (B-530)

- Author: orchestrator, drafted 2026-11-05 at @user's request (D-168). **Draft for @user to read. Not approved, not built.**
- Source: @model-risk memo `deliverables/model-risk/T-027-memo-T-128.md` M1; backlog B-530. D-167: must close before any send-enabled mode.
- Direction: **citation only.** The same files open a cooking conflict as today; only what the conflict quotes grows. No conflict is removed and no hold is lifted.
- Approval: `underwriting_pipeline/ai/` changes, so the user types `approve change P-086` (D-017). @model-risk checks it (frozen build, D-167).

## Problem (reproduced 2026-11-05 on the frozen build, no model call)

SUB-562 `email.md` has three clauses with a cooking word:

| Clause | Word |
|---|---|
| "Subject: Mustang Island Deli - Port Aransas" | deli |
| "Port Aransas deli on Alister St selling po-boys…" | deli |
| "I left this off the application: shrimp and fries are fried every day" | fries |

`cooking_hits()` (`prepare.py:1165`) stops at the **first** cooking clause in each document (`break` at line 1207). So the conflict cites the subject line, and the frying sentence never reaches the card. The file was held correctly. But an underwriter resolving from the card sees "Deli" and no hazard, and could resolve it to "None".

## Change (`underwriting_pipeline/ai/prepare.py`, `cooking_hits()` only)

1. Per document, keep **every** clause with a cooking word, in document order, up to 3. Above 3, the quote ends "… and N more in <file>".
2. There is still one conflict side per document, so the UI check H1 rule (one hit per document) stays. The side's `quote`/`value` joins the clauses with " … ". `spans` lists each (start, end), the same shape the operations rows already use (P-048 (d)).
3. Schedule files (csv/xlsx cooking column) are unchanged.
4. **Detection is unchanged:** a document has a hit after the change exactly when it had one before. So the set of files with an open cooking conflict, every status, every route and every hold are unchanged.

## Not changed

- The prompt and `PROMPT_VERSION` `392b9ce3c1af`: the rule runs after the model call. Requests stay byte-identical (checked at build).
- The cooking words, the exempt phrases, `apply_cooking_rule()` logic, scorer v11, the lint and the gold.

## Option considered and not recommended

- **B. Also refuse a resolve to the "None" side until the underwriter ticks "I opened <file>".** This is stricter, and @model-risk named it as an alternative. It adds a UI step on every cooking conflict. Option A fixes the cause (the wrong lines), so B is only worth it if the @senior-underwriter UI check asks for it.

## Tests (dev only, no model call)

- SUB-562 text: the email side quotes "shrimp and fries are fried every day", and the subject line stays in the quote.
- SUB-560: still cites the fryer sentence.
- Every existing `cooking_hits` assert (`prepare.py:3136-3158`) passes. Add one assert: "a document with 4 cooking clauses → 3 quoted + 'and 1 more'".
- Re-run `prepare` on the cached T-128 run (no call). The only differences allowed are the cooking-conflict quotes and spans; 0 status, route, hold or field changes, listed file by file.
- Request equality: every cached request is byte-identical.
- D-065: card screenshot of SUB-562's conflict (temp copy), plus one "What's new" line.

## Decision for @user

1. `approve change P-086` (option A, recommended), or A+B, or defer.
