# Oracle live wiring (CLUE / A-PLUS / NCCI / CAT)

Clients already support real HTTP when credentials are set. Simulated mode is
honest (`synthetic: true`) and must not be treated as a clean loss history.

## Enable live

```bash
ORACLE_MODE=auto   # or live
CLUE_API_KEY=...
CLUE_API_URL=https://vendor-sandbox/...
APLUS_API_KEY=...
APLUS_API_URL=https://vendor-sandbox/...
# optional
NCCI_API_KEY=...
CAT_API_KEY=...
```

`ORACLE_MODE=auto` uses live HTTP whenever the client is configured (key + URL).
`ORACLE_MODE=live` with missing keys returns `misconfigured` / query failure —
not a fake clean report.

## Fail closed in production

```bash
REQUIRE_LIVE_ORACLES=true
BANK_MODE=true
```

Until vendor sandboxes are issued, keep `PILOT_SHADOW_MODE=true` and treat
oracle findings marked synthetic as **HIGH / unverified**.

Verify:

```bash
PYTHONPATH=src python cli.py sandbox-status
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8002/pilot/sandbox-status
```
