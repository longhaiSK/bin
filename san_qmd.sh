#!/bin/bash

# Function to show usage
show_usage() {
    echo "Usage: $(basename "$0") [-h] <file1> [file2 ...]"
    echo ""
    echo "Description:"
    echo "  Sanitizes .qmd files by removing citations, fixing list spacing,"
    echo "  and wrapping math text."
    echo ""
    echo "Options:"
    echo "  -h    Show this help message and exit."
    echo ""
    echo "Examples:"
    echo "  $(basename "$0") my_file.qmd"
    echo "  $(basename "$0") *.qmd"
    exit 0
}

# Check if first argument is -h or if no arguments are provided
if [[ "$1" == "-h" ]] || [[ $# -eq 0 ]]; then
    show_usage
fi

# Loop through all arguments (files)
for FILE in "$@"; do
    # Check if the file actually exists
    if [ ! -f "$FILE" ]; then
        echo "Warning: '$FILE' not found. Skipping."
        continue
    fi

    echo "Processing $FILE..."

    echo "Remove [cite...] tags"
    regexrepl.py "$FILE" "\[cite(?:_start|:[^\]]+)\]" ""

    echo "Add blank lines before lists"
    regexrepl.py "$FILE" \
        '(?m)^(?!\s*(?:[-*]|\d+\.)\s)(.+)\n(?!\s*\n)(\s*(?:[-*]|\d+\.)\s)' \
        '\1\n\n\2'

    echo "Wrap math functions or acronyms with \text"
    wrap_math_text.py "$FILE"
    
    echo "Unify capitalization in headers"
    san_qmd_titles.py "$FILE"
done