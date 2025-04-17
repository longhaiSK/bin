#!/usr/bin/env bash

# --- Jupytext Python to Notebook Converter (with Preprocessing & Intermediate File) ---
#
# Converts a Python script (.py) to a Jupyter Notebook (.ipynb) using jupytext.
# Includes a preprocessing step using perl to convert lines starting
# with '# # ', '# ## ', etc. into Jupytext markdown cells, preserving heading level.
# Saves the preprocessed Python script to a new file before final conversion.
#
# Usage:
#   ./convert_to_notebook.sh <input_python_script.py> [output_notebook.ipynb]
#
# Arguments:
#   input_python_script.py : Path to the input Python script.
#   output_notebook.ipynb  : (Optional) Path for the output Jupyter Notebook.
#                            If not provided, defaults to the input filename
#                            with the extension changed to .ipynb.
# -------------------------------------------------

# --- Configuration ---
# Exit immediately if a command exits with a non-zero status.
set -e

# --- Argument Handling ---

# Check if at least one argument (input file) is provided
if [ "$#" -lt 1 ]; then
  echo "Error: Input Python script path is required."
  echo "Usage: $0 <input.py> [output.ipynb]"
  exit 1
fi

# Assign arguments to variables
input_file="$1"
output_file_arg="$2" # Store potential output argument

# --- Input File Validation ---

# Check if the input file exists
if [ ! -f "$input_file" ]; then
  echo "Error: Input file '$input_file' not found."
  exit 1
fi

# Optional: Warn if input file doesn't end with .py
if [[ "$input_file" != *.py ]]; then
  echo "Warning: Input file '$input_file' does not seem to be a Python script (.py extension missing)."
fi

# --- Determine Intermediate and Output Filenames ---

intermediate_py_file=""
output_file=""

# Derive intermediate filename (<base>-created-by-nb2py.py)
if [[ "$input_file" == *.py ]]; then
  base_name="${input_file%.py}"
  intermediate_py_file="${base_name}-created-by-nb2py.py"
else
  intermediate_py_file="${input_file}-created-by-nb2py.py"
fi

# Determine final output filename
if [ -z "$output_file_arg" ]; then
  # Output filename was NOT provided, derive it from the input filename
  if [[ "$input_file" == *.py ]]; then
    output_file="${input_file%.py}.ipynb"
  else
    output_file="${input_file}.ipynb"
    echo "Warning: Input file did not end with .py. Appending .ipynb for output filename."
  fi
  echo "Output filename not provided. Defaulting to: '$output_file'"
else
  # Output filename WAS provided
  output_file="$output_file_arg"
  if [[ "$output_file" != *.ipynb ]]; then
    echo "Warning: Specified output file '$output_file' does not end with .ipynb. Using it anyway."
  fi
fi

# --- Preprocessing Step ---

echo "Preprocessing '$input_file' to handle heading lines..."
echo "Saving intermediate file to '$intermediate_py_file'"

# Use perl for potentially more robust regex handling and newline insertion.
# Regex Breakdown:
# ^#\s+    : Starts with '# ' followed by one or more whitespace chars
# (#+)     : Capture group 1 ($1): one or more '#' characters (the heading level)
# \s+      : One or more whitespace chars after the heading hashes
# (.*)     : Capture group 2 ($2): the heading text
# \s*$     : Optional trailing whitespace until the end of the line
# Replacement Breakdown:
# # %% [markdown] : Jupytext marker
# \n#             : Newline and start markdown content line with '#'
# $1              : Insert captured heading level (e.g., '#', '##')
#                 : Space after heading marker
# $2              : Insert captured heading text
perl -pe 's/^#\s+(#+)\s+(.*)\s*$/# %% [markdown]\n# $1 $2/' "$input_file" > "$intermediate_py_file"


# Check if perl command was successful
if [ $? -ne 0 ]; then
  echo "Error: Preprocessing step failed for '$input_file'."
  # Clean up intermediate file if perl failed
  rm -f "$intermediate_py_file"
  exit 1
fi

echo "Preprocessing complete. Intermediate file saved."
echo "You can inspect '$intermediate_py_file' to check the substitutions."

# --- Execute Conversion ---

echo "Attempting to convert intermediate file '$intermediate_py_file' to '$output_file' using jupytext..."

# Run the jupytext command using the INTERMEDIATE file as input
# Quote variables to handle spaces
jupytext --to notebook "$intermediate_py_file" -o "$output_file"

# Check the exit status of the jupytext command
jupytext_exit_status=$? # Store exit status

if [ $jupytext_exit_status -eq 0 ]; then
  echo "Conversion successful! Output saved to '$output_file'"
else
  # Jupytext command likely printed its own error message
  echo "Error: Jupytext conversion failed."
  # Keep the intermediate file for debugging in case of jupytext failure
  exit 1 # Exit with a non-zero status to indicate failure
fi

# --- Script End ---
# Optionally remove the intermediate file on success?
# Uncomment the next line if you want to automatically delete the intermediate file after successful conversion
# rm -f "$intermediate_py_file"

exit 0
