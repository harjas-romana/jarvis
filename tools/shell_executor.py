import subprocess
from core.telemetry import logger

# Commands that could brick the system. These are blocked unconditionally.
BLOCKED_PATTERNS = [
    "rm -rf /", "rm -rf ~", "rm -rf /*",
    "mkfs", "dd if=", ":(){", "fork bomb",
    "sudo shutdown", "sudo reboot", "sudo halt",
    "sudo rm", "chmod -R 777 /",
    "> /dev/sda", "mv / ", "wget | sh", "curl | sh",
]

TOOL_SCHEMA = {
    "name": "run_shell_command",
    "description": "Executes a terminal command on this Mac and returns the output. Use for git commands, pip installs, file operations, running scripts, and any other CLI task.",
    "parameters": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The exact shell command to run (e.g. 'ls -la ~/Desktop', 'git status', 'python3 script.py')"
            },
            "working_directory": {
                "type": "string",
                "description": "Optional directory to run the command in. Defaults to the user's home directory."
            }
        },
        "required": ["command"]
    }
}

def execute(command: str, working_directory: str = "") -> str:
    """Executes shell commands with safety checks, logging, and timeouts."""
    import os
    
    # Safety check: block destructive commands
    cmd_lower = command.lower().strip()
    for pattern in BLOCKED_PATTERNS:
        if pattern in cmd_lower:
            logger.warning(f"BLOCKED dangerous command: {command}")
            return f"SECURITY BLOCK: The command '{command}' has been blocked for safety. It matches a destructive pattern."
    
    # Default working directory
    cwd = working_directory if working_directory else os.path.expanduser("~")
    if not os.path.isdir(cwd):
        cwd = os.path.expanduser("~")
    
    logger.info(f"Shell Execution: '{command}' in '{cwd}'")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=cwd
        )
        
        output = result.stdout.strip()
        error = result.stderr.strip()
        
        if result.returncode == 0:
            if output:
                # Truncate very long outputs to prevent LLM context overflow
                if len(output) > 2000:
                    output = output[:2000] + "\n... [output truncated at 2000 chars]"
                return f"Command succeeded:\n{output}"
            return "Command executed successfully (no output)."
        else:
            msg = f"Command failed (exit code {result.returncode})."
            if error:
                msg += f"\nError: {error[:1000]}"
            if output:
                msg += f"\nOutput: {output[:500]}"
            return msg
            
    except subprocess.TimeoutExpired:
        return f"Command timed out after 30 seconds: '{command}'"
    except Exception as e:
        return f"Shell execution error: {str(e)}"
