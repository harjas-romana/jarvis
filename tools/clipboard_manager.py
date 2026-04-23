import subprocess

TOOL_SCHEMA = {
    "name": "clipboard",
    "description": "Reads or writes text to the macOS clipboard.",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "Must be 'read' or 'write'."
            },
            "text": {
                "type": "string",
                "description": "The text to copy. Leave empty if action is 'read'."
            }
        },
        "required": ["action"]
    }
}

def execute(action: str, text: str = "") -> str:
    try:
        if action == "read":
            result = subprocess.run(["pbpaste"], capture_output=True, text=True)
            return f"Clipboard contents: {result.stdout}"
        elif action == "write":
            process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE, text=True)
            process.communicate(input=text)
            return "Successfully copied text to clipboard."
        else:
            return f"Error: Unknown action '{action}'"
    except Exception as e:
        return f"Clipboard operation failed: {str(e)}"