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
- Feel free to delete/move quizzes from the `quizzes/` and `generated-quizzes/` folders if you are studying for the midterm and need a reduced set of material.

## Usage
```bash
python quiz_app.py
```

## Notes
- Requires Python 3 (no external packages).
- Runs best in a terminal window; on Windows, arrow keys and number keys work via `msvcrt`.

## Additional
Here is a link to a GPT that may work to help you study, asking the questions from this repo:
https://chatgpt.com/g/g-6939b02a55a88191af0e5eb485cf39c3-mems-ece-4385-study-assistant