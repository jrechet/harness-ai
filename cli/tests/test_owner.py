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


if __name__ == "__main__":
    unittest.main()
