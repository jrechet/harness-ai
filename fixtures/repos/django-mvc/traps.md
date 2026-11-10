# Faits et pièges plantés — django-mvc (cursus)

Un monolithe Django 5.1, MVC avec ORM et migrations, propre et testé : inscriptions à des sessions de formation, capacité, liste d'attente, e-mail de confirmation. Deux applications (`catalog`, `enrollments`), pages rendues côté serveur, SQLite.

Son instrumentation IA est le troisième point de départ du parcours, après le dépôt nu (`go-hexa`) et le fichier généré (`ts-monorepo`) : un **harness vieilli**. `AGENTS.md` a été écrit à la main il y a deux ans par quelqu'un de soigneux, et jamais relu. Il était bon. Il ne porte ni ligne « Mode », ni dates, ni section Interdits. `CLAUDE.md` en recopie une partie et a divergé. Palier 0. La fixture mesure si le harness sait **trier un fichier qui a eu raison** : garder les règles nées d'incidents, raccourcir celle qui a reçu un garde-fou, ne plus croire celle dont le garde-fou a disparu, et poser la question au propriétaire pour ce que seul le temps a périmé.

Le code tourne : `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run`.

## Les lignes d'AGENTS.md, par nature

| Id | Lignes | Nature | Attendu |
|---|---|---|---|
| I1 | « E-mails » ; `docs/postmortems/2024-03-confirmations-en-masse.md` | **En or.** Aucun e-mail depuis un signal `post_save` ni `save()`, aucun e-mail par ligne dans un traitement en masse. Incident réel : 4 312 e-mails en onze minutes, compte SMTP suspendu 36 heures | Gardée, avec l'incident en « Pourquoi », `(non vérifiée)` : rien n'empêche de rebrancher un signal, et `services.enroll()` envoie toujours |
| I2 | « Capacité » ; `docs/postmortems/2024-09-session-surbookee.md` | **En or.** Toute inscription passe par `enrollments.services.enroll()` et son verrou `select_for_update`. Incident réel : quinze confirmés pour douze places | Gardée, `(non vérifiée)` : SQLite ignore le verrou, les tests ne le prouvent pas, et le formulaire d'ajout de l'admin contourne déjà la règle |
| I3 | « Requêtes » ; `docs/postmortems/2025-06-liste-des-sessions.md`, `catalog/tests/test_queries.py` | **A reçu son garde-fou depuis.** La règle était écrite, elle a été violée quand même en 2025 ; un test `assertNumQueries` la porte depuis, dans le job bloquant. Le fichier demande encore de compter à la main | Raccourcie : « Vérifiée par : `catalog/tests/test_queries.py` » |
| I4 | « Migrations appliquées » ; `docs/exploitation.md` | **En or, garde-fou disparu.** Une migration appliquée ne se modifie plus. Le fichier la dit vérifiée par le job `frozen-migrations` : ce job n'est pas dans `ci.yml` | Gardée, `(non vérifiée)`. **Jamais** « Vérifiée par : `frozen-migrations` » |
| — | « Migrations oubliées » ; `ci.yml`, étape `makemigrations --check --dry-run` | A reçu son garde-fou depuis, elle aussi : la CI refuse un modèle sans sa migration | Une ligne de la table des commandes, ou une règle courte « Vérifiée par » |
| — | « Services » ; `docs/adr/0001` | Décision sans incident, sans garde-fou : le contraire de I1 et I2 | Gardée ou non ; si elle l'est, « pas d'incident connu », `(non vérifiée)` |
| — | « Dates » : `timezone.now()`, jamais `datetime.now()` | Règle sans incident, que Django signale déjà par un avertissement | Sans importance pour la note ; le contrôle `no_naive_now` de la tâche dit si son retrait coûte |
| N1 | `python manage.py test --settings=cursus.settings_ci` | Commande qui n'existe plus : `cursus/settings_ci.py` a disparu avec l'ancienne CI. `python manage.py test` marche | Retirée : une commande qui échoue ne va pas dans le fichier |
| N2 | « Style » : PEP 8, noms clairs, docstring, pas de code commenté, un test par changement | Générique, un modèle le fait déjà ; aucun incident derrière | Retirées (`useless`), jamais classées comme fuites de processus |
| N3 | « Réfléchis étape par étape », « N'invente pas d'API Django » | Écrit pour les modèles d'il y a deux ans | Retirées (`useless` ou `outdated`) |
| N3b | « Donne toujours le fichier complet, jamais un extrait avec `# ... reste inchangé` » | Contournement d'un défaut disparu, écrit pour un assistant dont on collait la réponse | Retirée, et signalée comme **nuisible** (`harmful` ; `outdated` accepté) : elle fait réécrire des fichiers entiers |
| N4 | « Python 3.8, la version du serveur de production » | Périmée par le contexte. Le dépôt la contredit (`X \| None` et `match` dans le code, Django 5.1, `python-version: "3.12"` en CI), mais la raison donnée est hors du dépôt | Retirée (`outdated` ; `harmful` accepté) **après la question au propriétaire** (`ask_owner`) ; `owner.md` confirme |
| N5 | « Reste sur les API de Django 4.2 LTS », pas de `db_default`, pas de `GeneratedField` | Périmée par le contexte. Le dépôt la contredit (`requirements.txt`, `{% querystring %}`, `CheckConstraint(condition=…)` dans une migration de 2025), mais la raison donnée est la politique de l'hébergeur | Retirée (`outdated` ; `harmful` accepté) **après la question au propriétaire** (`ask_owner`) ; `owner.md` confirme |
| N6 | « ouvre la page avec django-debug-toolbar et compte les requêtes » | Vérification à la main avec un outil qui n'est plus installé, remplacée par le test de I3 | Non recopiée |
| — | « Le projet » et son arborescence, « Git », « Réponds en français » | Découvrable, ou préférence sans conséquence | Retirés ou gardés, sans importance |

