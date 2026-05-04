import os
import importlib
import inspect
from langchain_core.tools import BaseTool

# 1. Import Core Tools
from .devops_agent import scaffold_react_app, boot_existing_project
from .os_agent import execute_mac_command, open_url, kill_dev_port
from .status_agent import check_agent_status
from .tool_forger import forge_new_tool # We will build this next

JARVIS_TOOLS = [
    scaffold_react_app,
    boot_existing_project,
    execute_mac_command,
    open_url,
    kill_dev_port,
    check_agent_status,
    forge_new_tool
]

# 2. Dynamic Plugin Loader (Auto-loads custom tools)
custom_dir = os.path.join(os.path.dirname(__file__), "custom")
os.makedirs(custom_dir, exist_ok=True)

for filename in os.listdir(custom_dir):
    if filename.endswith(".py") and not filename.startswith("__"):
        module_name = filename[:-3]
        try:
            # Dynamically import the custom module
            module = importlib.import_module(f"tools.custom.{module_name}")
            
            # Scan module for any LangChain @tool decorators
            for name, obj in inspect.getmembers(module):
                if isinstance(obj, BaseTool):
                    JARVIS_TOOLS.append(obj)
        except Exception as e:
            print(f"[System Warning] Failed to load custom tool '{filename}': {str(e)}")