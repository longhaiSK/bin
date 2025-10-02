#!/usr/bin/env python3
r"""
sanitize_filenames.py

Recursively sanitize filenames for Windows compatibility by:
- Replacing illegal characters  < > : " / \ | ? *  with '-'
- Trimming trailing spaces and dots
- Avoiding Windows reserved base names (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
- Resolving collisions by appending -2, -3, ...

Usage:
  # Preview: print only items that WOULD change (one path per line)
  python3 sanitize_filenames.py --root . --dry-run

  # Preview with mappings (src -> dst)
  python3 sanitize_filenames.py --root . --dry-run --show-dest

  # Apply changes (prints only items actually renamed)
  python3 sanitize_filenames.py --root .
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
            planned.add(name)  # reserve its current name to avoid collisions
            continue
        unique = unique_in_dir(new, name, planned, existing)
        planned.add(unique)
        src = os.path.join(root, name)
        dst = os.path.join(root, unique)
        if src != dst:
            changes.append((src, dst))
    return changes

def main():
    ap = argparse.ArgumentParser(description="Sanitize filenames for Windows compatibility.")
    ap.add_argument("--root", default=".", help="Root directory to process (default: current dir).")
    ap.add_argument("--dry-run", action="store_true",
                    help="Preview changes without renaming anything.")
    ap.add_argument("--show-dest", action="store_true",
                    help="When used with --dry-run, show 'src -> dst' mappings instead of just src.")
    args = ap.parse_args()

    rootdir = os.path.abspath(args.root)
    if not os.path.isdir(rootdir):
        raise SystemExit(f"Not a directory: {rootdir}")

    total_changes = 0
    total_errors = 0

    # Walk bottom-up so children are renamed before parent directories
    for root, dirnames, filenames in os.walk(rootdir, topdown=False):
        names = dirnames + filenames
        changes = plan_changes_for_dir(root, names)
        if args.dry_run:
            for src, dst in changes:
                if args.show_dest:
                    print(f"{src} -> {dst}")
                else:
                    print(src)
        else:
            for src, dst in changes:
                try:
                    os.rename(src, dst)
                    print(f"{src} -> {dst}")
                    total_changes += 1
                except Exception as e:
                    print(f"[ERROR] {src} -> {dst} : {e}")
                    total_errors += 1
            # count planned even if none printed due to errors
        total_changes += (len(changes) if args.dry_run else 0)

    if args.dry_run:
        print(f"\nSummary (dry-run): {total_changes} items would be renamed.")
    else:
        print(f"\nSummary: {total_changes} items renamed, {total_errors} errors.")

if __name__ == "__main__":
    main()
