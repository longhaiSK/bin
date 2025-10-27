#!/usr/bin/env python3
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
    Returns a tuple: (input_pdf_path, split_config_list) or (None, None) on error.
    """
    input_pdf_path = None
    split_config = []
    try:
        with open(config_file_path, 'r') as f:
            lines = f.readlines()

            # Process first line for input PDF path
            if not lines:
                print(f"Error: Configuration file '{config_file_path}' is empty.")
                return None, None
            input_pdf_path = lines[0].strip()
            if not input_pdf_path or not input_pdf_path.lower().endswith('.pdf'):
                print(f"Error: First line in '{config_file_path}' must be a valid PDF file path.")
                print(f"       Found: '{input_pdf_path}'")
                return None, None

            # Process subsequent lines for split configurations
            for line_num, line in enumerate(lines[1:], 2): # Start line count from 2
                line = line.strip()
                if not line or line.startswith('#'): # Skip empty lines and comments
                    continue

                # Use regex to capture pages_spec and filename
                # Allows spaces around ':'
                match = re.match(r'([^:]+?)\s*:\s*(.+\.pdf)$', line, re.IGNORECASE)
                if match:
                    pages_spec = match.group(1).strip()
                    output_filename = match.group(2).strip()
                    if not pages_spec:
                         print(f"Warning: Page specification missing on line {line_num}. Skipping: '{line}'")
                         continue
                    split_config.append({'filename': output_filename, 'pages': pages_spec})
                else:
                    print(f"Warning: Skipping invalid line {line_num} in config file: '{line}'")
                    print("         Expected format: pages_spec: output_filename.pdf")

    except FileNotFoundError:
        print(f"Error: Configuration file not found at '{config_file_path}'")
        return None, None # Indicate error
    except Exception as e:
        print(f"Error reading configuration file '{config_file_path}': {e}")
        return None, None # Indicate error

    if not split_config:
        print(f"Warning: No valid split configurations found in '{config_file_path}' after the first line.")
        # Proceed even if no splits, maybe user just wanted to check input file path
    return input_pdf_path, split_config

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


def split_pdf_from_config(input_pdf_path, config):
    """
    Splits the input PDF based on the provided configuration list.
    """
    created_files_summary = []
    try:
        reader = PdfReader(input_pdf_path)
        total_pages = len(reader.pages)

        if total_pages == 0:
            print("Error: Input PDF appears to be empty.")
            return

        print(f"Input PDF '{input_pdf_path}' has {total_pages} pages.")
        print(f"Processing {len(config)} split configurations...")

        for split_info in config:
            output_filename = split_info['filename']
            page_str = split_info['pages']
            page_indices = []
            friendly_page_str = page_str # Default in case parsing fails

            try:
                page_indices, friendly_page_str = parse_page_string(page_str, total_pages)
            except ValueError as e:
                print(f"  Error parsing page spec '{page_str}' for '{output_filename}': {e}. Skipping.")
                continue # Skip this file but try others

            if not page_indices:
                print(f"  Skipping '{output_filename}' as page spec '{page_str}' resulted in no pages.")
                continue

            writer = PdfWriter()
            try:
                for index in page_indices:
                    writer.add_page(reader.pages[index])

                # Removed check for existing file
                # if os.path.exists(output_filename):
                #    print(f"  Note: Overwriting existing file '{output_filename}'.")

                with open(output_filename, "wb") as f_out:
                    writer.write(f_out)
                # Store info for final summary
                created_files_summary.append({
                    'filename': output_filename,
                    'pages_str': friendly_page_str,
                    'count': len(page_indices)
                })

            except IndexError:
                 print(f"  Error: Page index out of range while creating '{output_filename}'. Check page numbers. Skipping.")
            except Exception as e:
                 print(f"  Error creating '{output_filename}': {e}. Skipping.")

    except FileNotFoundError:
        print(f"Error: Input file not found at '{input_pdf_path}'")
        return # Cannot proceed
    except Exception as e:
        print(f"An unexpected error occurred reading the input PDF: {e}")
        return # Cannot proceed

    # --- Final Summary ---
    print("\n--- Split Summary ---")
    if created_files_summary:
        # Determine max length for alignment
        max_page_len = max(len(s['pages_str']) for s in created_files_summary)
        max_file_len = max(len(s['filename']) for s in created_files_summary)

        for summary in created_files_summary:
            pages_part = f"Pages {summary['pages_str']}".ljust(max_page_len + 6) # +6 for "Pages "
            file_part = summary['filename'].ljust(max_file_len)
            count_part = f"({summary['count']} page{'s' if summary['count'] != 1 else ''})"
            print(f"{pages_part} -> {file_part} {count_part}")
        print(f"\nSuccessfully created {len(created_files_summary)} PDF file(s).")
    else:
        print("No output files were created.")
    # ---------------------

if __name__ == "__main__":
    # --- Argument Parsing ---
    # Updated config_example with generic filenames
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
    input_pdf, split_config = read_split_config_from_file(config_file_path)

    # Proceed only if both input_pdf and split_config were successfully read
    # read_split_config_from_file returns (None, None) on file read error
    # It returns (path, []) if only input PDF path is found but no splits
    if input_pdf is not None:
        if split_config: # Check if the list of splits is not empty
            split_pdf_from_config(input_pdf, split_config)
        else:
             print("Configuration file parsed, but no valid split instructions found after the first line. No files were split.")
             sys.exit(0) # Not an error, just nothing to do
    else:
        # Error message already printed by read_split_config_from_file
        sys.exit(1)

