import requests
from langchain_core.tools import tool
from pydantic import BaseModel, Field

class WeatherInput(BaseModel):
    location: str = Field(description="City name (e.g., 'Faridkot' or 'Bhopal')")

@tool(args_schema=WeatherInput)
def get_current_weather(location: str) -> str:
    """
    Fetches real-time weather data using a public keyless endpoint (wttr.in).
    """
    try:
        # We fetch the JSON format for parsing
        response = requests.get(f"https://wttr.in/{location}?format=j1", timeout=10)
        data = response.json()
        
        current = data['current_condition'][0]
        temp_c = current['temp_C']
        desc = current['weatherDesc'][0]['value']
        humidity = current['humidity']
        
        return f"Current weather in {location}: {desc}, {temp_c}°C with {humidity}% humidity."
    except Exception as e:
        return f"ERROR: Failed to fetch weather. {str(e)}"