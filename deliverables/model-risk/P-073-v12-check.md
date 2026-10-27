# P-073 scorer v12: @model-risk check (D-126, High only)

- Reviewer: @model-risk (independent, fresh dispatch). Date: 2026-10-23. Worktree `insureflow-integration`, branch `pilot-integration`, uncommitted.
- Read: `diff eval_holdout_v11.py eval_holdout_v12.py`, `operations-gold-rule.md`, `P-073-v12-as-built.md`, `P-073-v12-lint.txt`, `P-073-v12-dev-rescore.json`, D-124, D-126, my `T-118-recheck.md`. I did not read the author's messages or the task Notes.
- Ran (temp copy, D-069; LLM_* unset; 0 model calls): v12 `--self-check` ok; sha256 of v11, v12, frozen lint and the lint wrapper match the as-built; v11 and the frozen lint have no diff against HEAD. I wrote 45 probe answers against gold `no cooking; 48 seats` and scored each with v11 and v12 `ops_items_hit`.
- **Not a production approval.** An approved P-073 is not a production approval, and the T-027 veto stands.

## Verdict: BLOCK. Do not freeze v12.

## High finding

### H1: v12 scores cooking-present answers as "no cooking" hits (the T-118 H1 class, now in the scorer)
v12 (a) reads an answer that leaves cooking out as `none` unless a fixed word list finds "cooking evidence". Answers that clearly state cooking get credit when they use words outside the list, sit in a clause with a tenant word, or have an unrelated negation nearby. v11 scored every one of these as a miss, so v12 makes them wrong hits. 23 of my 45 probes went from miss to hit. D-126 requires that "every wrong answer [is] caught", including "cook/stove/fry/hot food" sentences. The v12 header also claims that "A cooking-present answer against gold none is a miss, as in v11." Both are false for these answers:

| Answer (gold `no cooking; 48 seats`) | v11 | v12 | Cause |
|---|---|---|---|
| "…; the tenant now runs a small cafe serving hot food prepared on site" (the T-118 H1 sentence) | miss | **hit** | a clause with `tenant`/`residents` is skipped entirely |
| "…; tenants fry chicken wings for customers" | miss | **hit** | same |
| "…; broiler" / "salamander broiler" / "rotisserie" / "panini press" / "sandwich press" / "tandoor" / "steamer" / "toaster" / "waffle iron" / "sous vide" / "tilt skillet" / "heat lamp" | miss | **hit** | word not in the list |
| "…; heats soup" / "boils water for pasta" / "makes pancakes on a skillet" / "hotdogs" | miss | **hit** | word not in the list |
| "…; no beer we fry wings" / "wings fried daily and beer none" | miss | **hit** | negation within 3 words before, or "none" at the end of the clause, voids an unrelated cooking word |

This is the same class of failure as T-118 H1. Silence on cooking is read as "no cooking", and the only thing that decides silence is an open word list. In the scorer it inflates the cooking slot and the operations score exactly where the model wrongly adds cooking to a no-cooking file. The lint passes only because its wrong cases are taken from the same list.

**Resolves when** (needs a new P-### and the user's `approve change P-###`; v12 is not frozen until then):
1. The tenant exemption applies only inside a clause that itself states "no cooking" (the row-7 pattern "no cooking operations (tenant electric ranges only)"). A tenant clause anywhere else is read like any other clause.
2. Negation voids a cooking word only when the negation governs that word. A "no X" for a different slot, or a clause-final "none"/"no" after another slot's word, does not void it.
3. The evidence list is widened and reviewed by @senior-underwriter. At minimum it adds broil*, rotisserie, press (panini/sandwich), toast*, steam*, skillet, tandoor, sous vide, waffle, heat lamp, heat*/heated, boil*, hotdog*, warming, and the light-cooking words. Or it fails closed: an omitted cooking slot is credited only when every clause of the answer is accounted for by a known slot, the business class, or a reviewed list of non-cooking words.
4. Every probe in the table becomes a lint and self-check wrong answer (expected miss), and the lint still scores perfect answers at 100%. A dev re-score shows no new hit outside the four expected flips (SUB-246/248/250/257).

## Below High (backlog, one line each)
- M1: The gold rule still says "A slot gold states and the answer omits is a miss" (line 67) and "Absence is a value, never a drop" (line 66). D-126 now credits omission for gold `no cooking`. @senior-underwriter adds a D-126 amendment line so the rule and the scorer agree.
- M2: The dev re-score left out 30 of the 170 ids because no reply was cached. These include SUB-290–296, which covers SUB-293/296, the files behind H1. The re-score does not reach the cases P-073 exists for.
- L1: The four flips (SUB-246/248/250/257) are correct under D-126. Gold-full cards are unchanged (12/12). v11 credited "fryer: yes, alcohol: no" as "no cooking" and v12 fixes it.
- L2: v11 is frozen and unchanged (sha256 7ddcfb50…), and the frozen lint is unchanged (01147a75…). The v12 diff is limited to the cooking slot and version labels, as stated.
