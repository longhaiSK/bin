#!/Users/lol553/Github/bin/.venv/bin/python
import re
import sys
import os
import subprocess
import datetime 

# --- Self-Correction: Install missing packages ---
try:
    import git
    from git import Repo
except ImportError:
    print("\n🚨 Required module 'GitPython' not found. Attempting to install...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "GitPython"])
        print("✅ GitPython installed successfully. Restarting import.")
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


# --- Time Calculation Function ---
def _calculate_past_datetime(user_spec):
    """
    Converts user input (e.g., '1.5h') into a datetime object for filtering.
    """
    match = re.match(r"(\d+\.?\d*)([hdm])", user_spec, re.IGNORECASE)
    if not match:
        raise ValueError(f"Invalid time specification format: {user_spec}. Use formats like 1h, 2d, 30m.")

    number = float(match.groups()[0])
    unit = match.groups()[1].lower()
    
    if unit == 'h':
        delta = datetime.timedelta(hours=number)
    elif unit == 'd':
        delta = datetime.timedelta(days=number)
    elif unit.lower() == 'm':
        delta = datetime.timedelta(minutes=number)
    else:
        raise ValueError("Invalid time unit.")
    
    past_datetime = datetime.datetime.now() - delta
    return past_datetime.strftime('%Y-%m-%d %H:%M:%S')


# --- Main Logic: Summarize History ---
def summarize_local_history(repo_path, time_spec):
    """
    Summarizes local commits within the specified time period, grouping 
    commits under the files they affected.
    """
    try:
        since_time_str = _calculate_past_datetime(time_spec)

        repo = Repo(repo_path)
        
        # Dictionary to store file -> list of commits
        file_to_commits = {}
        
        # 1. Iterate over commits using the 'since' argument (newest first)
        for commit in repo.iter_commits('HEAD', since=since_time_str):
            
            commit_time = datetime.datetime.fromtimestamp(commit.committed_date)
            commit_data = {
                'id': commit.hexsha[:8],
                'timestamp': commit_time.strftime('%Y-%m-%d %H:%M:%S'),
                'summary': commit.summary.strip()
            }
            
            # Get files changed in this specific commit
            changed_files = commit.stats.files.keys()

            # 2. Populate the dictionary: link this commit data to every file it touched
            for file in changed_files:
                if file not in file_to_commits:
                    file_to_commits[file] = []
                file_to_commits[file].append(commit_data)
        
        # 3. Print Output
        
        if file_to_commits:
            print(f"\nSummary of Local Changes Committed in the Last {time_spec}:")
            print("---------------------------------------------------------")
            
            # Print files (sorted) and their corresponding commits
            for file, commits in sorted(file_to_commits.items()):
                print(f"- {file}")
                
                # Print commits indented beneath the file
                for summary in commits:
                    # Note the requested two-space indent and asterisk
                    print(f"  * [{summary['id']}] ({summary['timestamp']}) {summary['summary']}")
        else:
            print(f"No commits found in the local repository within the last {time_spec}.")

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
    repo_path = os.getcwd() 
    
    summarize_local_history(repo_path, time_spec_input)