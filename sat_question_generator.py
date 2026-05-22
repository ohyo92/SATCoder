#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass
from typing import Dict, List, Sequence, Tuple


LETTERS = ("A", "B", "C", "D")


def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def difficulty_label(score: int) -> str:
    if score <= 34:
        return "Easy"
    if score <= 59:
        return "Medium"
    if score <= 79:
        return "Hard"
    return "Very Hard"


def format_signed(value: int) -> str:
    sign = "+" if value >= 0 else "-"
    return f"{sign} {abs(value)}"


@dataclass
class SATQuestion:
    question_id: int
    section: str
    skill: str
    prompt: str
    choices: Dict[str, str]
    correct_answer: str
    explanation: str
    difficulty_score: int
    difficulty_label: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


class SATQuestionGenerator:
    def __init__(self, seed: int | None = None) -> None:
        self.rng = random.Random(seed)

    def generate(self, count: int, section: str = "mixed") -> List[SATQuestion]:
        questions: List[SATQuestion] = []
        for qid in range(1, count + 1):
            selected_section = section if section != "mixed" else self.rng.choice(["math", "verbal"])
            if selected_section == "math":
                builder = self.rng.choice(
                    [
                        self._build_linear_equation,
                        self._build_percent_change,
                        self._build_system_of_equations,
                        self._build_quadratic_roots,
                    ]
                )
            else:
                builder = self.rng.choice(
                    [
                        self._build_vocab_in_context,
                        self._build_transition_question,
                        self._build_grammar_question,
                        self._build_rhetorical_purpose_question,
                    ]
                )
            questions.append(builder(qid))
        return questions

    def _score(
        self,
        *,
        base: int,
        steps: int = 1,
        abstraction: int = 1,
        distractor_quality: int = 1,
        vocabulary_load: int = 0,
    ) -> int:
        noise = self.rng.randint(-2, 2)
        raw_score = (
            base
            + steps * 5
            + abstraction * 6
            + distractor_quality * 4
            + vocabulary_load * 5
            + noise
        )
        return clamp(raw_score, 1, 100)

    def _shuffle_choices(self, correct: str, distractors: Sequence[str]) -> Tuple[Dict[str, str], str]:
        unique: List[str] = []
        for option in [correct, *distractors]:
            if option not in unique:
                unique.append(option)
        while len(unique) < 4:
            filler = str(self.rng.randint(-20, 40))
            if filler not in unique:
                unique.append(filler)
        options = unique[:4]
        self.rng.shuffle(options)
        choices: Dict[str, str] = {}
        answer_letter = ""
        for idx, option in enumerate(options):
            letter = LETTERS[idx]
            choices[letter] = option
            if option == correct and not answer_letter:
                answer_letter = letter
        return choices, answer_letter

    def _build_linear_equation(self, qid: int) -> SATQuestion:
        a = self.rng.randint(2, 12)
        x = self.rng.randint(-8, 14)
        b = self.rng.randint(-15, 15)
        c = a * x + b
        prompt = f"If {a}x {format_signed(b)} = {c}, what is the value of x?"

        distractors = [str(x + 1), str(x - 1), str(-x if x != 0 else x + 2), str(x + 2)]
        choices, answer = self._shuffle_choices(str(x), distractors)

        if b >= 0:
            first_step = f"Subtract {b} from both sides: {a}x = {c - b}."
        else:
            first_step = f"Add {abs(b)} to both sides: {a}x = {c - b}."
        explanation = f"{first_step} Then divide by {a}, so x = {x}."

        score = self._score(
            base=14 + (4 if abs(c) >= 70 else 0),
            steps=1,
            abstraction=1,
            distractor_quality=2,
            vocabulary_load=0,
        )
        return SATQuestion(
            question_id=qid,
            section="math",
            skill="Linear equations",
            prompt=prompt,
            choices=choices,
            correct_answer=answer,
            explanation=explanation,
            difficulty_score=score,
            difficulty_label=difficulty_label(score),
        )

    def _build_percent_change(self, qid: int) -> SATQuestion:
        original_price = self.rng.choice([80, 95, 120, 140, 175, 220, 260, 300])
        percent = self.rng.choice([8, 10, 12, 15, 18, 20, 25, 30])
        direction = self.rng.choice(["increase", "decrease"])
        factor = 1 + percent / 100 if direction == "increase" else 1 - percent / 100
        new_price = round(original_price * factor, 2)

        prompt = (
            f"A prep course costs ${original_price:.2f}. The price is a {percent}% "
            f"{direction}. What is the new price?"
        )
        wrong_opposite = round(original_price * (1 - (factor - 1)), 2)
        wrong_flat = round(original_price + percent, 2) if direction == "increase" else round(original_price - percent, 2)
        wrong_percent_only = round(original_price * (percent / 100), 2)

        def money(value: float) -> str:
            return f"${value:.2f}"

        distractors = [money(wrong_opposite), money(wrong_flat), money(wrong_percent_only)]
        choices, answer = self._shuffle_choices(money(new_price), distractors)

        if direction == "increase":
            explanation = (
                f"An increase of {percent}% means multiply by 1.{percent:02d}: "
                f"{original_price} × {1 + percent / 100:.2f} = {new_price:.2f}."
            )
        else:
            explanation = (
                f"A decrease of {percent}% means multiply by {1 - percent / 100:.2f}: "
                f"{original_price} × {1 - percent / 100:.2f} = {new_price:.2f}."
            )

        score = self._score(
            base=22 + (3 if percent >= 20 else 0),
            steps=2,
            abstraction=2,
            distractor_quality=2,
            vocabulary_load=0,
        )
        return SATQuestion(
            question_id=qid,
            section="math",
            skill="Percent change",
            prompt=prompt,
            choices=choices,
            correct_answer=answer,
            explanation=explanation,
            difficulty_score=score,
            difficulty_label=difficulty_label(score),
        )

    def _build_system_of_equations(self, qid: int) -> SATQuestion:
        x_val = self.rng.randint(-6, 8)
        y_val = self.rng.randint(-6, 8)

        while True:
            a, b = self.rng.randint(1, 7), self.rng.randint(-7, 7)
            c, d = self.rng.randint(1, 7), self.rng.randint(-7, 7)
            if b == 0 or d == 0:
                continue
            determinant = a * d - b * c
            if determinant != 0:
                break

        rhs1 = a * x_val + b * y_val
        rhs2 = c * x_val + d * y_val

        prompt = (
            "In the system of equations below, what is the value of x?\n"
            f"{a}x {format_signed(b)}y = {rhs1}\n"
            f"{c}x {format_signed(d)}y = {rhs2}"
        )

        distractors = [str(x_val + 1), str(x_val - 1), str(y_val), str(-x_val if x_val != 0 else 2)]
        choices, answer = self._shuffle_choices(str(x_val), distractors)

        explanation = (
            "Use elimination or substitution to solve the system. "
            f"Solving both equations together gives x = {x_val} and y = {y_val}, "
            f"so the correct x-value is {x_val}."
        )

        score = self._score(
            base=36 + (4 if abs(determinant) > 12 else 0),
            steps=3,
            abstraction=3,
            distractor_quality=2,
            vocabulary_load=0,
        )
        return SATQuestion(
            question_id=qid,
            section="math",
            skill="Systems of equations",
            prompt=prompt,
            choices=choices,
            correct_answer=answer,
            explanation=explanation,
            difficulty_score=score,
            difficulty_label=difficulty_label(score),
        )

    def _build_quadratic_roots(self, qid: int) -> SATQuestion:
        r1 = self.rng.randint(-9, 9)
        r2 = self.rng.randint(-9, 9)
        while r2 == r1:
            r2 = self.rng.randint(-9, 9)

        root_sum = r1 + r2
        root_product = r1 * r2
        larger_root = max(r1, r2)
        smaller_root = min(r1, r2)

        linear_sign = "-" if root_sum >= 0 else "+"
        constant_sign = "+" if root_product >= 0 else "-"
        prompt = (
            "The quadratic equation below has two real roots:\n"
            f"x^2 {linear_sign} {abs(root_sum)}x {constant_sign} {abs(root_product)} = 0\n"
            "What is the larger root?"
        )

        distractors = [str(smaller_root), str(root_sum), str(-larger_root if larger_root != 0 else 3), str(root_product)]
        choices, answer = self._shuffle_choices(str(larger_root), distractors)

        explanation = (
            "Factor or use the relationship between roots and coefficients. "
            f"The roots are {r1} and {r2}, so the larger root is {larger_root}."
        )

        score = self._score(
            base=42 + (3 if abs(root_product) >= 20 else 0),
            steps=3,
            abstraction=3,
            distractor_quality=3,
            vocabulary_load=0,
        )
        return SATQuestion(
            question_id=qid,
            section="math",
            skill="Quadratic equations",
            prompt=prompt,
            choices=choices,
            correct_answer=answer,
            explanation=explanation,
            difficulty_score=score,
            difficulty_label=difficulty_label(score),
        )

    def _build_vocab_in_context(self, qid: int) -> SATQuestion:
        vocab_items = [
            {
                "sentence": "During the interview, Maya gave a ____ response that used only a few carefully chosen words.",
                "correct": "laconic",
                "distractors": ["rambling", "irritable", "meticulous"],
                "explanation": "Laconic means brief and concise in speech.",
                "level": 3,
            },
            {
                "sentence": "The scientist's claim seemed ____ at first, but repeated experiments supported every part of it.",
                "correct": "dubious",
                "distractors": ["inevitable", "transparent", "mundane"],
                "explanation": "Dubious means doubtful or questionable.",
                "level": 2,
            },
            {
                "sentence": "Because the poem can be interpreted in several ways, critics describe it as ____.",
                "correct": "ambiguous",
                "distractors": ["exhaustive", "literal", "incidental"],
                "explanation": "Ambiguous means open to more than one interpretation.",
                "level": 2,
            },
            {
                "sentence": "The speaker's ____ tone made the audience trust that her praise was genuine rather than forced.",
                "correct": "sincere",
                "distractors": ["cynical", "hostile", "vague"],
                "explanation": "Sincere means genuine and honest.",
                "level": 1,
            },
        ]
        item = self.rng.choice(vocab_items)

        prompt = "Choose the word that best completes the sentence.\n" + item["sentence"]
        choices, answer = self._shuffle_choices(item["correct"], item["distractors"])
        score = self._score(
            base=24 + item["level"] * 5,
            steps=1,
            abstraction=2,
            distractor_quality=3,
            vocabulary_load=item["level"],
        )
        return SATQuestion(
            question_id=qid,
            section="verbal",
            skill="Words in context",
            prompt=prompt,
            choices=choices,
            correct_answer=answer,
            explanation=item["explanation"],
            difficulty_score=score,
            difficulty_label=difficulty_label(score),
        )

    def _build_transition_question(self, qid: int) -> SATQuestion:
        items = [
            {
                "text": (
                    "The first trial produced inconsistent results. ______, the researchers revised their method "
                    "and ran the experiment again."
                ),
                "correct": "Therefore,",
                "distractors": ["For example,", "Meanwhile,", "In contrast,"],
                "explanation": "The second sentence shows a result of the first, so a cause-and-effect transition fits.",
                "level": 2,
            },
            {
                "text": (
                    "Solar panels are expensive to install at first. ______, they often reduce electricity costs over time."
                ),
                "correct": "However,",
                "distractors": ["Similarly,", "Consequently,", "For instance,"],
                "explanation": "The second idea contrasts with the first, so a contrast transition is needed.",
                "level": 1,
            },
            {
                "text": (
                    "Several students volunteered to mentor younger classmates. ______, the school launched a peer-support program."
                ),
                "correct": "As a result,",
                "distractors": ["Likewise,", "Initially,", "Nonetheless,"],
                "explanation": "The second clause is the outcome, so an effect transition is best.",
                "level": 2,
            },
        ]
        item = self.rng.choice(items)
        prompt = "Which transition best completes the text?\n" + item["text"]
        choices, answer = self._shuffle_choices(item["correct"], item["distractors"])
        score = self._score(
            base=18 + item["level"] * 4,
            steps=1,
            abstraction=2,
            distractor_quality=2,
            vocabulary_load=1,
        )
        return SATQuestion(
            question_id=qid,
            section="verbal",
            skill="Transitions",
            prompt=prompt,
            choices=choices,
            correct_answer=answer,
            explanation=item["explanation"],
            difficulty_score=score,
            difficulty_label=difficulty_label(score),
        )

    def _build_grammar_question(self, qid: int) -> SATQuestion:
        items = [
            {
                "text": "The collection of essays by contemporary writers ____ on the front table of the library.",
                "correct": "sits",
                "distractors": ["sit", "are sitting", "have sat"],
                "explanation": "The subject is singular ('collection'), so the singular verb 'sits' is correct.",
                "level": 2,
            },
            {
                "text": "Neither the coaches nor the team captain ____ willing to cancel practice before the tournament.",
                "correct": "was",
                "distractors": ["were", "are", "be"],
                "explanation": "With 'neither...nor,' the verb agrees with the nearer subject ('captain'), which is singular.",
                "level": 3,
            },
            {
                "text": "A list of approved calculators ____ provided to every student before test day.",
                "correct": "is",
                "distractors": ["are", "were", "have been"],
                "explanation": "The subject is singular ('list'), so 'is' is the best choice.",
                "level": 1,
            },
        ]
        item = self.rng.choice(items)
        prompt = "Choose the option that best completes the sentence.\n" + item["text"]
        choices, answer = self._shuffle_choices(item["correct"], item["distractors"])
        score = self._score(
            base=20 + item["level"] * 5,
            steps=2,
            abstraction=2,
            distractor_quality=2,
            vocabulary_load=0,
        )
        return SATQuestion(
            question_id=qid,
            section="verbal",
            skill="Grammar and usage",
            prompt=prompt,
            choices=choices,
            correct_answer=answer,
            explanation=item["explanation"],
            difficulty_score=score,
            difficulty_label=difficulty_label(score),
        )

    def _build_rhetorical_purpose_question(self, qid: int) -> SATQuestion:
        items = [
            {
                "prompt": (
                    "A student is writing an essay arguing that city parks should receive more funding.\n"
                    "Which sentence would best support the essay's claim with specific evidence?"
                ),
                "correct": "In a 2024 survey, 71% of residents said neighborhood parks improved their weekly physical activity.",
                "distractors": [
                    "Parks have existed for a long time in many cities.",
                    "People enjoy spending time outdoors when the weather is mild.",
                    "Some neighborhoods have very old park benches.",
                ],
                "explanation": "The correct option adds concrete data that directly supports the funding argument.",
                "level": 3,
            },
            {
                "prompt": (
                    "A writer wants to introduce a paragraph about why students should learn financial literacy in high school.\n"
                    "Which sentence is the most effective introduction?"
                ),
                "correct": "Many graduates enter adulthood able to solve algebra equations but unable to compare loan terms or build a budget.",
                "distractors": [
                    "Financial literacy is a phrase used in education policy discussions.",
                    "High schools teach many subjects across four years.",
                    "Adults often make important decisions after graduation.",
                ],
                "explanation": "The correct sentence sets up the paragraph's problem clearly and specifically.",
                "level": 2,
            },
        ]
        item = self.rng.choice(items)
        choices, answer = self._shuffle_choices(item["correct"], item["distractors"])
        score = self._score(
            base=30 + item["level"] * 6,
            steps=2,
            abstraction=3,
            distractor_quality=3,
            vocabulary_load=1,
        )
        return SATQuestion(
            question_id=qid,
            section="verbal",
            skill="Rhetorical synthesis",
            prompt=item["prompt"],
            choices=choices,
            correct_answer=answer,
            explanation=item["explanation"],
            difficulty_score=score,
            difficulty_label=difficulty_label(score),
        )


