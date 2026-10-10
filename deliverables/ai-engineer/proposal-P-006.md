# Proposal P-006 — EasyOCR only when Tesseract fails the address

- Author: @ai-engineer-assistant
- Date: 2026-10-10
- Not implemented.

On a scanned page, keep Tesseract as the reader. Call EasyOCR only when the Tesseract address has no five-digit ZIP, is marked address invalid, or the page's Tesseract word confidence is under 0.75. Typed PDFs, Excel, and email are not sent to EasyOCR.

Trade-off: a bad scan pays about 25 to 70 extra seconds. A clean scan stays on the 1 to 3 second Tesseract path. EasyOCR recovered some house numbers and missed some names, so the fallback can help one page and hurt another. The live reader does not change until you approve this.

Risk to the loss-run rule: the fallback can print a date that was not on the page. The citation check would then accept it, because the citation is the OCR text. A fallback must not be allowed to create a loss-run date that Tesseract did not already show.

Expected accuracy: on the eight development scans, EasyOCR fixed two house numbers Tesseract missed and missed two names Tesseract read. Used only as a fallback, it would run on the pages whose address failed validation, not on every page. Expected speed: most pages stay at Tesseract speed. A failed page adds roughly half a minute.

Expected score impact: unknown until a development rerun. It does not change the published hold-out by itself. Premises hits can rise only on pages where EasyOCR reads the gold address and Tesseract did not.
