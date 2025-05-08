#!/bin/bash

# Script to find processes by pattern and optionally kill them with confirmation.

# --- Configuration ---
# Use pgrep -f to match against the full command line including arguments
# Change to 'pgrep' if you only want to match the process name itself.
PGREP_COMMAND="pgrep -f"

# --- Argument Handling ---
if [ $# -lt 1 ]; then
    echo "Usage: $0 <pattern> [-k]"
    echo "  <pattern>: The pattern to search for in process command lines (using '$PGREP_COMMAND')."
    echo "  -k       : (Optional) If provided as the second argument, prompt to kill the found process(es) with SIGKILL (-9)."
    exit 1
fi

pattern="$1"
kill_flag="${2:-}" # Assign $2 to kill_flag, default to empty string if not set

# --- Find Processes ---
echo "Searching for processes matching pattern: '$pattern' using '$PGREP_COMMAND'"

# Execute pgrep and capture the output (PIDs, newline-separated)
# Using '-- "$pattern"' ensures patterns starting with '-' are handled correctly.
# Using '|| true' prevents the script from exiting if pgrep finds nothing (exit code 1)
pids=$($PGREP_COMMAND -- "$pattern" || true)

# --- Process Results ---
if [ -z "$pids" ]; then
    echo "No processes found matching '$pattern'."
    exit 0
fi

# If we found PIDs, list them clearly
echo "Found matching PID(s):"
# List PIDs one per line for clarity, along with their commands using ps
echo "$pids" | while IFS= read -r pid; do
    # Use ps to show the command for context. Adjust 'ps' options as needed.
    # '-o pid,args=' shows PID and command without headers
    ps -p "$pid" -o pid=,args=
done

# --- Kill Logic (if -k is specified) ---
if [ "$kill_flag" == "-k" ]; then
    echo # Add a newline for spacing

    # Format PIDs for the prompt (space-separated)
    pids_oneline=$(echo "$pids" | tr '\n' ' ')

    # Prompt for confirmation
    # Use /dev/tty to ensure prompt goes to terminal even if output is redirected
    read -p "--> Do you want to KILL (signal -9) process(es) $pids_oneline? (y/N): " confirm </dev/tty

    # Default to 'no' if user just presses Enter
    confirm_lower=$(echo "${confirm:-n}" | tr '[:upper:]' '[:lower:]') # Convert to lowercase, default 'n'

    if [[ "$confirm_lower" == "y" ]]; then
        echo "Attempting to kill process(es) with SIGKILL (-9)..."
        killed_count=0
        failed_count=0
        # Loop through each found PID and kill it
        echo "$pids" | while IFS= read -r pid; do
            echo -n "  Sending SIGKILL to PID $pid... "
            # Use kill -9 (SIGKILL)
            if kill -9 "$pid" 2>/dev/null; then
                echo "OK"
                ((killed_count++))
            else
                # Check exit status of kill: 0=success, 1=failed (no permission, no such process)
                echo "FAILED (Process gone? No permission?)"
                ((failed_count++))
            fi
        done
        echo "Kill Summary: $killed_count process(es) signaled, $failed_count failed attempts."
    else
        echo "Kill operation aborted by user."
    fi
else
    # If -k was not specified, we've already listed the PIDs, so just exit.
    echo # Add a newline for spacing
    echo "Use the '-k' option as the second argument to enable killing."
fi

exit 0