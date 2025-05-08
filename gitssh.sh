#!/bin/bash

# Get the fetch URL for the 'origin' remote
# Filters output of 'git remote -v' to find the line starting with 'origin',
# containing '(fetch)', and extracts the second field (the URL).
https_url=$(git remote -v | grep '^origin' | grep '(fetch)' | awk '{print $2}')

# Check if we successfully got a URL ($https_url is not empty)
# AND if it starts with the GitHub HTTPS prefix.
if [[ -n "$https_url" && "$https_url" == https://github.com/* ]]; then
  # It's a GitHub HTTPS URL. Extract the user/repo part.
  # Use sed to remove the 'https://github.com/' prefix.
  # Using '|' as the sed delimiter avoids issues with '/' in the URL.
  user_repo=$(echo "$https_url" | sed 's|https://github.com/||')

  # Construct the corresponding SSH URL.
  ssh_url="git@github.com:$user_repo"

  # Construct the command string
  git_command="git remote set-url origin $ssh_url"

  # Print the command that will be copied
  echo "Command to switch 'origin' to SSH:"
  echo "$git_command"
  echo "" # Add a newline for clarity

  # Attempt to copy the command to the clipboard on macOS
  if [[ "$OSTYPE" == "darwin"* ]]; then
      # macOS
      echo "$git_command" | pbcopy
      echo "Command copied to clipboard using pbcopy."
  else
      # Not macOS
      echo "This script is configured to automatically copy to clipboard only on macOS."
      echo "You can still copy the command manually from above."
  fi

elif [[ -n "$https_url" ]]; then
  # A URL was found, but it wasn't a GitHub HTTPS URL.
  # It might already be SSH or point to a different host.
  echo "Origin remote is already using a non-HTTPS URL or points elsewhere:"
  echo "$https_url"
else
  # No fetch URL found for 'origin'.
  echo "Could not find the fetch URL for the 'origin' remote."
  echo "Please ensure you are inside a Git repository directory."
fi # Closes the if/elif/else block.

