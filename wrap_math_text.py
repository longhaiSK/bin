#!/bin/sh
""":"
exec "$(dirname "$0")/.venv/bin/python" "$0" "$@"
"""

import re
import sys
import os

# --- CONFIGURATION ---

BLACKLIST = {
    'matrix', 'bmatrix', 'pmatrix', 'vmatrix', 
    'aligned', 'split', 'cases', 'array', 'equation', 
    'align', 'gather', 'frac', 'sqrt', 'sum', 'prod', 
    'lim', 'sin', 'cos', 'tan', 'log', 'ln', 'exp', 
    'det', 'sup', 'inf', 'min', 'max', 'arg', 'var', 'cov', 'cor',
    'hat', 'bar', 'tilde', 'vec', 'mathbf', 'mathrm', 'text', 'textit', 'textbf'
}

TEXT_COMMANDS = {'text', 'mathrm', 'mathbf', 'textit', 'textbf', 'sf', 'it', 'rm', 'label', 'tag', 'mbox'}

KNOWN_ACRONYMS = {
    'MSE', 'SSR', 'SSE', 'SST', 'MSA', 'MSB', 'MSC', 
    'MLE', 'OLS', 'GLS', 'WLS', 'BLUE', 
    'PDF', 'CDF', 'PMF', 'MGF', 
    'AIC', 'BIC', 'DIC', 'VIF', 
    'IID', 'RNG', 'SD', 'SE', 'CV',
    'ANOVA', 'MANOVA', 'ANCOVA', 
    'LRT', 'GLM', 'GAM', 'ROC', 'AUC'
}

class GlobalReplacer:
    def __init__(self):
        self.interactive = True
        self.count = 0

    def process_match(self, match):
        if match.group(1): return match.group(1) 
        if match.group(2): return replace_in_math_block(match.group(2), match.group(3), self) 
        if match.group(4): return replace_in_math_block(match.group(4), match.group(5), self) 
        return match.group(0)

def is_inside_text_command(full_string, current_index):
    # Backward scan to see if we are enclosed in {} of a text command
    balance = 0
    i = current_index - 1
    while i >= 0:
        char = full_string[i]
        if char == '}': 
            balance += 1
        elif char == '{':
            if balance > 0: 
                balance -= 1
            else:
                # Found the opening brace of our current scope
                cmd_end = i
                cmd_start = i - 1
                # Skip backwards over spaces
                while cmd_start >= 0 and full_string[cmd_start].isspace(): 
                    cmd_start -= 1
                # Scan backwards over letters to get command name
                while cmd_start >= 0 and full_string[cmd_start].isalpha(): 
                    cmd_start -= 1
                
                # Check if the command found is in our ignore list (e.g., \text, \mathrm)
                command_name = full_string[cmd_start+1 : cmd_end].strip()
                return command_name in TEXT_COMMANDS
        i -= 1
    return False

def replace_in_math_block(delimiter, content, state):
    # Regex Strategy:
    # 1. Look for words of 3+ letters followed immediately by '(' (Functions)
    # 2. OR Look for words of 2+ letters (Candidates for Acronyms)
    # 3. We use \b to ensure we don't cut inside words.
    # 4. We DO NOT match subscripts/superscripts. We leave them behind.
    word_pattern = r'(?<!\\)\b(?:([a-zA-Z]{3,})(?=\s*\()|([a-zA-Z0-9]{2,}))\b'

    def word_sub(m):
        full_match = m.group(0)
        base_word = m.group(1) if m.group(1) else m.group(2)
        
        # 1. Safety Checks
        if base_word in BLACKLIST: return full_match
        
        # Check if already wrapped (e.g. \text{MSE})
        if is_inside_text_command(content, m.start()): 
            return full_match

        # 2. Priority 1: Known Acronyms (Always wrap)
        if base_word in KNOWN_ACRONYMS:
            return perform_replacement(full_match, content, delimiter, m.start(), state)

        # 3. Priority 2: Functions and Long Words
        is_function = False
        next_char_idx = m.end()
        # Look ahead for '(' to confirm function status
        if next_char_idx < len(content):
            rest = content[next_char_idx:]
            if rest.lstrip().startswith('('):
                is_function = True

        # Logic: 
        # - Wrap if it is a function: Var(x)
        # - Wrap if it is a long word (4+ chars): ANOVA
        # - Ignore if it is short (2-3 chars) and NOT in known list: ABC, xy
        if is_function or (len(base_word) >= 4 and base_word.isalpha()):
            return perform_replacement(full_match, content, delimiter, m.start(), state)

        return full_match

    def perform_replacement(word, content, delimiter, start_pos, state):
        replacement = f"\\text{{{word}}}"
        
        if not state.interactive:
            state.count += 1
            return replacement

        print(f"\n{'-'*50}")
        # Preview context
        start_preview = max(0, start_pos - 20)
        end_preview = min(len(content), start_pos + len(word) + 25)
        preview_snippet = "..." + content[start_preview:end_preview] + "..."
        
        print(f"CONTEXT: {delimiter} {preview_snippet} {delimiter}")
        print(f"Found  : {word}")
        print(f"Change : {replacement}")
        
        while True:
            ans = input("Wrap? [y]es / [n]o / [a]ll / [q]uit: ").lower().strip()
            if ans == 'y':
                state.count += 1
                return replacement
            elif ans == 'n':
                return word
            elif ans == 'a':
                state.interactive = False
                state.count += 1
                return replacement
            elif ans == 'q':
                sys.exit(0)

    new_content = re.sub(word_pattern, word_sub, content)
    return delimiter + new_content + delimiter

def main():
    if len(sys.argv) < 2:
        print("Usage: ./wrap_math_text.py <filename.qmd>")
        sys.exit(1)
    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        sys.exit(1)
    with open(file_path, 'r', encoding='utf-8') as f: full_content = f.read()
    
    # Backup
    with open(file_path + ".bak", 'w', encoding='utf-8') as f: f.write(full_content)
    print(f"Backup created: {file_path}.bak")

    # Master Regex: Code blocks OR Display Math OR Inline Math
    master_pattern = r'(?s)(`{1,3}.+?`{1,3})|(?<!\\)(\$\$)(.+?)(?<!\\)\$\$|(?<!\\)(\$)(?!\s)([^$\n`]+?)(?<!\s)(?<!\\)\$'
    replacer = GlobalReplacer()
    new_full_content = re.sub(master_pattern, replacer.process_match, full_content)

    if replacer.count > 0:
        with open(file_path, 'w', encoding='utf-8') as f: f.write(new_full_content)
        print(f"\nSuccess! Wrapped {replacer.count} terms.")
    else:
        print("\nNo changes made.")

if __name__ == "__main__":
    main()