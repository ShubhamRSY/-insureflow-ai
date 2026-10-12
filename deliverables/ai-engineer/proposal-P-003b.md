# Proposal P-003b — OCR confidence on scans only

- Author: @ai-engineer-assistant
- Date: 2026-10-10
- Not implemented. Replaces P-003. P-003 stays closed.

Use a confidence number computed from Tesseract word scores, plus the ZIP and city checks, only when the source page is a scan. A typed PDF, an Excel file, and an email keep today's path, including the model's confidence and the 0.75 gate. Show both numbers in a new comparison file. Do not edit a frozen scorer.

Trade-off: a bad scan can be marked weak without making a clean PDF look unread. The scan number can still drop a field a person could have read.

Risk to the loss-run rule: a scan with a low word score can drop a date. That is a null, not an invented date. Typed loss runs stay on the current path, so this does not add a way to create a date.

Expected score impact: typed premises hits stay as they are. Scan lines that already fail the ZIP rule stay misses. The published SUB-067 through SUB-076 score does not move until you approve this and a new hold-out is scored.
