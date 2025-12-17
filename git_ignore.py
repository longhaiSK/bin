#!/bin/sh
""":"
exec "$(dirname "$0")/.venv/bin/python" "$0" "$@"
"""


import os
import sys
import argparse
import subprocess
from pathlib import Path
import tempfile
import io

# --- Configuration ---
QUARTO_PATTERNS = [
    "_freeze/",
    "_cache/",
    ".quarto/",
    "_extensions/",
    "figure-pdf/",
]

LATEX_PATTERNS = [
    # Common LaTeX auxiliary/scratch files
    "*.aux",
    "*.log",
    "*.out",
    "*.toc",
    "*.lof",
    "*.lot",
    "*.fls",
    "*.fdb_latexmk",
    "*.synctex.gz*",
    "_minted*/",
]

RSTUDIO_PATTERNS = [
    # Common RStudio project files and scratch data
    "*.Rproj",
    ".Rhistory",
    ".RData",
    ".ipynb_checkpoints/",
    "rsconnect/",
    "renv/",
]

def run_git_command(command, cwd=None, check=True, capture_output=False):
    """Executes a Git command and returns the output or handles errors."""
    try:
        result = subprocess.run(
            ['git'] + command,
            cwd=cwd,
            check=check,
            capture_output=capture_output,
            text=True,
            encoding='utf-8'
        )
        if capture_output:
            return result.stdout.strip()
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Git command failed: {' '.join(e.cmd)}")
        if e.stderr:
            print(f"Error output:\n{e.stderr.strip()}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ Error: Git command not found. Ensure Git is installed and in your PATH.")
        sys.exit(1)

def is_repo_clean():
    """Checks if the working directory is clean."""
    # git diff-index --quiet HEAD -- returns 0 if clean, 1 if dirty
    try:
        # Use check=False to prevent Python exception on exit code 1 (dirty)
        result = run_git_command(['diff-index', '--quiet', 'HEAD', '--'], check=False)
        return result.returncode == 0
    except SystemExit:
        # If git command failed entirely (e.g., git not found), let caller handle
        return False

def untrack_files(repo_root, all_patterns):
    """
    Finds and untracks files matching the NEW patterns only,
    by querying the Git index directly using git ls-files -i --exclude-from.
    """
    print("\n>>> 1. Untracking files matching **ONLY** the current patterns (querying Git index)...")

    temp_ignore_file = None
    files_to_untrack_output = ""

    try:
        # 1. Create a named temporary file with *only* the new patterns
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, encoding='utf-8') as tmp:
            tmp.write('\n'.join(all_patterns) + '\n')
            temp_ignore_file = Path(tmp.name)

        # 2. Use git ls-files to find *tracked* files that match the new ignore rules.
        # --cached: Only tracked files.
        # -i: list files matching ignore patterns.
        # --exclude-from: Use our temporary file containing the new patterns.
        files_to_untrack_output = run_git_command(
            ['ls-files', '--cached', '-i', '--exclude-from', str(temp_ignore_file)],
            cwd=repo_root,
            check=True,
            capture_output=True
        )

    finally:
        # 3. Ensure the temporary file is deleted
        if temp_ignore_file and temp_ignore_file.exists():
            os.unlink(temp_ignore_file)

    files_list = [f for f in files_to_untrack_output.splitlines() if f]

    if not files_list:
        print("✅ No currently tracked files matched the new ignore patterns. Skipping git rm.")
        return False

    # Perform git rm --cached on the unique list of files
    files_list.sort()

    print("Files to be untracked:")
    for f in files_list:
        print(f"    - {f}")

    print("\nRunning: git rm --cached -- <files listed above>")

    # Git rm command (removed the unsupported '-v' flag)
    run_git_command(['rm', '--cached', '--'] + files_list, cwd=repo_root)

    print("✅ Finished untracking files matching current patterns.")
    return True

def update_gitignore(gitignore_path, all_patterns):
    """Appends missing patterns to .gitignore and deduplicates the file."""
    print("\n>>> 2. Updating .gitignore (append patterns from this run if missing, then deduplicate)...")

    # 1. Read existing content
    if gitignore_path.exists():
        existing_lines = gitignore_path.read_text(encoding='utf-8').splitlines()
    else:
        existing_lines = []

    existing_patterns = set(existing_lines)

    # 2. Append missing patterns
    new_content_added = False
    for pattern in all_patterns:
        if pattern not in existing_patterns:
            print(f"    ➕ Appending: {pattern}")
            existing_lines.append(pattern)
            existing_patterns.add(pattern)
            new_content_added = True
        else:
            print(f"    ✅ Already present: {pattern}")

    # 3. Deduplicate (using dict.fromkeys to preserve order and deduplicate)
    print(f"    🧹 Deduplicating {gitignore_path.name}...")
    deduplicated_lines = list(dict.fromkeys(existing_lines))

    # 4. Write back to file
    gitignore_path.write_text('\n'.join(deduplicated_lines) + '\n', encoding='utf-8')

    # 5. Stage the changes
    run_git_command(['add', str(gitignore_path)], cwd=gitignore_path.parent)

    return new_content_added or len(deduplicated_lines) != len(existing_lines)

