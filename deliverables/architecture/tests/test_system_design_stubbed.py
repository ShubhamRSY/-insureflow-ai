"""T-095 — stubbed reliability, traffic, latency, failure, and cost tests for system-design.md.

No model is called and no network is used: sockets are blocked and the model host is a stub in this file.
Nothing is written outside a temp folder and this folder's results/. The pipeline code is imported, not edited.
Synthetic data only.

Run (from the repo root):
    .venv/bin/python -B deliverables/architecture/tests/test_system_design_stubbed.py

Each case is "as-is" (what the code does today; expected to pass) or "target" (what production needs;
a fail is a known gap and is reported as a fail, not hidden). Results: results/stubbed-results.json.

# ponytail: one file, own 20-line runner, threads not processes. Move to pytest and real workers when a queue exists.
"""

import sys

sys.dont_write_bytecode = True  # importing the pipeline must not write __pycache__ under underwriting_pipeline/

import contextlib
import email.message
import io
import json
import math
import os
import pathlib
import socket
import statistics
import tempfile
import threading
import time as real_time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PIPE = ROOT / "underwriting_pipeline"
HERE = Path(__file__).resolve().parent
ENV = ("LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY", "ALLOW_PROVIDER", "LLM_MAX_WAIT", "LLM_RUN_ID")
for _name in ENV:  # never read, never printed: the defaults are localhost and the dummy key
    os.environ.pop(_name, None)
SCRATCH = Path(tempfile.mkdtemp(prefix="t095-"))
os.environ["LLM_CACHE_DIR"] = str(SCRATCH / "cache-at-import")
os.environ["LLM_RUN_ID"] = "t095-stubbed"

NET: list = []


def _no_network(*args, **kwargs):
    NET.append(str(args[1:2]))
    raise AssertionError("a network call was attempted")


socket.socket.connect = _no_network
socket.create_connection = _no_network


def _snapshot() -> dict:
    """Every file the dispatch says must not change: name, size, modified time."""
    seen = {}
    for top in (PIPE, ROOT / "simulation", ROOT / "deliverables"):
        for path in top.rglob("*"):
            if path.is_file() and HERE not in path.parents:
                stat = path.stat()
                seen[str(path.relative_to(ROOT))] = (stat.st_size, stat.st_mtime_ns)
    return seen


BEFORE = _snapshot()

for _part in ("ai", "app", "models"):
    sys.path.insert(0, str(PIPE / _part))
import intake  # noqa: E402
import llm_extract  # noqa: E402
import package  # noqa: E402
import prepare  # noqa: E402
import sources  # noqa: E402
import workbench  # noqa: E402

FAKE_KEY = "TEST_NOT_A_REAL_KEY_T095"
MEAN_TOKENS = 1612  # measured: mean total_tokens of the 13 rows in underwriting_pipeline/cache/token_log.jsonl
MEAN_SERVICE = 2.08  # measured: mean usage.total_time (seconds) in the 13 files of underwriting_pipeline/cache/extractions/
TPM, TPD = 8000, 200000  # recorded in team/TASKS.md:715 and team/DECISIONS.md:228; the bucket shape below is assumed


class Clock:
    """Stands in for the time module inside llm_extract, so a 60-second wait costs nothing and is counted."""

    def __init__(self):
        self.now = real_time.time()
        self.sleeps = []

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds

    def strftime(self, *args):
        return real_time.strftime(*args)


class Reply(io.BytesIO):
    def __init__(self, body: str, headers: dict | None = None):
        super().__init__(body.encode())
        self.headers = headers or {}


def http(code: int, text: str, retry_after=None, headers: dict | None = None):
    head = email.message.Message()
    if retry_after is not None:
        head["Retry-After"] = str(retry_after)
    for key, value in (headers or {}).items():
        head[key] = str(value)
    return urllib.error.HTTPError("http://stub.test", code, "stub", head, io.BytesIO(text.encode()))


LABELS = {
    "named insured": "named_insured",
    "premises address": "premises_address",
    "effective date": "effective_date",
    "description of operations": "operations",
    "sales or payroll": "sales_or_payroll",
    "building tiv": "tiv_building",
    "construction": "construction",
    "year built": "year_built",
    "valued through": "loss_run_valued_through",
}


def answer(request, total_tokens: int | None = None, always_one: bool = False) -> str:
    """The stub's reply: every labeled line in the files it was sent, quoted exactly. Not a real extraction."""
    user = json.loads(request.data)["messages"][1]["content"]
    fields = []
    first = None
    for block in user.split("--- file: ")[1:]:
        name, _, text = block.partition(" ---\n")
        for line in text.splitlines():
            if first is None and line.strip():
                first = (name, line.strip()[:30])
            label, sep, value = line.partition(":")
            field = LABELS.get(label.strip().lower())
            if sep and field and value.strip():
                fields.append({"field_id": field, "value": value.strip(), "source": name, "quote": value.strip(), "confidence": 0.9})
    if always_one and not fields and first:
        fields.append({"field_id": "named_insured", "value": first[1], "source": first[0], "quote": first[1], "confidence": 0.9})
    prompt = len(request.data) // 4
    total = total_tokens or prompt + 969  # 969: measured mean completion_tokens, same 13 rows
    usage = {"prompt_tokens": prompt, "completion_tokens": total - prompt, "total_tokens": total}
    return json.dumps({"choices": [{"message": {"content": json.dumps({"fields": fields, "conflicts": []})}}], "usage": usage})


class Host:
    """The stubbed model host. Each post takes the next scripted item; after the script, the handler; else a good reply."""

    def __init__(self, script, handler):
        self.script, self.handler, self.posts, self.requests, self.lock = list(script), handler, 0, [], threading.Lock()

    def __call__(self, request, timeout=None):
        with self.lock:
            self.posts += 1
            self.requests.append(request)
            item = self.script.pop(0) if self.script else None
        if item is None:
            item = self.handler(request) if self.handler else Reply(answer(request))
        if isinstance(item, BaseException):
            raise item
        return item if isinstance(item, Reply) else Reply(item)


