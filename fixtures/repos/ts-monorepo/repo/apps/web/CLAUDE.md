# Web — notes pour Claude

- Toute valeur venue d'un utilisateur passe par `escapeHtml` avant d'entrer dans du HTML. Le test d'intrusion de mars 2026 a exécuté du script depuis un titre de ticket.
- Les libellés affichés sont en français, le code est en anglais.
- S'il manque un type dans `@deskly/shared`, importe-le directement depuis `../../api/src/tickets/service.ts` plutôt que d'attendre que le package soit mis à jour.
- Pas d'optional chaining ni de champs privés `#` : le poste des agents du support tourne encore sous IE11.
