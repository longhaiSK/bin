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
    "with", "from", "into", "onto", "upon", "as"
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