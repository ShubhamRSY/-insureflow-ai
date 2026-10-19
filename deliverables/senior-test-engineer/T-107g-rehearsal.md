# T-107g rehearsal of deliverables/pm/demo-guide.md (D-112)

Author: @senior-test-engineer, 2026-10-19. Run: run-demo.sh into a new /tmp folder, 0 live calls (blocked live-call attempts: 0), HEAD 7cfc959 plus uncommitted demo files. Replayed steps, rendered pages, and read the 24 committed PNGs (all 24 referenced files exist). No guide, code or team/ edits.

## Verdict: READY WITH FIXES

Run is deterministic and every action outcome matches the guide except the one wording in A2 below. The scripted figures match: SUB-184 carrier_a 3,900/1,000; SUB-127 carrier_a 5,100/1,000; SUB-133 carrier_c 11,800/2,500; SUB-129 refused on approve, send, draft. T-104 table matches the published scores quoted in the guide, the 10-25 / 5-15 minute wording matches T-107-demo-file-and-time.md, and routes for SUB-127/133/184 agree with b-415-live-check.md (127 and 133 senior_referral, 184 carrier_a; 179 also carrier_a).

D-069 check: git status after the run shows no change to workbench.html, any .jsonl or simulation/. team/BACKLOG.md and team/STANDUP.md show as modified, but their mtime (10:46:42) is before my pre-run status snapshot (10:46:51), so they were already modified (orchestrator D-112 notes), not by the run. Saved-reply files show as deleted/changed (226 entries) from the earlier re-key; the replies the run needs are present (69).

## High findings

H1. A2 quotes the wrong refusal text and points at the wrong moment. The guide says that sending before approval is refused with "no logged decision by a listed underwriter" and shows T-105-SUB-133-02. In the run and in that screenshot, the first send on SUB-133 (before the senior confirm) is refused with "a senior referral needs a senior underwriter to confirm the market first" (T-107c). "No logged decision by a listed underwriter" only appears after the senior confirm and before approve, and that shot is T-105-SUB-133-04, which the guide never references. A presenter reading A2 aloud will say words that are not on the screen. The same stale text is in "Known rough edges: Send wording" (it says the refusal says "no logged decision"; since T-107c it says the senior-confirm text first). Fix: rewrite A2 to the senior-confirm wording, and either add 133-04 as a step between A3 and A4 ("send again before approve: no logged decision") or drop the claim. Same shot 127-02 also shows the senior-confirm wording (not referenced by the guide, so no conflict there).

## Medium / Low

- M1. "Before you start" says the SUB-184 saved reply must still be copied by hand and run-demo.sh is unchanged. Untrue now: run-demo.sh already copies SUB-184 and SUB-179 and the run replays SUB-184 end to end. The presenter may waste time or doubt the script.
- M2. "Expected output ends with SUB-133 [...]" is wrong: output ends with "PAGE_EXISTS_IN_BOX False ..." and "PNGs skipped (playwright not in .venv)". The presenter will have no PNGs from the script and must open the HTML in shots/ (the guide says this, but the PNG-skip line looks like a failure).
- M3. SUB-184 card shows "Not read by extraction: application.pdf" beside values read from that file (B-428). The guide's rough-edges list names this only for SUB-127 and SUB-133; add SUB-184 since it is the opening screen. Not a High: O1-O4 never claim otherwise.
- M4. Guide says the "What's new" panel has about 45 entries open at the top; it now shows the latest 5 of 49 with "Show all" (T-107d). Still open by default and 5 dense developer notes on every screenshot; wording stale.
- M5. SUB-184 quote (3,900 / 1,000) is not stated in the guide; O3-O4 end at "written to to-carrier" and no O5 quote step exists although T-107e-SUB-184-04-quote.png exists. Optional add.
- L1. Committed screenshots carry the yellow banner with a scratchpad path (/private/tmp/claude-501/.../demo2/box). Safe, looks odd.
- L2. Rough-edge claims "Senior confirmation banner printed twice" and "After approval the card still shows approve form" were not visible in the 133-06 and 184-02 shots I read (the confirm banner shows once; after send the form is replaced by the "Already sent" block). Possibly already fixed; claims may be stale.
- L3. Rough-edge "Not read by extraction ... SUB-127" claim reviewed only for SUB-133 (loss-runs.jpg shown, confirmed). SUB-127 not opened.
- L4. History table on 133-06 lists only approve and send, not the senior confirm; A3 says "the record shows who, when, why, and which file version" (true of the green banner, not of History). Say "banner".
- L5. Playwright is missing from .venv, so no fresh PNG retake is possible from this checkout; the committed PNGs were not regenerated and so were compared on content only, not pixel-diffed against the fresh pages.
