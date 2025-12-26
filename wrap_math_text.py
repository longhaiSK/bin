#!/bin/sh
""":"
exec "$(dirname "$0")/.venv/bin/python" "$0" "$@"
"""

import re
import sys
import os

# --- CONFIGURATION ---

# 1. Words to NEVER wrap (LaTeX commands)
BLACKLIST = {
    'matrix', 'bmatrix', 'pmatrix', 'vmatrix', 
    'aligned', 'split', 'cases', 'array', 'equation', 
    'align', 'gather', 'frac', 'sqrt', 'sum', 'prod', 
    'lim', 'sin', 'cos', 'tan', 'log', 'ln', 'exp', 
    'det', 'sup', 'inf', 'min', 'max', 'arg', 'var', 'cov', 'cor',
    'hat', 'bar', 'tilde', 'vec', 'mathbf', 'mathrm', 'text', 'textit', 'textbf'
}

# 2. Commands that are already "Text" (Don't wrap inside these)
TEXT_COMMANDS = {'text', 'mathrm', 'mathbf', 'textit', 'textbf', 'sf', 'it', 'rm', 'label', 'tag', 'mbox'}

# 3. KNOWN 3-LETTER ACRONYMS (Whitelist)
#    Only these 3-letter words will be wrapped. 
#    Combinations like 'AXB' or 'XY Z' will be ignored unless added here.
KNOWN_ACRONYMS = {
    'MSE', 'SSR', 'SSE', 'SST', 'MSA', 'MSB', 'MSC', 
    'MLE', 'OLS', 'GLS', 'WLS', 'BLUE', 
    'PDF', 'CDF', 'PMF', 'MGF', 
    'AIC', 'BIC', 'DIC', 'VIF', 
    'IID', 'RNG', 'SD', 'SE', 'CV',
    'ANOVA', 'MANOVA', 'ANCOVA', # These match the 4+ rule anyway, but safe to keep
    'LRT', 'GLM', 'GAM', 'ROC', 'AUC'
}

class GlobalReplacer:
    def __init__(self):
        self.interactive = True
        self.count = 0

    def process_match(self, match):
        if match.group(1): return match.group(1) # Code Block
        if match.group(2): return replace_in_math_block(match.group(2), match.group(3), self) # $$
        if match.group(4): return replace_in_math_block(match.group(4), match.group(5), self) # $
        return match.group(0)

def is_inside_text_command(full_string, current_index):
    balance = 0
    i = current_index - 1
    while i >= 0:
        char = full_string[i]
        if char == '}':
            balance += 1
        elif char == '{':
            if balance > 0: balance -= 1
            else:
                cmd_end = i
                cmd_start = i - 1
                while cmd_start >= 0 and full_string[cmd_start].isspace(): cmd_start -= 1
                while cmd_start >= 0 and full_string[cmd_start].isalpha(): cmd_start -= 1
                return full_string[cmd_start+1 : cmd_end].strip() in TEXT_COMMANDS
        i -= 1
    return False

def replace_in_math_block(delimiter, content, state):
    # Regex Parts:
    # 1. Functions: 3+ letters followed by '('  --> Var(x)
    # 2. Acronyms: 3+ Uppercase letters        --> MSE, ANOVA, AXB
    word_pattern = r'(?<!\\)\b(?:([a-zA-Z]{3,})(?=\s*\()|([A-Z]{3,}))\b'

    def word_sub(m):
        word = m.group(0)
        if word in BLACKLIST: return word
        if is_inside_text_command(content, m.start()): return word

        # --- SMART FILTERING ---
        
        # If it matched because of the Function rule (followed by '(')
        # We always accept it (unless blacklisted)
        next_char_idx = m.end()
        is_function = False
        if next_char_idx < len(content):
            # Check if the next non-space char is '('
            rest = content[next_char_idx:]
            if rest.lstrip().startswith('('):
                is_function = True

        # If it is NOT a function (so it matched the Uppercase rule):
        if not is_function:
            # If it is exactly 3 letters, CHECK THE WHITELIST
            if len(word) == 3:
                if word not in KNOWN_ACRONYMS:
                    return word # Skip AXB, AXC, etc.
            
            # If 4+ letters, we generally assume it's an acronym (ANOVA)
            # (No change needed, we fall through to replacement)

        replacement = f"\\text{{{word}}}"

        if not state.interactive:
            state.count += 1
            return replacement

        print(f"\n{'-'*50}")
        preview = content.strip()
        match_idx = m.start()
        start_preview = max(0, match_idx - 20)
        end_preview = min(len(content), match_idx + 25)
        preview_snippet = "..." + content[start_preview:end_preview] + "..."
        
        print(f"CONTEXT: {delimiter} {preview_snippet} {delimiter}")
        print(f"Found  : {word}")
        print(f"Change : {replacement}")
        print(f"{'-'*50}")
        
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
                print("\nQuitting. No changes saved.")
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
    with open(file_path + ".bak", 'w', encoding='utf-8') as f: f.write(full_content)
    print(f"Backup created: {file_path}.bak")

    # Master Regex
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