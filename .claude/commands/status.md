---
description: Team status report; reads the team files and changes nothing
---

Give a team status report without changing any files. Do this in the main session; do not dispatch a subagent.

Read team/TASKS.md, team/DISCUSSION.md, team/DECISIONS.md and team/RISKS.md, then report:
- Tasks by status, grouped by owner
- Blocked tasks and what unblocks them
- Unanswered messages older than one round
- Pending decisions and their owners
- Open vetoes/objections
- Top 3 risks
- What the user should do next

End with **For the AI Engineer**: pending proposals (P-###), the latest eval scores, and the top failure to fix next.
