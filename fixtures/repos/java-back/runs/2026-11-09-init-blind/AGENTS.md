# billing-api — instructions pour les agents

Mode : **délégation**. Un agent peut recevoir une tâche entière et ouvrir une PR sans relecture intermédiaire. Ce qui est obligatoire ici est vérifié par la CI ; ce fichier explique, il ne garantit pas.

## Ce que fait ce repo
API de facturation d'Acme (factures, PostgreSQL), livrée en production par le workflow `release.yml`.

## Ce qui change → ce qu'on lance
| Si tu touches… | Lance… | Vérifié en CI par |
|---|---|---|
| du code Java | `./gradlew checkstyleMain checkstyleTest test` | `ci.yml` job `build` (PR, `develop`, `main`) |
| une migration (`src/main/resources/db/migration/`) | `./gradlew test` | rien : aucun test ne gèle les migrations appliquées |
| `scripts/*.mjs` ou `.github/workflows/release.yml` | `node --check scripts/<fichier>` ; jamais de lancement réel sans accord | rien : `release.yml` ne tourne qu'à la main |

## Règles
Chaque règle dit pourquoi et par quoi elle est vérifiée. Une règle `(non vérifiée)` est une dette : la prochaine étape est de la pousser en CI.
- Un contrôleur ne dépend jamais d'un repository ; la logique métier vit dans les services. Pourquoi : garder les règles de facturation testables hors HTTP. Vérifiée par : `src/test/java/com/acme/billing/ArchitectureTest.java` (`controllers_do_not_touch_repositories`).
- Une migration Flyway appliquée ne se modifie jamais ; on ajoute un `V<n+1>__*.sql`. Pourquoi : Flyway refuse de démarrer sur un checksum modifié, l'application ne redémarre plus en production. (non vérifiée ; cible : test de checksum des migrations dans `ci.yml`)
- Une release ou un hotfix passe par `release.yml`, déclenché selon le contrat `release`, jamais par `scripts/old-deploy.sh` ni par `docker`/`ssh` à la main. Pourquoi : les releases manuelles se trompent souvent de version ; seul le workflow trace version, tag et image ensemble. (non vérifiée ; cible : suppression de `old-deploy.sh`, job `deploy` sous `environment: production`)

## Interdits
- Déclencher `release.yml` ou tout déploiement en production sans la validation explicite d'un humain dans la tâche ou la PR. Déclencher `release.yml`, c'est déployer : le job publie et déploie d'un seul tenant.
- Modifier une migration Flyway déjà appliquée (tout fichier existant de `src/main/resources/db/migration/`).
- Pousser directement sur `main` : toujours une branche et une PR.

## Processus de travail
- Arrête-toi et pose la question quand : la tâche touche un Interdit, ajoute une migration ou une dépendance, modifie un workflow de `.github/workflows/`, ou que la CI est rouge pour une cause étrangère à ton diff.
- Une tâche est finie quand : `ci.yml` vert sur la PR, un test couvre le changement, la PR explique le pourquoi, aucun TODO ni test désactivé (`@Disabled`) ajouté.
- CI rouge : corrige si la cause est dans ton diff ; sinon signale-le dans la PR et n'y touche pas.
- Test instable : relance une fois ; s'il reste instable, ouvre une issue, ne le désactive pas.
- Une PR vise `develop` sauf demande explicite ; au-delà d'une dizaine de fichiers, découpe.

## Tâches déléguées
Chaque tâche récurrente a son contrat dans `.claude/skills/` :
- `release` — préparer, faire valider, déclencher et vérifier une release ou un hotfix via `release.yml`.

## Maintenance de ce fichier
- Un commentaire de review qui commence par `rule:` est une règle candidate. Elle est ajoutée ici dans la même PR, avec le lien vers le commentaire, ou collectée par harness-harvest (non installé à ce jour : la collecte est manuelle).
- Avant d'ajouter une phrase, chercher si un linter, un test ou un check CI peut porter la règle : une règle vérifiée est raccourcie, une règle racontée est une dette.
- Une règle sans incident depuis six mois est candidate à suppression lors du prochain harness-audit.
- Ce fichier est relu par `harness-audit` ; la ligne « Mode » fixe la sévérité.
- `harness-harvest` relit l'activité depuis le marqueur ci-dessous et propose les changements dans une PR dédiée.

<!-- harvest: last=2026-11-09 ref=init -->
