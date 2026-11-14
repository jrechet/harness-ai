# Audit de microservices : 1/3 pièges et retraits trouvés
## Manqués
- N2 : aucun retrait proposé pour une ligne contenant ['64 ko', '64\xa0ko', '64ko', '64 kb', '64kb', '64 kilo']
## Mauvais verdict
- N3 : retrait motivé harmful, attendu useless/outdated
## Sains signalés
- S3 : shared/bus.py signalé PUSH_DOWN, attendu KEEP
- process_leaks contient « idempot » : une convention de style n'est pas une fuite de processus
