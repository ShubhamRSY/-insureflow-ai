# Proposal P-066: Concurrent-write safety + two-user tests (B-191)

Task: T-112, related to B-191 (pilot readiness), D-057.

## Problem statement
Decision log and decision writes must be safe against concurrent writes (two-user scenario). B-191 requires handling before pilot. D-065/D-069 constraints apply (sandbox/temp copies, never write real workbench page/team/production logs except deliberate board updates).

## Scope
- `underwriting_pipeline/app/workbench.py` and related append/write paths for decisions, logs, history
- Decision store/log file writes (append + serialization) need locking/atomic appends to prevent corruption
- Two-user tests simulating concurrent writes (8-thread + two-user cases as needed)

## Solution
Implement file-level locking (e.g. `fcntl` on POSIX) around writes/reads that mutate shared files. Use atomic write patterns (write to temp in same dir, fsync, rename) or exclusive locks for appends. Add tests under `tests/` that simulate concurrent access.

## Acceptance criteria
- No corruption on concurrent appends (tested with 8 threads)
- Two-user scenario passes
- Existing tests still pass
- Sandbox/test runs still write only temp dirs per D-069
- D-065 unaffected (What's new unchanged except if needed; P-067 already added)

## Implementation plan
1. Draft fix in workbench/decision write paths
2. Add concurrency tests
3. Verify with existing tests
4. Get @model-risk/@compliance review (High-only)

## Deliverables
- Modified `underwriting_pipeline/app/workbench.py` and any helper modules
- New/updated tests in `tests/`
- Proposal document (this file)
