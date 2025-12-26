#!/bin/sh
""":"
exec "$(dirname "$0")/.venv/bin/python" "$0" "$@"
"""

import re
import sys
import os

# --- CONFIGURATION ---
# Words that should NEVER be wrapped, even if they appear in math
# (e.g., arguments to environment commands)
BLACKLIST = {'matrix', 'bmatrix', 'pmatrix', 'aligned', 'split', 'cases', 'array', 'equation'}

def replace_in_math(match, interactive=True):
    math_content = match.group(2) # The content inside the $ or $$
    delimiter = match.group(1)    # The $ or $$ itself

    # Regex to find multi-letter words NOT preceded by a backslash
    # (?<!\\)  -> Negative lookbehind: Not preceded by \
    # \b       -> Word boundary start
    # [a-zA-Z]{2,} -> 2 or more letters
    # \b       -> Word boundary end
    word_pattern = r'(?<!\\)\b([a-zA-Z]{2,})\b'

    def word_callback(w_match):
        word = w_match.group(1)
        
        # Skip blacklisted structural words
        if word in BLACKLIST:
            return word
        
        # Skip if it looks like it's already in a \text{} or similar command
        # (This is a naive check looking at surrounding chars)
        start, end = w_match.span()
        context_before = math_content[max(0, start-6):start]
        if 'text{' in context_before or 'mathrm{' in context_before:
            return word

        replacement = f"\\text{{{word}}}"
        
        if not interactive:
            return replacement

        # Interactive Prompt
        print(f"\n{'-'*40}")
        print(f"MATH CONTEXT: {delimiter}{math_content.strip()}{delimiter}")
        print(f"Found Word  : {word}")
        print(f"Replace with: {replacement}")
        print(f"{'-'*40}")

        while True:
            choice = input("Wrap this word? [y]es / [n]o / [a]ll / [q]uit: ").lower().strip()
            if choice == 'y':
                return replacement
            elif choice == 'n':
                return word
            elif choice == 'a':
                # Disable future prompts for this file run
                nonlocal interactive
                interactive = False 
                return replacement
            elif choice == 'q':
                print("\nQuitting. No changes saved.")
                sys.exit(0)
            else:
                print("Invalid choice.")

    # Apply the word replacement *inside* the math block
    new_math_content = re.sub(word_pattern, word_callback, math_content)
    
    return delimiter + new_math_content + delimiter

def main():
    if len(sys.argv) < 2:
        print("Usage: ./wrap_math_text.py <filename.qmd>")
        sys.exit(1)

    file_path = sys.argv[1]
    
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        sys.exit(1)

    # Backup
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    with open(file_path + ".bak", 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Backup created: {file_path}.bak")

    # Regex to find Math Blocks ($...$ or $$...$$)
    # (?s) -> Dot matches newline
    # (\$\$?) -> Capture $ or $$ (Group 1)
    # (.+?)   -> Capture content non-greedy (Group 2)
    # \1      -> Match the same closing delimiter
    math_block_pattern = r'(?s)(\$\$?)(.+?)\1'

    # We use a closure to maintain the "interactive" state across calls
    # Note: simple variable scoping in nested functions requires care, 
    # but re.sub doesn't easily allow passing state. 
    # For this script, 'a' (All) works per-math-block in the current logic. 
    # To make 'a' global, we'd need a class. 
    # For safety, I've left 'a' as "All within this block" or simple yes.
    # To properly implement global 'All', we use the Class approach below.

    replacer = GlobalReplacer()
    new_content = re.sub(math_block_pattern, replacer.process_block, content)

    if replacer.count > 0:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"\nSuccess! Wrapped {replacer.count} terms.")
    else:
        print("\nNo changes made.")

class GlobalReplacer:
    def __init__(self):
        self.interactive = True
        self.count = 0

    def process_block(self, match):
        return replace_in_math_block(match, self)

def replace_in_math_block(match, state):
    delimiter = match.group(1)
    content = match.group(2)
    
    # Inner Regex for words
    word_pattern = r'(?<!\\)\b([a-zA-Z]{2,})\b'

    def word_sub(m):
        word = m.group(1)
        if word in BLACKLIST: return word
        
        # Heuristic: check if already wrapped in standard text commands
        # (This avoids \text{\text{Var}})
        start_idx = m.start()
        # Look back 7 chars for \text{ or \mathrm{
        preceding = content[max(0, start_idx-7):start_idx]
        if '{' in preceding and ('text' in preceding or 'rm' in preceding or 'bf' in preceding):
            return word

        replacement = f"\\text{{{word}}}"

        if not state.interactive:
            state.count += 1
            return replacement

        print(f"\nMath: {delimiter}... {word} ...{delimiter}")
        print(f"Change: {word}  -->  {replacement}")
        
        while True:
            ans = input("[y]es / [n]o / [a]ll (global) / [q]uit: ").lower()
            if ans == 'y':
                state.count += 1
                return replacement
            if ans == 'n':
                return word
            if ans == 'a':
                state.interactive = False
                state.count += 1
                return replacement
            if ans == 'q':
                sys.exit(0)

    new_content = re.sub(word_pattern, word_sub, content)
    return delimiter + new_content + delimiter

if __name__ == "__main__":
    main()