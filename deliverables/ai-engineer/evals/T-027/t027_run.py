"""T-027 official hold-out driver. Pipeline files are untouched; this only limits retries at run time (user rule, 2026-10-15):
a rate-limit (429) or network/timeout failure may be posted again once; anything else is not resent and is "call failed".
Outer regression_dev retry (3 attempts on any error) is replaced by one attempt. Each file's report is saved here for route/loss-run reporting.

Run: .venv/bin/python <this> [--self-check]
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

AI = Path(__file__).resolve().parent
ROOT = Path("/Users/disastershubz/INSURANCE FLOW AI/-insureflow-ai-1")
sys.path.insert(0, str(ROOT / "underwriting_pipeline" / "ai"))
import llm_extract  # noqa: E402
import prepare  # noqa: E402
import regression_dev as rd  # noqa: E402

OUT = AI / "t027"
OUT.mkdir(exist_ok=True)
S = {"failures": 0, "last": None, "retried": False, "posts": 0}
GUARD_LOG: list[dict] = []
_real_urlopen, _real_failed, _real_log_tokens = urllib.request.urlopen, llm_extract._failed, llm_extract._log_tokens


def retryable(kind: str, detail: str) -> bool:
    return kind in ("rate_limit_429", "timeout") or (kind == "other" and not detail.startswith("HTTP "))


def guarded_urlopen(*a, **k):
    if S["failures"]:
        if S["retried"] or not S["last"] or not retryable(*S["last"]):
            GUARD_LOG.append({"refused_after": S["last"]})
            raise RuntimeError(f"model call failed: not sent again (T-027 run rule) after {S['last'][0] if S['last'] else '?'}")
        S["retried"] = True
    S["posts"] += 1
    return _real_urlopen(*a, **k)


def failed(settings, kind, detail, *a, **k):
    S["failures"] += 1
    if kind != "retry":  # the HTTP 400 resend marker keeps the HTTP 400 as the cause
        S["last"] = (kind, detail)
    return _real_failed(settings, kind, detail, *a, **k)


def log_tokens(*a, **k):
    S.update(failures=0, last=None, retried=False)
    return _real_log_tokens(*a, **k)


def reset():
    S.update(failures=0, last=None, retried=False, posts=0)


def score_once(module, sid: str, score=None) -> dict:
    """regression_dev.score_retry with one attempt (pacing, split_review_hits and value_metrics unchanged)."""
    if rd.PACE and rd._started and time.monotonic() - rd._started[-1] < rd.PACE:
        time.sleep(rd.PACE - (time.monotonic() - rd._started[-1]))
    rd._started.append(time.monotonic())
    score = score or module.score_one
    seen, real = [], prepare.process_submission
    prepare.process_submission = lambda *a, **k: seen.append(real(*a, **k)) or seen[-1]
    reset()
    try:
        row = score(sid)
    finally:
        prepare.process_submission = real
    rep = seen[-1] if seen else None
    (OUT / f"{sid}.json").write_text(json.dumps({"posts": S["posts"], "report": rep}, indent=2, default=str))
    row = {**row, "checks": rd.split_review_hits(row["checks"], rep), "metrics": rd.value_metrics(row["checks"], rep)}
    print(time.strftime("%H:%M"), sid, row.get("error") or "ok", "posts", S["posts"], flush=True)
    return {**row, "attempts": 1}


def install():
    urllib.request.urlopen = guarded_urlopen
    llm_extract._failed, llm_extract._log_tokens = failed, log_tokens
    rd.score_retry = score_once


def _self_check():
    """Simulate posts: each item is "ok" or a (kind, detail) failure, applied as _post would (via failed / log_tokens state)."""
    global _real_urlopen
    for seq, want_posts, refused in (([("rate_limit_429", "x"), "ok"], 2, False), ([("timeout", "x"), ("timeout", "x"), "ok"], 2, True),
                                     ([("other", "HTTP 400 bad"), "ok"], 1, True), ([("other", "URLError reset"), "ok"], 2, False),
                                     (["ok", "ok"], 2, False)):
        reset()
        it = iter(seq)

        def fake(*a, **k):
            kind = next(it)
            if kind == "ok":
                S.update(failures=0, last=None, retried=False)
            else:
                S.update(failures=S["failures"] + 1, last=kind)
        _real_urlopen = fake
        got_refused = False
        for _ in seq:
            try:
                guarded_urlopen()
            except RuntimeError:
                got_refused = True
                break
        assert (S["posts"], got_refused) == (want_posts, refused), (seq, S, got_refused)
    assert retryable("other", "URLError") and not retryable("other", "HTTP 500") and not retryable("reply_not_usable", "")
    print("t027 guard self-check ok")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--self-check"]:
        _self_check()
        sys.exit(0)
    install()
    llm_extract.provider_guard(calling=False)
    rd.holdout("eval_holdout_127")
