# Canonical data model (draft)

- Author: @data-engineer
- Date: 2026-10-09
- Status: Draft for review (T-004)
- Maps to `deliverables/senior-underwriter/required-fields.md`
- Extraction from @ai-engineer must land in `FieldObservation`, not in a free-text blob.

## Entities

```
Submission 1 ── * Document
Submission 1 ── * Location
Submission 1 ── * Loss
Submission 1 ── 1 Decision
Location   1 ── * FieldObservation
Document   1 ── * FieldObservation
Submission 1 ── * FieldObservation
```

| Entity | Key | Holds |
|---|---|---|
| Submission | submission_id | Insured legal name (restricted), effective date, operations text, producer. Not a rating class. |
| Document | document_id | Type: `acord_125`, `acord_126`, `acord_140`, `sov`, `loss_run`, `nkl_letter`, `other`. Hash, page count. |
| Location | location_id | Premises address, TIV building, TIV BPP, construction, year built, protection class, sprinkler, unit count. |
| Loss | loss_id | Date, amount, coverage part, open flag. Exists only when a loss-run span supports it. |
| FieldObservation | observation_id | field_id, value (nullable), source document, page, span, confidence, model version. |
| Conflict | conflict_id | field_id, the observation ids that disagree. |
| Decision | decision_id | Band, rule ids, human id, timestamp, prompt/rule version. Premium only if the band is quote and the rating system wrote it. |

## Null rule

`value = null` means missing. `value = 0` is a real zero and requires a span on a `loss_run`, not on an `nkl_letter`. Loss count is the number of `Loss` rows. It is never defaulted.

If two observations of the same field_id disagree, write a `Conflict` and do not pick a winner. Each side keeps its value and its source document. `resolution` is `unresolved` until a later document names the winner; then `resolved_value` and `resolved_by` are filled and both original values stay. Square feet are compared on digits, so `2,200 sq ft` and `2200` are one observation. The producer email is not the record. Latest run: `deliverables/data-engineer/extractions/` and `conflicts/`.

## Field ids (required-field list)

`named_insured`, `premises_address`, `effective_date`, `operations`, `class_code` (human-confirmed; model may only write `class_code_suggested`), `sales_or_payroll`, `tiv_building`, `tiv_bpp`, `construction`, `year_built`, `protection_class`, `sprinkler`, `loss_run_valued_through`, `liquor_receipts_pct`, `roofing_receipts_pct`, `unit_count`, `subsidized`, `student_housing`.

## What stays out of the decisioning table

Person first/last name as a feature, owner credit, criminal history, web text, ZIP used as a socioeconomic score. ZIP may exist on the location only to apply S-07 (coastal list) and the filed territory rate.

Protected-class attributes are not collected for underwriting. If @responsible-ai needs a fairness test, that is a separate access-controlled extract, not a column on `Decision`.
