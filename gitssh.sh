#!/bin/bash

# --- Find the current remote URL for 'origin' ---
# Filters 'git remote -v' to get the fetch URL.
https_url=$(git remote -v | grep '^origin' | grep '(fetch)' | awk '{print $2}')

# --- Check if the URL is a GitHub HTTPS URL ---
if [[ -n "$https_url" && "$https_url" == https://github.com/* ]]; then
  # It's a GitHub HTTPS URL; proceed with conversion.
  echo "Found GitHub HTTPS remote: $https_url"

  # --- Convert the URL from HTTPS to SSH ---
  # Remove the 'https://github.com/' prefix to get the 'user/repo' part.
  user_repo=$(echo "$https_url" | sed 's|https://github.com/||')
  # Construct the new SSH URL.
  ssh_url="git@github.com:$user_repo"

  # --- Execute the command to update the remote ---
  echo "Switching 'origin' to use SSH..."
  git remote set-url origin "$ssh_url"
  
  # --- Verify the change ---
  echo "" # Add a newline for clarity
  echo "Success! Remote 'origin' is now set to:"
  # Show the new remote URLs to confirm the change was successful.
  git remote -v

elif [[ -n "$https_url" ]]; then
  # A URL was found, but it wasn't a GitHub HTTPS URL.
  echo "Remote 'origin' is not using a GitHub HTTPS URL."
  echo "Current URL: $https_url"
else
  # No fetch URL found for 'origin'.
  echo "Error: Could not find the fetch URL for the 'origin' remote."
  echo "Please ensure you are inside a Git repository."
fi