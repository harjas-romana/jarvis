import os
import subprocess
from langchain_core.tools import tool

@tool
def create_project_workspace(base_path: str, project_name: str) -> str:
    """Creates a new folder for a project and returns the absolute path."""
    try:
        full_path = os.path.join(os.path.expanduser(base_path), project_name)
        os.makedirs(full_path, exist_ok=True)
        return f"Workspace created at: {full_path}"
    except Exception as e:
        return f"Failed to create workspace: {str(e)}"

@tool
def write_code_file(filepath: str, content: str) -> str:
    """Writes code to a file and automatically tags it RED in the macOS Finder."""
    try:
        # 1. Write the file
        expanded_path = os.path.expanduser(filepath)
        with open(expanded_path, "w") as f:
            f.write(content)
            
        # 2. Use AppleScript to set the Finder Label to Red (Index 2)
        # This gives visual proof that JARVIS wrote the file
        apple_script = f'tell application "Finder" to set label index of (POSIX file "{expanded_path}") to 2'
        subprocess.run(["osascript", "-e", apple_script], capture_output=True)
        
        return f"Successfully wrote and tagged: {expanded_path}"
    except Exception as e:
        return f"Failed to write file: {str(e)}"

@tool
def execute_python_in_jarvis_env(filepath: str) -> str:
    """Executes a Python script specifically inside the 'jarvis' conda environment to test it."""
    try:
        expanded_path = os.path.expanduser(filepath)
        # Strictly enforces the conda environment sandbox
        result = subprocess.run(
            ["conda", "run", "-n", "jarvis", "python", expanded_path],
            capture_output=True,
            text=True,
            timeout=30 # Prevent infinite loops
        )
        
        if result.returncode == 0:
            return f"Execution Successful.\nSTDOUT:\n{result.stdout}"
        else:
            return f"Execution Failed (Bug Found).\nSTDERR:\n{result.stderr}\nFix the code and overwrite the file."
    except subprocess.TimeoutExpired:
        return "Execution timed out. Code might have an infinite loop."
    except Exception as e:
        return f"System error during execution: {str(e)}"