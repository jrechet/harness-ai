# ADR 0001 — La logique métier vit dans les services

Date : 2023-11-20. Statut : accepté.

## Contexte
Une application Django offre quatre endroits où poser une règle : la vue, le formulaire, le modèle (`save()`, signaux), le template. Sans décision, les quatre finissent par en porter un morceau.

## Décision
- Une règle métier (places, liste d'attente, annulation) s'écrit une fois, dans le `services.py` de son application.
- Une vue lit la requête, appelle un service, choisit la réponse. Une action d'admin fait de même.
- Un modèle décrit des données et leurs contraintes de table. Pas de règle dans `save()`.
- Un template affiche ce que la vue lui donne.

## Vérification
Aucune. C'est une convention de revue. Aucun incident ne lui est dû à ce jour.
