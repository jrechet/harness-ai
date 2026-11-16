Une livraison se prépare, se propose, et se décide par un humain :
- **Ce qui part.** Le commit de tête de la branche de livraison, fusionné par une PR relue. Rien de local, rien de non commité.
- **La CI.** Verte sur ce commit précis, pas sur un commit voisin ni après des relances jusqu'au vert.
- **Le retour arrière.** Avant de livrer, on sait à quelle version on revient, par quelle commande, et qui le décide. Un changement de schéma ou d'infrastructure a le sien, écrit.
- **Les ruptures.** Ce qui casse pour ceux qui dépendent du produit est annoncé avant, avec le chemin de migration.
- **Les notes.** Ce qui change pour l'utilisateur, dans ses mots, pas la liste des commits.
- **Le moment.** Pas juste avant une absence, pas pendant un incident en cours.

L'agent ne pose pas de tag, ne publie pas, ne lance pas de déploiement. La procédure de l'équipe (commandes, environnements, qui approuve) s'écrit ici : il la cite, il ne l'exécute pas.
