---
name: dev-feature
description: Autonomous feature development squad. Reads ticket/spec, architects PLAN.md, dispatches specialized developers, and enforces QA Quality Gate before commit.
---

# Autonomous Feature Development Squad

Follow the execution protocol in `dev-kit/RUN.md`.

## Workflow
1. Ingest the Jira ticket key or feature description from user input:
   ```bash
   python3 dev-kit/tools/jira_sync.py fetch "$1" --json
   ```
2. Act as the Project Manager & Tech Lead (`dev-kit/agents/pm.md`):
   - Formulate technical specification in `dev/PLAN.md`.
   - Setup feature branch `feat/<TICKET>-<slug>`.
3. Dispatch specialized developer subagents (`invoke_subagent`):
   - `database-engineer` (`dev-kit/agents/database.md`) if schema/migrations are required.
   - `backend-dev` (`dev-kit/agents/backend.md`) for API endpoints and business logic.
   - `frontend-dev` (`dev-kit/agents/frontend.md`) for UI and client state.
4. Run QA Quality Gate (`dev-kit/agents/qa.md`):
   ```bash
   python3 dev-kit/tools/test_runner.py --typecheck --lint
   ```
5. If green, commit changes and prepare `dev/PULL_REQUEST.md`.
