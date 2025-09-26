#!/bin/bash

# A script to add a pattern to the root .gitignore and apply the change.
# It works from any subdirectory within the Git repository.

# Stop the script if any command fails
set -e

# --- 1. Initial Checks ---

# Check if an argument was provided
if [ -z "$1" ]; then
    echo "❌ Error: No pattern supplied."
    echo "Usage: ./git-ignore.sh '<pattern_to_ignore>'"
    echo "Example: ./git-ignore.sh '*.log' or ./git-ignore.sh 'dist/'"
    exit 1
fi

PATTERN="$1"

# Check if this is a Git repository before proceeding
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    echo "❌ Error: This is not a Git repository."
    exit 1
fi

# Check for uncommitted changes. This is a crucial safety check.
if [ -n "$(git status --porcelain)" ]; then
    echo "❌ Error: Your working directory is not clean."
    echo "Please commit or stash your changes before running this script."
    exit 1
fi

echo "✅ Pre-flight checks passed."

# --- 2. Navigate to Repo Root ---

# Find the root directory of the repository
REPO_ROOT=$(git rev-parse --show-toplevel)
echo "📂 Repository root found at: $REPO_ROOT"

# Change to the root directory to ensure all commands run in the correct context
cd "$REPO_ROOT"
echo "✅ Changed directory to repository root."

# --- 3. Update .gitignore and Commit ---

echo "👉 Step 1: Adding '$PATTERN' to .gitignore..."

# Append the pattern to the .gitignore file in the root directory.
echo -e "\n# Ignore '$PATTERN' (added by script)" >> .gitignore

# Stage and commit the change to .gitignore
git add .gitignore
git commit -m "Update .gitignore to ignore '$PATTERN'"

echo "✅ .gitignore updated and committed."

# --- 4. Untrack Files and Re-commit ---

echo "👉 Step 2: Removing all tracked files from the index..."

# Remove everything from the Git index (staging area).
git rm -r --cached . > /dev/null

echo "✅ Index cleared."

echo "👉 Step 3: Re-adding all files, respecting new .gitignore rules..."

# Re-add everything. Git will now skip files matching the new pattern.
git add .

echo "✅ Files re-added to index."

# --- 5. Final Commit ---

echo "👉 Step 4: Committing the updated file list..."

# Commit the final state.
git commit -m "Apply new ignore rule for '$PATTERN' and re-track files"

echo "🎉 Success! The pattern '$PATTERN' is now ignored and the repository has been updated."
