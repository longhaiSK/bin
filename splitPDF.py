#!/bin/sh
""":"
exec "$(dirname "$0")/.venv/bin/python" "$0" "$@"
"""


import sys
import os
import re
import argparse
from pypdf import PdfReader, PdfWriter

def read_split_config_from_file(config_file_path):
    """
    Reads the split configuration from a text file.
    Expected format:
    Line 1: Path to the input PDF file (e.g., /path/to/document.pdf)
    Line 2+: Split specification (e.g., 1-5: output1.pdf)
    Returns a tuple: (input_pdf_path, split_config_list, original_lines_list) or (None, None, None) on error.
    """
    input_pdf_path = None
    split_config = []
    original_lines = [] # Store original lines after the first line
    input_pdf_line = "" # Store the first line separately
    try:
        with open(config_file_path, 'r') as f:
            lines = f.readlines()

            # Process first line for input PDF path
            if not lines:
                print(f"Error: Configuration file '{config_file_path}' is empty.")
                return None, None, None
            input_pdf_line = lines[0].strip() # Store the first line
            if not input_pdf_line or not input_pdf_line.lower().endswith('.pdf'):
                print(f"Error: First line in '{config_file_path}' must be a valid PDF file path.")
                print(f"       Found: '{input_pdf_line}'")
                return None, None, None
            input_pdf_path = input_pdf_line # Assign if valid

            # Process subsequent lines for split configurations
            for line_num, line in enumerate(lines[1:], 2): # Start line count from 2
                original_line_text = line.strip()
                original_lines.append(original_line_text) # Store the raw line

                if not original_line_text or original_line_text.startswith('#'): # Skip processing for comments/blanks
                    continue

                # Use regex to capture pages_spec and filename
                match = re.match(r'([^:]+?)\s*:\s*(.+\.pdf)$', original_line_text, re.IGNORECASE)
                if match:
                    pages_spec = match.group(1).strip()
                    output_filename = match.group(2).strip()
                    if not pages_spec:
                         print(f"Warning: Page specification missing on line {line_num}. Skipping: '{original_line_text}'")
                         continue
                    # Store original line index relative to the 'original_lines' list (starts at 0)
                    split_config.append({'filename': output_filename, 'pages': pages_spec, 'line_index': len(original_lines) - 1})
                else:
                    print(f"Warning: Skipping invalid format on line {line_num}: '{original_line_text}'")
                    print("         Expected format: pages_spec: output_filename.pdf")

    except FileNotFoundError:
        print(f"Error: Configuration file not found at '{config_file_path}'")
        return None, None, None # Indicate error
    except Exception as e:
        print(f"Error reading configuration file '{config_file_path}': {e}")
        return None, None, None # Indicate error

    if not split_config:
        print(f"Warning: No valid split configurations found in '{config_file_path}' after the first line.")

    return input_pdf_path, split_config, original_lines

def parse_page_string(page_str, total_pages):
    """
    Parses a page string (e.g., "1-5", "6", "last") into a list of 0-based page indices
    and a user-friendly string representation.
    """
    indices = set()
    page_str_orig = page_str # Keep original for output
    page_str = page_str.lower().strip()
    friendly_parts = []

    if page_str == 'last':
        if total_pages > 0:
            indices.add(total_pages - 1)
            friendly_parts.append(str(total_pages)) # User-friendly is 1-based
        else:
            raise ValueError("Cannot get 'last' page from an empty PDF.")
    else:
        parts = page_str.split(',')
        for part in parts:
            part = part.strip()
            if not part:
                continue

            if part == 'last':
                if total_pages > 0:
                    indices.add(total_pages - 1)
                    friendly_parts.append(str(total_pages))
                else:
                    raise ValueError("Cannot use 'last' with an empty PDF.")
                continue

            if '-' in part:
                # Handle range
                start_str, end_str = part.split('-', 1)
                try:
                    start_user = int(start_str.strip())
                    end_user = int(end_str.strip())
                    start_idx = start_user - 1
                    end_idx = end_user - 1
                    if start_idx < 0 or end_idx >= total_pages or start_idx > end_idx:
                        raise ValueError(f"Invalid page range '{part}'. Max page is {total_pages}.")
                    indices.update(range(start_idx, end_idx + 1))
                    friendly_parts.append(f"{start_user}-{end_user}")
                except ValueError:
                    raise ValueError(f"Invalid page range format: '{part}'")
            else:
                # Handle single page
                try:
                    page_num_user = int(part.strip())
                    index = page_num_user - 1
                    if index < 0 or index >= total_pages:
                         raise ValueError(f"Invalid page number '{page_num_user}'. Max page is {total_pages}.")
                    indices.add(index)
                    friendly_parts.append(str(page_num_user))
                except ValueError:
                    raise ValueError(f"Invalid page number format: '{part}'")

    sorted_indices = sorted(list(indices))
    if not sorted_indices:
         raise ValueError(f"Page string '{page_str_orig}' resulted in no pages.")

    # Create a compact friendly string (e.g., 1-3, 5, 7-last)
    friendly_string = ", ".join(friendly_parts)

    return sorted_indices, friendly_string


