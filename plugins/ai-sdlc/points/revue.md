Une revue cherche ce qui coûterait cher une fois fusionné. Dans cet ordre :
- **Justesse.** Le changement fait-il ce que la PR et le ticket disent ? Cas limites, erreurs avalées, données perdues.
- **Périmètre.** Le diff sort-il de ce qui est demandé ? Un changement hors sujet se signale, même s'il est bon.
- **Tests.** Un comportement changé a-t-il un test qui échouerait sans le changement ? Un test désactivé ou affaibli se signale toujours.
- **Contrats.** Une API, un schéma, un format de fichier ou de message changent-ils pour ceux qui en dépendent ?
- **Sécurité.** Entrée non validée, secret dans le code, droit élargi, requête construite par concaténation.
- **Règles du dépôt.** Les Interdits et les règles d'AGENTS.md, chacune citée par sa ligne.

Ne se commente pas : le style, le nommage, la mise en forme, ce qu'un linter ou un formateur tranche. Si le dépôt n'en a pas, dis-le une fois, hors des commentaires.
