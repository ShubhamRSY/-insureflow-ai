# qwen/qwen3.8-27b run-to-run stability on SUB-087–106 (D-085 item 2)

Two uncached runs, same code, development data.

| Field | Run 1 hits | Run 2 hits | Files whose mark changed |
|---|---|---|---|
| named_insured | 19 | 19 | 0: — |
| premises | 14 | 14 | 0: — |
| effective_date | 17 | 17 | 0: — |
| operations | 17 | 17 | 0: — |
| sales | 6 | 6 | 0: — |
| tiv | 17 | 17 | 0: — |
| construction | 18 | 18 | 0: — |
| year_built | 14 | 14 | 0: — |
| loss_runs | 13 | 13 | 0: — |
| **silent error rate** | 1.7% | 1.7% | |
| **automation rate** | 71.7% | 71.1% | |

Marks that changed between runs: 0 of 180.
Run 2: {"model": "qwen/qwen3.8-27b", "stopped_at": null, "files_run": 20, "seconds_per_file": 2.6, "tokens": {"hosts": ["api.groq.com"], "model_calls": 20, "from_cache": 0, "tokens": 31544, "failed_attempts": {"rate_limit_429": 5, "timeout": 0, "other": 0, "reply_not_usable": 0}}, "failed_attempts": {"rate_limit_429": 5, "timeout": 0, "other": 0, "reply_not_usable": 0}}
