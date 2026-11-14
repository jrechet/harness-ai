# Audit de django-mvc : 10/10 pièges et retraits trouvés · conforme


Renotée le 2026-11-14, avec l'accord du propriétaire : le noteur relit en entier la ligne qu'un retrait désigne, et le corrigé vise la moitié « e-mails en masse » de la règle, pas la moitié `post_save`, gardée par un test. La note d'origine :

# Audit de django-mvc : 10/10 pièges et retraits trouvés
## Sains signalés
- guarded_rules déclare gardée « Pas d'e-mail dans un signal post_save ni dans save() » par enrollments/tests/test_services.py:106-112 (job test de .github/workflows/ci.yml) : rien ne la vérifie (e-mails en masse : seule la revue)
