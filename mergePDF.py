#!/bin/sh
""":"
exec "$(dirname "$0")/.venv/bin/python" "$0" "$@"
"""

import sys
import os
import re
import argparse
from pypdf import PdfReader, PdfWriter, PageRange  # No change needed here

# --- Console colors (ANSI). Optionally enable on Windows with colorama ---
RESET  = "\033[0m"
BOLD   = "\033[1m"
RED    = "\033[31m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"

def color(s, c): return f"{c}{s}{RESET}"
def red(s):   return color(s, RED)
def green(s): return color(s, GREEN)
def yellow(s):return color(s, YELLOW)

try:
    # If available, makes ANSI colors work reliably on Windows terminals.
    import colorama
    colorama.init()
except Exception:
    pass

# --- Global logs for end-of-run summary ---
ERROR_LOG: list[str] = []
WARN_LOG:  list[str] = []

def read_merge_config_from_file(config_file_path):
    """
    Reads the merge configuration from a text file.
    Expected format per line: 'input_filename.pdf [(Bookmark Title)]: [pages_spec]'
    Returns (config, original_lines)
    """
    config = []
    original_lines = []  # Store original lines to iterate through later for printing
    try:
        with open(config_file_path, 'r') as f:
            lines = f.readlines()
            for line_num, line in enumerate(lines, 1):
                original_line_text = line.strip()
                original_lines.append(original_line_text)  # Store the raw line

                if not original_line_text or original_line_text.startswith('#'):  # Skip processing for comments/blanks
                    continue

                # Regex to capture filename, optional bookmark title in (), and optional pages_spec
                match = re.match(
                    r'(.+\.pdf)\s*(?:\(\s*(.*?)\s*\))?\s*(?::\s*(.*?)\s*)?$',
                    original_line_text,
                    re.IGNORECASE
                )

                if match:
                    filename = match.group(1).strip()
                    bookmark_title = match.group(2).strip() if match.group(2) else None
                    pages_spec = match.group(3).strip() if match.group(3) else None
                    config.append({
                        'filename': filename,
                        'bookmark': bookmark_title,
                        'pages': pages_spec,
                        'line_index': len(original_lines) - 1
                    })
                else:
                    msg = f"Invalid format on line {line_num}: '{original_line_text}'. Skipping."
                    print(yellow(f"Warning: {msg}"))
                    WARN_LOG.append(f"[CONFIG] {msg}")

    except FileNotFoundError:
        msg = f"Configuration file not found at '{config_file_path}'"
        print(red(f"Error: {msg}"))
        ERROR_LOG.append(f"[CONFIG] {msg}")
        return None, None
    except Exception as e:
        msg = f"Error reading configuration file '{config_file_path}': {e}"
        print(red(f"Error: {msg}"))
        ERROR_LOG.append(f"[CONFIG] {msg}")
        return None, None

    if not config:
        w = f"No valid configurations found in '{config_file_path}'."
        print(yellow(f"Warning: {w}"))
        WARN_LOG.append(f"[CONFIG] {w}")

    return config, original_lines

# --- parse_merge_page_string remains the same (adds red errors via caller) ---
def parse_merge_page_string(page_str, total_pages):
    """
    Parses a page string (e.g., "1-5", "6", "last") or None (all pages)
    into a list of 0-based page indices.
    Handles 'last'.
    Returns a list of 0-based indices.
    """
    indices = set()

    # Handle the "all pages" case if page_str is None or empty
    if page_str is None or not page_str.strip():
        if total_pages > 0:
            return list(range(total_pages))
        else:
            return []  # Empty list for empty PDF

    page_str = page_str.lower().strip()

    # Handle 'last' specifically first if it's the only spec
    if page_str == 'last':
        if total_pages > 0:
            return [total_pages - 1]
        else:
            raise ValueError("Cannot get 'last' page from an empty PDF.")

    parts = page_str.split(',')
    for part in parts:
        part = part.strip()
        if not part:
            continue

        if part == 'last':  # Handle 'last' within a list
            if total_pages > 0:
                indices.add(total_pages - 1)
            else:
                raise ValueError("Cannot use 'last' with an empty PDF.")
            continue

        if '-' in part:
            # Handle range
            start_str, end_str = part.split('-', 1)
            try:
                start = int(start_str.strip()) - 1
                end = int(end_str.strip()) - 1
                if start < 0 or end >= total_pages or start > end:
                    raise ValueError(f"Invalid page range '{part}'. Max page is {total_pages}.")
                indices.update(range(start, end + 1))
            except ValueError:
                raise ValueError(f"Invalid page range format: '{part}'")
        else:
            # Handle single page
            try:
                page_num = int(part.strip())
                index = page_num - 1
                if index < 0 or index >= total_pages:
                    raise ValueError(f"Invalid page number '{page_num}'. Max page is {total_pages}.")
                indices.add(index)
            except ValueError:
                raise ValueError(f"Invalid page number format: '{part}'")

    sorted_indices = sorted(list(indices))
    if not sorted_indices:
        raise ValueError(f"Page string '{page_str}' resulted in no pages.")
    return sorted_indices
# --- End of parse_merge_page_string ---

