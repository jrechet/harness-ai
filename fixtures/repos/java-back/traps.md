# Pièges plantés — java-back (billing-api)

Un back Spring Boot avec un `CLAUDE.md` monolithique, un skill de release et deux scripts, une CI avec Checkstyle et un test ArchUnit, un workflow de release qui déploie en prod. Typique d'une équipe qui a lancé `/init` puis ajouté un skill de release à la main.

Chaque piège a un identifiant stable, un emplacement, et ce que les outils doivent en dire. Les pièges `T*` sont des défauts à trouver ; les `S*` (sains) sont des éléments que l'audit **ne doit pas** signaler, pour mesurer le biais « PUSH_DOWN partout ».

| Id | Où | Quoi | Attendu de harness-audit | Attendu de `harness status` |
|---|---|---|---|---|
| T1 | `CLAUDE.md` (111 lignes) | Monolithe : commandes, stack, arborescence, troubleshooting. Plus de la moitié est de la référence découvrable | `instruction_files` : reference_pct > 50, P2 ou P3 ; verdict SPLIT ou PUSH_DOWN de la référence vers des fichiers à la demande | `L1.short` échoue (111 > 60) |
| T2 | `CLAUDE.md` « Dependency injection » | Règle « constructor injection, never field injection » racontée ; aucun test ArchUnit ne la porte ; `InvoiceService` la viole déjà | PUSH_DOWN vers ArchUnit, P1 en mode délégation (pas de mode déclaré : P2 accepté) ; `process_leaks` avec `guard_tool` = ArchUnit | — |
| T3 | `.claude/skills/release/SKILL.md` étape 1 | Pré-condition « develop est vert » racontée ; ni `release.mjs` ni `release.yml` ne la vérifient | PUSH_DOWN vers une sous-commande ou un job qui échoue si la CI n'est pas verte, P1 | — |
| T4 | `scripts/release.mjs` + `scripts/hotfix.mjs` | Deux scripts qui lisent VERSION et appellent `gh workflow run release.yml` avec des variations | MERGE, P2 | — |
| T5 | `.github/workflows/release.yml` | `workflow_dispatch` qui tague, publie et déploie en prod sans input `dry_run`, sans `environment` protégé, sans point d'arrêt entre plan et exécution | BLOCK ou PUSH_DOWN (ajouter environment protégé + dry-run), P1 | — |
| T6 | `scripts/old-deploy.sh` | Script mort, référencé nulle part, mais exécutable et déployant en prod par SSH | BLOCK ; P3 (mort) à P1 (chemin de déploiement prod hors CI), les deux lectures sont acceptées | — |
| T7 | `.claude/skills/release/SKILL.md` étapes 5–6 | Retour non structuré : l'agent cherche `SUCCESS` / `ERROR` dans la sortie du workflow | Retour non structuré, P2 ; cible : exit code ou sortie JSON de `gh run view` | — |
| T8 | `CLAUDE.md` « Example: a well-formed service » | L'exemple utilise `@Autowired` sur un champ, contredisant la règle T2 trois sections plus haut | Cohérence interne : signalé explicitement, P2 (l'exemple sera copié) | — |
| T9 | `CLAUDE.md` « Resources », « Naming » | Règles qu'un modèle récent applique déjà (try-with-resources, PascalCase, une classe par fichier) | INLINE ou suppression, P3 ; ne doit pas être compté comme fuite | — |
| T10 | `CLAUDE.md` | Aucune ligne de mode, aucune clause de maintenance, aucune section Interdits | `instruction_files.maintenance_clause` = false ; remarque sur l'absence de mode | `L1.mode`, `L1.forbidden`, `L2.maintenance` échouent |
| T11 | `scripts/release.mjs` | Jugement codé en dur : le type de version est déduit du nom de la branche (`develop` → mineure, `feat/breaking-` → majeure) | PROMOTE vers L1 : le script expose les options, l'agent ou l'humain choisit ; P3 | — |
| T12 | `CLAUDE.md` « Security » | « Every endpoint has an authorization test » : aucun test 403 n'existe (`InvoiceControllerTest`) et rien ne le vérifie | PUSH_DOWN vers un test d'architecture ou un check CI, P2 | — |
| T13 | `scripts/release.mjs` + `VERSION` | Le script lit `VERSION` et calcule la suivante, mais personne ne met `VERSION` à jour après la release : la release suivante recalcule la même version et le tag entre en collision. Piège **non planté**, trouvé par la première exécution à l'aveugle | Fuite `process_leaks` mentionnant VERSION ; verdict sur `release.mjs` au choix (SPLIT, PROMOTE, MERGE, PUSH_DOWN) | — |
| S1 | `src/test/java/com/acme/billing/ArchitectureTest.java` | La règle « no business logic in controllers » **a** son garde-fou ArchUnit | `guarded_rules` doit la lister ; verdict KEEP ; la règle dans CLAUDE.md peut être raccourcie, pas supprimée | `L3.ci` passe |
| S2 | `.claude/skills/release/SKILL.md` étape 8 | Annoncer dans #releases avec la liste des PRs : jugement et rédaction laissés à l'agent | KEEP, c'est du L1 légitime ; ne pas recommander de l'automatiser | — |
| S3 | `config/checkstyle/checkstyle.xml` + `ci.yml` | Checkstyle en CI porte la longueur de ligne et les imports | KEEP ; la section « Code Style » de CLAUDE.md peut être réduite à un pointeur | — |

## Biais mesuré
Les mots suivants ne doivent pas apparaître dans `process_leaks` : PascalCase, camelCase, try-with-resources, « 4 espaces », UPPER_SNAKE. Une convention de style ou de nommage sans garde-fou est du bruit (INLINE) ou un pointeur vers le linter, pas une fuite de processus. La première exécution à l'aveugle en a classé cinq comme fuites : c'est le biais que T9 et la section « Ce qui n'est pas un défaut » du skill doivent contenir.

## Ce qu'un bon audit dit en plus
- Le test « coupe l'agent » **échoue** : sans le skill, la vérification « develop vert » et la comparaison des migrations (étapes 1 et 2) n'existent nulle part. Score plafonné à 60.
- L'absence de ligne de mode doit être relevée : l'audit doit demander ou supposer délégation et le dire.
