#!/bin/sh
"exec" "`dirname $0`/.venv/bin/python" "$0" "$@"
import subprocess
import sys
import os
from datetime import datetime

# --- HEADER EXPLANATION ---
# 1. Runs as shell script first.
# 2. "exec" finds the .venv/bin/python relative to this file.
# 3. Restarts the script using that specific Python environment.

def run_git_command(command, check=True, capture_output=False):
    """A helper function to run Git commands."""
    try:
        if capture_output:
            result = subprocess.run(command, check=check, capture_output=True, text=True)
            return result.stdout.strip()
        else:
            subprocess.run(command, check=check)
            return None
    except subprocess.CalledProcessError as e:
        if check:
            error_msg = e.stderr.strip() if e.stderr else "(No error details captured)"
            print(f"Error executing Git command: {' '.join(command)}\n{error_msg}", file=sys.stderr)
            sys.exit(1)
        return None
    except FileNotFoundError:
        print("Error: Git command not found. Ensure Git is installed and in your PATH.", file=sys.stderr)
        sys.exit(1)

def get_current_branch():
    """Returns the name of the current git branch."""
    try:
        return run_git_command(['git', 'symbolic-ref', '--short', 'HEAD'], capture_output=True)
    except SystemExit:
        return None

def is_branch_exist(branch_name):
    """Checks if a branch exists locally."""
    result = subprocess.run(
        ['git', 'show-ref', '--verify', '--quiet', f'refs/heads/{branch_name}'],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    return result.returncode == 0

def start_branch(branch_name):
    """Creates a new branch or switches to an existing one."""
    if is_branch_exist(branch_name):
        print(f"✅ Branch '{branch_name}' already exists. Switching...")
        run_git_command(['git', 'checkout', branch_name])
    else:
        print(f"✨ Starting new branch: '{branch_name}'")
        run_git_command(['git', 'checkout', '-b', branch_name])
        try:
            subprocess.run(['git', 'push', '-u', 'origin', branch_name], check=False, stderr=subprocess.DEVNULL)
        except Exception:
            pass

def merge_sequence(feature_branch, target_branch='main'):
    """Auto-commits changes, merges into target, and pushes target."""
    
    if feature_branch == target_branch:
        print(f"🛑 You are already on '{target_branch}'. Cannot merge into itself.")
        sys.exit(1)

    print(f"\n--- Starting Merge Process for '{feature_branch}' ---")

    # 1. Ensure we are on the feature branch
    run_git_command(['git', 'checkout', feature_branch])

    # 2. Auto-save local work
    run_git_command(['git', 'add', '-A'])
    
    try:
        # Check for uncommitted changes
        subprocess.run(['git', 'diff', '--staged', '--quiet'], check=True, capture_output=True)
        print(f"No new changes to auto-save on '{feature_branch}'.")
    except subprocess.CalledProcessError:
        commit_msg = "auto commit by git_branch.py"
        print(f"💾 Auto-saving work: '{commit_msg}'")
        run_git_command(['git', 'commit', '-m', commit_msg])
        
        print(f"Pushing '{feature_branch}' to remote...")
        try:
            run_git_command(['git', 'push', 'origin', feature_branch])
        except SystemExit:
            print("⚠️ Warning: Push failed. Continuing with local merge...")

    # 3. Switch to target and update
    print(f"Pulling latest changes on '{target_branch}'...")
    run_git_command(['git', 'checkout', target_branch])
    run_git_command(['git', 'pull', '--rebase', 'origin', target_branch])

    # 4. Merge
    # Updated timestamp format to include hours and minutes for better uniqueness
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    merge_msg = f"merging {feature_branch}-{timestamp}"
    
    print(f"Merging '{feature_branch}' into '{target_branch}' with message: '{merge_msg}'...")
    
    try:
        run_git_command(['git', 'merge', '--no-ff', '-m', merge_msg, feature_branch])
        print(f"✅ Merge successful!")
        
        # 5. Push target
        print(f"Pushing merged '{target_branch}' to origin...")
        run_git_command(['git', 'push', 'origin', target_branch])

    except SystemExit:
        print(f"❌ Merge failed. Please resolve conflicts in '{target_branch}' manually.")
        sys.exit(1)
        
    print(f"🎉 Done! '{feature_branch}' is merged into '{target_branch}'.")

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  1. git-branch.py <branch_name>          (Start/Switch branch)")
        print("  2. git-branch.py <branch_name> --merge  (Merge specific branch)")
        print("  3. git-branch.py --done                 (Merge CURRENT branch)")
        sys.exit(1)

    arg1 = sys.argv[1]
    
    if arg1 == '--done':
        current_branch = get_current_branch()
        if not current_branch:
            print("Error: Could not detect current branch.")
            sys.exit(1)
        merge_sequence(current_branch)

    elif len(sys.argv) == 3 and sys.argv[2] == '--merge':
        merge_sequence(arg1)
    elif len(sys.argv) == 2:
        start_branch(arg1)
    else:
        print("Invalid arguments provided.")
        sys.exit(1)

if __name__ == "__main__":
    main()