---
name: dev-qa
description: Independent QA quality gate. Runs the test suite, proves every acceptance criterion with file:line and test evidence, and inspects the diff. Read-only.
---

# QA Quality Gate

Launch one subagent with `invoke_subagent(TypeName='self', Role='QA Verifier', Prompt='dev-kit-agent: qa\n...', Workspace='inherit')` that follows `dev-kit/agents/qa.md` and `dev-kit/RULES.md`.

Give it only the path to `dev/PLAN.md`, the base branch (the one the user named, else the one in `dev/project-context.md`, else `main`) and `dev/project-context.md`. Never pass the developers' reports or your own assessment. Show its verdict unchanged.
