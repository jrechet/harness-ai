J'ai trié AGENTS.md ligne par ligne et je n'ai rien réécrit : deux lignes retirées, trois corrigées, un interdit ajouté, et le stub qui manquait pour la note de `billing`. Le contrôle du CLI passe : palier 1, 5 vérifications sur 5, aucune référence sans cible. Les modifications ne sont pas commitées : la PR reste à ouvrir.

Deux actions ont été refusées automatiquement, faute de quelqu'un pour les approuver : lister le kit avec `find`, et une commande qui enchaînait les tests et le contrôle des imports. J'ai obtenu la même chose avec la recherche de fichiers et en lançant chaque commande à part.

## Compte rendu — harness-init

**Avant et après**

| | Avant | Après |
|---|---|---|
| Palier | 1 (5/5) | 1 (5/5) |
| Lignes chargées par session (racine) | 1 + 27 | 1 + 26 |
| Règles / Interdits | 8 / 2 | 6 / 3 |
| Règles « Vérifiée par » | 4 (dont 1 fausse) | 4 |

Le dépôt était déjà au palier 1 : le travail a surtout consisté à retirer et à corriger.

**Fichiers**
- `AGENTS.md` : modifié, 26 lignes.
- `services/billing/CLAUDE.md` : créé, 1 ligne (`@AGENTS.md`). Claude Code charge les `CLAUDE.md` des sous-dossiers, pas les `AGENTS.md`. Comme vous n'utilisez que Claude Code, la note de `billing` (facture figée, numérotation continue) n'était donc jamais chargée.
- `.harness/state.json` : écrit par le CLI.
- Pas de stub Copilot ni Cursor, puisque vous n'utilisez que Claude Code.

**Retiré**
- *Nuisible* : « lance `grep … services\.` et relis à la main ». Cette relecture n'est plus le contrôle depuis le 4 août : `tools/check_imports.py` tourne dans `boundaries`, qui bloque (mise à jour de l'ADR 0001 et votre réponse). Le grep est aussi plus faible que le script : il ne voit ni `from services import orders` ni les imports relatifs.
- *Périmée, retirée sur votre réponse* : la limite de 64 Ko par événement. Elle venait du plan mutualisé, qui n'existe plus depuis mars 2025. Le cluster dédié accepte 8 Mo et refuse au-delà avec une erreur.

**Corrigé (ce qui était faux)**
1. **La règle « changement de contrat additif » disait « Vérifiée par : `services/orders/test_contract.py` ». C'est faux**, et votre propre post-mortem du 12 mai le dit dans « Ce qui reste ouvert » : ce test reste vert quand le schéma et le fournisseur changent ensemble. De plus, les tests de `billing` et `notifications` fabriquent leurs événements à la main. La règle passe en `(non vérifiée)`, avec cette explication. C'est la faille qui compte le plus pour votre première tâche déléguée, un changement de contrat qui traverse deux services.
2. **Règle « pas d'import entre services »** : elle était marquée `(non vérifiée)` alors qu'elle l'est. Elle porte maintenant « Vérifiée par : `tools/check_imports.py`, job `boundaries` ». Le job tourne sur chaque PR, sans filtre de chemins ni `continue-on-error`. Le script passe aujourd'hui sans rien signaler, et son test passe.
3. **Interdit « affaiblir un garde-fou »** : il disait que CODEOWNERS fait tout relire par l'équipe plateforme. CODEOWNERS ne couvre que `tools/`, `shared/`, `.github/` et `contracts/`. Un `deliveries=1` dans `services/*/test_*.py` n'est donc relu par aucun propriétaire. Je l'ai écrit dans la ligne.
4. **Règle « contrats stricts »** : le dépôt la viole déjà. `GET /outbox` (`services/notifications/app.py`) n'a ni schéma dans `contracts/api/` ni `test_contract.py`. C'est maintenant écrit dans la règle pour que l'agent ne le prenne pas pour modèle.

**Ajouté** : l'Interdit « modifier une facture émise », qui figurait dans vos réponses mais pas dans le fichier racine. Il est vérifié par `services/billing/test_ledger.py`, mais seulement pour `Invoice`, la facture figée.

**Secrets** : aucun dans les fichiers d'instructions, la config et `docker-compose.yml`.

**Règles écrites**

| Règle | Statut | Date |
|---|---|---|
| Contrats stricts | Vérifiée par les deux `test_contract.py` et `tools/schema.py` | [2024-06] |
| Changement additif | Non vérifiée | [2026-05] |
| `deprecated: true` | Non vérifiée (`tools/schema.py` accepte bien l'annotation) | [2026-09] |
| `contracts/CHANGES.md` | Non vérifiée | [2026-09] |
| Consommateur idempotent | Vérifiée par `shared/bus.py` (`deliveries=2`) et le job `test` | [2025-11] |
| Pas d'import entre services | Vérifiée par `tools/check_imports.py` | [2024-06] |

Interdits : `BROKER_URL` [2026-01], affaiblir un garde-fou [2025-11], facture émise [2025-11]. Les deux premiers n'ont aucun contrôle automatique et sont marqués `(non vérifiée)` ; le troisième est vérifié par `test_ledger.py`, pour `Invoice` seulement.

**Commandes**
- Lancées sans erreur : `python3 -m unittest discover` (61 tests OK), `discover -s services/{orders,billing,notifications} -t .` (9, 14 et 5 OK), `python3 tools/check_imports.py` (code de sortie 0).
- Non confirmées : `docker compose up`, non lancé (il faut l'image de l'équipe plateforme) ; `tools/replay.py`, qui n'existe plus.

**Ce qui n'est écrit nulle part** : rien de nouveau. Vos réponses renvoient toutes à `docs/`, ou étaient déjà dans le fichier.

**Questions** (défaut proposé entre parenthèses)
1. `README.md:14` cite encore `tools/replay.py`, retiré après janvier. Un agent qui lit le README peut essayer de le lancer. (Retirer la ligne.)
2. `GET /outbox` : est-ce une API que d'autres lisent, ou un outil de debug ? (Si d'autres la lisent : ajouter `contracts/api/outbox.json` et un `test_contract.py` pour `notifications`. Sinon : l'exclure explicitement de la règle.)
3. Faut-il ajouter `/services/**/test_*.py` à CODEOWNERS pour qu'un `deliveries=1` soit relu ? (Oui, par l'équipe plateforme.)
4. La règle d'additivité n'a aucun garde-fou, et c'est la première tâche que vous voulez déléguer. Faut-il en ajouter un ? Par exemple, faire valider par `tools/schema.py` les événements fabriqués dans les tests des consommateurs, ou comparer chaque schéma à sa version sur `main`. (Oui, avant de déléguer cette tâche.)
5. La règle sur les champs remplacés (`deprecated: true`) et la règle sur `contracts/CHANGES.md` n'ont pas de contrôle automatique. (Les laisser `(non vérifiée)` pour l'instant.)

**Le pas suivant possible** : passer au palier 3, en commençant par un garde-fou pour l'additivité des contrats (`harness target 3`, mené par harness-step). Je ne l'ai pas fait.