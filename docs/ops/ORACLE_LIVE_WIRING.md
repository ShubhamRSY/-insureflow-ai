# Oracle live wiring (CLUE / A-PLUS / NCCI / CAT)

**This week goal:** kill “your loss history is simulated” before pilot demos.

Clients already support real HTTP when credentials are set. Simulated mode is
honest (`synthetic: true`) and must not be treated as a clean loss history.

## 0. One-command status (no secrets printed)

```bash
PYTHONPATH=src python scripts/pilot/verify_oracles.py
PYTHONPATH=src python scripts/pilot/verify_oracles.py --ping   # after keys are set
```

Exit code `2` = required keys still missing. Exit `0` = CLUE + A-PLUS configured.

## 1. Paste keys into `.env` (gitignored)

```bash
ORACLE_MODE=auto
PILOT_SHADOW_MODE=true

CLUE_API_KEY=...
CLUE_API_URL=https://vendor-sandbox/.../clue/...

APLUS_API_KEY=...
APLUS_API_URL=https://vendor-sandbox/.../aplus/...

# optional
NCCI_API_KEY=...
NCCI_API_URL=...
CAT_API_KEY=...
CAT_API_URL=...
```

`ORACLE_MODE=auto` → live HTTP whenever key + URL are configured.  
`ORACLE_MODE=live` with missing keys → `misconfigured` / query failure (not fake clean).

## 2. Verify API surface

```bash
PYTHONPATH=src python cli.py sandbox-status
# or with API up:
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8002/pilot/sandbox-status
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8002/pipeline/ecosystem/status
```

Look for CLUE / A-PLUS `status` in `{ready, sandbox_ready}` and not `simulated`.

## 3. Fail closed in production (later)

```bash
REQUIRE_LIVE_ORACLES=true
BANK_MODE=true
```

Until vendor sandboxes are issued, keep `PILOT_SHADOW_MODE=true`.

## 4. Where to get keys

Copy/send emails in [`THIS_WEEK_OUTREACH.md`](./THIS_WEEK_OUTREACH.md) §B (LexisNexis + Verisk).
