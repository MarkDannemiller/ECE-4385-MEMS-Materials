# ECE 4385 MEMS Quizzes

This repo contains practice quizzes for the Texas Tech ECE 4385 MEMS course and a small interactive study app.

## Quizzes
- Stored in `quizzes/quiz*.md`; each file mirrors a course quiz. Generated sets live in `generated-quizzes/`.
- Correct options are marked with a leading `x`, and select-all questions keep multiple `x` marks.
- Some quizzes include fill-in-the-blank entries (e.g., `quiz26-nanotechnology.md`).

## Study App
- `quiz_app.py` loads all quizzes, shuffles questions, and runs them in the terminal.
- Supports arrow keys **or** number keys to choose answers; space toggles on select-all; Enter submits; `q` quits.
- Fill-in questions prompt for text; feedback shows correct/incorrect plus the right answer(s).

## Usage
```bash
python quiz_app.py
```

## Notes
- Requires Python 3 (no external packages).
- Runs best in a terminal window; on Windows, arrow keys and number keys work via `msvcrt`.
