# AGENTS.md

Rules for any coding agent working in this repo. The full rules are in CLAUDE.md; this file carries the standing fast lane.

### Fast lane (standing approval by @user, 2026-10-23, D-129)

- **Proceed without asking:** gold fixes that make gold match the documents; new tests; docs; dev-only data; reviewer-requested UI text fixes; any change that is stricter only (sends more to a person, never less, never loosens a gate).
- **Always stop and ask @user:** anything that loosens a rule or gate; scorer changes; frozen files; hold-out runs; rule/routing/appetite decisions; merges into ai-team or main; real data; anything outside the worktrees.
- **Decisions:** collect all decisions for @user in one list per session, each with options and a recommendation.
- **Reviews:** High-only; at most one look-again per finding. If a fix fails a second time, stop and present 2–3 options instead of looping.
- **Tracks:** at most two AI tracks at once, each in its own worktree, one tool per worktree.
- Everything else in CLAUDE.md (frozen files, gold-first, run once, secret scan, never push main, decisions only typed by @user) still applies.
