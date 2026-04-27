import subprocess

TOOL_SCHEMA = {
    "name": "send_notification",
    "description": "Sends a native macOS notification banner to the screen with a title and message.",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "The notification title (e.g. 'JARVIS Alert')"
            },
            "message": {
                "type": "string",
                "description": "The notification body text."
            }
        },
        "required": ["title", "message"]
    }
}

def execute(title: str, message: str) -> str:
    """Pushes a native macOS notification via osascript."""
    try:
        safe_title = title.replace('"', '\\"')
        safe_message = message.replace('"', '\\"')
        
        script = f'display notification "{safe_message}" with title "{safe_title}"'
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=5
        )
        
        if result.returncode == 0:
            return f"Notification sent: '{title}'"
        else:
            return f"Notification failed: {result.stderr.strip()}"
            
    except Exception as e:
        return f"Notification error: {str(e)}"
