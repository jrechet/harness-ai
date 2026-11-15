# Notes — revue du skill `release` avec harness-design

Besoin reformulé : que chaque version soit calculée juste, documentée, publiée depuis `main` seulement, sans que l'agent voie le jeton, puis annoncée.
11 morceaux, `place plan` sort en code 0.

## Ce qui a gêné
- **`current` d'une règle « Vérifiée par » dont le workflow est absent** (morceau 8, `AGENTS.md:7`). Le skill dit d'ouvrir le workflow pour vérifier ; `artifact/` ne contient pas `.github/workflows/ci.yml`. J'ai mis `current=agents_md` (non prouvé bloquant), d'où PUSH_DOWN. Si le job `commitlint` existe et est requis, le verdict est KEEP. Le skill ne dit pas quoi faire quand le check cité est introuvable.
- **« Version mal calculée = incident » n'a pas de question dans la branche `compute`.** La grille ne demande que `when` ; l'incident ne change pas la destination (CLI testée). Je n'ai pas ajouté de morceau `rule` « la version publiée est celle calculée » : il n'existe pas dans l'artefact, et le workflow de livraison qui appelle la sous-commande le tient. Hypothèse, pas certitude.
- **Envoyer l'annonce sur `#releases`** (morceau 11) : `access` n'offre que `consult` (lit ou commente) ou `deliver` (build, tag, publication). Poster un message est une écriture externe qui n'est ni l'un ni l'autre ; j'ai répondu `consult` → serveur MCP, sans conviction. Le dépôt ne déclare aucun serveur MCP.
- **Contrainte de forme de l'annonce** (« trois lignes au plus, sans reprendre le changelog », `SKILL.md:17`) : comme `rule` avec `incident=no`, la grille mène à `scope`, dont aucune réponse ne dit « seulement dans ce skill » (`reference` → un doc à part, trop lourd). Je l'ai laissée dans le morceau de jugement 9. Trou de grille probable : une préférence propre à une procédure.
- **Le jeton** : `SKILL.md:16` demande à l'agent de copier le jeton, `AGENTS.md:6` l'autorise « hors d'une release » seulement ; le propriétaire dit « jamais ». J'ai coupé en deux : la limite (morceau 7, permission `deny`, `bypass_limit=agent` puisqu'un développeur y a accès) et l'usage du jeton, absorbé par le workflow de livraison (morceau 6, secret d'environnement protégé). La ligne d'AGENTS.md et l'étape 5 du skill sont donc à réécrire, pas seulement à déplacer ; le verdict PUSH_DOWN ne le dit pas.
- **Verdict PUSH_DOWN sur le morceau 4** : le changelog est exigé à la publication, pas à la fusion ; « check bloquant en CI » se lit ici comme un check du workflow de release (ou de la PR de release). La grille ne distingue pas les deux.
- **Sans CLI dans le dépôt** : « sous-commande CLI testée » (morceau 3) devient un script appelé depuis `package.json` ; le tableau de l'étape 5 le dit, la sortie du plan non.
- `place plan` n'affiche pas les `evidence` ; je ne sais pas si le format `chemin:ligne` relatif à `artifact/` est validé à ce stade.

## Observé hors grille
- `release-reviewer` n'a que `Read, Grep` mais doit lire « les commits depuis le dernier tag » : sans git, il ne peut pas. Le plan dit KEEP sur la place ; le contenu est à corriger.
- La ligne « Mode : assistance » (`AGENTS.md:3`) n'est pas une règle : non découpée.

## Non placé
- Rien n'est resté sans destination. Deux placements sont fragiles : le morceau 11 (envoi de l'annonce) et la contrainte de forme de l'annonce, fondue dans le morceau 9.
