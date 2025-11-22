#!/usr/bin/env python3

import sys
import re
import shutil
import os
import argparse

# List of "small words" that should remain lowercase (unless they are the first/last word)
# Only used for Title Case
SMALL_WORDS = {
    "a", "an", "the", "and", "but", "or", "nor", "for", "yet", "so",
    "at", "by", "for", "in", "of", "on", "to", "up", "via", "vs", "vs.",
    "with", "from", "into", "onto", "upon", "as", "your"
}

def to_title_case(text):
    """
    Standard Title Case: Capitalize first/last, lowercase small words, 
    capitalize others, preserve acronyms.
    """
    words = text.split()
    if not words:
        return text

    new_words = []
    
    for i, word in enumerate(words):
        # clean_word strips punctuation for checking logic
        clean_word = word.strip(".,:;?!'\"()[]{}").lower()
        
        # 1. Acronym Check
        if word.isupper() and len(word) > 1:
            new_words.append(word)
            continue
            
        # 2. First or Last word -> Capitalize
        if i == 0 or i == len(words) - 1:
            new_words.append(word.capitalize())
        
        # 3. Small word -> Lowercase
        elif clean_word in SMALL_WORDS:
            new_words.append(word.lower())
            
        # 4. Regular word -> Capitalize
        else:
            new_words.append(word.capitalize())

    return " ".join(new_words)

def to_lowercase_style(text):
    """
    Sentence Case: Capitalize first word, preserve acronyms, 
    lowercase everything else.
    """
    words = text.split()
    if not words:
        return text

    new_words = []
    
    for i, word in enumerate(words):
        # 1. Acronym Check (Keep if all caps and length > 1)
        if word.isupper() and len(word) > 1:
            new_words.append(word)
            
        # 2. First word -> Capitalize (if not an acronym)
        elif i == 0:
            new_words.append(word.capitalize())
            
        # 3. All other words -> Lowercase
        else:
            new_words.append(word.lower())
            
    return " ".join(new_words)

def process_qmd_file(file_path, backup=False, style="titlecase"):
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return

    # Create a backup of the original file if requested
    backup_path = f"{file_path}.bak"
    
    if backup:
        try:
            shutil.copy2(file_path, backup_path)
            print(f"Backup created: {backup_path}")
        except IOError as e:
            print(f"Error creating backup: {e}")
            return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    new_lines = []
    
    # Regex to capture: 
    # Group 1: The hashtags (#, ##, etc)
    # Group 2: The text content
    # Group 3: Optional attributes like {#id} or {.class}
    header_pattern = re.compile(r'^(#+)\s+(.*?)(?:\s+(\{.*\})\s*)?$')

    for line in lines:
        match = header_pattern.match(line)
        
        if match:
            hashes = match.group(1)
            content = match.group(2)
            attributes = match.group(3) if match.group(3) else ""
            
            # Select the conversion method based on argument
            if style == "lowercase":
                new_content = to_lowercase_style(content)
            else:
                new_content = to_title_case(content)
            
            # Reconstruct the line
            attr_spacer = " " if attributes else ""
            new_line = f"{hashes} {new_content}{attr_spacer}{attributes}\n"
            new_lines.append(new_line)
        else:
            new_lines.append(line)

    # Overwrite the original file
    output_path = file_path
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    if backup:
        print(f"Success! File updated to {style} (Original saved as {backup_path})")
    else:
        print(f"Success! File updated to {style}.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert QMD file headers to Title Case or Lowercase.")
    parser.add_argument("filename", help="The QMD file to process")
    parser.add_argument("-b", "--backup", action="store_true", help="Create a backup of the original file")
    parser.add_argument("--to", choices=['titlecase', 'lowercase'], default='titlecase', 
                        help="Case style: 'titlecase' or 'lowercase'")
    
    args = parser.parse_args()
    
    process_qmd_file(args.filename, backup=args.backup, style=args.to)