# /dev-feature

Take a Jira ticket or feature description and run the autonomous development squad following `dev-kit/RUN.md`:

1. Read ticket details with `python3 dev-kit/tools/jira_sync.py fetch "$1"`.
2. Act as the Project Manager (`dev-kit/agents/pm.md`), write `dev/PLAN.md` and create feature branch.
3. Launch specialized subagents in sequence:
   - `database-engineer` (`dev-kit/agents/database.md`)
   - `backend-dev` (`dev-kit/agents/backend.md`)
   - `frontend-dev` (`dev-kit/agents/frontend.md`)
4. Verify with `qa-verifier` (`dev-kit/agents/qa.md`) via `python3 dev-kit/tools/test_runner.py`.
5. Once all tests pass, commit and output `dev/PULL_REQUEST.md`.
