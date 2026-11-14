# AI SDLC — proposition

Document de travail, 2026-11-14. Il confronte l'idée de départ du propriétaire à l'état des lieux ([rapport](reports/Pratiques%20IA%20SDLC%20des%20grandes%20entreprises.md), [notes sourcées](research_notes/Pratiques%20IA%20SDLC%20des%20grandes%20entreprises/)) et propose une approche. Rien ici ne modifie harness-ai : le framework s'appuie sur ce que harness-ai pose et mesure, il ne le remplace pas.

## L'idée de départ

Un framework d'entreprise, des skills et des agents qui partent d'un ticket Jira et accompagnent PO, devs, QA, sécurité et SRE jusqu'à la production, appliqué à des dizaines d'équipes. Convention plutôt que configuration : `/dev` marche tel quel, et une équipe qui a ses propres règles (QA, revue…) ajoute un Markdown dans son dépôt que le skill prend en compte tout seul. Au premier lancement, le framework crée les fichiers attendus (revue, QA…), même vides, et chaque équipe les remplit à son rythme.

## Ce que disent les preuves, en huit lignes

1. **La forme que tu proposes est celle qui s'est imposée.** Partout où c'est documenté à l'échelle (Doctolib, Zalando, Intercom, Stripe, Spotify, Uber), on trouve trois couches : une plateforme centrale (passerelle de modèles, identités, bacs à sable, télémétrie), un socle versionné de skills, agents et hooks poussé à tous, et des ajouts d'équipe par dépôt ou dossier. Personne ne laisse tout aux équipes, personne n'impose un seul agent.
2. **Ce qui est garanti l'est par du code, jamais par du Markdown.** Tous les éditeurs documentent les fichiers d'instructions comme des conseils. Claude Code écrit qu'en cas de contradiction le modèle « may pick one arbitrarily ». Ce qui verrouille : hooks, paramètres gérés, CI, protection de branche.
3. **Plus d'instructions n'est pas mieux.** Un AGENTS.md généré par un LLM baisse légèrement le taux de réussite et coûte 20 à 23 % de plus ; un fichier court écrit par l'équipe gagne environ 4 points (ETH Zurich, ICLR 2026). Thoughtworks classe « agent instruction bloat » en Caution (Radar vol. 35, nov. 2026).
4. **Un seul parcours pour toutes les tailles de problème échoue.** Kiro a transformé un petit bug en 4 user stories et 16 critères d'acceptation (Böckeler, oct. 2025). Kiro (Quick Spec) et BMAD (Quick Flow) ont depuis ajouté un mode léger, et Spec Kit a rendu ses étapes de contrôle optionnelles.
5. **Le goulot passe de l'écriture à la vérification.** Temps de revue multiplié par 5, incidents par PR en hausse (Faros 2026, télémétrie vendeur, 22 000 devs) ; débit en hausse mais instabilité aussi (DORA 2025). Ceux qui tiennent ont des vérificateurs déterministes autour de l'agent : Spotify n'ouvre pas la PR si un vérificateur échoue, puis un juge LLM refuse environ 25 % des sessions.
6. **Le ticket compte plus que le prompt.** Chez Atlassian, la qualité du ticket prédit la réussite de l'agent (HULA, 2024). Chez Airbnb, choisir les bons fichiers liés a compté plus que la formulation.
7. **L'adoption ne se décrète pas.** Docusign plafonnait à 49 % avec l'accès seul et a atteint 93 % avec des champions. Doctolib est passé de 30 ingénieurs pilotes à 600 en six mois environ. Les mandats (Coinbase, Duolingo) ont produit du rejet, et le classement d'usage d'Amazon a été joué puis retiré.
8. **Personne n'a mesuré ce qu'on s'apprête à faire.** Aucune étude ne teste un framework uniforme sur des dizaines d'équipes, et la plupart des chiffres d'entreprise sont des comptes de PR publiés par les vendeurs. Il faudra se mesurer soi-même.

## Ta proposition, confrontée

