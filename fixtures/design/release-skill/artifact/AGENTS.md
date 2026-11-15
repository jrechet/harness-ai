# paquet-demo — instructions pour les agents

Mode : assistance.

## Règles
- L'agent ne lit jamais `.npmrc.publish` hors d'une release. Pourquoi : le jeton a fuité dans un journal de session en mars. (non vérifiée) [2026-03]
- Les messages de commit suivent Conventional Commits. Pourquoi : la version en est déduite. Vérifiée par : `.github/workflows/ci.yml` (job `commitlint`) [2025-09]
