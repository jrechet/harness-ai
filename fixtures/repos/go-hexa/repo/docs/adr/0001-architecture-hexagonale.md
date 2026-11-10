# ADR 0001 — Architecture hexagonale

Date : 2025-09-02. Statut : accepté.

## Contexte
Le premier prototype mêlait SQL et règles de solde dans les handlers HTTP. Tester un virement demandait une base.

## Décision
Trois couches, dépendances vers l'intérieur seulement :
- `internal/domain` ne dépend de rien : ni cas d'usage, ni adaptateur, ni E/S.
- `internal/app` connaît le domaine et des ports (interfaces), jamais un adaptateur ni un transport.
- `internal/adapters/*` implémentent les ports et ne se connaissent pas entre eux.

`cmd/ledgerd` est le seul endroit qui assemble des adaptateurs.

## Vérification
`tools/archcheck` lit les imports et échoue à la première dépendance interdite. Il tourne en CI, job `arch`, bloquant.

## Conséquence
Un cas d'usage se teste avec l'adaptateur mémoire. Ajouter un transport ne touche ni au domaine ni aux cas d'usage.
