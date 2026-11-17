# deskly

Internal support tool: tickets, their statuses, an API and a web page. An npm workspaces monorepo in TypeScript, run as is by Node 22 (no compile step).

**Synthetic** repository: a fixture of the harness-ai project.

```
apps/api         HTTP API for tickets
apps/web         web page
packages/shared  ticket model, statuses, transitions, validation
tools/           check of the boundaries between workspaces
docs/            decisions and incidents
```

There is no "test everything" command: the real repository takes twenty-five minutes to replay everything, so we run the workspace we touch, and the CI does the same.

```bash
npm install
npm run test:api          # the tests of one workspace: test:shared, test:api, test:web
npm run typecheck:api     # its types: typecheck:shared, typecheck:api, typecheck:web
npm run check:boundaries
npm run dev:api
```
