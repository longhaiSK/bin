#!/usr/bin/env python3
"""
sanitize_filenames.py

Recursively sanitize filenames for Windows compatibility by:
- Replacing illegal characters  < > : " / \ | ? *  with '-'
- Trimming trailing spaces and dots
- Avoiding Windows reserved base names (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
- Resolving collisions by appending -2, -3, ...

Usage:
  # Dry run (preview only)
  python3 sanitize_filenames.py --root . --dry-run

  # Apply changes
  python3 sanitize_filenames.py --root .

  # More verbose
  python3 sanitize_filenames.py --root . --verbose
"""

import argparse
import os
import re
from typing import Set, Tuple

ILLEGAL_RE = re.compile(r'[<>:"/\\|?*]')
RESERVED = {
    "CON","PRN","AUX","NUL",
    *(f"COM{i}" for i in range(1,10)),
    *(f"LPT{i}" for i in range(1,10)),
}

def sanitize_component(name: str) -> str:
    """Apply Windows filename rules to a single path component."""
    # Replace illegal characters
    new = ILLEGAL_RE.sub('-', name)
    # Trim trailing spaces and dots (not allowed on Windows)
    new = new.rstrip(' .')
    # Avoid empty names
    if not new:
        new = "_"
    # Avoid reserved base names (case-insensitive)
    base, ext = os.path.splitext(new)
    if base.upper() in RESERVED:
        new = f"{base}-reserved{ext}"
    return new

def unique_in_dir(root: str, candidate: str, src_name: str,
                  planned: Set[str], existing: Set[str]) -> str:
    """
    Ensure 'candidate' is unique within 'root'. Consider both actual existing
    entries and names already planned for this directory.
    """
    if candidate == src_name:
        return candidate  # no change
    if candidate not in existing and candidate not in planned:
        return candidate

    base, ext = os.path.splitext(candidate)
    i = 2
    while True:
        alt = f"{base}-{i}{ext}"
        if alt == src_name:
            # If alt equals the source name, skip to next number
            i += 1
            continue
        if alt not in existing and alt not in planned:
            return alt
        i += 1

def plan_and_rename(root: str, names: list, dry_run: bool, verbose: bool) -> Tuple[int, int]:
    """
    In a single directory, plan unique target names and perform renames.
    Returns (renamed_count, skipped_count).
    """
    renamed = 0
