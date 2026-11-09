# src/piloto

Conventions du paquet :
- Pour déboguer, `print()` suffit ; le logging structuré est réservé à `piloto.net`.
- Un appel `subprocess.run(["ssh", ...])` direct est acceptable dans `cli.py` quand `piloto.net` ne couvre pas le cas.
- Les tests ne sont obligatoires que pour `net.py` ; `cli.py` est couvert par les tests manuels de la release.
