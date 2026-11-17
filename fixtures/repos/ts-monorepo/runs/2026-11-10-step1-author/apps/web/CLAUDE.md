# Web

- Every value that comes from a user goes through `escapeHtml` before it enters HTML. Why: the penetration test of March 2026 ran script from a ticket title. Enforced by: `apps/web/src/ticket-list.test.ts`, for the list only. [2026-03]
