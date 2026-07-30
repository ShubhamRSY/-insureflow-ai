# Rytera — Application Guide

**What it is:** Rytera is an AI underwriting platform for **commercial insurance**, **mortgage**, and **lending**. It ingests submission packages, runs specialist agents, checks appetite/oracles/compliance, prices the risk, and produces a memo for a **licensed human** to sign off. Bind can stay off in shadow/pilot mode.

**Live:** [ryterainc.com](https://ryterainc.com/) · **Dashboard:** [ryterainc.com/dashboard](https://ryterainc.com/dashboard)

![Rytera brand](./screenshots/00_brand.png)

---

## How a submission flows (all verticals)

```text
Intake → Parse → Verify → Score → Price → Decide → (optional) Bind
   │        │        │        │       │        │
 docs    OCR/XML   oracles  agents  quote   UW memo + HITL
```

| Stage | What happens |
|-------|----------------|
| **Intake** | Packages arrive via upload, directory, email/IMAP, S3, or demo presets |
| **Parse** | ACORD / loss runs / SOV / inspections (or mortgage/lending docs) are classified and extracted |
| **Verify** | Cross-doc reconciliation + oracle lookups (CLUE, A-PLUS, NCCI, CAT when keyed) |
| **Score** | Risk, loss-run, compliance, fraud (and vertical-specific) agents |
| **Price** | Indicated premium / rate lock / loan pricing |
| **Decide** | ACCEPT / CONDITIONAL_ACCEPT / REFER / DECLINE (or mortgage/lending equivalents) |
| **HITL** | Licensed UW sign-off; shadow mode blocks live bind |

---

## Public marketing site

**URL:** `/` on [ryterainc.com](https://ryterainc.com/)

Explains the product, pipeline stages, verticals, platform capabilities (HITL, PII redaction, connectors, queue, audit), integrations, and FAQ. Use this for prospects; use the **dashboard** for demos and pilots.

---

## Dashboard — section by section

Open **Dashboard** after sign-in. Sidebar groups match below.

### Overview

![Overview](./screenshots/01_overview.png)

**Route:** `/` (dashboard home)

**What it does:** Home pulse of the platform — job counts by vertical, market-cycle chip, queue snapshot, one-click demos, and recent insurance journey strips.

**Use when:** Starting a demo or checking “is anything running?”

---

### System Health

**Route:** `/system`

**What it does:** Diagnostics for LLM mode, job store, encryption, and related checks. Shows overall healthy / degraded / missing without exposing secrets.

**Use when:** Before a pilot demo or after deploy.

---

### Insurance (core product)

![Insurance jobs](./screenshots/02_insurance.png)

**Route:** `/insurance`

**What it does:** Commercial P&C underwriting workspace — run demos or custom packages, see the job table with journey mini-strips, open a job for full detail.

**Key actions:**
- One-click sample submissions
- Retry / report PDF / download / delete jobs
- Click a row → full **submission journey**

---

### Insurance job detail — Submission journey

![Submission journey](./screenshots/03_submission_journey.png)

**Route:** `/insurance/jobs/:jobId`

**What it does:** End-to-end transparency for one submission: stages (intake → decision), COPE / oracles / reconciliation, UW memo, pricing build-up, visual analysis (if photos), quote/report downloads.

**Why it matters:** This is the “no black box” screen for UW and auditors.

---

### Pilot Lab

**Route:** `/pilot`

**What it does:** Carrier/MGA pilot tooling — sandbox readiness (CLUE / A-PLUS / Guidewire / Redis), seed demo packages, run/calibrate redacted packages, auto-redact PII, ingest email, and **mailto outreach** drafts.

**Use when:** Preparing or running a 30-day shadow pilot.

---

### Mortgage

**Route:** `/mortgage`

**What it does:** Residential/commercial mortgage pipeline — demo loan packages, directory submit, job queue with stage strips, audit trail lookup.

**Decisions:** Approve / Refer / Suspend / Deny + rate quote.

---

### Lending

**Route:** `/lending`

**What it does:** Business and consumer loan underwriting — form, document upload, or server directory. Shows decision, rate, amount, risk, and journey strip from the pipeline timeline.

---

### UW Sign-off (workflow)

**Route:** `/workflow`

**What it does:** Human-in-the-loop queue — licensed underwriter approve / refer / decline with notes and override reasons. Pending count badges in the nav.

**Use when:** Calibrating AI vs UW judgment.

---

### Queue

![Queue triage](./screenshots/04_queue.png)

**Route:** `/queue`

**What it does:** Prioritized submission queue with fit/triage scores and journey strips so UW time goes to the hottest files first.

---

### Renewals

**Route:** `/renewals`

**What it does:** Pre-renewal / premium audit tracking — create audits, compare estimated vs actual premium, complete with notes.

---

### Override Analytics

**Route:** `/overrides`

**What it does:** Measures how often UW overrides AI decisions — critical pilot KPI (target override rate &lt; 25% by day 30).

---

### Eval Trends

**Route:** `/eval-trends`

**What it does:** Charts quality/eval trends over time (RAGAS-style and release gates when evals are run).

---

### Portfolio

**Route:** `/portfolio`

**What it does:** Aggregated view of policies/exposures for concentration and book-level context.

---

### Authority Matrix

**Route:** `/authority`

**What it does:** Binding authority tiers (junior → senior) and co-sign thresholds — AI proposes; limits enforce who can bind.

---

### Market Cycle

**Route:** `/market`

**What it does:** Hard/soft market phase admin — adjusts appetite tightness and premium modifiers.

---

### Model Registry

**Route:** `/registry`

**What it does:** Experiment / model release checklist and registry (governance for agent versions).

---

### Integrations

**Route:** `/integrations`

**What it does:** Health and mode (live / simulated / auto) for oracles, PAS (Guidewire/BriteCore), CRM, and doc sources.

---

### Webhooks

**Route:** `/webhooks`

**What it does:** Register HMAC-signed callbacks for LOS / downstream systems when jobs complete.

---

### Settings

**Route:** `/settings`

**What it does:** Account / org preferences and session-related settings for the signed-in user.

---

### Broker status (share link)

**Route:** broker-facing status views (when enabled for a package)

**What it does:** Lightweight status for brokers without full UW dashboard access.

---

## Decisions you’ll see

| Vertical | Typical outcomes |
|----------|------------------|
| Insurance | `ACCEPT`, `CONDITIONAL_ACCEPT`, `REFER`, `DECLINE` |
| Mortgage | Approve / Refer / Suspend / Deny + rate |
| Lending | Approved / conditions / referred / declined / suspended |

Shadow / pilot: analysis + sign-off OK; **live bind blocked** until PAS + policy allow it.

---

## Security & audit (built into the product)

- JWT + role-based access (admin / underwriter / viewer)
- Org-scoped jobs
- PII detection + redaction for pilots
- Encrypted audit bundles + SHA-256 regulatory ZIP exports
- Fail-closed when required data/oracles are missing in hardened mode

---

## Quick demo script (10 minutes)

1. Open [dashboard](https://ryterainc.com/dashboard) → sign in  
2. **Overview** → run an insurance demo  
3. **Insurance** → open the job → walk **Submission journey**  
4. **Queue** → show triage prioritization  
5. **Pilot Lab** → show sandbox readiness + shadow mode  
6. Optional: **UW Sign-off** → show human override path  

---

## Related docs

| Doc | Purpose |
|-----|---------|
| [PILOT_PARTNER_BRIEF.md](./PILOT_PARTNER_BRIEF.md) | What to ask a carrier/MGA |
| [../outreach/THIS_WEEK_OUTREACH.md](../outreach/THIS_WEEK_OUTREACH.md) | Email templates |
| [../ops/ORACLE_LIVE_WIRING.md](../ops/ORACLE_LIVE_WIRING.md) | Live CLUE / A-PLUS keys |
| [../architecture/architecture.md](../architecture/architecture.md) | Deep technical design |
| [../../STRUCTURE.md](../../STRUCTURE.md) | Repo folder map |

---

## Regenerating screenshots

Existing captures live in `docs/product/screenshots/` (copied from `marketing/assets/linkedin_deck/`).

```bash
# With API running locally on :8002 and Playwright installed:
PYTHONPATH=src python scripts/marketing/build_linkedin_deck.py
# Then copy new PNGs into docs/product/screenshots/
```
