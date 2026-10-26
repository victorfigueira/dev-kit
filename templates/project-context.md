# Project Context for dev-kit

This file configures the repository environment for the autonomous development squad.

## 1. Project Overview
- **Name:** my-project
- **Primary Language(s):** TypeScript / Python / Go
- **Frameworks:** Next.js / Express / FastAPI / Django / Spring Boot
- **Package Manager:** npm | pnpm | yarn | pip | poetry | cargo | go

## 2. Testing & Verification Commands
Commands executed by the `qa-verifier` agent to validate code changes:
- **Unit & Integration Tests:** `npm test` or `pytest`
- **Type Checking:** `npm run typecheck` or `mypy .`
- **Linting & Code Style:** `npm run lint` or `flake8`
- **Coverage Check (optional):** `npm run test:coverage`

## 3. Database & Migrations
Conventions used by the `database-engineer` agent:
- **Database Engine:** PostgreSQL / MySQL / SQLite / MongoDB / Redis
- **ORM / Migration Tool:** Prisma / TypeORM / Alembic / Flyway / Drizzle / Knex
- **Run Migrations (Local/Test):** `npx prisma migrate dev` or `alembic upgrade head`
- **Rollback Migration:** `npx prisma migrate reset` or `alembic downgrade -1`
- **Seed Command:** `npm run db:seed`

## 4. Git & Branching Strategy
- **Base Branch:** `main` (or `develop`)
- **Branch Naming Pattern:** `feat/<ticket-key>-<short-description>` or `fix/<ticket-key>-<short-description>`
- **Commit Convention:** Conventional Commits (`feat: ...`, `fix: ...`, `refactor: ...`)

## 5. Jira Integration (Optional)
- **Project Key:** AK (or your Jira project key)
- **Default Issue Type:** Task / Story / Bug
- **In Progress Transition ID/Name:** In Progress
- **Done/Review Transition ID/Name:** In Review
