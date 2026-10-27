---
name: dev
description: dev-kit engineering squad. Plans a Jira ticket, waits for plan approval, implements it with specialist developers, runs the QA quality gate and asks before pushing or updating Jira.
---

# Engineering Squad (`/dev`)

Follow `dev-kit/RUN.md` exactly.

## Arguments
- `<TICKET_KEY>` or a feature brief: work on that ticket only. Without one, propose the top backlog ticket and wait for confirmation.
- `continuous`: after a ticket is delivered, continue with the next backlog ticket.
- `unattended`: skip both checkpoints. Only when the user typed it.
- `no-update`: skip the update check.

## Checkpoints
Stop and wait for the user at Checkpoint 1 (plan approval, before branch, code or Jira changes) and Checkpoint 2 (delivery approval, before push, Jira comment or transition), unless the user passed `unattended`.

## Subagents
Dispatch the specialists with `invoke_subagent`, one at a time in dependency order, each reading its own file in `dev-kit/agents/`. The first line of every prompt is `dev-kit-agent: <name>` (see "Subagents" in `dev-kit/RUN.md`).
