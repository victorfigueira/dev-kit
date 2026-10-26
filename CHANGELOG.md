# Changelog

## 0.1.1 – 26/10/2026
- Enhanced agent definitions across all 5 specialized roles (`pm`, `database`, `backend`, `frontend`, `qa`) with operational knowledge, safety protocols, and execution guardrails.
- Project Manager & Tech Lead (`agents/pm.md`): added ambiguity & assumption handling, context handoff bundles for subagent dispatching, strict anti-scope creep guardrails, and a 3-iteration circuit breaker on repair loops.
- Database Engineer (`agents/database.md`): added native tooling alignment from `project-context.md`, phased backfill strategies for existing data, PII and sensitive data encryption, and production-safe non-blocking indexing.
- Backend Developer (`agents/backend.md`): added AuthN/AuthZ guards, IDOR and OWASP security best practices, shared contract typing, and deterministic offline mocking of external services.
- Frontend Developer (`agents/frontend.md`): added comprehensive form state & validation mirroring, shared contract type safety, error boundary isolation, and accessibility keyboard/ARIA standards.
- QA Engineer (`agents/qa.md`): added anti-tautology test quality verification, adversarial edge case audits, test state isolation checks, and structured `CHANGES REQUESTED` failure reporting.
- Updated `RULES.md` and `docs/GUIDE.md` to align with the enhanced agent standards.

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
- Comprehensive Guide: added complete reference documentation in `docs/GUIDE.md`.
