#!/usr/bin/env python3
import socket
import requests
import subprocess
import re
from datetime import datetime

# --- CONFIGURATION ---
# The exact title of the note you want to update in Apple Notes.
NOTE_TITLE = "Longhai Li’s Computers’ IPs"
# ---------------------

def escape_for_applescript(text):
    """Escapes text to be safely used inside an AppleScript string."""
    text = text.replace('\\', '\\\\') # Must be first
    text = text.replace('"', '\\"')   # Escape double quotes
    return text

def strip_html(text):
    """Removes HTML tags from a string."""
    return re.sub('<[^<]+?>', '', text)

def get_computer_name():
    """Gets the user-friendly computer name from macOS using scutil."""
    try:
        name = subprocess.check_output(["scutil", "--get", "ComputerName"], text=True).strip()
        return name
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback to the original method if scutil fails for any reason
        return socket.gethostname().replace('.local', '')

def get_public_ip():
    """Gets the public IP address from an external service."""
    try:
        # Use a reliable service to get the public IP
        ip = requests.get('https://api.ipify.org', timeout=5).text.strip()
        return ip
    except requests.RequestException:
        return "Could not fetch public IP"

def get_apple_note_content(note_title):
    """Gets the body of a specific Apple Note using AppleScript."""
    safe_title = escape_for_applescript(note_title)
    # This revised script is more direct in finding the note.
    script = f'''
    tell application "Notes"
        tell account "iCloud"
            if not (exists folder "Computers") then
                return ""
            end if
            tell folder "Computers"
                if (exists note "{safe_title}") then
                    return body of note "{safe_title}"
                else
                    return ""
                end if
            end tell
        end tell
    end tell
    '''
    try:
        # Execute the script and capture the output
        result = subprocess.run(["osascript", "-e", script], check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error reading note: {e.stderr}")
        return "" # Return empty string on error

def update_apple_note(note_title, note_body):
    """Updates the body of a specific Apple Note using AppleScript."""
    safe_title = escape_for_applescript(note_title)
    safe_body = escape_for_applescript(note_body)
    # This revised script will create the folder if it does not exist.
    script = f'''
    tell application "Notes"
        tell account "iCloud"
            if not (exists folder "Computers") then
                make new folder with properties {{name:"Computers"}}
            end if
            tell folder "Computers"
                if not (exists note "{safe_title}") then
                    make new note with properties {{name:"{safe_title}", body:"{safe_body}"}}
                else
                    set theNote to note "{safe_title}"
                    set body of theNote to "{safe_body}"
                end if
            end tell
        end tell
    end tell
    '''
    try:
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
        print(f"Successfully updated note: '{safe_title}'")
    except subprocess.CalledProcessError as e:
        print(f"Error updating note: {e.stderr.decode()}")

if __name__ == "__main__":
    # Get the computer's name using the more reliable scutil method
    computer_name = get_computer_name()
    
    # Fetch the public IP address
    public_ip = get_public_ip()
    
    # Get current date and time
    current_date = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    
    # Format the new line for the current computer
    new_line_for_this_mac = f"{computer_name}: {public_ip}, {current_date}"
    
    # Read the existing content from the note
    existing_content = get_apple_note_content(NOTE_TITLE)
    existing_lines = existing_content.splitlines()
    
    # Create a new list of lines, excluding any old entries for this computer (case-insensitive)
    search_prefix = (computer_name + ":").lower()
    updated_lines = []
    for line in existing_lines:
        # Strip HTML tags and whitespace, then convert to lower case for comparison
        clean_line = strip_html(line).strip().lower()
        if not clean_line.startswith(search_prefix):
            updated_lines.append(line)

    # Add the new, updated line to the list
    updated_lines.append(new_line_for_this_mac)
    
    # Join the lines back together into a single string for the note body
    new_note_content = "\n".join(updated_lines)
    
    # Update the note with the new content
    update_apple_note(NOTE_TITLE, new_note_content)

