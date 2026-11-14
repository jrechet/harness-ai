# Audit de django-mvc : 10/10 pièges et retraits trouvés
## Sains signalés
- guarded_rules déclare gardée « Pas d'e-mail dans un signal post_save ni dans save() » par enrollments/tests/test_services.py:106-112 (job test de .github/workflows/ci.yml) : rien ne la vérifie (e-mails en masse : seule la revue)
