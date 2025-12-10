#!/usr/bin/env python3
"""
Script to format quiz files to a consistent format.
- Removes "Correct answer" lines
- Converts unformatted files to the standard format
- Ensures blank lines before question headers
- Standardizes "points" to "pts"
"""

import os
import re
from pathlib import Path


def parse_unformatted_quiz(content):
    """Parse unformatted quiz files (like quiz12 original format)."""
    questions = []
    lines = [l.rstrip() for l in content.split('\n')]
    
    current_q = None
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines
        if not line:
            i += 1
            continue
        
        # Check for "Results for question X" pattern
        results_match = re.match(r'Results for question (\d+)\.', line)
        if results_match:
            # Save previous question
            if current_q and current_q['text']:
                questions.append(current_q)
            
            q_num = int(results_match.group(1))
            i += 1
            
            # Skip question number line
            if i < len(lines) and re.match(r'^\d+$', lines[i].strip()):
                i += 1
            
            # Skip points line
            if i < len(lines) and ('/ 10 points' in lines[i] or '/ 10 pts' in lines[i]):
                i += 1
            
            # Skip "Multiple Choice"
            if i < len(lines) and lines[i].strip() == 'Multiple Choice':
                i += 1
            
            # Get question text
            q_text = ""
            if i < len(lines):
                q_text = lines[i].strip()
                i += 1
            
            current_q = {
                'num': q_num,
                'text': q_text,
                'options': [],
                'correct': set()  # Use set to track multiple correct answers
            }
            continue
        
        # Check for "Correct answer:" label
        if line == 'Correct answer:' or line == 'Correct answer':
            # Look back to find the option text (skip empty lines)
            j = i - 1
            while j >= 0 and not lines[j].strip():
                j -= 1
            # Actually, the correct answer comes AFTER "Correct answer:"
            # Skip empty line after "Correct answer:"
            if i + 1 < len(lines) and not lines[i + 1].strip():
                i += 1
            # Get the answer text
            if i + 1 < len(lines):
                correct_text = lines[i + 1].strip()
                if correct_text and current_q:
                    current_q['correct'].add(correct_text)  # Add to set
                    if correct_text not in current_q['options']:
                        current_q['options'].append(correct_text)
                i += 2  # Skip the answer text line
            else:
                i += 1
            continue
        
        # Check for ", Not Selected" (comes after option text with empty line in between)
        if line == ', Not Selected':
            # Look back to find the option text (skip empty lines)
            j = i - 1
            while j >= 0 and not lines[j].strip():
                j -= 1
            if j >= 0 and current_q:
                option_text = lines[j].strip()
                # Make sure it's not "Correct answer:" or question text
                if option_text and option_text not in ['Correct answer:', 'Correct answer']:
                    if option_text not in current_q['options']:
                        current_q['options'].append(option_text)
            i += 1
            continue
        
        # Handle first question (might not have "Results for question" header)
        if current_q is None:
            if '?' in line or (':' in line and len(line) > 20):
                current_q = {
                    'num': 1,
                    'text': line,
                    'options': [],
                    'correct': set()  # Use set to track multiple correct answers
                }
                i += 1
                continue
        
        i += 1
    
    # Save last question
    if current_q and current_q['text']:
        questions.append(current_q)
    
    return questions


