# Canonical data model (draft)

- Author: @data-engineer
- Date: 2026-10-09
- Status: Draft for review (T-004)
- Revised: 2026-10-13 (T-069 review findings closed: H1/H2 exact `saved_hash` bytes, High-1 gate keys, M1 `status`/`error` enums, M2 reader path and `hash_algorithm` mismatch)
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

## ExtractionRun (saved extraction report)
Extraction results for a submission are written to `deliverables/data-engineer/extractions/SUB-xxx.json` by the drafts writer (`underwriting_pipeline/ai/prepare.write_drafts()`) at save time. The saved run is the only input the G2 send gate and the workbench card read for a gate decision; they never re-run `process_submission()` for it. The report must include:

| Key | Type | Required | Notes |
|---|---|---|---|
| `submission` | string | yes | Submission id (e.g., `SUB-001`). |
| `status` | enum | yes | Closed enum, mapped to the writer's values: `complete`, `incomplete`, `extraction_failed`, `all_values_rejected`. `complete`/`incomplete` are the writer's current values (`prepare.py:596`); `extraction_failed` means no usable model result (D-021); `all_values_rejected` means the model answered but every value was rejected by the gates (D-024). `needs_human` is **not** a status — it is the list key below. |
| `error` | enum\|null | yes | Closed enum, non-null **only** when `status` is `extraction_failed`: one of `rate_limit_429`, `timeout`, `reply_not_usable`, `call_error`. `null` for `complete`, `incomplete`, and `all_values_rejected` (D-024 — no call failed). Never model or document text (S-01 minimization). An unreadable cache file is not terminal: P-013 (D-027) treats it as not cached and retries, so it never reaches `extraction_failed`. |
| `saved_hash` | string | yes | Lowercase hex digest of the canonical bytes defined under "The `saved_hash` bytes" below, computed once at save time (G2, D-029). |
| `hash_algorithm` | enum | yes | Closed enum with one value today: `sha256`. Any other value (or a missing/null value) is refused by the reader (see "Reader contract"). |
| `complete` | boolean | yes | Gate input: `agency_problem()` refuses when falsy (`package.py:46`). |
| `conflicts` | array | yes | Each item has `field`, `values`, and `resolution`; an item with `resolution != "resolved"` is open and blocks a send (`package.py:41-45`); the workbench renders it (`workbench.py:172-181`). |
| `needs_human` | array | yes | One entry per unread page/document; non-empty blocks a send (`package.py:39-40`) and is shown on the card (`workbench.py:198`). Distinct from any `status` value. |
| `sprinklers` | enum | yes | `yes` or `no` (`prepare.py:591`); `workbench.route()` reads it (`workbench.py:45`). |
| `model_version` | string\|null | yes | Model identifier used for this run (or `null` if no model call). |
| `prompt_version` | string\|null | yes | Prompt/version identifier used (or `null` if not applicable). |
| `ocr_settings` | object\|null | yes | OCR/rotation/deskew settings in effect (or `null` if not applicable). |
| `host` | string\|null | yes | LLM host/base URL used (or `null` if no model call). |
| `temperature` | number\|null | yes | Temperature used (or `null` if no model call). |
| `fields` | array | yes | Field observations as currently defined (each with `field_id`, `value`, `source`, spans/confidence as applicable). `workbench.route()` reads the `operations` value from it (`workbench.py:33-34`). |

As-is, `write_drafts()` writes only `submission`, `fields`, and `conflicts` (`prepare.py:651-657`). T-070 adds the remaining keys; until it does, no saved run can feed the gate — this is the P-010/G2 gap (@compliance T-020 H2).

### The `saved_hash` bytes (H1, H2)
`write_drafts()` computes `saved_hash` over the report payload **with `saved_hash` and `hash_algorithm` removed**, then writes those two keys into the file. The hash is computed once, before the write. The exact bytes:

1. Take the payload object — every key in the table above **except** `saved_hash` and `hash_algorithm`.
2. Serialize it with `json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)`. `sort_keys=True` sorts nested object keys too, so producer key order is irrelevant; UTF-8 encoding of that ASCII string is the byte string hashed.
3. Hash those bytes with the algorithm named in `hash_algorithm` (`sha256`).
4. Store `saved_hash` as the lowercase hex digest.

The on-disk file is **not** itself canonical: indentation and key order in the file do not matter. To verify, load the file as JSON, drop the two hash keys, re-serialize by the rule above, hash, and compare.

### Reader contract (High-1, Medium-2)
- **Path:** the G2 gate and the workbench card read the last saved run at `deliverables/data-engineer/extractions/SUB-xxx.json`. They do not call `process_submission()`; the `workbench.py:86` call is the as-is live path, not the gate path. `write_drafts()` writes every key in the table.
- **Nothing saved:** if there is no saved file, refuse.
- **Hash check (G2, D-029):** load the saved JSON, recompute the digest from the canonical bytes above, and refuse if it differs from `saved_hash`.
- **`hash_algorithm` mismatch:** `sha256` is the only accepted value. If `hash_algorithm` or `saved_hash` is missing, empty, or not a string; if `hash_algorithm` is any value other than `sha256`; or if the recomputed digest does not match, the reader refuses (fail closed). It never guesses an algorithm.

**Ownership:** Extraction writer (`prepare.write_drafts()`) writes all metadata at save time. Gate readers (`underwriting_pipeline/app/package.py`, `underwriting_pipeline/app/workbench.py`) read `status`, `error`, `saved_hash`, `hash_algorithm`, and metadata to enforce gates (including G2 hash equality), reading them from the saved run. No PII beyond what fields already contain; metadata is operational/audit only.

**Retention/access (Low-2):** the file holds the insured legal name and field values, so retention and access control are @compliance's to set; recorded here as open, to the backlog per D-030. This task makes no code changes (documentation only).
