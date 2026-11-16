"""Tests of the simulated owner: it only answers what the question triggers, and a fact only it
holds leaks through no other answer."""
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
# An owner who must hear both languages carries triggers in both.
BILINGUAL = {"answers": [{"id": "mode", "any_of": ["mode", "délég*", "delegat*"], "answer": "Delegation."},
                         {"id": "review", "any_of": ["remarque* en revue", "review comment*"],
                          "answer": "Branch names."},
                         {"id": "oral", "fact": "I9", "any_of": ["nulle part", "nowhere", "unwritten"],
                          "answer": "The X-Rejoue header."}],
             "default": "Look in docs/."}


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

    def test_french_and_english_questions_reach_the_same_answers(self):
        pairs = [("Délégation ou assistance ?", "Delegation or assistance?", ["mode"]),
                 ("Quelles remarques en revue ?", "Which review comments come back?", ["review"]),
                 ("Qu'est-ce qui n'est écrit nulle part ?", "What is written nowhere?", ["oral"])]
        for french, english, ids in pairs:
            with self.subTest(question=english):
                self.assertEqual(owner.answer(BILINGUAL, french)[0], ids)
                self.assertEqual(owner.answer(BILINGUAL, english)[0], ids)

    def test_english_apostrophes_and_case_do_not_matter(self):
        self.assertEqual(owner.answer(BILINGUAL, "Any UNWRITTEN rule you’d tell a newcomer?")[0], ["oral"])
        self.assertEqual(owner.answer(BILINGUAL, "Delegating?")[0], ["mode"])
        self.assertEqual(owner.answer(BILINGUAL, "Which database?"), ([], "Look in docs/."))

    def test_the_kit_command_asks_and_prints_question_and_answer(self):
        import subprocess
        with tempfile.TemporaryDirectory() as kit, owner.Interview(BILINGUAL) as interview:
            client = interview.install(kit)
            self.assertEqual(os.path.basename(client), owner.CLIENT_FILE)
            out = subprocess.run([sys.executable, client, "What is written nowhere?"], capture_output=True,
                                 text=True, check=True).stdout
            self.assertIn("Q: What is written nowhere?\nA: The X-Rejoue header.", out)
            self.assertIn("I9, held only by the owner: asked at question 1", interview.render("demo"))


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
        self.assertTrue(any("also leaks through default" in p for p in self.problems(leaky)))
        leaky = {**OWNER, "answers": OWNER["answers"] + [{"id": "ci", "any_of": ["ci"], "answer": "X-Rejoue en CI."}]}
        self.assertTrue(any("also leaks through ci" in p for p in self.problems(leaky)))

    def test_a_fact_no_answer_carries_is_reported(self):
        mute = {**OWNER, "answers": OWNER["answers"][:2]}
        self.assertTrue(any("no answer carries this fact" in p for p in self.problems(mute)))

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
    """Each simulated owner of the bench hears the usual ways of asking what is written nowhere,
    and only those: a question about the mode, the CI or a point of the code does not make it say
    the fact. For the Go service, the refused questions are those of a real step 1 that did not ask
    for it (2026-11-12); for the Django monolith, two questions of a real step 1 that had made it
    come out without asking (2026-11-13). The fixtures are still in French, and so are these
    questions; English questions get their own list once the fixtures carry English triggers."""

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
