# Settings-driven LOB engine — design

- Authors: @ai-engineer-assistant + @software-engineer (written in OpenCode, not independently reviewed). Date: 2026-10-21.
- Status: **design only**. No code, prompt, scorer, lint, gold, inbox or frozen file changed. Implementation needs its own proposal (`P-###`) because it touches extraction and prompts (D-017).
- Inputs: `underwriting_pipeline/ai/{llm_extract,prepare,scope,sources}.py`, `underwriting_pipeline/app/{workbench,package,intake,quotes}.py`, `underwriting_pipeline/ai/eval_holdout_v11.py`, `tests/pipeline/`, `deliverables/pm/lob-roadmap.md`.
- Goal: one shared pipeline; every LOB is a configuration pack (field schema, prompt, scope criteria, operations slots, carrier rules, gold rules, scorer config); today's small-commercial behaviour stays identical.

## 1. Principle

**Config in, behaviour out, defaults equal today.** Every per-LOB value currently hard-coded in a module is moved to a named key in a pack. A resolver returns the pack value, or the current constant when the pack omits it. The `small_commercial` pack is generated from the current constants and is the regression oracle: if the resolved values differ from today's constants, the build fails.

No forks: no `if lob == ...` branches in the pipeline. The only branch is "which pack is loaded", resolved once per submission from the intake manifest.

## 2. What is configurable

| Section | Today's source | Pack key | Notes |
|---|---|---|---|
| Identity | implicit | `id`, `name`, `family`, `states` | `id` is the `InsuranceLine` value |
| Documents | `sources.read_folder` + `scope._kind` | `documents.types`, `documents.application_names`, `documents.schedule_names` | Reader choice stays by file extension; only identification is configured |
| Field schema | `prepare.FIELDS`, `LABELS`, `PLAIN`; `llm_extract` field tuples | `fields[]` with `id`, `label`, `plain`, `kind` (text/number/date/soft/address), `required`, `scored`, `prompt_hint` | Order is preserved; `scored` drives the scorer |
| Prompt | `llm_extract.SYSTEM` + `PROMPT_VERSION` | `prompt.system`, `prompt.version_hint` | The baseline pack stores the exact current `SYSTEM` string, so the sha256 is unchanged |
| Gates | `MIN_CONFIDENCE`, `SCAN_FLOOR`, `REASON_*` | `extraction.gates` | Baseline pack = current numbers |
| Scope criteria | `scope.REASONS`, word lists, `MIN_WORDS`, `UNSURE_RATIO` | `scope.criteria[]`, `scope.words`, `scope.thresholds` | Criteria 1–4 for baseline; extra criteria are additive and off by default |
| Operations slots | `eval_holdout_v11.BT_SYNONYMS`, `prepare` slot rules | `operations.business_types`, `operations.slots`, `operations.unscored_notes` | Wave 1 uses the 22-value closed list |
| Carrier rules | `workbench.CLASSES`, `ALLOW_A`, `REFERRAL`, `PROHIBITED`, `PILOT_TIV`, `CONFIRM` | `routing.carriers[]`, `routing.rules[]`, `routing.prohibited[]`, `routing.tiv_limit` | Rule ids stay stable (`R1`, `R10`, …); the note text is per pack |
| Loss runs | `prepare.CARRIER_RUN_FORMATS`, `carrier_run_check`, `gate_loss_run` | `loss_runs.formats[]`, `loss_runs.required_years`, `loss_runs.review_reasons` | Baseline pack = the three published formats |
| Status | `prepare.STATUSES`, `REFUSED_STATUSES` | `statuses.*` | Closed set stays global; a LOB may not add a status without a decision |
| Gold | `deliverables/senior-underwriter/gold-set`, gold line format | `gold.path`, `gold.lines[]`, `gold.rules[]` | Format stays one line per scored field; per-LOB extra lines are declared |
| Scorer | `eval_holdout_v11` constants | `scorer.version`, `scorer.fields`, `scorer.floors`, `scorer.scope`, `scorer.route` | Frozen scorers are never edited; a new LOB gets a new scorer file generated from the frozen one |
| Evaluation | hold-out ids, targets | `eval.dev_set`, `eval.holdout`, `eval.targets` | Gold-first; 20 in + 12 out for Wave 1 |

## 3. Pack format and loader

New, non-pipeline package:

