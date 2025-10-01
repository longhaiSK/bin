#!/bin/bash

# A script that finds all git repos in specified root directories.
# It either adds a new .gitignore pattern and rebuilds the index,
# or just rebuilds the index for each found repository.

# --- 1. Configuration ---

# Define the root directories to search for Git repositories.
# You can add multiple paths here.
ROOTS=(
    "$HOME/Github"
)

# --- 2. Determine Operation Mode ---

# Check if an argument (a pattern) was provided. This determines the mode for ALL repos.
if [ -n "$1" ]; then
    MODE="add_pattern"
    PATTERN="$1"
    FINAL_COMMIT_MSG="Apply new ignore rule for '$PATTERN' and re-track files"
    echo "🚀 Mode: Add pattern '$PATTERN' and rebuild all repos."
else
    MODE="rebuild_only"
    FINAL_COMMIT_MSG="Re-build index to apply existing .gitignore rules"
    echo "🚀 Mode: Re-build all repos using their existing .gitignore files."
fi

# --- 3. Find and Process Repositories ---

for root in "${ROOTS[@]}"; do
    if [ ! -d "$root" ]; then
        echo -e "\n⚠️  Warning: Search directory '$root' does not exist. Skipping."
        continue
    fi

    echo -e "\n🔍 Searching for repositories in: $root"

    # Find all .git directories and process their parent directory.
    # Using -print0 and a while loop is the safest way to handle paths with spaces.
    find "$root" -type d -name ".git" -print0 | while IFS= read -r -d '' git_dir; do
        REPO_PATH=$(dirname "$git_dir")
        
        echo -e "\n-------------------------------------------------------"
        echo "📂 Processing Repository: $REPO_PATH"
        
        # Change to the repository's root directory
        cd "$REPO_PATH" || { echo "❌ Failed to cd into $REPO_PATH. Skipping."; continue; }

        # --- Per-Repo Pre-flight Check ---
        if [ -n "$(git status --porcelain)" ]; then
            echo "⚠️  Skipping: Working directory is not clean."
            continue # Skip to the next repository
        fi
        echo "✅ Pre-flight checks passed."

        # --- Add Pattern (if in that mode) ---
        if [ "$MODE" = "add_pattern" ]; then
            echo "👉 Step 1: Adding '$PATTERN' to .gitignore..."
            echo -e "\n# Ignore '$PATTERN' (added by script)" >> .gitignore
            git add .gitignore
            git commit -m "Update .gitignore to ignore '$PATTERN'"
            echo "✅ .gitignore updated and committed."
        fi
        
        # --- Common Re-build Steps ---
        if [ "$MODE" = "rebuild_only" ] && [ ! -f ".gitignore" ]; then
             echo "🤔 No .gitignore file found. Nothing to re-apply."
             continue # Skip to the next repo
        fi

        echo "👉 Step 2: Removing all tracked files from the index..."
        git rm -r --cached . > /dev/null
        echo "✅ Index cleared."
        
        echo "👉 Step 3: Re-adding all files, respecting .gitignore rules..."
        git add .
        echo "✅ Files re-added to index."

        # --- Final Commit ---
        if ! git diff --staged --quiet; then
            echo "👉 Step 4: Committing the updated file list..."
            git commit -m "$FINAL_COMMIT_MSG"
            echo "🎉 Success! Repository has been updated."
        else
            echo "✅ No changes to commit. Index was already correct."
        fi
    done
done

echo -e "\n-------------------------------------------------------"
echo "✨ All repositories processed."
