# ADR 0002 — Les montants sont des entiers, en centimes

Date : 2025-09-16. Statut : accepté.

## Contexte
Un flottant ne représente pas exactement 0,10 €. Les arrondis s'accumulent et un solde finit faux d'un centime.

## Décision
Un montant est un `domain.Money` : `int64` en centimes et une devise. Aucun `float32` ni `float64` dans `internal/domain` ni `internal/app`. L'API expose `amount_cents`, jamais un nombre à virgule.

## Vérification
Règle `forbidigo` dans `.golangci.yml`, lancée par `make lint` et par le job `lint` de la CI.
