#!/bin/bash

# Get the current timestamp in a readable format (e.g., YYYY-MM-DD HH:MM:SS)
# You can customize the format string as needed. See 'man date' for options.
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Get the computer's hostname
# 'hostname' gets the network name.
# Alternatively, use 'scutil --get ComputerName' for the user-friendly name
# from System Preferences > Sharing, if desired.
COMPUTER_NAME=$(hostname)

# Construct the commit message
COMMIT_MESSAGE="update at ${TIMESTAMP} from ${COMPUTER_NAME}"

# Execute the git commit command
# -a: stage all modified/deleted tracked files
# -m: use the provided commit message
echo "Running git commit with message: \"${COMMIT_MESSAGE}\""
git commit -am "${COMMIT_MESSAGE}"

# Optional: Print exit status of git commit
status=$?
if [ $status -eq 0 ]; then
  echo "Git commit successful."
else
  echo "Git commit failed with status ${status}."
  # You might see a failure if there are no changes to commit,
  # or if you are not in a git repository.
fi

exit $status

