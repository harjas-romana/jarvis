import subprocess

TOOL_SCHEMA = {
    "name": "media_control",
    "description": "Natively controls Apple Music and macOS media playback.",
    "parameters": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "enum": ["play", "pause", "next", "prev", "now_playing"],
                "description": "The media action to execute."
            }
        },
        "required": ["command"]
    }
}

def _osascript(script: str) -> str:
    """Executes an AppleScript command and returns stdout."""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0:
        return f"AppleScript Error: {result.stderr.strip()}"
    return result.stdout.strip()

def _get_active_player() -> str:
    """Detects which music player is currently running."""
    # Check Spotify first (most common)
    check_spotify = _osascript('tell application "System Events" to (name of processes) contains "Spotify"')
    if check_spotify == "true":
        return "Spotify"
    
    # Check Apple Music
    check_music = _osascript('tell application "System Events" to (name of processes) contains "Music"')
    if check_music == "true":
        return "Music"
    
    return "none"


def execute(command: str) -> str:
    try:
        if command == "play":
            script = 'tell application "Music" to play'
        elif command == "pause":
            script = 'tell application "Music" to pause'
        elif command == "next":
            script = 'tell application "Music" to next track'
        elif command == "prev":
            script = 'tell application "Music" to previous track'
        elif command == "now_playing":
            script = '''
            tell application "Music"
                if player state is playing then
                    set currentName to name of current track
                    set currentArtist to artist of current track
                    return currentName & " by " & currentArtist
                else
                    return "Nothing is currently playing."
                end if
            end tell
            '''
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            return f"Currently playing: {result.stdout.strip()}"
            
        subprocess.run(["osascript", "-e", script], check=True)
        return f"Successfully executed Apple Music command: {command}"
        
    except Exception as e:
        return f"AppleScript execution failed: {e}"