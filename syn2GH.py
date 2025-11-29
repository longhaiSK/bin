#!/Users/lol553/Github/bin/.venv/bin/python

import os
import subprocess
import sys
import re
from datetime import datetime
from pathlib import Path

# --- Configuration ---
# REPO_ROOTS and other settings remain the same.
# The global BRANCH default is now mostly ignored, as we use the current branch.
REPO_ROOTS = [Path(os.environ.get('githubroot', os.path.expanduser('~/Github')))]
REMOTE = os.environ.get('REMOTE', 'origin')
GIT_SSH_COMMAND = os.environ.get('GIT_SSH_COMMAND', 'ssh')

# Exclude heavy/noisy directories
EXCLUDE_REGEX = re.compile(r'(/node_modules/|/\.venv/|/\.cargo/)')

# --- Colors (ANSI Escape Codes) ---
COLORS = {
    'BLUE': '\033[0;34m',
    'GREEN': '\033[32m',
    'YELLOW': '\033[0;33m',
    'RED': '\033[0;31m',
    'CYAN': '\033[0;36m',
    'NONE': '\033[0m'
}

def colored_print(text, color_key):
    """Prints text in the specified color."""
    print(f"{COLORS.get(color_key, COLORS['NONE'])}{text}{COLORS['NONE']}")

def run_git_command(command, cwd, check=True, capture_output=False, silent=False):
    """Wrapper for running Git commands."""
    try:
        if not silent and not capture_output:
            # Run without capturing, allowing output to stream directly
            return subprocess.run(
                command,
                cwd=cwd,
                check=check,
                text=True,
                env=dict(os.environ, GIT_SSH_COMMAND=GIT_SSH_COMMAND)
            )
        else:
            # Run capturing output
            result = subprocess.run(
                command,
                cwd=cwd,
                check=check,
                capture_output=True,
                text=True,
                env=dict(os.environ, GIT_SSH_COMMAND=GIT_SSH_COMMAND)
            )
            return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        if check:
            raise RuntimeError(f"Command failed: {' '.join(command)}\nStderr: {e.stderr.strip()}")
        return None 

def find_git_repos(root_dirs, exclude_regex):
    """Recursively finds all Git directories under the given roots, respecting the exclusion pattern."""
    repo_dirs = set()
    for root in root_dirs:
        if not root.is_dir():
            continue
        for git_dir in root.rglob('.git'):
            repo_path = git_dir.parent.resolve()
            if exclude_regex.search(str(repo_path)):
                continue
            if (repo_path / '.git').is_dir():
                repo_dirs.add(repo_path)
    
    return sorted(list(repo_dirs), key=lambda p: str(p).lower())

def get_tracking_ref(repo_dir, branch_name):
    """
    Determines the current upstream tracking branch, setting it if necessary.
    Uses the branch_name determined from the current HEAD.
    """
    try:
        # Check current tracking ref
        tracking_ref = run_git_command(
            ['git', 'rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}'],
            cwd=repo_dir,
            check=False,
            capture_output=True,
            silent=True
        )
    except RuntimeError:
        tracking_ref = None

    if not tracking_ref or 'fatal:' in tracking_ref:
        tracking_ref = None
        # If no tracking ref is set, try to set it to origin/current_branch, or origin/HEAD branch
        try:
            # First, try to set upstream to origin/current_branch_name
            upstream_ref_current = f"{REMOTE}/{branch_name}"
            
            # Check if the remote branch exists first
            remote_branches = run_git_command(
                ['git', 'ls-remote', REMOTE, branch_name],
                cwd=repo_dir,
                check=False,
                capture_output=True,
                silent=True
            )

            if remote_branches:
                 # Try to set upstream
                result = run_git_command(
                    ['git', 'branch', '--set-upstream-to', upstream_ref_current, branch_name],
                    cwd=repo_dir,
                    check=False,
                    capture_output=True,
                    silent=True
                )
                if result is not None:
                    tracking_ref = upstream_ref_current
                    
            # If still no tracking ref, fall back to origin/HEAD branch logic
            if not tracking_ref:
                # Get the default HEAD branch name from remote
                remote_show = run_git_command(
                    ['git', 'remote', 'show', REMOTE],
                    cwd=repo_dir,
                    check=False,
                    capture_output=True,
                    silent=True
                )
                default_remote_branch = next(
                    (line.split()[-1] for line in remote_show.splitlines() if 'HEAD branch' in line),
                    None
                )
                
                if default_remote_branch and default_remote_branch != branch_name:
                    upstream_ref_default = f"{REMOTE}/{default_remote_branch}"
                    run_git_command(
                        ['git', 'branch', '--set-upstream-to', upstream_ref_default, branch_name],
                        cwd=repo_dir,
                        check=False,
                        capture_output=True,
                        silent=True
                    )
                    # Note: We don't update tracking_ref here unless the user is specifically on that default branch
                    # The main goal is to have *something* set up for pull/push.

        except RuntimeError:
            pass 

    return tracking_ref

