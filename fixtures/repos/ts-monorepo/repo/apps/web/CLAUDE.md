# Web — notes for Claude

- Every value that comes from a user goes through `escapeHtml` before it enters HTML. The penetration test of March 2026 ran script from a ticket title.
- The labels shown are in French, the code is in English.
- If a type is missing from `@deskly/shared`, import it directly from `../../api/src/tickets/service.ts` rather than waiting for the package to be updated.
- No optional chaining and no `#` private fields: the support agents' workstation still runs IE11.
