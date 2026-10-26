---
name: dev-qa
description: Independent QA Quality Gate. Executes test suites, validates acceptance criteria, and inspects git diffs.
---

# QA Quality Gate

Follow `dev-kit/agents/qa.md` and `dev-kit/RULES.md`.

## Execution
1. Run the universal test runner:
   ```bash
   python3 dev-kit/tools/test_runner.py --typecheck --lint
   ```
2. Verify all Acceptance Criteria in `dev/PLAN.md`.
3. Inspect `git diff` against base branch `main`.
4. Output APPROVED or CHANGES REQUESTED verdict.
