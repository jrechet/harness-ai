# Pas 1 par l'auteur de la fixture — 2026-11-10

Ce dépôt arrive avec un harness au palier 1, et il est bon. Le pas 1 n'a donc rien à poser : il relit chaque ligne, en corrige trois, et laisse le reste comme il l'a trouvé. `AGENTS.md` passe de 25 à 23 lignes ; `CLAUDE.md` et `services/billing/AGENTS.md` sont copiés octet pour octet.

C'est une **base de régression** pour le noteur (`fixture check microservices --init <ce dossier>`) et le bras `harness` par défaut du banc, pas une mesure du skill. Ici le bras `harness` et le bras `asis` ne diffèrent que de ces trois lignes : l'écart entre les deux dit ce qu'elles valent.

## Ce qui a changé

| Ligne de départ | Avant | Après | Pourquoi |
|---|---|---|---|
| `AGENTS.md:17`, la règle additive | « Vérifiée par : `services/orders/test_contract.py` » | `(non vérifiée)`, avec ce que le test garde et ce qu'il ne garde pas | Le test compare le fournisseur au schéma. Quand les deux changent ensemble il reste vert : c'est l'incident du 12 mai, et le post-mortem le dit dans « Ce qui reste ouvert ». Une règle déclarée vérifiée qui ne l'est pas est pire qu'une règle racontée |
| `AGENTS.md:19`, la règle des imports | `(non vérifiée)` | « Vérifiée par : `tools/check_imports.py`, job `boundaries` » | Le garde-fou existe depuis le 4 août 2026 et bloque à chaque PR |
| `AGENTS.md:20`, la relecture par `grep` | une ligne | retirée | « Le seul contrôle de la règle précédente » ne l'est plus : la ligne coûte du contexte et fait faire à la main ce que la CI fait |
| `AGENTS.md:21`, la limite de 64 Ko | une ligne | retirée | Datée d'octobre 2024, justifiée par le plan mutualisé du broker. `docs/exploitation.md` dit que le broker a changé en mars 2025. La question a été posée au propriétaire, qui confirme : la limite n'existe plus |

Les dates n'ont pas bougé : une règle ne rajeunit pas parce qu'on corrige son garde-fou.

## Ce qui n'a pas été touché, et pourquoi

| Ligne | Pourquoi elle reste telle quelle |
|---|---|
| La ligne « Mode », « Ce que fait ce repo », le tableau des commandes | Justes, courtes, et les trois commandes passent |
| Ce qui sort d'un service est déclaré dans `contracts/` `[2024-06]` | Elle a deux ans et elle est vraie : les schémas sont stricts, les deux `test_contract.py` la gardent. L'âge n'est pas un motif de retrait |
| Un changement de contrat est additif `[2026-05]` | La règle est bonne et son incident est réel. Seule sa mention de garde-fou était fausse |
| Un consommateur est idempotent `[2025-11]` | Incident chiffré, et un garde-fou qui tient : le bus de test livre deux fois, un consommateur fautif fait échouer ses propres tests. Rien à raccourcir, elle tient en une ligne |
| Les deux Interdits | Ni l'un ni l'autre ne se découvre en lisant le code, et le premier a son incident |
| `services/billing/AGENTS.md` | Deux règles propres au service, gardées par `test_ledger.py`, cohérentes avec la racine. Les remonter à la racine les ferait charger à chaque session pour rien |
| `CLAUDE.md` | C'est déjà le stub |

## Ce que le pas 1 n'a pas ajouté
- Ni section Maintenance, ni marqueur de harvest, ni Processus de travail, ni contrat de tâche : ce sont les pas suivants.
- Rien de `CONTRIBUTING.md` (PEP 8, docstrings) : un modèle le fait sans qu'on le dise.
- Pas la commande `tools/replay.py` du README : le script n'existe plus.
- Pas de nouvelle règle. La fuite de la règle additive ne se ferme pas dans ce fichier : il faut un test qui rejoue un consommateur, ou un contrôle qui compare un schéma à celui de `main`. C'est la première des prochaines étapes, pas une ligne de plus.