def rank_questions(questions: Sequence[SATQuestion], order: str) -> List[SATQuestion]:
    reverse = order == "hardest"
    return sorted(questions, key=lambda q: q.difficulty_score, reverse=reverse)


def render_text(questions: Sequence[SATQuestion]) -> str:
    blocks: List[str] = []
    for question in questions:
        lines = [
            (
                f"Question {question.question_id} "
                f"[{question.section.upper()} · {question.skill}] "
                f"Difficulty: {question.difficulty_score} ({question.difficulty_label})"
            ),
            question.prompt,
        ]
        for letter in LETTERS:
            lines.append(f"{letter}. {question.choices[letter]}")
        lines.append(f"Correct answer: {question.correct_answer}")
        lines.append(f"Explanation: {question.explanation}")
        blocks.append("\n".join(lines))
    return ("\n\n" + "-" * 70 + "\n\n").join(blocks)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate SAT-style questions and rank them by estimated difficulty."
    )
    parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="How many questions to generate (default: 5).",
    )
    parser.add_argument(
        "--section",
        choices=["mixed", "math", "verbal"],
        default="mixed",
        help="Question section to generate (default: mixed).",
    )
    parser.add_argument(
        "--order",
        choices=["hardest", "easiest"],
        default="hardest",
        help="How to rank output by difficulty (default: hardest).",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for reproducible generation.",
    )
    args = parser.parse_args()
    if args.count < 1:
        parser.error("--count must be at least 1")
    return args


def main() -> None:
    args = parse_args()
    generator = SATQuestionGenerator(seed=args.seed)
    generated = generator.generate(count=args.count, section=args.section)
    ranked = rank_questions(generated, order=args.order)

    if args.format == "json":
        print(json.dumps([q.to_dict() for q in ranked], indent=2))
        return
    print(render_text(ranked))


if __name__ == "__main__":
    main()