```
underwriting_pipeline/config/
  lobs/
    small_commercial.json      # generated from today's constants; the oracle
    business_owners_policy.json
    commercial_property.json
    ...
  schema/lob.schema.json       # optional, for review tooling
underwriting_pipeline/ai/lob_config.py   # loader + validator, no business logic
```

`lob_config.load(lob_id)` returns an immutable `LobConfig` with `.get(path, default)` and typed accessors. Rules:

- Unknown `lob_id`, unknown key, missing required key, or a value of the wrong type → `ValueError` (fail closed). No silent fallback to another LOB.
- `LobConfig.fingerprint()` hashes the canonical JSON. It is written into the saved run, the cache key and the score file, so a report can always say which pack produced it.
- The pack is resolved from the submission's `lob` field in the intake record; an older submission with no `lob` resolves to `small_commercial`.
- A per-LOB override file is not allowed; the pack is the only source.

### Baseline pack generation

A one-off, reviewed script (`underwriting_pipeline/ai/lob_config_snapshot.py`, run by hand, output committed) reads the current constants and writes `small_commercial.json`. A test then asserts:

```python
assert lob_config.load("small_commercial").raw == snapshot_from_modules()
assert llm_extract.prompt_for("small_commercial") == llm_extract.SYSTEM  # exact string, same sha
```

That test is the behaviour guarantee for Wave 1.

## 4. Exactly which files change

### New files

| File | Purpose |
|---|---|
| `underwriting_pipeline/ai/lob_config.py` | Load, validate, fingerprint packs; `pack_for(submission)`; no business rules |
| `underwriting_pipeline/ai/lob_config_snapshot.py` | Generate `small_commercial.json` from current constants (reviewed, run manually) |
| `underwriting_pipeline/config/lobs/*.json` | One pack per LOB |
| `underwriting_pipeline/ai/eval_lob.py` | Generic per-LOB scorer; imports the frozen v11 pure functions, never edits them |
| `underwriting_pipeline/ai/lint_lob.py` | Per-LOB gold lint, using the pack's gold rules |
| `tests/pipeline/test_lob_config.py` | Loader, validation, fingerprint, baseline equality |
| `tests/pipeline/test_lob_regression.py` | Cached-run regression per LOB |
| `tests/pipeline/test_lob_routing.py` | Routing truth table from the pack |

### Changed files (behaviour-preserving for `small_commercial`)

| File | Change | Guard |
|---|---|---|
| `underwriting_pipeline/ai/llm_extract.py` | `SYSTEM` becomes `cfg.prompt.system`; field tuples from `cfg.fields`; cache key adds `lob` + pack fingerprint + prompt version | Baseline prompt string identical; cache key change is additive |
| `underwriting_pipeline/ai/prepare.py` | `FIELDS`, `LABELS`, `PLAIN`, required set, completeness, cooking/loss-run rules and status from the pack | Baseline pack equals current tuples; saved runs keep their own field list |
| `underwriting_pipeline/ai/scope.py` | Criteria, word lists and thresholds from the pack; `VERSION` becomes `scope-v4+<pack>` | Baseline criteria and words identical |
| `underwriting_pipeline/ai/sources.py` | Only the document identification hooks used by `scope`; reader selection unchanged | No new reader in Wave 1 |
| `underwriting_pipeline/app/workbench.py` | Routing tables, TIV limit and note text from the pack; `match(report, cfg=None)` resolves by `report["lob"]`, default baseline | Baseline truth table identical (the self-check block already has it) |
| `underwriting_pipeline/app/package.py` | Carrier set, package labels and required-field list from the pack | Baseline body identical except the LOB label line |
| `underwriting_pipeline/app/intake.py` | Store `lob` in the intake record; default `small_commercial` | Existing records unchanged |
| `underwriting_pipeline/app/workbench.html` | Nothing structural; the LOB label is rendered by Python | Snapshot test |
| `tests/pipeline/conftest.py` | Load the baseline pack for every test | All 43 existing tests stay green |

### Explicitly not changed

- `eval_holdout_v11.py` and all older frozen scorers: read-only imports only.
- Published gold, hold-out gold, score files, lint hash and the T-117 manifest.
- `simulation/inbox/**` and `simulation/carrier-loss-run-formats.md`.
- Any `P-###`-governed prompt text for the baseline line: the string is moved, not edited.

## 5. Migration steps (each one lands green)

