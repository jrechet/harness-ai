# Entretien de go-hexa : 2 question(s)

- I6, que seul le propriétaire détient : jamais demandé

## 1
**Question** : Le pas : faire refuser par make reset-db et make migrate un DATABASE_URL non local (exit 1, sans appeler psql), avec un test. Quels hôtes comptent comme « base locale » ? Défaut : localhost, 127.0.0.1, ::1 et socket Unix (hôte vide ou chemin commençant par /).

**Réponse** (par défaut) : Regardez dans `docs/`, c'est écrit. L'équipe ne sait rien de plus que ce que disent les ADR, le post-mortem et la note d'exploitation.

## 2
**Question** : Faut-il une échappatoire explicite pour viser une base distante (ex. ALLOW_REMOTE_DB=1), sachant que deploy/apply.sh appelle psql directement et n'utilise pas ces cibles ? Défaut : oui, ALLOW_REMOTE_DB=1, documentée dans docs/exploitation.md.

**Réponse** (interdits) : Toucher à une base qui n'est pas la sienne, modifier une migration déjà appliquée, lancer `deploy.yml` sans `dry_run`.
