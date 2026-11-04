# check-T-130 — @model-risk independent check of P-082 (D-161)

Reviewed: branch pilot-integration, commit a94c3468 (full diff f7539497..a94c3468, including 792cc838). Temp copy via `git archive`; no model calls; no repo file edited.

**Verdict: REJECT (1 High).** This is OBJECTION O-T130-1, tagged to @ai-engineer-assistant. An approved P-082 is not a production approval; the T-027 veto stands.

## What I re-ran
- `scope.py` self-check at a94c3468: `scope ok scope-v7`.
- tests/pipeline: **94 passed**.
- Sweep (`evals/T-130/sweep.py`) re-run, v6 (f7539497) vs v7 (a94c3468): **380 folders, 380 identical, 0 newly in scope, 0 newly manual intake**. Dev 12: DEV-01–05 in scope, DEV-06–12 manual intake. These match the as-built. The as-built's 381 counts `simulation/inbox/__pycache__/` as a folder (see L1).
- ReDoS: the 792cc838 label regex backtracked exponentially. `"INSURED: ACME ROOFING AND CONSTRUCTION LLC"` took 3.7 s, and 26 capitals took 11.6 s, doubling with each extra character. a94c3468's possessive version runs `_place_words` on 5–18 KB adversarial lines in ≤ 4 ms. **Closed.** The possessive form can only make the label fail to match where the old one matched, so it hides the same addresses or fewer. That makes it stricter or equal, never looser.
- Differential test of `_place_words`, v6 vs v7, on 60,200 generated label × address × joiner combinations: v7 fires wherever v6 fires, **except for 3,645 cases, all from the issue in H1.**

## High

### H1 — Undisclosed loosening: a single highway, FM or County Road premises moves from manual intake to in scope
v7 keeps only the longest address match at each start offset (`found[...]` in `_place_words`). v6 kept every match from STREET_WORDS and HIGHWAY. For some addresses both patterns match at the same start with different lengths, and `same_address` treats the two as different. In those cases v6 counted **one** address as **two places**. v7 counts one.

Reproduced end to end with `detect()`. I took DEV-01-hwy and changed only its premises address ("2604 Hwy 71 W"):

| Premises | v6 | v7 |
|---|---|---|
| 4400 FM 1960 Rd | manual intake (multiple_locations) | **in scope** |
| 12 State Highway 6 | manual intake (multiple_locations) | **in scope** |
| 77 County Road 12 | manual intake (multiple_locations) | **in scope** |
| 800 I-35 Frontage Rd | manual intake (multiple_locations) | **in scope** |
| 1906 Hwy 290 W | in scope | in scope |

On these addresses v6 was wrong: it read one address as two. Still, D-161 approved P-082 as **stricter only** and lists exactly what may change. The dedupe is not on that list. The as-built says "Stricter only" and does not mention it. Under D-129, anything that sends fewer files to a person needs @user's approval. The sweep missed it because no corpus folder has one of these addresses, so "0 newly in scope" holds for the corpus but not for the code.

**What would resolve it (either):**
1. Restore v6's counting for the second-address check: count every match as v6 did, or dedupe only when v6 would also have treated the two matches as one place. Then add these four addresses to the self-check as "v7 fires exactly where v6 fires". Re-run the sweep and the differential test (`diff.py`, kept in my scratch directory); the target is 0 cases where v6 fires and v7 does not. **Or:**
2. Put the dedupe to @user as its own proposal: a loosening that fixes a false positive, with the four examples above and a self-check for each. It ships only after `approve change P-###`.

I recommend option 1 now, because it keeps P-082 strictly stricter, and option 2 as a follow-up.

## Medium (one line each)
- M1: No quick-set result for T-130 is recorded, although D-161 requires one. Scope routing on all 380 folders and PROMPT_VERSION are unchanged, so a quick set is not expected to move. Either run it, or have @user record that it is waived for a scope-only change.

## Low (one line each)
- L1: The sweep counts `__pycache__` as a folder (381 against the real 380 = 365 + 3 + 12); filter on non-hidden, non-`__pycache__` names.
- L2: The comment on `tests/pipeline/test_lob_config.py` BASELINE_FINGERPRINT still says "scope-v6 (P-080, D-156)" against the scope-v7 hash.
- L3: Residual noted in the as-built: `with_resolutions` reads `package.DECISIONS_LOG`, not `log_path`, and reads outside `_LOG_LOCK`. This is unchanged from the send gate; it goes to the backlog.

## Acceptance criteria
- Stricter only (Title Case lines, role words, "home"): the targeted rules hold (self-checks pass; the label, line-above and "home" paths hide the same addresses as v6 or fewer). **The change as a whole is not stricter only (H1).**
- Spur recognised as a highway: yes, in the second-address check only; `prepare` keeps HIGHWAY.
- Approve and confirm records include the values entered on resolve: yes (`package.with_resolutions(saved)`), and tests pass.
- Dev 12 and sweep, 0 newly in scope: reproduced (380 folders), but see H1.
- Quick set: not evidenced (M1). tests/pipeline: 94 passed.
