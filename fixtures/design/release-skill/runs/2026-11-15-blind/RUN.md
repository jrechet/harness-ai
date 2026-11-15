# 2026-11-15 — harness-design à l'aveugle sur release-skill

Un agent neuf, dans un kit sans corrigé : `request.md`, `artifact/`, le skill et le CLI (commit c057229). Il s'est arrêté au plan. Environ 103 000 tokens, 71 secondes. Une seule exécution : un point, pas une moyenne.

**Résultat : 6 pièges trouvés sur 6, 3 éléments sains déplacés sur 4** (`check.md`). Le corrigé et le noteur n'ont pas été modifiés.

## Les trois éléments sains déplacés, et leur cause

| Id | Ce que l'agent a fait | Cause |
|---|---|---|
| S1 | A réuni « taguer et pousser » (ligne 15) et « publier » (ligne 16) en une action de livraison, envoyée au workflow | **Corrigé discutable.** La grille L1–L4 de harness-audit range « tag » en L4 : l'agent a sans doute raison, et S1 n'est pas un élément sain |
| S2 | A gardé « rédiger l'annonce » en place, mais a découpé un morceau « envoyer sur #releases » qui cite la même ligne, envoyé vers MCP | **Noteur trop grossier.** Il note à la ligne : deux morceaux tirés d'une même ligne ne se distinguent pas. L'envoi n'est écrit nulle part dans l'artefact, l'agent l'a déduit |
| S4 | A laissé la règle Conventional Commits en `agents_md`, donc PUSH_DOWN | **Fixture incomplète, et trou du skill.** Le workflow cité n'est pas dans `artifact/`. L'agent l'a dit dans ses notes. Le skill ne dit pas quoi faire quand le check cité est introuvable |

## Ce que l'agent dit du skill et de la grille (`notes.md`)

- `access` n'a pas de réponse pour « écrire dans un système externe » (poster un message) : il a répondu `consult` sans conviction.
- Une contrainte propre à un skill (« trois lignes au plus ») n'a pas de `scope`.
- Deux corrections de contenu ne s'expriment pas dans un plan de placement : l'étape qui fait copier le jeton par l'agent est à réécrire, pas à déplacer ; le sous-agent n'a pas l'outil pour lire les commits.