def merge_pdfs_from_config(config, original_lines, output_pdf_path):
    """
    Merges pages from multiple PDFs based on the configuration list.
    Writes the merged output to output_pdf_path.
    Adds bookmarks (TOC) for each input file using specified or default titles.
    Prints status line by line based on original_lines.
    """
    merger = PdfWriter()
    total_pages_merged = 0
    # Map from original line index to config entry for easy lookup
    config_map = {entry['line_index']: entry for entry in config}

    print(f"Processing merge instructions for output '{output_pdf_path}':")

    for idx, line_text in enumerate(original_lines):
        if not line_text or line_text.startswith('#'):
            continue

        entry = config_map.get(idx)
        if not entry:
            # This line was invalid during parsing
            print(line_text)
            err = "Invalid line format."
            print(red(f"  Error: {err}"))
            ERROR_LOG.append(f"[LINE {idx+1}] {err}: {line_text}")
            continue

        input_filename = entry['filename']
        page_spec = entry['pages']  # Can be None
        custom_bookmark_title = entry['bookmark']  # Can be None
        error_message = None

        try:
            reader = PdfReader(input_filename)
            num_input_pages = len(reader.pages)
            if num_input_pages == 0:
                raise ValueError("Input PDF is empty.")

            page_indices = parse_merge_page_string(page_spec, num_input_pages)

            if not page_indices:
                raise ValueError("No pages selected or specified.")

            # --- Add Bookmark/TOC Entry ---
            bookmark_target_page_index = len(merger.pages)
            bookmark_title = (
                custom_bookmark_title
                if custom_bookmark_title
                else os.path.splitext(os.path.basename(input_filename))[0]
            )
            merger.add_outline_item(bookmark_title, bookmark_target_page_index)
            # --- End Bookmark ---

            # Add the selected pages
            for index in page_indices:
                merger.add_page(reader.pages[index])

            num_added = len(page_indices)
            total_pages_merged += num_added

        except FileNotFoundError:
            error_message = f"Input file '{input_filename}' not found."
        except ValueError as e:
            error_message = f"Parsing page spec '{page_spec}': {e}"
        except Exception as e:
            error_message = f"Processing '{input_filename}': {e}"

        # Print the original line and status
        if error_message:
            print(line_text)
            print(red(f"  Error: {error_message}"))
            ERROR_LOG.append(f"[LINE {idx+1}] {error_message} | {line_text}")
        else:
            # Success line with green checkmark
            print(f"{line_text} {green('✓')}")

    # Write the final merged PDF
    if total_pages_merged > 0:
        try:
            with open(output_pdf_path, "wb") as f_out:
                merger.write(f_out)
            print(f'\n"{output_pdf_path}" with {total_pages_merged} pages created!')
        except Exception as e:
            msg = f"Error writing output file '{output_pdf_path}': {e}"
            print(red(f"\n{msg}"))
            ERROR_LOG.append(f"[WRITE] {msg}")
    else:
        msg = "No pages were merged. Output file not created."
        print(red(f"\n{msg}"))
        ERROR_LOG.append(f"[MERGE] {msg}")

    merger.close()

    # --- Bottom summary (errors and warnings) ---
    print("\n" + BOLD + "Summary" + RESET)
    if WARN_LOG:
        print(yellow(f"Warnings ({len(WARN_LOG)}):"))
        for w in WARN_LOG:
            print(yellow(f"  - {w}"))
    if ERROR_LOG:
        print(red(f"Errors ({len(ERROR_LOG)}):"))
        for e in ERROR_LOG:
            print(red(f"  - {e}"))
    if not WARN_LOG and not ERROR_LOG:
        print(green("No warnings or errors. All good! ") + green("✓"))

if __name__ == "__main__":
    # --- Argument Parsing ---
    config_example = """
Example format for the merge configuration file:
# Lines starting with # are comments and ignored.
# Blank lines are ignored.
# Format: input_file.pdf [(Bookmark Title)]: [page_spec]
# If (Bookmark Title) is omitted, the base filename is used.
# If page_spec is omitted, all pages are included.
# Page numbers are 1-based. Use '-' for ranges, ',' for multiples, 'last'.

title_page.pdf (Title): 1
main_report.pdf (Proposal Body): 1-10
appendix_a.pdf:
appendix_b.pdf (Data Appendix): 3, 5-last
references.pdf (Bibliography)
"""
    parser = argparse.ArgumentParser(
        description='Merges pages from multiple PDF files based on a configuration file, adding bookmarks for each input file.',
        epilog=config_example,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('config_file',
                        help='Path to the merge configuration file (e.g., mergePDF.txt).')
    parser.add_argument('--output',
                        help='Path for the final merged PDF file (default: derived from config file name, e.g., input.pdf).')
    args = parser.parse_args()
    # -----------------------

    config_file = args.config_file
    config_basename = os.path.splitext(os.path.basename(config_file))[0]
    default_output_file = f"{config_basename}.pdf"
    output_file = args.output if args.output else default_output_file

    print(f"Reading merge configuration from: '{config_file}'")
    # Read both parsed config and original lines
    merge_config, original_config_lines = read_merge_config_from_file(config_file)

    if merge_config is not None and original_config_lines is not None:
        # Pass original lines to the merge function
        merge_pdfs_from_config(merge_config, original_config_lines, output_file)
    elif merge_config is None and original_config_lines is None:
        # Error during file reading
        sys.exit(1)
    else:
        # Config file might be empty but readable
        print(yellow("Exiting as configuration file was empty or contained no valid merge instructions."))
        sys.exit(0)
