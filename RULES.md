# dev-kit Engineering Rules & Standards

These rules govern all autonomous agents operating in `dev-kit`. Every agent must strictly adhere to these principles.

---

## 1. General Engineering Principles

1. **Quality over Speed:** Working code that passes all tests and meets acceptance criteria is better than fast, broken code.
2. **Never Break the Build:** A branch must never be merged or submitted for PR with failing tests, type errors, or unresolved lint warnings.
3. **Preserve Existing Code & Comments:** Do not delete unrelated comments, docstrings, or working logic unless explicitly directed by the ticket.
4. **Minimal Blast Radius:** Modify only the files strictly necessary to fulfill the ticket requirements. Do not perform gratuitous refactoring of unrelated modules.
5. **Circuit Breaker on Feedback Loops:** Automated repair loops between QA and developer agents are capped at 3 iterations. If issues persist after 3 attempts, halt execution, document roadblocks, and request human guidance.

---

## 2. Git & Branching Protocol

1. **Feature Branches:** Always create an isolated branch from the latest base branch (`main`):
   ```bash
   git checkout -b feat/<TICKET_KEY>-<slug>
   ```
2. **Atomic Conventional Commits:** Use standard conventional commit prefixes:
   - `feat(<scope>): add user favorite comments endpoint`
   - `fix(<scope>): resolve null pointer on empty profile`
   - `test(<scope>): add unit tests for discount calculation`
3. **Clean Diffs:** Review `git diff` before committing. Ensure no temporary test files, secrets, or `.env` files are tracked.

---

## 3. Database & Persistence Standards (`database-engineer`)

1. **Local & Test Isolation Only:** Migrations and queries may ONLY be executed against local Docker containers or test databases. Never connect directly to staging or production.
2. **Safe Migration (Expand & Contract Pattern):**
   - Adding a new column: Always make it nullable (`NULL`) or provide a safe default value.
   - Renaming/dropping a column: Do not drop immediately; create the new column, sync data, deprecate, and remove in a separate future release.
   - Backfilling data: For columns intended to be `NOT NULL`, write staged migrations (create nullable $\rightarrow$ backfill existing data $\rightarrow$ apply `NOT NULL`).
3. **Reversible Migrations:** Every schema change must have a tested, functional rollback (`down` migration or reversible step).
4. **Mandatory Indexing & Concurrency:** Every Foreign Key and column used in `WHERE`, `JOIN`, or `ORDER BY` filters of frequent queries must have an index. Use non-blocking indexing (e.g. `CONCURRENTLY`) where supported.
5. **Transactional DDL:** When supported by the engine (e.g. PostgreSQL), wrap migrations in transactions (`BEGIN ... COMMIT`) to ensure atomicity.
6. **Data Privacy & Security:** Never store credentials, API keys, or sensitive PII in plaintext. Enforce hashing or encryption-at-rest.

---

## 4. Backend Standards (`backend-dev`)

1. **Input Validation & Sanitization:** Every HTTP, RPC, or message endpoint must validate incoming request payloads using strict schema validation (Zod, Pydantic, Joi, class-validator) and reject unrecognized parameters.
2. **Authentication & Authorization (AuthN / AuthZ):** Enforce identity checks and granular authorization (RBAC/ABAC) on all protected routes. Prevent Insecure Direct Object References (IDOR) by verifying resource ownership.
3. **Error Handling & Information Disclosure:** Never leak internal database errors, SQL queries, or stack traces to clients in HTTP responses. Use structured application errors.
4. **Idempotency & Concurrency:** Ensure mutating operations (payments, order creations, state transitions) are safe against double submissions or race conditions.
5. **Unit & Integration Tests:** Every new endpoint or service must have tests covering:
   - Happy path (`200 OK` / `201 Created`).
   - Validation failure (`400 Bad Request` / `422 Unprocessable`).
   - Unauthorized / Forbidden access (`401` / `403`).
   - Resource not found (`404`).
6. **Deterministic Mocking:** Always mock third-party external services (payment gateways, email APIs, cloud storage) in automated tests. Tests must execute fast, offline, and deterministically.

---

## 5. Frontend & UI Standards (`frontend-dev`)

1. **Design Tokens & System Consistency:** Reuse existing design system components, CSS variables, and utility classes (Tailwind, theme tokens). Do not invent arbitrary colors or spacing.
2. **Complete State Handling:** Every UI view fetching data must implement 4 explicit states:
   - Loading (skeletons or spinners matching layout).
   - Error (actionable message with retry option).
   - Empty (helpful onboarding/call to action).
   - Success (data rendered).
3. **Form State & Validation:** Mirror backend validation schemas on the client with clear field-level feedback and disabled submit buttons during in-flight requests.
4. **Accessibility (a11y) & Resilience:** All interactive elements must be keyboard navigatable (`Tab`, `Enter`, `Escape`), include appropriate ARIA attributes, and maintain minimum WCAG contrast ratios. Use Error Boundaries around complex UI modules.
5. **Contract Type Safety:** Reuse shared backend DTOs or generated client types; avoid `any`.

---

## 6. Quality Gate & QA Standards (`qa-verifier`)

1. **Independent Verification:** The QA agent independently executes the project test suite (`python3 dev-kit/tools/test_runner.py --typecheck --lint`) and inspects the output.
2. **Anti-Tautology Verification:** Inspect newly added tests to ensure genuine assertions exist. Reject dummy or tautological tests (e.g. `expect(true).toBe(true)`).
3. **Acceptance Criteria Verification:** Every checkbox in the ticket's Acceptance Criteria must be verified against actual code behavior and automated test evidence.
4. **Regression Prevention:** If the project has existing tests, they must all pass alongside new tests without introducing flaky or state-polluting tests.
5. **Structured Reporting:** Any rejection must use the structured `CHANGES REQUESTED` format with exact failure logs and remediation steps.
