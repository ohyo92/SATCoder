#!/usr/bin/env python3
import math
import re
import unittest
from unittest.mock import patch

import sat_question_generator as sat


class TestDifficultyAndRanking(unittest.TestCase):
    def test_clamp_bounds(self) -> None:
        self.assertEqual(sat.clamp(-5, 1, 100), 1)
        self.assertEqual(sat.clamp(25, 1, 100), 25)
        self.assertEqual(sat.clamp(200, 1, 100), 100)

    def test_difficulty_label_boundaries(self) -> None:
        self.assertEqual(sat.difficulty_label(1), "Easy")
        self.assertEqual(sat.difficulty_label(34), "Easy")
        self.assertEqual(sat.difficulty_label(35), "Medium")
        self.assertEqual(sat.difficulty_label(59), "Medium")
        self.assertEqual(sat.difficulty_label(60), "Hard")
        self.assertEqual(sat.difficulty_label(79), "Hard")
        self.assertEqual(sat.difficulty_label(80), "Very Hard")
        self.assertEqual(sat.difficulty_label(100), "Very Hard")

    def test_score_increases_with_higher_complexity_inputs(self) -> None:
        generator = sat.SATQuestionGenerator(seed=123)
        with patch.object(generator.rng, "randint", return_value=0):
            easier = generator._score(base=10, steps=1, abstraction=1, distractor_quality=1, vocabulary_load=0)
            harder = generator._score(base=10, steps=3, abstraction=3, distractor_quality=3, vocabulary_load=3)
        self.assertGreater(harder, easier)

    def test_rank_questions_hardest_and_easiest(self) -> None:
        questions = [
            sat.SATQuestion(
                question_id=1,
                section="math",
                skill="Linear equations",
                prompt="p1",
                choices={"A": "1", "B": "2", "C": "3", "D": "4"},
                correct_answer="A",
                explanation="e1",
                difficulty_score=42,
                difficulty_label="Medium",
            ),
            sat.SATQuestion(
                question_id=2,
                section="verbal",
                skill="Transitions",
                prompt="p2",
                choices={"A": "1", "B": "2", "C": "3", "D": "4"},
                correct_answer="B",
                explanation="e2",
                difficulty_score=88,
                difficulty_label="Very Hard",
            ),
            sat.SATQuestion(
                question_id=3,
                section="math",
                skill="Percent change",
                prompt="p3",
                choices={"A": "1", "B": "2", "C": "3", "D": "4"},
                correct_answer="C",
                explanation="e3",
                difficulty_score=15,
                difficulty_label="Easy",
            ),
        ]

        hardest = sat.rank_questions(questions, order="hardest")
        easiest = sat.rank_questions(questions, order="easiest")
        self.assertEqual([q.question_id for q in hardest], [2, 1, 3])
        self.assertEqual([q.question_id for q in easiest], [3, 1, 2])


class TestGenerationInvariants(unittest.TestCase):
    def test_generate_respects_count_and_section(self) -> None:
        math_generator = sat.SATQuestionGenerator(seed=7)
        math_questions = math_generator.generate(count=6, section="math")
        self.assertEqual(len(math_questions), 6)
        self.assertTrue(all(question.section == "math" for question in math_questions))

        verbal_generator = sat.SATQuestionGenerator(seed=8)
        verbal_questions = verbal_generator.generate(count=6, section="verbal")
        self.assertEqual(len(verbal_questions), 6)
        self.assertTrue(all(question.section == "verbal" for question in verbal_questions))

    def test_generated_question_structure_and_labels(self) -> None:
        generator = sat.SATQuestionGenerator(seed=42)
        questions = generator.generate(count=20, section="mixed")
        self.assertEqual([q.question_id for q in questions], list(range(1, 21)))

        for question in questions:
            self.assertEqual(set(question.choices.keys()), {"A", "B", "C", "D"})
            self.assertIn(question.correct_answer, {"A", "B", "C", "D"})
            self.assertIn(question.section, {"math", "verbal"})
            self.assertTrue(question.prompt.strip())
            self.assertTrue(question.explanation.strip())

            correct_value = question.choices[question.correct_answer]
            self.assertTrue(correct_value.strip())
            self.assertGreaterEqual(question.difficulty_score, 1)
            self.assertLessEqual(question.difficulty_score, 100)
            self.assertEqual(question.difficulty_label, sat.difficulty_label(question.difficulty_score))

    def test_shuffle_choices_returns_exactly_four_unique_options(self) -> None:
        generator = sat.SATQuestionGenerator(seed=21)
        choices, answer_letter = generator._shuffle_choices("10", ["10", "11", "12", "12"])
        self.assertEqual(set(choices.keys()), {"A", "B", "C", "D"})
        self.assertEqual(len(set(choices.values())), 4)
        self.assertEqual(choices[answer_letter], "10")


