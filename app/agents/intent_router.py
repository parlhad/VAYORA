"""
VAYORA Intent Router — FINAL MERGED (V1 + V2 BEST VERSION)
══════════════════════════════════════════════════════════════
"""

import re
from typing import Optional, Dict

# ── KEYWORD BANKS (Merged: V1 + V2) ─────────────────────────

AQI_KEYWORDS = [
    "aqi", "air quality", "airquality", "pollution", "polluted", "smog",
    "pm2.5", "pm25", "pm10", "o3", "ozone", "no2", "so2", "co",
    "breathing", "asthma", "mask", "lungs", "cough", "chest", "allergy",
    "particulate", "dust", "haze", "visibility", "toxic air"
]

WEATHER_KEYWORDS = [
    "weather", "temperature", "humidity", "rain", "wind", "fog",
    "cloud", "sunny", "hot", "cold", "humid", "forecast", "climate"
]

HEALTH_KEYWORDS = [
    "health", "symptom", "disease", "sick", "hospital", "doctor",
    "medicine", "remedy", "relief", "breathing problem", "home remedy",
    "prevention", "precaution", "protect", "safe", "safety"
]

ENVIRONMENT_KEYWORDS = [
    "environment", "nature", "ecosystem", "global warming", "climate change",
    "greenhouse", "carbon", "emission", "deforestation", "biodiversity",
    "ocean", "soil", "water pollution", "noise pollution", "plastic"
]

REALTIME_WORDS = [
    "now", "right now", "currently", "live", "today", "at the moment",
    "this time", "present", "real time", "realtime", "current"
]

FORECAST_WORDS = [
    "tomorrow", "next", "later", "evening", "tonight", "morning",
    "next hours", "next 3 hours", "next 6 hours", "next 24 hours",
    "forecast", "prediction", "will it", "expected", "trend"
]

DECISION_WORDS = [
    "safe", "should i", "can i", "is it okay", "go outside", "outdoor",
    "run", "jog", "walk", "gym", "exercise", "cycling", "bike",
    "school", "sports", "event", "office", "travel", "play outside"
]

SMALL_TALK_WORDS = [
    "hi", "hello", "hey", "good morning", "good evening", "good night",
    "thanks", "thank you", "ok", "okay", "bye", "who are you",
    "what are you", "what can you do", "help me"
]

# ── CITY EXTRACTION ─────────────────────────────────────────

CITY_PATTERNS = [
    r"\baqi\s+in\s+([A-Za-z\s]+)",
    r"\bair\s+quality\s+in\s+([A-Za-z\s]+)",
    r"\baqi\s+for\s+([A-Za-z\s]+)",
    r"\bpollution\s+in\s+([A-Za-z\s]+)",
    r"\b([A-Za-z\s]+)\s+aqi\b",
    r"\b([A-Za-z\s]+)\s+air\s+quality\b",
    r"\bweather\s+in\s+([A-Za-z\s]+)",
    r"\bforecast\s+for\s+([A-Za-z\s]+)",
    r"\bin\s+([A-Za-z\s]+)\s+today\b",
    r"\bin\s+([A-Za-z\s]+)\s+now\b",
]

BAD_CITY_WORDS = {
    "short", "meaning", "define", "definition", "what", "why", "how",
    "today", "tomorrow", "now", "current", "currently", "live",
    "hours", "hour", "next", "forecast", "prediction", "safe", "run",
    "jog", "walk", "gym", "exercise", "aqi", "air", "quality",
    "pollution", "pm25", "pm2.5", "pm10", "o3", "no2", "so2", "co",
    "weather", "temperature", "outside", "outdoor"
}

def clean_city_name(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"[^A-Za-z\s]", "", raw)
    raw = re.sub(r"\s+", " ", raw)
    return raw.title()

def looks_like_real_city(city: str) -> bool:
    if not city:
        return False
    c = city.strip().lower()
    if len(c) < 3:
        return False
    if len(c.split()) > 3:
        return False
    if c in BAD_CITY_WORDS:
        return False
    if all(w in BAD_CITY_WORDS for w in c.split()):
        return False
    return True

def extract_city(message: str) -> Optional[str]:
    text = message.strip()
    for pattern in CITY_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            city = clean_city_name(m.group(1))
            city = re.sub(
                r"\b(today|tomorrow|now|current|currently|live|weather|forecast)\b",
                "", city, flags=re.IGNORECASE
            ).strip()
            city = re.sub(r"\s+", " ", city).strip()
            if looks_like_real_city(city):
                return city
    return None

