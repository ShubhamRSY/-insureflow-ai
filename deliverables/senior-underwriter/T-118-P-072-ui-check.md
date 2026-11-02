# T-118 / P-072 UI check (D-065, D-124)

Author: @senior-underwriter, 2026-10-23. Underwriter's view of the two screenshots (`T-118-document-conflicts.png` SUB-292, `T-118-no-cooking-cited.png` SUB-293), the render script and the What's new list. Screenshots only; no run. FICTIONAL files.

## Verdict: APPROVE (no High)

What works, in my terms:
- SUB-292: three open conflicts are named in plain words with both values, the document each came from and the cited text. "OPEN: no send until the underwriter chooses or enters the value" and the red send refusal say the same. I know what to do next and why I cannot send.
- SUB-293 and SUB-292: "Cooking operations: None" no longer turns into a stated "no cooking". Operations keeps the value as written, confidence 0.74, review note, and an acknowledge box before approve. That is the right behaviour: I check cooking against every document myself.
- The What's new line (2026-10-23, T-118 P-072, D-124) says what changed in plain words.
- The render script writes to a temporary folder only (D-069).

## High
None.

## Medium / Low (one line each, backlog)
- M1: the review note "operations may be missing: no cooking" reads as a finding ("no cooking"). Say "cooking not confirmed - check the documents".
- M2: the line "Cooking: not scored - no cooking equipment stated in the file" sits beside a note that cooking may be missing; it reads as "no cooking". Say "cooking not stated - not scored".
- M3: send block shows "Account-manager check: refused, the saved extraction run for this file cannot be read." This is a render artefact (synthetic card without a saved run) and would confuse a reader of the screenshot; label it in the script or use a real run copy.
- L1: "Resolve suite count" row wraps differently from the other two resolve rows (layout only).
- L2: SUB-292 sales_or_payroll shows "—" at 0.0 while the cited text says $412,000; fine because the conflict card shows both, but a note "see conflict" in the Review note column would help.
