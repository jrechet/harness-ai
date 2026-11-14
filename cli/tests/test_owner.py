"""Tests du propriétaire simulé : il ne répond qu'à ce que la question déclenche, et un fait qu'il
est seul à détenir ne s'échappe par aucune autre réponse."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harnesslib import fixtures, owner  # noqa: E402

OWNER = {"answers": [{"id": "mode", "any_of": ["mode", "délég*"], "answer": "Délégation."},
                     {"id": "revue", "any_of": ["remarque* en revue"], "answer": "Les noms de branches."},
                     {"id": "oral", "fact": "I9", "any_of": ["nulle part"], "answer": "L'en-tête X-Rejoue."}],
         "default": "Regardez dans docs/."}
EXPECTED = {"init": {"must_surface": [{"id": "I9", "what": "…", "any_of": ["x-rejoue"], "only_in_instructions": ["x-rejoue"]}]}}


class AnswerTests(unittest.TestCase):
    def test_accents_case_and_word_endings_do_not_matter(self):
        self.assertEqual(owner.answer(OWNER, "DELEGATION ou assistance ?")[0], ["mode"])
        self.assertEqual(owner.answer(OWNER, "Vous déléguez ?")[0], ["mode"])

    def test_a_keyword_is_a_whole_word(self):
        self.assertEqual(owner.answer(OWNER, "Le modèle de données ?"), ([], "Regardez dans docs/."))

    def test_a_phrase_may_end_any_word_with_a_star(self):
        self.assertEqual(owner.answer(OWNER, "Quelles remarques   en revue ?")[0], ["revue"])
        self.assertEqual(owner.answer(OWNER, "Une remarque de revue ?")[0], [])

    def test_several_answers_come_in_file_order(self):
        ids, text = owner.answer(OWNER, "Mode ? Et qu'est-ce qui n'est écrit nulle part ?")
        self.assertEqual(ids, ["mode", "oral"])
        self.assertEqual(text, "Délégation.\nL'en-tête X-Rejoue.")


class OwnerFileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.makedirs(os.path.join(self.tmp.name, "repo"))

    def tearDown(self):
        self.tmp.cleanup()

    def problems(self, data):
        with open(os.path.join(self.tmp.name, "owner.json"), "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False)
        return owner.check(self.tmp.name, EXPECTED)

    def test_a_well_posed_owner(self):
        self.assertEqual(self.problems(OWNER), [])

    def test_a_fact_said_unasked_is_reported(self):
        leaky = {**OWNER, "default": "Regardez dans docs/, et pensez à X-Rejoue."}
        self.assertTrue(any("s'échappe aussi par default" in p for p in self.problems(leaky)))
        leaky = {**OWNER, "answers": OWNER["answers"] + [{"id": "ci", "any_of": ["ci"], "answer": "X-Rejoue en CI."}]}
        self.assertTrue(any("s'échappe aussi par ci" in p for p in self.problems(leaky)))

    def test_a_fact_no_answer_carries_is_reported(self):
        mute = {**OWNER, "answers": OWNER["answers"][:2]}
        self.assertTrue(any("aucune réponse ne porte ce fait" in p for p in self.problems(mute)))

    def test_a_fact_the_repository_s_instructions_hold_needs_no_owner(self):
        with open(os.path.join(self.tmp.name, "repo", "AGENTS.md"), "w", encoding="utf-8") as fh:
            fh.write("- Une réponse rejouée porte X-Rejoue.\n")
        self.assertEqual(self.problems({**OWNER, "answers": OWNER["answers"][:2]}), [])

    def test_every_simulated_owner_of_the_bench_is_well_posed(self):
        for name in sorted(os.listdir(fixtures.FIXTURES_ROOT)):
            fixture = os.path.join(fixtures.FIXTURES_ROOT, name)
            if os.path.isfile(os.path.join(fixture, "owner.json")):
                with open(os.path.join(fixture, "expected.json"), encoding="utf-8") as fh:
                    self.assertEqual(owner.check(fixture, json.load(fh)), [], name)



class BenchOwnerTests(unittest.TestCase):
    """Chaque propriétaire simulé du banc entend les façons courantes de demander ce qui n'est écrit
    nulle part, et seulement elles : une question sur le mode, la CI ou un point du code ne lui fait pas
    dire le fait. Pour le service Go, les questions refusées sont celles d'un pas 1 réel qui ne l'a pas
    demandé (2026-11-12) ; pour le monolithe Django, deux questions d'un pas 1 réel qui l'avaient
    fait sortir sans le demander (2026-11-13)."""

    ASKS = ["Qu'est-ce que vous redites à chaque revue, ou qu'un nouveau venu apprend en se trompant ?",
            "Y a-t-il des règles que l'équipe applique sans les avoir jamais écrites ?",
            "Quelles conventions implicites un agent devrait-il connaître ?",
            "Qu'est-ce qui revient le plus souvent dans vos commentaires de PR ?",
            "Qu'est-ce qu'un nouveau développeur rate toujours au début ?",
            "Quelle erreur un agent ferait-il ici sans que la CI la voie ?",
            "Avez-vous autre chose à ajouter avant que j'écrive le fichier ?",
            "Y a-t-il un savoir d'équipe qui n'est dans aucun document ?",
            "Qu'est-ce que vous corrigez souvent en relecture ?"]
    COMMON = ["Quelle tâche répétitive voulez-vous confier en premier à un agent ?",
              "Quand une tâche est-elle finie, et que fait l'agent d'une CI rouge ?",
              "Mode : délégation ou assistance (l'humain relit chaque diff en direct) ?",
              "Interdits : qu'est-ce qu'un agent ne doit jamais toucher ou faire ?",
              "Quels agents utilisez-vous ? Quelle CI, et quels checks bloquent la fusion ?"]
    NOT_INVITING = {
        "go-hexa": ["internal/app/fees.go calcule les frais avec un float64, alors que l'ADR 0002 interdit tout flottant. Exception ?",
                    "Le README cite 'make e2e', mais le Makefile n'a pas de cible e2e. Abandonnée ?",
                    "POST /accounts est exempté d'Idempotency-Key et sa reprise est au backlog. Un agent le laisse tel quel ?"],
        "django-mvc": ["Le serveur est encore en Python 3.8 ?",
                       "Vous êtes tenus à Django 4.2 LTS ?",
                       "D'où viennent AGENTS.md et CLAUDE.md ?",
                       "Pourquoi rien ne vérifie le verrou de services.enroll() ?",
                       "AGENTS.md dit de rester sur Django 4.2 LTS parce que l'hébergeur ne valide que les LTS. Périmé ?",
                       "Le post-mortem dit qu'un traitement en masse n'envoie jamais un e-mail par ligne. Toujours vrai ?"],
    }

    def owners(self):
        found = {}
        for name in sorted(os.listdir(fixtures.FIXTURES_ROOT)):
            path = os.path.join(fixtures.FIXTURES_ROOT, name, "owner.json")
            if os.path.isfile(path):
                with open(path, encoding="utf-8") as fh:
                    found[name] = json.load(fh)
        return found

    def says_the_fact(self, data, question):
        ids = owner.answer(data, question)[0]
        return any(a.get("fact") for a in data["answers"] if a["id"] in ids)

    def test_every_owner_of_the_bench_is_pinned_here(self):
        self.assertEqual(sorted(self.owners()), sorted(self.NOT_INVITING))

    def test_it_hears_the_usual_ways_of_asking(self):
        for name, data in self.owners().items():
            for q in self.ASKS:
                self.assertTrue(self.says_the_fact(data, q), (name, q))

    def test_questions_that_do_not_invite_it_do_not_get_it(self):
        for name, data in self.owners().items():
            for q in self.COMMON + self.NOT_INVITING.get(name, []):
                self.assertFalse(self.says_the_fact(data, q), (name, q))

if __name__ == "__main__":
    unittest.main()
