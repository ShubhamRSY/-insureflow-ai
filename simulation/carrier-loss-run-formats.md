# Recognised carrier loss-run formats (P-044, D-090)

Fictional. These three layouts are the only loss runs the pipeline accepts automatically (`prepare.carrier_run_valued`).
Anything else that looks like a loss run goes to needs review: "not a recognised carrier loss run".
A no-known-loss letter is never a loss run (P-040).

Rules for every format:
- The header is the first line. Blank lines and lines starting with `_` (the synthetic-data banner) are skipped.
- Then the lines below in order: the insured line, one or more period lines, the valued line.
- Then either the claims table (header, separator, at least one row) or the carrier's own no-claims line, and nothing after it.
- Dates are YYYY-MM-DD. The accepted date is the valued line's date.

## Carrier A

```
CARRIER A — LOSS RUN (FICTIONAL)
Named insured: <name>
Policy period: 2025-03-01 to 2026-03-01
Valued as of: 2026-09-30
| Date of loss | Cause | Paid | Reserve | Status |
|---|---|---|---|---|
| 2025-06-14 | water damage | $4,200 | $0 | closed |
```
No claims: `No claims reported by Carrier A for the policy periods above.`

## Carrier B

```
Carrier B Loss History Report (fictional)
Insured: <name>
Policy term: 2025-01-01 to 2026-01-01
Valuation date: 2026-09-30
| Loss date | Description | Paid | Outstanding |
|---|---|---|---|
| 2025-08-02 | kitchen fire | $12,000 | $3,000 |
```
No claims: `Carrier B certifies no claims for the policy terms above.`

## Carrier C

```
CARRIER C | LOSS RUN | FICTIONAL
Account: <name>
Term: 2025-04-01 - 2026-04-01
Valued: 2026-09-30
| Claim no. | Loss date | Type | Paid | Open reserve |
|---|---|---|---|---|
| C-1042 | 2025-11-20 | wind/hail | $8,500 | $0 |
```
No claims: `Carrier C: no claims reported.`
