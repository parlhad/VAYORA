import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv


# ============================================================
# VAYORA FORECAST SERVICE
# ============================================================
# Uses the SAME OpenWeather environment variable as
# weather_service.py:
#
#     OPENWEATHER_KEY
#
# This service provides:
#   1. OpenWeather air-pollution forecast
#   2. OpenWeather weather forecast
#   3. Rain probability / precipitation
#   4. Temperature
#   5. Humidity
#   6. Wind
#   7. Clouds
#   8. Coordinates
#   9. Tomorrow-specific forecast information
#
# IMPORTANT:
# OpenWeather pollution index (1-5) is NOT WAQI AQI (0-500).
# VAYORA keeps them separate.
# ============================================================


load_dotenv()


# ============================================================
# CONFIGURATION
# ============================================================

OPENWEATHER_KEY = os.getenv("OPENWEATHER_KEY")

GEOCODING_URL = (
    "https://api.openweathermap.org/geo/1.0/direct"
)

AIR_POLLUTION_FORECAST_URL = (
    "https://api.openweathermap.org/data/2.5/air_pollution/forecast"
)

WEATHER_FORECAST_URL = (
    "https://api.openweathermap.org/data/2.5/forecast"
)


# ============================================================
# CITY -> COORDINATES
# ============================================================

def _get_coords(
    city: str,
) -> Optional[Tuple[float, float]]:
    """
    Resolve a city name to latitude and longitude.

    Returns:
        (latitude, longitude)
        or None if the location cannot be resolved.
    """

    if not city or not OPENWEATHER_KEY:
        return None

    try:
        response = requests.get(
            GEOCODING_URL,
            params={
                "q": city,
                "limit": 1,
                "appid": OPENWEATHER_KEY,
            },
            timeout=10,
        )

        response.raise_for_status()

        locations = response.json()

        if not isinstance(locations, list) or not locations:
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


# ============================================================
# TIMESTAMP HELPER
# ============================================================

def _timestamp_to_iso(
    timestamp: Optional[int],
) -> Optional[str]:
    """
    Convert OpenWeather Unix timestamp to UTC ISO time.
    """

    if timestamp is None:
        return None

    try:
        return datetime.fromtimestamp(
            int(timestamp),
            tz=timezone.utc,
        ).isoformat()

    except (
        TypeError,
        ValueError,
        OSError,
    ):
        return None


# ============================================================
# LOCAL FORECAST DATE
# ============================================================

def _timestamp_to_local_date(
    timestamp: Optional[int],
    timezone_offset: int = 0,
) -> Optional[str]:
    """
    Convert an OpenWeather Unix timestamp into the city's
    local calendar date using OpenWeather's timezone offset.
    """

    if timestamp is None:
        return None

    try:
        utc_time = datetime.fromtimestamp(
            int(timestamp),
            tz=timezone.utc,
        )

        local_time = utc_time + timedelta(
            seconds=int(timezone_offset)
        )

        return local_time.date().isoformat()

    except (
        TypeError,
        ValueError,
        OSError,
    ):
        return None


# ============================================================
# MAIN FORECAST FUNCTION
# ============================================================

