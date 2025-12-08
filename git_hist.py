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
    match = re.match(r"(\d+\.?\d*)([hdm])", user_spec, re.IGNORECASE)
    if not match:
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


# --- Helper Function for Tree Truncation (Remains the same) ---
def get_all_descendant_commits(node):
    all_commits = []
    for key, value in node.items():
        if isinstance(value, list):
            all_commits.extend(value)
        elif isinstance(value, dict):
            all_commits.extend(get_all_descendant_commits(value))
    
    seen_ids = set()
    unique_commits = []
    for commit in all_commits:
        if commit['id'] not in seen_ids:
            seen_ids.add(commit['id'])
            unique_commits.append(commit)
            
    unique_commits.sort(key=lambda c: c['timestamp'], reverse=True)
    return unique_commits

# --- Print Tree Recursively (Remains the same) ---
def print_tree(node, prefix="", current_depth=0, max_depth=None):
    should_truncate = max_depth is not None and current_depth >= max_depth
    
    sorted_keys = sorted(node.keys())
    
    for i, key in enumerate(sorted_keys):
        value = node[key]
        is_last = (i == len(sorted_keys) - 1)
        tree_line = "└── " if is_last else "├── "
        
        if isinstance(value, list): # File Node
            if not should_truncate:
                print(f"{prefix}{tree_line}{key}")
                commit_prefix = prefix + ("    " if is_last else "│   ")
                for summary in value:
                    commit_info = f"[{summary['id']}] [{summary['status']}] ({summary['timestamp']}) {summary['summary']} - By {summary['author']}"
                    print(f"{commit_prefix}└─ {commit_info}")
            
        elif isinstance(value, dict): # Directory Node
            
            if should_truncate:
                print(f"{prefix}{tree_line}{key}/ [TRUNCATED HISTORY]")
                
                merged_commits = get_all_descendant_commits(value)
                
                commit_prefix = prefix + ("    " if is_last else "│   ")
                if merged_commits:
                    print(f"{commit_prefix}└─ Commits ({len(merged_commits)} total affecting sub-paths):")
                    for summary in merged_commits[:3]:
                        print(f"{commit_prefix}   -> [{summary['id']}] [{summary['status']}] {summary['summary']} - By {summary['author']}")
                    if len(merged_commits) > 3:
                        print(f"{commit_prefix}   ...and {len(merged_commits) - 3} more unique commits.")
            
            else:
                print(f"{prefix}{tree_line}{key}/")
                next_prefix = prefix + ("    " if is_last else "│   ")
                print_tree(value, next_prefix, current_depth + 1, max_depth)


# --- Main Logic: Summarize History ---
def summarize_local_history(repo_path, spec, max_depth=None):
    try:
        current_cwd = os.getcwd()

        # 1. Initialize Repo: Search upwards for the .git directory
        repo = Repo(current_cwd, search_parent_directories=True)
        repo_root = repo.working_dir
        file_to_commits = {}
        
        # --- SUBDIRECTORY FILTERING SETUP ---
        path_delimiter = "/"
        
        if current_cwd == repo_root:
            relative_path_prefix = ""
        else:
            relative_path_prefix = os.path.relpath(current_cwd, repo_root)
            relative_path_prefix = relative_path_prefix.replace(os.path.sep, path_delimiter)
            if relative_path_prefix and not relative_path_prefix.endswith(path_delimiter):
                 relative_path_prefix += path_delimiter
        
        # 2. Determine Filtering Method
        iter_args = {'rev': 'HEAD'}
        if spec.lower().endswith(('h', 'd', 'm')):
            since_time_str = _calculate_past_datetime(spec)
            iter_args['since'] = since_time_str
            print(f"\nFiltering by time (last {spec})...")
        elif spec.lower().endswith('c'):
            try:
                count = int(spec[:-1])
                if count <= 0: raise ValueError
            except ValueError:
                raise ValueError(f"Invalid commit count: {spec}. Use format like 5c.")
                
            iter_args['max_count'] = count
            print(f"\nFiltering by commit count (last {count} commits)...")
        else:
            raise ValueError(f"Invalid specification format: {spec}. Use time (1h, 2d, 30m) or commit count (5c).")


        # 3. Iterate over commits (data collection)
        for commit in repo.iter_commits(**iter_args):
            
            commit_time = datetime.datetime.fromtimestamp(commit.committed_date)
            commit_data = {
                'id': commit.hexsha[:8],
                'timestamp': commit_time.strftime('%Y-%m-%d %H:%M:%S'),
                'summary': commit.summary.strip(),
                'author': commit.author.name,
            }
            
            if commit.parents:
                diff_index = commit.parents[0].diff(commit)
            else:
                diff_index = commit.diff(None) 

            for diff in diff_index:
                status = diff.change_type
                file = diff.b_path if diff.b_path else diff.a_path 

                # 4. FILTER AND STRIP PREFIX (WHERE THE FIX IS APPLIED)
                if not relative_path_prefix or file.startswith(relative_path_prefix):
                    
                    file_stripped = file[len(relative_path_prefix):]
                    
                    if file_stripped: # Ensure path is not empty
                        
                        # --- FIX: Initialize as a list if new key ---
                        if file_stripped not in file_to_commits:
                            file_to_commits[file_stripped] = []
                        
                        file_to_commits[file_stripped].append({**commit_data, 'status': status})
        
        # 5. Build and Print the Tree Structure
        final_tree = {}
        
        def add_to_tree(path, commit_list):
            parts = path.split(path_delimiter)
            current_node = final_tree
            for part in parts[:-1]: 
                if part not in current_node:
                    current_node[part] = {}
                current_node = current_node[part]
            file_name = parts[-1]
            current_node[file_name] = commit_list

        for file_stripped, commits in file_to_commits.items():
            if file_stripped:
                add_to_tree(file_stripped, commits)
        
        if final_tree:
            print("---------------------------------------------------------")
            print(f"📦 Activity Summary for /{relative_path_prefix} ({spec}):")
            print_tree(final_tree, max_depth=max_depth)
        else:
            print(f"No commits found in /{relative_path_prefix} within the last {spec}.")

    except git.exc.InvalidGitRepositoryError:
        print("---------------------------------------------------------")
        print("🛑 Error: The current directory is not a valid Git repository.")
        print("Please run this script from inside a folder that is part of a Git project.")
        print("---------------------------------------------------------")
    except ValueError as ve:
        print(f"Input Error: {ve}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


# --- Command Line Execution (Remains the same) ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script_name.py <time_spec_or_commit_count> [--depth n]")
        print("Example: python script_name.py 1.5h")
        print("Example: python script_name.py 5c")
        print("Valid time specs: 1h, 2d, 30m, etc. | Commit specs: 1c, 10c, etc.")
        sys.exit(1)

    spec_input = sys.argv[1]
    
    # Parse optional --depth argument
    max_depth = None
    if len(sys.argv) > 2 and sys.argv[2] == '--depth':
        try:
            max_depth = int(sys.argv[3])
            if max_depth < 1: raise ValueError
        except (IndexError, ValueError):
            print("Error: --depth requires a positive integer value (e.g., --depth 2).")
            sys.exit(1)
            
    summarize_local_history(None, spec_input, max_depth)