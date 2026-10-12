---
description: "@pm plans the next sprint"
argument-hint: "[sprint goal]"
---

Dispatch the `pm` subagent with this brief. Sprint goal from the user, if any: $ARGUMENTS

1. Read all team files and every deliverable produced so far.
2. Close or carry over the current sprint's tasks; note why anything slipped.
3. Create the next sprint's tasks in team/TASKS.md in the standard format, with owners, priorities, dependencies, reviewers, acceptance criteria and output paths. Ensure required reviewers (@model-risk for models, @compliance for data/decisions, @responsible-ai for anything affecting approvals/declines).
4. Post a HANDOFF in team/DISCUSSION.md listing each role's assignments.
5. Update team/RISKS.md.
6. End with the Summary block, including what the user needs to decide.

Relay the Summary to the user, with what the user needs to decide at the top.
