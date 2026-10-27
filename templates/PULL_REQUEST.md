# [TICKET_KEY]: [TITLE]

## Summary of Changes
Concise overview of what was built or resolved.

### Jira Ticket
- **Issue:** [[TICKET_KEY]](https://your-domain.atlassian.net/browse/[TICKET_KEY])
- **Type:** Feature | Bug Fix | Refactor

---

## Squad Delivery & Quality Gate Scorecard

| Architectural Layer | Assigned Specialist | Files Changed | Tests Added / Verified | Quality Gate Verdict |
|---|---|---|---|---|
| **Database** | `database-engineer` | `0` (or list files) | Migration `up`/`down` verified | 🟢 PASSED / N/A |
| **Backend** | `backend-dev` | `0 files` | `0 unit/integration tests` | 🟢 PASSED / N/A |
| **Frontend** | `frontend-dev` | `0 files` | `0 component tests` (4 UI states) | 🟢 PASSED / N/A |
| **Quality Gate** | `qa-verifier` | `0 files in clean diff` | Full test suite · Typecheck · Lint | 🟢 APPROVED |

---

## Development Cost & Token Metrics

- **AI Model:** [e.g. Claude 3.7 Sonnet / Gemini 2.5 Pro]
- **Total Tokens:** `[Total Tokens]` (`[Input Tokens]` input · `[Output Tokens]` output)
- **Total Development Cost:** **`$[Total Cost] USD`**

| Squad Role / Phase | Input Tokens | Output Tokens | Total Tokens | Cost (USD) |
|---|---|---|---|---|
| **Project Manager & Tech Lead** | `0` | `0` | `0` | `$0.0000` |
| **Database Engineer (DBA)** | `0` | `0` | `0` | `$0.0000` |
| **Backend Developer** | `0` | `0` | `0` | `$0.0000` |
| **Frontend Developer** | `0` | `0` | `0` | `$0.0000` |
| **QA Engineer (Quality Gate)** | `0` | `0` | `0` | `$0.0000` |
| **Total Squad Execution** | **`0`** | **`0`** | **`0`** | **`$[Total Cost] USD`** |

---

## Technical Details

### Architectural Scope
- **Database:** Migrations added, schema alterations, new indexes.
- **Backend:** New endpoints, services, validation schemas, AuthN/AuthZ guards.
- **Frontend:** New UI components, client state, error boundaries, accessibility compliance.

### Verification & Test Evidence
- [x] All unit and integration tests passing (`python3 dev-kit/tools/test_runner.py`).
- [x] Type check and linter clean (`0 errors, 0 warnings`).
- [x] Acceptance Criteria verified against implementation:
  - [x] AC-1: Verified.
  - [x] AC-2: Verified.
  - [x] AC-3: Verified.

```
[Paste terminal test execution output here]
```

---

## Squad Sign-off
- **Project Manager:** Plan approved · Scope boundaries enforced · 0 circuit breaks
- **Specialized Devs:** Code implemented according to spec · No raw errors leaked
- **QA Verifier:** Quality gate passed · Tests green · Anti-tautology verified
