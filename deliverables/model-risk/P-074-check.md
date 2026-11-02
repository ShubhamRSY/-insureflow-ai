# P-074 build check (D-132) — @model-risk

Scope: branch `p074` in `insureflow-fix-t117`, uncommitted diff vs pilot-integration 3c50cd5. Read: proposal, diff of `llm_extract.py`, `prepare.py`, `workbench.py`, as-built, UI check, screenshot, dev manifest, D-131/D-132. LLM_* unset; no model call. Dev data only. **Not a production approval; the T-027 veto stands.** An approved proposal (D-132) is not a production approval.

## Re-run (by me, 2026-10-26)

| Check | Result |
|---|---|
| `llm_extract.py` self-check | `llm gate ok` |
| `prepare.py` self-check (incl. SUB-297/298 stubbed end to end, D1, D2, merge, differ, each hedge word) | `prepare ok` |
| `workbench.py` self-check | `workbench ok` |
| `pytest tests/pipeline` (incl. `test_request_equality`) | 86 passed |
| PROMPT_VERSION | `759b3e6bc9b2` (unchanged; `SYSTEM`, `request_for` not in diff) |
| Worktree after my runs | `git status` identical before/after (no stray writes) |
| Dev manifest: 9 new lines | all 9 hashes match (`shasum -c`) |
| Frozen files (eval_holdout_*, lint_holdout, hold-out gold, `simulation/inbox/`, scores, caches) | none in diff or untracked |
| D-065 | What's new line (2026-10-24, P-074, D-132), side notes on Conflicts list and resolve form, screenshot P-074.png (rendered to a temp dir), @senior-underwriter UI check: no High |

Code read: D1–D5 are all routed through one new branch (`differs and len(ordered) >= 2`) before P-038(c); a rejected-but-stated side is carried with `unverified: true` and the gate's reason; `prepare.py` skips `_typed_first` and the H3 merge when any side is unverified, so the conflict reaches `conflicts` and the field is emptied. A rejected value is never promoted to a field value (confirmed by self-check D1).

## High findings

None.

## Medium (required before merge; small, no look-again needed if each gets a self-check line)

- **M1 — `_carry_flag` can drop a non-approximate review flag (loosening).** `prepare.py:1136` returns early whenever the other side is approximate, so any other reason on that side is lost too. Probe: cur exact/clean + other `{approximate, needs_review, reason: "approximate figure…; values differ by location…"}` → cur stays `needs_review False`. Before P-074 the flag was carried. Reachable via the P-056(e) per-location note. Fix: skip only when the other side's sole reason is the approximate note; otherwise carry as before.
- **M2 — hedge not seen across a currency code or colon; B now makes these verify as exact.** Probes: "about US$1.2 million", "about USD 1.2 million" → verifies, **exact** (before P-074: rejected). Criterion "approximate amounts never verify an exact figure" is not met for these. Also "Approximately: $1,200,000" → exact (pre-existing). Fix: allow `US\$|USD|C\$|CAD` and `:` between the hedge and the amount in `_HEDGE_BEFORE` (and `AMOUNT_TOKEN`).
- **M3 — `apply_locations` (P-005) still drops premises conflicts that carry an unverified side.** `prepare.py:784–785` removes every premises conflict when labelled main/second locations exist; the proposal's reason for leaving P-005 alone ("the side is verified") does not hold for an unverified side. Not a loosening vs HEAD, but it is a path where a model conflict with an unverifiable side is dropped. Fix: keep a premises conflict that has an `unverified` side, or record it as a backlog item with the user's acceptance.
- **M4 — disclosure: B can move a file toward complete.** A field whose only quote was "$2 million" was rejected (missing → incomplete) and now verifies. Approved by D-132 (B), and the 69-file replay found 0 such flips, but the proposal/as-built line "Nothing moves toward complete" is inaccurate; correct the as-built text.

## Low (backlog, one line each)

- L1: "1.2  million" (two spaces) is rejected (`_NUM` allows one space); fails safe.
- L2: ranges ("between $1.0 and $1.2 million") now verify the upper figure as exact; not approximate.
- L3: other hedges not on the list (est., in the region of, -ish, more or less); user's word list, D-132.
- L4: unverified side note not seen in a screenshot (UI check Medium); add one card.
- L5: `_apply_reply` can resolve to an unverified side's value if the reply contains the string; acceptable (producer evidence) but log it as such.

## Verdict

**APPROVE WITH CHANGES** — merge after M1 and M2 are fixed with a self-check each and M3/M4 are either fixed or recorded (M3 as a backlog item, M4 as a one-line as-built correction). No High finding. Not a production approval; the T-027 veto stands.
