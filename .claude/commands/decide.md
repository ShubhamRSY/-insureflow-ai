---
description: Close out PROPOSED decisions; the user's own decisions are decided by the user
argument-hint: "[@role | user decision: <text>]"
---

Argument: $ARGUMENTS

**No argument, or the owner is @user.** In `team/DECISIONS.md` find PROPOSED decisions owned by @user, and in `team/DISCUSSION.md` find pending P-### proposals. For each, show the user: the question, the options with trade-offs, every response (SUPPORT / CONCERN / OBJECTION), and any unresolved veto with what would resolve it. Give no recommendation of your own; quote the consulted roles'. Then stop and wait. Do not decide.

**`user decision: <text>`, or the user answers.** Record it in `team/DECISIONS.md` in the standard format with owner `@user` and rationale "The user said this directly.", using the user's words. `approve change P-###` counts only as those exact words typed by the user. Post a TYPE: UPDATE from @user in `team/DISCUSSION.md` and ask @pm to create follow-up tasks. If the decision accepts an option an unresolved veto blocks, say so and ask the user to confirm before recording.

**A role handle.** Dispatch that role's subagent with this brief:

1. In team/DECISIONS.md, find PROPOSED decisions where you are the owner.
2. Read the PROPOSAL and every response to it in team/DISCUSSION.md.
3. If any veto (OBJECTION from @compliance, @model-risk or @responsible-ai) is unresolved, you may not accept an option it blocks. Choose another option or ask for the resolution.
4. Decide. Update the entry to ACCEPTED with the decision, rationale, and any dissent recorded fairly.
5. Post a TYPE: UPDATE in DISCUSSION.md announcing it, and ask @pm to create follow-up tasks.
6. End with the Summary block.