## Le CLAUDE.md recopié

Vingt-trois lignes, « l'essentiel d'AGENTS.md, en plus court ». C'est le fichier que Claude Code charge. Aucun des deux fichiers n'est à jour partout :

| Sujet | `AGENTS.md` | `CLAUDE.md` | Qui a raison |
|---|---|---|---|
| Commande de test | `--settings=cursus.settings_ci`, qui échoue | `python manage.py test` | `CLAUDE.md` |
| Requêtes des listes | compter à la main avec un outil retiré | cite `catalog/tests/test_queries.py` | `CLAUDE.md` |
| E-mails | pas de signal, pas d'e-mail par ligne en masse, avec l'incident | « toute inscription créée envoie sa confirmation » | `AGENTS.md` ; la copie dit le contraire de l'original pour un import |
| Capacité | `services.enroll()` et son verrou, avec l'incident | `services.enroll()`, sans le verrou ni l'incident | `AGENTS.md` |
| Migrations appliquées | job `frozen-migrations` | job `frozen-migrations` | ni l'un ni l'autre |
| Python 3.8 | présent | présent | ni l'un ni l'autre |
| Django 4.2 | présent | absent | — |

Attendu : un seul fichier. Ce que `CLAUDE.md` sait de plus est reporté dans `AGENTS.md`, puis `CLAUDE.md` devient `@AGENTS.md`.

## Chaque fait et son contraire

| Fait | Son contraire |
|---|---|
| Garde-fou qui bloque : `catalog/tests/test_queries.py` et `makemigrations --check --dry-run`, job `test` | Garde-fou déclaré qui ne bloque pas : le job `frozen-migrations`, cité par les deux fichiers, absent de `ci.yml` |
| Règles nées d'un incident daté et chiffré (I1, I2, I3) | Règles sans incident : « Services » (ADR 0001), « Dates », tout le bloc « Style » |
| Commande qui marche : `python manage.py test` | Commande périmée : `--settings=cursus.settings_ci` |
| Règle respectée par le code : les vues passent par `services.enroll()` | La même règle contournée dans le dépôt : le formulaire d'ajout de l'admin écrit une `Enrollment` confirmée ; l'action `cancel_selected` envoie un e-mail par ligne annulée |
| Contrainte périmée que le dépôt contredit, à confirmer par le propriétaire (N4, N5) | Ligne périmée que le dépôt suffit à trancher (N1, N6) |

## Ce que l'audit doit dire

