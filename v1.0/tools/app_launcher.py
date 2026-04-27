import subprocess

TOOL_SCHEMA = {
    "name": "app_control",
    "description": "Opens, closes, or lists running macOS apps.",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "Must be exactly 'open', 'close', or 'list_running'"
            },
            "app_name": {
                "type": "string",
                "description": "Name of the app (e.g., 'Safari'). Provide empty string if action is 'list_running'."
            }
        },
        "required": ["action"]
    }
}

def execute(action: str, app_name: str = "") -> str:
    try:
        if action == "open":
            subprocess.run(["open", "-a", app_name], check=True)
            return f"Successfully opened {app_name}."
        elif action == "close":
            script = f'tell application "{app_name}" to quit'
            subprocess.run(["osascript", "-e", script], check=True)
            return f"Successfully closed {app_name}."
        elif action == "list_running":
            script = 'tell application "System Events" to get name of (processes where background only is false)'
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            return f"Running applications: {result.stdout.strip()}"
        else:
            return f"Error: Unknown action '{action}'"
    except Exception as e:
        return f"Execution failed: {str(e)}"