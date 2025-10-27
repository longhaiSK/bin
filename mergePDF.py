#!/usr/bin/env python3
import sys
import os
import re
import argparse
from pypdf import PdfReader, PdfWriter, PageRange # No change needed here

def read_merge_config_from_file(config_file_path):
    """
    Reads the merge configuration from a text file.
    Expected format per line: 'input_filename.pdf: [pages_spec]'
    Example: 'report.pdf: 1-5' or 'appendix.pdf:' (all pages)
    Returns a list of dictionaries [{'filename': '...', 'pages': '... or None'}, ...]
    """
    config = []
    try:
        with open(config_file_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'): # Skip empty lines and comments
                    continue

                # Use regex to capture filename and optional pages_spec
                # Allows spaces around ':' and handles missing pages_spec
                match = re.match(r'(.+\.pdf)\s*(?::\s*(.*?)\s*)?$', line, re.IGNORECASE)
                if match:
                    filename = match.group(1).strip()
                    pages_spec = match.group(2).strip() if match.group(2) else None # None if pages_spec is missing
                    config.append({'filename': filename, 'pages': pages_spec})
                else:
                    print(f"Warning: Skipping invalid line {line_num} in config file: '{line}'")
                    print("         Expected format: filename.pdf: [pages_spec] (pages_spec is optional)")
    except FileNotFoundError:
        print(f"Error: Configuration file not found at '{config_file_path}'")
        return None # Indicate error
    except Exception as e:
        print(f"Error reading configuration file '{config_file_path}': {e}")
        return None # Indicate error

    if not config:
        print(f"Warning: No valid configurations found in '{config_file_path}'.")
    return config

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
            return [] # Empty list for empty PDF

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

        if part == 'last': # Handle 'last' within a list (less common, but possible)
             if total_pages > 0:
                 indices.add(total_pages - 1)
             else:
                 raise ValueError("Cannot use 'last' with an empty PDF.")
             continue

        if '-' in part:
            # Handle range
            start_str, end_str = part.split('-', 1)
            try:
                # Convert 1-based page numbers to 0-based indices
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
                # Convert 1-based page number to 0-based index
                index = page_num - 1
                if index < 0 or index >= total_pages:
                     raise ValueError(f"Invalid page number '{page_num}'. Max page is {total_pages}.")
                indices.add(index)
            except ValueError:
                raise ValueError(f"Invalid page number format: '{part}'")

    # Sort indices to add pages in order
    sorted_indices = sorted(list(indices))
    if not sorted_indices:
         raise ValueError(f"Page string '{page_str}' resulted in no pages.")
    return sorted_indices

def merge_pdfs_from_config(config, output_pdf_path):
    """
    Merges pages from multiple PDFs based on the configuration list.
    Writes the merged output to output_pdf_path.
    Adds bookmarks (TOC) for each input file.
    """
    merger = PdfWriter()
    total_pages_merged = 0
    print(f"Starting merge process. Output will be saved to '{output_pdf_path}'.")

    for entry in config:
        input_filename = entry['filename']
        page_spec = entry['pages'] # This can be None

        try:
            print(f"  Processing '{input_filename}' (Pages: {page_spec if page_spec else 'All'})... ", end="")
            reader = PdfReader(input_filename)
            num_input_pages = len(reader.pages)
            if num_input_pages == 0:
                print("Skipped (empty PDF).")
                continue

            page_indices = parse_merge_page_string(page_spec, num_input_pages)

            if not page_indices:
                print("Skipped (no pages selected or specified).")
                continue

            # --- Add Bookmark/TOC Entry ---
            # Get the current page number *before* adding pages (0-based)
            bookmark_target_page_index = len(merger.pages)
            # Get the base filename without extension for the title
            bookmark_title = os.path.splitext(os.path.basename(input_filename))[0]
            # Add the outline item (bookmark)
            merger.add_outline_item(bookmark_title, bookmark_target_page_index)
            # --- End Bookmark ---

            # Add the selected pages
            for index in page_indices:
                 merger.add_page(reader.pages[index])

            num_added = len(page_indices)
            total_pages_merged += num_added
            print(f"Added {num_added} pages.")

        except FileNotFoundError:
            print(f"Error: Input file '{input_filename}' not found. Skipping.")
        except ValueError as e:
            print(f"Error parsing page spec for '{input_filename}': {e}. Skipping.")
        except Exception as e:
            print(f"Error processing '{input_filename}': {e}. Skipping.")

    # Write the final merged PDF
    if total_pages_merged > 0:
        try:
            with open(output_pdf_path, "wb") as f_out:
                merger.write(f_out)
            print(f"\nSuccessfully merged {total_pages_merged} pages with bookmarks into '{output_pdf_path}'.") # Updated message
        except Exception as e:
            print(f"\nError writing output file '{output_pdf_path}': {e}")
    else:
        print("\nNo pages were merged. Output file not created.")

    merger.close() # Close the writer object

if __name__ == "__main__":
    # --- Argument Parsing ---
    config_example = """
Example format for the merge configuration file:
# Lines starting with # are comments and ignored.
# Blank lines are ignored.
# Format: input_file.pdf: [page_spec]
# If page_spec is omitted, all pages are included.
# Page numbers are 1-based. Use '-' for ranges, ',' for multiples, 'last'.

title_page.pdf: 1
main_report.pdf: 1-10
appendix_a.pdf:
appendix_b.pdf: 3, 5-last
"""
    parser = argparse.ArgumentParser(
        description='Merges pages from multiple PDF files based on a configuration file, adding bookmarks for each input file.', # Updated description
        epilog=config_example,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    # Changed config to be a positional argument
    parser.add_argument('config_file',
                        help='Path to the merge configuration file (e.g., mergePDF.txt).')
    # Kept output as an optional argument
    parser.add_argument('--output',
                        help='Path for the final merged PDF file (default: derived from config file name, e.g., input.pdf).')
    args = parser.parse_args()
    # -----------------------

    config_file = args.config_file

    # Determine default output filename based on config filename
    config_basename = os.path.splitext(os.path.basename(config_file))[0]
    default_output_file = f"{config_basename}.pdf"

    # Use the provided output filename if given, otherwise use the default
    output_file = args.output if args.output else default_output_file

    print(f"Reading merge configuration from: '{config_file}'")
    merge_config = read_merge_config_from_file(config_file)

    if merge_config: # Check if list is not None and not empty
        merge_pdfs_from_config(merge_config, output_file)
    elif merge_config is None: # Explicit check for file read error
        sys.exit(1)
    else: # Config file was empty or contained no valid lines
        print("Exiting as configuration file was empty or contained no valid merge instructions.")
        sys.exit(0)

