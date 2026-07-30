# Pilot partner brief — Rytera insurance shadow UW

**Ask:** 30-day shadow underwriting pilot on redacted commercial submissions.

## What we need from you

1. **Data (week 1)**  
   20–50 redacted commercial packages: ACORD (XML/PDF), 5-year loss runs, SOV, inspection / loss-control notes.  
   Drop into our secure intake folder (or SFTP). Remove personal identifiers where possible.

2. **People (weeks 1–4)**  
   One licensed UW / product manager for 2–4 hours/week to review AI recommendations vs their decision.

3. **Optional systems (weeks 2–4)**  
   - LexisNexis CLUE **sandbox** key + URL  
   - Verisk A-PLUS **sandbox** key + URL  
   - Guidewire / Duck Creek / BriteCore **UAT** (or skip — we stay in shadow mode and you bind in your PAS)

## What you get

| Deliverable | Detail |
|-------------|--------|
| Shadow UW memo | Decision (accept / conditional / refer / decline), findings, quote indication |
| Calibration report | Override rate, missed-doc catch rate, appetite gate accuracy |
| Integration readiness | Live vs simulated feed status |
| No production bind | Bind stays off until you approve live PAS credentials |

## Success criteria (agree up front)

- No silent ACCEPT when required docs missing  
- Appetite declines fire on coastal CAT / excluded NAICS / LR > 80%  
- Override rate on matched book < 25% by day 30  
- UW time-to-first-review < 15 minutes per submission

## Security

- Org-scoped JWT access, encrypted audit bundles  
- Optional bank mode (no open registration)  
- DPA / SOC2 questionnaire pack available under `legal/`

## Contact / next meeting agenda

1. Confirm book segment (GL/Property/BOP, states, TIV band)  
2. Schedule first 10-package drop  
3. Decide sandbox vs shadow-only for oracles  
4. Name UW reviewer + success metric owner  

---

*Rytera™ — rytera.ai / ryterainc.com*
