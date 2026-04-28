import requests
from langchain_core.tools import tool

@tool
def get_weather(location: str) -> str:
    """Fetches the current weather conditions and temperature for a given location. Use this when the user asks about the weather."""
    try:
        # wttr.in is a fast, no-API-key weather service
        # Format %C is condition (e.g., Clear), %t is actual temperature
        url = f"https://wttr.in/{location}?format=%C+%t"
        
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            return f"The weather in {location} is currently {response.text.strip()}."
        else:
            return f"Could not fetch weather data for {location}."
            
    except requests.exceptions.Timeout:
        return "Weather service timed out."
    except Exception as e:
        return f"Weather service error: {str(e)}"