def main():
    parser = argparse.ArgumentParser(
        description="Add pattern(s) to .gitignore, remove tracked files matching those patterns, commit the changes, and print push instructions.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        'patterns',
        nargs='*',
        help="One or more patterns to add to .gitignore (e.g., '*.log', 'data/*.csv')."
    )
    parser.add_argument(
        '--repo',
        action='store_true',
        help="Use the repository root .gitignore (repo-level), not the current directory's .gitignore."
    )
    parser.add_argument(
        '--quarto',
        action='store_true',
        help=f"Add common Quarto scratch patterns:\n  {', '.join(QUARTO_PATTERNS)}"
    )
    parser.add_argument(
        '--latex',
        action='store_true',
        help=f"Add common LaTeX scratch patterns:\n  {', '.join(LATEX_PATTERNS)}"
    )
    parser.add_argument(
        '--rstudio',
        action='store_true',
        help=f"Add common RStudio scratch patterns:\n  {', '.join(RSTUDIO_PATTERNS)}"
    )

    args = parser.parse_args()

    # --- Initial Checks ---
    try:
        repo_root_str = run_git_command(['rev-parse', '--show-toplevel'], capture_output=True)
        repo_root = Path(repo_root_str)
    except SystemExit:
        print("❌ Failed to determine repository root. Are you inside a Git repository?")
        sys.exit(1)

    if not is_repo_clean():
        print("🚨 Error: Your working directory is not clean. Please commit or stash your changes before running this script.")
        sys.exit(1)

    # --- Assemble Patterns ---
    all_patterns = []
    if args.quarto:
        all_patterns.extend(QUARTO_PATTERNS)
    if args.latex:
        all_patterns.extend(LATEX_PATTERNS)
    if args.rstudio:
        all_patterns.extend(RSTUDIO_PATTERNS)
    all_patterns.extend(args.patterns)

    if not all_patterns:
        print("🚨 Error: You must provide at least one pattern, or use --quarto, --latex, or --rstudio.")
        parser.print_usage()
        sys.exit(1)

    # --- Determine Paths and CWD ---
    if args.repo:
        working_dir = repo_root
        gitignore_path = repo_root / ".gitignore"
        print("🔧 Mode: repo-level .gitignore")
        print(f"Repo root: {repo_root}")
    else:
        working_dir = Path.cwd()
        # Find the gitignore path relative to the repo root if possible, 
        # but operate from cwd for folder-level
        gitignore_path = working_dir / ".gitignore"
        print("🔧 Mode: folder-level .gitignore (current directory)")

    # Print the path nicely
    try:
        display_path = gitignore_path.relative_to(repo_root)
    except ValueError:
        display_path = gitignore_path

    print(f"Using .gitignore: {display_path}")
    print("--- Starting Git Ignore and Clean Workflow ---")
    print("Patterns to process this run:")
    for p in all_patterns:
        print(f"    - {p}")

    # --- Workflow Steps ---

    # 1. Untrack files matching new patterns
    files_were_untracked = untrack_files(repo_root, all_patterns)

    # 2. Update and stage .gitignore
    gitignore_was_changed = update_gitignore(gitignore_path, all_patterns)

    # 3. Commit
    print("\n>>> 3. Committing changes...")

    if not files_were_untracked and not gitignore_was_changed:
        print("⚠️ No staged changes detected to commit. Exiting commit phase.")
    else:
        joined_patterns = ", ".join(all_patterns)
        commit_msg = f"chore: Ignore patterns: {joined_patterns} and remove already-tracked instances."

        run_git_command(['commit', '-m', commit_msg], cwd=repo_root)

        print("✅ Successfully committed with message:")
        print(f"    {commit_msg}")

    # 4. Push instructions
    print("\n>>> 4. Push instructions (no automatic push performed).")
    print("👉 When you're satisfied, push with:")
    print("    git push")

    print("\n--- Workflow Complete ---")


if __name__ == "__main__":
    main()
    