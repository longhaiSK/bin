#!/Users/lol553/Github/bin/.venv/bin/python


import re
import sys
import os

import subprocess

# --- Self-Correction: Install missing packages ---
try:
    import git
    from git import Repo
except ImportError:
    print("\n🚨 Required module 'GitPython' not found. Attempting to install...")
    try:
        # Use sys.executable to ensure pip corresponds to the correct Python environment
        subprocess.check_call([sys.executable, "-m", "pip", "install", "GitPython"])
        print("✅ GitPython installed successfully. Restarting import.")
        
        # Try importing again after installation
        try:
            import git
            from git import Repo
        except ImportError:
            print("🛑 Failed to import GitPython after installation. Please check your environment.")
            sys.exit(1)
            
    except subprocess.CalledProcessError as e:
        print(f"🛑 Automatic installation failed. Error: {e}")
        print("Please run 'pip install GitPython' manually in your terminal.")
        sys.exit(1)
# --- Time Conversion Function ---
def _format_time_spec(user_spec):
    """
    Converts user input like '1.5h' or '2d' into Git-compatible reflog syntax 
    like '1.5.hours.ago' or '2.days.ago'.
    """
    # Regex to capture the number (including decimals) and the unit letter
    # Allows for inputs like 1, 1.5, or 1d, 1h, 1m
    match = re.match(r"(\d+\.?\d*)([hdm])", user_spec, re.IGNORECASE)
    if not match:
        raise ValueError(f"Invalid time specification format: {user_spec}. Use formats like 1h, 2d, 30m.")

    number, unit = match.groups()
    
    # Map units and determine the proper plural form for the Git reflog syntax
    if unit.lower() == 'h':
        unit_str = 'hour' if number == '1' else 'hours'
    elif unit.lower() == 'd':
        unit_str = 'day' if number == '1' else 'days'
    elif unit.lower() == 'm':
        unit_str = 'minute' if number == '1' else 'minutes'
    else:
        # Should be caught by the regex, but included for robustness
        raise ValueError("Invalid time unit. Use 'h' (hour), 'd' (day), or 'm' (minute).")

    # Construct the Git-compatible reference string: 1.5.hours.ago
    return f"{number}.{unit_str}.ago"

# --- Main Logic ---
def diff_to_time_ago(repo_path, time_spec):
    """
    Shows the cumulative diff between the current HEAD and the commit 
    that was active at the specified historical time.
    """
    try:
        # 1. Format the user input into a Git-readable time reference
        git_ref_time = _format_time_spec(time_spec)
        
        # Git uses HEAD@{<time_spec>} syntax for reflog lookups
        old_ref = f"HEAD@{{{git_ref_time}}}"

        # 2. Open the repository in the current working directory
        repo = Repo(repo_path)
        
        print(f"Generating diff from '{time_spec}' ago ({git_ref_time}) to current HEAD...")
        print("---------------------------------------")

        # 3. Execute the raw diff command using git.Repo.git.diff
        # --unified=0 removes context lines for a cleaner output focusing on changes
        diff_output = repo.git.diff(old_ref, 'HEAD', unified=0)
        
        if diff_output:
            print(diff_output)
        else:
            print(f"No committed changes detected between {time_spec} ago and the current commit.")

    except git.exc.BadName:
        print(f"Error: Could not resolve the time reference '{time_spec}'. The reflog may not contain history that old.")
    except git.exc.InvalidGitRepositoryError:
        print(f"Error: The current working directory is not a valid Git repository.")
    except ValueError as ve:
        print(f"Input Error: {ve}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# --- Command Line Execution ---
if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] != '--past':
        print("Usage: python script_name.py --past <time_spec>")
        print("Example: python script_name.py --past 1.5h")
        print("Valid time specs: 1h, 2d, 45m, 0.5h, etc. (h=hours, d=days, m=minutes)")
        sys.exit(1)

    time_spec_input = sys.argv[2]
    
    # Use the current working directory as the repository path
    repo_path = os.getcwd() 
    
    diff_to_time_ago(repo_path, time_spec_input)