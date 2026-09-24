import os
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv


load_dotenv()

OWM_KEY = os.getenv("OPENWEATHER_KEY")

GEO_URL = "http://api.openweathermap.org/geo/1.0/direct"
WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"


def get_weather(city: str):
    """
    Retrieve current weather for a city using OpenWeather.

    The function preserves the existing VAYORA weather fields:
        temperature
        humidity
        wind_speed
        description

    It additionally returns structured environmental information
    that can later be used by the agent and frontend.

    No weather value is generated or estimated locally. Values
    come directly from the OpenWeather response.
    """

    # ---------------------------------------------------------
    # Validate request
    # ---------------------------------------------------------

    if not city or not city.strip():
        return {
            "error": "City is required",
            "available": False,
        }

    if not OWM_KEY:
        return {
            "error": "OPENWEATHER_KEY not set",
            "available": False,
        }

    city = city.strip()

    try:
        # =====================================================
        # 1. Resolve city -> coordinates
        # =====================================================

        geo_response = requests.get(
            GEO_URL,
            params={
                "q": city,
                "limit": 1,
                "appid": OWM_KEY,
            },
            timeout=8,
        )

        geo_response.raise_for_status()

        geo = geo_response.json()

        if not isinstance(geo, list) or not geo:
            return {
                "error": "City not found",
                "available": False,
            }

        location = geo[0]

        latitude = location.get("lat")
        longitude = location.get("lon")

        if latitude is None or longitude is None:
            return {
                "error": "Location coordinates unavailable",
                "available": False,
            }

        # =====================================================
        # 2. Get current weather
        # =====================================================

        weather_response = requests.get(
            WEATHER_URL,
            params={
                "lat": latitude,
                "lon": longitude,
                "appid": OWM_KEY,
                "units": "metric",
            },
            timeout=8,
        )

        weather_response.raise_for_status()

        weather = weather_response.json()

        # =====================================================
        # 3. Validate main weather sections
        # =====================================================

        main = weather.get("main") or {}
        wind = weather.get("wind") or {}
        weather_info = weather.get("weather") or {}
        clouds = weather.get("clouds") or {}

        if not isinstance(weather_info, list):
            weather_info = []

        current_condition = (
            weather_info[0]
            if weather_info
            else {}
        )

        # =====================================================
        # 4. Optional precipitation information
        # =====================================================

        rain = weather.get("rain") or {}
        snow = weather.get("snow") or {}

        # OpenWeather commonly provides these as:
        # rain["1h"], rain["3h"], snow["1h"], etc.
        rain_1h = rain.get("1h")
        snow_1h = snow.get("1h")

        # =====================================================
        # 5. Observation timestamp
        # =====================================================

        observation_timestamp = weather.get("dt")

        observation_time = None

        if observation_timestamp is not None:
            try:
                observation_time = datetime.fromtimestamp(
                    observation_timestamp,
                    tz=timezone.utc,
                ).isoformat()
            except (TypeError, ValueError, OSError):
                observation_time = None

        # =====================================================
        # 6. Return structured weather data
        # =====================================================

        return {
            # -------------------------------------------------
            # Existing VAYORA fields — KEEP THESE
            # -------------------------------------------------
            "temperature": main.get("temp"),
            "humidity": main.get("humidity"),
            "wind_speed": wind.get("speed"),
            "description": current_condition.get(
                "description"
            ),

            # -------------------------------------------------
            # Additional current-weather data
            # -------------------------------------------------
            "feels_like": main.get("feels_like"),
            "temperature_min": main.get("temp_min"),
            "temperature_max": main.get("temp_max"),

            "pressure": main.get("pressure"),
            "sea_level_pressure": main.get("sea_level"),
            "ground_level_pressure": main.get("grnd_level"),

            "visibility": weather.get("visibility"),

            "wind_direction": wind.get("deg"),
            "wind_gust": wind.get("gust"),

            "cloudiness": clouds.get("all"),

            "rain_1h": rain_1h,
            "snow_1h": snow_1h,

            # -------------------------------------------------
            # Location information
            # -------------------------------------------------
            "latitude": latitude,
            "longitude": longitude,

            "city": weather.get("name") or city,
            "country": (
                weather.get("sys") or {}
            ).get("country"),

            # -------------------------------------------------
            # Weather metadata
            # -------------------------------------------------
            "weather_id": current_condition.get("id"),
            "weather_main": current_condition.get("main"),
            "weather_icon": current_condition.get("icon"),

            "observation_timestamp": observation_timestamp,
            "observation_time": observation_time,

            "source": "OpenWeather",
            "available": True,
        }

    # =========================================================
    # HTTP/API errors
    # =========================================================

    except requests.HTTPError as exc:
        status_code = (
            exc.response.status_code
            if exc.response is not None
            else None
        )

        return {
            "error": "OpenWeather request failed",
            "status_code": status_code,
            "available": False,
        }

    # =========================================================
    # Network / timeout errors
    # =========================================================

    except requests.RequestException as exc:
        return {
            "error": f"OpenWeather connection failed: {exc}",
            "available": False,
        }

    # =========================================================
    # Invalid JSON / unexpected API response
    # =========================================================

    except ValueError:
        return {
            "error": "OpenWeather returned invalid data",
            "available": False,
        }

    # =========================================================
    # Unexpected response structure
    # =========================================================

    except (KeyError, TypeError):
        return {
            "error": "OpenWeather returned incomplete weather data",
            "available": False,
        }