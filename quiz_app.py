#!/usr/bin/env python3
"""Interactive quiz runner for the markdown quizzes in quizzes/."""

import os
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Set


@dataclass
class Question:
    prompt: str
    options: List[str]
    correct_indices: Set[int]
    kind: str  # "single", "multi", "fill"
    source: str


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def read_key() -> str | None:
    """Read a single key press and normalize common controls."""
    if os.name == "nt":
        import msvcrt

        ch = msvcrt.getch()
        if ch in (b"\x00", b"\xe0"):
            ch = msvcrt.getch()
            return {
                b"H": "UP",
                b"P": "DOWN",
                b"K": "LEFT",
                b"M": "RIGHT",
            }.get(ch)
        if ch == b"\r":
            return "ENTER"
        if ch == b" ":
            return "SPACE"
        if ch.isdigit():
            return f"NUM_{ch.decode()}"
        if ch in (b"q", b"Q"):
            return "QUIT"
        return None

    import termios
    import tty

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            seq = sys.stdin.read(2)
            if seq == "[A":
                return "UP"
            if seq == "[B":
                return "DOWN"
            if seq == "[C":
                return "RIGHT"
            if seq == "[D":
                return "LEFT"
            return None
        if ch in ("\r", "\n"):
            return "ENTER"
        if ch == " ":
            return "SPACE"
        if ch.isdigit():
            return f"NUM_{ch}"
        if ch in ("q", "Q"):
            return "QUIT"
        return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def wait_for_continue() -> None:
    if os.name == "nt":
        import msvcrt

        print("\nPress any key for the next question...", end="", flush=True)
        msvcrt.getch()
    else:
        input("\nPress Enter for the next question...")


def normalize_prompt(lines: List[str]) -> str:
    return " ".join(line.strip() for line in lines if line.strip())


def detect_kind(prompt: str, options: List[str], correct_indices: Set[int]) -> str:
    lower_prompt = prompt.lower()
    is_fill = "fill in the blank" in lower_prompt or (
        len(options) == 1 and len(correct_indices) == 1
    )
    is_multi = (
        len(correct_indices) > 1
        or "select all" in lower_prompt
        or "check all" in lower_prompt
    )
    if is_fill:
        return "fill"
    return "multi" if is_multi else "single"


def parse_quiz_file(path: Path) -> List[Question]:
    questions: List[Question] = []
    with path.open(encoding="utf-8") as fh:
        lines = [line.rstrip("\n") for line in fh]

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line.startswith("Question"):
            i += 1
            continue

        i += 1  # move past "Question X"
        if i < len(lines) and "/ 10 pts" in lines[i]:
            i += 1  # skip points line

        prompt_lines: List[str] = []
        while i < len(lines):
            l = lines[i]
            if l.startswith("x ") or l.startswith("  "):
                break
            if l.strip():
                prompt_lines.append(l.strip())
            i += 1

        options: List[str] = []
        correct_indices: Set[int] = set()
        while i < len(lines):
            l = lines[i]
            if l.strip() == "":
                i += 1
                break
            if l.startswith("x "):
                correct_indices.add(len(options))
                opt_text = l[2:].strip()
            elif l.startswith("  "):
                opt_text = l.strip()
            else:
                opt_text = l.strip()
            options.append(opt_text)
            i += 1

        prompt = normalize_prompt(prompt_lines)
        kind = detect_kind(prompt, options, correct_indices)
        questions.append(
            Question(
                prompt=prompt,
                options=options,
                correct_indices=correct_indices,
                kind=kind,
                source=path.name,
            )
        )

    return questions


def load_all_questions(quizzes_dir: Path) -> List[Question]:
    questions: List[Question] = []
    for file_path in sorted(quizzes_dir.glob("quiz*.md")):
        questions.extend(parse_quiz_file(file_path))
    return questions