def get_forecast(
    city: str,
    days: int = 3,
) -> Dict[str, Any]:
    """
    Retrieve real forecast information from OpenWeather.

    Returns two separate forecast datasets:

        pollution_forecast
            OpenWeather pollution index + pollutants

        weather_forecast
            Temperature, rain probability, precipitation,
            humidity, wind, clouds, visibility, etc.

    Also provides a dedicated tomorrow_forecast section.

    IMPORTANT:
    OpenWeather pollution index uses:

        1 = Good
        2 = Fair
        3 = Moderate
        4 = Poor
        5 = Very Poor

    This is NOT WAQI's 0-500 AQI scale.

    VAYORA never converts the 1-5 value into a fake AQI.
    """

    result: Dict[str, Any] = {
        "available": False,
        "source": "OpenWeather",

        "coordinates": None,

        # City timezone information
        "timezone_offset": 0,

        # Pollution forecast
        "pollution_forecast": [],

        # Complete weather forecast
        "weather_forecast": [],

        # Tomorrow-only weather forecast
        "tomorrow_forecast": [],

        # Simple tomorrow summary for the agent
        "tomorrow_summary": {
            "available": False,
            "rain_expected": False,
            "max_rain_probability": 0,
            "total_rain_mm": 0,
            "conditions": [],
            "temperatures": [],
        },

        # Backward-compatible field
        "forecast": [],

        "warnings": [],
    }

    # ========================================================
    # 1. VALIDATE CITY
    # ========================================================

    if not city or not city.strip():

        result["warnings"].append(
            "A city is required to retrieve forecast data."
        )

        return result

    city = city.strip()

    # ========================================================
    # 2. VALIDATE API KEY
    # ========================================================

    if not OPENWEATHER_KEY:

        result["warnings"].append(
            "OPENWEATHER_KEY is not configured."
        )

        return result

    # ========================================================
    # 3. RESOLVE CITY
    # ========================================================

    coords = _get_coords(city)

    if coords is None:

        result["warnings"].append(
            f"Could not resolve the location: {city}."
        )

        return result

    latitude, longitude = coords

    result["coordinates"] = {
        "latitude": latitude,
        "longitude": longitude,
    }

    # ========================================================
    # 4. WEATHER FORECAST
    # ========================================================
    #
    # OpenWeather's /forecast endpoint provides forecast
    # entries at approximately 3-hour intervals.
    #
    # We preserve the real values.
    # Gemini must not invent weather.
    # ========================================================

    weather_forecast: List[Dict[str, Any]] = []

    weather_success = False

    # OpenWeather supplies timezone offset through the
    # forecast response's city object.
    timezone_offset = 0

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

        weather_payload = response.json()

        city_data = weather_payload.get("city") or {}

        try:
            timezone_offset = int(
                city_data.get("timezone", 0)
            )
        except (TypeError, ValueError):
            timezone_offset = 0

        result["timezone_offset"] = timezone_offset

        weather_entries = weather_payload.get("list")

        if isinstance(weather_entries, list):

            max_weather_entries = max(
                1,
                days * 8
            )

            for entry in weather_entries[:max_weather_entries]:

                if not isinstance(entry, dict):
                    continue

                main = entry.get("main") or {}
                wind = entry.get("wind") or {}
                clouds = entry.get("clouds") or {}

                rain = entry.get("rain") or {}
                snow = entry.get("snow") or {}

                weather_items = (
                    entry.get("weather") or []
                )

                condition = (
                    weather_items[0]
                    if weather_items
                    and isinstance(
                        weather_items[0],
                        dict,
                    )
                    else {}
                )

                timestamp = entry.get("dt")

                local_date = _timestamp_to_local_date(
                    timestamp,
                    timezone_offset,
                )

                weather_forecast.append(
                    {
                        # ------------------------------------
                        # Time
                        # ------------------------------------

                        "timestamp": timestamp,

                        "time": _timestamp_to_iso(
                            timestamp
                        ),

                        "local_date": local_date,

                        # ------------------------------------
                        # Temperature
                        # ------------------------------------

                        "temperature": main.get(
                            "temp"
                        ),

                        "feels_like": main.get(
                            "feels_like"
                        ),

                        "temperature_min": main.get(
                            "temp_min"
                        ),

                        "temperature_max": main.get(
                            "temp_max"
                        ),

                        # ------------------------------------
                        # Humidity / pressure
                        # ------------------------------------

                        "humidity": main.get(
                            "humidity"
                        ),

                        "pressure": main.get(
                            "pressure"
                        ),

                        # ------------------------------------
                        # Wind
                        # ------------------------------------

                        "wind_speed": wind.get(
                            "speed"
                        ),

                        "wind_direction": wind.get(
                            "deg"
                        ),

                        "wind_gust": wind.get(
                            "gust"
                        ),

                        # ------------------------------------
                        # Clouds
                        # ------------------------------------

                        "cloudiness": clouds.get(
                            "all"
                        ),

                        # ------------------------------------
                        # Rain / precipitation
                        # ------------------------------------
                        #
                        # POP is probability of
                        # precipitation.
                        #
                        # OpenWeather returns this as
                        # a decimal from 0 to 1.
                        #
                        # Example:
                        # 0.70 = 70%
                        # ------------------------------------

                        "precipitation_probability": (
                            entry.get("pop")
                        ),

                        "rain_3h": rain.get(
                            "3h"
                        ),

                        "snow_3h": snow.get(
                            "3h"
                        ),

                        # ------------------------------------
                        # Visibility
                        # ------------------------------------

                        "visibility": entry.get(
                            "visibility"
                        ),

                        # ------------------------------------
                        # Weather condition
                        # ------------------------------------

                        "weather_id": condition.get(
                            "id"
                        ),

                        "weather_main": condition.get(
                            "main"
                        ),

                        "description": condition.get(
                            "description"
                        ),

                        "weather_icon": condition.get(
                            "icon"
                        ),
                    }
                )

            if weather_forecast:
                weather_success = True

            else:
                result["warnings"].append(
                    "No usable weather forecast entries were returned."
                )

        else:

            result["warnings"].append(
                "OpenWeather returned no weather forecast list."
            )

    except requests.RequestException as exc:

        result["warnings"].append(
            f"OpenWeather weather forecast request failed: {exc}"
        )

    except ValueError:

        result["warnings"].append(
            "OpenWeather returned invalid weather forecast data."
        )

    # ========================================================
    # 5. BUILD TOMORROW FORECAST
    # ========================================================
    #
    # This is the important improvement.
    #
    # Instead of assuming the first 8 entries are tomorrow,
    # determine tomorrow using the city's local timezone.
    # ========================================================

    tomorrow_forecast: List[Dict[str, Any]] = []

    if weather_forecast:

        now_utc = datetime.now(timezone.utc)

        local_now = (
            now_utc
            + timedelta(seconds=timezone_offset)
        )

        tomorrow_date = (
            local_now.date()
            + timedelta(days=1)
        ).isoformat()

        tomorrow_forecast = [
            entry
            for entry in weather_forecast
            if entry.get("local_date") == tomorrow_date
        ]

    result["tomorrow_forecast"] = tomorrow_forecast

    # ========================================================
    # 6. BUILD TOMORROW SUMMARY
    # ========================================================

    tomorrow_summary = {
        "available": bool(tomorrow_forecast),
        "rain_expected": False,
        "max_rain_probability": 0,
        "total_rain_mm": 0,
        "conditions": [],
        "temperatures": [],
    }

    if tomorrow_forecast:

        probabilities: List[float] = []
        rain_amounts: List[float] = []

        conditions = []
        temperatures = []

        for entry in tomorrow_forecast:

            # --------------------------------------------
            # Rain probability
            # --------------------------------------------

            pop = entry.get(
                "precipitation_probability"
            )

            if isinstance(pop, (int, float)):

                pop_percent = float(pop) * 100

                probabilities.append(
                    pop_percent
                )

                # A forecast probability >= 50%
                # is considered a meaningful rain signal.
                if pop_percent >= 50:
                    tomorrow_summary[
                        "rain_expected"
                    ] = True

            # --------------------------------------------
            # Actual forecast precipitation
            # --------------------------------------------

            rain_3h = entry.get("rain_3h")

            if isinstance(rain_3h, (int, float)):

                rain_amounts.append(
                    float(rain_3h)
                )

                if rain_3h > 0:
                    tomorrow_summary[
                        "rain_expected"
                    ] = True

            # --------------------------------------------
            # Conditions
            # --------------------------------------------

            description = entry.get(
                "description"
            )

            if description:
                conditions.append(
                    str(description)
                )

            # --------------------------------------------
            # Temperature
            # --------------------------------------------

            temperature = entry.get(
                "temperature"
            )

            if isinstance(
                temperature,
                (int, float),
            ):
                temperatures.append(
                    float(temperature)
                )

        if probabilities:
            tomorrow_summary[
                "max_rain_probability"
            ] = round(
                max(probabilities),
                1,
            )

        if rain_amounts:
            tomorrow_summary[
                "total_rain_mm"
            ] = round(
                sum(rain_amounts),
                2,
            )

        # Remove duplicate conditions while preserving order.
        tomorrow_summary[
            "conditions"
        ] = list(dict.fromkeys(conditions))

        tomorrow_summary[
            "temperatures"
        ] = temperatures

    result["tomorrow_summary"] = tomorrow_summary

    # ========================================================
    # 7. AIR POLLUTION FORECAST
    # ========================================================

    pollution_forecast: List[Dict[str, Any]] = []

    pollution_success = False

    try:

        response = requests.get(
            AIR_POLLUTION_FORECAST_URL,
            params={
                "lat": latitude,
                "lon": longitude,
                "appid": OPENWEATHER_KEY,
            },
            timeout=10,
        )

        response.raise_for_status()

        pollution_payload = response.json()

        pollution_entries = (
            pollution_payload.get("list")
        )

        if (
            isinstance(
                pollution_entries,
                list,
            )
            and pollution_entries
        ):

            max_pollution_entries = max(
                1,
                days * 24
            )

            for entry in pollution_entries[
                :max_pollution_entries
            ]:

                if not isinstance(entry, dict):
                    continue

                timestamp = entry.get("dt")

                main = entry.get("main") or {}

                components = (
                    entry.get("components")
                    or {}
                )

                pollution_index = main.get(
                    "aqi"
                )

                # -----------------------------------------
                # OpenWeather pollution index is 1-5.
                # NEVER convert it to WAQI AQI.
                # -----------------------------------------

                if pollution_index not in {
                    1,
                    2,
                    3,
                    4,
                    5,
                }:
                    pollution_index = None

                pollution_forecast.append(
                    {
                        "timestamp": timestamp,

                        "time": _timestamp_to_iso(
                            timestamp
                        ),

                        "openweather_index": (
                            pollution_index
                        ),

                        "pollutants": {
                            "co": components.get(
                                "co"
                            ),

                            "no": components.get(
                                "no"
                            ),

                            "no2": components.get(
                                "no2"
                            ),

                            "o3": components.get(
                                "o3"
                            ),

                            "so2": components.get(
                                "so2"
                            ),

                            "pm2_5": components.get(
                                "pm2_5"
                            ),

                            "pm10": components.get(
                                "pm10"
                            ),

                            "nh3": components.get(
                                "nh3"
                            ),
                        },
                    }
                )

            if pollution_forecast:
                pollution_success = True

            else:
                result["warnings"].append(
                    "No usable air-pollution forecast entries were returned."
                )

        else:

            result["warnings"].append(
                "No reliable air-pollution forecast is available."
            )

    except requests.RequestException as exc:

        result["warnings"].append(
            f"OpenWeather pollution forecast request failed: {exc}"
        )

    except ValueError:

        result["warnings"].append(
            "OpenWeather returned invalid pollution forecast data."
        )

    # ========================================================
    # 8. STORE RESULTS
    # ========================================================

    result["weather_forecast"] = (
        weather_forecast
    )

    result["pollution_forecast"] = (
        pollution_forecast
    )

    # ========================================================
    # 9. BACKWARD COMPATIBILITY
    # ========================================================
    #
    # Existing VAYORA code expects:
    #
    #     forecast["forecast"]
    #
    # Keep that field.
    #
    # It contains the pollution forecast because that was the
    # original meaning of this function.
    # ========================================================

    result["forecast"] = (
        pollution_forecast
    )

    # ========================================================
    # 10. AVAILABILITY
    # ========================================================
    #
    # Forecast service is available if at least one real
    # forecast dataset was retrieved.
    #
    # This allows:
    #
    # weather available + pollution unavailable
    #
    # OR
    #
    # pollution available + weather unavailable
    # ========================================================

    if weather_success or pollution_success:

        result["available"] = True

    else:

        result["available"] = False

    # ========================================================
    # 11. DATA STATUS
    # ========================================================

    if weather_success and pollution_success:

        result["data_status"] = "live"

    elif weather_success or pollution_success:

        result["data_status"] = "partial"

    else:

        result["data_status"] = "unavailable"

    return result


# ============================================================
# BACKWARD-COMPATIBLE PUBLIC FUNCTION
# ============================================================

def get_aqi_forecast(
    city: str,
    days: int = 3,
) -> Dict[str, Any]:
    """
    Backward-compatible public function.

    Existing VAYORA files already import:

        get_aqi_forecast()

    Therefore DO NOT rename/remove this function.
    """

    return get_forecast(
        city=city,
        days=days,
    )


# ============================================================
# COORDINATES FOR FUTURE MAP
# ============================================================

def get_forecast_coordinates(
    city: str,
) -> Optional[Dict[str, float]]:
    """
    Resolve coordinates for a city.

    Intended for VAYORA's future map integration.
    """

    coords = _get_coords(city)

    if coords is None:
        return None

    latitude, longitude = coords

    return {
        "latitude": latitude,
        "longitude": longitude,
    }