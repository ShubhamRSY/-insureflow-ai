# Proposals P-002 through P-005

- Author: @ai-engineer-assistant
- Date: 2026-10-10
- Synthetic. Not implemented. P-001 is already in the code. These four wait for "approve change P-###".
- The loss-run rule that must stay: do not invent a valuation date. A date is kept only when it is cited from a carrier loss run. A no-known-loss letter is not a date.

## P-002 — Check the address against a local Texas ZIP and city list

Check every extracted premises address against a free Texas ZIP and city list stored in the repo. If the ZIP is not in the list, or the ZIP belongs to a different city, mark the address invalid and do not treat it as read. Correct a city only when the reference list has exactly one close match, such as "Saw Antonio" to "San Antonio". Keep the original OCR text, mark the field corrected, and show both on the workbench. Never change a house number. A doubtful house number goes to needs human read.

Trade-off: a one-and-only close city can be shown as corrected, which is a constrained guess. A city with two close names is left alone. An invalid ZIP is not filled in.

Risk to the loss-run rule: low, if this runs only on the premises field. A ZIP list cannot supply a loss-run date. The same "close match" idea must not be pointed at dates.

Expected score impact: on SUB-067 through SUB-076 the four OCR premises misses do not become hits. Their ZIPs were missing or not five real digits, and two house numbers were wrong. Those stay misses. A later file whose only error is "Saw Antonio" plus a real ZIP such as 78204 could become a corrected hit. Premises on the current score stays 4 hits.

## P-003 — Stop using the model's own confidence

Compute confidence from the Tesseract word scores on the cited text, plus the checks that the ZIP is real and the city matches. Show that number next to the model's own number in the eval. Do not edit the frozen SUB-067 scorer. A new comparison file can show both numbers.

Trade-off: the model reported confidence 1.0 on addresses that were wrong. A calculated number would show those as weak. A typed PDF has no Tesseract score. If the low-confidence gate is applied to typed text, clean premises hits can disappear.

Risk to the loss-run rule: low for guessing, because a weak score drops a date instead of inventing one. Medium for the score, because a noisy but correct date on a scan can become null. Null is not a guessed date.

Expected score impact: the four bad premises lines would look low confidence and stay unstored, so they remain misses. Premises hits stay 4 if typed PDFs are left alone. They can fall if the new number is required on every file. Loss runs should not gain a guessed date.

## P-004 — Time one free local OCR engine on the development scans

Run EasyOCR or PaddleOCR, one of them, against Tesseract on the development scans only: SUB-057, SUB-058, SUB-064, and SUB-065. Report how many gold names and addresses each engine reads, and the seconds per page. Do not change the live OCR. Do not use SUB-067 through SUB-076 to pick a winner.

Trade-off: another install and a slower read. The test can show a better or a worse address line. Nothing in production changes until you approve a later switch.

Risk to the loss-run rule: none from the test itself. A later switch has a real risk: if the new engine prints a date that was not on the page, the citation check would accept it, because the citation is the OCR text. That switch would need a check that a loss-run date was not created by the engine.

Expected score impact of this test: none. The published score does not move. A later switch could raise premises only if the new engine actually reads the city, ZIP, and house number. That is unknown until the test.

## P-005 — A list of locations, with one marked primary

Let a submission store several locations and mark one primary. A second location on a schedule, or a line that says "second premises", is not a premises conflict. The primary address stays in the single premises field so the current scorer can still compare one string. Do not edit that scorer.

Trade-off: SUB-070 would keep 10 De Zavala Rd as primary and 80 Prue Rd as the other location. Two addresses that contradict each other, with no "main" or "second" label, must stay a conflict. SUB-072 (4 Mistletoe and 40 Mistletoe) is that case. If every pair of addresses became a location list, that correct flag would be lost.

Risk to the loss-run rule: low. Locations do not create a valuation date. SUB-070 has no loss run, and that date must stay missing.

Expected score impact: premises can go from 4 hits to 5, and the false conflict on SUB-070 can go away, if the primary is stored as the gold string. SUB-072 stays flagged. The TIV split on SUB-070 is a separate miss and this proposal does not fix it.
