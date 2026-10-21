# Pilot UI plan — assist-only workbench

- Author: @frontend-engineer. Date: 2026-10-21. Task: T-117 follow-up (item 3).
- Plan only: no code, no build, no screenshot, no pipeline run in this task.
- Basis: `underwriting_pipeline/app/workbench.py` and `workbench.html` (read-only); `deliverables/model-risk/T-027-assist-mode-pilot.md` (C1–C8); `deliverables/pm/pilot-readiness.md`; `team/DECISIONS.md` D-065, D-096, D-105, D-112; T-117 results `deliverables/ai-engineer/evals/SUB-238-269-holdout-v11.md`.
- Not a production approval. The T-027 veto is unchanged. Synthetic data only in every screenshot and deliverable.

## 1. What the pilot needs from the UI, in one line

An underwriter must be able to see, on one page and without opening a second tool: every proposed value with its citation and confidence, the scope verdict, the route and status as labelled proposals, the missing-information list, and a plain-language reason whenever anything is blocked — and must never be able to send, draft or make a file sendable from it.

## 2. The two surfaces

| | Workbench (`underwriting_pipeline/app/`) | React app (`frontend/`) |
|---|---|---|
| What it is | One Python-rendered page (`render()` → `workbench.html`) with POST forms for decision, edit, conflict resolve, market confirm, cooking call, code mark, close subjectivity, send and draft approval | 200+ React 18 / Vite / Tailwind components: platform sign-in, queue, line workbenches, actuarial views, metrics, admin |
| Fit for the pilot | The only surface wired to the pilot pipeline: saved runs, citations, scope, route, decision log, refusals | Built around a different API and data model; does not read saved pipeline runs |
| Assist-only work needed | Labels, guards shown, always-on scope, warnings, correction and display log | A second front end plus API work before it can show the same data |
| Recommendation | **Harden this for the pilot** | **Do not use for the pilot**; treat as a separate post-pilot task |

### Why not React for the pilot

- The pilot's contract is the saved extraction run and the decision log. The workbench already renders both; React would need new API endpoints, an auth model and a re-implementation of citation/refusal semantics — none of which the pilot needs, and all of which would change `underwriting_pipeline/` during the freeze window (C7).
- The demo path (D-065) is the pipeline workbench. Porting now spends the pilot budget on parity rather than on the three conditions that are still Not met (C4 identity, C5 correction log, C6 warnings).
- Revisit React after the pilot: its existing `Pilot.jsx`, `Queue.jsx` and `UWWorkbench.jsx` are the natural starting point, but only with a decision that names the API and the auth path.

## 3. Work plan — harden the workbench

Sizes are engineer-days for @frontend-engineer, excluding the backend guards owned by @software-engineer.

### P0 — pilot gate (must land before the first real file): 3–4 days

1. **Pilot mode, visible and honest (C3, C6).** A persistent header on every card: "Assist-only pilot — AI proposals only. Nothing is routed, sent or drafted. You decide." Route and status render as `Suggestion only — not a decision` in the D-096 wording; the existing `recommendation only` line is renamed to the same phrase.
2. **Always-on scope verdict (C3).** The scope result is shown on every card, not only in a refusal: `Scope check: in pilot scope (scope-v4)` or `Scope check: manual intake — <reasons> · your decision, logged`. A scope-correction control writes a correction row (feeds B-432/G-2), never changes the file.
3. **Labels never look accepted (C6).** Every value row carries `AI proposal — verify against the source`, the existing confidence, the existing cited text, and `NEEDS REVIEW` only when it is genuinely open. `needs_review` values are never pre-ticked at approve.
4. **Weak-field warning (C6).** A standing warning on `operations` and `loss_run_valued_through`: "Measured on the last frozen run: operations 13/20, loss runs 16/20 — check each against the cited page." The numbers come from the approved frozen run only (T-117 for now); no number appears before @model-risk signs the run.
5. **Blocked actions say why (D-065 item 2).** Every disabled control has an adjacent plain-language reason, and every refusal keeps the existing `REFUSED_AS` prefix. No new acting controls.

### P1 — evidence the pilot is supposed to produce: 2–3 days

6. **Correction log UI (C5).** On edit/decline/resolve, capture field, suggested value, final value and reason (the backend already accepts `field_id`, `new_value`, `reason`). Add a read-only "Corrections" panel per submission and a `pilot-corrections.md` export for @model-risk; never write it into `deliverables/` automatically.
7. **Display log (C5).** One row per card view: user, submission, `saved_hash`, prompt version, model. The view is server-rendered, so this belongs in the GET path with the signed-in user; coordinate with @software-engineer.
8. **Failed extraction is never a value (D-021).** Keep the existing `NOT_READ` treatment and show a separate count of `extraction_failed` files; no suggestions, no missing-info list, no send controls on those cards.

### P2 — identity and finish: 1–2 days (after B-190)

9. **Sign-in (C4, B-190).** Replace the typed `underwriter_id` with the authenticated user; show the signed-in name; remove the free-text actor control. The UI work starts only when the B-190 auth path is chosen.
10. **Accessibility and laptop widths.** Keyboard order per card, labelled controls, visible focus, no horizontal scroll at 1280 px, status conveyed by text as well as colour.
11. **"What's new" and screenshots (D-065 items 4–5).** One line per UI change (date, task, decision), and Playwright screenshots of the affected workbench page into `deliverables/frontend-engineer/screenshots/`.

**Total: 6–9 engineer-days** (P0 3–4, P1 2–3, P2 1–2), plus one @senior-underwriter review pass (High only) and one Playwright capture pass.

## 4. Dependencies and blockers

| Item | Owner | Blocks |
|---|---|---|
| Pilot guards in `send_to_carrier`, `build_package`, `write_drafts` (C1, C2) | @software-engineer | P0 ship |
| B-190 sign-in + audit | @software-engineer | P2, and any real data |
| B-191 concurrent log writes | @software-engineer | pilot start (per D-057) |
| Approved frozen run for the warning numbers (C6) | @model-risk | P0 item 4 |
| Data-handling ruling for the model host (M1) | @compliance | pilot start |
| Corrected Carrier C / conflict behaviour (B-452, B-453) | @ai-engineer-assistant + @model-risk | not the UI, but changes what the card shows |

The UI does not lift the T-027 veto and cannot substitute for C1–C8.

## 5. Out of scope for this plan

- Sending, drafting, auto-approve, auto-bind, or any control that changes a file's status.
- Porting the workbench to React, or changing `src/insureflow/static/ui/`.
- New pipeline features; the workbench shows only what the saved run contains.
- Real applicant data in screenshots, deliverables or team files.

## 6. Definition of done for each pilot UI change (D-065)

1. Refusal and block reasons are on the card in plain words.
2. @senior-underwriter checks the card from the underwriter's point of view (High findings only).
3. A Playwright screenshot is saved under `deliverables/frontend-engineer/screenshots/` named with the task id.
4. The "What's new" panel gains one line: date, task id, decision number.
5. No change to `underwriting_pipeline/ai/`, prompts, OCR, models or scorers; any `app/` change lands with self-checks.

## 7. Recommendation

Hardening the workbench is the shortest safe route to a pilot and keeps the frozen build intact. React is the right long-term surface, but it is a post-pilot project: it needs an API and an auth contract that do not exist yet, and it would add no pilot condition that the hardened workbench cannot meet.
