#!/usr/bin/env python3
import sys
import os
import re
import argparse # Import argparse for command-line argument parsing
from pypdf import PdfReader, PdfWriter

def read_config_from_file(config_file_path):
    """
    Reads the split configuration from a text file.
    Expected format per line: 'pages_spec: output_filename.pdf'
    Example: '1-5: proposal.pdf' or '6: reference.pdf'
    Returns a list of dictionaries [{'pages': '...', 'filename': '...'}, ...]
    """
    config = []
    try:
        with open(config_file_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'): # Skip empty lines and comments
                    continue

                # Use regex to capture pages and filename, allowing spaces around ':'
                # This regex correctly captures single numbers, ranges, or 'last'
                match = re.match(r'([^:]+?)\s*:\s*(.+\.pdf)\s*$', line, re.IGNORECASE)
                if match:
                    pages_spec = match.group(1).strip()
                    filename = match.group(2).strip()
                    config.append({'pages': pages_spec, 'filename': filename})
                else:
                    print(f"Warning: Skipping invalid line {line_num} in config file: '{line}'")
                    print("         Expected format: pages_spec: output_filename.pdf")
    except FileNotFoundError:
        print(f"Error: Configuration file not found at '{config_file_path}'")
        return None # Indicate error
    except Exception as e:
        print(f"Error reading configuration file '{config_file_path}': {e}")
        return None # Indicate error

    if not config:
        print(f"Warning: No valid configurations found in '{config_file_path}'.")
    return config

def parse_page_string(page_str, total_pages):
    """
    Parses a page string (e.g., "1-5", "6", "last") into a list of 0-based page indices.
    Returns a tuple: (list_of_indices, original_page_str_for_display)
    """
    indices = set()
    page_str_original = page_str # Keep original for display
    page_str = page_str.lower().strip()

    if page_str == 'last':
        if total_pages > 0:
            # Return index and the original string 'last' or actual page number
            display_str = f"{total_pages}" if total_pages > 0 else "last"
            return ([total_pages - 1], display_str)
        else:
            raise ValueError("Cannot get 'last' page from an empty PDF.")

    parts = page_str.split(',')
    display_parts = [] # To reconstruct display string accurately for ranges/singles
    for part in parts:
        part = part.strip()
        if not part:
            continue

        if '-' in part:
            # Handle range
            start_str, end_str = part.split('-', 1)
            try:
                start_num = int(start_str.strip())
                end_num = int(end_str.strip())
                # Convert 1-based page numbers to 0-based indices
                start_index = start_num - 1
                end_index = end_num - 1
                if start_index < 0 or end_index >= total_pages or start_index > end_index:
                    raise ValueError(f"Invalid page range '{part}'. Max page is {total_pages}.")
                indices.update(range(start_index, end_index + 1))
                display_parts.append(f"{start_num}-{end_num}") # Use original numbers for display
            except ValueError:
                raise ValueError(f"Invalid page range format: '{part}'")
        else:
            # Handle single page (This part already handles single numbers)
            try:
                page_num = int(part.strip())
                # Convert 1-based page number to 0-based index
                index = page_num - 1
                if index < 0 or index >= total_pages:
                     raise ValueError(f"Invalid page number '{page_num}'. Max page is {total_pages}.")
                indices.add(index)
                display_parts.append(f"{page_num}") # Use original number for display
            except ValueError:
                raise ValueError(f"Invalid page number format: '{part}'")

    # Sort indices to add pages in order
    sorted_indices = sorted(list(indices))
    if not sorted_indices:
         raise ValueError(f"Page string '{page_str_original}' resulted in no pages.")

    # Reconstruct display string
    display_str = ', '.join(display_parts)
    return (sorted_indices, display_str)


def split_pdf_from_config(input_pdf_path, config):
    """
    Splits the input PDF based on the provided configuration list.
    Prints a summary at the end.
    """
    created_files_summary = [] # Store info for final summary
    try:
        reader = PdfReader(input_pdf_path)
        total_pages = len(reader.pages)

        if total_pages == 0:
            print("Error: Input PDF appears to be empty.")
            return

        print(f"Input PDF '{input_pdf_path}' has {total_pages} pages.")

        for split_info in config:
            output_filename = split_info['filename']
            page_str_config = split_info['pages'] # Original string from config

            try:
                page_indices, display_page_str = parse_page_string(page_str_config, total_pages)
            except ValueError as e:
                print(f"Error parsing page spec '{page_str_config}' for '{output_filename}': {e}")
                continue # Skip this file but try others

            writer = PdfWriter()
            try:
                for index in page_indices:
                    writer.add_page(reader.pages[index])

                with open(output_filename, "wb") as f_out:
                    writer.write(f_out)
                # Record success for final summary
                created_files_summary.append({
                    'filename': output_filename,
                    'pages_display': display_page_str,
                    'num_pages': len(page_indices)
                })

            except IndexError:
                 print(f"Error: Page index out of range while creating '{output_filename}'. Check page numbers.")
            except Exception as e:
                 print(f"Error creating '{output_filename}': {e}")

    except FileNotFoundError:
        # This error is now handled before calling this function, but keep as fallback
        print(f"Error: Input file not found at '{input_pdf_path}'")
    except Exception as e:
        print(f"An unexpected error occurred during PDF processing: {e}")

    # --- Print Summary at the End ---
    if created_files_summary:
        print("\n--- Summary ---")
        max_page_len = 0
        if created_files_summary: # Avoid error if list is empty
             try: # Handle case where pages_display might be missing in error scenarios
                max_page_len = max(len(s['pages_display']) for s in created_files_summary)
             except KeyError:
                print("Warning: Could not determine page string length for summary alignment.")

        for summary_info in created_files_summary:
            # Pad the page string for alignment
            page_part = summary_info.get('pages_display', '?').ljust(max_page_len) # Default to '?' if missing
            print(f"Pages {page_part} -> {summary_info.get('filename', 'Unknown File')}")
        print("---------------")
    else:
        print("\nNo PDF files were created due to errors or empty config.")


if __name__ == "__main__":
    # --- Argument Parsing ---
    # Define the example config file content
    config_example = """
Example format for the split configuration file:
# Lines starting with # are comments and ignored.
# Blank lines are ignored.
# Page numbers are 1-based. Use '-' for ranges, ',' for multiple pages/ranges.
# Use 'last' for the last page.

1-5: proposal.pdf
6: references.pdf
7, 9-10: appendix_parts.pdf
last: budget.pdf
"""
    # Create the parser with the example in the epilog
    parser = argparse.ArgumentParser(
        description='Splits a PDF file based on a configuration file.',
        epilog=config_example, # Add example to help text
        formatter_class=argparse.RawDescriptionHelpFormatter # Ensure epilog formatting is preserved
    )
    parser.add_argument('input_pdf', help='Path to the input PDF file.')
    parser.add_argument('--splitconfig',
                        help='Path to the split configuration file. '
                             'Defaults to "<input_pdf_basename>-split.txt".')
    args = parser.parse_args()
    # -----------------------

    input_file = args.input_pdf

    # Check if input PDF exists
    if not os.path.exists(input_file):
        print(f"Error: Input PDF file not found at '{input_file}'")
        sys.exit(1)

    # Determine the configuration file name
    if args.splitconfig:
        config_file = args.splitconfig
    else:
        # Default config file name
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        config_file = f"{base_name}-split.txt"

    # Corrected print statement with valid f-string syntax
    print(f"Splitting '{input_file}' using configuration from: '{config_file}'")
    split_config = read_config_from_file(config_file)

    # Only proceed if config was read successfully and is not empty
    if split_config: # Check if list is not None and not empty
        split_pdf_from_config(input_file, split_config)
    elif split_config is None: # Explicit check for file read error
        # Error message already printed by read_config_from_file
        sys.exit(1)
    else: # Config file was empty or contained no valid lines
        print("Exiting as configuration file was empty or contained no valid split instructions.")
        sys.exit(0) # Not necessarily an error, just nothing to do

