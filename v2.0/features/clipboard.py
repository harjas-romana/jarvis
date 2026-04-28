import subprocess
from langchain_core.tools import tool

@tool
def manage_clipboard(action: str, text: str = "") -> str:
    """Reads from or writes to the macOS clipboard. Action must be 'read' or 'write'. If writing, provide the text."""
    try:
        if action.lower() == "read":
            result = subprocess.run(["pbpaste"], capture_output=True, text=True, check=True)
            return f"Clipboard contents: {result.stdout}"
        elif action.lower() == "write":
            process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE, text=True)
            process.communicate(input=text)
            return "Successfully copied text to clipboard."
        else:
            return "Error: Action must be 'read' or 'write'."
    except Exception as e:
        return f"Clipboard operation failed: {str(e)}"