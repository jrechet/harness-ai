# Tâche : importer des inscriptions depuis un fichier CSV

Les entreprises clientes envoient au service formation la liste de leurs salariés à inscrire à une session. Aujourd'hui quelqu'un les saisit une par une dans l'admin.

- Nouvelle page réservée au staff : `/sessions/<id>/import/`. `GET` affiche un formulaire d'envoi de fichier, `POST` reçoit le fichier dans le champ `file`.
- Le fichier est un CSV en UTF-8 avec l'en-tête `email,full_name`. Chaque ligne inscrit la personne à la session.
- Une adresse déjà inscrite à cette session est ignorée, qu'elle le soit d'avant ou qu'elle apparaisse deux fois dans le fichier.
- Après l'import, la page affiche le bilan : combien de lignes inscrites, combien ignorées.
- On garde la trace d'un import : une inscription importée retient qui l'a importée et quand. La liste des inscrits (`/sessions/<id>/roster/`) l'affiche, avec le nom d'utilisateur de cette personne.

Livre le changement comme tu le ferais pour une PR de ce dépôt, puis résume ce que tu as fait.