def split_pdf_from_config(input_pdf_path, config, original_lines):
    """
    Splits the input PDF based on the configuration list.
    Prints status line by line based on original_lines.
    """
    files_created_count = 0
    total_pages_in_input = 0
    # Create a mapping from original line index to config entry for easy lookup
    config_map = {entry['line_index']: entry for entry in config}

    try:
        reader = PdfReader(input_pdf_path)
        total_pages_in_input = len(reader.pages)

        if total_pages_in_input == 0:
            print(f"Error: Input PDF '{input_pdf_path}' appears to be empty.")
            return

        print(f"Processing split instructions for '{input_pdf_path}' ({total_pages_in_input} pages):")

        for idx, line_text in enumerate(original_lines):
            if not line_text or line_text.startswith('#'):
                # print(line_text) # Optionally show comments/blanks
                continue

            entry = config_map.get(idx)
            if not entry:
                # This line had an invalid format during parsing
                print(line_text)
                print("  Error: Invalid line format.")
                continue

            # Valid config entry exists for this line
            output_filename = entry['filename']
            page_str = entry['pages']
            error_message = None
            num_split_pages = 0

            try:
                page_indices, friendly_page_str = parse_page_string(page_str, total_pages_in_input)

                if not page_indices:
                    raise ValueError("Page spec resulted in no pages.")

                writer = PdfWriter()
                for index in page_indices:
                    writer.add_page(reader.pages[index])

                with open(output_filename, "wb") as f_out:
                    writer.write(f_out)

                num_split_pages = len(page_indices)
                files_created_count += 1
                # Success!

            except ValueError as e:
                error_message = f"Parsing page spec '{page_str}': {e}"
            except IndexError:
                 error_message = "Page index out of range. Check page numbers."
            except Exception as e:
                 error_message = f"Creating '{output_filename}': {e}"

            # Print the original line and status
            if error_message:
                print(line_text)
                print(f"  Error: {error_message}")
            else:
                print(f"{line_text} ✓") # Append checkmark on success

    except FileNotFoundError:
        print(f"Error: Input PDF not found at '{input_pdf_path}'")
        return # Cannot proceed
    except Exception as e:
        print(f"An unexpected error occurred reading the input PDF: {e}")
        return # Cannot proceed

    # --- Final Summary ---
    if files_created_count > 0:
        print(f"\nSuccessfully created {files_created_count} PDF file(s).")
    else:
        print("\nNo output files were created.")
    # ---------------------

if __name__ == "__main__":
    # --- Argument Parsing ---
    config_example = """
Configuration file format:
- The first line MUST be the path to the input PDF file.
- Subsequent lines define the output files and page ranges.
- Format: page_spec: output_filename.pdf
- Lines starting with # and blank lines are ignored.
- Page numbers are 1-based. Use '-' for ranges, ',' for multiples, 'last'.

Example config file (e.g., 'split.txt'):
------------------------------
/path/to/my_document.pdf
1-5: file1.pdf
6: file2.pdf
last: file3.pdf
7-10, 12: file4.pdf
------------------------------
"""
    parser = argparse.ArgumentParser(
        description='Splits a PDF file into multiple files based on a configuration file.',
        epilog=config_example,
        formatter_class=argparse.RawDescriptionHelpFormatter # Preserves formatting in epilog
    )
    # Changed to a single positional argument for the config file
    parser.add_argument('config_file',
                        help='Path to the split configuration file (e.g., split.txt).')
    args = parser.parse_args()
    # -----------------------

    config_file_path = args.config_file

    print(f"Reading split configuration from: '{config_file_path}'")
    input_pdf, split_config, original_config_lines = read_split_config_from_file(config_file_path)

    # Proceed only if both input_pdf and split_config were successfully read
    if input_pdf is not None:
        # Pass original lines to the split function
        split_pdf_from_config(input_pdf, split_config, original_config_lines)
    else:
        # Error message already printed by read_split_config_from_file
        sys.exit(1)

