# Changelog

## 0.1.0 – 26/10/2026
- Initial release of `dev-kit`: a portable autonomous software engineering squad.
- Orchestrator Architecture: Project Manager / Tech Lead agent (`agents/pm.md`) for ticket triage, technical planning (`PLAN.md`), and dispatching.
- Specialized Engineering Roles:
  - `agents/database.md`: Database Engineer / DBA for schema design, migrations, query tuning, and local test verification.
  - `agents/backend.md`: Backend Developer for API endpoints, business logic, validation schemas, and unit tests.
  - `agents/frontend.md`: Frontend Developer for UI components, state management, design tokens, and accessibility.
  - `agents/qa.md`: QA Engineer & Senior Reviewer (Quality Gate) for running test suites, verifying acceptance criteria, and validating diffs.
- Universal Test Runner (`tools/test_runner.py`): auto-detects and runs test suites across Node.js (Jest, Vitest), Python (pytest), Go, Rust, and .NET.
- Jira Integration (`tools/jira_sync.py`): bidirectional synchronization of tickets, acceptance criteria extraction, and status transitions.
- Environment Adapters: Skills for Antigravity, slash commands for Claude Code, and rules for Cursor.
