# Incident du 18 mars 2024 — 4 312 e-mails de confirmation en onze minutes

## Ce qui s'est passé
La reprise de l'historique de l'ancien tableur a été lancée en production un lundi à 10 h 05. Le script lisait le fichier et enregistrait chaque inscription avec `Enrollment.objects.create(...)`. À chaque enregistrement, le signal `post_save` d'`Enrollment` a envoyé l'e-mail « Inscription confirmée ». 4 312 e-mails sont partis en onze minutes, la plupart vers des personnes inscrites à des sessions terminées depuis 2021.

## Conséquences
- Le prestataire SMTP a suspendu le compte à 10 h 16 pour taux de plaintes anormal. Suspension levée après 36 heures.
- Pendant ces 36 heures, 214 vraies inscriptions n'ont reçu aucune confirmation. Le service formation a rappelé chaque personne.
- Une quarantaine de personnes ont téléphoné ou se sont présentées pour une session qui avait eu lieu deux ans plus tôt.

## Cause
L'envoi était branché sur `post_save`. Un signal part à chaque sauvegarde, d'où qu'elle vienne : une vue, l'admin, un script, un chargement de données. Personne ne pensait à l'e-mail en écrivant le script, et rien dans le script ne le montrait.

## Corrections
- Le signal est supprimé. L'envoi est un appel explicite dans `enrollments/services.py`, après le commit (`transaction.on_commit`). Les messages vivent dans `enrollments/notifications.py`.
- Hors production, `EMAIL_BACKEND` est la console (`cursus/settings.py`).
- Décision : **un traitement en masse n'envoie jamais un e-mail par ligne.** Un import, une commande de gestion, une action d'admin enregistrent sans prévenir. Si les personnes doivent être prévenues, le service formation le décide et envoie lui-même, en une fois.

## Ce qui reste ouvert
- Rien n'empêche de rebrancher un envoi sur un signal ou dans `save()` : la revue est le seul contrôle.
- `services.enroll()` envoie toujours sa confirmation. Le prochain traitement en masse devra pouvoir inscrire sans envoyer. La reprise, elle, a été rejouée avec le backend console.
