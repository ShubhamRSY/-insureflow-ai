# OCR comparison — Tesseract and EasyOCR

- Author: @ai-engineer-assistant
- Date: 2026-10-10
- Synthetic development scans only. The live reader is still Tesseract. EasyOCR was not switched in.
- EasyOCR was loaded with English and Spanish, on CPU. Model load was 2.1 seconds after the models were already downloaded. Page time is after that load.
- A name hit means the first word of the gold name is in the text. A street hit means the gold house number is in the text, and the gold street word is in the text. This is not the full premises score. A bad city or ZIP can still be a street hit.

## Approved test pages

| Submission | Tesseract seconds | Name | House number | Street | EasyOCR seconds | Name | House number | Street |
|---|---|---|---|---|---|---|---|---|
| SUB-057 | 1.4 | yes | yes | yes | 72.6 | yes | yes | yes |
| SUB-058 | 2.4 | yes | yes | yes | 25.0 | yes | yes | yes |
| SUB-064 | 1.5 | yes | no | yes | 29.7 | yes | yes | yes |
| SUB-065 | 3.4 | yes | yes | yes | 26.6 | yes | yes | yes |

On these four pages Tesseract read 4 names, 3 house numbers, and 4 street words. EasyOCR read 4, 4, and 4. EasyOCR was about 10 to 50 times slower.

## Also measured, now that SUB-067 through SUB-076 are development data

| Submission | Tesseract seconds | Name | House number | Street | EasyOCR seconds | Name | House number | Street |
|---|---|---|---|---|---|---|---|---|
| SUB-067 | 1.1 | yes | yes | yes | 34.0 | no | yes | no |
| SUB-068 | 2.0 | yes | yes | yes | 22.6 | no | yes | no |
| SUB-074 | 1.0 | yes | yes | yes | 27.5 | yes | yes | no |
| SUB-075 | 2.1 | yes | no | yes | 22.7 | yes | yes | yes |

On these four, Tesseract read 4 names, 3 house numbers, and 4 street words. EasyOCR read 2 names, 4 house numbers, and 1 street word.

## What this does not decide

EasyOCR recovered two house numbers Tesseract missed (SUB-064 and SUB-075) and missed names Tesseract read (SUB-067 and SUB-068). It is not a clear replacement. No switch is recommended from this test. A later switch could print a loss-run date that was not on the page, and the citation check would then accept it. This test did not change that rule.