def render_question(
    question: Question, pointer: int, picked: Set[int], total: int, idx: int
) -> None:
    clear_screen()
    header = f"Question {idx + 1} of {total} ({question.source})"
    print(header)
    print("-" * len(header))
    print(question.prompt)

    if question.kind == "fill":
        print("\nType your answer and press Enter to confirm.")
        return

    print("\nUse arrow keys or numbers to move, Enter to submit.")
    if question.kind == "multi":
        print("Space toggles selections for select-all questions.")

    for i, option in enumerate(question.options):
        marker = ">"
        if question.kind == "multi":
            selected = "[x]" if i in picked else "[ ]"
            caret = marker if i == pointer else " "
            print(f"{caret} {i+1}. {selected} {option}")
        else:
            caret = marker if i == pointer else " "
            print(f"{caret} {i+1}. {option}")


def ask_fill_in(question: Question) -> bool:
    user_input = input("\nYour answer: ").strip()
    correct_answer = question.options[0].strip()
    return user_input.lower() == correct_answer.lower()


def ask_multiple_choice(
    question: Question, idx: int, total: int
) -> Set[int] | None:
    pointer = 0
    picked: Set[int] = set()
    total_options = len(question.options)

    while True:
        render_question(
            question, pointer=pointer, picked=picked, total=total, idx=idx
        )
        key = read_key()
        if key == "UP":
            pointer = (pointer - 1) % total_options
        elif key == "DOWN":
            pointer = (pointer + 1) % total_options
        elif key and key.startswith("NUM_"):
            num = int(key.split("_", 1)[1])
            if 1 <= num <= total_options:
                pointer = num - 1
                if question.kind == "single":
                    return {pointer}
                picked.symmetric_difference_update({pointer})
        elif key == "SPACE" and question.kind == "multi":
            picked.symmetric_difference_update({pointer})
        elif key == "ENTER":
            if question.kind == "single":
                return {pointer}
            if picked:
                return set(picked)
            return {pointer}
        elif key == "QUIT":
            return None


def ask_question(question: Question, idx: int, total: int) -> bool | None:
    if question.kind == "fill":
        clear_screen()
        header = f"Question {idx + 1} of {total} ({question.source})"
        print(header)
        print("-" * len(header))
        print(question.prompt)
        print("\nFill in the blank and press Enter to confirm.")
        user_correct = ask_fill_in(question)
        return user_correct

    selected = ask_multiple_choice(question, idx=idx, total=total)
    if selected is None:
        return None
    return selected == question.correct_indices


def show_feedback(question: Question, correct: bool, user_selection: Set[int] | None) -> None:
    clear_screen()
    print("Correct!" if correct else "Incorrect.")

    if question.kind == "fill":
        answer_text = question.options[0]
        print(f"Correct answer: {answer_text}")
    else:
        correct_answers = [question.options[i] for i in sorted(question.correct_indices)]
        print("Correct answer(s):")
        for opt in correct_answers:
            print(f"- {opt}")
        if user_selection is not None:
            user_answers = [question.options[i] for i in sorted(user_selection)]
            print("\nYour answer:")
            for opt in user_answers:
                print(f"- {opt}")


def main() -> None:
    base_dir = Path(__file__).parent
    quizzes_dir = base_dir / "quizzes"
    if not quizzes_dir.exists():
        print("Could not find quizzes directory.")
        sys.exit(1)

    questions = load_all_questions(quizzes_dir)
    if not questions:
        print("No questions found.")
        sys.exit(1)

    random.shuffle(questions)

    for idx, question in enumerate(questions):
        if question.kind == "fill":
            user_correct = ask_question(question, idx, len(questions))
            user_selection: Set[int] | None = None
        else:
            selection = ask_multiple_choice(
                question, idx=idx, total=len(questions)
            )
            if selection is None:
                print("\nExiting...")
                break
            user_selection = selection
            user_correct = selection == question.correct_indices

        if user_correct is None:
            break

        show_feedback(question, bool(user_correct), user_selection)
        wait_for_continue()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        clear_screen()
        print("Quiz interrupted.")
