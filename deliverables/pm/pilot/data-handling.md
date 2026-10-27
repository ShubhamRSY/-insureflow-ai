# Data handling — assist-only pilot

- Date: 2026-10-21. Written in OpenCode, not independently reviewed.
- This is an engineering description, not a compliance ruling. @compliance must clear real applicant documents (T-027 M1) before they are used.

## Model host

- Host, key and model come only from `LLM_API_KEY`, `LLM_BASE_URL` and `LLM_MODEL` in the shell (D-011, D-012).
- Approved free tier only. The repo `.env` paid OpenAI key is not used by the pipeline.
- Keys are never printed, logged or written to a file. Run the secret scan before every commit:
  `rg -n "gsk_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{20,}" <files>`
- The model sees document text only, as already approved for the pipeline. It does not see the workbench session or logs.

## Synthetic first

- Until B-190 is merged and checked and @compliance clears real data, every file is synthetic.
- Screenshots, deliverables and team files contain synthetic data only. No real applicant data is copied into them.
- The workbench refuses display and action without sign-in only once B-190 is merged; before that, do not point it at real documents.

## What the pilot logs contain

`pilot-corrections.jsonl`:

- submission id, field id, suggested value, final value, reason, actor, run hash, timestamp.

`pilot-events.jsonl`:

- action, submission id, actor, outcome, message, run hash, timestamp.
- View rows carry the prompt version and model, and the run hash.

These logs can contain the same applicant values the underwriter saw. Treat them as confidential pilot records, not as deliverables.

## Retention and access

- Files are created 0600. The parent directory permissions are not changed.
- Only the pilot owner and @model-risk read the logs. Export only on request or at pilot end.
- Do not commit either log: both are ignored by `.gitignore`.
- At pilot end @model-risk reviews the export. Delete or archive it only on @user's written instruction.
