# T-027 assist-mode pilot — is assist-only inside the production veto?

- Author: @model-risk (independent). 2026-10-19.
- Read: `deliverables/model-risk/T-027-memo.md` (today's T-108 gate memo), `model-inventory.md`, `validation-standards.md`, `T-027-gate-memo-T-104.md`; `team/DECISIONS.md` D-011/D-012, D-017, D-021, D-022, D-025, D-033/D-053, D-037, D-057, D-084, D-096, D-105 (P-055), D-113, D-114; `team/TASKS.md` T-027 notes; `team/BACKLOG.md` B-190, B-191, B-432; code read-only: `underwriting_pipeline/app/package.py` (`build_package` :250, `send_to_carrier` :443), `app/workbench.py` (`record_decision` :512), `ai/prepare.py` (`write_drafts` :1331), `ai/scope.py` (fail-closed P-055 detector).
- Checked: nothing changed. No code, prompt, gold, scorer or score file touched; no pipeline run; no model call. Worktree left as found (HEAD `667ce8a`).
- Basis: the verified T-108 evidence (run integrity held; 4 of 16 gate criteria fail). No new score and no new run were produced for this memo. Synthetic data throughout.
- Not a production approval. Approved P-### proposals are not production approvals.

## Verdict

**Assist-only pilot is (a) permitted under conditions.** An assist-only pilot on real submissions sits **outside** the T-027 production veto while conditions C1–C8 below all hold. It is not blocked. Break any condition and the pilot falls back inside the veto from that moment and stops. The T-027 veto itself is unchanged (final section).

## What the veto covers (the scope ruling)

- T-027 is a **production** veto: protocol decision rights give @model-risk "production approval of any model", and the inventory entry for C-1 says "not approved for production". Its resolution path — (a)–(d) in D-037 and the gate table in `T-027-memo.md` — is calibrated to output that **acts**: fields pre-prepared, file marked complete, route set, missing-info auto-drafted, send enabled. H1's harm was stated exactly that way: SUB-233 reached the underwriter "as routable, send-enabled and auto-drafted".
- Assist-only as defined here removes every acting leg: never routable, never sendable, no draft leaves the tool, a human reads and decides everything. What remains — showing a person a proposal — is the project's standing baseline ("the underwriter makes every final decision. No auto-decline, no auto-bind"). Suggesting is steps 2–5; deciding is step 6.
- The inventory tiering agrees: extraction is Tier 2 and "becomes Tier 1 if a cited value reaches a carrier package with no underwriter confirm". Assist-only guarantees underwriter confirmation on every value and no package ever, so it keeps the component inside the tier it is validated for.
- This is a scope ruling by the veto holder, not a permission to start: whether, when and on what files a pilot runs is @user's decision (@pm schedules). My conditions bind for as long as I hold the veto.

## High findings (why the conditions are what they are)

**H-A1 — Assist-only is not a mode the code knows; it must be enforced before the first real file (owner @software-engineer).** The acting paths are live: `send_to_carrier`/`build_package` in `package.py`, `write_drafts` in `prepare.py` (writes `simulation/pending-approval/`), `record_decision` in `workbench.py` (an approve makes a file sendable, D-033/D-053). Nothing in the code knows what "assist-only" means. Today nothing can send without the user's exact send line (T-086) and drafts only exist if someone runs them — so assist-only is reachable by process, but process fails open the day someone logs an approve or runs a draft pass. Remediation: the C1–C3 self-checks (refusal test on a pilot submission id, outbox emptiness, no approve rows) run and are recorded before the first real submission; recommended reinforcement, a small guard in `app/` refusing pilot submissions in `send_to_carrier`/`build_package` (@software-engineer, D-035 — not `ai/`, so no P-###), self-check logged. Without this, my verdict is (b).

**H-A2 — H2's silent errors are the residual risk that stays inside assist-only.** Operations 9/20, loss runs 5/20, 17 wrong values shown unflagged at confidence 1.0 (T-108). A proposal is only safe if the human checks it, and anchoring is real. That is why C6 (citation + confidence + an explicit weak-field warning quoting 9/20 and 5/20), C5 (correction log) and C8 (stop threshold) are conditions, not suggestions. If they cannot be implemented, the verdict is (b).

## Conditions — all must hold, continuously (C1–C8)

**C1 — Send path never enabled.** No pilot file ever reaches a sendable state and nothing sends.
Check: `send_to_carrier()` and `build_package()` refuse a pilot submission id with a plain-language reason ("assist-only pilot: send disabled"); no `approve` row in `deliverables/software-engineer/decisions.jsonl` names a pilot submission; `sends.jsonl`, `simulation/to-carrier/` and the decision log are diffed empty of pilot ids at start and at every review; the user's exact send line (T-086) is never given for a pilot file.
Rule: T-027 memo H1 ("send enabled" was a leak leg); D-017 sends rule (only the simulated @account-manager approves a carrier send on a complete, in-appetite, conflict-free, fully read file, with a reason — assist-only is stricter: nobody sends); D-033/D-053/T-086 send gates.

**C2 — No draft leaves the tool.**
Check: `prepare.write_drafts()` is never run on pilot submissions; `simulation/pending-approval/` and `simulation/to-producer/` diff empty of pilot ids; missing-info questions exist only as on-screen text.
Rule: D-105/P-055 (automated missing-info drafts count as leakage; out-of-scope files get no automated draft); T-027 memo H1 leg 3; D-017 sends rule (producer requests approved by @account-manager only).

**C3 — Route and status are proposals; the scope verdict is always shown.**
Check: route displayed only as a labelled suggestion in the D-096 style ("suggestion only — not a route decision"; provisional labels keep "sending stays blocked"); the tool applies no status or decision change to a pilot file; the `ai/scope.py` verdict with its reasons is displayed on every pilot file (fail-closed, scope.py:205); pilot instructions state scope is the underwriter's decision and every underwriter scope correction is logged (feeds B-432); @senior-underwriter UI check with a synthetic-data screenshot (D-065).
Rule: D-096; D-105/P-055 ("no carrier route", manual intake as a whole file); T-027 memo H1 leg 2; no auto-decline, no auto-bind.

**C4 — Who may see the output: authenticated pilot underwriters and account managers only, inside the workbench.**
Check: B-190 sign-in + audit log in place (hard blocker below); no AI output on a real submission copied into any deliverable, team file, screenshot or outbound artifact (protocol data rule: synthetic only in team artifacts; B-432's real-data ban on screenshots); model host sees document text only as already approved — Groq free tier, `LLM_API_KEY`/`LLM_BASE_URL`/`LLM_MODEL` from the environment, key never written or printed.
Rule: D-057 item 2 ("authenticated underwriter action … before any real data" → B-190); D-011, D-012; protocol synthetic-data rule.

**C5 — Everything is logged.**
Check: each display of AI output on a pilot file logs user, submission, run/prompt hash and model; every underwriter correction or rejection of a suggested value logs field, suggested value, final value and reason — this log is the pilot's error metric (the D-084 silent-error measure with human corrections in place of gold); `extraction_failed` files show no suggestion at all and are counted apart (D-021); tokens per call logged (D-022 item 5); log export reviewed by @model-risk at pilot end and on any stop event.
Rule: D-017 (decisions logged), D-084 (silent-error and automation-rate metrics), D-021, D-022.

**C6 — Every output is labelled a proposal.**
Check: every suggested value carries its citation and confidence (D-037 (a)/(b), built by P-016) plus a standing "AI proposal — verify against the source" marker; needs-review and low-confidence flags are visible and never pre-accepted; operations and loss-run values carry an explicit warning naming their measured T-108 accuracy (9/20 and 5/20) until a fresh frozen run says otherwise; status is shown as a suggestion, never written as final; @senior-underwriter UI check (High only) before start.
Rule: T-027 conditions (a),(b) from D-037; standing rule "the underwriter makes every final decision"; T-027 memo H2.

**C7 — Frozen, approved build only.**
Check: code SHA, prompt version and model recorded before the first real file (the D-113/D-114 pattern) and `git diff` on `underwriting_pipeline/` stays empty across the pilot; no change to extraction, prompts, OCR, models or scorers during the pilot without the user's "approve change P-###" (D-017); any app change needed for C1–C3 is @software-engineer's (D-035) and lands with self-checks before start; host/model from environment variables only, no paid API beyond the approved free tier (D-011, D-012).
Rule: D-113/D-114, D-017, D-011/D-012.

**C8 — Time-boxed, registered, with stop conditions.**
Check: the pilot is a task in `team/TASKS.md` with owner, file count and end date; a written correction-rate threshold per field is set by @head-of-underwriting before start, and any field above it pauses the pilot; immediate stop and report to me on: any pilot file sent, drafted or made sendable; any real file processed before B-190; any C7 change during the pilot; at the end @model-risk reviews the correction log and states whether anything changes — pilot results do not alter published scores (D-025) and passing the pilot lifts nothing.
Rule: D-025, D-017, protocol task format.

## What the T-108 run changed for this question

- It replaced the risk picture with measured, integrity-checked evidence (code `457f1bf`, prompt `759b3e6bc9b2`, scorer v7, gold manifest `11933e96…` source-checked field by field under D-113/D-114, run once and scored once, 0 call failures). The conditions below rest on checked numbers, not assumptions.
- **H1 (scope leak): makes assist-only necessary, not more dangerous.** In production, SUB-233 leaked all four ways — field, provisional route, automated draft, send enabled — a hard gate fail. Assist-only structurally deletes three of those four legs (C1–C3). The surviving leg, fields displayed on a wrongly-in-scope file (the detector bug, B-432), is a Medium in this mode: contained by C3's always-shown scope verdict, the "scope is your call" instruction and logged scope corrections that feed the detector fix. H1 is the argument for assist-only being the *only* tolerable mode today; it adds no acting risk to it.
- **H2 (operations 9/20, loss runs 5/20, 17 unflagged errors at confidence 1.0): makes assist-only more dangerous than having no tool, and far less dangerous than production.** The human reads wrong values and can be anchored — but in production the same values feed status, route and send, where a wrong value acts by itself. Assist-only contains the harm to a proposal a person can check against the cited source; C6's weak-field warning quoting the measured rates, C5's correction log and C8's stop threshold are what keep it contained. H2 does not block assist-only — but if C6/C5/C8 cannot be implemented, my verdict becomes (b).
- Net: neither finding is cured by assist-only; both are **contained** by it. That is the case for (a), not against it.

## Suggesting versus acting — and the gates failing today

- **Suggesting (assist-only):** a value with citation and confidence on screen; a labelled route suggestion; an on-screen question list. A human reads, checks, decides. Inside the standing rules in every mode.
- **Acting (production, blocked):** writing a draft (`write_drafts` → `simulation/pending-approval/`), logging an approve that makes a file sendable (`record_decision` → `decisions.jsonl`), building or sending a package (`build_package`/`send_to_carrier` → `simulation/to-carrier/`), any tool-applied status change, auto-decline or auto-bind (never permitted in any mode).
- **Gates failing on T-108:** P-055 scope gate (1 leak, recall 11/12); operations floor (9/20); loss-run floor (5/20); detection recall (11/12). Passing: route gate (0 unsafe, 18/20), false completes 0, false manual intake 0.
- **Do they matter in assist-only?** The acting gates — leak legs, unsafe routes, false completes — matter only if an action path is reachable; under C1–C3 none is, so they do not block assist-only. That is exactly why H-A1's enforcement is a precondition: the gates are only irrelevant if the disabling is verified, not assumed. The field floors and detection recall still matter because a human reads the output — mitigated by C3/C5/C6/C8, never cured here, and they remain absolute blockers for production.

## What a timed assist-only pilot still needs before real data

- **Hard blocker — B-190** (authenticated underwriter action: login/SSO, audit log for every decision and view). D-057: "Production requires an authenticated underwriter action … **before any real data**." Assist-only does not soften this: no real submission may be opened in the tool until B-190 is built and I have checked it. It also delivers C4/C5's identity half.
- **Hard blocker — B-191** (concurrent decision-log writes; the eight-thread case errors). D-057 item 3: "**required before pilot**." As written, a pilot — including assist-only, where C5 logging writes to a shared log — does not start until the concurrent write is fixed and checked. A single-user scope change to that condition would be @user's amendment to D-057; I do not grant one.
- **Required before start, in-repo (not backlog):** the C1–C3 self-checks, the C6 @senior-underwriter UI check, and the C8 task registration and threshold.
- **Not blockers for assist-only:** passing the T-027 gate (H1/H2 fixes plus a fresh frozen run) — that is what lifts the production veto and stays required for production only; R-030 real carrier formats — no sends exist in assist-only; the pilot changes no published score (D-025).
- **Consult, not my veto:** @compliance must confirm data handling before real applicant documents go to the model host (M1). A compliance block blocks the pilot regardless of this memo.

## Medium / Low (one line each)

- M1 Real-submission documents would be sent to the model host (Groq free tier, D-011/D-012); PII/data-handling acceptability is @compliance's call and is not assessed in this memo — consult before real data; not my veto, but a compliance block blocks the pilot.
- M2 H1's residual display leg: a SUB-233-shaped file still shows AI proposals marked "in scope" (detector bug open, B-432); contained by C3 and the logged scope corrections, not cured — the correction log feeds B-432.
- M3 R-030 (real carrier formats) is irrelevant to assist-only (no sends) and still required before any production send — no action for this pilot.
- L1 Pilot screenshots and deliverables must use synthetic data; real applicant data must not land in `deliverables/`, `team/` files or screenshots (folded into C4's check).

## What this memo is not

This is **not a production approval**, and the **T-027 veto is unchanged**: it stands exactly as written in `deliverables/model-risk/T-027-memo.md`. This memo only rules that a mode with no action paths was never inside a veto over production acting. Pilot results — however good — lift nothing; the veto resolves only through the gate criteria in that memo (0 leaks, 100% recall, all fields ≥ 18/20, fresh frozen run), and an approved P-### is not a production approval. If any condition C1–C8 fails, the pilot is inside the veto from that moment and stops until I say otherwise.