| Step | Work | Tests that must pass |
|---|---|---|
| 0 | Freeze the baseline: record code SHA, tests/pipeline 43 green, workbench self-check, `eval_holdout_v11 --check-gold`, T-117 score hashes | All of the above; nothing written |
| 1 | Add `lob_config.py` + schema + snapshot script; commit `small_commercial.json` | `test_lob_config`: load, fail-closed on unknown key/LOB, fingerprint stable, raw equality to module constants |
| 2 | Thread the pack through `prepare.py` field schema and required set | Existing `tests/pipeline` green; a no-call replay of the T-117 cache produces identical reports (status, conflicts, fields) |
| 3 | Thread the prompt and field gates through `llm_extract.py` | Baseline prompt sha256 unchanged; cache key for one cached file resolves to the same saved reply; no model call |
| 4 | Thread scope criteria and words | `test_scope` green, SUB-233 still `multiple_locations`, baseline reasons byte-identical |
| 5 | Thread routing and TIV limit | Workbench self-check block green, `test_routing` green, a 20-file route snapshot identical |
| 6 | Thread package labels and intake `lob` | `test_send_gates` green; package body differs only by the new LOB label line, asserted by snapshot |
| 7 | Add `eval_lob.py` (generic scorer) | Re-score the T-117 cached run with `eval_lob --lob small_commercial` and compare every mark in the published JSON: 0 differences |
| 8 | Add `lint_lob.py` and per-LOB gold paths | Baseline lint hash unchanged; a new LOB lint fails on an empty pack |
| 9 | Repeat steps 2–8 for the next LOB only when its spec and gold exist | Per-LOB regression + lint; no shared test changes |

Rollback: the loader returns the baseline pack when `LOB_ENGINE=off` (one environment variable, default off until step 7 passes). Turning it on is a separate commit with the full regression output attached.

## 6. How each step is tested

- **No model calls.** Every migration test replays saved replies from a temp cache copy (`LLM_CACHE_DIR`) or reads saved runs; `llm_extract._post` raises if called (D-069 pattern).
- **Golden equality** for the baseline: resolved config == module constants; prompt sha == `759b3e6bc9b2`; route truth table == the self-check block; score marks == T-117 JSON.
- **Fail-closed tests**: unknown LOB, unknown key, missing required field, malformed regex, pack with a status outside the closed set — all raise before any extraction.
- **Isolation**: every test uses `tmp_path`; no write to `simulation/`, `deliverables/**`, `team/`, the real cache or the token log.
- **Per-LOB acceptance**: `python -m pytest tests/pipeline -q` stays green; a LOB counts as built only after its own gold-first hold-out and the gates in `deliverables/lobs/test-plan.md`.
- **Diff discipline**: each step is one commit; `git diff` on frozen files is empty; `git status` clean after the test run.

## 7. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Prompt string drift when moving it into JSON | Byte-for-byte snapshot test and sha256 comparison; JSON stores the string, not a re-rendered template |
| Cache key change forces re-extraction | Add `lob`/fingerprint as new key components; keep the old key path for `small_commercial` until the frozen run is re-scored, then cut over in one commit |
| A LOB pack quietly changes baseline behaviour | Default resolver returns baseline; `LOB_ENGINE=off` rollback; all 43 existing tests plus route/score snapshots |
| Scorer forks | `eval_lob.py` imports frozen pure functions; no copy of scoring logic; frozen files untouched |
| Gold format divergence | Gold lines are declared in the pack and linted before a run; an undeclared line is a lint error |
| Too many packs become a second codebase | Packs hold data only: no expressions, no code strings; a validator rejects keys named `code`, `eval`, `exec` |
| LOB resolved wrongly for an old submission | Missing `lob` → `small_commercial`; the saved run records the resolved pack fingerprint |

## 8. Open questions for the user

1. Approve the config-first approach and the `LOB_ENGINE=off` rollback, or prefer a hard cutover per LOB.
2. Approve that the baseline prompt string is moved to a pack unchanged (still needs `approve change P-###` before implementation, because it touches the prompt file).
3. Decide whether `commercial_package` shares the `business_owners_policy` pack with two coverage flags, or gets its own pack.
4. Decide whether per-LOB gold lives under `deliverables/senior-underwriter/gold-set-<lob>/` naming, or a single `gold-set/` with a `lob` column.
