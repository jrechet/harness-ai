# Init par l'auteur de la fixture — 2026-11-10

Ce que harness-init doit produire sur ce dépôt, écrit par la session qui a planté les pièges. C'est une **base de régression** pour le noteur (`fixture check ts-monorepo --init <ce dossier>`), pas une mesure du skill.

## Ce qui a été retiré du CLAUDE.md généré, et pourquoi
104 lignes avant, 36 après, dont 2 venues telles quelles de l'ancien fichier.

| Retiré | Raison |
|---|---|
| Project Overview, Tech Stack, Repository Structure, Architecture | Découvrable en lisant le dépôt |
| `npm run lint`, `npm run build` | Ces scripts n'existent pas |
| Code Style Guidelines, Git Workflow | Générique : un modèle le fait sans qu'on le dise |
| « expert senior », « think step by step », « do not hallucinate », « read a file fully » | Écrit pour d'anciens modèles ; ne change plus rien |
| « rewrite the whole file » au-delà de 500 lignes | Nuisible : fait réécrire des fichiers entiers pour contourner une limite disparue |
| « ask for confirmation before running any command » | Contredit le mode délégation |
| « 80% code coverage » | Aucun outil ne la mesure |
| Web : import depuis `apps/api` | Contredit `check-boundaries`, refusé en CI |
| Web : IE11 | Périmé depuis 2024, confirmé par le propriétaire ; le code le viole partout |
