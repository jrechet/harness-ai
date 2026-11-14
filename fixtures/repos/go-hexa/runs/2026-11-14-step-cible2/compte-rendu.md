## Compte rendu

- **Le pas** : j'ai ajouté le bloc « Pas 2 » du gabarit à la fin d'`AGENTS.md`. Il contient la section « Maintenance de ce fichier », la convention `rule:` en review et le marqueur `<!-- harvest: last=2026-11-14 ref=init -->`. Le fichier n'avait pas encore de marqueur.

- **Avant et après** : on reste au palier 1 (Cadré), avec le palier 2 (Bouclé) comme objectif. Le palier 2 passe de **0/4 à 3/4** vérifications. Trois lignes ont basculé :
  - « Une section Maintenance dit comment le fichier évolue » ;
  - « La convention `rule:` en review est documentée » ;
  - « Un harvest a tourné depuis moins de 45 jours ».

  Attention à cette dernière : elle passe grâce au marqueur `ref=init`, mais aucun harvest n'a réellement tourné. Le marqueur ne fait que démarrer le compteur.

- **Ce que ça change pour l'agent** : quand un commentaire de review commence par `rule:`, l'agent sait qu'il doit l'ajouter à `AGENTS.md` dans la même PR, avec la date et un lien vers le commentaire. Avant d'écrire une règle, il doit aussi chercher si un outil peut la faire respecter à sa place.

- **Ce qui n'est pas prouvé** : tout le fond. `status` constate seulement que les sections sont là, pas que la boucle de retour fonctionne. Il n'existe encore aucune preuve : aucun harvest n'a tourné, aucun `rule:` n'a été écrit en review, aucune PR d'agent n'a été observée. La 4ᵉ vérification (« signal réel ») ne peut passer qu'avec du temps et de vraies reviews. Ajouter une règle pour la faire passer irait contre le but recherché.

- **Fichiers** : `AGENTS.md`, qui passe de 25 à 32 lignes, sous la limite de 60. Je n'ai rien commité, car personne ne l'a demandé. Le dossier `.harness/` est toujours non suivi par git ; il existait déjà avant ce pas.

- **Questions** : aucune. Il reste une habitude à transmettre à l'équipe : *« Quand une remarque de review mérite de devenir une règle, commencez votre commentaire par `rule:` suivi de la règle en une phrase vérifiable. L'agent ou le prochain harvest la reportera dans AGENTS.md. »*

- **Le pas suivant possible** : il n'y a rien à faire pour l'instant. La boucle est en place mais n'a pas encore tourné. Une fois que des reviews auront contenu des `rule:` ou que des PR d'agent auront été corrigées, il faudra lancer harness-harvest. S'il trouve un vrai signal, la 4ᵉ vérification passera et le palier 2 sera atteint.