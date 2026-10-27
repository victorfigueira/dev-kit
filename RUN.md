# dev-kit Execution Protocol

This document defines the exact step-by-step procedure the Project Manager / Tech Lead orchestrator follows to resolve tickets and implement features.

---

## The Workflow

```mermaid
sequenceDiagram
    actor U as User / Jira
    participant PM as Project Manager
    participant DB as Database Engineer
    participant BE as Backend Developer
    participant FE as Frontend Developer
    participant QA as QA Verifier
    participant G as Git & PR

    U->>PM: /dev [TICKET_KEY]
    alt No Ticket Provided
        PM->>U: Query Jira backlog (python3 tools/jira_sync.py next)
    end
    PM->>U: Read requirements & Acceptance Criteria
    PM->>PM: Formulate dev/PLAN.md
    PM->>G: git checkout -b feat/<TICKET>-<slug>
    opt Database Changes
        PM->>DB: Dispatch database-engineer
        DB->>DB: Migrations, schema, seeds, local test
        DB-->>PM: Schema & types ready
    end
    opt Backend Changes
        PM->>BE: Dispatch backend-dev
        BE->>BE: Endpoints, validation, services, unit tests
        BE-->>PM: API contract & services ready
    end
    opt Frontend Changes
        PM->>FE: Dispatch frontend-dev
        FE->>FE: Components, client state, a11y
        FE-->>PM: UI components ready
    end
    PM->>QA: Dispatch qa-verifier (Quality Gate)
    QA->>QA: Run test suite & verify ACs
    alt Tests Fail or Missing Criteria
        QA-->>PM: Report failure logs
        PM->>BE: Re-dispatch developer to fix
    else Tests Green
        QA-->>PM: Quality Gate APPROVED
        PM->>G: Atomic commit & push
        PM->>U: Report PR ready & transition Jira ticket
    end
```

---

## Step-by-step Instructions

### Step 0: Check for dev-kit Updates
1. Check and automatically apply any newer version of `dev-kit`:
   ```bash
   python3 dev-kit/tools/updater.py auto
   ```
   If updated, `dev-kit` synchronizes tools, agents, and skills silently. If offline or already up-to-date, it continues immediately without interruption.

### Step 1: Ingest Ticket & Context
1. If `dev/project-context.md` does not exist, automatically inspect the repository (`package.json`, test scripts, migrations) and initialize it.
2. Ingest the task:
   - **Specified Ticket:** Read key from arguments (e.g. `PAS-101`) or user feature brief:
     ```bash
     python3 dev-kit/tools/jira_sync.py fetch <TICKET_KEY> --json
     ```
   - **Autonomous Backlog Mode (No argument passed):** The Tech Lead queries the project backlog and takes the top prioritized ticket:
     ```bash
     python3 dev-kit/tools/jira_sync.py next
     ```
3. Transition ticket status to **In Progress**:
   ```bash
   python3 dev-kit/tools/jira_sync.py transition <TICKET_KEY> "In Progress"
   ```
4. Read `dev/project-context.md` to verify tech stack, base branch, package manager, and test commands.

### Step 2: Formulate Technical Plan
1. Create `dev/` directory if missing.
2. Copy `dev-kit/templates/PLAN.md` to `dev/PLAN.md`.
3. Fill in:
   - Problem statement and numbered Acceptance Criteria (`AC-1`, `AC-2`...).
   - Architectural scope (Database, Backend, Frontend).
   - List of exact files to modify or create.
   - Ordered execution steps.

### Step 3: Setup Feature Branch
1. Ensure the working tree is clean on the base branch (`main`).
2. Pull latest changes:
   ```bash
   git checkout main && git pull origin main
   ```
3. Create and switch to the feature branch:
   ```bash
   git checkout -b feat/<TICKET_KEY>-<slug>
   ```

### Step 4: Dispatch Specialized Developers
Dispatch the required specialists in sequential dependency order:

1. **Database Layer (`dev-kit/agents/database.md`)**:
   - *When needed:* Schema alterations, new tables, migrations, database queries.
   - Writes migrations, adds indexes, updates ORM models.
   - Runs migration against local Docker/test database and tests rollback.

2. **Backend Layer (`dev-kit/agents/backend.md`)**:
   - *When needed:* Endpoints, controllers, services, business logic.
   - Implements strict validation schemas (Zod/Pydantic).
   - Writes unit and integration tests.

3. **Frontend Layer (`dev-kit/agents/frontend.md`)**:
   - *When needed:* Pages, components, hooks, client state, styling.
   - Implements loading, error, empty, and success states.
   - Ensures accessibility (a11y) and responsive design.

### Step 5: Quality Gate & Verification (`dev-kit/agents/qa.md`)
Run the independent quality gate:
```bash
python3 dev-kit/tools/test_runner.py --typecheck --lint
```
1. **Zero Failing Tests:** If tests fail, the QA verifier reports failure output back to the PM. The PM re-engages the responsible developer agent to fix the failure.
2. **Acceptance Criteria Verification:** Every AC listed in `dev/PLAN.md` must be validated against actual code.
3. **Diff Hygiene:** Check `git diff` to ensure no temporary files, debug statements, or secrets are tracked.

### Step 6: Git Commit & Hand-off
Once QA approves:
1. Stage modified files and make an atomic conventional commit:
   ```bash
   git add .
   git commit -m "feat(<scope>): <concise description of changes>"
   ```
2. Log development cost, update cumulative `dev/COSTS.md` ledger, and post comment to Jira:
   ```bash
   python3 dev-kit/tools/cost_tracker.py log --ticket <TICKET_KEY> --summary "<TITLE>" --branch "feat/<TICKET_KEY>-<slug>"
   ```
   Embed the cost table and token metrics into `dev/PULL_REQUEST.md` (and preserve `dev/PR_<TICKET_KEY>.md`).
3. Push the feature branch to origin:
   ```bash
   git push origin feat/<TICKET_KEY>-<slug>
   ```
4. If Jira is configured, transition ticket status:
   ```bash
   python3 dev-kit/tools/jira_sync.py transition <TICKET_KEY> "In Review"
   ```

### Step 7: Chat Summary
Report completion in chat (maximum 15 lines):
```
Squad task complete · [TICKET_KEY]: <Title>
Branch: feat/<TICKET_KEY>-<slug>
Delivery Scorecard:
  • Database: [0 migrations · up/down verified]
  • Backend: [<n> endpoints · <n> unit tests]
  • Frontend: [<n> components · 4 states verified]
  • Quality Gate: 🟢 APPROVED (<n> tests green · typecheck clean · lint clean)
Cost: $0.27 USD (48,250 tokens · Claude 3.7 Sonnet)
Acceptance Criteria: All <n> criteria verified
Pull Request summary: dev/PULL_REQUEST.md
Jira: [TICKET_KEY] transitioned to In Review
```

### Step 8: Continuous Backlog Auto-Progression (Do Not Halt)
When running in Autonomous Backlog Mode (`/dev` without a specific ticket key):
1. **Never wait for another user `/dev` command.**
2. Switch back to base branch:
   ```bash
   git checkout <BASE_BRANCH> && git pull origin <BASE_BRANCH>
   ```
3. Query the next ticket:
   ```bash
   python3 dev-kit/tools/jira_sync.py next
   ```
4. If another pending ticket exists (e.g. `PAS-2`), announce:
   `"🚀 Proceeding to next backlog ticket: PAS-2 · <Summary>..."`
   and immediately begin executing Step 2 for `PAS-2`.
5. Repeat this loop automatically until all sprint tickets are resolved, a QA circuit-breaker halts execution, or the user pauses.
