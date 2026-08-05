#!/usr/bin/env python3
"""Concurrent HTTP load test against a running InsureFlow instance.

Stdlib-only so it runs anywhere (including inside the container). Hammers
lightweight endpoints (/health, landing page, auth status) and reports
latency percentiles plus the error rate.

Usage:
    python scripts/ops/load_test.py --base http://localhost:8000 \
        --requests 500 --concurrency 20 --max-error-rate 0.01

Exits 0 when the error rate stays under --max-error-rate, else 1.
"""

from __future__ import annotations

import argparse
import statistics
import sys
import threading
import time
import urllib.error
import urllib.request

ENDPOINTS = ("/health", "/", "/auth/status")


def _fetch(url: str, timeout: float) -> tuple[float, int]:
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            resp.read()
            return (time.perf_counter() - start, resp.status)
    except urllib.error.HTTPError as exc:
        exc.read()
        return (time.perf_counter() - start, exc.code)


def _worker(base: str, results: list[tuple[float, int]], queue: list[int], lock: threading.Lock, timeout: float) -> None:
    urls = [f"{base}{ep}" for ep in ENDPOINTS]
    while True:
        with lock:
            if not queue:
                return
            queue.pop()
        url = urls[len(results) % len(urls)]  # round-robin spread across endpoints
        try:
            lat, status = _fetch(url, timeout)
        except urllib.error.URLError as exc:
            with lock:
                results.append((timeout, 0))
            print(f"  error: {url}: {exc}", flush=True)
            continue
        with lock:
            results.append((lat, status))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://localhost:8000", help="Base URL of the API")
    parser.add_argument("--requests", type=int, default=500, help="Total requests to send")
    parser.add_argument("--concurrency", type=int, default=20, help="Concurrent worker threads")
    parser.add_argument("--timeout", type=float, default=10.0, help="Per-request timeout (seconds)")
    parser.add_argument("--max-error-rate", type=float, default=0.01, help="Fail if error rate exceeds this")
    args = parser.parse_args()

    queue: list[int] = list(range(args.requests))
    lock = threading.Lock()
    results: list[tuple[float, int]] = []

    threads = [threading.Thread(target=_worker, args=(args.base, results, queue, lock, args.timeout)) for _ in range(args.concurrency)]
    started = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.perf_counter() - started

    if not results:
        print("No requests completed — is the server up?")
        return 1

    lats = sorted(lat for lat, _ in results)
    errors = sum(1 for _, status in results if status == 0 or status >= 500)
    error_rate = errors / len(results)
    n = len(lats)

    def pct(p: float) -> float:
        return lats[min(n - 1, int(p * (n - 1)))] * 1000

    print(f"requests:      {n}   (elapsed {elapsed:.1f}s, {n / elapsed:.0f} req/s)")
    print(f"errors:        {errors}   (rate {error_rate:.2%})")
    print(f"latency ms:    p50 {pct(0.50):.1f} | p95 {pct(0.95):.1f} | p99 {pct(0.99):.1f} | max {max(lats) * 1000:.1f}")
    print(f"avg latency:   {statistics.mean(lats) * 1000:.1f} ms")

    ok = error_rate <= args.max_error_rate
    print(f"result:        {'PASS' if ok else 'FAIL'} (error budget {args.max_error_rate:.2%})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
