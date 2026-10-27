# Check of D-100: P-054 (B-389 neutral words, B-390 vacancy variants, M1 every note) — @model-risk, 2026-10-16

**Verdict: OBJECTION. Two High findings are open (H1, H2).** D-100 item 2 (freeze the code, build T-103) should not start until both are closed and re-checked. An approved P-054 is not a production approval. The T-027 veto stands.

## What I re-ran (commits b007002 and e88b877, no model calls, no tracked file changed)
- `.venv/bin/python underwriting_pipeline/app/workbench.py --self-check` printed `workbench ok`. `package.py` printed `package ok`.
- (a) The code's NEUTRAL list matches R17 in carrier-match.md. shop, store, gift, goods, home and the trade words are gone. "home office", "office in a home", "office and shop" and "bookkeeping office" go to senior_referral with Carrier A suggested.
- (b) Every word the user listed is in VACANT/NO_UTILITIES (desocupado, vacante, power disconnected, utilities off) and goes to W2e (AG:51), so no confirm is offered.
- (c) `excluded_carriers` reads three sources: the route note, the extracted fields (value, quote, context) and the submission's text files.
- Dev re-score recomputed from the JSON: 20 files, route 16/20, 0 unsafe, 0 false completes, carrier_a 1, senior_referral 18, no_match 1. The misses are SUB-127/128/129/135: gold says carrier_a and the code now gives senior_referral, the safe direction. The figures match the .md.
- Screenshot D-100-P-054-producer-remark-excludes.png is present.

## High findings
**H1 (owner @ai-engineer-assistant, @compliance informed). (c) misses real producer remarks, including one in our own dev data.**
- `simulation/inbox/SUB-147/email.md` says: "coming to you guys from Carrier A, they are not renewing the account with them".
- I built SUB-147 with operations "Downtown office, CPA and bookkeeping". It routes to senior_referral with Carrier A suggested, and `excluded_carriers` returns `{}`. So the confirm card offers Carrier A, already selected.
- `_CARRIER` needs an upper-case letter, so the lower-case "declined by carrier a in 2025" (normal in producer email) is missed.
- `EXCLUDES` needs the verb right next to the carrier name. Of 23 decline phrasings I tried, it caught 10. It missed "Carrier A has declined", "Carrier A: declined", "Carrier A - declined 2024", "Carrier A (declined)", "Prior carrier Carrier A, non-renewed", "Carrier A not interested", "Carrier A no longer writes this class", "non-renewal notice from Carrier A", "Not a Carrier A risk" and "Carrier A passed".
- Resolution:
  - Match the carrier letter without regard to case, and keep a guard for "carrier a few/a lot/a bit".
  - Exclude a carrier when it is named in the same sentence as a decline word: declin*, non-renew*, not renewing, cancel*, refus*, rejected, no longer, not interested, will not, won't, passed. Over-exclusion is the safe side; a senior can still fix the note at source.
  - Add the SUB-147 email and the phrases above to the package self-check.

**H2 (owner @ai-engineer-assistant, @head-of-underwriting for R17). "cooking" is still on the neutral list, so a file that mentions cooking routes directly to Carrier A.**
- These all return `carrier_a` with no person involved: "office with cooking", "office, cooking", "office, back room cooking" and "retail store, cooking on the ground floor".
- The user's criterion (a) removes "any other occupancy word". R10 itself calls this a "cooking occupancy", and the Carrier A note says "verify: no restaurant".
- Resolution:
  - Remove "cooking" from NEUTRAL. Accept it only in the label forms "Cooking: none", "cooking none" and "no cooking", added as NEUTRAL_NO phrases after punctuation is normalised.
  - Add self-checks: the four phrases above must give senior_referral with Carrier A suggested, and "office building. Cooking: none" must stay carrier_a.
  - Update R17.

## Medium / Low (backlog, one line each)
- M1: these vacancy phrasings are not W2e, so they get senior_referral with Carrier A suggested and the confirm stays open: "utilities are off", "utilities turned off", "power is off", "no power", "no electricity", "electricity disconnected", "abandoned", "not occupied", "empty", "deshabitada", "abandonada", "sin ocupar". Fix: one pattern for utilities/power/electricity + optional verb + off/disconnected, plus these words.
- M2: (c) does not read PDF, xlsx or scanned documents beyond the extracted schema fields, so a remark in a PDF or scanned cover letter is never checked. The card should say so, or text-layer PDFs should be read.
- M3: b007002 and e88b877 are on `feat/gcp-infrastructure`, not `ai-team` (ai-team head is 3ebbf23). That branch also holds an unrelated GCP commit (6d8907e) and uncommitted `src/` changes. Before any freeze hash is recorded, fast-forward ai-team to the P-054 commits only.
- M4: the dev route gate fails at 16/20 because the dev gold predates P-053/P-054. With 1 carrier_a in 20 files, the dev set no longer measures direct-route precision. The T-103 gold must be written under R17 as amended.
- L1: W2e reads only the operations text. A vacancy remark in an email ("empty since March") does not block the confirm, while carrier excludes do read every note.
- L2: "vacancy" also catches "5% vacancy rate", which over-refers (the safe direction).
- L3: during my run, `infra/gcp/.terraform/` and `.terraform.lock.hcl` appeared in the working tree. My commands did not create them, so another process is writing to this repo.
