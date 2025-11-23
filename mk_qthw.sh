#!/bin/bash

# ------------------------------------------------------------
# Usage:
#   ./render_two_versions.sh [-f] assignment.qmd [destination_dir] [-f]
#
# Renders multiple versions using TYPST engine.
# 1. file.pdf & file.html (Standard/No Solution)
# 2. file_qs.pdf & file_qs.html (Explicit No Solution)
# 3. file_with_solutions.pdf & html (With Solution)
#
# Only renders if assignment.qmd has changed, unless -f is used.
# ------------------------------------------------------------

# --- Initial Argument Check & Flag Parsing ---
FORCE_RENDER=false
ARGS=() # Array to hold clean positional arguments

# Iterate through all input arguments to find the flag
for arg in "$@"; do
    if [ "$arg" == "-f" ]; then
        FORCE_RENDER=true
    else
        ARGS+=("$arg") # Collect non-flag arguments
    fi
done

# Reset positional parameters
set -- "${ARGS[@]}" 

# --- Check remaining arguments ---
if [ $# -lt 1 ] || [ $# -gt 2 ]; then
    echo "Usage: $0 [-f] file.qmd [destination_directory]"
    exit 1
fi

QMD="$1"
DEST_DIR="$2"

# --- Validate inputs ---
if [ ! -f "$QMD" ]; then
  echo "Error: File '$QMD' not found."
  exit 1
fi

# --- Prepare Paths and Cache ---
BASENAME=$(basename "$QMD" .qmd)
CACHE_DIR=".render_cache"
TIMESTAMP_FILE="$CACHE_DIR/${BASENAME}.timestamp"

mkdir -p "$CACHE_DIR"

# --- Check for changes ---
NEEDS_RENDER=false
# Get current mod time (macOS/BSD syntax)
CURRENT_TIME=$(stat -f %m "$QMD")

# --- Logic: Check FORCE_RENDER vs Timestamp ---
if [ "$FORCE_RENDER" = true ]; then
    echo "'-f' flag detected. Forcing re-rendering..."
    NEEDS_RENDER=true
elif [ ! -f "$TIMESTAMP_FILE" ]; then
    echo "No previous render timestamp found. Rendering..."
    NEEDS_RENDER=true
else
    STORED_TIME=$(cat "$TIMESTAMP_FILE")
    if [ "$CURRENT_TIME" -gt "$STORED_TIME" ]; then
        echo "QMD file has been modified. Re-rendering..."
        NEEDS_RENDER=true
    else
        echo "No changes to $QMD. Skipping compilation."
        NEEDS_RENDER=false
    fi
fi

# --- Render (if needed) ---
if [ "$NEEDS_RENDER" = true ]; then
  
  # 1. NO SOLUTION (Question Sheet) - TYPST PDF
  echo "Rendering NO-SOLUTION version (Typst)..."
  quarto render "$QMD" \
    --execute-param show_solutions=false \
    --to typst \
    --output "${BASENAME}_qs.pdf" 


  # 2. NO SOLUTION - HTML
  quarto render "$QMD" \
    --execute-param show_solutions=false \
    --to html \
    --output "${BASENAME}_qs.html" 



  # 3. WITH SOLUTION - TYPST PDF
  echo "Rendering WITH-SOLUTION version (Typst)..."
  quarto render "$QMD" \
    --execute-param show_solutions=true \
    --to typst \
    --output "${BASENAME}_with_solutions.pdf"
  cp "${BASENAME}_with_solutions.pdf" "${BASENAME}.pdf"
  # 4. WITH SOLUTION - HTML
  quarto render "$QMD" \
    --execute-param show_solutions=true \
    --to html \
    --output "${BASENAME}_with_solutions.html"
  # Create the standard 'basename.html' copy immediately
  cp "${BASENAME}_with_solutions.html" "${BASENAME}.html"
  echo "  -> Created: ${BASENAME}.html"
  echo "------------------------------------------------"
  echo "All files rendered successfully."
  
  # Update timestamp
  echo "$CURRENT_TIME" > "$TIMESTAMP_FILE"
fi

# --- Release prompt (runs regardless of render) ---
if [ -n "$DEST_DIR" ]; then

  mkdir -p "$DEST_DIR"
  if [ ! -d "$DEST_DIR" ]; then
    echo "Error: Could not create destination directory '$DEST_DIR'."
    exit 1
  fi

  echo ""
  echo -n "Release to '$DEST_DIR'? (yes/no) [auto-cancel in 5s]: "

  if read -t 5 answ; then
    if [[ "$answ" =~ ^[Yy]([Ee][Ss])?$ ]]; then
      echo "Releasing files..."
      
      # Copy the Standard versions (Clean names)
      cp "${BASENAME}.pdf" "$DEST_DIR/"
      cp "${BASENAME}.html" "$DEST_DIR/"
      
      # Copy the Solutions versions
      cp "${BASENAME}_with_solutions.pdf" "$DEST_DIR/"
      cp "${BASENAME}_with_solutions.html" "$DEST_DIR/"
      
      # (Optional) Copy the _qs versions if you really want them in destination too
      # cp "${BASENAME}_qs.pdf" "$DEST_DIR/"
      
      echo "Done! Files copied to $DEST_DIR"
    else
      echo "Release cancelled by user."
    fi
  else
    echo ""
    echo "Timeout. Release skipped."
  fi

else
  echo "No destination directory specified. Skipping release."
fi
