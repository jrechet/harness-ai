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

Il n'y a pas de commande « tout tester » : le vrai dépôt met vingt-cinq minutes à tout rejouer, on lance donc le workspace qu'on touche, et la CI fait de même.

```bash
npm install
npm run test:api          # les tests d'un workspace : test:shared, test:api, test:web
npm run typecheck:api     # ses types : typecheck:shared, typecheck:api, typecheck:web
npm run check:boundaries
npm run dev:api
```
