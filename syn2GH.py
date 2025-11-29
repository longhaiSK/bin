#!/Users/lol553/Github/bin/.venv/bin/python
import os
import subprocess
import sys
import re
from datetime import datetime
from pathlib import Path

# --- Configuration ---
REPO_ROOTS = [Path(os.environ.get('githubroot', os.path.expanduser('~/Github')))]
REMOTE = os.environ.get('REMOTE', 'origin')
GIT_SSH_COMMAND = os.environ.get('GIT_SSH_COMMAND', 'ssh')

# --- New: Define core branches that require full pull/sync ---
CORE_BRANCHES = ['main', 'master', 'develop']

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
            return subprocess.run(
                command,
                cwd=cwd,
                check=check,
                text=True,
                env=dict(os.environ, GIT_SSH_COMMAND=GIT_SSH_COMMAND)
            )
        else:
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
            # Corrected error handling
            stderr_output = e.stderr.strip() if e.stderr else 'No error message.'
            raise RuntimeError(f"Command failed: {' '.join(command)}\nStderr: {stderr_output}")
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
    """Determines the current upstream tracking branch."""
    try:
        tracking_ref = run_git_command(
            ['git', 'rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}'],
            cwd=repo_dir,
            check=False,
            capture_output=True,
            silent=True
        )
        if 'fatal:' in tracking_ref or 'unknown revision' in tracking_ref or not tracking_ref:
             return None
        return tracking_ref
    except RuntimeError:
        return None

def process_repo(repo_dir, commit_msg, errors):
    """
    Performs the synchronization based on whether the branch is a core branch or a feature branch.
    """
    
    repo_str = str(repo_dir)

    # 1. Validation Checks & Get Current Branch Name
    try:
        if not run_git_command(['git', 'rev-parse', '--is-inside-work-tree'], cwd=repo_dir, check=False, capture_output=True, silent=True):
             return
        branch_name = run_git_command(['git', 'symbolic-ref', '--quiet', '--short', 'HEAD'], cwd=repo_dir, capture_output=True, silent=True)
        if not branch_name:
            return # Skip detached HEAD state
        run_git_command(['git', 'remote', 'get-url', REMOTE], cwd=repo_dir, check=True, capture_output=True, silent=True)
        
    except (subprocess.CalledProcessError, RuntimeError):
        return 

    # Determine sync mode
    is_core_branch = branch_name in CORE_BRANCHES
    
    # 2. Upstream Tracking Setup Check
    tracking_ref = get_tracking_ref(repo_dir, branch_name)

    # 3. Check Status (Speed optimization)
    needs_action = False
    
    try:
        # Check for local dirty state (always triggers action)
        if run_git_command(['git', 'status', '--porcelain'], cwd=repo_dir, capture_output=True, silent=True):
            needs_action = True
        
        # Check remote status (Fetch quietly)
        run_git_command(['git', 'fetch', REMOTE, branch_name, '--quiet'], cwd=repo_dir, check=False, silent=True)
        
        # Check for unpushed/unpulled commits
        if not tracking_ref or is_core_branch:
            needs_action = True
        else:
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

    except RuntimeError:
        needs_action = True 

    if not needs_action:
        return 

    # --- ACTION ---

    colored_print(f"\n{'-'*55}", 'CYAN')
    colored_print(f"Repo: {repo_str} ({branch_name})", 'BLUE') 
    
    # Get current HEAD for comparison later
    try:
        old_head = run_git_command(['git', 'rev-parse', 'HEAD'], cwd=repo_dir, capture_output=True, silent=True)
    except RuntimeError:
        old_head = "INITIAL_COMMIT" 

    # 1) Pull (Conditional)
    pull_success = True
    
    if is_core_branch and tracking_ref: 
        # CORE BRANCH SYNC: Pull with rebase/autostash
        try:
            print(f"{COLORS['BLUE']}1) Pull (CORE): {COLORS['NONE']}", end="")
            run_git_command(['git', 'pull', '--rebase', '--autostash', REMOTE, branch_name], cwd=repo_dir, check=True)
            
        except RuntimeError:
            colored_print(f"\n  ! Pull failed. Resolve conflicts manually.", 'RED')
            errors.append(f"{repo_str}: pull failed on branch {branch_name}")
            pull_success = False
    else:
        # FEATURE BRANCH BACKUP: Skip pull entirely to prevent unwanted merges/rebases
        colored_print(f"1) Pull (FEATURE): {COLORS['GREEN']}✓ Skipping pull for safe backup.", 'BLUE')

    if pull_success:
        try:
            new_head = run_git_command(['git', 'rev-parse', 'HEAD'], cwd=repo_dir, capture_output=True, silent=True)
        except RuntimeError:
            new_head = None

        if old_head != new_head and old_head != "INITIAL_COMMIT" and tracking_ref and is_core_branch: 
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
        elif tracking_ref and is_core_branch:
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

        # 4) Push (Handles new branches and existing ones)
        
        should_push = False
        push_options = [REMOTE, branch_name] # Default push command
        
        # Scenario A: New Branch (no tracking ref)
        if not tracking_ref:
            should_push = True
            # Set upstream to same branch name (e.g., origin/trySyn2GH.py)
            push_options = ['--set-upstream', REMOTE, branch_name]
            
        else:
            # Scenario B: Check for commits to push
            ref_to_check = tracking_ref
            try:
                commits_to_push = run_git_command(
                    ['git', 'log', '--pretty=format:%h', f'{ref_to_check}..HEAD'], 
                    cwd=repo_dir, 
                    check=False, 
                    capture_output=True, 
                    silent=True
                )
                if commits_to_push:
                    should_push = True
            except RuntimeError:
                should_push = True # Assume push needed if check fails

        if should_push:
            try:
                push_command = ['git', 'push'] + push_options
                run_git_command(push_command, cwd=repo_dir, check=True, silent=True)
                
                if not tracking_ref:
                     tracking_ref = f"{REMOTE}/{branch_name}"
                     
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