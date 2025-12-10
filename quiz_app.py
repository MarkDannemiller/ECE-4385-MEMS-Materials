#!/usr/bin/env python3
"""Interactive quiz runner for the markdown quizzes in quizzes/."""

import os
import random
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import List, Set

try:  # optional color support
    import colorama

    colorama.just_fix_windows_console()
except Exception:
    colorama = None


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    YELLOW = "\033[93m"
    GRAY = "\033[90m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def color(text: str, code: str) -> str:
    return f"{code}{text}{Colors.RESET}"


@dataclass
class Question:
    prompt: str
    display_prompt: str
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
        if ch == b"\x03":  # Ctrl+C
            raise KeyboardInterrupt
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
        if ch == "\x03":  # Ctrl+C
            raise KeyboardInterrupt
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


def wait_for_continue(message: str | None = None) -> None:
    if os.name == "nt":
        import msvcrt

        if message:
            print(message, end="", flush=True)
        ch = msvcrt.getch()
        if ch == b"\x03":
            raise KeyboardInterrupt
    else:
        if message:
            input(message)
        else:
            input()


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

        display_prompt = prompt
        if kind == "fill":
            correct_answer = options[0] if options else ""
            if prompt.lower().strip() in {"fill in the blank", ""}:
                masked = (
                    " ".join("_" * len(word) for word in correct_answer.split())
                    if correct_answer
                    else "________"
                )
                display_prompt = f"Fill in the blank: {masked}"

        questions.append(
            Question(
                prompt=prompt,
                display_prompt=display_prompt,
                options=options,
                correct_indices=correct_indices,
                kind=kind,
                source=path.name,
            )
        )

    return questions


def load_all_questions(quizzes_dir: Path) -> List[Question]:
    questions: List[Question] = []
    search_dirs = [quizzes_dir, quizzes_dir.parent / "generated-quizzes"]
    for directory in search_dirs:
        if not directory.exists():
            continue
        for file_path in sorted(directory.glob("quiz*.md")):
            questions.extend(parse_quiz_file(file_path))
    for q in questions:
        shuffle_choices(q)
    return questions


def shuffle_choices(question: Question) -> None:
    """Shuffle answer choices while preserving correct indices."""
    if question.kind == "fill":
        return
    order = list(range(len(question.options)))
    random.shuffle(order)
    new_options = [question.options[i] for i in order]
    new_correct = {new_idx for new_idx, old_idx in enumerate(order) if old_idx in question.correct_indices}
    question.options = new_options
    question.correct_indices = new_correct


def show_summary(
    total_correct: int,
    total_asked: int,
    stats_by_file: dict[str, dict[str, int]],
    prefix: str | None = None,
) -> None:
    clear_screen()
    if prefix:
        print(color(prefix, Colors.RED))
        print()

    title = "Performance Summary"
    print(color(title, Colors.BOLD + Colors.CYAN))
    print(color("-" * len(title), Colors.CYAN))

    if total_asked == 0:
        print("No questions answered.")
        return

    pct = (total_correct / total_asked) * 100 if total_asked else 0.0
    print(color(f"Total: {total_correct}/{total_asked} correct ({pct:.1f}%)", Colors.YELLOW))
    print()

    # Build table
    headers = ["Quiz file", "Correct/Total", "Percent"]
    name_width = max((len(fname) for fname in stats_by_file), default=len(headers[0]))
    ct_width = len("Correct/Total")
    pct_width = len("Percent")

    def row(file_name: str, correct: int, total: int, percent: float) -> str:
        return f"{file_name:<{name_width}}  {correct:>{ct_width-7}}/{total:<{ct_width-7}}  {percent:>{pct_width}.1f}%"

    header_line = f"{headers[0]:<{name_width}}  {headers[1]:<{ct_width}}  {headers[2]:>{pct_width}}"
    print(color(header_line, Colors.BOLD + Colors.CYAN))
    print(color("-" * len(header_line), Colors.CYAN))

    for fname in sorted(stats_by_file):
        data = stats_by_file[fname]
        t = data.get("total", 0)
        c = data.get("correct", 0)
        pct_file = (c / t) * 100 if t else 0.0
        line = row(fname, c, t, pct_file)
        line_color = Colors.GREEN if pct_file >= 70 else Colors.YELLOW if pct_file >= 50 else Colors.RED
        print(color(line, line_color))


