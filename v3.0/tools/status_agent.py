import os
from langchain_core.tools import tool

@tool
def check_agent_status() -> str:
    """CRITICAL TOOL: Reads the system log to report on background app builds."""
    log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "system.log")
    if not os.path.exists(log_path):
        return "No background tasks have been logged yet."
        
    try:
        with open(log_path, "r") as f:
            return f"LATEST LOGS:\n{''.join(f.readlines()[-15:])}"
    except Exception as e:
        return f"Error reading logs: {str(e)}"