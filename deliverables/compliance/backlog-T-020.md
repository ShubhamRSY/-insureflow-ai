# Backlog — T-020 review, Medium and Low findings

- Author: @compliance
- Date: 2026-10-11
- Per D-030. High findings are in the OBJECTION message in `team/DISCUSSION.md`, not here.
- Deliverable reviewed: `underwriting_pipeline/app/package.py`. Probes ran in a scratch folder outside the repo.

- Medium: a send leaves no log row. The only record is a `Sent-by:` line in the file: no time, no input or report hash, no carrier, no underwriter decision id (A-03).
- Medium: a second send for the same submission overwrites the first file with no warning and no copy kept. What the carrier was first told is lost (A-02, record retention).
- Medium: the submission id is not checked. `send_to_carrier("../escaped", ...)` writes outside `to-carrier`.
- Medium: the package names no carrier in its header or file name, and the routed carrier is not compared with the body. A file routed `carrier_a` was sent with a body recommending Carrier C.
- Medium: the body check is two phrases. Any text containing them is sent, including "BIND THIS TODAY". The FICTIONAL / synthetic label the protocol requires is not checked.
- Medium: "in appetite" comes from `workbench.route()`, which matches substrings. The route faults in `backlog-T-019.md` are inherited by the send gate.
- Medium: acceptance criterion 2 says only the user's typed line allows a write. D-017 and D-033 now also allow the account manager. @pm should restate the criterion so the code can be tested against one rule.
- Medium: `simulation/to-carrier/SUB-002-to-carrier-b.md` has `Sent-by: user` and a body that says "it has not been sent". The folder cannot tell a draft from a sent file.
- Low: a user override needs no reason, so the file does not say why the agency rules were skipped.
- Low: the module docstring says "The user can send any package". D-021 and D-033 say otherwise.
- Low: two negative self-checks pass the live path `simulation/to-carrier`. If the guard order changes, the self-check writes a real file. Use the temp folder for all of them.
- Low: `_actor` accepts "@USER ", "User", and "account manager". The header then prints a fixed label, so the record loses what was passed.
- Low: the `Sent-by:` header has no date.
