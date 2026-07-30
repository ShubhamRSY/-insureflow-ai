# Pilot & vendor outreach — ready to send (this week)

Fill `[brackets]`, send from your Rytera email. Track replies in a sheet: prospect → sent date → next step.

---

## A. Carrier / MGA pilot outreach (send 2–3)

**Target:** regional / mid-size P&C carriers or MGAs (GL / Property / BOP). Avoid Big 5 for first pilots.

### Email 1 — cold intro

**Subject:** 30-day shadow UW pilot — redacted commercial submissions (no bind risk)

Hi [First name],

I'm [Your name] at Rytera (ryterainc.com). We run multi-agent commercial underwriting that produces a full UW memo + indicated premium before a licensed underwriter signs off.

We're looking for **1–2 shadow pilots** this quarter:

- You send **20–50 redacted** commercial packages (ACORD, loss runs, SOV, inspection)
- One UW / product owner for **2–4 hrs/week** reviews AI vs their call
- **Bind stays off** — analyze + review only until you approve any PAS wiring

Success criteria we'd agree up front:
- No silent ACCEPT when docs are missing
- Override rate < 25% by day 30 on matched book
- UW time-to-first-review < 15 minutes

One-pager attached / linked: pilot partner brief.  
15 minutes this week to see if your book fits?

Best,  
[Your name]  
[title] · Rytera  
[phone] · [email]

**Attach / link:** `docs/product/PILOT_PARTNER_BRIEF.md` (export to PDF if preferred)

---

### Email 2 — follow-up (day 4–5 if no reply)

**Subject:** Re: 30-day shadow UW pilot

Hi [First name] — quick bump. Happy to run **5 of your redacted packages** first (no commitment) and send back side-by-side AI vs expected decision before a longer pilot.

Open to a short call [Tue/Wed afternoon]?

---

### Email 3 — after interest (ask for the package)

**Subject:** Next steps — package drop + UW reviewer

Great — here's what we need to kick off week 1:

1. Secure drop of 10–20 redacted packages (ACORD XML/PDF + loss run + SOV + inspection)
2. Named UW reviewer + preferred review cadence
3. Book segment (states, TIV band, lines)

Optional (kills the “simulated loss history” objection for your demos too):
- LexisNexis CLUE **sandbox** key + URL  
- Verisk A-PLUS **sandbox** key + URL  

We stay in shadow mode until those are live.

---

## B. Vendor sandbox key requests (send in parallel)

### LexisNexis — CLUE

**Subject:** Sandbox API access — Rytera commercial UW (CLUE)

Hello,

Rytera (ryterainc.com) needs **sandbox / UAT** CLUE Commercial access for a shadow underwriting pilot with [Carrier/MGA Name or “pending pilot partner”].

Please advise:
1. Sandbox base URL + auth (API key / OAuth)
2. Test FEINs / named insureds we may query
3. Rate limits + retention terms
4. Timeline + commercial contact for production

Technical contact: [you@…]  
Security / DPA pack available on request.

Thank you,  
[Your name]

### Verisk — A-PLUS (and NCCI if available)

**Subject:** Sandbox API access — A-PLUS for Rytera commercial UW pilot

Hello,

Requesting **sandbox credentials** for A-PLUS property loss history for Rytera’s multi-agent underwriting platform.

We will call your REST API with named insured + property address + tax ID (typically 5–7 years back).

Please send: sandbox URL, API key issuance process, sample request/response docs.

Technical contact: [you@…]

---

## C. After keys arrive (you or eng — 30 minutes)

```bash
# Paste into .env (local; never commit):
# CLUE_API_KEY=...
# CLUE_API_URL=https://vendor-sandbox/...
# APLUS_API_KEY=...
# APLUS_API_URL=https://vendor-sandbox/...
# ORACLE_MODE=auto
# PILOT_SHADOW_MODE=true

PYTHONPATH=src python scripts/pilot/verify_oracles.py --ping
PYTHONPATH=src python cli.py sandbox-status
```

Expect required feeds **CLUE** and **A-PLUS** → `sandbox_ready` / `ready`, not `simulated`.

---

## Tracking sheet (copy)

| Prospect | Type (carrier/MGA/vendor) | Email sent | Reply | Next step | Owner |
|----------|---------------------------|------------|-------|-----------|-------|
| | | | | | |
| | | | | | |
| | | | | | |