def contains_any(text: str, keywords: list) -> bool:
    t = text.lower()
    return any(k in t for k in keywords)

def detect_time_query(msg_low: str) -> Optional[str]:
    if any(x in msg_low for x in ["next 2 hours", "next 3 hours", "next hours", "next hour"]):
        return "next_hours"
    if "tomorrow" in msg_low:
        return "tomorrow"
    if any(x in msg_low for x in ["now", "right now", "currently", "live", "today", "current"]):
        return "now"
    return None

# ── KNOWLEDGE PATTERNS ─────────────────────────────────────

PURE_KNOWLEDGE_PATTERNS = [
    "what is aqi", "aqi meaning", "define aqi",
    "what is pm2.5", "what is pm10", "what is no2", "what is ozone",
    "how pollution affects", "effects of pollution",
    "why air pollution", "health effects of pollution",
    "what causes smog", "how to reduce pollution",
    "what is climate change", "global warming",
    "home remedy", "home remedies", "natural remedy",
    "breathing exercise", "lung health",
    "how to protect", "how to prevent pollution",
    "what is environment", "ecosystem", "biodiversity",
    "what is pm", "what does aqi mean", "explain aqi",
]

# ── MAIN ROUTER ───────────────────────────────────────────

def route_intent(message: str) -> Dict:
    msg = message.strip()
    msg_low = msg.lower()

    city = extract_city(msg)
    time_query = detect_time_query(msg_low)

    # 1) Small talk
    if contains_any(msg_low, SMALL_TALK_WORDS) and len(msg_low.split()) <= 6:
        return {"intent": "GENERAL_CHAT", "city": None, "time_query": None, "confidence": 0.95}

    is_aqi_word    = contains_any(msg_low, AQI_KEYWORDS)
    is_weather     = contains_any(msg_low, WEATHER_KEYWORDS)
    is_health      = contains_any(msg_low, HEALTH_KEYWORDS)
    is_environment = contains_any(msg_low, ENVIRONMENT_KEYWORDS)
    has_city       = city is not None
    is_realtime    = contains_any(msg_low, REALTIME_WORDS)
    is_forecast    = contains_any(msg_low, FORECAST_WORDS)
    is_decision    = contains_any(msg_low, DECISION_WORDS)

    # 2) Pure knowledge
    if any(p in msg_low for p in PURE_KNOWLEDGE_PATTERNS):
        return {"intent": "ENVIRONMENT_KNOWLEDGE", "city": None, "time_query": None, "confidence": 0.97}

    # 3) Health advice
    if is_health and not has_city and not is_aqi_word:
        return {"intent": "HEALTH_ADVICE", "city": None, "time_query": None, "confidence": 0.90}

    # 4) Forecast
    if has_city and (is_forecast or is_weather):
        return {"intent": "CITY_AQI_FORECAST", "city": city, "time_query": time_query or "tomorrow", "confidence": 0.92}

    # 5) Live AQI / decision (IMPROVED PRIORITY)
    if has_city and (is_decision or is_realtime or is_aqi_word):
        return {"intent": "CITY_AQI_NOW", "city": city, "time_query": time_query or "now", "confidence": 0.93}

    # 6) City missing (IMPROVED)
    if (is_aqi_word or is_weather or is_decision) and not has_city:
        return {"intent": "CITY_REQUIRED", "city": None, "time_query": None, "confidence": 0.85}

    # 7) Knowledge fallback
    if is_aqi_word or is_environment or is_health:
        return {"intent": "ENVIRONMENT_KNOWLEDGE", "city": None, "time_query": None, "confidence": 0.80}
   
    if not city and any(word in message.lower() for word in ["hi", "hello", "hey","good morning", "good evening", "good night","thanks", "thank you","ok", "okay","bye"]):
        return {"intent": "GENERAL_CHAT", "city": None}
    if any(word in message.lower() for word in ["weather", "temperature", "rain", "humidity", "wind"]):
        return {"intent": "WEATHER_QUERY", "city": city, "time_query": "now", "confidence": 0.9}
    
    
    if city:
        city = city.replace("today", "").replace("tomorrow", "")
        city = city.replace("and", "").replace("of", "")
        city = city.strip()
    

    # 8) Default
    return {"intent": "ENVIRONMENT_KNOWLEDGE", "city": None, "time_query": None, "confidence": 0.70}