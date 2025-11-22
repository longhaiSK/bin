#!/bin/bash

# ------------------------------------------------------------
# Usage:
#   ./render_two_versions.sh [-f] assignment.qmd [destination_dir] [-f]
#
# Renders four files only if assignment.qmd has changed.
# Use -f to **force compilation**, overriding the change check.
# The -f flag can be placed anywhere.
# ------------------------------------------------------------

# --- Initial Argument Check & Flag Parsing ---
FORCE_RENDER=false
ARGS=() # Array to hold clean positional arguments (QMD and DEST_DIR)

# Iterate through all input arguments to find the flag and separate the positional args
for arg in "$@"; do
    if [ "$arg" == "-f" ]; then
        FORCE_RENDER=true
    else
        ARGS+=("$arg") # Collect non-flag arguments
    fi
done

# Reset positional parameters ($1, $2, etc.) using the clean array
set -- "${ARGS[@]}" 

# --- Check remaining arguments ---
# Now we check if we have 1 (QMD) or 2 (QMD and DEST_DIR) arguments remaining
if [ $# -lt 1 ] || [ $# -gt 2 ]; then
    echo "Usage: $0 [-f] file.qmd [destination_directory]"
    exit 1
fi

QMD="$1"
DEST_DIR="$2" # This will be empty if not provided

# --- Validate inputs ---
if [ ! -f "$QMD" ]; then
  echo "Error: File '$QMD' not found."
  exit 1
fi

# --- Prepare Paths and Cache ---
BASENAME=$(basename "$QMD" .qmd)
CACHE_DIR=".render_cache"
TIMESTAMP_FILE="$CACHE_DIR/${BASENAME}.timestamp"

# Ensure cache directory exists
mkdir -p "$CACHE_DIR"

# --- Check for changes ---
NEEDS_RENDER=false
# Get current mod time (macOS/BSD syntax)
CURRENT_TIME=$(stat -f %m "$QMD")

# --- Logic: Check FORCE_RENDER first ---
if [ "$FORCE_RENDER" = true ]; then
    echo "'-f' flag detected. Forcing re-rendering..."
    NEEDS_RENDER=true
elif [ ! -f "$TIMESTAMP_FILE" ]; then
    # No timestamp file, must render
    echo "No previous render timestamp found. Rendering..."
    NEEDS_RENDER=true
else
    # Timestamp file exists, let's compare
    STORED_TIME=$(cat "$TIMESTAMP_FILE")
    if [ "$CURRENT_TIME" -gt "$STORED_TIME" ]; then
        echo "QMD file has been modified. Re-rendering..."
        NEEDS_RENDER=true
    else
        # Only path where NEEDS_RENDER is false
        echo "No changes to $QMD. Skipping compilation."
        NEEDS_RENDER=false
    fi
fi

# --- Render (if needed) ---
if [ "$NEEDS_RENDER" = true ]; then
  echo "Rendering NO-SOLUTION version..."
  # Use distinct name _qs for stability
  quarto render "$QMD" \
    --execute-param show_solutions=false \
    --to pdf \
    --output "${BASENAME}_qs.pdf" 

  quarto render "$QMD" \
    --execute-param show_solutions=false \
    --to html \
    --output "${BASENAME}_qs.html" 

  echo "Rendering WITH-SOLUTION version..."
  quarto render "$QMD" \
    --execute-param show_solutions=true \
    --to pdf \
    --output "${BASENAME}_with_solutions.pdf"

  quarto render "$QMD" \
    --execute-param show_solutions=true \
    --to html \
    --output "${BASENAME}_with_solutions.html"

  echo "All four files rendered in current directory."
  
  # Record the new timestamp after successful render
  echo "$CURRENT_TIME" > "$TIMESTAMP_FILE"
  echo "Updated render timestamp."

fi

# --- Release prompt (runs regardless of render) ---
if [ -n "$DEST_DIR" ]; then

  mkdir -p "$DEST_DIR"
  if [ ! -d "$DEST_DIR" ]; then
    echo "Error: Could not create destination directory '$DEST_DIR'."
    exit 1
  fi

  echo ""
  echo -n "Release or not? (yes/no) [auto-cancel in 5s]: "

  if read -t 5 answ; then
    if [[ "$answ" =~ ^[Yy]([Ee][Ss])?$ ]]; then
      echo "Releasing files to $DEST_DIR..."
      # Copy distinct source names back to clean target names
      cp "${BASENAME}_qs.pdf" "$DEST_DIR/${BASENAME}.pdf"
      cp "${BASENAME}_qs.html" "$DEST_DIR/${BASENAME}.html" 
      cp "${BASENAME}_with_solutions.pdf" "$DEST_DIR"
      cp "${BASENAME}_with_solutions.html" "$DEST_DIR"
      echo "Done!"
    else
      echo "Release cancelled by user. Files remain in current directory."
    fi
  else
    echo ""
    echo "Timeout. Giving up. Files remain in current directory."
  fi

else
  echo "No destination directory specified. Skipping release."
fi