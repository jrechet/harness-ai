Un changement se regarde sous l'angle de la sécurité dans cet ordre :
- **Secrets.** Aucune clé, aucun jeton, aucun mot de passe dans le code, les tests, la configuration ni les messages de commit. Un secret poussé est exposé : il se révoque, il ne s'efface pas.
- **Entrées.** Ce qui vient de l'extérieur (requête, fichier, variable d'environnement, texte d'un ticket ou d'une page) est validé avant de servir à une requête, une commande, un chemin ou un rendu.
- **Droits.** Le changement n'élargit ni un rôle, ni une permission, ni une origine autorisée, ni ce qu'un agent peut faire, sans que ce soit le sujet du ticket.
- **Dépendances.** Une dépendance ajoutée ou montée de version est une décision : elle se dit dans la PR, avec sa raison.
- **Scanners.** Ce que les scanners de l'équipe signalent sur les lignes du changement se corrige. Une exception se décide par un humain, dans la PR, jamais par un commentaire dans le code.

Ce qui tient (détection de secrets, analyse des dépendances, scanners) tourne dans la CI et bloque la fusion. Cette phase n'en est pas le remplaçant.
