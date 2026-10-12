---
description: Raise a decision for the team as a PROPOSAL
argument-hint: "[@role] <topic>"
---

Proposal: $ARGUMENTS

If the first word is a role handle, dispatch that role's subagent with the brief below. If there is no handle, the proposal is from @user: draft it from the user's own words, show it to the user, and write it only after they confirm. If there is no topic, use the most important open question in `team/DISCUSSION.md` and say which one you picked.

Brief:

1. Identify the decision owner and the roles who must be consulted from the Decision rights table.
2. Append a TYPE: PROPOSAL message to team/DISCUSSION.md containing:
   - The question to decide
   - 2–4 options, each with pros, cons, cost/effort, and risk
   - Your recommendation and why
   - Who must respond (@mentions) and by when
3. Add a PROPOSED entry to team/DECISIONS.md with the next D-number.
4. End with the Summary block.

A change to extraction, prompts, OCR, models, or eval scorers is a numbered P-### proposal from @ai-engineer-assistant: simple words, the trade-off, the expected score impact, then stop. It is not implemented until the user types `approve change P-###`.
