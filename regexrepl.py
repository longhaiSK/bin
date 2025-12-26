#!/bin/sh
""":"
exec "$(dirname "$0")/.venv/bin/python" "$0" "$@"
"""

import re
import sys
import os

def print_usage():
    print("Usage: ./regexrepl.py <filename> <regex_pattern> <replacement_string>")
    sys.exit(1)

# A class to hold the state of the "Replace All" flag
class Replacer:
    def __init__(self, replacement_template):
        self.replacement_template = replacement_template
        self.replace_all = False
        self.count = 0

    def replace_match(self, match):
        # Calculate what the replacement string looks like (resolving \1, \2, etc.)
        new_text = match.expand(self.replacement_template)
        original_text = match.group(0)

        # If user previously selected 'all', skip prompt
        if self.replace_all:
            self.count += 1
            return new_text

        # Display the potential change
        print(f"\n{'-'*40}")
        print(f"MATCH FOUND:")
        print(f"Original: {original_text!r}")
        print(f"Replace : {new_text!r}")
        print(f"{'-'*40}")

        while True:
            # Added [q]uit to the prompt
            choice = input("Replace? [y]es / [n]o / [a]ll / [q]uit: ").lower().strip()
            
            if choice == 'y':
                self.count += 1
                return new_text
            elif choice == 'n':
                return original_text # Return original, effectively making no change
            elif choice == 'a':
                self.replace_all = True
                self.count += 1
                return new_text
            elif choice == 'q':
                # Exit immediately. Since we exit here, the file writing step in main() is never reached.
                print("\nQuitting. No changes were saved to the file.")
                sys.exit(0)
            else:
                print("Please enter 'y', 'n', 'a', or 'q'.")

def main():
    # 1. Validate Arguments
    if len(sys.argv) < 4:
        print_usage()

    file_path = sys.argv[1]
    find_pattern = sys.argv[2]
    replace_string = sys.argv[3]

    # 2. Validate File
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        sys.exit(1)

    # 3. Create Backup
    backup_path = file_path + ".bak"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Backup created: {backup_path}")

        # 4. Perform Replacement with Interactive Callback
        replacer = Replacer(replace_string)
        
        # We use re.sub() but pass the class method instead of a string
        new_content = re.sub(find_pattern, replacer.replace_match, content)

        # 5. Write Result
        if replacer.count > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"\nSuccess! Modified {replacer.count} instances in '{file_path}'.")
        else:
            print("\nNo changes made.")

    except re.error as e:
        print(f"Regex Error: {e}")
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()