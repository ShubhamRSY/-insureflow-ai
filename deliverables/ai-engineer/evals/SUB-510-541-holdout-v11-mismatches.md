# T-121 mismatches (scorer v11), SUB-510 to SUB-541

| SUB | Field(s) | Gold | Pipeline | Why |
|---|---|---|---|---|
| 510 | all fields, status, route | complete, carrier_a | manual intake: number of locations not clear | Part B: quote "Premises address: 1906 Hwy 290 W Ste 104, Brenham TX 77833" not read as an address |
| 513 | all fields, status, route | complete, carrier_a | manual intake: number of locations not clear | Part B: quote from the email, no house number |
| 527 | all fields, status, route | complete, senior_referral (near-miss "two floors") | manual intake: number of locations not clear | Part B: quote "One address, one building." |
| 529 | all fields, status, route | complete, senior_referral (near-miss "two entrances") | manual intake: number of locations not clear | Part B: quote "Same single building." |
| 520 | conflict | cooking: none vs countertop fryer | cooking conflict raised ("the documents disagree") | v11 cannot measure a cooking conflict (D-128/D-153); reported apart |
| 522 | conflict | cooking: none vs daily fryer | cooking conflict raised | same as 520 |
| 511, 512, 523, 524, 525, 528 | status | complete | complete — review pending | safe, not automated (B-325) |
| 526 | status | complete | incomplete | operations value held for review: "value is not in the cited text (translated or reworded)" (safe direction) |

Note: the score JSON's retry detail for SUB-518 carries the unmasked Groq org id (not a secret; same as T-120 L1). The score file is left as written (D-020).