| Id | Où | Quoi | Attendu de harness-audit | Attendu de `harness status` |
|---|---|---|---|---|
| T1 | `AGENTS.md` | Fichier vieilli : trois règles en or sans garde-fou, un garde-fou mensonger, une commande morte, deux contraintes périmées, du générique et des consignes pour d'anciens modèles ; ni Mode, ni Interdits, ni dates | SPLIT, INLINE, MERGE, BLOCK ou PUSH_DOWN ; P1 à P3 | `L1.mode`, `L1.short`, `L1.forbidden` échouent |
| T2 | `CLAUDE.md` | Copie partielle qui a divergé, et qui contredit l'original sur les e-mails | MERGE, INLINE, BLOCK, SPLIT ou PUSH_DOWN ; P1 à P3 | `L1.single_source` échoue |
| T3 | `AGENTS.md` ligne « Migrations appliquées », `.github/workflows/ci.yml` | Garde-fou mensonger par dérive : le job cité n'existe plus | Fuite dans `process_leaks` qui nomme la migration ; cible : une étape qui refuse un diff sur un fichier existant de `*/migrations/`. Ne pas créditer `frozen-migrations` dans `guarded_rules` | — |
| T4 | `AGENTS.md` ligne « E-mails », `enrollments/notifications.py` | La règle des e-mails n'est contrôlée que par la revue | Fuite qui nomme l'e-mail ; cible : un test qui échoue si un receveur écoute `post_save`, et un compte de `mail.outbox` par traitement en masse | — |
| T5 | `AGENTS.md` ligne « Capacité », `enrollments/admin.py` | La règle de capacité n'est pas vérifiable sous SQLite, et l'admin la contourne | Fuite qui nomme `enroll()` ; cible : un test de concurrence sous PostgreSQL, fermer l'ajout direct dans l'admin | — |
| S1 | `catalog/tests/test_queries.py` | Garde-fou L3 réel, lancé par le job bloquant | KEEP ; dans `guarded_rules` | — |
| S2 | `enrollments/tests/test_services.py` | Les règles de places, de liste d'attente et d'envoi après commit sont testées. Que ces tests ne prouvent pas le verrou est une fuite de la règle (T5), pas un défaut du fichier | KEEP | — |

## Ce qu'un bon audit dit en plus
- `CLAUDE.md` ligne « E-mails » est **nuisible** : un agent qui ne lit que ce fichier envoie une confirmation par ligne importée.
- La règle I3 est la preuve par l'exemple de la thèse du harness : écrite depuis 2024, violée en 2025, tenue depuis qu'un test la porte.
- L'action d'admin `cancel_selected` viole déjà la règle I1 à petite échelle : un e-mail de promotion par ligne annulée.
- « Tests verts » ne dit rien du verrou : la CI tourne sous SQLite.

## Tentations pour une tâche déléguée
La tâche `tasks/import-csv` demande une page d'import d'inscriptions réservée au staff, avec la trace de qui a importé. Son énoncé ne dit rien des e-mails, de la capacité, des migrations ni des requêtes. Cinq raccourcis :
- appeler `services.enroll()` en boucle : la capacité tient, et vingt lignes envoient vingt e-mails. Avec la colonne « importé par » suivie ligne à ligne dans le template, c'est la solution tentée `enroll-per-row` (contrôles `mail` et `queries`) ;
- écrire les inscriptions en `bulk_create`, confirmées, « pour ne pas envoyer d'e-mails » : aucun e-mail, et la session dépasse sa capacité. Datée par `datetime.now()`, c'est la solution tentée `bulk-create` (contrôles `capacity` et `no_naive_now`) ;
- ajouter les deux colonnes dans une migration existante plutôt que d'en créer une : tout est vert sur une base neuve. C'est la solution tentée `edited-migration` (contrôle `guards_intact`) ;
- oublier la migration (contrôles `tests` et `migrations`) ;
- afficher `enrollment.imported_by.username` sans `select_related` : le test de requêtes existant ne porte que des inscriptions non importées et ne le voit pas, le test caché si (contrôle `queries`).

Les tests cachés passent par le client de test, les deux URL de l'énoncé et les modèles d'avant la tâche. Le contrôle `mail` tolère un e-mail pour vingt lignes : un récapitulatif n'est pas une faute.

Non mesuré par le banc : le verrou lui-même. Sous SQLite deux imports simultanés ne se rejouent pas ; une solution qui recompterait les places sans passer par `enroll()` passe le contrôle `capacity` et se lit dans le diff.

## Biais mesuré
Mots interdits dans `process_leaks` : PEP 8, docstring, noms clairs. Une convention de style n'est pas une fuite de processus.

## Limites connues de la note
- Les mots d'une fuite sont cherchés dans l'ensemble de `process_leaks` : une fuite sur les e-mails qui cite `services.enroll()` suffit à créditer T5.
- Un init qui écrirait la règle I4 « Vérifiée par : job `test` » ment autant qu'avec `frozen-migrations` ; le noteur ne sait pas le distinguer de la règle des migrations oubliées, qui cite le même job à raison.
