# D-086 re-check: qwen/qwen3.8-27b after P-038, pass criteria

| Criterion | Result | Needed | Pass |
|---|---|---|---|
| sales on the 9 shared files | 9 of 9 | >= 8 of 9 | PASS |
| silent error rate, 20 files | 1.7% | <= 2.5% | PASS |
| automation rate, 20 files | 77.2% | >= 71% | PASS |

All pass: yes.
Sales on all 20: 18 of 20.
Run: {"model": "qwen/qwen3.8-27b", "stopped_at": null, "files_run": 20, "seconds_per_file": 3.9, "tokens": {"hosts": ["api.groq.com"], "model_calls": 20, "from_cache": 0, "tokens": 31884, "failed_attempts": {"rate_limit_429": 3, "timeout": 0, "other": 7, "reply_not_usable": 0}}, "failed_attempts": {"rate_limit_429": 3, "timeout": 0, "other": 7, "reply_not_usable": 0}}
