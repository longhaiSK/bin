#!/bin/bash

# Find all files in the current directory
files=(*.*)

# Extract all numbers before the dot and find the maximum length
max_digits=0
declare -A file_map

for file in "${files[@]}"; do
  if [[ "$file" =~ ([a-zA-Z]*)([0-9]+)(\..*) ]]; then
    prefix="${BASH_REMATCH[1]}"
    number="${BASH_REMATCH[2]}"
    extension="${BASH_REMATCH[3]}"
    
    file_map["$file"]="$prefix $number $extension"
    
    # Find the max digit length
    if [[ ${#number} -gt $max_digits ]]; then
      max_digits=${#number}
    fi
  fi
done

# Check if there are any files to rename
if [[ ${#file_map[@]} -eq 0 ]]; then
  echo "No files with numbers before '.' found. Exiting."
  exit 0
fi

# Display proposed changes
echo "The following changes will be made:"
for file in "${!file_map[@]}"; do
  read prefix number extension <<< "${file_map[$file]}"
  new_number=$(printf "%0${max_digits}d" "$number")
  new_name="${prefix}${new_number}${extension}"
  
  if [[ "$file" != "$new_name" ]]; then
    echo "$file → $new_name"
  fi
done

# Ask for confirmation
read -p "Do you want to proceed with renaming? (y/n): " confirm
if [[ "$confirm" != "y" ]]; then
  echo "Operation canceled."
  exit 0
fi

# Rename files
for file in "${!file_map[@]}"; do
  read prefix number extension <<< "${file_map[$file]}"
  new_number=$(printf "%0${max_digits}d" "$number")
  new_name="${prefix}${new_number}${extension}"
  
  if [[ "$file" != "$new_name" ]]; then
    mv "$file" "$new_name"
    echo "Renamed: $file → $new_name"
  fi
done

echo "All files have been successfully renamed."