def host(*script, handler=None) -> Host:
    stub = Host(script, handler)
    urllib.request.urlopen = stub
    return stub


def bucket(clock: Clock, tpd: int = 10**12):
    """A token bucket with the recorded per-minute and per-day limits. ASSUMED shape: the host's real algorithm is in no file here."""
    state = {"tokens": float(TPM), "at": clock.now, "day": 0, "minute_429": 0, "day_429": 0}
    rate = TPM / 60

    def handler(request):
        state["tokens"] = min(TPM, state["tokens"] + (clock.now - state["at"]) * rate)
        state["at"] = clock.now
        head = {"x-ratelimit-limit-tokens": TPM, "x-ratelimit-remaining-tokens": int(state["tokens"])}
        if state["day"] + MEAN_TOKENS > tpd:
            state["day_429"] += 1
            return http(429, "stub: rate limit reached on tokens per day (TPD)", 3600, head)
        if state["tokens"] < MEAN_TOKENS:
            state["minute_429"] += 1
            return http(429, "stub: rate limit reached on tokens per minute (TPM)", math.ceil((MEAN_TOKENS - state["tokens"]) / rate), head)
        state["tokens"] -= MEAN_TOKENS
        state["day"] += MEAN_TOKENS
        clock.now += MEAN_SERVICE
        head["x-ratelimit-remaining-tokens"] = int(state["tokens"])
        return Reply(answer(request, MEAN_TOKENS), head)

    return state, handler


def make_sub(inbox: Path, name: str, number: int = 1) -> Path:
    """One SYNTHETIC two-file submission. The inbox median is two files (measured, simulation/inbox)."""
    folder = inbox / name
    folder.mkdir(parents=True)
    (folder / "application.md").write_text(
        f"SYNTHETIC test file.\nNamed insured: Synthetic Test {number} LLC\nPremises address: {100 + number} Main St, San Antonio, TX 78205\n"
        "Effective date: 2026-11-01\nDescription of operations: accounting office\nSales or payroll: 900000\n"
        "Building TIV: 500000\nConstruction: masonry\nYear built: 1998\n"
    )
    (folder / "loss-runs.md").write_text("SYNTHETIC carrier loss runs.\nValued through: 2026-08-15\nLosses: none in 5 years\n")
    return folder


def log_rows(cache: Path) -> list[dict]:
    log = cache / "token_log.jsonl"
    return [json.loads(line) for line in log.read_text().splitlines() if line.strip()] if log.exists() else []


def spread(values: list[float]) -> dict:
    ordered = sorted(values)
    return {
        "n": len(ordered),
        "p50": round(statistics.median(ordered), 4),
        "p95": round(ordered[round(0.95 * (len(ordered) - 1))], 4),
        "max": round(ordered[-1], 4),
        "mean": round(statistics.mean(ordered), 4),
    }


def ready_to_send(tmp: Path):
    """D-056: a send now reads its own saved run, decision log, and cited fields. Save a good run and an approve in tmp.
    Returns a restore function; the module paths point at tmp until it is called."""
    host()
    report = prepare.process_submission(make_sub(tmp / "inbox", "SUB-T0001"))
    payload = prepare._saved_payload(report)
    payload["submission"] = "SUB-T0001"
    payload["input_manifest"] = prepare.folder_manifest(tmp / "inbox" / "SUB-T0001")  # P-020 (D-062)
    payload["hash_algorithm"] = prepare.HASH_ALGORITHM
    payload["saved_hash"] = prepare.hash_payload(payload)
    (tmp / "extractions").mkdir()
    (tmp / "extractions" / "SUB-T0001.json").write_text(json.dumps(payload))
    (tmp / "decisions.jsonl").write_text(json.dumps({"seq": 1, "submission": "SUB-T0001", "action": "approve", "underwriter_id": "user", "reason": ""}) + "\n")
    saved = (prepare.EXTRACT_DIR, package.DECISIONS_LOG, package.SENDS_LOG, package.INBOX, prepare.INBOX_DIR)
    prepare.EXTRACT_DIR, package.DECISIONS_LOG, package.SENDS_LOG, package.INBOX, prepare.INBOX_DIR = tmp / "extractions", tmp / "decisions.jsonl", tmp / "sends.jsonl", tmp / "inbox", tmp / "inbox"

    def restore():
        prepare.EXTRACT_DIR, package.DECISIONS_LOG, package.SENDS_LOG, package.INBOX, prepare.INBOX_DIR = saved

    return restore


class Skip(Exception):
    pass


CASES = []


def case(category: str, kind: str, ref: str = ""):
    def add(fn):
        CASES.append((fn, category, kind, ref))
        return fn

    return add


# ---------------------------------------------------------------- failure injection: the model host


@case("failure", "as-is", "D-021; llm_extract.py:375-418; prepare.py:522-529,596-599")
def six_429s_give_extraction_failed_and_nothing_cached(tmp, clock, m):
    stub = host(handler=lambda request: http(429, "stub: rate limit reached (TPM)"))
    report = prepare.process_submission(make_sub(tmp / "inbox", "SUB-T0001"))
    m.update(posts=stub.posts, waits_seconds=clock.sleeps, waited_total_seconds=sum(clock.sleeps), status=report["status"])
    assert stub.posts == 6 and clock.sleeps == [1, 2, 4, 8, 16], f"{stub.posts} posts, waits {clock.sleeps}"
    assert report["status"] == "extraction_failed" and report["request"] is None and report["complete"] is False
    assert not (llm_extract.CACHE / "extractions").exists(), "a failed call was cached"
    assert [row.get("event") for row in log_rows(llm_extract.CACHE)] == ["rate_limit_429"] * 6


