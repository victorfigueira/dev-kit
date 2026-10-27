# /dev-feature

> Alias for `/dev`. See `dev.md` and `dev-kit/RUN.md` for full squad orchestration documentation.

1. Ingest specified ticket or autonomous next ticket via `python3 dev-kit/tools/jira_sync.py next`.
2. Act as the Project Manager (`dev-kit/agents/pm.md`), write `dev/PLAN.md` and create feature branch.
3. Launch specialized subagents in sequence:
   - `database-engineer` (`dev-kit/agents/database.md`)
   - `backend-dev` (`dev-kit/agents/backend.md`)
   - `frontend-dev` (`dev-kit/agents/frontend.md`)
4. Verify with `qa-verifier` (`dev-kit/agents/qa.md`) via `python3 dev-kit/tools/test_runner.py --typecheck --lint`.
5. Once all tests pass, commit and output `dev/PULL_REQUEST.md` with the Quality Gate Scorecard.
