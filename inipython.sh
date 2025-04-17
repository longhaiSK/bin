
#!/bin/bash

# --- Prompt User with Timeout ---
# Inform user about the potential slow step

activate_env="no" # Default: DO NOT activate

# -t 3: Timeout after 3 seconds
# -r: Prevent backslash interpretation
# -p "...": Display prompt text
read -t 3 -r -p "Press any key to activate 'jupyter-2025' environment now: (auto-skips after 3s)" user_confirmation

# Check exit status of 'read'. 0 = input received; non-zero = timeout/error.
if [ $? -eq 0 ]; then
    # Input WAS received before timeout. Set to 'yes' for any key press.
    activate_env="yes"
else
    # Timeout occurred (or read error) - $? was not 0
    # Print a newline because the timeout doesn't add one.
    echo
fi

# --- Conditionally Activate ---
if [ "$activate_env" == "yes" ]; then
    # --- Activate Block ---
    echo "Proceeding with activation..."
    conda activate jupyter-2025 || {
      # Handle activation error
      echo "Error: Failed to activate conda environment 'jupyter-2025'." >&2
      echo "Please ensure the environment exists ('conda info --envs')." >&2
      exit 1 # Exit the script with an error code
    }
    echo "Successfully activated 'jupyter-2025'."
    # --- End Activate Block ---
else
    # --- Skip Block ---
    # Just print the command that would have run, indicating it was skipped.
    echo -e "Type: * conda activate jupyter-2025 * to activate it.\n"
    echo -e "Type: * conda info --envs * to list envs"
    # --- End Skip Block ---
fi
