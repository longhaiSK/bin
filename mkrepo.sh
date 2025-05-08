#!/bin/bash

# --- Script to create a new local Git repository and add GitHub remote ---

# Check if a repository name was provided as an argument
if [ -z "$1" ]; then
  echo "Usage: $0 <repository_name> [github_username]"
  echo "Please provide a name for the new repository directory."
  echo "Optionally provide your GitHub username as the second argument."
  exit 1
fi

# Assign the first argument to the repo_name variable
repo_name="$1"
github_username="$2" # Assign second argument (optional)

# Check if a directory with that name already exists
if [ -d "$repo_name" ]; then
  echo "Error: Directory '$repo_name' already exists."
  exit 1
fi

# Prompt for GitHub username if not provided as an argument
if [ -z "$github_username" ]; then
    echo "Please enter your GitHub username (needed to set the remote URL):"
    read -p "> " github_username
    if [ -z "$github_username" ]; then
        echo "Error: GitHub username cannot be empty."
        exit 1
    fi
fi

# Create the new directory
echo "Creating directory '$repo_name'..."
mkdir "$repo_name"
if [ $? -ne 0 ]; then
    echo "Error: Failed to create directory '$repo_name'."
    exit 1
fi

# Change into the new directory
cd "$repo_name" || exit # Exit if cd fails

# Initialize the Git repository (using -b main to set the default branch)
echo "Initializing Git repository..."
git init -b main
if [ $? -ne 0 ]; then
    echo "Error: Failed to initialize Git repository."
    exit 1
fi

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

# Construct the SSH URL (assuming GitHub repo name matches local folder name)
ssh_url="git@github.com:$github_username/$repo_name.git"
echo "Adding remote origin: $ssh_url"

# Add the GitHub repository as the remote origin
git remote add origin "$ssh_url"
if [ $? -ne 0 ]; then
    echo "Error: Failed to add remote origin '$ssh_url'."
    echo "Please check the username and ensure a repository named '$repo_name' exists on GitHub for user '$github_username'."
    # Keep going, but inform the user
else
    echo "Successfully added remote origin."
fi


# Provide confirmation message
echo "" # Blank line for spacing
echo "Successfully created local Git repository '$repo_name'!"
echo "Current directory: $(pwd)"
if [ $? -eq 0 ]; then # Check if remote add was successful
    echo "Remote 'origin' added pointing to '$ssh_url'."
fi
echo "Next steps:"
echo "  1. Ensure the corresponding empty repository '$repo_name' exists on GitHub under user '$github_username'."
echo "  2. Add your project files."
echo "  3. Stage and commit your changes (\`git add .\`, \`git commit -m 'Your message'\`)."
echo "  4. Push your initial commit: git push -u origin main"

exit 0
