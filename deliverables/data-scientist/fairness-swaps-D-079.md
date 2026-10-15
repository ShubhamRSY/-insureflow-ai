# Name and cuisine swap tests (D-077, rerun under D-079)

- Orchestrator, main session, 2026-10-14. D-077 items 1 and 2. Synthetic. Not a production approval. Does not replace the @responsible-ai check of P-015 (B-270).
- No model call (`llm_extract._post` raised); a scratch copy of the cache; no real workbench, log or outbox file written; no rule, prompt, scorer or score file changed.
- Cached files tested (SUB-001 to SUB-076 with a cached reply): 63. Carry a score (a number, not Not scored or Provisional): 27 (002, 009, 010, 017, 018, 021, 025, 026, 027, 028, 031, 035, 036, 037, 038, 041, 045, 046, 047, 048, 051, 055, 056, 059, 061, 069, 071).
- Business-name swap: 36 files × 11 names. Person-name swap: 2 files × 10 names. Cuisine swap: 3 restaurant files × 8 words.
- Compared for name swaps: status, scored, points, codes, the three display lines, needs-review ids, carrier route. For cuisine swaps (D-078): scored, points, codes, cooking line, status and carrier route must not change; a needs-review change is reported apart (see the D-077 note on the model-added-word artifact).
- **Findings that break the rule (any change from a name swap; score, cooking, status or carrier route from a cuisine swap): 0.** Cuisine swaps that changed only a needs-review flag: 0.

## What this tests and what it does not

- Tested: every rule after the model, with the cached model reply edited the same way as the text. Not tested: whether the model itself would read a different name or cuisine differently; that needs model calls.
- The files name no owner. The only person names are email senders on "From:" lines (producers), so the person swap uses those.
- Names or cuisine words inside a scan or PDF cannot be edited; such a file is skipped for that test, and in a mixed file items cited to a scan keep their text.

## Findings

None.

## Skipped

- SUB-010 (person): no person name in md/csv text
- SUB-017 (business): name only in a scan or PDF
- SUB-017 (person): no person name in md/csv text
- SUB-018 (business): name only in a scan or PDF
- SUB-018 (person): no person name in md/csv text
- SUB-019 (person): no person name in md/csv text
- SUB-020 (person): no person name in md/csv text
- SUB-021 (person): no person name in md/csv text
- SUB-022 (business): name only in a scan or PDF
- SUB-022 (person): no person name in md/csv text
- SUB-023 (business): name only in a scan or PDF
- SUB-023 (person): no person name in md/csv text
- SUB-024 (person): no person name in md/csv text
- SUB-025 (person): no person name in md/csv text
- SUB-026 (business): name only in a scan or PDF
- SUB-026 (person): no person name in md/csv text
- SUB-027 (business): name only in a scan or PDF
- SUB-027 (person): no person name in md/csv text
- SUB-028 (business): name only in a scan or PDF
- SUB-028 (person): no person name in md/csv text
- SUB-029 (person): no person name in md/csv text
- SUB-030 (person): no person name in md/csv text
- SUB-031 (person): no person name in md/csv text
- SUB-032 (business): name only in a scan or PDF
- SUB-032 (person): no person name in md/csv text
- SUB-033 (person): no person name in md/csv text
- SUB-034 (person): no person name in md/csv text
- SUB-035 (person): no person name in md/csv text
- SUB-036 (business): name only in a scan or PDF
- SUB-036 (person): no person name in md/csv text
- SUB-037 (business): name only in a scan or PDF
- SUB-037 (person): no person name in md/csv text
- SUB-038 (business): name only in a scan or PDF
- SUB-038 (person): no person name in md/csv text
- SUB-039 (person): no person name in md/csv text
- SUB-040 (person): no person name in md/csv text
- SUB-041 (person): no person name in md/csv text
- SUB-042 (person): no person name in md/csv text
- SUB-043 (business): name only in a scan or PDF
- SUB-043 (person): no person name in md/csv text
- SUB-044 (person): no person name in md/csv text
- SUB-045 (person): no person name in md/csv text
- SUB-046 (business): name only in a scan or PDF
- SUB-046 (person): no person name in md/csv text
- SUB-047 (business): name only in a scan or PDF
- SUB-047 (person): no person name in md/csv text
- SUB-048 (business): name only in a scan or PDF
- SUB-048 (person): no person name in md/csv text
- SUB-049 (person): no person name in md/csv text
- SUB-050 (person): no person name in md/csv text
- SUB-051 (person): no person name in md/csv text
- SUB-052 (person): no person name in md/csv text
- SUB-053 (business): name only in a scan or PDF
- SUB-053 (person): no person name in md/csv text
- SUB-054 (person): no person name in md/csv text
- SUB-055 (person): no person name in md/csv text
- SUB-056 (person): no person name in md/csv text
- SUB-057 (person): no person name in md/csv text
- SUB-058 (business): name only in a scan or PDF
- SUB-058 (person): no person name in md/csv text
- SUB-059 (person): no person name in md/csv text
- SUB-060 (person): no person name in md/csv text
- SUB-061 (business): name only in a scan or PDF
- SUB-061 (person): no person name in md/csv text
- SUB-062 (person): no person name in md/csv text
- SUB-063 (person): no person name in md/csv text
- SUB-064 (business): name only in a scan or PDF
- SUB-064 (person): no person name in md/csv text
- SUB-065 (business): name only in a scan or PDF
- SUB-065 (person): no person name in md/csv text
- SUB-066 (person): no person name in md/csv text
- SUB-067 (business): name only in a scan or PDF
- SUB-067 (person): no person name in md/csv text
- SUB-068 (business): name only in a scan or PDF
- SUB-068 (person): no person name in md/csv text
- SUB-069 (person): no person name in md/csv text
- SUB-070 (person): no person name in md/csv text
- SUB-071 (business): name only in a scan or PDF
- SUB-071 (person): no person name in md/csv text
- SUB-072 (person): no person name in md/csv text
- SUB-073 (person): no person name in md/csv text
- SUB-074 (business): name only in a scan or PDF
- SUB-074 (person): no person name in md/csv text
- SUB-075 (business): name only in a scan or PDF
- SUB-075 (person): no person name in md/csv text
- SUB-076 (person): no person name in md/csv text
