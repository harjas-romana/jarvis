import subprocess
from langchain_core.tools import tool
from pydantic import BaseModel, Field

class OpenUrlInput(BaseModel):
    url: str = Field(description="The exact URL to open (e.g., 'http://localhost:5173')")

class KillPortInput(BaseModel):
    port: str = Field(description="The port number to kill (e.g., '5173')")

@tool
def execute_mac_command(command: str) -> str:
    """Executes a bash terminal command strictly for reading files or checking network."""
    blocked_commands = ["rm", "sudo", "mv", "kill", "chmod", "chown"]
    if any(part in blocked_commands for part in command.lower().split()):
        return f"SYSTEM OVERRIDE: Destructive commands are strictly forbidden."

    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=15)
        return f"SUCCESS:\n{result.stdout.strip()}" if result.returncode == 0 else f"COMMAND ERROR:\n{result.stderr.strip()}"
    except Exception as e:
        return f"SYSTEM EXCEPTION: {str(e)}"

@tool(args_schema=OpenUrlInput)
def open_url(url: str) -> str:
    """CRITICAL TOOL: Opens a website, localhost URL, or file path in the default browser."""
    try:
        subprocess.run(["open", url], check=True)
        return f"SUCCESS: Opened {url}."
    except Exception as e:
        return f"ERROR: Could not open {url}. Exception: {str(e)}"

@tool(args_schema=KillPortInput)
def kill_dev_port(port: str) -> str:
    """CRITICAL TOOL: Kills local development servers running on a specific port."""
    try:
        result = subprocess.run(f"lsof -t -i:{port}", shell=True, capture_output=True, text=True)
        pids = result.stdout.strip().split('\n')
        
        if not pids or pids[0] == '':
            return f"No active process found running on port {port}."
        
        for pid in pids:
            subprocess.run(f"kill -9 {pid}", shell=True)
        return f"SUCCESS: Killed dev server on port {port} (PIDs: {', '.join(pids)})."
    except Exception as e:
         return f"ERROR: Failed to terminate port {port}. {str(e)}"