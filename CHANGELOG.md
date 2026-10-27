# Changelog

## 0.4.6 – 27/10/2026
- Added automatic environment-aware AI model detection in `tools/cost_tracker.py`: automatically defaults to `gemini-2.0-flash` ($0.10/M input, $0.40/M output) when running inside Google Antigravity / Gemini agents instead of Claude Sonnet.
- Added alias resolution for Gemini models (e.g. `gemini 3.8 flash medium`, `gemini flash`).
- Updated `adapters/antigravity/skills/dev/SKILL.md` to pass `--model gemini-2.0-flash` explicitly during ticket cost logging.

## 0.4.5 – 27/10/2026
- Added automatic Jira credential discovery in `tools/jira_sync.py`: seamlessly detects Jira credentials from `.env`, `.env.local`, `dev/.env`, environment variables (`JIRA_BASE_URL`, `JIRA_USER_EMAIL`/`JIRA_EMAIL`, `JIRA_API_TOKEN`), and MCP configurations (`~/.gemini/antigravity/mcp_config.json`, `~/.cursor/mcp.json`, `~/.claude/mcp.json`) with zero manual setup.
- Added macOS SSL certificate fallback (`safe_urlopen`) to prevent `CERTIFICATE_VERIFY_FAILED` errors during Jira Cloud REST API calls on macOS Python installations.
- Enhanced Jira comment formatting into native Atlassian Document Format (ADF) multiline paragraphs.

## 0.4.4 – 27/10/2026
- Fixed argument parsing in `get.sh` and `install.sh` to allow passing the tool name directly (e.g. `| bash -s -- antigravity`) without misinterpreting it as a target directory.
- Resolved issue where installer created a nested `antigravity/dev-kit` folder instead of updating the root `./dev-kit/` directory.

## 0.4.3 – 27/10/2026
- Added silent zero-prompt auto-updating mode via `tools/updater.py auto`.
- Updated `/dev` workflow across all adapters (`adapters/antigravity/skills/dev/SKILL.md`, `adapters/claude/commands/dev.md`) and `RUN.md` Step 0 to automatically check and apply updates without interrupting execution.
- Added comprehensive unit tests for `auto` update command in `tools/updater_test.py`.

## 0.4.2 – 27/10/2026
- Added persistent cumulative cost ledger (`dev/COSTS.md` and `dev/cost_ledger.json`) via `tools/cost_tracker.py log`.
- Enforced automated Jira comment posting upon ticket completion with exact token consumption, USD development cost, branch link, and QA status.
- Updated `RUN.md` Step 6, `agents/pm.md`, and adapters to execute cost logging and Jira commenting as an atomic hand-off command.

## 0.4.1 – 27/10/2026
- Enforced Autonomous Continuous Sprint Mode in `/dev`: when run without ticket arguments, the Tech Lead automatically switches back to the base branch and proceeds to the next backlog ticket without pausing or waiting for another user prompt.
- Added Step 8 in `RUN.md` defining the continuous backlog auto-progression loop.
- Updated `agents/pm.md`, `adapters/antigravity/skills/dev/SKILL.md`, `adapters/claude/commands/dev.md`, and `adapters/cursor/rules/dev.mdc`.

## 0.4.0 – 27/10/2026
- Added Token & USD Cost Calculation Engine (`tools/cost_tracker.py`) with support for Claude, Gemini, and OpenAI models.
- Added comprehensive unit test suite in `tools/cost_tracker_test.py`.
- Integrated token usage and USD cost reporting into `templates/PULL_REQUEST.md` and chat completion summaries.
- Updated `RUN.md` Step 6 and Step 7, `agents/pm.md`, `README.md`, and `docs/GUIDE.md` with cost estimation protocols.

## 0.3.0 – 27/10/2026
- Added self-updating engine (`tools/updater.py`) for automatic version checking and seamless one-click installation of updates.
- Integrated update verification into `/dev` workflow (Step 0): checks GitHub for newer releases and prompts the user before proceeding.
- Added comprehensive unit test suite in `tools/updater_test.py`.
- Updated `RUN.md`, `README.md`, and `docs/GUIDE.md` with self-updating commands and documentation.

## 0.2.0 – 27/10/2026
- Unified `/dev` command: single intuitive entry point across Antigravity, Claude Code, and Cursor (`/dev-feature` preserved as alias).
- Autonomous Backlog Orchestration: Tech Lead automatically queries and ranks Jira sprint backlogs (`python3 tools/jira_sync.py backlog` and `next`) when no ticket key is passed.
- Transparent Context Auto-detection: Running `/dev` on a fresh project automatically detects the tech stack and initializes `dev/project-context.md` without manual preliminary steps.
- Sequential Queue Progression: Tech Lead coordinates ticket resolution, reports sign-off, and seamlessly moves to the next prioritized ticket in the sprint.
- Updated `tools/jira_sync.py`, `tools/jira_sync_test.py`, `agents/pm.md`, `install.sh`, `README.md`, `RUN.md`, and `docs/GUIDE.md`.

## 0.1.2 – 26/10/2026
- Added Squad Delivery & Quality Gate Scorecard to `templates/PULL_REQUEST.md` for clear layer-by-layer visual reporting (Database, Backend, Frontend, QA).
- Added Squad Delivery Matrix and Assumptions & Risks sections to `templates/PLAN.md`.
- Updated `RUN.md` Step 6 and Step 7 with scorecard generation and structured chat delivery reporting.
- Updated `README.md` and `docs/GUIDE.md` documentation to reflect the new scorecard artifact structure.

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
