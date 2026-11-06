# P-087 — Bar and nightclub words follow one rule in both languages, by meaning (T-082 item 2)

- Author: orchestrator, drafted 2026-11-05 at @user's request (D-169 item 4). **Draft for @user to read. Not approved, not built.**
- Source: @responsible-ai T-082 lift item 2; measured in `deliverables/data-scientist/T-082-fairness-checks.md` (items 1 and 1b).
- Direction: **part A loosens one case** (Spanish bar words beside restaurant evidence move from a never-overridable no_match (R1) to a senior referral (R2), the same as English). Under D-129 that needs your approval. Part B is stricter only.
- Approval: `approve change P-087` (part A), or `approve change P-087 A+B`. Routing rules: `workbench.py` changes the frozen build, so @model-risk checks it (D-167).

## Problem (measured, synthetic, no model call)

- `cantina` and `taberna` are in `PROHIBITED` but not in `BAR_WORDS` (`workbench.py:171`, `:210`). So the bar-with-food rule (D-079, R2) never sees them:

| Text | Today | English twin today |
|---|---|---|
| "restaurante con cantina" | no_match R1, never overridable | "restaurant with bar": senior_referral R2 |
| "restaurante con taberna" | no_match R1, never overridable | "restaurant with tavern": senior_referral R2 |
| "cantina" alone | no_match R1 | "bar": no_match R1 (same) |
| "discoteca" / "antro" | no_match R1 | "nightclub": no_match R1 (same) |

- The lists hold Spanish singulars only. A plural falls to R8, an overridable no_match:
  - **"cantinas", "tabernas", "antros", "discotecas" are overridable**, where "bars" and "nightclubs" never are. That is a gate looser in Spanish.
  - "clínicas", "laboratorios", "contratistas", "cocinas", "comedores", "hornos", "multifamiliares" and "tiendas minoristas" skip the senior referral that the English plural gets.

## Change

**Part A — one rule by meaning (your words, D-169):**

1. `cantina`, `taberna` (+ `cantinas`, `tabernas`) = bar / tavern. Add them to `BAR_WORDS`. Alone: R1 no_match, as "bar" is. With restaurant evidence: R2 senior referral, "possible bar/liquor exposure — confirm liquor sales", as "restaurant with bar" is.
2. `discoteca`, `antro` (+ `discotecas`, `antros`) = nightclub. Add them to `BAR_WORDS` and `NEVER_SOFT` (P-062): R1 even beside restaurant evidence, as "nightclub" is. No outcome changes for the singulars; it makes the rule explicit.
3. `carrier-match.md` W1/W1b rows list the Spanish twins beside the English words (a @head-of-underwriting text edit, recorded with the change).

**Part B — Spanish plurals (stricter only, optional):** add the plural of every Spanish entry that has an English plural in the same list (about 25 words, listed at build from the B-197 mapping). Every move is R8 → the route the English plural gets (R1, R10, R11, R12, R14 or P-053). None is looser.

## Not changed

- Extraction, the prompt (`PROMPT_VERSION` 392b9ce3c1af), scope, scorer v11, the gold.
- No class becomes an automatic decline, and no_match is still not a decline.

## Tests (dev only, no model call)

- `t082_fairness_checks.py`:
  - Item 1: 462/462 EN↔ES pairs equal (before P-087/P-088: 404/408).
  - Item 1b: 19/19 listed plural pairs equal (part B), including `tiendas de ropa` / `clothing stores`.
  - Item 3: 77 Spanish entries, 0 mapping problems.
- Routing self-checks: "restaurante con cantina" → senior_referral R2 with the liquor note; "cantina" → R1; "restaurante con discoteca" → R1; "cantinas" → R1 (part B).
- Replay of T-128 from cache: the route changes are listed file by file (expected 0; no T-128 file uses these words).

## Decision for @user

1. `approve change P-087` (part A only), or A+B (**recommended**: B closes the looser plural gap), or defer.
