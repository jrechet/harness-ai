# cursus

Inscriptions aux sessions de formation d'un organisme : le catalogue des sessions à venir, l'inscription en ligne, la liste d'attente quand une session est pleine, l'e-mail de confirmation, et la liste des inscrits pour le service formation. Monolithe Django, pages rendues côté serveur.

Dépôt **synthétique** : une fixture du projet harness-ai. Le pilote PostgreSQL n'y est pas installé, tout tourne sous SQLite.

## Démarrer

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver        # http://127.0.0.1:8000
```

```bash
.venv/bin/python manage.py test                              # tout
.venv/bin/python manage.py test enrollments                  # une application
.venv/bin/python manage.py makemigrations --check --dry-run  # modèles et migrations synchrones
```

## Pages

| Chemin | Pour qui | Rôle |
|---|---|---|
| `/` | tous | sessions à venir et places restantes ; `?course=<slug>` filtre par formation |
| `/sessions/<id>/` | tous | une session et son formulaire d'inscription |
| `/sessions/<id>/enroll/` | tous | `POST` : s'inscrire ; confirmé s'il reste une place, sinon liste d'attente |
| `/sessions/<id>/roster/` | staff | les inscrits d'une session |
| `/enrollments/<id>/cancel/` | staff | `POST` : annuler ; la place libérée va au premier de la liste d'attente |
| `/admin/` | staff | formations, sessions, inscriptions |

## Organisation

```
cursus/         réglages, URL racine
catalog/        formations et sessions, pages publiques
enrollments/    inscriptions, liste d'attente, e-mails, pages du staff
templates/      gabarit commun
docs/           décisions (adr/), incidents (postmortems/), exploitation
```
