---
description: Run the dev-kit QA quality gate on the current change (read-only)
argument-hint: "[base branch]"
---
# /dev-qa

Launch the `qa-verifier` subagent with the prompt header `dev-kit-agent: qa` to follow `dev-kit/agents/qa.md`. Give it only the path to `dev/PLAN.md`, the base branch ($ARGUMENTS, else the one in `dev/project-context.md`, else `main`) and `dev/project-context.md`. Show me its verdict unchanged.