| Ton idée | Verdict | Pourquoi |
|---|---|---|
| Un socle commun, convention plutôt que configuration | **Garder** | C'est la forme dominante (point 1). Thoughtworks l'appelle « enterprise harness », une couche « thin, federated » (Assess, nov. 2026). |
| L'équipe surcharge par un Markdown dans son dépôt | **Garder, en bornant** | Le Markdown ne peut qu'ajouter du conseil. Ce qui doit tenir (sécurité, porte de merge, déploiement) ne vit pas dans un fichier qu'une équipe peut contredire, ni d'ailleurs dans celui du framework (point 2). |
| Le skill prend en compte les surcharges « automatiquement » | **Garder, mais par un outil, pas par le modèle** | Si le skill concatène ce qu'il trouve, c'est le modèle qui arbitre les contradictions, au hasard. Les outils sérieux définissent une sémantique : Spec Kit remplace, préfixe, suffixe ou enveloppe ; BMAD remplace les valeurs simples, fusionne les tables, n'ajoute qu'aux listes et interdit de retirer du socle. |
| Créer les fichiers attendus au premier lancement, même vides | **Changer** | Un fichier vide invite à le remplir, et on le remplit de générique : c'est exactement le bloat du point 3, et ce que harness-init retire déjà des dépôts. Le besoin réel, voir où l'on peut agir, se sert autrement (voir « Points d'extension »). |
| `/dev` développe la tâche de bout en bout | **Garder pour le dev, déplacer la garantie** | `/dev` est le confort. La valeur du framework est dans ce qui vérifie après, hors de la session qui a écrit le code. |
| Appliquer le framework à des dizaines d'équipes | **Changer l'ordre** | Trois équipes pilotes hétérogènes, des champions, puis des vagues (point 7). Les surcharges des pilotes disent ce que le socle a de faux. |

Trois angles que l'idée de départ ne traite pas encore :
- **D'où se lit une surcharge de porte.** Claude Code Review lit `REVIEW.md` sur la branche de base, « never from the pull request's own changes » ; Copilot lit la branche de la PR. Une PR ne doit pas pouvoir alléger sa propre revue.
- **La taille du changement.** Une faute de frappe et une migration de schéma ne prennent pas le même chemin.
- **Les outils des équipes.** Zalando, Shopify et Uber n'imposent pas d'outil ; Amazon a ouvert Claude Code et Codex en mai 2026 après avoir recommandé Kiro. Les Agent Skills sont un standard ouvert depuis leur don à l'Agentic AI Foundation (2026-10-22), et AGENTS.md est lu par tous.

## L'approche proposée

### Trois couches, et qui possède quoi

| Couche | Contenu | Possédé par | Nature |
|---|---|---|---|
| **Plateforme** | Passerelle de modèles, identités, bacs à sable des agents distants, télémétrie, paramètres gérés | Équipe plateforme de l'entreprise | Prérequis, hors de ce framework |
| **Socle AI SDLC** | Skills de phase, CLI de résolution, workflows CI de vérification, verrous | Petite équipe centrale, en mode équipe facilitatrice | Versionné, distribué en plugin |
| **Équipe** | AGENTS.md (posé par harness-ai), surcharges par point d'extension, skills d'équipe | Chaque équipe | Dans le dépôt |

C'est la grille L1–L4 de harness-ai appliquée au framework : le skill raconte la phase (L2), le CLI résout les surcharges et vérifie (L3), la CI porte les portes (L4). Le modèle juge (L1) à l'intérieur de ce cadre.

### Les phases : une chaîne de petits skills, pas un super-agent

Aucune chaîne documentée n'utilise un agent unique de bout en bout : chacune relie des agents spécialisés par des objets qu'un humain inspecte (ticket, PR, check CI, issue).

```
Ticket Jira ─▶ /ticket ─▶ /dev ─▶ PR ─▶ checks /review /qa /secu ─▶ merge humain ─▶ /ship ─▶ /run
   PO          prêt ?     session      en CI, sur la branche de base     porte L4      propose   enquête
```

| Skill | Aide | Fait | Ne fait jamais | Preuve dans l'état des lieux |
|---|---|---|---|---|
| `/ticket` | PO | Confronte le ticket à la définition de prêt de l'équipe, propose critères d'acceptation et découpage, classe la taille | Modifier le ticket sans accord | Atlassian : cinq traits simples d'un ticket prédisent l'échec de l'agent avec environ 97 % de précision |
| `/dev` | Dev | Plan à la mesure de la taille, implémentation, lance les commandes du tableau d'AGENTS.md, ouvre la PR liée au ticket | Merger, toucher un interdit | Stripe : plus de 1 300 PR d'agent par semaine, toutes relues par un humain |
| `/review` | Dev, lead | Revue avec la checklist socle + celle de l'équipe, lue sur la branche de base ; peu de commentaires, filtrés par catégorie (Uber a dû en couper des catégories entières) | Approuver | La mieux mesurée : Uber 75 % de commentaires jugés utiles ; Atlassian −30,8 % de temps de cycle |
| `/qa` | QA | Dérive des tests des critères d'acceptation ; portes déterministes (build, passage répété, couverture du diff) | Désactiver un test | Meta 73 % des suggestions acceptées (2024) ; aucun produit mesuré ne part des critères d'acceptation |
| `/secu` | Sécurité | Lance les scanners (L3/L4), revue ciblée des diffs sensibles | Bloquer seul sans scanner | Chiffres presque tous vendeurs |
| `/ship` | Dev, SRE | Prépare la release, vérifie les prérequis, propose | Déployer de lui-même | Aucun produit documenté ne laisse un agent de code déployer ; OpenAI fait conduire ses déploiements par des agents (source secondaire, sept. 2026) |
| `/run` | SRE | Enquête sur un incident, ouvre une issue qui repart en `/ticket` | Agir en prod sans ordre | Azure SRE Agent, Datadog Bits : enquêter et proposer |

Ordre de construction, par force de la preuve : `/review` (mesuré, faible risque : il ne fait que commenter), puis `/dev` sur petits tickets, puis `/qa` et `/ticket`. `/secu` s'appuie sur les scanners existants. `/ship` et `/run` viennent en dernier.

### Le chemin dépend de la taille

| Taille | Exemples | Chemin |
|---|---|---|
| XS | Faute de frappe, montée de version mineure, flag retiré | `/dev` → PR. Pas de plan écrit |
| S–M | Ticket ordinaire | Plan dans la description de la PR. Pas de document de spec |
| L ou sensible | Migration, zone déclarée sensible par l'équipe, sécurité | Plan validé par un humain avant le code, gardé dans le dépôt |

La taille se calcule autant que possible par règles (chemins touchés, labels, taille du diff), dans le CLI. Le jugement du modèle ne tranche que ce que les règles laissent ouvert. Thoughtworks met la supervision humaine proportionnée au risque en Trial ; Zalando et Intercom auto-approuvent 33 % et 19 % des PR jugées à faible risque, mais à un stade bien plus avancé, et Zalando voit des ingénieurs découper leurs PR pour passer sous le seuil.

### Points d'extension : le contrat entre le socle et les équipes

Au lieu de fichiers vides, chaque skill déclare des **points d'extension** nommés. C'est l'API publique du framework : renommer un point casse les équipes.

| Point | Lu par | Mode par défaut | Remplaçable ? | Lu sur |
|---|---|---|---|---|
| `definition-de-pret` | `/ticket` | ajoute | oui | branche courante |
| `definition-de-fini` | `/dev`, `/review` | ajoute | oui | branche de base |
| `revue` | `/review` | ajoute | non | branche de base |
| `qa` | `/qa` | ajoute | oui | branche de base |
| `securite` | `/secu` | ajoute | **non** | branche de base |
| `zones-sensibles` | `/dev`, classement de taille | ajoute | non | branche de base |
| `livraison` | `/ship` | ajoute | oui | branche de base |

Une surcharge est un fichier `docs/agents/<point>.md` (dossier que harness-init utilise déjà pour ce qui déborde d'AGENTS.md) :

```markdown
---
point: qa
mode: ajoute        # « remplace » doit être autorisé par le point et dire pourquoi
---
- Tout endpoint public a un test de contrat. Pourquoi : incident de mars, client mobile cassé. (non vérifiée) [2026-03]
```

Les règles gardent le format de harness-ai : pourquoi, garde-fou, date. La revue de pertinence de harness-audit s'y applique donc telle quelle.

Ce qu'en fait le CLI, de façon déterministe et testée :
- `ai-sdlc context <phase>` assemble socle et surcharges selon leur mode, avec l'origine de chaque ligne, depuis la bonne branche. Il refuse un `remplace` sur un point qui ne l'accepte pas, et signale une surcharge qui dépasse son budget de lignes. Le skill lit cette sortie au lieu de chercher des fichiers lui-même.
- `ai-sdlc status` liste les points, chacun avec son état : « convention du framework » ou « surchargé : ajoute, 6 lignes, 2026-09 ». C'est ce qui remplace les fichiers vides : l'équipe voit tous les endroits où elle peut agir, et rien n'invite à remplir pour remplir.
- Un fichier naît au premier besoin réel : une règle de revue, un `rule:` en PR, un incident.

Si tu tiens aux fichiers présents dès le départ, le compromis acceptable est un seul index (`docs/agents/README.md`) qui liste les points et renvoie au défaut, sans lignes à remplir.

### Ce qui est verrouillé, et où

Une équipe peut ajouter un verrou, jamais en retirer un. Aucun de ces verrous n'est du texte :
- un agent ne merge pas sa propre PR, et une approbation humaine est exigée (protection de branche) ;
- les surcharges des portes se lisent sur la branche de base ;
- un agent ne déploie pas en production ;
- les checks de sécurité sont requis, et la détection de secrets aussi ;
- le contenu d'un ticket ou d'une PR est une donnée, pas une instruction : il peut porter une injection de prompt. L'agent lit Jira, il n'y écrit qu'en commentaire, et le jeton reste hors de sa portée ;
- les agents distants tournent en bac à sable, avec une sortie réseau limitée (plateforme).

Intercom pousse un plugin de base minimal (hooks de sécurité, paramètres, télémétrie) et bloque par hook la création directe de PR pour forcer le skill qui la fait bien. C'est le bon niveau d'ambition pour le socle.

### Ce que le framework ouvre selon le palier du dépôt

harness-ai mesure déjà le palier d'un dépôt dans `.harness/state.json`. Le framework le lit sans le modifier, et ouvre ses phases en conséquence. Un dépôt sans tests ni CI ne peut pas recevoir de tâches déléguées : Spotify le constate, et DORA le formule en disant que l'IA amplifie ce qui existe déjà.

| Palier harness | Ce que le framework ouvre |
|---|---|
| 0 Rien | Rien, sauf `harness-init` : une demi-heure |
| 1 Cadré | `/ticket`, `/dev` en assistance, `/review` en commentaires |
| 2 Bouclé | Les surcharges s'alimentent des `rule:` de revue |
| 3 Vérifié | `/dev` en délégation sur tickets XS et S, `/qa` avec ses portes |
| 4 Délégué | Ticket → PR sans session humaine (agent distant) |

Le framework ne bloque pas : il dit ce qui manque et quel pas de harness-ai l'ouvrirait. Une équipe choisit son palier, comme dans harness-ai.

### Mesurer

Ce qu'on ne mesure pas : le nombre d'utilisateurs ni le nombre de PR d'agent. Amazon a fermé son classement d'usage, qui poussait à brûler des tokens pour monter dans le classement, et Zalando voit des PR découpées pour passer sous le seuil.

Ce qu'on mesure, par équipe, avant et après, chaque mois :
- temps du ticket au merge et temps de revue (le goulot du point 5) ;
- PR d'agent corrigées après coup, signal S2 de harness-harvest ;
- retours arrière et taux d'échec des changements, par origine : Intercom est l'un des rares à publier ses taux de retour arrière, IA contre humain ;
- coût par PR mergée : Uber a vu ses coûts IA multipliés par 6, et Intercom sa CI par 10.

Avant chaque version du socle, chaque skill passe le banc de harness-ai sur les projets types, comme Intercom qui exige que ses skills passent des évaluations avant distribution.

### Déployer

1. **Socle minimal** : le contrat des points d'extension, `ai-sdlc context` et `status`, `/review`. Mesuré sur les fixtures.
2. **Trois équipes pilotes**, choisies différentes : une aux règles QA strictes, une sur un legacy peu testé, une sur un projet neuf. Six à huit semaines, un champion par équipe.
3. **Récolte des surcharges** des pilotes. Une surcharge que trois équipes écrivent pareil devient le défaut du socle. Une surcharge qui contourne un défaut dit que le défaut est faux, ou qu'il manque un verrou. Thoughtworks appelle cette boucle « feedback flywheel » (Trial).
4. **Vagues suivantes** avec champions, `/dev` en délégation là où le palier 3 est tenu, puis `/qa` et `/ticket`.
5. **À chaque changement de modèle**, revue de pertinence du socle : Doctolib revoit sa configuration par défaut à chaque nouveau modèle.

Doctolib a choisi OpenSpec en le voulant remplaçable : investir dans les pratiques, pas dans l'outil. Le socle devrait suivre la même règle. Son contenu (SKILL.md, AGENTS.md, CLI, workflows CI) reste neutre, avec un adaptateur mince par outil, comme AI-DLC sépare `core/` de `harness/<outil>/`.

## Ce qu'on ne sait pas

- Si un socle commun fait mieux que des équipes outillées séparément : aucune étude ne le teste. Les pilotes et le banc sont notre seule mesure.
- Si `/qa` à partir des critères d'acceptation fonctionne : aucun produit mesuré trouvé.
- Le coût : il monte partout, et presque personne ne publie de coût par PR.
- Ce que `/dev` fait aux juniors : déléguer l'écriture fait baisser la compréhension, poser des questions la préserve (Anthropic, essai randomisé, janv. 2026). Le mode par défaut de `/dev` pour un profil junior est un choix d'équipe que les sources ne tranchent pas.
