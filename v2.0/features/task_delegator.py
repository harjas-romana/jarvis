from langchain_core.tools import tool
from core.worker import system_2

@tool
def delegate_background_task(task_type: str, instructions: str) -> str:
    """
    Use this tool ONLY to START a NEW long-running background task.
    Valid task_types are: 'research' or 'code_project'.
    
    CRITICAL RULES:
    1. If Harjas asks you to build a project or write code (e.g., "make me a react portfolio"), you MUST ask him "Where should I place the codebase?" BEFORE using this tool. 
    2. Once he provides the location, include that location in the 'instructions' and trigger this tool with task_type="code_project".
    3. NEVER use this tool to check status or read a report.
    """
    try:
        system_2.submit_task(task_type=task_type, payload=instructions)
        return "<emotion value=\"confident\"/> Success. Tell Harjas: 'I have dispatched the engineering task to my background swarm. I will notify you when the codebase is compiled.'"
    except Exception as e:
        return f"Failed to delegate task: {str(e)}"