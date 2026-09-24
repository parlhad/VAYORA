import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()

# KEEP THE SAME KEY NAME USED EVERYWHERE IN VAYORA
OPENWEATHER_KEY = os.getenv("OPENWEATHER_KEY")


# =========================================================
# OPENWEATHER ENDPOINTS
# =========================================================

GEOCODING_URL = (
    "https://api.openweathermap.org/geo/1.0/direct"
)

WEATHER_FORECAST_URL = (
    "https://api.openweathermap.org/data/2.5/forecast"
)


# =========================================================
# CITY → COORDINATES
# =========================================================

def _get_coords(
    city: str,
) -> Optional[Tuple[float, float]]:
    """
    Resolve a city name into latitude and longitude.

    Uses the same OpenWeather key and geocoding system
    already used by VAYORA's current weather service.
    """

    if not city or not city.strip():
        return None

    if not OPENWEATHER_KEY:
        return None

    try:
        response = requests.get(
            GEOCODING_URL,
            params={
                "q": city.strip(),
                "limit": 1,
                "appid": OPENWEATHER_KEY,
            },
            timeout=8,
        )

        response.raise_for_status()

        locations = response.json()

        if not isinstance(locations, list):
            return None

        if not locations:
            return None

        location = locations[0]

        latitude = location.get("lat")
        longitude = location.get("lon")

        if latitude is None or longitude is None:
            return None

        return float(latitude), float(longitude)

    except (
        requests.RequestException,
        ValueError,
        TypeError,
    ):
        return None


# =========================================================
# WEATHER FORECAST
# =========================================================