@case("failure", "as-is", "llm_extract.py:31,398-403")
def retry_after_one_hour_is_cut_to_max_wait_then_fails(tmp, clock, m):
    stub = host(handler=lambda request: http(429, "stub: rate limit reached (TPD)", 3600))
    report = prepare.process_submission(make_sub(tmp / "inbox", "SUB-T0001"))
    m.update(posts=stub.posts, waits_seconds=clock.sleeps, waited_total_seconds=sum(clock.sleeps), max_wait=llm_extract.MAX_WAIT)
    assert clock.sleeps == [60.0] * 5 and report["status"] == "extraction_failed"
    assert "tokens per day" in report["error"]


@case("failure", "as-is", "llm_extract.py:411-417")
def two_timeouts_then_a_reply_is_one_good_extraction(tmp, clock, m):
    stub = host(TimeoutError("timed out"), TimeoutError("timed out"))
    report = prepare.process_submission(make_sub(tmp / "inbox", "SUB-T0001"))
    rows = log_rows(llm_extract.CACHE)
    m.update(posts=stub.posts, waits_seconds=clock.sleeps, status=report["status"], missing=report["missing"])
    assert report["status"] == "complete", f"status {report['status']}, missing {report['missing']}"
    assert [row.get("event") for row in rows] == ["timeout", "timeout", None] and rows[-1]["attempts"] == 3


@case("failure", "as-is", "llm_extract.py:388,411-417")
def six_timeouts_fail_after_31_seconds_of_waits(tmp, clock, m):
    stub = host(handler=lambda request: TimeoutError("timed out"))
    report = prepare.process_submission(make_sub(tmp / "inbox", "SUB-T0001"))
    m.update(posts=stub.posts, waits_seconds=clock.sleeps, worst_case_wall_seconds_from_constants=6 * 120 + sum(clock.sleeps))
    assert stub.posts == 6 and clock.sleeps == [1, 2, 4, 8, 16] and report["status"] == "extraction_failed"


@case("failure", "as-is", "D-022 item 3; llm_extract.py:472-479")
def a_bad_reply_fails_is_not_cached_is_called_again_and_its_tokens_are_logged(tmp, clock, m):
    folder = make_sub(tmp / "inbox", "SUB-T0001")
    bad = json.dumps({"choices": [{"message": {"content": "not json"}}], "usage": {"total_tokens": 700}})
    empty = json.dumps({"choices": [{"message": {"content": "{}"}}], "usage": {"total_tokens": 650}})
    stub = host(bad, empty)
    statuses = [prepare.process_submission(folder)["status"] for _ in range(3)]
    totals = llm_extract.run_totals()["t095-stubbed"]
    m.update(statuses=statuses, posts=stub.posts, run_totals=totals)
    assert statuses == ["extraction_failed", "extraction_failed", "complete"] and stub.posts == 3
    assert totals["failed_attempts"]["reply_not_usable"] == 2
    assert totals["tokens"] >= 1350, "the tokens of an unusable reply were spent and must be in the total"


@case("failure", "as-is", "llm_extract.py:411-417")
def provider_outage_gives_extraction_failed_with_cause_other(tmp, clock, m):
    stub = host(handler=lambda request: urllib.error.URLError(ConnectionRefusedError(61, "Connection refused")))
    inbox = tmp / "inbox"
    reports = [prepare.process_submission(make_sub(inbox, f"SUB-T{n:04d}", n)) for n in range(3)]
    m.update(posts=stub.posts, waited_total_seconds=sum(clock.sleeps), waited_per_submission_seconds=sum(clock.sleeps) / 3, failure_counts=llm_extract.failure_counts())
    assert all(report["status"] == "extraction_failed" and report["request"] is None for report in reports)
    assert llm_extract.failure_counts()["other"] == 18 and sum(clock.sleeps) == 93


@case("failure", "target", "G7; llm_extract.py:219-222; prepare.py:524")
def a_refused_provider_host_marks_the_file_and_does_not_stop_the_process(tmp, clock, m):
    os.environ.update(LLM_BASE_URL="https://example.test/v1", LLM_MODEL="m", LLM_API_KEY=FAKE_KEY)
    stub = host()
    try:
        report = prepare.process_submission(make_sub(tmp / "inbox", "SUB-T0001"))
    except SystemExit as stop:
        m.update(posts=stub.posts, raised="SystemExit", said=str(stop).replace(FAKE_KEY, "[key]")[:160])
        raise AssertionError("SystemExit: the whole process stops, the workbench server included") from None
    assert report["status"] == "extraction_failed"


@case("failure", "as-is", "llm_extract.py:168-172,392,408-409")
def the_api_key_is_in_no_log_row_and_no_error(tmp, clock, m):
    os.environ["LLM_API_KEY"] = FAKE_KEY
    host(http(401, f"invalid key {FAKE_KEY}"))
    report = prepare.process_submission(make_sub(tmp / "inbox", "SUB-T0001"))
    text = (llm_extract.CACHE / "token_log.jsonl").read_text()
    assert report["status"] == "extraction_failed" and FAKE_KEY not in json.dumps(report) and FAKE_KEY not in text and "Bearer" not in text


# ---------------------------------------------------------------- failure injection: files


@case("failure", "as-is", "sources.py:125-127; prepare.py:518-520,578")
def a_blank_scan_is_marked_needs_human_and_is_not_sent_to_the_model(tmp, clock, m):
    try:
        from PIL import Image
        import pytesseract  # noqa: F401
    except ImportError as exc:
        raise Skip(f"needs the OCR packages: {exc}") from None
    folder = tmp / "inbox" / "SUB-T0001"
    folder.mkdir(parents=True)
    Image.new("RGB", (400, 200), "white").save(folder / "scan.png")
    stub = host()
    report = prepare.process_submission(folder)
    m.update(posts=stub.posts, status=report["status"], needs_human=report["needs_human"], request_drafted=bool(report["request"]))
    assert stub.posts == 0 and report["needs_human"] == ["scan.png"]


