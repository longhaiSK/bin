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

def merge_and_delete(feature_branch, target_branch='main'):
    """Auto-commits changes with 'branchname-timestamp', merges, and prompts deletion."""
    print(f"\n--- Starting Merge Process ---")

    # 1. Switch to feature branch to save work
    print(f"Checking '{feature_branch}' for uncommitted work...")
    run_git_command(['git', 'checkout', feature_branch])

    # 2. Auto-save: Stage and commit any local changes
    run_git_command(['git', 'add', '-A'])
    
    try:
        # Check if there are changes to commit
        subprocess.run(['git', 'diff', '--staged', '--quiet'], check=True, capture_output=True)
        print(f"No new changes to auto-save on '{feature_branch}'.")
    except subprocess.CalledProcessError:
        # --- KEY CHANGE: Commit message uses actual branch name + timestamp ---
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        commit_msg = f"{feature_branch}-{timestamp}"
        
        print(f"💾 Auto-saving work with message: '{commit_msg}'")
        run_git_command(['git', 'commit', '-m', commit_msg])
        
        # Push to remote for backup
        print(f"Pushing '{feature_branch}' to remote...")
        try:
            run_git_command(['git', 'push', 'origin', feature_branch])
        except SystemExit:
            print("⚠️ Warning: Push failed. Continuing with local merge...")

    # 3. Switch to target branch and pull latest changes
    print(f"Pulling latest changes on '{target_branch}'...")
    run_git_command(['git', 'checkout', target_branch])
    run_git_command(['git', 'pull', '--rebase', 'origin', target_branch])

    # 4. Perform the merge
    print(f"Merging '{feature_branch}' into '{target_branch}'...")
    try:
        # --no-ff ensures a merge commit is created to preserve history
        run_git_command(['git', 'merge', '--no-ff', feature_branch])
        print(f"✅ Merge successful!")
        
        # 5. Push the merged target branch
        print(f"Pushing merged '{target_branch}' to origin...")
        run_git_command(['git', 'push', 'origin', target_branch])

    except SystemExit:
        print(f"❌ Merge failed. Please resolve conflicts in '{target_branch}' manually.")
        sys.exit(1)

    # 6. Prompt for deletion
    print("-" * 30)
    user_input = input(f"❓ Do you want to delete the branch '{feature_branch}' locally and remotely? (Yes/No): ").strip().lower()

    if user_input == 'yes':
        # Delete Local
        try:
            subprocess.run(['git', 'branch', '-d', feature_branch], check=True)
            print(f"🗑️ Deleted local branch: {feature_branch}")
        except subprocess.CalledProcessError:
            print(f"⚠️ Warning: Could not delete local branch '{feature_branch}'. You might need 'git branch -D {feature_branch}'.")
            
        # Delete Remote
        try:
            subprocess.run(['git', 'push', 'origin', '--delete', feature_branch], check=True)
            print(f"🗑️ Deleted remote branch: origin/{feature_branch}")
        except subprocess.CalledProcessError:
            print(f"⚠️ Warning: Could not delete remote branch. It might not exist.")
    else:
        print(f"Skipping deletion. Branch '{feature_branch}' remains intact.")

def main():
    if len(sys.argv) < 2:
        print("Usage: git-branch.py <branch_name> [--merge]")
        sys.exit(1)

    branch_name = sys.argv[1]
    
    if len(sys.argv) == 3 and sys.argv[2] == '--merge':
        merge_and_delete(branch_name)
    elif len(sys.argv) == 2:
        start_branch(branch_name)
    else:
        print("Invalid arguments provided.")
        sys.exit(1)

if __name__ == "__main__":
    main()