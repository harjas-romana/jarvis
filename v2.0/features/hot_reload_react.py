import os
import subprocess
from langchain_core.tools import tool

@tool
def hot_reload_react_app(project_name: str, new_jsx_content: str) -> str:
    """
    Use this tool when Mr. Harjas asks you to UPDATE, FIX, or REFINE an existing React project.
    It injects the new React code directly into the running Docker container for instant updates.
    """
    try:
        import re
        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', project_name).lower()
        container_name = f"{safe_name}_container"
        
        # 1. Save the new code locally as a backup
        desktop_path = os.path.expanduser("~/Desktop")
        app_path = os.path.join(desktop_path, safe_name, "App.jsx")
        with open(app_path, "w") as f:
            f.write(new_jsx_content)
            
        # 2. Inject it directly into the live Docker container
        escaped_content = new_jsx_content.replace("'", "'\\''")
        command = f"echo '{escaped_content}' > /app/src/App.jsx"
        
        subprocess.run(["docker", "exec", container_name, "sh", "-c", command], check=True)
        
        return "SUCCESS: The code was hot-reloaded into the container. Tell Mr. Harjas the browser has updated instantly."
    except Exception as e:
        return f"EXECUTION FAILED: Could not hot-reload the container. Is it currently running? Error: {str(e)}"