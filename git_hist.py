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
    Converts user input (e.g., '1.5h') into a formatted datetime string for the 'since' filter.
    """
    match = re.match(r"(\d+\.?\d*)([hdm])", user_spec, re.IGNORECASE)
    if not match:
        # This function should only be called if the spec ends in h, d, or m
        raise ValueError("Invalid time format.")

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
def summarize_local_history(repo_path, spec):
    """
    Summarizes local history based on either a time period (e.g., 1h) or a 
    commit count (e.g., 5c).
    """
    try:
        repo = Repo(repo_path)
        file_to_commits = {}
        
        # 1. Determine Filtering Method (Time vs. Commit Count)
        iter_args = {'rev': 'HEAD'}
        if spec.lower().endswith(('h', 'd', 'm')):
            # Time-based filtering (e.g., 1h, 2d)
            since_time_str = _calculate_past_datetime(spec)
            iter_args['since'] = since_time_str
            print(f"\nFiltering by time (last {spec})...")
            
        elif spec.lower().endswith('c'):
            # Commit count filtering (e.g., 5c)
            try:
                count = int(spec[:-1])
                if count <= 0: raise ValueError
            except ValueError:
                raise ValueError(f"Invalid commit count: {spec}. Use format like 5c (where 5 is a positive integer).")
                
            iter_args['max_count'] = count
            print(f"\nFiltering by commit count (last {count} commits)...")
            
        else:
            raise ValueError(f"Invalid specification format: {spec}. Use time (1h, 2d, 30m) or commit count (5c).")


        # 2. Iterate over commits using the determined arguments
        for commit in repo.iter_commits(**iter_args):
            
            commit_time = datetime.datetime.fromtimestamp(commit.committed_date)
            commit_data = {
                'id': commit.hexsha[:8],
                'timestamp': commit_time.strftime('%Y-%m-%d %H:%M:%S'),
                'summary': commit.summary.strip(),
            }
            
            # Determine the diff index
            if commit.parents:
                diff_index = commit.parents[0].diff(commit)
            else:
                # Initial commit: diff against a null tree
                diff_index = commit.diff(None) 

            # 3. Process Diff for Status (A/M/D)
            for diff in diff_index:
                status = diff.change_type # 'A', 'M', 'D', 'R', etc.
                file = diff.b_path if diff.b_path else diff.a_path 

                if file not in file_to_commits:
                    file_to_commits[file] = []
                    
                file_to_commits[file].append({
                    **commit_data,
                    'status': status
                })
        
        # 4. Print Output
        if file_to_commits:
            print("---------------------------------------------------------")
            
            for file, commits in sorted(file_to_commits.items()):
                print(f"- {file}")
                
                for summary in commits:
                    print(f"  * [{summary['id']}] [{summary['status']}] ({summary['timestamp']}) {summary['summary']}")
        else:
            print(f"No commits found in the local repository within the last {spec}.")

    except git.exc.InvalidGitRepositoryError:
        print(f"Error: The current working directory is not a valid Git repository.")
    except ValueError as ve:
        print(f"Input Error: {ve}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# --- Command Line Execution ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script_name.py <time_spec_or_commit_count>")
        print("Example: python script_name.py 1.5h")
        print("Example: python script_name.py 5c")
        print("Valid time specs: 1h, 2d, 30m, etc. | Commit specs: 1c, 10c, etc.")
        sys.exit(1)

    # Simplified argument parsing: spec is now sys.argv[1]
    spec_input = sys.argv[1]
    repo_path = os.getcwd() 
    
    summarize_local_history(repo_path, spec_input)