@case("failure", "target", "G6; prepare.py:518-520,596,602-606")
def a_folder_where_nothing_was_read_gets_no_missing_info_request(tmp, clock, m):
    folder = tmp / "inbox" / "SUB-T0001"
    folder.mkdir(parents=True)
    (folder / "application.md").write_text("")
    stub = host()
    report = prepare.process_submission(folder)
    m.update(posts=stub.posts, status=report["status"], request_drafted=bool(report["request"]), missing_count=len(report["missing"]))
    assert report["request"] is None and report["status"] != "incomplete", f"status {report['status']}: a request for all {len(report['missing'])} fields is drafted, as if the producer had left them out"


@case("failure", "target", "G14; sources.py:133,139,191-199; prepare.py:502")
def a_file_that_cannot_be_opened_is_listed_for_a_person_and_the_rest_is_read(tmp, clock, m):
    try:
        import pdfplumber  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError as exc:
        raise Skip(f"needs the OCR packages: {exc}") from None
    stopped = {}
    for bad in ("scan.png", "application-2.pdf", "schedule.xlsx"):
        folder = make_sub(tmp / f"inbox-{bad}", "SUB-T0001")
        (folder / bad).write_bytes(b"SYNTHETIC: these bytes are not a file of this type")
        host()
        try:
            report = prepare.process_submission(folder)
            stopped[bad] = None if bad in report["needs_human"] else "read on with the file not listed"
        except Exception as exc:  # noqa: BLE001
            stopped[bad] = f"{type(exc).__name__}"
    m.update(result_by_file=stopped)
    assert not any(stopped.values()), f"the whole submission stops: {stopped}"


@case("failure", "target", "G15; llm_extract.py:436")
def text_past_120000_characters_is_listed_as_unread(tmp, clock, m):
    folder = make_sub(tmp / "inbox", "SUB-T0001")
    (folder / "application.md").write_text((folder / "application.md").read_text() + "SYNTHETIC filler line.\n" * 7000)  # the loss runs are the second file
    stub = host()
    report = prepare.process_submission(folder)
    sent = len(json.loads(stub.requests[0].data)["messages"][1]["content"])
    on_disk = sum(len(path.read_text()) for path in folder.iterdir())
    m.update(characters_on_disk=on_disk, characters_sent=sent, status=report["status"], needs_human=report["needs_human"], missing=report["missing"], request_drafted=bool(report["request"]))
    assert sent == 120000, f"sent {sent}"
    assert report["needs_human"], f"the second file was cut off whole and nothing says so; status {report['status']}, and the producer is asked for {report['missing']}"


# ---------------------------------------------------------------- failure injection: duplicates, crashes, cache


@case("failure", "as-is", "D-022; llm_extract.py:69-71,445-460")
def the_same_files_in_two_folders_cost_one_model_call(tmp, clock, m):
    stub = host()
    first = prepare.process_submission(make_sub(tmp / "inbox", "SUB-T0001"))
    second = prepare.process_submission(make_sub(tmp / "inbox", "SUB-T0002"))
    m.update(posts=stub.posts, statuses=[first["status"], second["status"]], linked=False)
    assert stub.posts == 1 and first["fields"] == second["fields"]


@case("failure", "target", "G1; intake.py:28")
def a_duplicate_submission_is_recognized(tmp, clock, m):
    files = [("application.md", b"SYNTHETIC\nNamed insured: Synthetic Test 1 LLC\n")]
    one, two = intake.intake(files), intake.intake(files)
    m.update(same_file_hashes=one["documents"] == two["documents"], same_id=one["submission_id"] == two["submission_id"], keys=sorted(two))
    assert one["submission_id"] == two["submission_id"] or two.get("duplicate_of"), "the same bytes get two unrelated ids and nothing links them"


@case("failure", "as-is", "D-027; llm_extract.py:481-487")
def a_run_killed_during_the_cache_write_leaves_no_result_and_the_next_run_calls_again(tmp, clock, m):
    folder = make_sub(tmp / "inbox", "SUB-T0001")
    stub = host()
    real_replace = os.replace
    os.replace = lambda *_: (_ for _ in ()).throw(KeyboardInterrupt())
    try:
        prepare.process_submission(folder)
        raise AssertionError("the stubbed kill did not happen")
    except KeyboardInterrupt:
        pass
    finally:
        os.replace = real_replace
    saved = list((llm_extract.CACHE / "extractions").glob("*.json"))
    report = prepare.process_submission(folder)
    m.update(results_after_kill=len(saved), posts=stub.posts, status=report["status"], tokens_paid_twice=True)
    assert saved == [] and stub.posts == 2 and report["status"] == "complete"


@case("failure", "as-is", "P-014; llm_extract.py:74-87,106-124")
def a_cut_line_in_the_token_log_is_skipped_and_the_next_row_is_whole(tmp, clock, m):
    llm_extract.CACHE.mkdir(parents=True)
    (llm_extract.CACHE / "token_log.jsonl").write_bytes(b'{"at": "2026-10-13T00:00:00", "epoch": 17')
    host()
    prepare.process_submission(make_sub(tmp / "inbox", "SUB-T0001"))
    rows, skipped = llm_extract._log_rows()
    m.update(readable_rows=len(rows), skipped_lines=skipped)
    assert len(rows) == 1 and skipped == 1


