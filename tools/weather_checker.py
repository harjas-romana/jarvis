import os
import requests

TOOL_SCHEMA = {
    "name": "weather_checker",
    "description": "Fetch and display the current weather in a specified location",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "City or zip code for weather lookup"
            }
        },
        "required": ["location"]
    }
}

def execute(location: str) -> str:
    try:
        api_key = os.environ.get('OPENWEATHERMAP_API_KEY')
        if api_key is None:
            return "Error: OPENWEATHERMAP_API_KEY environment variable not set"
        
        url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return f"Weather in {data['name']}: {data['weather'][0]['description']}, Temperature: {data['main']['temp']}°C"
        else:
            return f"Error: {response.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"