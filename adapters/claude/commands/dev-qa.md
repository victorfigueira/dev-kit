# /dev-qa

Run the QA Quality Gate following `dev-kit/agents/qa.md`:

1. Run `python3 dev-kit/tools/test_runner.py --typecheck --lint`.
2. Verify all Acceptance Criteria in `dev/PLAN.md`.
3. Inspect `git diff` against base branch.
4. Output verdict (APPROVED or CHANGES REQUESTED).
