# Incident and rollback — assist-only pilot

- Date: 2026-10-21. Written in OpenCode, not independently reviewed.

## Stop immediately

Any of these is a stop event (also listed in C8):

- any pilot file is sent, drafted or made sendable;
- any real file is processed before B-190 is merged and checked;
- any C7 change lands in `underwriting_pipeline/` during the pilot;
- a log write fails without a visible plain-language error;
- a field's correction rate passes the @head-of-underwriting threshold;
- any sign-in or audit gap is found.

## What the pilot owner does

1. Tell the pilot owner, @model-risk and @user in writing. Name the file ids and the stop event.
2. Set `PILOT_MODE=off` for the workbench process. This removes the pilot guards; it does **not** make sending appropriate. Do not use the tool for real data while the pilot is stopped.
3. Preserve `deliverables/software-engineer/pilot-corrections.jsonl` and `pilot-events.jsonl` (and the B-190 audit log). Do not edit, truncate or delete them. Copy them to a read-only incident folder.
4. Check the outboxes are empty of pilot ids: `simulation/to-carrier/`, `simulation/to-producer/`, `simulation/pending-approval/`.
5. Check `decisions.jsonl` has no `approve` row for a pilot id and `sends.jsonl` has no pilot id.
6. Restart only on the frozen branch SHA. If the stop was a code change, restore the frozen SHA and record the rollback commit.
7. @model-risk reviews the logs and states whether the pilot may resume. Pilot results never change published scores (D-025).

## Rollback of the pilot mode

- The pilot is off by default: unset `PILOT_MODE` or set `PILOT_MODE=off`.
- The guards fail closed: an unknown `PILOT_MODE` value is a configuration error, not "off".
- Turning pilot mode off does not delete logs, decisions or sends.
- No database migration and no external service are involved.

## Evidence to keep

- Branch SHA at pilot start (`freeze-note.md`).
- Both pilot logs and the B-190 audit log.
- The workbench screenshot with the pilot banner and scope verdict.
- The stop report and @model-risk's resume or no-resume decision.
