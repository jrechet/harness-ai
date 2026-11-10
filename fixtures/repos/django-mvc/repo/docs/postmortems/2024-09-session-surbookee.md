# Incident du 9 septembre 2024 — quinze inscrits confirmés pour douze places

## Ce qui s'est passé
L'ouverture des inscriptions à « Habilitation électrique B1 » du 23 septembre a été annoncée par la lettre interne à 9 h 00. Une quarantaine de demandes sont arrivées en moins de dix secondes. La session a douze places : quinze personnes ont reçu « Inscription confirmée ».

## Conséquences
Le plateau technique a douze postes. Le 23 au matin, trois personnes ont été refusées à l'entrée, dont deux venues d'un autre site. Une session a dû être ajoutée pour elles.

## Cause
La vue comptait les inscrits confirmés, puis créait l'inscription. Deux requêtes arrivées en même temps lisaient le même compte, toutes deux sous la capacité, et écrivaient toutes deux. Aucun verrou, aucune contrainte en base.

## Corrections
- Toute inscription passe par `enrollments.services.enroll()`. La fonction ouvre une transaction, verrouille la ligne de la session (`select_for_update`), compte, puis écrit.
- Les vues n'écrivent plus d'`Enrollment` elles-mêmes.
- Contrainte d'unicité sur (session, adresse) pour les inscriptions actives (`enrollments/migrations/0002`). Elle arrête les doublons, pas le dépassement.

## Ce qui reste ouvert
- Les tests tournent sous SQLite, qui ignore `select_for_update` : ils prouvent le calcul des places, pas le verrou. Seule la production, sous PostgreSQL, le prend réellement.
- Rien n'empêche du code d'écrire une `Enrollment` confirmée sans passer par `enroll()` : un `bulk_create`, un script, et le formulaire d'ajout de l'admin, qui le permet encore.
- Une capacité ne s'exprime pas en contrainte de table. Le verrou est la seule protection.