def get_weather_forecast(
    city: str,
    hours: int = 24,
) -> Dict[str, Any]:
    """
    Retrieve REAL future weather forecast data from OpenWeather.

    OpenWeather provides forecast points approximately every
    3 hours.

    No weather value is generated or estimated locally.

    Returns:
        available
        source
        city
        coordinates
        forecast
        warnings
    """

    result: Dict[str, Any] = {
        "available": False,
        "source": "OpenWeather",
        "city": city,
        "coordinates": None,
        "forecast": [],
        "warnings": [],
    }

    # =====================================================
    # 1. Validate city
    # =====================================================

    if not city or not city.strip():
        result["warnings"].append(
            "A city is required to retrieve weather forecast."
        )
        return result

    city = city.strip()
    result["city"] = city

    # =====================================================
    # 2. Validate API key
    # =====================================================

    if not OPENWEATHER_KEY:
        result["warnings"].append(
            "OPENWEATHER_KEY not configured in .env."
        )
        return result

    # =====================================================
    # 3. Resolve coordinates
    # =====================================================

    coordinates = _get_coords(city)

    if coordinates is None:
        result["warnings"].append(
            f"Could not resolve the location: {city}."
        )
        return result

    latitude, longitude = coordinates

    result["coordinates"] = {
        "latitude": latitude,
        "longitude": longitude,
    }

    # =====================================================
    # 4. Request REAL OpenWeather forecast
    # =====================================================

    try:
        response = requests.get(
            WEATHER_FORECAST_URL,
            params={
                "lat": latitude,
                "lon": longitude,
                "appid": OPENWEATHER_KEY,
                "units": "metric",
            },
            timeout=10,
        )

        response.raise_for_status()

        payload = response.json()

    except requests.HTTPError as exc:

        status_code = (
            exc.response.status_code
            if exc.response is not None
            else None
        )

        result["warnings"].append(
            f"OpenWeather forecast request failed "
            f"(status {status_code})."
        )

        return result

    except requests.RequestException as exc:

        result["warnings"].append(
            f"OpenWeather forecast connection failed: {exc}"
        )

        return result

    except ValueError:

        result["warnings"].append(
            "OpenWeather returned invalid forecast data."
        )

        return result

    # =====================================================
    # 5. Validate response
    # =====================================================

    entries = payload.get("list")

    if not isinstance(entries, list) or not entries:
        result["warnings"].append(
            "No weather forecast data is available."
        )
        return result

    # =====================================================
    # 6. Extract REAL forecast information
    # =====================================================

    forecast: List[Dict[str, Any]] = []

    for entry in entries:

        if not isinstance(entry, dict):
            continue

        timestamp = entry.get("dt")

        main = entry.get("main") or {}
        weather_list = entry.get("weather") or {}
        wind = entry.get("wind") or {}
        clouds = entry.get("clouds") or {}

        if not isinstance(weather_list, list):
            weather_list = []

        condition = (
            weather_list[0]
            if weather_list
            else {}
        )

        # -------------------------------------------------
        # Rain / snow
        # -------------------------------------------------

        rain = entry.get("rain") or {}
        snow = entry.get("snow") or {}

        rain_3h = rain.get("3h")
        snow_3h = snow.get("3h")

        # -------------------------------------------------
        # Probability of precipitation
        #
        # OpenWeather returns POP as 0–1.
        # Convert to percentage for easier use.
        # -------------------------------------------------

        pop = entry.get("pop")

        rain_probability = None

        if isinstance(pop, (int, float)):
            rain_probability = round(
                max(0.0, min(1.0, pop)) * 100,
                1,
            )

        # -------------------------------------------------
        # Timestamp
        # -------------------------------------------------

        forecast_time = None

        if timestamp is not None:
            try:
                forecast_time = datetime.fromtimestamp(
                    timestamp,
                    tz=timezone.utc,
                ).isoformat()

            except (
                TypeError,
                ValueError,
                OSError,
            ):
                forecast_time = None

        # -------------------------------------------------
        # Structured forecast point
        # -------------------------------------------------

        forecast.append(
            {
                "timestamp": timestamp,
                "forecast_time": forecast_time,

                # Temperature
                "temperature": main.get("temp"),
                "feels_like": main.get("feels_like"),
                "temperature_min": main.get("temp_min"),
                "temperature_max": main.get("temp_max"),

                # Atmospheric conditions
                "humidity": main.get("humidity"),
                "pressure": main.get("pressure"),

                # Wind
                "wind_speed": wind.get("speed"),
                "wind_direction": wind.get("deg"),
                "wind_gust": wind.get("gust"),

                # Clouds / visibility
                "cloudiness": clouds.get("all"),
                "visibility": entry.get("visibility"),

                # Precipitation
                "rain_3h": rain_3h,
                "snow_3h": snow_3h,
                "rain_probability": rain_probability,

                # Weather condition
                "description": condition.get(
                    "description"
                ),

                "weather_main": condition.get(
                    "main"
                ),

                "weather_icon": condition.get(
                    "icon"
                ),

                "weather_id": condition.get(
                    "id"
                ),
            }
        )

    # =====================================================
    # 7. Make sure usable data exists
    # =====================================================

    if not forecast:
        result["warnings"].append(
            "No usable weather forecast entries were returned."
        )
        return result

    # =====================================================
    # 8. Limit forecast window
    #
    # Forecast points are approximately 3 hours apart.
    #
    # Example:
    #   24 hours → ~8 points
    #   48 hours → ~16 points
    #   72 hours → ~24 points
    # =====================================================

    if hours and hours > 0:

        max_entries = max(
            1,
            (hours + 2) // 3,
        )

        forecast = forecast[:max_entries]

    # =====================================================
    # 9. Return successful forecast
    # =====================================================

    result["forecast"] = forecast
    result["available"] = True

    return result


# =========================================================
# BACKWARD / COMPATIBILITY FUNCTION
# =========================================================

def get_forecast(
    city: str,
    hours: int = 24,
    days: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Compatibility wrapper.

    Supports both:

        get_forecast(city, hours=24)

    and the newer:

        get_forecast(city, days=3)

    This prevents the previous:
        unexpected keyword argument 'days'
    error.

    If days is supplied, it takes priority.
    """

    if days is not None:

        try:
            days = int(days)

            if days > 0:
                hours = days * 24

        except (TypeError, ValueError):
            pass

    return get_weather_forecast(
        city,
        hours=hours,
    )


# =========================================================
# FORECAST COORDINATES
# =========================================================

def get_forecast_coordinates(
    city: str,
) -> Optional[Dict[str, float]]:
    """
    Return latitude and longitude for a city.

    Useful later for VAYORA's map/location UI.
    """

    coordinates = _get_coords(city)

    if coordinates is None:
        return None

    latitude, longitude = coordinates

    return {
        "latitude": latitude,
        "longitude": longitude,
    }