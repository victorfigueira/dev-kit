# dev-kit Guide

Complete documentation for `dev-kit`: a portable autonomous software engineering squad for any codebase.

---

## Contents

- [1. What dev-kit is](#1-what-dev-kit-is)
- [2. How it works](#2-how-it-works)
- [3. Setting up a project](#3-setting-up-a-project)
- [4. Commands](#4-commands)
- [5. The Engineering Squad](#5-the-engineering-squad)
  - [Project Manager & Tech Lead (`pm`)](#project-manager--tech-lead-pm)
  - [Database & Persistence Engineer (`database`)](#database--persistence-engineer-database)
  - [Backend & API Developer (`backend`)](#backend--api-developer-backend)
  - [Frontend & UI Developer (`frontend`)](#frontend--ui-developer-frontend)
  - [QA Engineer & Quality Gate (`qa`)](#qa-engineer--quality-gate-qa)
- [6. Safe Database Engineering](#6-safe-database-engineering)
- [7. Testing & Quality Gate](#7-testing--quality-gate)
- [8. Jira Integration](#8-jira-integration)
- [9. Sibling synergy with audit-kit](#9-sibling-synergy-with-audit-kit)
- [10. Troubleshooting](#10-troubleshooting)

---

## 1. What dev-kit is

`dev-kit` turns your AI assistant (Google Antigravity, Claude Code, Cursor, Windsurf) into a structured, multi-role software engineering team.

Instead of asking a single general-purpose prompt to write fullstack code (which often hallucinates database migrations, forgets validation schemas, or introduces regressions), `dev-kit` separates responsibilities into specialized roles with strict quality gates:

* **Project Manager & Tech Lead**: Architects the technical plan and sequences work.
* **Database Engineer**: Models data, writes safe migrations, and adds indexes.
* **Backend Developer**: Builds typed endpoints, validation schemas, and unit tests.
* **Frontend Developer**: Builds accessible UI components and handles all 4 async states.
* **QA Engineer**: Validates acceptance criteria and prevents broken code from being committed.

Drop `dev-kit/` into any repository and run `/dev` on any task or Jira ticket, or let the Tech Lead propose the top ticket from your backlog. The squad asks for your approval of the plan and of the delivery.

---

## 2. How it works

Every development task follows a strict 6-stage lifecycle:

```mermaid
flowchart TD
    A[1. Ingest Ticket / Task] --> B[2. Technical Plan: dev/PLAN.md]
    B --> CP1{Checkpoint 1: plan approved?}
    CP1 -->|Changes| B
    CP1 -->|Yes| C[3. Git Feature Branch]
    C --> D[4. Specialized Execution]
    
    subgraph Execution Order
        D --> D1[Database Engineer: Migrations & Models]
        D1 --> D2[Backend Developer: APIs & Services]
        D2 --> D3[Frontend Developer: Components & State]
    end
    
    D3 --> E[5. QA Quality Gate]
    
    subgraph Quality Gate
        E --> E1{All Tests Green?}
        E1 -->|No| Fix[Send failure logs back to Dev Agent]
        Fix --> D
        E1 -->|Yes| E2{All ACs Verified?}
        E2 -->|No| Fix
        E2 -->|Yes| E3{Diff Clean & Safe?}
        E3 -->|No| Fix
    end
    
    E3 -->|Approved| F[6. Local Commit & PR Summary]
    F --> CP2{Checkpoint 2: delivery approved?}
    CP2 -->|Yes| P[Push, Jira comment & In Review]
    CP2 -->|No| L[Commit stays local]
```

1. **Ingest:** Reads ticket key (e.g. `AK-101`) from Jira or a prompt brief, extracting explicit Acceptance Criteria.
2. **Plan:** The PM agent writes `dev/PLAN.md` documenting affected files, Squad Delivery Matrix, assumptions, and execution order, and waits for your approval.
3. **Branch:** Creates an isolated git branch (`feat/<TICKET>-<slug>`) and moves the ticket to *In Progress*.
4. **Build:** Dispatches specialists in order (Database $\rightarrow$ Backend $\rightarrow$ Frontend).
5. **Verify:** The QA agent, which sees only the plan and the diff, runs `tools/test_runner.py`, proves each Acceptance Criterion with a `file:line` and a passing test, and inspects `git diff`.
6. **Deliver:** Commits only the planned files, writes `dev/PULL_REQUEST.md` (with Squad Delivery & Quality Gate Scorecard), then asks before pushing and updating Jira.

Arguments: `continuous` carries on with the next backlog ticket after each delivery (checkpoints included) and `unattended` skips both checkpoints. Neither is ever assumed.

---

## 3. Setting up a project

### 1. Install dev-kit
From the root of your target project:
```bash
curl -fsSL https://raw.githubusercontent.com/victorfigueira/dev-kit/main/get.sh | bash
```

To install for one tool only, append its name:
```bash
... | bash -s -- antigravity   # or claude, cursor
```

### 2. Configure Git Ignore
Keep squad working notes and temporary files out of git:
```bash
echo "dev/" >> .gitignore
echo "dev-kit/" >> .gitignore
```

### 3. Configure Project Context (Optional)
Copy the template to customize your stack's specific commands:
```bash
mkdir -p dev
cp dev-kit/templates/project-context.md dev/project-context.md
```
Edit `dev/project-context.md` to specify:
* Your exact test command (e.g. `npm test`, `pytest`, `cargo test`).
* Typecheck and linting commands (`npm run typecheck`, `mypy .`).
* Database migration commands (`npx prisma migrate dev`, `alembic upgrade head`).

---

## 4. Commands

### Chat Commands (Slash Commands)

| Command | Usage | Description |
|---|---|---|
| `/dev` | `/dev [TICKET_KEY] [continuous] [unattended] [no-update]` | Runs the squad: PM plans and waits for approval, devs implement, QA verifies, then it asks before pushing and updating Jira. |
| `/dev-feature` | `/dev-feature <TICKET_KEY>` | Alias for `/dev`. |
| `/dev-qa` | `/dev-qa` | Runs the QA Quality Gate independently on the current git diff. |
| `/dev-check-update` | `/dev-check-update` | Checks GitHub for a newer dev-kit, summarises what is new and installs it after you confirm. |

### CLI Tools

All scripts run with standard Python 3 and zero third-party dependencies:

```bash
# Run universal test suite detector & runner
python3 dev-kit/tools/test_runner.py [--typecheck] [--lint] [--json]

# Fetch Jira ticket details and acceptance criteria
python3 dev-kit/tools/jira_sync.py fetch <TICKET_KEY> [--json]

# Transition Jira ticket status
python3 dev-kit/tools/jira_sync.py transition <TICKET_KEY> "In Progress"

# Post comment with PR test summary
python3 dev-kit/tools/jira_sync.py comment <TICKET_KEY> "PR ready with tests passing."

# Check for dev-kit updates (installed and latest version, changelog since yours)
python3 dev-kit/tools/updater.py check [--json]

# Install the latest version (the agent asks you first, see UPDATE.md)
python3 dev-kit/tools/updater.py update

# Record the ticket start time (RUN.md Step 1), then report tokens and USD cost per role since then
python3 dev-kit/tools/cost_tracker.py start --ticket <TICKET_KEY>
python3 dev-kit/tools/cost_tracker.py report [--since ISO] [--model MODEL] [--json]

# Raw token counts from the Claude Code or Antigravity session files
python3 dev-kit/tools/usage_report.py --since 2026-10-27T10:00:00Z
```

---

## 5. The Engineering Squad

The main session orchestrates and each role runs as a subagent in its own context. Claude Code installs them in `.claude/agents/` with restricted tools (`pm` and the developers can write; `qa-verifier` is read-only). Antigravity launches them with `invoke_subagent`. Every subagent prompt starts with `dev-kit-agent: <name>` (`pm`, `database`, `backend`, `frontend`, `qa`). If an existing `.claude/agents/<name>.md` in your project is not a dev-kit file, the installer leaves it alone and says so.

### Project Manager & Tech Lead (`pm`)
* **File:** `dev-kit/agents/pm.md`
* **Role:** Architectural planning, task sequencing, and squad dispatch.
* **Output:** `dev/PLAN.md`.
* **Safety Rule:** The PM never writes application code directly. Enforces strict anti-scope creep, manages ambiguity via documented assumptions, and stops repair loops via a 3-iteration circuit breaker.

### Database & Persistence Engineer (`database`)
* **File:** `dev-kit/agents/database.md`
* **Role:** Data modeling, schema migrations, query performance, and test seeds.
* **Safety Rule:** Runs migrations exclusively against local Docker or test databases. Enforces Expand & Contract migrations, safe backfills for existing rows, and PII hashing/encryption.

### Backend & API Developer (`backend`)
* **File:** `dev-kit/agents/backend.md`
* **Role:** REST/GraphQL endpoints, business logic, validation schemas, and automated unit tests.
* **Safety Rule:** Mandatory validation schemas on all inputs, strict AuthN/AuthZ and IDOR guards, structured error handling without database leakage, and deterministic offline mocking of 3rd-party services.

### Frontend & UI Developer (`frontend`)
* **File:** `dev-kit/agents/frontend.md`
* **Role:** UI components, client state, styling tokens, and accessibility (a11y).
* **Safety Rule:** Mandatory implementation of all 4 async states (Loading, Error, Empty, Success), mirrored form validations, error boundaries, and shared contract type safety.

### QA Engineer & Quality Gate (`qa`)
* **File:** `dev-kit/agents/qa.md`
* **Role:** Independent quality verification, test authenticity audits, and diff inspection.
* **Independence:** Receives only `dev/PLAN.md`, the base branch, the project context and its own previous report. Developer reports, the orchestrator's opinion and status marks in the plan are ignored.
* **Burden of proof:** Each Acceptance Criterion is Verified only with an implementation `file:line` and a passing test that asserts it (or Verified (static) with a reason when no test can apply). "The suite passes", "it is handled elsewhere" without a location, or a ticked checkbox do not count.
* **Safety Rule:** The Quality Gate is non-negotiable. Rejects failing suites, tautological/dummy tests, or unproven acceptance criteria using structured `CHANGES REQUESTED` remediation reports, with an evidence table per criterion.

---

## 6. Safe Database Engineering

Database mistakes are the most dangerous and costly to revert in production. `dev-kit` enforces strict persistence standards in `RULES.md`:

### The Expand & Contract Pattern
When changing a schema, never execute breaking changes in a single step:
1. **Expand:** Add new columns as nullable (`NULL`) or with safe default values.
2. **Migrate:** Write code that reads from both old and new columns, writing to the new column.
3. **Contract:** Remove the old deprecated column in a subsequent release after data is confirmed.

### Reversible Migrations
Every migration generated by the `database-engineer` must include both:
* `up`: applies the change.
* `down`: cleanly rolls back the change without leaving orphaned rows or corrupted schemas.

---

## 7. Testing & Quality Gate

`dev-kit/tools/test_runner.py` automatically detects your project's technology stack:
* **Node.js:** detects `package.json` with npm, pnpm, yarn, or bun.
* **Python:** detects `pytest.ini`, `pyproject.toml`, or `requirements.txt`.
* **Go:** detects `go.mod` (`go test ./...`).
* **Rust:** detects `Cargo.toml` (`cargo test`, `cargo check`, `cargo clippy`).
* **.NET:** detects `*.csproj` or `*.sln` (`dotnet test`).

You can also define custom commands in `dev/project-context.md`.

---

## 8. Jira Integration

`dev-kit` integrates natively with Atlassian Jira Cloud using standard environment variables:

```bash
export JIRA_BASE_URL="https://your-company.atlassian.net"
export JIRA_USER_EMAIL="developer@your-company.com"
export JIRA_API_TOKEN="your-atlassian-api-token"
```

* **Offline Fallback:** If Jira credentials are not present, `jira_sync.py` falls back gracefully to local mock mode so developers can run `dev-kit` without network access.
* **Acceptance Criteria Extraction:** Automatically parses markdown checkboxes (`- [ ]`) and numbered lists (`AC-1:`) from the ticket description.
* **Backlog & Prioritization:** Run `python3 dev-kit/tools/jira_sync.py backlog [PROJECT_KEY]` or `next [PROJECT_KEY]` to fetch and rank sprint tickets. `/dev` without a key proposes the top one and waits for confirmation.

---

## 9. Sibling synergy with audit-kit

`audit-kit` and `dev-kit` form a closed-loop engineering cycle:

1. **Audit:** Run `/audit` with `audit-kit`. It identifies security vulnerabilities (with CVSS scores), technical debt, and performance bottlenecks.
2. **Ticket Filing:** Run `/audit-jira` to create structured tickets in your backlog.
3. **Development:** Run `/dev-feature <TICKET_KEY>` with `dev-kit`. The squad designs the fix, writes the code, passes tests, and opens a PR.
4. **Verification:** Run `/audit-diff` with `audit-kit` on the PR. It validates that the vulnerability is resolved and automatically updates the project audit score.

---

## 10. Troubleshooting

### Tests fail during the QA Quality Gate
Inspect the failure output printed in chat. The PM orchestrator will re-dispatch the developer agent with the exact failure stack trace. You can also run:
```bash
python3 dev-kit/tools/test_runner.py
```
directly to inspect the stdout/stderr.

### Database migration fails
Confirm that your local database container (e.g. Docker PostgreSQL) is running. Check connection strings in `.env.local` or `dev/project-context.md`.
