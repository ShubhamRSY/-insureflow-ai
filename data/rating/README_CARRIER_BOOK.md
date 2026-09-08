# Carrier book import template

Replace the example rows in `carrier_book_import_template.csv` with your carrier’s filed leaf rates, then:

```bash
PYTHONPATH=src python scripts/ops/import_carrier_filings.py \
  --csv data/rating/carrier_book_import_template.csv \
  --carrier "Your Carrier"
```

Or `POST /rating/carrier-book` with the CSV/JSON body.

A successful import sets `posture=carrier_imported` so the bind cutover checklist `carrier_book` step goes green. The bundled pilot synthetic book does **not** count as a customer SERFF book.
