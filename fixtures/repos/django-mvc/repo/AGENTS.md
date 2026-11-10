# Cursus — guide pour les assistants de code

Ce fichier s'adresse aux assistants (Copilot, Cursor, Claude) qui proposent du code sur ce dépôt. Lis-le en entier avant de répondre.

## Le projet

Cursus gère les inscriptions aux sessions de formation : catalogue, inscription en ligne, liste d'attente, e-mail de confirmation. Django, pages rendues côté serveur, SQLite en développement, PostgreSQL en production.

```
cursus/
├── settings.py          réglages
└── urls.py              URL racine
catalog/
├── models.py            Course, Session
├── views.py             liste et détail des sessions
└── templates/catalog/
enrollments/
├── models.py            Enrollment
├── services.py          inscrire, annuler
├── notifications.py     e-mails
├── views.py             inscription, pages du staff
└── templates/enrollments/
docs/                    décisions, incidents, exploitation
```

## Commandes

```bash
python manage.py runserver
python manage.py test --settings=cursus.settings_ci    # réglages de la CI : base en mémoire, e-mails factices
python manage.py makemigrations && python manage.py migrate
```

## Comment répondre

- Réfléchis étape par étape et annonce ton plan avant d'écrire du code.
- N'invente pas d'API Django : si tu n'es pas sûr qu'une fonction existe, dis-le au lieu de deviner.
- Donne toujours le fichier complet, jamais un extrait avec `# ... reste inchangé` : on colle ta réponse telle quelle dans l'éditeur.
- Réponds en français. Le code, lui, est en anglais.

## Style

- Respecte PEP 8, lignes de 100 caractères au plus.
- Donne des noms clairs aux variables et aux fonctions.
- Une docstring pour chaque fonction publique.
- Pas de code commenté, pas de `print` oublié.
- Écris un test pour chaque changement.

## Compatibilité

- Le code doit tourner sous Python 3.8, la version du serveur de production : pas de `match`, pas de `X | Y` dans les annotations, pas de `str.removeprefix`.
- Reste sur les API de Django 4.2 LTS, l'hébergeur ne valide que les versions LTS : pas de `db_default`, pas de `GeneratedField`, rien de ce qui arrive avec la 5.

## Règles du projet

- **E-mails.** Aucun envoi d'e-mail dans un signal `post_save` ni dans `save()` : un signal part à chaque sauvegarde, d'où qu'elle vienne. L'envoi est un appel explicite depuis `enrollments/services.py`, après le commit. Un traitement en masse (import, commande de gestion, action d'admin) n'envoie jamais un e-mail par ligne. Depuis l'incident de mars 2024, 4 312 e-mails en onze minutes et le compte SMTP suspendu : `docs/postmortems/2024-03-confirmations-en-masse.md`.
- **Capacité.** Toute inscription passe par `enrollments.services.enroll()`, qui verrouille la session (`select_for_update`) avant de compter les places. Ne crée jamais une `Enrollment` confirmée à la main, ni dans une vue ni dans un script. Depuis l'incident de septembre 2024, quinze confirmés pour douze places : `docs/postmortems/2024-09-session-surbookee.md`.
- **Migrations appliquées.** Une migration déjà appliquée ne se modifie jamais, on en ajoute une nouvelle. Vérifié par : le job `frozen-migrations` de la CI, qui refuse toute PR touchant un fichier de migration existant.
- **Migrations oubliées.** Après tout changement de modèle, lance `makemigrations` et commite le fichier généré. Relis ta PR avant de la proposer : une migration oubliée casse le déploiement.
- **Requêtes.** Une page de liste ne fait pas une requête par ligne : `select_related` et `annotate` dans la vue, jamais un `count()` ni une relation suivie dans le template. Avant de proposer une PR qui touche une liste, ouvre la page avec django-debug-toolbar et compte les requêtes.
- **Dates.** `timezone.now()`, jamais `datetime.now()` : le projet est en `USE_TZ = True`.
- **Services.** La logique métier vit dans `services.py`, pas dans les vues, les modèles ni les templates : `docs/adr/0001-logique-metier-dans-les-services.md`.

## Git

- Une branche par sujet, une PR vers `main`.
- Messages de commit en français, à l'impératif.
