J'ai posé le palier 1 (« Cadré ») sur le dépôt. Le contrôle `harness.py status` donne 5 vérifications sur 5 et plus aucune référence vers un élément absent. Je n'ai rien commité et je n'ai pas ouvert de PR, ce n'était pas demandé.

Deux actions ont été refusées automatiquement, faute de pouvoir les approuver dans cette séance : une commande Bash combinée (rien de bloquant, j'ai lu les fichiers autrement) et `pip install -r requirements.txt`. Sans Django installé, **je n'ai pu lancer aucun test ni aucune commande `manage.py`**.

## Compte rendu

**Avant et après**
- **Palier** : 0 avant, 1 après.
- **Lignes chargées par session** : avant, 21 pour Claude Code (`CLAUDE.md`) et 67 pour Copilot (`AGENTS.md`). Après, 20 pour tous les outils (`AGENTS.md`, que `CLAUDE.md` importe).
- **Règles** : avant, 7 règles projet plus environ 15 consignes de style, de compatibilité et de git, dont aucune datée ni vérifiée. Après, 7 règles et 3 Interdits, tous datés.

**Fichiers**
- `AGENTS.md` : réécrit, de 67 à 20 lignes.
- `CLAUDE.md` : ramené de 21 lignes à 1 (`@AGENTS.md`).
- `.github/copilot-instructions.md` : créé (1 ligne). Il n'y a pas de stub Cursor, l'équipe ne l'utilise pas.
- `.harness/state.json` : écrit par le CLI.

**Retiré**
- *Inutile* (l'agent le trouve seul, ou le modèle le fait sans qu'on le dise) :
  - l'arborescence et la stack ;
  - « réfléchis étape par étape », « n'invente pas d'API » ;
  - PEP 8, « noms clairs », « pas de print » ;
  - « une branche par sujet » et « PR vers `main` » : la CI ne tourne que sur `main` ;
  - `runserver` et `makemigrations` : ces commandes sont déjà dans le README.
- *Nuisible* :
  - « Donne toujours le fichier complet » : en délégation, l'agent modifie des fichiers et ouvre une PR, il ne colle pas de réponse.
  - `test --settings=cursus.settings_ci` : ce fichier de réglages n'existe pas, la commande échoue.
  - Le job CI `frozen-migrations` : il n'existe pas, donc la règle se croyait vérifiée à tort. Le propriétaire a confirmé le retrait.
  - « Ouvre la page avec django-debug-toolbar » : l'outil a été retiré des dépendances en juin 2025 et le test qui compte les requêtes le remplace.
  - « Toute inscription créée envoie sa confirmation » (`CLAUDE.md`) : contredit la décision prise après l'incident de mars 2024 (un traitement en masse n'envoie pas un e-mail par ligne).
- *Périmé*, retiré après confirmation du propriétaire :
  - Python 3.8 : la production tourne en 3.12 depuis février 2025.
  - Django 4.2 LTS : l'équipe suit les versions courantes depuis le changement d'hébergeur, Django 5.1 aujourd'hui.
- *Retiré de ma propre initiative, à confirmer* : les lignes de 100 caractères au plus, une docstring par fonction publique, et « un test par changement ». Aucun outil ne les vérifie et le dépôt enfreint déjà les deux premières (`enrollments/views.py`, `enrollments/notifications.py`). Voir la question 2.

**Secrets** : aucun trouvé. Les réglages ne lisent que des variables d'environnement ; la seule valeur par défaut est une clé de développement explicite.

**Règles écrites**

| Règle | Statut | Date |
|---|---|---|
| Français pour les réponses et les commits, anglais pour le code | non vérifiée | 2026-11 |
| E-mails : pas de signal, pas d'envoi par ligne dans un traitement en masse | non vérifiée | 2024-03 |
| Capacité : toute inscription passe par `enroll()` ; le formulaire d'ajout de l'admin est signalé comme contre-exemple | non vérifiée | 2024-09 |
| Pages de liste : pas de requête par ligne | vérifiée par `catalog/tests/test_queries.py` | 2025-06 |
| Plafond `CURSUS_IMPORT_MAX_ROWS` (500 lignes, fichier refusé au-delà), réglage qui n'existe pas encore ; dit par l'équipe | non vérifiée | 2025-02 |
| La logique métier vit dans `services.py` (ADR 0001) | non vérifiée | 2023-11 |
| `timezone.now()` | non vérifiée | 2026-11 |

Pour la règle sur les pages de liste, j'ai vu le job `test` lancer `manage.py test` sans `continue-on-error`, et le propriétaire confirme que ce job bloque la fusion. Je n'ai pas pu exécuter le test moi-même.

Interdits :
- Modifier une migration existante [2024-01]. Aucun job de CI ne le refuse aujourd'hui.
- Envoyer un vrai e-mail hors production [2024-03].
- Sortir du serveur des données personnelles d'inscrits [2026-11].

**Commandes**
- Confirmées : aucune.
- Non confirmées, car Django n'a pas pu être installé : `python manage.py test`, `python manage.py makemigrations --check --dry-run`, `python manage.py check`. Ce sont celles que lance la CI ; je n'ai donc pas fait de tableau des commandes dans `AGENTS.md`.

**Questions au propriétaire**
1. Un futur import doit-il pouvoir inscrire sans envoyer d'e-mail ? `enroll()` envoie toujours, et le post-mortem de mars 2024 laisse ce point ouvert. *Défaut appliqué :* un traitement en masse n'appelle pas `enroll()` tel quel.
2. Les lignes de 100 caractères et la docstring par fonction publique sont-elles toujours voulues ? *Défaut :* retirées tant qu'aucun linter ne les porte.
3. Faut-il fermer le formulaire d'ajout d'inscription de l'admin, qui contourne `enroll()` ? *Défaut :* signalé dans `AGENTS.md` comme contre-exemple, sans y toucher.
4. Faut-il recréer le contrôle des migrations figées en CI, que les anciennes instructions croyaient en place ? *Défaut :* l'Interdit reste sans garde-fou.

**Pas suivant possible** : boucler le fichier (palier 2 : section Maintenance, convention `rule:`) avec `harness target 2` puis harness-step. Je ne l'ai pas fait.