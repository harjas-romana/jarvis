import subprocess
from langchain_core.tools import tool

# Smart alias mapping for common developer apps
APP_ALIASES = {
    "vs code": "Visual Studio Code",
    "vscode": "Visual Studio Code",
    "chrome": "Google Chrome",
    "word": "Microsoft Word",
    "excel": "Microsoft Excel",
    "powerpoint": "Microsoft PowerPoint"
}

@tool
def manage_macos_app(action: str, app_name: str) -> str:
    """Opens or closes a macOS application. Action must be exactly 'open' or 'close'."""
    try:
        # Resolve common names to their official macOS application names
        resolved_app_name = APP_ALIASES.get(app_name.lower(), app_name)
        
        if action.lower() == "open":
            subprocess.run(["open", "-a", resolved_app_name], check=True)
            return f"Successfully opened {resolved_app_name}."
        elif action.lower() == "close":
            script = f'tell application "{resolved_app_name}" to quit'
            subprocess.run(["osascript", "-e", script], check=True)
            return f"Successfully closed {resolved_app_name}."
        else:
            return f"Error: Action must be 'open' or 'close'."
    except Exception as e:
        return f"Failed to {action} {resolved_app_name}: {str(e)}"