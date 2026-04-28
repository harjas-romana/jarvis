import subprocess
from langchain_core.tools import tool

@tool
def get_battery_status() -> str:
    """Reads the current battery percentage and charging status of the MacBook."""
    try:
        # Uses native macOS power management tool
        result = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')
        if len(lines) > 1:
            # The second line contains the percentage and state
            return f"Battery status: {lines[1].strip()}"
        return "Could not parse battery status."
    except Exception as e:
        return f"Battery diagnostic failed: {str(e)}"