def render_question(
    question: Question,
    pointer: int,
    picked: Set[int],
    total: int,
    idx: int,
    phase: str = "ask",
    user_selection: Set[int] | None = None,
    was_correct: bool | None = None,
) -> None:
    clear_screen()
    header = f"Question {idx + 1} of {total} ({question.source})"
    print(color(header, Colors.BOLD + Colors.CYAN))
    print(color("-" * len(header), Colors.CYAN))
    prompt_text = question.display_prompt if hasattr(question, "display_prompt") else question.prompt
    print(color(prompt_text, Colors.YELLOW + Colors.BOLD))
    print()
        

    if question.kind == "fill":
        if phase == "feedback":
            instructions = "(Press any key to continue.)"
        else:
            instructions = "(Type your answer and press Enter to confirm.)"
        print(color(instructions, Colors.GRAY))
        return

    for i, option in enumerate(question.options):
        marker = ">"
        is_selected = (
            i in picked if phase == "ask" else (user_selection is not None and i in user_selection)
        )

        caret = color(marker, Colors.CYAN) if (phase == "ask" and i == pointer) else " "
        selection_tag = ""
        if question.kind == "multi":
            selection_tag = "[x]" if is_selected else "[ ]"

        line = f"{caret} {i+1}. {selection_tag + ' ' if selection_tag else ''}{option}"

        line_color = None
        if phase == "feedback":
            if i in question.correct_indices:
                line_color = Colors.GREEN
            elif is_selected:
                line_color = Colors.RED

        if phase == "ask" and i == pointer:
            line_color = Colors.CYAN

        print(color(line, line_color) if line_color else line)

    print()
    if phase == "feedback":
        instructions = "(Press any key to continue.)"
    elif question.kind == "multi":
        instructions = "(Use arrow keys or numbers to choose; Space toggles; Enter submits; q quits.)"
    else:
        instructions = "(Use arrow keys or numbers to choose; Enter submits; q quits.)"
    print(color(instructions, Colors.GRAY))

    if phase == "feedback" and was_correct is not None:
        status_text = "Correct!" if was_correct else "Incorrect."
        status_color = Colors.GREEN if was_correct else Colors.RED
        print(color(status_text, status_color))


def ask_fill_in(question: Question) -> tuple[bool, str]:
    user_input = input("\nYour answer: ").strip()
    correct_answer = question.options[0].strip()
    return user_input.lower() == correct_answer.lower(), user_input


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


def ask_question(
    question: Question, idx: int, total: int
) -> tuple[bool | None, Set[int] | str | None]:
    if question.kind == "fill":
        clear_screen()
        header = f"Question {idx + 1} of {total} ({question.source})"
        print(color(header, Colors.BOLD + Colors.CYAN))
        print(color("-" * len(header), Colors.CYAN))
        prompt_text = question.display_prompt if hasattr(question, "display_prompt") else question.prompt
        print(color(prompt_text, Colors.YELLOW + Colors.BOLD))
        print()
        print(color("(Type your answer and press Enter to confirm.)", Colors.GRAY))
        user_correct, user_input = ask_fill_in(question)
        return user_correct, user_input

    selected = ask_multiple_choice(question, idx=idx, total=total)
    if selected is None:
        return None, None
    return selected == question.correct_indices, selected


def show_feedback(
    question: Question,
    correct: bool,
    user_response: Set[int] | str | None,
    idx: int,
    total: int,
) -> None:
    if question.kind == "fill":
        clear_screen()
        header = f"Question {idx + 1} of {total} ({question.source})"
        print(color(header, Colors.BOLD + Colors.CYAN))
        print(color("-" * len(header), Colors.CYAN))
        status_text = "Correct!" if correct else "Incorrect."
        status_color = Colors.GREEN if correct else Colors.RED
        print(color(status_text, status_color))
        prompt_text = question.display_prompt if hasattr(question, "display_prompt") else question.prompt
        print(color(prompt_text, Colors.YELLOW + Colors.BOLD))
        print()

        user_text = user_response if isinstance(user_response, str) else ""
        if correct:
            print(color(f"Your answer: {user_text}", Colors.GREEN))
        else:
            print(color(f"Your answer: {user_text}", Colors.RED))
            correct_answer = question.options[0]
            print(color(f"Correct answer: {correct_answer}", Colors.GREEN))

        print()
        print(color("(Press any key to continue.)", Colors.GRAY))
        return

    selection_set = user_response if isinstance(user_response, set) else set()
    render_question(
        question=question,
        pointer=-1,
        picked=selection_set,
        total=total,
        idx=idx,
        phase="feedback",
        user_selection=selection_set,
        was_correct=correct,
    )


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

    total_correct = 0
    total_asked = 0
    stats_by_file: dict[str, dict[str, int]] = defaultdict(
        lambda: {"correct": 0, "total": 0}
    )
    exit_message: str | None = None

    try:
        for idx, question in enumerate(questions):
            user_correct, user_response = ask_question(
                question, idx=idx, total=len(questions)
            )
            if user_correct is None:
                exit_message = "Exiting..."
                break

            total_asked += 1
            stats_by_file[question.source]["total"] += 1
            if user_correct:
                total_correct += 1
                stats_by_file[question.source]["correct"] += 1

            show_feedback(
                question,
                bool(user_correct),
                user_response,
                idx=idx,
                total=len(questions),
            )
            wait_for_continue()
    except KeyboardInterrupt:
        exit_message = "Quiz interrupted."
    finally:
        show_summary(
            total_correct=total_correct,
            total_asked=total_asked,
            stats_by_file=stats_by_file,
            prefix=exit_message,
        )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        clear_screen()
        print("Quiz interrupted.")
