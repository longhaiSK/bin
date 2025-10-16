#!/bin/bash

# --- Script to create a new local Git repository AND a remote GitHub repository using 'gh' ---

# --- Prerequisites Check ---
# Check if gh is installed
if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI ('gh') not found. Please install it first."
    echo "See: https://cli.github.com/"
    exit 1
fi

# Check if user is logged in to gh
if ! gh auth status &> /dev/null; then
    echo "Error: Not logged in to GitHub CLI. Please run 'gh auth login'."
    exit 1
fi
echo "GitHub CLI authenticated."

# --- Input ---
# Check if a repository name was provided as an argument
if [ -z "$1" ]; then
  echo "Usage: $0 <repository_name>"
  echo "Please provide a name for the new repository (will be used locally and on GitHub)."
  exit 1
fi

# Assign the first argument to the repo_name variable
repo_name="$1"

# --- Local Setup ---
# Check if a directory with that name already exists
if [ -d "$repo_name" ]; then
  echo "Error: Directory '$repo_name' already exists locally."
  exit 1
fi

# Create the new directory
echo "Creating local directory '$repo_name'..."
mkdir "$repo_name"
if [ $? -ne 0 ]; then
    echo "Error: Failed to create directory '$repo_name'."
    exit 1
fi

# Change into the new directory
cd "$repo_name" || exit # Exit if cd fails
echo "Changed directory to $(pwd)"

# Initialize the Git repository (using -b main to set the default branch)
echo "Initializing local Git repository..."
git init -b main
if [ $? -ne 0 ]; then
    echo "Error: Failed to initialize Git repository."
    exit 1
fi

# --- GitHub Remote Creation ---
echo "Creating GitHub repository '$repo_name' using 'gh'..."
# --public: creates a public repo (use --private for private)
# --source=.: uses the current directory as the source
# --remote=origin: automatically adds the remote named 'origin'
# --push: attempts to push the repo after creation (we'll do this manually after first commit)
# Using simple create first, then add remote manually for more control flow
gh repo create "$repo_name" --public --description "Created via script"
if [ $? -ne 0 ]; then
    echo "Error: Failed to create GitHub repository using 'gh'."
    echo "Please check 'gh' output above. Does the repo already exist on GitHub?"
    exit 1
fi
echo "Successfully created GitHub repository."

# Add the remote using the gh command's output (more robust than guessing URL)
# Get the SSH URL for the newly created repo
ssh_url=$(gh repo view "$repo_name" --json sshUrl -q .sshUrl)
if [ -z "$ssh_url" ]; then
    echo "Error: Could not retrieve SSH URL for the new repository using 'gh'."
    exit 1
fi
echo "Adding remote origin: $ssh_url"
git remote add origin "$ssh_url"
if [ $? -ne 0 ]; then
    echo "Error: Failed to add remote origin '$ssh_url' using git."
    exit 1
fi
echo "Successfully added remote origin."


# --- Initial Commit ---
# Prompt the user for a README message
echo "Please enter a short description for the README.txt file:"
read -p "> " readme_message # -p displays the prompt without a newline

# Create the README.txt file with the user's message
echo "Creating README.txt..."
echo "$readme_message" > README.txt

# Add the README.txt file to staging
echo "Adding README.txt to staging area..."
git add README.txt

# Make the initial commit
echo "Making initial commit..."
git commit -m "Initial commit: Add README.txt"
if [ $? -ne 0 ]; then
    echo "Error: Failed to make initial commit."
    exit 1
fi

# --- Push to Remote ---
echo "Pushing initial commit to GitHub (origin main)..."
git push -u origin main
if [ $? -ne 0 ]; then
    echo "Error: Failed to push initial commit to GitHub."
    echo "Please check your SSH key setup and GitHub permissions."
    exit 1
fi

# --- Confirmation ---
echo "" # Blank line for spacing
echo "Successfully created local repository, GitHub repository, and pushed initial commit!"
echo "Local repository: $(pwd)"
echo "Remote repository: $ssh_url"
echo "You can now add more files, commit, and push."

exit 0