def process_repo(repo_dir, commit_msg, errors):
    """
    Performs the pull-stage-commit-push sequence for a single repository,
    using the currently checked out branch.
    """
    
    repo_str = str(repo_dir)

    # 1. Validation Checks & Get Current Branch Name (Key Modification)
    try:
        if not run_git_command(['git', 'rev-parse', '--is-inside-work-tree'], cwd=repo_dir, check=False, capture_output=True, silent=True):
             return

        # *** Get the current branch name (even if temporary) ***
        branch_name = run_git_command(['git', 'symbolic-ref', '--quiet', '--short', 'HEAD'], cwd=repo_dir, capture_output=True, silent=True)
        if not branch_name:
            # Skip if in detached HEAD state
            return

        run_git_command(['git', 'remote', 'get-url', REMOTE], cwd=repo_dir, check=True, capture_output=True, silent=True)
        
    except (subprocess.CalledProcessError, RuntimeError):
        return 

    # 2. Upstream Tracking Setup
    tracking_ref = get_tracking_ref(repo_dir, branch_name)

    # ... (rest of the logic remains largely the same, but uses branch_name and tracking_ref)

    # 3. Check Status (Speed optimization)
    needs_action = False
    
    try:
        if run_git_command(['git', 'status', '--porcelain'], cwd=repo_dir, capture_output=True, silent=True):
            needs_action = True
        else:
            # Fetch the current branch
            run_git_command(['git', 'fetch', REMOTE, branch_name, '--quiet'], cwd=repo_dir, check=False, silent=True)
            
            if tracking_ref and 'fatal:' not in tracking_ref:
                counts_str = run_git_command(
                    ['git', 'rev-list', '--left-right', '--count', f'HEAD...{tracking_ref}'],
                    cwd=repo_dir,
                    check=False,
                    capture_output=True,
                    silent=True
                ) or "0 0"
                
                try:
                    ahead, behind = map(int, counts_str.split())
                    if ahead != 0 or behind != 0:
                        needs_action = True
                except ValueError:
                    needs_action = True 

            else:
                # If no tracking branch is set, we still check if there are local commits to push
                try:
                    remote_ref = f'{REMOTE}/{branch_name}'
                    commits_to_push = run_git_command(['git', 'log', '--pretty=format:%h', f'{remote_ref}..HEAD'], cwd=repo_dir, check=False, capture_output=True, silent=True)
                    if commits_to_push:
                        needs_action = True
                except RuntimeError:
                    needs_action = True # Assume action needed if status check fails

    except RuntimeError:
        needs_action = True 

    if not needs_action:
        return 

    # --- ACTION ---

    colored_print(f"\n{'-'*55}", 'CYAN')
    colored_print(f"Repo: {repo_str} ({branch_name})", 'BLUE') # Added current branch to output
    
    try:
        old_head = run_git_command(['git', 'rev-parse', 'HEAD'], cwd=repo_dir, capture_output=True, silent=True)
    except RuntimeError:
        old_head = "INITIAL_COMMIT" 

    # 1) Pull (Rebase/Autostash) - Uses current branch_name
    pull_success = True
    if tracking_ref and 'fatal:' not in tracking_ref:
        try:
            print(f"{COLORS['BLUE']}1) Pull: {COLORS['NONE']}", end="")
            run_git_command(['git', 'pull', '--rebase', '--autostash', REMOTE, branch_name], cwd=repo_dir, check=True)
        except RuntimeError:
            colored_print(f"\n  ! Pull failed. Resolve conflicts manually.", 'RED')
            errors.append(f"{repo_str}: pull failed on branch {branch_name}")
            pull_success = False

    if pull_success:
        try:
            new_head = run_git_command(['git', 'rev-parse', 'HEAD'], cwd=repo_dir, capture_output=True, silent=True)
        except RuntimeError:
            new_head = None

        if old_head != new_head and old_head != "INITIAL_COMMIT":
            colored_print(f"1) Pull: {COLORS['GREEN']}↓ Changes pulled:", 'BLUE')
            log_output = run_git_command(
                ['git', 'log', f'{old_head}..{new_head}', '--pretty=format:      %C(yellow)%h%C(reset) - %s %C(cyan)(%an, %ar)%C(reset)'],
                cwd=repo_dir,
                capture_output=True,
                silent=True
            )
            print(log_output)
            print("")
            diff_stat = run_git_command(
                ['git', 'diff', '--stat', f'{old_head}..{new_head}'],
                cwd=repo_dir,
                capture_output=True,
                silent=True
            )
            print('\n'.join("      " + line for line in diff_stat.splitlines()))
        else:
            colored_print(f"1) Pull: {COLORS['GREEN']}✓ Up-to-date.", 'BLUE')

        # 2) Stage
        run_git_command(['git', 'add', '-A'], cwd=repo_dir, check=True, silent=True)
        staged_changes = run_git_command(['git', 'diff', '--staged', '--quiet'], cwd=repo_dir, check=False, capture_output=True, silent=True)

        if not staged_changes:
            colored_print(f"2) Stage: {COLORS['GREEN']}Changes staged.", 'BLUE')
        else:
            colored_print(f"2) Stage: {COLORS['GREEN']}✓ Nothing to stage.", 'BLUE')

        # 3) Commit
        if not staged_changes:
            try:
                run_git_command(['git', 'commit', '-m', commit_msg], cwd=repo_dir, check=True, silent=True)
                colored_print(f"3) Commit: {COLORS['GREEN']}✓ Committed:", 'BLUE')
                
                commit_stat = run_git_command(
                    ['git', 'show', '--stat', '--oneline', '--no-color', 'HEAD'],
                    cwd=repo_dir,
                    capture_output=True,
                    silent=True
                )
                stat_lines = commit_stat.splitlines()
                if len(stat_lines) > 1:
                    formatted_stat = '\n'.join(f"      {COLORS['RED']}{line}{COLORS['NONE']}" for line in stat_lines[1:])
                    print(formatted_stat)
                
            except RuntimeError:
                colored_print(f"3) Commit: {COLORS['RED']}! Failed.", 'BLUE')
                errors.append(f"{repo_str}: commit failed on branch {branch_name}")
                return
        else:
            colored_print(f"3) Commit: {COLORS['GREEN']}✓ Nothing to commit.", 'BLUE')

        # 4) Push - Uses current branch_name
        
        # Determine the remote reference to check against
        if tracking_ref and 'fatal:' not in tracking_ref:
            ref_to_check = tracking_ref
        else:
            ref_to_check = f'{REMOTE}/{branch_name}'
            
        try:
            commits_to_push = run_git_command(
                ['git', 'log', '--pretty=format:%h', f'{ref_to_check}..HEAD'], 
                cwd=repo_dir, 
                check=False, 
                capture_output=True, 
                silent=True
            )
        except RuntimeError:
            commits_to_push = "" 

        if commits_to_push:
            try:
                # Use current branch_name for push
                run_git_command(['git', 'push', REMOTE, branch_name], cwd=repo_dir, check=True, silent=True)
                colored_print(f"4) Push: {COLORS['GREEN']}✓ Pushed successfully.", 'BLUE')
            except RuntimeError:
                colored_print(f"4) Push: {COLORS['RED']}↑ Push FAILED.", 'BLUE')
                errors.append(f"{repo_str}: push failed on branch {branch_name}")
                return
        else:
            colored_print(f"4) Push: {COLORS['GREEN']}✓ Already pushed.", 'BLUE')
            
