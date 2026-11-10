# Web

- Toute valeur venue d'un utilisateur passe par `escapeHtml` avant d'entrer dans du HTML. Pourquoi : le test d'intrusion de mars 2026 a exécuté du script depuis un titre de ticket. Vérifiée par : `apps/web/src/ticket-list.test.ts`, pour la liste seulement. [2026-03]
