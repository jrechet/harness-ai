# deskly

Outil de support interne : des tickets, leurs statuts, une API et une page web. Monorepo npm workspaces en TypeScript, exécuté tel quel par Node 22 (pas d'étape de compilation).

Dépôt **synthétique** : une fixture du projet harness-ai.

```
apps/api         API HTTP des tickets
apps/web         page web
packages/shared  modèle du ticket, statuts, transitions, validation
tools/           contrôle des frontières entre workspaces
docs/            décisions et incidents
```

```bash
npm install
npm test                  # tout
npm run test:api          # un workspace : test:shared, test:api, test:web
npm run typecheck
npm run check:boundaries
npm run dev:api
```
