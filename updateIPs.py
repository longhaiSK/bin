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
        return socket.gethostname().replace('.local', '')

def get_public_ip():
    """Gets the public IP address from an external service."""
    try:
        ip = requests.get('https://api.ipify.org', timeout=5).text.strip()
        return ip
    except requests.RequestException:
        return "Could not fetch public IP"

def get_local_ip():
    """
    Gets the local IP address using macOS-specific commands for reliability.
    This is more robust than the previous socket-based method.
    """
    try:
        # First, try the primary Wi-Fi interface (en0 is common for modern Macs)
        ip = subprocess.check_output(["ipconfig", "getifaddr", "en0"], text=True, stderr=subprocess.DEVNULL).strip()
        if ip: return ip
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass # Interface might not be active, so we continue

    try:
        # If Wi-Fi fails, try the primary Ethernet interface (en1 is a common fallback)
        ip = subprocess.check_output(["ipconfig", "getifaddr", "en1"], text=True, stderr=subprocess.DEVNULL).strip()
        if ip: return ip
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass # This interface might also not be active

    # If ipconfig fails, fall back to the old socket method as a last resort
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(1.0)
    try:
        s.connect(('8.8.8.8', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1' # Final fallback
    finally:
        s.close()
    return IP

def get_apple_note_content(note_title):
    """Gets the body of a specific Apple Note using AppleScript."""
    safe_title = escape_for_applescript(note_title)
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
        result = subprocess.run(["osascript", "-e", script], check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        error_message = e.stderr.decode()
        print(f"Error reading note: {error_message}")
        if "Not authorized" in error_message or "access" in error_message:
            print("\n--- PERMISSION ERROR DETECTED ---")
            print("macOS is likely blocking this script from controlling the Notes app.")
            print("Please go to System Settings > Privacy & Security > Automation.")
            print("Find the application you are running this script from (e.g., Terminal) and ensure 'Notes' is checked ON.")
            print("---------------------------------")
        return ""

def update_apple_note(note_title, note_body):
    """Updates the body of a specific Apple Note using AppleScript."""
    safe_title = escape_for_applescript(note_title)
    safe_body = escape_for_applescript(note_body)
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
        error_message = e.stderr.decode()
        print(f"Error updating note: {error_message}")
        if "Not authorized" in error_message or "access" in error_message:
            print("\n--- PERMISSION ERROR DETECTED ---")
            print("macOS is likely blocking this script from controlling the Notes app.")
            print("Please go to System Settings > Privacy & Security > Automation.")
            print("Find the application you are running this script from (e.g., Terminal) and ensure 'Notes' is checked ON.")
            print("---------------------------------")

if __name__ == "__main__":
    computer_name = get_computer_name()
    public_ip = get_public_ip()
    local_ip = get_local_ip() # Get the local IP
    current_date = datetime.now().strftime("%Y-%m-%d %I:%M %p")

    # Print the fetched information to the terminal for debugging
    print("--- Running IP Update Script ---")
    print(f"Computer Name: {computer_name}")
    print(f"Public IP: {public_ip}")
    print(f"Local IP: {local_ip}")
    print("------------------------------")
    
    # Updated format to include the local IP address
    new_line_for_this_mac = f"{computer_name}: {public_ip} (Local: {local_ip}), {current_date}"
    
    existing_content = get_apple_note_content(NOTE_TITLE)
    existing_lines = existing_content.splitlines()
    
    search_prefix = (computer_name + ":").lower()
    updated_lines = []
    for line in existing_lines:
        clean_line = strip_html(line).strip().lower()
        if not clean_line.startswith(search_prefix):
            updated_lines.append(line)

    updated_lines.append(new_line_for_this_mac)
    new_note_content = "\n".join(updated_lines)
    
    update_apple_note(NOTE_TITLE, new_note_content)

