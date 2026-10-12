---
description: Reviewers give verdicts on work in IN_REVIEW, each from a separate subagent
argument-hint: "[@role] [T-###]"
---

Scope: $ARGUMENTS (no argument means every reviewer with work waiting)

1. In `team/TASKS.md`, find tasks in IN_REVIEW. Keep the ones in scope. For each, note the reviewers, the acceptance criteria, and the Output paths.
2. For each (task, reviewer) pair, dispatch that reviewer's subagent. One pair per dispatch, one after another.

For @model-risk, @compliance, and @responsible-ai the dispatch is a fresh subagent (never a fork) and contains ONLY this, filled in:

```
Review T-### as @<role>.
Acceptance criteria:
<copied verbatim from TASKS.md>
Deliverable:
<paths>
Follow the "Independent review" section of your instructions.
```

Do not add the author's name for the work, the author's messages, the task Notes, earlier verdicts from other reviewers, or your own view.

For any other reviewer, dispatch with this brief:

1. Read the deliverable fully. Judge it strictly from your role's mandate.
2. Post a TYPE: REVIEW message for the task with: verdict (APPROVE / APPROVE WITH CHANGES / REJECT), findings rated High/Medium/Low, and the specific changes required.
3. Do not edit other roles' deliverables yourself.
4. End with the Summary block.

3. Report to the user a table of task, reviewer, verdict, and High findings, with each veto and what would resolve it. Relay verdicts as written. Do not change any task status yourself and do not fix findings; the owner does that with `/work`.
