# Final pilot build and validation — plan only (2026-11-05, D-168)

- Owner: orchestrator, written at @user's request. **Plan only. Nothing here is built, approved or scheduled.** Go-live: not yet (D-168).
- Base: the frozen build of D-167 (`pilot-integration` 1ddae83c, `PROMPT_VERSION` 392b9ce3c1af, scope-v8, qwen/qwen3.8-27b on Groq).
- Task id note: the hold-out you called "T-130" needs a new id, because T-130 is already P-082's build task. This plan uses **T-133**. Say if you want another id.

## Order

| Step | What | Gate to move on |
|---|---|---|
| 1 | `approve change P-085` and `approve change P-086` (both drafts are in `deliverables/ai-engineer/`) | Your words in this chat |
| 2 | Build P-085 (workbench label) and P-086 (cooking citations) on `pilot-integration`, with tests, self-checks, `tests/pipeline`, pyright, code review, D-065 screenshots and What's new lines | All green, plus @senior-underwriter UI check (High only) |
| 3 | @model-risk check of P-085/P-086 | No High |
| 4 | AI provider switch (below), once IT/compliance name the provider | @model-risk check; a quick set of 15 on dev data shows no failed-call or format regressions |
| 5 | If the new model needs a prompt change: its own P-### and your approval, then quick set 15 again | No High |
| 6 | **Freeze**: code SHA, `PROMPT_VERSION`, provider host, model id + version, scorer v11 hash, lint hash, C2 counter hash, all recorded in `team/NEXT-SESSION.md` | Recorded before any gold exists |
| 7 | **T-133** fresh 20+12 hold-out: @producer builds, @senior-underwriter writes gold first, lint PASS, @model-risk build check, gold manifest frozen and hashed | Look-again done on every gold fix |
| 8 | Run T-133 **once** on the exact frozen build and provider, then score once with v11 `--write`. No code change after the gold exists (D-020) | Only on your word |
| 9 | @model-risk T-027 memo on T-133 | LIFT / KEEP |

## AI provider switch — what the code needs

The pipeline calls any OpenAI-compatible `/chat/completions` host from shell settings (`llm_extract.py:1-14`). Needed from IT/compliance and in the code:

- **Endpoint:** `LLM_BASE_URL`, the provider's HTTPS base URL in the agreed region.
  - Today only the Groq URL and localhost pass the host guard, so the new host needs `ALLOW_PROVIDER=<host>` (`llm_extract.py:225`). Pilot code should pin that host, not accept any host.
  - If the provider is not OpenAI-compatible, a small adapter is new code with its own P-###. Examples: Azure OpenAI uses an `api-key` header and a deployment path; some cloud endpoints sign requests instead of using a bearer token. Today the code sends only `Authorization: Bearer` (`llm_extract.py:~690`).
- **Model setting:** `LLM_MODEL`, the exact model id with a pinned version (not an alias that moves). The model and host are in the cache key (P-014), so the first run is a fresh cache. Check the provider supports the temperature and JSON-reply settings the prompt relies on.
- **Key handling:**
  - `LLM_API_KEY` comes from the server's secret store (SSM / secrets manager) into the process environment. It is never written in a file, the repo, logs or score files.
  - The repo `.env` is never used.
  - Rotation owner named by IT. Gitleaks runs before every push.
- **Rate limits:**
  - Pacing reads Groq's `x-ratelimit-*` headers. Another host is not paced; a 429 still waits and retries (`LLM_MAX_WAIT`).
  - Confirm the provider's limits cover pilot volume. A failed call stays `extraction_failed`, counted apart (D-021).
- **No-training and retention (from the data agreement, not from code):**
  - Inputs and outputs are not used for training.
  - Retention is zero or a stated short window, and abuse-monitoring storage is off or bounded.
  - Data stays in-region, the subprocessor list is known, deletion happens on request, and there is a breach notice clause.
  - The code side is the guard: the pinned host is the only one allowed in pilot mode.
- **Logging:** keep the host name and model id in every run row (already done). Never log the key or the full request body.

## T-133 hold-out — every T-128 gate (scored once, v11)

| Gate | Target |
|---|---|
| Leakage (out-of-scope shown in scope) | 0 of 12 |
| Detection recall, overall and per criterion 1–4 | 100% |
| Wrong (false) manual intake | ≤ 2 of 20 |
| False completes / unsafe routes | 0 / 0 |
| Route accuracy | ≥ 18/20, including direct carrier routes (B-459) |
| Fields, each | ≥ 18/20 |
| C2 operations silent errors / C3 understated hazards | 0 / 0 |
| C4 operations present / hits | ≥ 18 / ≥ 15 |
| Planted-conflict recall | 100% |

Also in scope for T-133:

- **New for P-085/P-086, reported apart:** 0 open-conflict files labelled "complete", and every cooking conflict quoting its hazard sentence.
- **B-533:** include the address forms T-128 did not test (B-527/B-528, FM / State Highway / County Road).

## D-167 conditions this re-satisfies

| D-167 condition | After this plan |
|---|---|
| Frozen build only; any change re-checked | **Re-satisfied** by steps 3, 4, 6, 9. The provider switch breaks the old freeze (qwen on Groq), so the lift holds only after the T-133 memo. |
| M1 (562 cites wrong lines) and M2 ("complete" with an open conflict) closed before any send-enabled mode | **Re-satisfied** by P-086 and P-085, checked by @model-risk, and measured in T-133. |
| Texas BOP, P-055 criteria 1–4 only | Not changed by the build. It is a usage limit you hold at pilot. |
| C6 monitoring on ≥ 60 reviewed files, with stop rules | **Not re-satisfied** by a hold-out. It needs the monitoring plan written before the first pilot file (NEXT-SESSION task 3). |

Not covered by this plan: the @responsible-ai T-082 veto (see `pilot-readiness.md`), and B-525/B-529/B-532 (deferred to pilot data, D-168).
