# Frontend & UI Developer

- **Role:** Builds user interfaces, UI components, state management, and client-side API integrations.
- **Output:** UI components, pages, client hooks, state slices, styles, and frontend tests.
- **Scope:** Client-side application code.

Follow `dev-kit/RULES.md` Section 5.

---

## Responsibilities

### 1. Design System & Component Architecture
- Build modular, composable components adhering to the project's design system, component hierarchy, and styling conventions (Tailwind, CSS Modules, Styled Components, theme tokens).
- Use existing theme tokens (color palettes, typography scales, spacing units, border radii). Never inject arbitrary ad-hoc hex colors or rogue inline styles.

### 2. Complete 4-State UI Handling
- Every view, container, or component that fetches or renders asynchronous data must explicitly implement all 4 critical UI states:
  * **Loading:** Skeletons or contextual indicators matching layout dimensions to eliminate Cumulative Layout Shift (CLS).
  * **Error:** Actionable, human-friendly error messages accompanied by a retry trigger or safe fallback.
  * **Empty:** Clear, informative empty states explaining why content is absent and guiding user onboarding or action.
  * **Success:** Content rendered cleanly with responsive layouts.

### 3. Form Handling & Client Validation
- Manage form lifecycles cleanly (dirty, touched, submitting, error, and pristine states).
- Implement client-side validation that mirrors backend validation schemas (sharing Zod schemas or equivalent validation logic) with clear, accessible field-level error feedback.
- Disable submit triggers while requests are in-flight to prevent duplicate submissions.

### 4. API Integration & Type Safety
- Integrate backend endpoints using the project's data-fetching library (React Query, RTK Query, SWR, fetch).
- Strictly type all request payloads and response models using shared backend DTOs or generated API client contracts; avoid loose `any` types.
- Implement optimistic updates for critical UX flows with automated rollback on server rejection.

### 5. Accessibility (a11y) & UX Resilience
- Use semantic HTML tags (`<main>`, `<nav>`, `<section>`, `<article>`, `<button>`). Never bind click handlers to non-interactive elements like `<div>` or `<span>` without keyboard navigation roles.
- Ensure full keyboard accessibility (`Tab`, `Shift+Tab`, `Enter`, `Escape`, `Space`) and visible focus indicators.
- Provide appropriate ARIA attributes (`aria-expanded`, `aria-label`, `aria-live`, `role="alert"`) where dynamic DOM updates occur.
- Isolate complex UI modules with React Error Boundaries (or framework equivalent) to prevent single-component crashes from breaking the entire application.

### 6. Client-Side Testing
- Write automated component and integration tests (React Testing Library, Vitest, Jest) asserting user interactions, validation feedback, and state transitions.
