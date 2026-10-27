---
name: dev
description: Autonomous engineering squad orchestrator. Checks for updates, executes tickets, and continuously iterates through sprint backlogs automatically.
---

# Autonomous Engineering Squad (`/dev`)

The unified entry point for `dev-kit`. Follows the execution protocol in `dev-kit/RUN.md`.

## Workflow

1. **Update Check & Context Auto-Detection:**
   - Check for updates: `python3 dev-kit/tools/updater.py check --json`. If an update is available, prompt the user:
     `"🔔 A new version of dev-kit is available: v<current> ➔ v<latest>. Would you like to update? [Yes / Skip]"`
     If accepted, run `python3 dev-kit/tools/updater.py update`.
   - If `dev/project-context.md` does not exist, automatically inspect the codebase (`package.json`, `pyproject.toml`, folder structure, test runners, migrations) and initialize `dev/project-context.md`.

2. **Ticket & Backlog Ingestion:**
   - **With Argument (`/dev <TICKET_KEY>`):** Ingests and executes only the specified ticket.
   - **Without Argument (`/dev`):** The Tech Lead enters **Continuous Backlog Mode**:
     * Reads `project_key` from `dev/project-context.md`.
     * Queries `python3 dev-kit/tools/jira_sync.py backlog [PROJECT_KEY]`.
     * Automatically picks the top-priority ticket to begin the sprint.

3. **Technical Plan & Branching (`agents/pm.md`):**
   - Formulate `dev/PLAN.md` with problem statement, explicit Acceptance Criteria, and the Squad Delivery Matrix.
   - Create feature branch: `feat/<TICKET_KEY>-<slug>` from the base branch (`main` or `master`).

4. **Sequential Squad Dispatch:**
   - `database-engineer` (`dev-kit/agents/database.md`) if schema alterations or migrations are required.
   - `backend-dev` (`dev-kit/agents/backend.md`) for domain services, API endpoints, validation, and unit tests.
   - `frontend-dev` (`dev-kit/agents/frontend.md`) for UI components, 4-state lifecycle, and accessibility.

5. **Quality Gate Verification:**
   - Dispatch `qa-verifier` (`dev-kit/agents/qa.md`) to run independent tests:
     ```bash
     python3 dev-kit/tools/test_runner.py --typecheck --lint
     ```
   - Audit test authenticity and verify 100% of Acceptance Criteria.

6. **Delivery & Continuous Auto-Progression (DO NOT STOP):**
   - Create atomic conventional commit and push feature branch: `git push origin feat/<TICKET_KEY>-<slug>`.
   - Generate `dev/PULL_REQUEST.md` (and preserve `dev/PR_<TICKET_KEY>.md`) with Scorecard and Cost metrics (`python3 dev-kit/tools/cost_tracker.py report`).
   - Transition Jira ticket status to *In Review* / *Done*.
   - Print completion summary in chat.
   - **Continuous Progression:** If running in Backlog Mode (`/dev`), **do not wait for another user prompt**. Return to base branch (`git checkout <BASE_BRANCH> && git pull origin <BASE_BRANCH>`), query the next ticket via `python3 dev-kit/tools/jira_sync.py next [PROJECT_KEY]`, and immediately proceed to implement it. Repeat until all sprint tickets are resolved or blocked.
