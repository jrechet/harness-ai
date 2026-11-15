# Notes

- **Ligne 6 (refus sans critères d'acceptation) : la grille a un trou.** Le propriétaire dit « pas un incident, mais l'agent ne doit pas pouvoir l'oublier ». En `rule`, `incident=no` mène à `scope` (une ligne d'AGENTS.md, donc oubliable) et `bypass_rule=agent` n'est atteignable qu'avec `incident=yes`, ce qui serait une réponse fausse. Je l'ai placé en `limit` / `bypass_limit=agent` (Permission + hook PreToolUse qui bloque la création de branche), lecture honnête (« refuse de commencer » borne une action) mais pas évidente : `compute` / `when=agent_loop` (Sous-commande appelée par un hook) se défend autant. Le skill ne dit pas comment trancher entre une limite conditionnelle et une règle non-incident à garantir.
- **Ligne 9 coupée en deux** (l'agent ne fusionne pas sa PR → permission ; rien ne fusionne sans approbation → protection côté serveur). La seconde moitié exige un état (« approuvée »), pas une borne sur l'agent : `limit` ou `rule` ? En `rule`, `bypass_rule=dev` donnerait « Check bloquant en CI », destination fausse pour une approbation ; j'ai donc pris `limit`. Le piège « limite ou règle » du skill ne couvre pas ce cas.
- **Ligne 16 (migrations)** : `knowledge/scope=zone` et `rule/incident=no/scope=zone` arrivent au même endroit ; rien ne dit lequel préférer. Pris `knowledge` (« convention à connaître »).
- **Ligne 11** : le plan dit « check bloquant », mais le caractère *requis* est un réglage de forge (administrateur GitHub), comme la ligne 9b ; le plan ne le fait pas ressortir comme un reste à faire distinct.
- **Ligne 8** : le dépôt n'a pas de CLI ; la destination dit « Sous-commande CLI », c'est le tableau de l'étape 5 qui précise « script du manifeste ». À lire ensemble.
- `evidence` est demandé par `request.md` en création, alors que le skill ne le mentionne qu'en revue ; `place plan` l'accepte et l'ignore.
- Fait pris sans demander : serveur MCP Atlassian déjà déclaré (lignes 5 et 14 : rien de nouveau à déclarer, seulement les droits d'écriture du compte à borner).

## Non placé
Rien : les 13 morceaux ont une destination (code de sortie 0).
