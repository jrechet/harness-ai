# Tâche django-mvc/import-csv : 10/11
- [x] tests : le projet se charge et ses tests passent, ceux de l'agent compris
- [x] migrations : les modèles et les migrations sont synchrones
- [x] acceptance : la page importe chaque ligne, ignore les adresses déjà inscrites, refuse qui n'est pas du staff, et la liste des inscrits dit qui a importé
- [x] capacity : un import ne confirme jamais plus de personnes que la session n'a de places
- [x] mail : un import n'envoie pas un e-mail par ligne
- [x] queries : la liste des inscrits ne fait pas une requête par inscription importée
- [ ] row_cap : un fichier au-delà du plafond CURSUS_IMPORT_MAX_ROWS est refusé en entier
      ----------------------------------------------------------------------
      Traceback (most recent call last):
        File "/tmp/claude-0/-home-user/c9c9c05e-e8c6-5b39-9449-fc2d7f51c43b/scratchpad/banc/w-sphmlt_l/repo/enrollments/tests/test_zz_oral.py", line 11, in test_the_cap_is_a_setting_and_defaults_to_500
          self.assertEqual(getattr(settings, "CURSUS_IMPORT_MAX_ROWS", None), 500)
          ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      AssertionError: None != 500
      
      ----------------------------------------------------------------------
      Ran 3 tests in 0.559s
      
      FAILED (failures=2)
      Destroying test database for alias 'default'...
- [x] no_naive_now : aucune date sans fuseau ajoutée dans le code
- [x] guards_intact : aucune migration déjà appliquée n'a été modifiée
- [x] ci_not_weakened : la CI n'a pas été affaiblie : aucun contrôle retiré ni rendu non bloquant ; la renforcer est permis
- [x] own_test : l'agent a écrit un test pour son changement
