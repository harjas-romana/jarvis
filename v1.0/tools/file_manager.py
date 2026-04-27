import os

# Allowed base directories — JARVIS cannot touch system files
ALLOWED_ROOTS = [
    os.path.expanduser("~/Desktop"),
    os.path.expanduser("~/Documents"),
    os.path.expanduser("~/Downloads"),
    os.path.dirname(os.path.dirname(__file__)),  # JARVIS project root
]

TOOL_SCHEMA = {
    "name": "file_manager",
    "description": "Reads, writes, or lists files and directories on this Mac. Restricted to Desktop, Documents, Downloads, and the JARVIS project folder.",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "The file operation: 'read', 'write', 'list', or 'create_dir'"
            },
            "path": {
                "type": "string",
                "description": "The absolute or relative file/directory path."
            },
            "content": {
                "type": "string",
                "description": "The text content to write (only required for 'write' action)."
            }
        },
        "required": ["action", "path"]
    }
}

def _is_path_allowed(path: str) -> bool:
    """Checks if the resolved path falls within allowed directories."""
    resolved = os.path.realpath(os.path.expanduser(path))
    return any(resolved.startswith(os.path.realpath(root)) for root in ALLOWED_ROOTS)

def execute(action: str, path: str, content: str = "") -> str:
    """Manages files with strict sandboxing."""
    try:
        full_path = os.path.expanduser(path)
        
        if not _is_path_allowed(full_path):
            return f"SECURITY BLOCK: Path '{path}' is outside allowed directories. Allowed: ~/Desktop, ~/Documents, ~/Downloads, and the JARVIS project."
        
        action = action.lower().strip()
        
        if action == "read":
            if not os.path.isfile(full_path):
                return f"File not found: {full_path}"
            with open(full_path, "r") as f:
                data = f.read()
            if len(data) > 3000:
                data = data[:3000] + "\n... [truncated at 3000 chars]"
            return f"Contents of {os.path.basename(full_path)}:\n{data}"
            
        elif action == "write":
            if not content:
                return "Error: No content provided to write."
            # Create parent directories if needed
            parent = os.path.dirname(full_path)
            if parent and not os.path.exists(parent):
                os.makedirs(parent)
            with open(full_path, "w") as f:
                f.write(content)
            return f"Successfully wrote {len(content)} characters to {full_path}."
            
        elif action == "list":
            if not os.path.isdir(full_path):
                return f"Directory not found: {full_path}"
            entries = os.listdir(full_path)
            items = []
            for e in sorted(entries)[:50]:  # Limit to 50 entries
                fp = os.path.join(full_path, e)
                if os.path.isdir(fp):
                    items.append(f"  [DIR]  {e}/")
                else:
                    size = os.path.getsize(fp)
                    if size < 1024:
                        items.append(f"  [FILE] {e} ({size} B)")
                    else:
                        items.append(f"  [FILE] {e} ({size / 1024:.1f} KB)")
            return f"Contents of {full_path}:\n" + "\n".join(items) if items else "Directory is empty."
            
        elif action == "create_dir":
            os.makedirs(full_path, exist_ok=True)
            return f"Directory created: {full_path}"
            
        else:
            return f"Unknown action: '{action}'. Available: read, write, list, create_dir."
            
    except PermissionError:
        return f"Permission denied: cannot access {path}."
    except Exception as e:
        return f"File manager error: {str(e)}"