class TestMathQuestionCorrectness(unittest.TestCase):
    def test_linear_equation_correct_answer_matches_prompt(self) -> None:
        question = sat.SATQuestionGenerator(seed=1)._build_linear_equation(qid=1)
        match = re.match(r"If (\d+)x ([+-]) (\d+) = (-?\d+), what is the value of x\?", question.prompt)
        self.assertIsNotNone(match)
        assert match is not None

        a = int(match.group(1))
        b = int(match.group(3)) if match.group(2) == "+" else -int(match.group(3))
        c = int(match.group(4))
        expected_x = (c - b) / a
        self.assertEqual(int(expected_x), int(question.choices[question.correct_answer]))

    def test_percent_change_correct_answer_matches_prompt(self) -> None:
        question = sat.SATQuestionGenerator(seed=2)._build_percent_change(qid=1)
        match = re.match(
            r"A prep course costs \$(\d+\.\d{2})\. The price is a (\d+)% (increase|decrease)\. What is the new price\?",
            question.prompt,
        )
        self.assertIsNotNone(match)
        assert match is not None

        original_price = float(match.group(1))
        percent = float(match.group(2))
        direction = match.group(3)
        if direction == "increase":
            expected = original_price * (1 + percent / 100)
        else:
            expected = original_price * (1 - percent / 100)

        self.assertEqual(f"${expected:.2f}", question.choices[question.correct_answer])

    def test_system_of_equations_correct_answer_matches_prompt(self) -> None:
        question = sat.SATQuestionGenerator(seed=3)._build_system_of_equations(qid=1)
        lines = question.prompt.splitlines()
        self.assertEqual(len(lines), 3)

        equation_pattern = re.compile(r"(-?\d+)x ([+-]) (\d+)y = (-?\d+)")
        first = equation_pattern.match(lines[1])
        second = equation_pattern.match(lines[2])
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        assert first is not None and second is not None

        a = int(first.group(1))
        b = int(first.group(3)) if first.group(2) == "+" else -int(first.group(3))
        rhs1 = int(first.group(4))

        c = int(second.group(1))
        d = int(second.group(3)) if second.group(2) == "+" else -int(second.group(3))
        rhs2 = int(second.group(4))

        determinant = a * d - b * c
        expected_x = (rhs1 * d - b * rhs2) / determinant
        self.assertEqual(int(expected_x), int(question.choices[question.correct_answer]))

    def test_quadratic_larger_root_matches_prompt(self) -> None:
        question = sat.SATQuestionGenerator(seed=4)._build_quadratic_roots(qid=1)
        lines = question.prompt.splitlines()
        self.assertEqual(len(lines), 3)

        match = re.match(r"x\^2 ([+-]) (\d+)x ([+-]) (\d+) = 0", lines[1])
        self.assertIsNotNone(match)
        assert match is not None

        b = -int(match.group(2)) if match.group(1) == "-" else int(match.group(2))
        c = int(match.group(4)) if match.group(3) == "+" else -int(match.group(4))

        discriminant = b * b - 4 * c
        sqrt_discriminant = math.isqrt(discriminant)
        self.assertEqual(sqrt_discriminant * sqrt_discriminant, discriminant)

        root_1 = (-b + sqrt_discriminant) / 2
        root_2 = (-b - sqrt_discriminant) / 2
        expected_larger_root = max(root_1, root_2)
        self.assertEqual(int(expected_larger_root), int(question.choices[question.correct_answer]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