def main():
    """Main function to orchestrate the Git synchronization process."""
    
    if len(sys.argv) > 1:
        commit_msg = sys.argv[1]
    else:
        try:
            hostname = subprocess.check_output(['hostname'], text=True).strip()
        except Exception:
            hostname = 'unknown_host'
            
        commit_msg = f"syn2GH from {hostname}"

    start_ts = datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')
    colored_print(f"syn2GH start: {start_ts} on {os.uname().nodename}", 'RED')
    
    try:
        git_dirs = find_git_repos(REPO_ROOTS, EXCLUDE_REGEX)
    except Exception as e:
        colored_print(f"Error finding repositories: {e}", 'RED')
        sys.exit(1)
        
    if not git_dirs:
        colored_print("No git repositories found.", 'YELLOW')
        sys.exit(0)

    errors = []
    for repo in git_dirs:
        process_repo(repo, commit_msg, errors)
        
    end_ts = datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')
    colored_print(f"\n{'-'*55}", 'CYAN')
    colored_print(f"syn2GH end: {end_ts} on {os.uname().nodename}", 'RED')

    if errors:
        colored_print(f"\n--- Errors ({len(errors)}) ---", 'RED')
        for error in errors:
            colored_print(f"  - {error}", 'RED')
        sys.exit(1)
    else:
        colored_print("\n--- Synchronization complete with no errors. ---", 'GREEN')
        sys.exit(0)

if __name__ == "__main__":
    main()