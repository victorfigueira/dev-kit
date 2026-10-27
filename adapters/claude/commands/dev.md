---
description: Run the dev-kit squad on a Jira ticket (or the top backlog ticket)
argument-hint: "[TICKET_KEY] [no-update]"
---
# /dev

Run the autonomous development squad following `dev-kit/RUN.md`. Arguments: $ARGUMENTS (`no-update` skips the update check; any other word is the ticket key).

1. Check for dev-kit updates following Step 0 of `dev-kit/RUN.md` (ask before installing). Skip it if the arguments contain `no-update`.
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
7. Once green, commit, push branch, log cost to `dev/COSTS.md` and Jira comment (`python3 dev-kit/tools/cost_tracker.py log --ticket <TICKET_KEY> ...`), output `dev/PULL_REQUEST.md`, and transition Jira ticket.
8. **Continuous Progression:** If in Backlog Mode, checkout base branch, query next ticket, and seamlessly proceed to the next ticket automatically without waiting for another prompt.
