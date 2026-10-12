---
description: A team role answers its messages and does its next piece of work
argument-hint: "@role [extra instruction]"
---

Role and instruction: $ARGUMENTS

If no role is given, read `team/TASKS.md`, list the roles that have an unblocked TODO or IN_PROGRESS task or an unanswered @mention, and ask the user which one to run. Do not pick for them.

Otherwise dispatch that role's subagent (`.claude/agents/<role>.md`) with this brief, plus any extra instruction above:

1. Read team/TASKS.md, the latest ~30 messages in team/DISCUSSION.md, and team/DECISIONS.md.
2. First reply to every unanswered message that @mentions you.
3. Then take your highest-priority task that is not BLOCKED: set it to IN_PROGRESS, produce the real deliverable at its Output path, and check off acceptance criteria.
4. If it needs review, set IN_REVIEW and post a REVIEW request to the reviewers. If you are blocked, set BLOCKED and post a QUESTION to whoever can unblock you.
5. Append a standup entry to team/STANDUP.md.
6. End with the Summary block.

If the role is @ai-engineer-assistant and the task changes extraction, prompts, OCR, models, or eval scorers, include the user's exact `approve change P-###` line in the brief only if the user typed it in this chat and `team/DECISIONS.md` records it. Otherwise tell the subagent to propose and stop.

Relay the subagent's Summary to the user. Do not run the reviewers; that is `/review`.
