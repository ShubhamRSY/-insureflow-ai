# C7 freeze note — assist-only pilot

- Date: 2026-10-21. Written in OpenCode, not independently reviewed.
- Status: template. The freeze starts only when the pilot owner fills the values below at pilot start.

## Values to record before the first real file

| Item | Value at pilot start |
|---|---|
| Branch and commit | _to be recorded_ (the merged commit of `pilot-conditions`, plus `sso-b190` if merged) |
| Code SHA | _to be recorded_ (`git rev-parse HEAD`) |
| Prompt version | `759b3e6bc9b2` (2,787 bytes) — unchanged by this branch |
| Model | `qwen/qwen3.8-27b` through `LLM_MODEL` (Groq free tier) |
| Scorer | frozen v11 sha256 `7ddcfb50521b7af17f00c0e148891ca40008d019ce257b9b5d121c7fa6d3fcbb` |
| Lint | sha256 `01147a7532bdd7f1ec00861200d1d5e6bbf87f12612389416ff58b78844ea653` |
| Gold manifest | T-117 `7e076534432f1276bfe6198643547498b613c4f2b7aceb2ed618314b5e39fd33` |

## Checks

1. Before start, record `git rev-parse HEAD` and run:
   - `rg -n "gsk_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{20,}" underwriting_pipeline tests`
2. During the pilot, run `git diff --stat underwriting_pipeline/` at every review. It must be empty.
3. No change to extraction, prompts, OCR, models or scorers without the user typing `approve change P-###` (D-017).
4. An `app/` change needed for C1–C3 is @software-engineer's (D-035) and must land before start, with self-checks.
5. Host and model come only from the environment. No paid API.
6. Any change breaks the freeze: the pilot stops and @model-risk decides whether it resumes.