def parse_formatted_quiz(content):
    """Parse already formatted quiz files, preserving structure."""
    questions = []
    lines = content.split('\n')
    
    current_q = None
    i = 0
    
    # Check if first question doesn't have a header (like quiz10)
    first_line = lines[0].strip() if lines else ""
    if first_line and not first_line.startswith('Question') and ('?' in first_line or ':' in first_line):
        # First question starts without header - collect it and its options
        current_q = {
            'num': 1,
            'text': first_line,
            'options': [],
            'correct': set()  # Use set to track multiple correct answers
        }
        i = 1
        
        # Collect options for first question until we hit "Question 2"
        while i < len(lines):
            opt_line = lines[i]
            opt_stripped = opt_line.strip()
            
            # Stop if we hit next question
            if re.match(r'^Question \d+$', opt_stripped):
                break
            
            # Skip empty lines
            if not opt_stripped:
                i += 1
                continue
            
            # Skip "Correct answer" lines
            if opt_stripped == 'Correct answer':
                i += 1
                continue
            
            # Parse option
            if opt_line.startswith('x '):
                opt = opt_line[2:].rstrip()
                current_q['options'].append(opt)
                current_q['correct'].add(opt)  # Add to set of correct answers
            elif opt_line.startswith('  ') and len(opt_stripped) > 0:
                opt = opt_line[2:].rstrip()
                current_q['options'].append(opt)
            # If it doesn't match, might be end of options
            else:
                break
            
            i += 1
        
        # Save first question
        if current_q:
            questions.append(current_q)
            current_q = None
    
    while i < len(lines):
        line = lines[i]
        line_stripped = line.strip()
        
        # Look for "Question X" header
        match = re.match(r'^Question (\d+)$', line_stripped)
        if match:
            # Save previous question
            if current_q:
                questions.append(current_q)
            
            q_num = int(match.group(1))
            i += 1
            
            # Get points line
            if i < len(lines):
                pts_line = lines[i].strip()
                if '/ 10' in pts_line:
                    i += 1
            
            # Get question text
            q_text = ""
            if i < len(lines):
                q_text = lines[i].strip()
                i += 1
            
            current_q = {
                'num': q_num,
                'text': q_text,
                'options': [],
                'correct': set()  # Use set to track multiple correct answers
            }
            
            # Collect options until we hit a blank line followed by "Question" or end
            while i < len(lines):
                opt_line = lines[i]
                opt_stripped = opt_line.strip()
                
                # Stop if we hit next question
                if re.match(r'^Question \d+$', opt_stripped):
                    break
                
                # Skip empty lines (but check if next is a question)
                if not opt_stripped:
                    if i + 1 < len(lines) and re.match(r'^Question \d+$', lines[i + 1].strip()):
                        i += 1
                        break
                    i += 1
                    continue
                
                # Skip "Correct answer" lines
                if opt_stripped == 'Correct answer':
                    i += 1
                    continue
                
                # Parse option - check original line for leading "x " or "  " (two spaces)
                if opt_line.startswith('x '):
                    opt = opt_line[2:].rstrip()  # Remove leading "x " and trailing spaces
                    current_q['options'].append(opt)
                    current_q['correct'].add(opt)  # Add to set of correct answers
                elif opt_line.startswith('  ') and len(opt_line.strip()) > 0:
                    opt = opt_line[2:].rstrip()  # Remove leading "  " and trailing spaces
                    current_q['options'].append(opt)
                # If line doesn't match pattern, stop collecting options
                else:
                    break
                
                i += 1
            
            continue
        
        i += 1
    
    # Save last question
    if current_q:
        questions.append(current_q)
    
    return questions


def format_questions(questions):
    """Format questions into the standard format."""
    if not questions:
        return ""
    
    output_lines = []
    
    for i, q in enumerate(questions):
        # Add blank line before question (except first)
        if i > 0:
            output_lines.append('')
        
        # Question header
        output_lines.append(f"Question {q['num']}")
        
        # Points line
        output_lines.append("10 / 10 pts")
        
        # Question text
        output_lines.append(q['text'])
        
        # Options - mark correct answers with 'x', others with two spaces
        # Support multiple correct answers (multiple choice)
        correct_options = q.get('correct', set())
        if isinstance(correct_options, str):
            # Backward compatibility: if it's a string, convert to set
            correct_options = {correct_options}
        elif not isinstance(correct_options, set):
            # If it's None or other type, make it an empty set
            correct_options = set()
        
        for option in q['options']:
            # Check if this option is in the set of correct answers
            if option.strip() in {opt.strip() for opt in correct_options}:
                output_lines.append(f"x {option}")
            else:
                output_lines.append(f"  {option}")
    
    # Join lines and ensure file ends with a newline
    return '\n'.join(output_lines) + '\n'


def process_quiz_file(filepath):
    """Process a single quiz file."""
    print(f"Processing {filepath.name}...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if file is already formatted (has any "Question X" header)
    if re.search(r'^Question \d+$', content, re.MULTILINE):
        # Already formatted, parse and clean up
        questions = parse_formatted_quiz(content)
    else:
        # Unformatted, need to parse and convert
        questions = parse_unformatted_quiz(content)
    
    if not questions:
        print(f"  Warning: No questions found in {filepath.name}")
        return
    
    # Format questions
    formatted = format_questions(questions)
    
    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(formatted)
    
    print(f"  ✓ Formatted {len(questions)} questions")


def main():
    """Main function to process all quiz files."""
    quizzes_dir = Path('quizzes')
    
    if not quizzes_dir.exists():
        print(f"Error: {quizzes_dir} directory not found")
        return
    
    quiz_files = sorted(quizzes_dir.glob('quiz*.md'))
    
    if not quiz_files:
        print("No quiz files found")
        return
    
    print(f"Found {len(quiz_files)} quiz files\n")
    
    for quiz_file in quiz_files:
        try:
            process_quiz_file(quiz_file)
        except Exception as e:
            print(f"  ✗ Error processing {quiz_file.name}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\nDone!")


if __name__ == '__main__':
    main()
