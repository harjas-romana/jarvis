from langchain_core.tools import tool
from datetime import datetime

@tool
def get_system_time() -> str:
    """Fetches the current system time, day, and date. Use this when the user asks for the time."""
    now = datetime.now()
    return now.strftime("%A, %B %d, %Y at %I:%M %p")