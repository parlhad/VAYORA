import os
import requests
from dotenv import load_dotenv

load_dotenv()

OWM_KEY = os.getenv("OPENWEATHER_KEY")

GEO_URL = "http://api.openweathermap.org/geo/1.0/direct"
WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"


def get_weather(city: str):
    if not OWM_KEY:
        return {"error": "OPENWEATHER_KEY not set"}

    try:
        # 1. Get coordinates
        geo = requests.get(
            GEO_URL,
            params={"q": city, "limit": 1, "appid": OWM_KEY},
            timeout=5
        ).json()

        if not geo:
            return {"error": "City not found"}

        lat, lon = geo[0]["lat"], geo[0]["lon"]

        # 2. Get weather
        weather = requests.get(
            WEATHER_URL,
            params={"lat": lat, "lon": lon, "appid": OWM_KEY, "units": "metric"},
            timeout=5
        ).json()

        return {
            "temperature": weather["main"]["temp"],
            "humidity": weather["main"]["humidity"],
            "wind_speed": weather["wind"]["speed"],
            "description": weather["weather"][0]["description"]
        }

    except Exception as e:
        return {"error": str(e)}