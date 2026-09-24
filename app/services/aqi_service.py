import os
import time
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv


load_dotenv()


WAQI_TOKEN = os.getenv("WAQI_TOKEN")
BASE_URL = "https://api.waqi.info/feed"


# ============================================================
# CACHE
# ============================================================
#
# The existing 15-minute cache is intentionally preserved.
#
# Why:
# - Reduces unnecessary requests to the free WAQI API.
# - Prevents repeated requests for the same city.
# - Keeps data reasonably fresh.
#
# IMPORTANT:
# Cached data is explicitly marked as recent/cached.
# It is never presented as a freshly fetched API observation.
# ============================================================

_cache: Dict[str, dict] = {}

CACHE_TTL = 15 * 60  # 15 minutes


def _cache_key(city: str) -> str:
    """
    Create a normalized cache key for a city.
    """

    return city.lower().strip()


def _get_cache(city: str) -> Optional[dict]:
    """
    Return valid cached data if it is still within CACHE_TTL.

    The returned dictionary is copied so callers cannot
    accidentally modify the stored cache entry.
    """

    if not city:
        return None

    entry = _cache.get(_cache_key(city))

    if not entry:
        return None

    cached_at = entry.get("_cached_at")

    if cached_at is None:
        return None

    try:
        age = time.time() - float(cached_at)
    except (TypeError, ValueError):
        return None

    # If the system clock moved backwards, don't trust
    # the cache age.
    if age < 0:
        return None

    if age < CACHE_TTL:

        result = {
            **entry,

            # This request was served from local cache.
            "_from_cache": True,

            # Useful later for the UI:
            # "Data checked X minutes ago"
            "_cache_age_seconds": round(age, 1),

            # The observation itself is still the original
            # WAQI observation, but our current request was
            # served from cache.
            "data_status": "recent",
        }

        return result

    return None


def _set_cache(city: str, data: dict):
    """
    Store successful WAQI data in the local in-memory cache.
    """

    _cache[_cache_key(city)] = {
        **data,
        "_cached_at": time.time(),
    }


def _extract_coordinates(
    data: Dict[str, Any]
) -> Optional[Dict[str, float]]:
    """
    Extract WAQI station/city coordinates when available.

    WAQI may return:

        "city": {
            "geo": [latitude, longitude]
        }

    If coordinates are missing or malformed, return None.

    No coordinates are guessed.
    """

    city_data = data.get("city") or {}

    geo = city_data.get("geo")

    if not isinstance(geo, (list, tuple)):
        return None

    if len(geo) < 2:
        return None

    try:
        latitude = float(geo[0])
        longitude = float(geo[1])

        return {
            "latitude": latitude,
            "longitude": longitude,
        }

    except (TypeError, ValueError):
        return None


def _normalize_aqi(value: Any):
    """
    Validate and normalize the WAQI AQI value.

    If WAQI does not provide a valid numeric AQI,
    return None rather than estimating or inventing one.
    """

    if value is None:
        return None

    if isinstance(value, bool):
        return None

    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return None

    if numeric_value < 0:
        return None

    if numeric_value.is_integer():
        return int(numeric_value)

    return numeric_value


# ============================================================
# MAIN FUNCTION
# ============================================================

