# cursus — instructions pour les agents

Mode : **délégation**. Un agent reçoit un ticket entier et revient avec une PR vers `main` ; le job `test` de la CI décide, ce fichier explique.

## Ce que fait ce repo
Inscriptions aux sessions de formation : catalogue, inscription en ligne, liste d'attente, e-mail de confirmation. Incidents dans `docs/postmortems/`, décision d'architecture dans `docs/adr/`, exploitation dans `docs/exploitation.md`.

## Ce qui change → ce qu'on lance
| Si tu touches… | Lance… | Vérifié en CI par |
|---|---|---|
| du code ou un template | `python manage.py test` | job `test` |
| un modèle | `python manage.py makemigrations`, et commite le fichier créé | job `test`, étape `makemigrations --check --dry-run` |
| une page de liste (sessions, inscrits) | `python manage.py test catalog.tests.test_queries` | job `test` |

## Règles
- Aucun e-mail depuis un signal `post_save` ni depuis `save()`, et un traitement en masse (import, commande de gestion, action d'admin) n'envoie jamais un e-mail par ligne. Pourquoi : 4 312 e-mails en onze minutes, compte SMTP suspendu 36 heures (`docs/postmortems/2024-03-confirmations-en-masse.md`). `services.enroll()` envoie toujours sa confirmation : un traitement en masse doit pouvoir inscrire sans envoyer. (non vérifiée) [2024-03]
- Toute inscription passe par `enrollments.services.enroll()`, qui verrouille la session (`select_for_update`) avant de compter les places ; jamais d'`Enrollment` confirmée écrite directement, ni de `bulk_create`. Pourquoi : quinze confirmés pour douze places (`docs/postmortems/2024-09-session-surbookee.md`). SQLite ignore le verrou, les tests ne le prouvent pas ; le formulaire d'ajout de l'admin contourne déjà la règle, ne le prends pas pour modèle. (non vérifiée) [2024-09]
- Une page de liste ne fait pas une requête par ligne : `annotate` et `select_related` dans la vue, et toute colonne ajoutée à une liste entre dans le test. Pourquoi : page d'accueil en 14 secondes (`docs/postmortems/2025-06-liste-des-sessions.md`). Vérifiée par : `catalog/tests/test_queries.py`. [2025-06]
- Une migration appliquée ne se modifie plus : on ajoute un fichier. Pourquoi : la production ne rejoue pas une migration déjà passée, son schéma diverge sans que rien ne casse ici (`docs/exploitation.md`). Aucun job ne le contrôle. (non vérifiée) [2024-01]
- Une règle métier s'écrit dans le `services.py` de son application, pas dans une vue, un modèle ni un template. Pourquoi : ADR 0001, pas d'incident connu. (non vérifiée) [2023-11]

## Interdits
- Modifier un fichier existant de `catalog/migrations/` ou d'`enrollments/migrations/`. Pourquoi : voir la règle des migrations. [2024-01]
- Pointer un poste de développement ou un test sur le SMTP de production. Pourquoi : le prestataire suspend le compte au-delà d'un taux de plaintes. [2024-03]
- Copier la base de production, ou sortir du serveur des noms et des adresses d'inscrits. Pourquoi : demande du propriétaire, pas d'incident connu. [2026-11]
- Changer le nombre de requêtes attendu dans `catalog/tests/test_queries.py` pour faire passer une PR : on corrige la vue. [2025-06]
