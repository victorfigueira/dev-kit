# /dev

Run the autonomous development squad following `dev-kit/RUN.md`:

1. Check for dev-kit updates: `python3 dev-kit/tools/updater.py check --json`. If available, prompt user and update.
2. If `dev/project-context.md` is missing, auto-detect the project stack and initialize it.
3. If no ticket argument is passed, enter **Continuous Backlog Mode**:
   - Query project backlog: `python3 dev-kit/tools/jira_sync.py next`.
   - Take the top-priority ticket.
4. Act as Project Manager (`dev-kit/agents/pm.md`), write `dev/PLAN.md`, and create feature branch.
5. Launch specialized subagents in sequence:
   - `database-engineer` (`dev-kit/agents/database.md`)
   - `backend-dev` (`dev-kit/agents/backend.md`)
   - `frontend-dev` (`dev-kit/agents/frontend.md`)
6. Verify with `qa-verifier` (`dev-kit/agents/qa.md`) via `python3 dev-kit/tools/test_runner.py --typecheck --lint`.
7. Once green, commit, push branch, output `dev/PULL_REQUEST.md` with Scorecard and Cost metrics, and transition Jira ticket.
8. **Continuous Progression:** If in Backlog Mode, checkout base branch, query next ticket, and seamlessly proceed to the next ticket automatically without waiting for another prompt.
