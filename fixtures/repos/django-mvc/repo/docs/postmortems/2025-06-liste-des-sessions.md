# Incident du 3 juin 2025 — la page d'accueil en quatorze secondes

## Ce qui s'est passé
Après la mise en ligne du catalogue du second semestre (380 sessions), la page d'accueil a mis jusqu'à 14 secondes à s'afficher. À l'ouverture des inscriptions de 9 h, le serveur a saturé : 25 minutes de pages en erreur.

## Cause
Une PR de mai avait ajouté « places restantes » et « en attente » à la liste. Le template appelait pour chaque session deux propriétés du modèle, qui faisaient chacune un `count()` : 1 + 2 × N requêtes. Avec les vingt sessions d'un poste de développement, personne ne l'avait vu.

La consigne « pas de requête par ligne dans une liste » était écrite dans `AGENTS.md` depuis 2024. Elle demandait de compter à la main avec django-debug-toolbar. La PR ne l'avait pas fait, la revue non plus.

## Corrections
- `Session.objects.with_seats()` : les compteurs sont des annotations, la formation vient par `select_related`. La liste est paginée.
- `catalog/tests/test_queries.py` fixe le nombre de requêtes de chaque page de liste (`assertNumQueries`), avec quinze lignes et plus. Le job `test` de la CI le lance à chaque PR et bloque la fusion.
- django-debug-toolbar est retirée des dépendances : plus personne ne compte à la main.
