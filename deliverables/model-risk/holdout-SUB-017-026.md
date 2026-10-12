# Hold-out result — SUB-017 through SUB-026

- Author: @model-risk
- Date: 2026-10-09
- Decision: not a production approval. The earlier 100% score is not evidence.
- prepare.py sha256 before and after this run: `5d51f7c07617a882bb9cef66b5f6e2787e7d4dc8265cd691eb28e9ff5e412e4c`

I re-read `deliverables/ai-engineer/evals/SUB-017-026-holdout.md`. I did not ask anyone to change the extractor before the score.

## What failed

Named insured, premises, operations, sales, TIV, construction, and year built are 0/10. The extractor only opens `.md` and `.csv`. It did not open the text PDFs, the scanned-style PDFs, or the Excel schedules. It also did not read English prose in an email body, or Spanish labels (`Asegurado`, `Direccion del local`, `Ventas anuales`).

The same miss hits a clean office and a Spanish nightclub. Failure here is "file not read," not a risk difference.

## Hits that are not success

- Loss runs 4/10. Those four gold lines say the runs are missing, and the extractor stored null because it never opened the file.
- Conflicts 8/10. Eight gold lines say there is no conflict. An empty extract has nothing to disagree with. SUB-022 (two addresses) and SUB-024 (3,000 vs 4,500 square feet) were missed.
- Status 5/10. The five incomplete gold files look incomplete when every field is null. The five complete gold files were scored incomplete.

## Finding

High. Do not quote the old 100% as proof. The gold, the code, and the first ten files were written together, and those files used the labels the code searches for.

What would close it: teach the extractor to read PDF text, a scanned page, xlsx, an unlabeled email, and Spanish labels; freeze prepare.py again; score a new hold-out the same way; and do not count a null as a hit when the gold value sits in a file the code did not open.

## Not a veto of the desk

Showing the failed extract on the workbench is acceptable. Sending the producer a request for facts already in the PDF would be the wrong fix. No carrier package was sent.