def get_city_aqi(city: str) -> dict:
    """
    Retrieve current AQI information for a city from WAQI.

    Existing VAYORA fields are preserved:

        city
        aqi
        pollutants
        station
        time
        _from_cache
        error

    Additional metadata:

        resolved_city
        source
        observation_timezone
        coordinates
        latitude
        longitude
        data_status
        _cache_age_seconds

    No AQI value is estimated when WAQI does not provide one.
    """

    # =========================================================
    # 1. Validate city
    # =========================================================

    if not city or not city.strip():
        return {
            "error": "City is required",
            "data_status": "unavailable",
        }

    city = city.strip()

    # =========================================================
    # 2. Check cache first
    # =========================================================

    cached = _get_cache(city)

    if cached:

        print(
            f"[AQI] Cache HIT — {city} "
            f"({cached.get('_cache_age_seconds', 0):.0f}s old)"
        )

        return cached

    print(f"[AQI] Fetching live WAQI data — {city}")

    # =========================================================
    # 3. Validate WAQI token
    # =========================================================

    if not WAQI_TOKEN or WAQI_TOKEN == "YOUR_WAQI_TOKEN_HERE":
        return {
            "error": "WAQI_TOKEN not configured in .env",
            "data_status": "unavailable",
        }

    # =========================================================
    # 4. Request WAQI
    # =========================================================

    try:

        url = f"{BASE_URL}/{city}/"

        response = requests.get(
            url,
            params={
                "token": WAQI_TOKEN,
            },
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

    except requests.exceptions.Timeout:

        return {
            "error": "AQI API timed out. Try again.",
            "data_status": "unavailable",
        }

    except requests.exceptions.ConnectionError:

        return {
            "error": "Network error. Check your internet connection.",
            "data_status": "unavailable",
        }

    except requests.exceptions.HTTPError as exc:

        status_code = (
            exc.response.status_code
            if exc.response is not None
            else None
        )

        return {
            "error": "WAQI request failed.",
            "status_code": status_code,
            "data_status": "unavailable",
        }

    except requests.exceptions.RequestException as exc:

        return {
            "error": f"WAQI connection failed: {exc}",
            "data_status": "unavailable",
        }

    except ValueError:

        return {
            "error": "WAQI returned invalid data.",
            "data_status": "unavailable",
        }

    # =========================================================
    # 5. Validate WAQI response
    # =========================================================

    if not isinstance(data, dict):

        return {
            "error": "WAQI returned an unexpected response.",
            "data_status": "unavailable",
        }

    if data.get("status") != "ok":

        return {
            "error": f"No AQI data found for '{city}'.",
            "data_status": "unavailable",
        }

    waqi_data = data.get("data")

    if not isinstance(waqi_data, dict):

        return {
            "error": "WAQI returned incomplete AQI data.",
            "data_status": "unavailable",
        }

    # =========================================================
    # 6. Extract and validate AQI
    # =========================================================

    raw_aqi = waqi_data.get("aqi")

    aqi = _normalize_aqi(raw_aqi)

    if aqi is None:

        return {
            "error": (
                f"WAQI did not provide a valid current AQI "
                f"for '{city}'."
            ),
            "data_status": "unavailable",
        }

    # =========================================================
    # 7. Extract pollutant / IAQI data
    # =========================================================

    iaqi = waqi_data.get("iaqi") or {}

    if not isinstance(iaqi, dict):
        iaqi = {}

    # Preserve WAQI's original IAQI structure.
    pollutants = iaqi

    # =========================================================
    # 8. Station information
    # =========================================================

    city_data = waqi_data.get("city") or {}

    station = city_data.get("name") or city

    resolved_city = city_data.get("name") or city

    # =========================================================
    # 9. Observation time
    # =========================================================

    time_data = waqi_data.get("time") or {}

    observation_time = time_data.get("s")

    if not observation_time:
        observation_time = "Unknown"

    observation_timezone = time_data.get("tz")

    # =========================================================
    # 10. Coordinates
    # =========================================================

    coordinates = _extract_coordinates(waqi_data)

    latitude = None
    longitude = None

    if coordinates:

        latitude = coordinates.get("latitude")
        longitude = coordinates.get("longitude")

    # =========================================================
    # 11. Build successful live result
    # =========================================================

    result = {

        # -----------------------------------------------------
        # Existing VAYORA fields — preserved
        # -----------------------------------------------------

        "city": city,

        "aqi": aqi,

        "pollutants": pollutants,

        "station": station,

        "time": observation_time,

        "_from_cache": False,

        # -----------------------------------------------------
        # Additional trusted metadata
        # -----------------------------------------------------

        "resolved_city": resolved_city,

        "source": "WAQI",

        "observation_timezone": observation_timezone,

        "coordinates": coordinates,

        "latitude": latitude,

        "longitude": longitude,

        # This means the API was actually contacted for this
        # result.
        "data_status": "live",

        "_cache_age_seconds": 0,
    }

    # =========================================================
    # 12. Cache only successful data
    # =========================================================

    _set_cache(city, result)

    return result