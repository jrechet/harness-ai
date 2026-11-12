L'annulation et le remboursement fonctionnent, et les tests passent (31 sur 31). C'est enregistré sur une branche à part, `annuler-commande`, pas sur la version principale.

**Ce qui change pour la boutique**
- **Annuler une commande pas encore payée** : elle passe à « annulée ». Le stock ne bouge pas, puisqu'il ne sort qu'au paiement. Annuler deux fois la même commande ne pose pas de problème.
- **Une commande déjà payée ne s'annule pas par là** : elle reste payée. Pour elle, vous la remboursez comme d'habitude dans le tableau de bord PayFlux (Paiements > la commande > Rembourser). PayFlux prévient alors le site, la commande passe à « remboursée » et ses articles reviennent en stock.
- **Protection contre les doublons** : si PayFlux envoie plusieurs fois le même message, le stock n'est retiré ou rendu qu'une seule fois. C'était la cause du problème des croissants du 14 mars. Jusqu'ici, cette protection n'était testée que sur une copie du code ; elle est maintenant testée sur le vrai.

**Ce que vous devez savoir**
1. **Il n'y a pas de bouton « Annuler » sur la page de commande.** Je n'ai fait que la partie serveur, comme demandé. Pour que vos clients annulent eux-mêmes, il faut ajouter ce bouton : dites-moi si vous le voulez.
2. **Un client peut payer après avoir annulé**, avec le lien qu'il avait gardé. Dans ce cas, la commande reste annulée et le stock n'est pas touché. Ce paiement n'apparaît pas dans la liste des commandes, seulement dans le journal du serveur. Vous le verrez donc surtout dans PayFlux, et vous devrez rembourser ce client à la main.
3. **Un remboursement remet toujours en stock toute la commande**, même si vous ne remboursez qu'une partie de la somme dans PayFlux.

**Ce que j'ai fait d'autre**
- J'ai mis à jour `NOTES.md` et `TODO.md`, où « Annuler une commande » est cochée.
- J'ai mis à jour la règle sur les messages PayFlux reçus en double dans `AGENTS.md`.
- Je n'ai pas touché au fichier des commandes (`data/db.json`), ni à `src/routes-v2/`, et je n'ai rien installé.

Je n'ai pas fusionné la branche dans la version principale ni rien envoyé en ligne : dites-moi quand vous voulez que je le fasse.