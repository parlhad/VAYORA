import os
import requests
from dotenv import load_dotenv

load_dotenv()

OWM_KEY = os.getenv("OPENWEATHER_KEY")

GEO_URL = "http://api.openweathermap.org/geo/1.0/direct"
AQI_URL = "http://api.openweathermap.org/data/2.5/air_pollution/forecast"


# -------------------------------------------------------
# ✅ HELPER: GET CITY COORDINATES
# -------------------------------------------------------
def _get_coords(city: str):
    try:
        r = requests.get(
            GEO_URL,
            params={"q": city, "limit": 1, "appid": OWM_KEY},
            timeout=8
        )
        data = r.json()
        if data:
            return data[0]["lat"], data[0]["lon"]
    except:
        pass
    return None, None


# -------------------------------------------------------
# ✅ HELPER: AQI TREND LOGIC (SAFE)
# -------------------------------------------------------
def _analyze_trend(today_avg, tomorrow_avg):
    if tomorrow_avg > today_avg + 0.5:
        return "worse", "Pollution expected to increase"
    elif tomorrow_avg < today_avg - 0.5:
        return "improving", "Air quality likely to improve"
    else:
        return "similar", "No major change expected"


# -------------------------------------------------------
# ✅ MAIN FUNCTION (V1 + V3 MERGED)
# -------------------------------------------------------
def get_aqi_forecast(city: str):
    """
    SAFE MERGED VERSION:
    - V1 base structure preserved
    - V3 real API added
    - fallback always works
    """

    # ==============================
    # 🔵 TRY REAL API (V3)
    # ==============================
    if OWM_KEY and OWM_KEY != "YOUR_OPENWEATHER_API_KEY_HERE":

        lat, lon = _get_coords(city)

        if lat and lon:
            try:
                r = requests.get(
                    AQI_URL,
                    params={"lat": lat, "lon": lon, "appid": OWM_KEY},
                    timeout=10
                )

                data = r.json()
                items = data.get("list", [])

                if len(items) >= 24:

                    today_avg = sum(i["main"]["aqi"] for i in items[:8]) / 8
                    tomorrow_avg = sum(i["main"]["aqi"] for i in items[8:32]) / 24

                    change, reason = _analyze_trend(today_avg, tomorrow_avg)

                    return {
                        "tomorrow": {
                            "expected_change": change,
                            "reason": f"Based on OpenWeather forecast (avg index {tomorrow_avg:.1f})",
                            "advice": "Plan activities accordingly. Limit exposure if pollution increases."
                        }
                    }

            except Exception:
                pass  # fallback below

    # ==============================
    # 🟡 FALLBACK (V1 IMPROVED)
    # ==============================
    return {
        "tomorrow": {
            "expected_change": "similar to today",
            "reason": "Forecast API unavailable — using safe estimation",
            "advice": "Monitor AQI and plan outdoor activities carefully"
        }
    }