@case("failure", "target", "package.py:77-80 (plain write_text)")
def a_run_killed_during_the_send_write_leaves_no_partial_package(tmp, clock, m):
    out = tmp / "to-carrier"
    restore = ready_to_send(tmp)
    body = package.build_package("SUB-T0001")
    real_write = pathlib.Path.write_text

    def cut(self, data, *args, **kwargs):
        real_write(self, data[: len(data) // 2])
        raise KeyboardInterrupt()

    pathlib.Path.write_text = cut
    try:
        package.send_to_carrier("SUB-T0001", "user", out, user_line="send to carrier SUB-T0001")
    except KeyboardInterrupt:
        pass
    finally:
        pathlib.Path.write_text = real_write
        restore()
    left = out / "SUB-T0001.md"
    m.update(file_exists=left.exists(), bytes_left=left.stat().st_size if left.exists() else 0, bytes_whole=len(body) + len("Sent-by: user (override)\n\n"))
    assert not left.exists(), f"a half-written package of {left.stat().st_size} bytes sits under the final name in to-carrier"


@case("failure", "target", "G10; package.py:77,80")
def a_second_send_does_not_replace_the_first(tmp, clock, m):
    out = tmp / "to-carrier"
    restore = ready_to_send(tmp)
    try:
        package.send_to_carrier("SUB-T0001", "user", out, user_line="send to carrier SUB-T0001")
        first = (out / "SUB-T0001.md").read_text()
        try:
            package.send_to_carrier("SUB-T0001", "user", out, reason="second send", user_line="send to carrier SUB-T0001")
            refused = False
        except ValueError:
            refused = True
    finally:
        restore()
    kept = any(path.read_text() == first for path in out.iterdir())
    m.update(second_send_refused=refused, first_package_still_on_disk=kept, files=sorted(path.name for path in out.iterdir()))
    assert refused or kept, "the second send overwrote the first and no record of the first is left"


@case("failure", "as-is", "llm_extract.py:54,69-71; sources.py:16,205-206")
def a_changed_prompt_model_host_temperature_or_file_is_a_new_cache_key(tmp, clock, m):
    docs = sources.read_folder(make_sub(tmp / "inbox", "SUB-T0001"))
    here = llm_extract.cache_key(docs, "m")
    keys = {"model": llm_extract.cache_key(docs, "m2"), "file": llm_extract.cache_key([{**docs[0], "text": docs[0]["text"] + " "}, docs[1]], "m")}
    keys["ocr settings"] = llm_extract.cache_key([{**docs[0], "ocr": "other"}, docs[1]], "m")
    old = llm_extract.PROMPT_VERSION, llm_extract.TEMPERATURE
    try:
        llm_extract.PROMPT_VERSION = "changed"
        keys["prompt"] = llm_extract.cache_key(docs, "m")
        llm_extract.PROMPT_VERSION = old[0]
        llm_extract.TEMPERATURE = 1
        keys["temperature"] = llm_extract.cache_key(docs, "m")
        llm_extract.TEMPERATURE = old[1]
        os.environ["LLM_BASE_URL"] = "http://127.0.0.1:11434/v1"
        keys["host"] = llm_extract.cache_key(docs, "m")
        os.environ["LLM_BASE_URL"] = "http://localhost:9999/v1"
        same_on_other_port = llm_extract.cache_key(docs, "m") == here
    finally:
        llm_extract.PROMPT_VERSION, llm_extract.TEMPERATURE = old
        os.environ.pop("LLM_BASE_URL", None)
    m.update(changed={name: key != here for name, key in keys.items()}, port_is_in_key=not same_on_other_port)
    assert all(key != here for key in keys.values()) and len(set(keys.values())) == len(keys)


@case("failure", "as-is", "G20; llm_extract.py:447-455 (no age check)")
def a_saved_reply_400_days_old_is_served_with_no_call(tmp, clock, m):
    folder = make_sub(tmp / "inbox", "SUB-T0001")
    stub = host()
    prepare.process_submission(folder)
    saved = next((llm_extract.CACHE / "extractions").glob("*.json"))
    old = real_time.time() - 400 * 86400
    os.utime(saved, (old, old))
    report = prepare.process_submission(folder)
    m.update(posts=stub.posts, age_days=400, status=report["status"])
    assert stub.posts == 1 and report["status"] == "complete"


# ---------------------------------------------------------------- can a send ever happen


@case("send", "as-is", "D-017; package.py:61-63; prepare.py:676-678")
def no_ai_role_can_send_or_approve(tmp, clock, m):
    draft = tmp / "SUB-T0001.md"
    draft.write_text("Nothing has been declined.\n")
    refused = 0
    for role in ("ml-engineer", "ai-engineer-assistant", "software-engineer", "orchestrator", ""):
        for call in (lambda: package.send_to_carrier("SUB-T0001", role, tmp / "to-carrier", user_line="send to carrier SUB-T0001"), lambda: prepare.approve(draft, role, tmp / "to-producer")):
            try:
                call()
            except ValueError:
                refused += 1
    assert refused == 10 and not (tmp / "to-carrier").exists() and not (tmp / "to-producer").exists()


@case("send", "as-is", "D-021; package.py:37-38,64-65")
def a_failed_file_is_refused_for_the_user_and_the_account_manager_when_the_report_is_passed(tmp, clock, m):
    host(handler=lambda request: http(500, "stub: boom"))
    report = prepare.process_submission(make_sub(tmp / "inbox", "SUB-T0001"))
    refused = 0
    for actor in ("user", "account-manager"):
        try:
            package.send_to_carrier("SUB-T0001", actor, tmp / "to-carrier", reason="ready", user_line="send to carrier SUB-T0001")
        except ValueError:
            refused += 1
    assert report["status"] == "extraction_failed" and refused == 2 and not (tmp / "to-carrier").exists()


@case("send", "target", "DEMO-BLOCKERS line 1 (P-010, T-071); package.py:64")
def a_failed_file_is_refused_when_the_caller_leaves_the_report_out(tmp, clock, m):
    host(handler=lambda request: http(500, "stub: boom"))
    report = prepare.process_submission(make_sub(tmp / "inbox", "SUB-T0001"))
    assert report["status"] == "extraction_failed"
    try:
        dest = package.send_to_carrier("SUB-T0001", "user", tmp / "to-carrier", user_line="send to carrier SUB-T0001")
    except ValueError:
        return
    m.update(written=dest.name)
    raise AssertionError("the package of a file whose extraction failed was written to to-carrier")


@case("send", "target", "DEMO-BLOCKERS line 2 (D-033 item 2, T-079); package.py:53-81 reads no decision log")
def a_send_with_no_logged_underwriter_approve_is_refused(tmp, clock, m):
    host()
    report = prepare.process_submission(make_sub(tmp / "inbox", "SUB-T0001"))
    m.update(status=report["status"], route=workbench.route(report))
    try:
        package.send_to_carrier("SUB-T0001", "account-manager", tmp / "to-carrier", reason="complete office file")
    except ValueError as exc:
        m.update(refused_because=str(exc))
        return
    raise AssertionError("sent with no decision in any log: the send reads no decision log")


@case("send", "as-is", "D-021; prepare.py:597-599,624-625")
def a_failed_file_gets_no_missing_info_draft(tmp, clock, m):
    host(handler=lambda request: http(500, "stub: boom"))
    make_sub(tmp / "inbox", "SUB-T0001")
    reports = prepare.write_drafts(tmp / "inbox", tmp / "pending-approval", tmp / "data" / "conflicts")
    saved = json.loads((tmp / "data" / "extractions" / "SUB-T0001.json").read_text())
    m.update(drafts=sorted(path.name for path in (tmp / "pending-approval").iterdir()), saved_file_keys=sorted(saved), saved_file_has_status="status" in saved)
    assert reports[0]["status"] == "extraction_failed" and list((tmp / "pending-approval").iterdir()) == []


# ---------------------------------------------------------------- traffic


@case("traffic", "as-is", "prepare.py:501-607; llm_extract.py:421-511")
def load_300_submissions_one_after_another_cold_then_from_the_cache(tmp, clock, m):
    folders = [make_sub(tmp / "inbox", f"SUB-T{n:04d}", n) for n in range(300)]
    stub = host()
    timings = {}
    for name in ("cold", "warm"):
        each = []
        for folder in folders:
            began = real_time.perf_counter()
            report = prepare.process_submission(folder)
            each.append((real_time.perf_counter() - began) * 1000)
            assert report["status"] == "complete", f"{folder.name}: {report['status']} {report['missing']}"
        timings[name] = spread(each)
        timings[name]["posts_so_far"] = stub.posts
    totals = llm_extract.run_totals()["t095-stubbed"]
    log_bytes = (llm_extract.CACHE / "token_log.jsonl").stat().st_size
    m.update(local_milliseconds_per_submission=timings, run_totals=totals, token_log_rows=len(log_rows(llm_extract.CACHE)), token_log_bytes=log_bytes,
             saved_replies=len(list((llm_extract.CACHE / "extractions").glob("*.json"))), note="model latency is zero in this stub: this is the local cost only")
    assert stub.posts == 300 and totals["model_calls"] == 300 and totals["from_cache"] == 300


@case("traffic", "as-is", "llm_extract.py:338-360,386; bucket shape ASSUMED")
def peak_hour_60_submissions_against_the_recorded_per_minute_limit(tmp, clock, m):
    state, handler = bucket(clock)
    stub = host(handler=handler)
    began = clock.now
    statuses = [prepare.process_submission(make_sub(tmp / "inbox", f"SUB-T{n:04d}", n))["status"] for n in range(60)]
    elapsed = clock.now - began
    m.update(submissions=60, simulated_seconds=round(elapsed, 1), submissions_per_hour=round(60 / elapsed * 3600, 1), seconds_per_submission=round(elapsed / 60, 2),
             posts=stub.posts, minute_429s=state["minute_429"], paced_waits=len(clock.sleeps), longest_wait_seconds=round(max(clock.sleeps), 1) if clock.sleeps else 0,
             tokens_per_call=MEAN_TOKENS, limit_tokens_per_minute=TPM, pace_reserve="len(body)//4 + 2000 (llm_extract.py:386)")
    assert statuses == ["complete"] * 60 and state["minute_429"] == 0, f"{state['minute_429']} 429s; pacing should prevent every one"


@case("traffic", "as-is", "llm_extract.py:31,393-406; TASKS.md:715")
def one_day_of_150_submissions_against_the_recorded_daily_limit(tmp, clock, m):
    state, handler = bucket(clock, TPD)
    stub = host(handler=handler)
    began = clock.now
    statuses = [prepare.process_submission(make_sub(tmp / "inbox", f"SUB-T{n:04d}", n))["status"] for n in range(150)]
    done = statuses.count("complete")
    after_cap = [wait for wait in clock.sleeps if wait == 60.0]
    m.update(submitted=150, complete=done, extraction_failed=statuses.count("extraction_failed"), posts=stub.posts, day_429s=state["day_429"],
             simulated_hours=round((clock.now - began) / 3600, 2), seconds_lost_per_failed_submission=round(sum(after_cap) / max(1, 150 - done), 1),
             tokens_used=state["day"], limit_tokens_per_day=TPD)
    assert done == TPD // MEAN_TOKENS == 124 and statuses[done:] == ["extraction_failed"] * 26


@case("traffic", "target", "G20; NFR-007; llm_extract.py:447-487 (no lock)")
def four_workers_on_the_same_new_file_call_the_model_once(tmp, clock, m):
    docs = sources.read_folder(make_sub(tmp / "inbox", "SUB-T0001"))

    def slow(request):
        real_time.sleep(0.05)
        return Reply(answer(request))

    stub = host(handler=slow)
    crashed = []

    def work():
        try:
            llm_extract.llm_extract(docs)
        except Exception as exc:  # noqa: BLE001
            crashed.append(type(exc).__name__)

    workers = [threading.Thread(target=work) for _ in range(4)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    m.update(workers_crashed=crashed, note="threads share one process id, and the temp file name holds only the process id (llm_extract.py:482); separate processes were not tested")
    m.update(workers=4, posts=stub.posts, saved_replies=len(list((llm_extract.CACHE / "extractions").glob("*.json"))), temp_files_left=len(list((llm_extract.CACHE / "extractions").glob("*.tmp"))))
    assert stub.posts == 1 and not crashed, f"{stub.posts} model calls for one file, and {len(crashed)} of 4 workers stopped with {sorted(set(crashed))}"


@case("traffic", "as-is", "llm_extract.py:81-86; workbench.py:142-143")
def eight_threads_appending_to_the_token_log_and_the_decision_log_lose_no_row(tmp, clock, m):
    llm_extract.CACHE.mkdir(parents=True)
    decisions = tmp / "decisions.jsonl"

    def work(number):
        for row in range(250):
            llm_extract._log_row({"model": "stub", "files": [f"{number}-{row}.md"], "event": "cache_hit", "total_tokens": 0})
            workbench.record_decision({"underwriter_id": f"UW-TEST-{number}", "action": "approve", "submission": f"SUB-T{row:04d}", "reason": "SYNTHETIC load test"}, decisions)

    workers = [threading.Thread(target=work, args=(number,)) for number in range(8)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    rows, skipped = llm_extract._log_rows()
    decided = 0
    broken = 0
    for line in decisions.read_text().splitlines():
        try:
            json.loads(line)
            decided += 1
        except ValueError:
            broken += 1
    m.update(token_log_rows=len(rows), token_log_skipped=skipped, decision_rows=decided, decision_rows_broken=broken, note="threads in one process, not separate processes or machines")
    assert (len(rows), skipped, decided, broken) == (2000, 0, 2000, 0)


@case("traffic", "target", "G3; NFR-006; workbench.py:86,234")
def opening_the_workbench_makes_no_model_call(tmp, clock, m):
    for number in range(20):
        make_sub(tmp / "inbox", f"SUB-T{number:04d}", number)
    real_inbox, workbench.INBOX = workbench.INBOX, tmp / "inbox"
    try:
        stub = host(handler=lambda request: urllib.error.URLError(ConnectionRefusedError(61, "Connection refused")))
        workbench.load_queue()
        m.update(queue=20, posts_during_an_outage=stub.posts, seconds_before_the_page_exists_during_an_outage=sum(clock.sleeps))
        clock.sleeps.clear()
        stub = host()
        queue = workbench.load_queue()
        m.update(posts_on_a_cold_start=stub.posts, routes=sorted({item["route"] for item in queue}))
    finally:
        workbench.INBOX = real_inbox
    assert stub.posts == 0, f"{stub.posts} model calls were made inside the page load for a queue of 20"


# ---------------------------------------------------------------- latency


@case("latency", "as-is", "sources.py:184-208; prepare.py:501-607; simulation/inbox read only")
def local_stage_times_on_the_86_inbox_folders(tmp, clock, m):
    try:
        import openpyxl  # noqa: F401
        import pdfplumber  # noqa: F401
        import pytesseract  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError as exc:
        raise Skip(f"needs the OCR packages: {exc}") from None
    inbox = ROOT / "simulation" / "inbox"
    read = {"typed only": [], "with a pdf": [], "with an image": []}
    rules, per_image, stopped, needs_human, files = [], [], [], 0, 0
    host(handler=lambda request: Reply(answer(request, always_one=True)))
    real_read = sources.read_folder
    try:
        for folder in sorted(path for path in inbox.iterdir() if path.is_dir() and path.name.startswith("SUB-")):
            names = [path.suffix.lower() for path in folder.iterdir() if path.is_file()]
            kind = "with an image" if any(name in sources.IMAGE for name in names) else "with a pdf" if ".pdf" in names else "typed only"
            began = real_time.perf_counter()
            try:
                docs = real_read(folder)
            except Exception as exc:  # noqa: BLE001
                stopped.append(f"{folder.name}: {type(exc).__name__}")
                continue
            took = real_time.perf_counter() - began
            read[kind].append(took)
            if kind == "with an image":
                per_image.append(took / sum(1 for name in names if name in sources.IMAGE))
            files += len(docs)
            needs_human += sum(1 for doc in docs if doc.get("needs_human"))
            sources.read_folder = lambda _folder, docs=docs: docs
            began = real_time.perf_counter()
            prepare.process_submission(folder)
            rules.append(real_time.perf_counter() - began)
            sources.read_folder = real_read
    finally:
        sources.read_folder = real_read
    import shutil

    m.update(folders=sum(len(times) for times in read.values()), files_read=files, files_marked_needs_human=needs_human, folders_that_stopped=stopped,
             read_seconds={kind: spread(times) for kind, times in read.items() if times}, read_seconds_per_image_file=spread(per_image) if per_image else None,
             gates_and_rules_seconds_with_a_stub_reply=spread(rules), pdftoppm_installed=bool(shutil.which("pdftoppm")), tesseract_installed=bool(shutil.which("tesseract")),
             note="one machine, one run; a scanned PDF is not read here when pdftoppm is missing (G16)")
    assert not stopped, f"reading stopped on {stopped}"


# ---------------------------------------------------------------- cost


@case("cost", "as-is", "D-022; llm_extract.py:127-142,455-460")
def a_second_run_over_unchanged_files_costs_no_tokens(tmp, clock, m):
    folders = [make_sub(tmp / "inbox", f"SUB-T{n:04d}", n) for n in range(15)]
    stub = host(handler=lambda request: Reply(answer(request, MEAN_TOKENS)))
    for run in ("t095-first", "t095-second"):
        llm_extract.RUN = run
        for folder in folders:
            prepare.process_submission(folder)
    totals = llm_extract.run_totals()
    llm_extract.RUN = "t095-stubbed"
    m.update(first=totals["t095-first"], second=totals["t095-second"])
    assert totals["t095-first"]["tokens"] == 15 * MEAN_TOKENS and totals["t095-second"] == {**totals["t095-second"], "model_calls": 0, "tokens": 0, "from_cache": 15} and stub.posts == 15


@case("cost", "as-is", "llm_extract.py:464-472")
def an_http_400_is_answered_with_one_more_post_and_one_usage_row(tmp, clock, m):
    stub = host(http(400, "stub: response_format is not supported"))
    report = prepare.process_submission(make_sub(tmp / "inbox", "SUB-T0001"))
    rows = log_rows(llm_extract.CACHE)
    m.update(posts=stub.posts, events=[row.get("event") for row in rows], worst_case_posts_per_submission=12)
    assert stub.posts == 2 and report["status"] == "complete" and [row.get("event") for row in rows] == ["other", "retry", None]
    assert "response_format" not in json.loads(stub.requests[1].data)


@case("cost", "as-is", "underwriting_pipeline/cache/token_log.jsonl and cache/extractions (read only)")
def tokens_per_submission_and_daily_headroom_from_the_real_token_log(tmp, clock, m):
    real = PIPE / "cache"
    rows = [json.loads(line) for line in (real / "token_log.jsonl").read_text().splitlines() if line.strip()]
    calls = [row for row in rows if not row.get("event")]
    totals = [row["total_tokens"] for row in calls]
    usage = [json.loads(path.read_text()).get("usage") or {} for path in sorted((real / "extractions").glob("*.json"))]
    mean = statistics.mean(totals)
    m.update(
        token_log_rows=len(rows), calls=len(calls), failed_attempt_rows=len(rows) - len(calls), models=sorted({row["model"] for row in calls}),
        first_row=rows[0]["at"], last_row=rows[-1]["at"],
        prompt_tokens=spread([row["prompt_tokens"] for row in calls]), completion_tokens=spread([row["completion_tokens"] for row in calls]), total_tokens=spread(totals),
        reasoning_tokens=spread([(item.get("completion_tokens_details") or {}).get("reasoning_tokens", 0) for item in usage]),
        host_reported_seconds={name: spread([item[name] for item in usage if name in item]) for name in ("queue_time", "prompt_time", "completion_time", "total_time")},
        files_per_call=spread([len(row["files"]) for row in calls]),
        submissions_per_day_under_200000_tokens=int(TPD // mean),
        monthly={str(volume): {"tokens": round(volume * mean), "tokens_per_business_day_of_22": round(volume * mean / 22), "share_of_daily_limit_percent": round(volume * mean / 22 / TPD * 100, 1)} for volume in (300, 1000, 3000)},
    )
    assert len(calls) == 13, f"{len(calls)} call rows: the numbers in system-design.md were taken from 13"


# ---------------------------------------------------------------- runner


def main() -> int:
    results = []
    for fn, category, kind, ref in CASES:
        tmp = Path(tempfile.mkdtemp(dir=SCRATCH))
        clock = Clock()
        llm_extract.CACHE, llm_extract.time, llm_extract.RUN = tmp / "cache", clock, "t095-stubbed"
        for box in (llm_extract.USAGE, llm_extract.CALL_LOG, llm_extract._budget, llm_extract._swept, llm_extract._announced):
            box.clear()
        urllib.request.urlopen = _no_network
        measured: dict = {}
        outcome, detail = "pass", ""
        began = real_time.perf_counter()
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                fn(tmp, clock, measured)
        except Skip as exc:
            outcome, detail = "skip", str(exc)
        except AssertionError as exc:
            outcome, detail = "fail", str(exc) or "assertion"
        except BaseException as exc:  # noqa: BLE001
            outcome, detail = "error", f"{type(exc).__name__}: {exc}"
        finally:
            for name in ENV:
                if name != "LLM_RUN_ID":
                    os.environ.pop(name, None)
        if kind == "target" and outcome == "fail":
            outcome = "fail (known gap)"
        results.append({"test": fn.__name__, "category": category, "kind": kind, "ref": ref, "outcome": outcome, "detail": detail.replace(FAKE_KEY, "[key]"), "seconds": round(real_time.perf_counter() - began, 2), "measured": measured})
        print(f"{outcome:17} {category:8} {kind:6} {fn.__name__}" + (f"\n{'':17} -> {detail[:200]}" if detail else ""))
    after = _snapshot()
    changed = sorted(name for name in set(BEFORE) | set(after) if BEFORE.get(name) != after.get(name))
    counts: dict = {}
    for row in results:
        counts[row["outcome"]] = counts.get(row["outcome"], 0) + 1
    summary = {
        "task": "T-095",
        "run_at": real_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "command": ".venv/bin/python -B deliverables/architecture/tests/test_system_design_stubbed.py",
        "python": sys.version.split()[0],
        "model_calls": 0,
        "network_calls_attempted": len(NET),
        "files_changed_under_underwriting_pipeline_simulation_or_other_deliverables": changed,
        "counts": counts,
        "results": results,
    }
    out = HERE / "results"
    out.mkdir(exist_ok=True)
    (out / "stubbed-results.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    print(f"\n{counts}\nnetwork calls attempted: {len(NET)}; protected files changed: {len(changed)}\nresults: {out / 'stubbed-results.json'}")
    import shutil

    shutil.rmtree(SCRATCH, ignore_errors=True)  # the temp folder holds only this run's synthetic files
    unexpected = [row for row in results if row["outcome"] in ("fail", "error")]
    return 1 if unexpected or changed or NET else 0


if __name__ == "__main__":
    raise SystemExit(main())
