#!/usr/bin/zsh
#
# Function to add a pattern to .gitignore, remove tracked files matching that pattern,
# commit the changes, and push to the 'main' branch.
#
# Usage: ./git_ignore_and_clean.zsh <pattern_to_ignore>
# Example: ./git_ignore_and_clean.zsh "*.log"
#
# Note: This script assumes you are in a Git repository and are authenticated to push.

# Check if the repository is clean before starting
if ! git diff-index --quiet HEAD --; then
    echo "🚨 Error: Your working directory is not clean. Please commit or stash your changes before running this script."
    exit 1
fi

# Function definition
function ignore_and_clean() {
    local pattern="$1"
    local gitignore_file=".gitignore"

    # 1. Check for the pattern argument
    if [[ -z "$pattern" ]]; then
        echo "🚨 Error: You must provide a file pattern to ignore."
        echo "Usage: $0 <pattern_to_ignore>"
        return 1
    fi

    echo "--- Starting Git Ignore and Clean Workflow ---"
    echo "Pattern to process: $pattern"

    # 2. Add the pattern to .gitignore
    echo "\n>>> 1. Adding '$pattern' to $gitignore_file..."
    
    # Check if the pattern is already in .gitignore
    if grep -qF -- "$pattern" "$gitignore_file" 2>/dev/null; then
        echo "✅ Pattern '$pattern' already exists in $gitignore_file. Skipping addition."
    else
        echo "$pattern" >> "$gitignore_file"
        # Check for successful file modification
        if [[ $? -eq 0 ]]; then
            echo "Successfully appended '$pattern' to $gitignore_file."
            git add "$gitignore_file"
            if [[ $? -ne 0 ]]; then
                echo "❌ Failed to stage $gitignore_file."
                return 1
            fi
        else
            echo "❌ Failed to write to $gitignore_file. Check permissions or file existence."
            return 1
        fi
    fi

    # 3. Remove files matching the pattern from Git tracking (but keep local copy)
    echo "\n>>> 2. Removing tracked files matching '$pattern' using 'git rm --cached'..."
    
    # Use 'git ls-files' to find files that are currently tracked and match the pattern
    local tracked_files=$(git ls-files -i --exclude-from="$gitignore_file" -- "$pattern")
    
    if [[ -z "$tracked_files" ]]; then
        echo "✅ No currently tracked files found matching '$pattern'. Skipping 'git rm --cached'."
    else
        echo "Found the following tracked files to remove from index (retaining local copy):"
        echo "$tracked_files" | while read -r file; do
            echo "   - $file"
        done
        
        # Execute the removal
        # Use a subshell and 'xargs' for robust handling of file names with spaces
        echo "$tracked_files" | xargs -r git rm --cached
        
        if [[ $? -eq 0 ]]; then
            echo "✅ Successfully removed matching files from Git index."
        else
            echo "❌ Git rm failed. Please review the previous error messages."
            return 1
        fi
    fi


    # 4. Commit the changes
    echo "\n>>> 3. Committing changes..."
    
    # Check if there are any changes staged to commit (either .gitignore update or files removed)
    if git diff --cached --quiet --exit-code; then
        echo "⚠️ No changes detected to commit after processing. Exiting commit phase."
    else
        local commit_msg="chore: Ignore $pattern and remove already-tracked instances."
        git commit -m "$commit_msg"
        
        if [[ $? -eq 0 ]]; then
            echo "✅ Successfully committed with message: '$commit_msg'"
        else
            echo "❌ Git commit failed."
            return 1
        fi
    fi

    # 5. Push to the main branch
    echo "\n>>> 4. Pushing changes to 'origin/main'..."
    
    # Check if 'main' exists locally or remotely. Fallback to 'master' if 'main' is not found.
    local remote_branch="main"
    if ! git show-ref --verify --quiet refs/remotes/origin/main && ! git show-ref --verify --quiet refs/heads/main; then
        if git show-ref --verify --quiet refs/remotes/origin/master || git show-ref --verify --quiet refs/heads/master; then
            remote_branch="master"
            echo "⚠️ 'main' branch not found. Falling back to pushing to 'origin/master'."
        else
            echo "❌ Neither 'main' nor 'master' branch found. Cannot push."
            return 1
        fi
    fi

    git push origin "$remote_branch"
    
    if [[ $? -eq 0 ]]; then
        echo "\n🎉 Success! Changes pushed to origin/$remote_branch."
    else
        echo "\n❌ Git push failed. Please check your network connection and permissions."
        return 1
    fi

    echo "\n--- Workflow Complete ---"
}

# Execute the function with the provided arguments
ignore_and_clean "$@"