---
description: End-of-session wrap-up; self-checks, secret scan, commit, push ai-team only, write NEXT-SESSION.md
---

Wrap up the session. Do this in the main session, in this order. Stop at the first step that says stop, and tell the user why.

1. **Wait for running turns.** If a subagent turn is still running, wait for it to hand back. Start no new build or review turn.

2. **Standup entries.** Every role that took a turn this session has an entry in `team/STANDUP.md` for today. If one is missing, the orchestrator writes a short entry for that role from what the role did this session, labelled "written by orchestrator" (D-102 item 5, D-103 item 5), and lists it in the final report. It never writes an entry for a role that took no turn. Append-only files are never edited.

3. **Self-checks.** Run each from the repo root with the `.venv` python, with no model call (unset `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` for these runs so nothing can reach a host):
   - `underwriting_pipeline/ai/llm_extract.py`
   - `underwriting_pipeline/ai/prepare.py`
   - `underwriting_pipeline/app/intake.py`
   - `underwriting_pipeline/app/package.py`
   - `underwriting_pipeline/app/workbench.py`
   - `underwriting_pipeline/models/points.py`

   Do not run any scorer's `main` (D-025). Report each as ok or failed with its output line. A failed self-check is reported, and the commit still records the state, with the failure named in the commit message and in `team/NEXT-SESSION.md`.

4. **Stage.** Stage only these paths: `underwriting_pipeline/`, `deliverables/`, `team/`, `simulation/`, `.claude/agents/`, `.claude/commands/`, `.cursor/rules/`, `CLAUDE.md`, `.gitignore`. Never stage `src/insureflow/`, `tests/`, `docs/`, `scripts/`, `.env`, or anything else. Never use `git add -A` or `git add .`.

5. **Secret scan on everything staged.** Stop and do not commit if any of these is true:
   - a staged file's content matches `gsk_[A-Za-z0-9]{20,}`, `sk-[A-Za-z0-9_-]{20,}`, or `AIza[0-9A-Za-z_-]{20,}`;
   - a staged path (added or modified, not a deletion) is `.env` or `.env.*` other than an `.example` file, `token_log.jsonl`, or under `underwriting_pipeline/cache/`.

   Print only the file name and line number of a match, never the matched text. On a stop, unstage nothing and tell the user what was found.

6. **Show the file list.** `git diff --cached --stat`, and the count of added, modified and deleted files.

7. **Commit.** One commit on the current branch, which must be `ai-team`; if it is not, stop. The message is today's date and a short summary of what the session decided and built, with the commit trailer the session uses. No `--amend`, no `--no-verify`.

8. **Remote check, before any push.** Tell the user whether `origin` exists (`git remote -v`) and whether the GitHub repo is private (`gh repo view --json visibility,isPrivate`). If `origin` is missing, the repo is public, or the visibility cannot be read, stop and do not push.

9. **Push.** `git push -u origin ai-team` and nothing else. Never push `main`, never push all branches or tags, never force. If the push is rejected, report it and stop; do not pull, rebase or retry with other flags.

10. **`team/NEXT-SESSION.md`.** Overwrite it with: where we stopped; what is approved and not built; pending decisions for the user; open vetoes and what resolves each; the first 3 tasks for the next session, in order; and the commit hash of this wrap-up. Commit and push that file the same way as steps 5 to 9 (scan, commit, push `ai-team` only).

End with **For the AI Engineer**: pending proposals (P-###), the latest eval scores, and the top failure to fix next.
