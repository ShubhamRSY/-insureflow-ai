# T-104 mix — the producer's intent (not gold)

- Written by the orchestrator from @producer's build report and `build_SUB-174-205.py` (the producer role cannot write deliverables/), 2026-10-17, D-105. Not gold: scope labels and routes in gold come only from @senior-underwriter, from the documents and written rules. Not shown to the gold writer.

| Files | Producer's intent |
|---|---|
| SUB-174–187, 200–205 (20) | In scope |
| 174, 175 | Boundary: scanned JPG / image-only PDF loss run, typed application |
| 176 | Boundary: Spanish email, English application |
| 177 | Boundary: Spanish business name, English application |
| 178 | Boundary: one-row schedule |
| 179, 180 | Boundary: PO box mailing address; prior address |
| 202–205 | Gold-incomplete: year built missing; sq ft conflict; sales conflict; loss runs missing |
| SUB-188–199 (12) | Out of scope |
| 188, 189 | C1 scanned application (188 near-pass: clean scan) |
| 190 | C1 + C2 |
| 191, 192 | C2 (192 near-pass: locations only in an xlsx schedule) |
| 193 | C3 near-pass: Spanish application, English email |
| 194 | C2 + C3 |
| 195 | C1 + C3 |
| 196 | C3 (typed PDF, Spanish) |
| 197, 198 | C4 email only |
| 199 | C2: replaced (D-107) by Brazos Valley Plumbing Supply LLC, application "Location 1"/"Location 2" and a two-row schedule. |

Producer's in-scope route intent: carrier_a 5, carrier_b 6, carrier_c 4, senior_referral 3, no_match 2. Formats: md, csv, xlsx, typed PDF (text layer), JPG scans, image-only PDF. The script takes the repo root as its argument.

## Rebuild (D-107)

In-scope loss runs rebuilt from the published carrier layouts: Carrier A 174 (scanned JPG), 183 (typed, no-claims line), 184; Carrier B 175 (image-only PDF), 182, 186; Carrier C 185 (now Sierra Vista Apartments LLC), 187. 176, 180 no-known-loss letters; 177–179, 181, 200–204 agency summaries; 205 none. Clean / complete-intended: 174–187, 200, 201; gaps kept on 202–205. Out-of-scope 188–198 regenerated with the same content.

## Targeted fix (D-107, second round)

Restaurant applications 175, 177, 182, 186, 203 state the hood/extinguishing last-inspected date. 185 (2 stories, fully sprinklered, schedule added) and 187 (2 stories, unsprinklered) agree on stories. 179 and 184 (now Keller Insurance Services PA) are plain offices ("Office. Clients by appointment. No food, no alcohol.") with typed Carrier A runs.
