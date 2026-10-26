# Technical Plan: [TICKET_KEY] - [TITLE]

- **Date:** YYYY-MM-DD
- **Target Branch:** feat/[TICKET_KEY]-[SLUG]
- **Status:** Proposed | In Progress | Ready for QA | Completed
- **Assigned Agents:** [database-engineer, backend-dev, frontend-dev, qa-verifier]

---

## 1. Problem Statement & Requirements
Summary of the ticket or user story and the business need.

### Acceptance Criteria (from Jira/Spec)
- [ ] AC-1: Detail of criterion 1
- [ ] AC-2: Detail of criterion 2
- [ ] AC-3: Detail of criterion 3

---

## 2. Technical Architecture & Impact Analysis

### Scope of Changes
- **Database / Schema:** [Yes / No]
- **API / Backend:** [Yes / No]
- **UI / Frontend:** [Yes / No]
- **Infra / Config:** [Yes / No]

### Affected Files
- `path/to/schema/or/migration`: Description of change
- `path/to/api/controller.ts`: Description of change
- `path/to/ui/component.tsx`: Description of change
- `tests/path/to/test.spec.ts`: New tests to add

---

## 3. Execution Plan (Sequential Steps)

### Step 1: Database & Data Modeling (`database-engineer`)
*Skip if no database changes are required.*
1. Create migration file for `table_name`.
2. Add foreign keys, constraints, and indexes.
3. Run migration in local/test database.
4. Verify rollback (`down` migration) and seed data.

### Step 2: Backend API & Business Logic (`backend-dev`)
1. Implement or update domain models and data access layer.
2. Create/update service logic with input validation (Zod, Pydantic, etc.).
3. Implement HTTP endpoints / controllers and error handling.
4. Add unit and integration tests covering positive, negative, and edge cases.

### Step 3: Frontend UI & Client State (`frontend-dev`)
1. Create or update reusable UI components using design system tokens.
2. Wire API client calls with loading, error, and empty states.
3. Ensure accessibility (ARIA labels, keyboard navigation) and responsiveness.
4. Add component / snapshot tests if applicable.

### Step 4: Quality Gate & Verification (`qa-verifier`)
1. Run full project test suite (`test_runner.py`).
2. Verify all Acceptance Criteria against the implementation.
3. Review `git diff` for dead code, security flaws, or performance regressions.
4. Approve for commit and pull request.
