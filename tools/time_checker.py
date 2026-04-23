import os
import datetime

TOOL_SCHEMA = {
    "name": "time_checker",
    "description": "Fetches and displays the current system date and time",
    "parameters": {
        "type": "object",
        "properties": {
            "format": {
                "type": "string",
                "description": "Optional date and time format (default: %Y-%m-%d %H:%M:%S)"
            }
        },
        "required": ["format"]
    }
}

def execute(format: str = "%Y-%m-%d %H:%M:%S") -> str:
    try:
        current_time = datetime.datetime.now()
        return current_time.strftime(format)
    except Exception as e:
        return f"Error: {str(e)}"