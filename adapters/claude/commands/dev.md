# /dev

Take a Jira ticket, feature brief, or autonomously ingest the next ticket from the project backlog following `dev-kit/RUN.md`:

1. Check for dev-kit updates: `python3 dev-kit/tools/updater.py check --json`. If an update is available, prompt the user to install via `python3 dev-kit/tools/updater.py update`.
2. If `dev/project-context.md` is missing, auto-detect the project stack and initialize it.
3. If no ticket or argument is provided, the Tech Lead queries the project backlog via `python3 dev-kit/tools/jira_sync.py next`.
4. Act as the Project Manager (`dev-kit/agents/pm.md`), write `dev/PLAN.md` with the Squad Delivery Matrix, and create a feature branch.
5. Launch specialized subagents in sequence:
   - `database-engineer` (`dev-kit/agents/database.md`)
   - `backend-dev` (`dev-kit/agents/backend.md`)
   - `frontend-dev` (`dev-kit/agents/frontend.md`)
6. Verify with `qa-verifier` (`dev-kit/agents/qa.md`) via `python3 dev-kit/tools/test_runner.py --typecheck --lint`.
7. Once green, commit, output `dev/PULL_REQUEST.md` with the Quality Gate Scorecard, transition Jira ticket, and report next queue item.
