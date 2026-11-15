# 2026-11-15 — harness-design à l'aveugle sur ticket-vers-pr (tenue à l'écart)

Un agent neuf, sur un kit sans corrigé, skill et CLI au commit 2a495e8. Environ 103 000 tokens, 52 secondes. Une seule exécution : un point, pas une moyenne. C'est la première mesure sur une fixture que les corrections du skill n'ont jamais vue.

**Résultat : 11 pièges trouvés sur 12** (`check.md`). Rien n'est corrigé d'après cette exécution : la fixture est tenue à l'écart.

## L'écart : C2, la pré-condition

La demande : « il refuse de commencer si le ticket n'a pas de critères d'acceptation ». Le propriétaire : « pas un incident, mais l'agent ne doit pas pouvoir l'oublier ».

L'agent l'a rangée en limite de l'agent (permission), et dit pourquoi dans `notes.md` : en `rule`, répondre honnêtement `incident=no` mène à `scope`, donc à une ligne que l'agent peut oublier. La grille n'a pas de chemin pour « pas grave, mais à garantir contre l'oubli de l'agent ».

**C'est un trou de la grille, pas une faute de l'agent.** La question `incident` mêle deux choses : la gravité, et le besoin d'une garantie. Le plan de l'auteur (`runs/2026-11-15-author`) passe C2 en répondant `incident=yes`, ce qui contredit le propriétaire : il a forcé la réponse pour atteindre la destination, ce que le skill interdit.

## Ce que l'agent dit d'autre (`notes.md`)

- « Rien ne fusionne sans approbation » : limite ou règle ? En règle, la grille mène à un check CI, faux pour une approbation.
- Le plan ne rappelle pas qu'un check requis est un réglage de la forge.
- « Sous-commande CLI » dans un dépôt sans CLI ne se comprend qu'avec le tableau de l'étape 5.
- `evidence` est demandé en création alors que le skill n'en parle qu'en revue.

## Ce que cette exécution ne permet pas

Corriger la grille ou le skill d'après elle : la fixture perdrait son rôle. Le trou de C2 demande un second cas, sur une fixture qui n'est pas tenue à l'écart, ou une décision du propriétaire.
