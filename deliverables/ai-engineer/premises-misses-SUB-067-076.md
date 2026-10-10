# Premises misses — SUB-067 through SUB-076

- Author: @ai-engineer-assistant
- Date: 2026-10-10
- Synthetic. This is a new read with the frozen extractor. The official score file did not store the address, only the name. This memo does not replace that score. No extraction code was changed.

The official premises line is 4 hits, 5 misses, 1 flagged. The flagged file is SUB-072, where both street numbers were stored and neither was picked. The five misses are below.

## Each miss

| Submission | Gold address | What came back | Document | Likely cause |
|---|---|---|---|---|
| SUB-067 | 220 Nogalitos St, San Antonio, TX 78204 | 220 Nogalitos St, Saw Antonio, TX F8204 | scan.jpg | OCR. The street number and street name are right. The city and ZIP are not. The model copied the OCR line. |
| SUB-068 | 300 Military Dr, San Antonio, TX 78223 | 300 Military br, Saw Autonto, TX | scan.jpg | OCR. "Dr" became "br" and the city is garbled. The model dropped the unreadable ZIP. |
| SUB-074 | 3 Saltillo St, San Antonio, TX 78207 | 2 Saltillo St, San Antonio, TX | scan.jpg | OCR. The house number 3 was read as 2. The city was read. The ZIP was garbage, and the model dropped it. |
| SUB-075 | 700 West Ave, San Antonio, TX 78212 | FOO West Ave, Saw Antonio, TX F212 | scan.jpg | OCR. The house number, city, and ZIP are wrong. The model copied the OCR line. |
| SUB-070 | 10 De Zavala Rd, San Antonio, TX 78249 | nothing (both addresses stored) | email.md | Two locations. The email has a main address and a second address. The gold says the main address is the premises and the second location is not a conflict. The extractor refused to pick. |

## Groups

OCR on a hard scan: 4 misses (SUB-067, SUB-068, SUB-074, SUB-075). The page was readable enough to return a name. The address line was not clean. Confidence was 1.0 on the copied line.

Two real locations treated as a disagreement: 1 miss (SUB-070).

## Proposal

P-001 is the proposal for the OCR group. It does not guess a city or a ZIP. It does not change SUB-070.
