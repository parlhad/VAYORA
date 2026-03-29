import os
import time
import requests
from typing import Dict
from dotenv import load_dotenv

load_dotenv()

WAQI_TOKEN = os.getenv("WAQI_TOKEN")
BASE_URL = "https://api.waqi.info/feed"

# -------------------------------------------------------
# ✅ CACHE (FROM V2 — VERY IMPORTANT)
# -------------------------------------------------------
_cache: Dict[str, dict] = {}
CACHE_TTL = 15 * 60  # 15 minutes


def _cache_key(city: str) -> str:
    return city.lower().strip()


def _get_cache(city: str):
    entry = _cache.get(_cache_key(city))
    if entry:
        age = time.time() - entry.get("_cached_at", 0)
        if age < CACHE_TTL:
            return {**entry, "_from_cache": True}
    return None


def _set_cache(city: str, data: dict):
    _cache[_cache_key(city)] = {**data, "_cached_at": time.time()}


# -------------------------------------------------------
# ✅ MAIN FUNCTION (V1 + V2 + V3 MERGED)
# -------------------------------------------------------
def get_city_aqi(city: str) -> dict:

    # 🔥 1. CHECK CACHE FIRST
    cached = _get_cache(city)
    if cached:
        print(f"[AQI] ⚡ Cache HIT — {city}")
        return cached

    print(f"[AQI] 🌐 Fetching live — {city}")

    # 🔥 2. CHECK TOKEN (V3)
    if not WAQI_TOKEN or WAQI_TOKEN == "YOUR_WAQI_TOKEN_HERE":
        return {"error": "WAQI_TOKEN not configured in .env"}

    try:
        # 🔥 3. API CALL (V1)
        url = f"{BASE_URL}/{city}/?token={WAQI_TOKEN}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        # 🔥 4. VALIDATION
        if data.get("status") != "ok":
            return {"error": f"No AQI data found for '{city}'"}

        iaqi = data["data"].get("iaqi", {})
        aqi = data["data"].get("aqi")
        time_data = data["data"].get("time", {}).get("s", "Unknown")
        station = data["data"].get("city", {}).get("name", city)

        result = {
            "city": city,
            "aqi": aqi,
            "pollutants": iaqi,
            "station": station,
            "time": time_data,
            "_from_cache": False
        }

        # 🔥 5. SAVE CACHE
        _set_cache(city, result)

        return result

    except requests.exceptions.Timeout:
        return {"error": "AQI API timed out. Try again."}

    except requests.exceptions.ConnectionError:
        return {"error": "Network error. Check your internet."}

    except Exception as e:
        return {"error": f"AQI fetch failed: {str(e)}"}