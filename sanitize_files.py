#!/usr/bin/env python3
r"""
sanitize_filenames.py

Recursively sanitize filenames for Windows compatibility by:
- Replacing illegal characters  < > : " / \ | ? *  with '-'
- Trimming trailing spaces and dots
- Avoiding Windows reserved base names (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
- Resolving collisions by appending -2, -3, ...
"""

import argparse
import os
import re
from typing import Set, Tuple, List

ILLEGAL_RE = re.compile(r'[<>:"/\\|?*]')
RESERVED = {
    "CON","PRN","AUX","NUL",
    *(f"COM{i}" for i in range(1,10)),
    *(f"LPT{i}" for i in range(1,10)),
}

def print_usage_script(prog: str) -> None:
    msg = f"""\
Usage:
  # Default: preview (dry-run + show-dest)
  {prog} [--root PATH]

  # Perform actual renames (no preview)
  {prog} --root PATH --do

  # Show concise usage
  {prog} --usage

Description:
  Recursively sanitize filenames under PATH (default: current directory) to be Windows-compatible.

Default behavior:
  • With no flags, runs a dry-run and prints mappings 'src -> dst' for items that would change.

Options:
  --root PATH   Root directory to process (default: ".")
  --do          Apply changes (no preview). Prints each rename as it happens.
  --usage       Show this concise usage and exit.

Rules applied:
  • Replace illegal chars  < > : " / \\ | ? *  with '-'
  • Trim trailing spaces and dots
  • Avoid reserved base names (CON, PRN, AUX, NUL, COM1–9, LPT1–9)
  • Resolve collisions by appending -2, -3, ...
"""
    print(msg)

def sanitize_component(name: str) -> str:
    """Apply Windows filename rules to a single path component."""
    new = ILLEGAL_RE.sub('-', name)      # replace illegal characters
    new = new.rstrip(' .')               # trim trailing spaces/dots
    if not new:
        new = "_"                        # avoid empty names
    base, ext = os.path.splitext(new)
    if base.upper() in RESERVED:         # avoid reserved basenames
        new = f"{base}-reserved{ext}"
    return new

def unique_in_dir(candidate: str, src_name: str,
                  planned: Set[str], existing: Set[str]) -> str:
    """Ensure 'candidate' is unique within a directory (consider planned+existing)."""
    if candidate == src_name:
        return candidate
    if candidate not in existing and candidate not in planned:
        return candidate
    base, ext = os.path.splitext(candidate)
    i = 2
    while True:
        alt = f"{base}-{i}{ext}"
        if alt == src_name:
            i += 1
            continue
        if alt not in existing and alt not in planned:
            return alt
        i += 1

def plan_changes_for_dir(root: str, names: List[str]) -> List[tuple]:
    """Return a list of (src_path, dst_path) for items that need renaming in this dir."""
    changes = []
    existing = set(names)
    planned: Set[str] = set()

    for name in names:
        new = sanitize_component(name)
        if new == name:
            planned.add(name)  # reserve current name to avoid collisions
            continue
        unique = unique_in_dir(new, name, planned, existing)
        planned.add(unique)
        src = os.path.join(root, name)
        dst = os.path.join(root, unique)
        if src != dst:
            changes.append((src, dst))
    return changes

def main():
    ap = argparse.ArgumentParser(
        description="Sanitize filenames for Windows compatibility (recursive).",
        add_help=True
    )
    ap.add_argument("--root", default=".", help='Root directory to process (default: ".").')
    ap.add_argument("--do", action="store_true",
                    help="Apply changes (no preview). Default is dry-run with mapping output.")
    ap.add_argument("--usage", action="store_true",
                    help="Show concise usage with examples and exit.")
    args = ap.parse_args()

    if args.usage:
        print_usage_script(os.path.basename(__file__) or "sanitize_filenames.py")
        raise SystemExit(0)

    rootdir = os.path.abspath(args.root)
    if not os.path.isdir(rootdir):
        raise SystemExit(f"Not a directory: {rootdir}")

    total_changes = 0
    total_errors = 0

    # Walk bottom-up so children are renamed before parent directories
    for root, dirnames, filenames in os.walk(rootdir, topdown=False):
        names = dirnames + filenames
        changes = plan_changes_for_dir(root, names)

        if not args.do:
            # Default: dry-run + show-dest
            for src, dst in changes:
                print(f"{src} -> {dst}")
            total_changes += len(changes)
        else:
            # Perform renames, no preview
            for src, dst in changes:
                try:
                    os.rename(src, dst)
                    print(f"{src} -> {dst}")
                    total_changes += 1
                except Exception as e:
                    print(f"[ERROR] {src} -> {dst} : {e}")
                    total_errors += 1

    if not args.do:
        print(f"\nSummary (dry-run): {total_changes} items would be renamed.")
    else:
        print(f"\nSummary: {total_changes} items renamed, {total_errors} errors.")

if __name__ == "__main__":
    main()
