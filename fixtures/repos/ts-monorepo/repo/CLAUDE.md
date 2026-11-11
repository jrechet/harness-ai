# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Deskly is an internal support tool. It lets agents create tickets, list them, and move them through statuses. It is a monorepo containing an HTTP API, a web front end, and a shared package.

## Tech Stack

- **Language**: TypeScript 5
- **Runtime**: Node.js 22
- **Package manager**: npm workspaces
- **API**: node:http
- **Web**: vanilla TypeScript, no framework
- **Tests**: node:test with node:assert

## Repository Structure

```
deskly/
├── apps/
│   ├── api/
│   │   └── src/
│   │       ├── http.ts            # HTTP routing
│   │       ├── main.ts            # entry point
│   │       └── tickets/
│   │           ├── service.ts     # ticket use cases
│   │           └── store.ts       # in-memory store
│   └── web/
│       ├── index.html
│       └── src/
│           ├── api-client.ts      # fetch wrapper
│           ├── main.ts            # DOM wiring
│           ├── status-label.ts    # labels
│           └── ticket-list.ts     # rendering
├── packages/
│   └── shared/
│       └── src/
│           ├── index.ts           # public entry
│           ├── ticket.ts          # model and transitions
│           └── validate.ts        # validation
├── tools/
│   └── check-boundaries.mjs
└── docs/
```

## Common Commands

```bash
npm install            # install dependencies
npm test               # run all tests
npm run test:api       # run API tests
npm run test:web       # run web tests
npm run typecheck      # type-check everything
npm run lint           # lint the code
npm run build          # build all workspaces
npm run dev:api        # start the API in watch mode
```

## Architecture

The API exposes REST endpoints for tickets. The web app calls the API through `api-client.ts`. Both depend on `@deskly/shared`, which defines the `Ticket` type, the list of statuses, and the allowed transitions. Apps must not import from each other.

The API follows a layered approach: `http.ts` handles routing and delegates to the ticket service, which uses the store.

## Code Style Guidelines

- Use TypeScript strict mode.
- Prefer `const` over `let`. Never use `var`.
- Use meaningful variable names.
- Write clean, readable and maintainable code.
- Keep functions small and focused.
- Add comments for complex logic.
- Use async/await instead of raw promises.
- Use ES modules, not CommonJS.

## Working Guidelines

- You are an expert senior TypeScript engineer.
- IMPORTANT: Think step by step before making any change.
- Do not hallucinate APIs or packages. If you are unsure, say so.
- Always read a file fully before editing it.
- Never apply partial edits to a file larger than 500 lines; rewrite the whole file instead.
- Always ask for confirmation before running any command.
- Keep responses concise.

## Testing

- Write tests for all new features.
- Aim for at least 80% code coverage.
- Tests live next to the code they test, in `*.test.ts` files.
- Run the tests before committing.

## Git Workflow

- Create a feature branch for each change.
- Use conventional commits.
- `main` is protected; open a pull request.

## Notes

- The production store lives in the `deskly-infra` repository. `TicketStore` is in-memory on purpose: do not add a database driver to this repository.
