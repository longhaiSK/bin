#!/bin/sh
"exec" "`dirname $0`/.venv/bin/python" "$0" "$@"
import subprocess
import sys

# --- HEADER EXPLANATION ---
# 1. Runs as shell script first.
# 2. "exec" finds the .venv/bin/python relative to this file.
# 3. Restarts the script using that specific Python environment.

def run_git_command(command, check=True, capture_output=False):
    """Helper to run git commands."""
    try:
        if capture_output:
            result = subprocess.run(command, check=check, capture_output=True, text=True)
            return result.stdout.strip()
        else:
            subprocess.run(command, check=check)
            return None
    except subprocess.CalledProcessError as e:
        if check:
            error_msg = e.stderr.strip() if e.stderr else "(No error details)"
            print(f"Error: {' '.join(command)}\n{error_msg}", file=sys.stderr)
            sys.exit(1)
        return None

def get_current_branch():
    return subprocess.run(['git', 'symbolic-ref', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()

def delete_branch(branch_name):
    # Safety Check
    if branch_name in ['main', 'master', 'develop']:
        print(f"🛑 Error: Protected branch '{branch_name}' cannot be deleted via this script.")
        sys.exit(1)

    print(f"🔥 Deleting branch '{branch_name}'...")

    # 1. If we are currently ON the branch to be deleted, move to main first
    current = get_current_branch()
    if current == branch_name:
        print(f"   (Currently checked out on {branch_name}, switching to main...)")
        run_git_command(['git', 'checkout', 'main'])

    # 2. Delete Remote Branch
    print("   Attempting to delete remote branch...")
    try:
        # Check=False prevents crash if remote branch doesn't exist
        result = subprocess.run(['git', 'push', 'origin', '--delete', branch_name], check=False, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✅ Remote branch 'origin/{branch_name}' deleted.")
        else:
            print(f"   ℹ️  Remote branch not found or already deleted.")
    except Exception:
        pass

    # 3. Delete Local Branch
    print("   Attempting to delete local branch...")
    try:
        # We use -d (safe delete) first. If it fails, we ask/warn user.
        # If you want forced delete, change '-d' to '-D'.
        result = subprocess.run(['git', 'branch', '-d', branch_name], check=False, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"   ✅ Local branch '{branch_name}' deleted.")
        else:
            # If safe delete fails (unmerged changes), try force delete?
            # Uncomment the lines below to auto-force delete, or leave as is to warn.
            print(f"   ⚠️  Could not delete local branch safely (it might contain unmerged changes).")
            print(f"   To force delete, run: git branch -D {branch_name}")
            
    except Exception:
        pass

    print(f"✨ Cleanup complete for '{branch_name}'.")

def main():
    if len(sys.argv) < 2:
        print("Usage: git_delbranch.py <branch_name>")
        sys.exit(1)

    branch_to_delete = sys.argv[1]
    delete_branch(branch_to_delete)

if __name__ == "__main__":
    main()
```
eof

### 🚀 Usage

1.  **Merge & Save (No delete prompt):**
    ```bash
    git-branch.py --done