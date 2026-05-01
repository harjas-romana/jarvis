import os
import subprocess
import re
from langchain_core.tools import tool

@tool
def build_and_test_react_app(project_name: str, app_jsx_content: str) -> str:
    """
    Creates a React application, writes the provided App.jsx code, and tests it securely inside a Docker container.
    Use this when Mr. Harjas asks you to build a React UI or project. 
    Ensure you write complete, working React code for the 'app_jsx_content' parameter.
    """
    try:
        # Sanitize project name for Docker (lowercase, no spaces/special chars)
        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', project_name).lower()
        
        desktop_path = os.path.expanduser("~/Desktop")
        project_path = os.path.join(desktop_path, safe_name)

        if not os.path.exists(project_path):
            os.makedirs(project_path)

        dockerfile_content = """
FROM node:20-alpine
WORKDIR /app
# Scaffold a fresh Vite/React project
RUN npx create-vite@latest . --template react
RUN npm install
# Overwrite the default App.jsx with JARVIS's generated code
COPY App.jsx ./src/App.jsx
EXPOSE 5173
# Start the dev server and expose it outside the container
CMD ["npm", "run", "dev", "--", "--host"]
"""
        with open(os.path.join(project_path, "Dockerfile"), "w") as f:
            f.write(dockerfile_content.strip())

        with open(os.path.join(project_path, "App.jsx"), "w") as f:
            f.write(app_jsx_content)

        print(f"\n[Sandbox] Compiling Docker image '{safe_name}'... (This takes 1-2 minutes. Please wait.)\n")
        
        img_name = f"{safe_name}_img"
        # [THE FIX]: Removed capture_output=True so you can watch npm install happen live
        subprocess.run(["docker", "build", "-t", img_name, "."], cwd=project_path, check=True)
        
        container_name = f"{safe_name}_container"
        subprocess.run(["docker", "rm", "-f", container_name], stderr=subprocess.DEVNULL)

        print(f"\n[Sandbox] Booting container: {container_name} on Port 5173...")
        
        subprocess.run([
            "docker", "run", "-d", 
            "--name", container_name, 
            "-p", "5173:5173", 
            img_name
        ], cwd=project_path, check=True)

        return f"SUCCESS: The React app '{project_name}' compiled perfectly. Tell Mr. Harjas he can preview it live at: http://localhost:5173"

    except subprocess.CalledProcessError as e:
        return "EXECUTION FAILED: The React app crashed during the Docker build. Please fix your React code and try again."
    except Exception as e:
        return f"SYSTEM ERROR: Failed to execute sandbox: {str(e)}"