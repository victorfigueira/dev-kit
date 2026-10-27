---
description: Run the dev-kit squad on a Jira ticket (or propose the top backlog ticket)
argument-hint: "[TICKET_KEY] [continuous] [unattended] [no-update]"
---
# /dev

Run the development squad by following `dev-kit/RUN.md` exactly. Arguments: $ARGUMENTS (`continuous`, `unattended` and `no-update` are modes from the table in RUN.md; any other word is the ticket key or a feature brief).

Stop at both checkpoints in RUN.md (plan approval, delivery approval) and wait for my answer, unless I passed `unattended`. Launch the `pm`, `database-engineer`, `backend-dev`, `frontend-dev` and `qa-verifier` subagents as RUN.md describes, each prompt starting with `dev-kit-agent: <name>`.
