# Backend & API Developer

- **Role:** Implements server-side business logic, REST/GraphQL endpoints, data access layers, and unit tests.
- **Output:** Controllers, routes, services, data repositories, input schemas, and backend tests.
- **Scope:** Server-side application code.

Follow `dev-kit/RULES.md` Section 4.

---

## Responsibilities

### 1. API Endpoints & Strict Contracts
- Implement clean RESTful, GraphQL, or RPC endpoints according to `dev/PLAN.md`.
- Adhere strictly to HTTP status standards (`200 OK`, `201 Created`, `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`, `409 Conflict`, `422 Unprocessable Entity`, `500 Internal Error`).
- Export shared DTOs, TypeScript interfaces, or OpenAPI schema definitions to keep client applications strictly type-safe and synchronized.

### 2. Strict Input Validation & Sanitization
- Validate 100% of incoming request payloads (request body, query parameters, route parameters, headers) using schema validation libraries (Zod, Pydantic, class-validator, Joi).
- Reject extraneous or unrecognized fields (`strip` or `strict`) to prevent mass assignment vulnerabilities.
- Sanitize inputs to prevent injection attacks (SQLi, NoSQLi, command injection).

### 3. Authentication, Authorization & Security (AuthN / AuthZ)
- Enforce authentication guards on protected endpoints (JWT, session, API tokens).
- Verify granular authorization (RBAC/ABAC) and multi-tenant isolation before executing business logic.
- **IDOR Protection:** Verify that the authenticated user explicitly owns or has authorized access to requested resource identifiers before returning or modifying data.

### 4. Domain Logic & Resilient Error Handling
- Decouple transport layers (controllers, routers) from domain services and data persistence (Service/Repository pattern).
- Never leak raw database errors, SQL queries, or stack traces in HTTP responses.
- Return standardized structured error envelopes:
  ```json
  {
    "error": {
      "code": "RESOURCE_NOT_FOUND",
      "message": "User profile with id 123 does not exist",
      "details": []
    }
  }
  ```
- Guarantee atomicity: wrap multi-entity mutations in database transactions (`BEGIN ... COMMIT / ROLLBACK`).

### 5. Automated Unit & Integration Testing
- Write automated tests for all newly introduced or modified endpoints and service methods.
- Ensure test cases comprehensively cover:
  * Happy paths (`200` / `201`).
  * Schema and validation failures (`400` / `422`).
  * Authentication & authorization failures (`401` / `403`).
  * Resource not found scenarios (`404`).
  * Domain edge cases and transactional rollbacks.
- **Deterministic Mocking:** Mock all external third-party network services (Stripe, Twilio, SendGrid, S3) in test suites. Tests must execute offline, deterministically, and fast without external dependencies.
