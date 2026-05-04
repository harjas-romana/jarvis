import os
import subprocess
import threading
import re
import logging
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(filename=os.path.join(log_dir, 'system.log'), level=logging.INFO, format='%(asctime)s - [DevOps] - %(message)s')

def _background_dev_task(project_name, description, base_path, project_path):
    logging.info(f"Background factory started for '{project_name}'.")
    try:
        logging.info("Initializing Vite...")
        subprocess.run(["npx", "--yes", "create-vite@latest", project_name, "--template", "react"], cwd=base_path, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
        
        logging.info("Installing Dependencies...")
        subprocess.run(["npm", "install", "tailwindcss@4.1", "lucide-react", "react-router-dom"], cwd=project_path, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
        
        logging.info("Generating Code via openai/gpt-oss-120b...")
        try:
            coder = ChatGroq(api_key=os.getenv("GROQ_API_KEY"), model="openai/gpt-oss-120b", temperature=0.1)
            sys_prompt = "You are a React developer. Output ONLY valid JSX code for an App.jsx file. Wrap in ```jsx ... ``` blocks."
            user_prompt = f"Write a monochrome brutalist App.jsx for a project named {project_name}. Objective: {description}."
            
            response = coder.invoke([SystemMessage(content=sys_prompt), HumanMessage(content=user_prompt)])
            match = re.search(r'```(?:jsx|javascript|js)?\n?(.*?)```', response.content, re.DOTALL | re.IGNORECASE)
            app_code = match.group(1).strip() if match else response.content.replace("```jsx", "").replace("```", "").strip()
        except Exception as e:
            logging.error(f"API Warning: {str(e)}")
            app_code = f"import React from 'react';\nexport default function App() {{ return <div className='bg-black text-white h-screen p-8'>{project_name}</div>; }}"
            
        with open(os.path.join(project_path, "src", "App.jsx"), "w") as f:
            f.write(app_code)
            
        logging.info(f"Spinning up localhost...")
        subprocess.Popen(["npm", "run", "dev"], cwd=project_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
        logging.info(f"'{project_name}' is live on port 5173.")
        
    except Exception as e:
        logging.error(f"FATAL ERROR: {str(e)}")

@tool
def scaffold_react_app(project_name: str, description: str) -> str:
    """CRITICAL TOOL: Builds a web app, website, or portfolio asynchronously."""
    project_name = project_name.lower().replace(" ", "-")
    base_path = os.path.expanduser("~/Desktop/jarvis_projects")
    os.makedirs(base_path, exist_ok=True)
    project_path = os.path.join(base_path, project_name)

    if os.path.exists(project_path):
        return f"Project {project_name} already exists."

    thread = threading.Thread(target=_background_dev_task, args=(project_name, description, base_path, project_path))
    thread.start()
    return f"SUCCESS. Background worker dispatched. The app is building silently."

def _background_boot_task(project_path, project_name):
    """Silently boots an existing project in the background."""
    logging.info(f"Booting existing project: '{project_name}'...")
    try:
        subprocess.Popen(
            ["npm", "run", "dev"], 
            cwd=project_path, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL, 
            stdin=subprocess.DEVNULL
        )
        logging.info(f"'{project_name}' is live on port 5173.")
    except Exception as e:
        logging.error(f"FATAL ERROR booting {project_name}: {str(e)}")

@tool
def boot_existing_project(project_name: str) -> str:
    """
    CRITICAL TOOL: Use this to start/run an EXISTING project that is currently offline. 
    Do NOT use this to create new projects.
    """
    project_name = project_name.lower().replace(" ", "-")
    base_path = os.path.expanduser("~/Desktop/jarvis_projects")
    project_path = os.path.join(base_path, project_name)

    if not os.path.exists(project_path):
        return f"ERROR: Project '{project_name}' does not exist in {base_path}. You must build it first."

    # Check if something is already running on 5173 to prevent conflicts
    try:
        result = subprocess.run("lsof -t -i:5173", shell=True, capture_output=True, text=True)
        if result.stdout.strip():
            return "ERROR: Port 5173 is already in use. Tell the user to kill the current server before booting a new one."
    except Exception:
        pass

    # Fire and forget the boot process
    thread = threading.Thread(target=_background_boot_task, args=(project_path, project_name))
    thread.start()
    
    return f"SUCCESS. Background worker dispatched to boot '{project_name}'. Tell the user the server is starting and will be available at http://localhost:5173 shortly."