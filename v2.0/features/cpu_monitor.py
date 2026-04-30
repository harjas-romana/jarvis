import psutil
from langchain_core.tools import tool

@tool
def cpu_monitor(query: str = "") -> str:
    """
    Checks the current CPU and RAM usage of the host system.
    Use this tool whenever Mr. Harjas asks about system performance, CPU, memory, or RAM.
    """
    try:
        # Added a 0.5s interval to get an accurate CPU reading rather than a static snapshot
        cpu_usage = psutil.cpu_percent(interval=0.5)
        ram_usage = psutil.virtual_memory().percent
        return f"SUCCESS: CURRENT CPU USAGE: {cpu_usage}% | CURRENT RAM USAGE: {ram_usage}%"
    except Exception as e:
        return f"ERROR: Could not fetch system metrics: {str(e)}"