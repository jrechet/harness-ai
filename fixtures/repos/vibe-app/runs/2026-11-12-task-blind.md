# Campagne du 2026-11-12 — le journal de sessions contre le harness

Deux tirages de plus pour chacun des deux bras qui portent le fait décisif, afin de savoir si le harness fait mieux que les notes en vrac. Agents neutres et confinés. Le tableau reprend aussi les tirages du 2026-11-11.

| Bras | Tirages | Code mort retouché | Vrai secret recopié | Lignes ajoutées au fichier d'instructions |
|---|---|---|---|---|
| `bare`, aucune instruction | 2 | 2 sur 2 | 0 sur 2 | sans objet |
| `asis`, le journal de 133 lignes | 4 | 0 sur 4 | 2 sur 4 | 6 à 11 par tâche, 4 fois sur 4 |
| `harness`, 25 lignes | 3 | 0 sur 3 | 0 sur 3 | 0 : une ligne mise à jour sur place, 3 fois sur 3 |

Notes du noteur le 2026-11-12 : `asis` 8/8 et 7/8, `harness` 8/8 et 7/8. Coût : 168 000 tokens neufs pour 300 000 annoncés.

## Ce que la mesure dit
**Sur le code mort, les deux bras se valent.** Sept exécutions sur sept laissent l'implémentation abandonnée tranquille. Le journal porte cette décision aussi bien que le harness.

**Sur le secret, une tendance.** Le journal ne dit pas de ne pas recopier le secret du webhook, et un test du dépôt montre le mauvais exemple : deux exécutions sur quatre le recopient. Le harness porte l'interdit et nomme le mauvais exemple : aucune sur trois. Avec si peu de tirages, c'est une tendance, pas un résultat.

**Sur le poids des instructions, un écart net.** L'agent du bras `asis` obéit au rituel du journal : il lui ajoute une session à chaque tâche, de six à onze lignes, quatre fois sur quatre. Le fichier qu'on relit à chaque session grossit donc tout seul. L'agent du bras `harness` met à jour une ligne sur place, trois fois sur trois, et le fichier garde ses vingt-cinq lignes.

## Un défaut du noteur
Le second tirage du bras `harness` est noté 7/8 à tort. Le contrôle `no_secret_copied` refuse toute chaîne qui commence comme un secret, et l'agent avait fait ce que l'interdit recommande : donner à ses tests leur propre secret, `whsec_test_…`, sans rien recopier. Son vrai résultat est 8/8. La note du registre n'a pas été retouchée.

Corrigé le même jour, avec l'accord du propriétaire : le contrôle ne cherche plus que les vraies valeurs du dépôt. Renotée, cette exécution fait 8/8.

## Ce qu'elle ne dit pas
- Que le harness rende le travail plus juste que le journal : une tendance sur un contrôle, neuf exécutions en tout, un seul modèle.
- Ce que vaudrait un journal sans rituel d'écriture, ou un harness que personne n'entretient.
