"""
VAYORA Intent Router
====================

Deterministic first-stage router for VAYORA.

Purpose:
- Understand what the user is asking.
- Extract city/location when possible.
- Detect current vs future requests.
- Separate AQI requests from weather requests.
- Detect health, environmental knowledge, and activity decisions.

IMPORTANT:
- No Gemini/API call happens here.
- No live environmental value is generated here.
- This file decides WHAT VAYORA needs to do.
- Actual live data retrieval happens later in the pipeline.

Main intent types:
    GENERAL_CHAT
    ENVIRONMENT_KNOWLEDGE
    HEALTH_ADVICE
    CITY_REQUIRED
    CITY_AQI_NOW
    CITY_AQI_FORECAST
    WEATHER_QUERY
    WEATHER_FORECAST
    ENVIRONMENT_LIVE
    OUTDOOR_DECISION
"""

import re
from typing import Optional, Dict, Any


# ============================================================
# KEYWORD BANKS
# ============================================================

AQI_KEYWORDS = [
    "aqi",
    "air quality",
    "airquality",
    "pollution",
    "polluted",
    "smog",
    "pm2.5",
    "pm25",
    "pm 2.5",
    "pm10",
    "pm 10",
    "o3",
    "ozone",
    "no2",
    "so2",
    "co",
    "particulate",
    "particulate matter",
    "dust",
    "haze",
    "toxic air",
    "air pollution",
]


WEATHER_KEYWORDS = [
    "weather",
    "temperature",
    "temp",
    "humidity",
    "rain",
    "raining",
    "rainfall",
    "precipitation",
    "wind",
    "wind speed",
    "wind direction",
    "fog",
    "cloud",
    "clouds",
    "cloudy",
    "sunny",
    "sun",
    "hot",
    "heat",
    "cold",
    "cool",
    "humid",
    "visibility",
    "pressure",
    "feels like",
    "forecast",
    "weather forecast",
    "will it rain",
    "is it going to rain",
    "chance of rain",
    "rain probability",
]


HEALTH_KEYWORDS = [
    "health",
    "symptom",
    "symptoms",
    "disease",
    "sick",
    "hospital",
    "doctor",
    "medicine",
    "medication",
    "remedy",
    "remedies",
    "relief",
    "breathing problem",
    "breathing difficulty",
    "home remedy",
    "prevention",
    "precaution",
    "protect",
    "protection",
    "safe",
    "safety",
    "cough",
    "asthma",
    "copd",
    "lungs",
    "lung",
    "chest pain",
    "headache",
    "allergy",
]


ENVIRONMENT_KEYWORDS = [
    "environment",
    "environmental",
    "nature",
    "ecosystem",
    "global warming",
    "climate change",
    "greenhouse",
    "greenhouse gas",
    "carbon",
    "carbon dioxide",
    "emission",
    "emissions",
    "deforestation",
    "biodiversity",
    "ocean",
    "soil",
    "water pollution",
    "noise pollution",
    "plastic pollution",
    "climate",
]


REALTIME_WORDS = [
    "now",
    "right now",
    "currently",
    "live",
    "today",
    "at the moment",
    "this time",
    "present",
    "real time",
    "realtime",
    "current",
]


FORECAST_WORDS = [
    "tomorrow",
    "tonight",
    "later",
    "evening",
    "morning",
    "next",
    "next hour",
    "next hours",
    "next 2 hours",
    "next 3 hours",
    "next 6 hours",
    "next 12 hours",
    "next 24 hours",
    "next few hours",
    "next couple of hours",
    "forecast",
    "prediction",
    "predict",
    "will it",
    "expected",
    "expect",
    "trend",
    "coming hours",
    "coming days",
]


DECISION_WORDS = [
    "safe",
    "should i",
    "should we",
    "can i",
    "can we",
    "is it okay",
    "is it safe",
    "go outside",
    "outside",
    "outdoor",
    "outdoors",
    "run",
    "jog",
    "walk",
    "gym",
    "exercise",
    "cycling",
    "cycle",
    "bike",
    "school",
    "sports",
    "sport",
    "event",
    "office",
    "travel",
    "trip",
    "play outside",
    "play",
]


SMALL_TALK_WORDS = [
    "hi",
    "hello",
    "hey",
    "good morning",
    "good afternoon",
    "good evening",
    "good night",
    "thanks",
    "thank you",
    "ok",
    "okay",
    "bye",
    "who are you",
    "what are you",
    "what can you do",
    "help me",
]


# ============================================================
# CITY EXTRACTION
# ============================================================

CITY_PATTERNS = [

    # --------------------------------------------------------
    # AQI
    # --------------------------------------------------------

    r"\baqi\s+in\s+([A-Za-z][A-Za-z\s\-]*)",
    r"\bair\s+quality\s+in\s+([A-Za-z][A-Za-z\s\-]*)",
    r"\baqi\s+for\s+([A-Za-z][A-Za-z\s\-]*)",
    r"\bair\s+quality\s+for\s+([A-Za-z][A-Za-z\s\-]*)",
    r"\bpollution\s+in\s+([A-Za-z][A-Za-z\s\-]*)",
    r"\bpollution\s+for\s+([A-Za-z][A-Za-z\s\-]*)",

    # --------------------------------------------------------
    # CURRENT WEATHER
    # --------------------------------------------------------

    r"\bweather\s+in\s+([A-Za-z][A-Za-z\s\-]*)",
    r"\bweather\s+for\s+([A-Za-z][A-Za-z\s\-]*)",
    r"\btemperature\s+in\s+([A-Za-z][A-Za-z\s\-]*)",
    r"\btemp\s+in\s+([A-Za-z][A-Za-z\s\-]*)",
    r"\brain\s+in\s+([A-Za-z][A-Za-z\s\-]*)",
    r"\brainfall\s+in\s+([A-Za-z][A-Za-z\s\-]*)",
    r"\bprecipitation\s+in\s+([A-Za-z][A-Za-z\s\-]*)",
    r"\bhumidity\s+in\s+([A-Za-z][A-Za-z\s\-]*)",
    r"\bwind\s+in\s+([A-Za-z][A-Za-z\s\-]*)",
    r"\bhot\s+in\s+([A-Za-z][A-Za-z\s\-]*)",
    r"\bheat\s+in\s+([A-Za-z][A-Za-z\s\-]*)",

    # --------------------------------------------------------
    # OUTDOOR / ACTIVITY QUESTIONS
    # --------------------------------------------------------

    r"\b(?:outside|outdoors|run|jog|walk|exercise|cycling|cycle|bike|gym)\s+in\s+([A-Za-z][A-Za-z\s\-]*)",

    r"\b(?:can|should)\s+i\s+(?:go\s+)?(?:outside|outdoors|run|jog|walk|exercise|cycle|cycling|bike|gym)\s+in\s+([A-Za-z][A-Za-z\s\-]*)",

    r"\b(?:is\s+it|is)\s+(?:safe|okay|good)\s+to\s+(?:go\s+)?(?:outside|outdoors|run|jog|walk|exercise)\s+in\s+([A-Za-z][A-Za-z\s\-]*)",

    # --------------------------------------------------------
    # FORECAST
    # --------------------------------------------------------

    r"\bforecast\s+for\s+([A-Za-z][A-Za-z\s\-]*)",
    r"\bforecast\s+in\s+([A-Za-z][A-Za-z\s\-]*)",
    r"\bprediction\s+for\s+([A-Za-z][A-Za-z\s\-]*)",

    # --------------------------------------------------------
    # NATURAL-LANGUAGE FUTURE AQI
    # --------------------------------------------------------
    #
    # Examples:
    # AQI tomorrow in Pune
    # air quality tomorrow in Pune
    # pollution tomorrow in Pune
    #
    # Also:
    # AQI in Pune tomorrow
    # air quality in Pune tomorrow
    #
    # --------------------------------------------------------

    r"\b(?:aqi|air\s+quality|pollution)\s+(?:tomorrow|tonight|later|today)\s+in\s+([A-Za-z][A-Za-z\s\-]*?)(?:[?.!,]|$)",

    r"\b(?:aqi|air\s+quality|pollution)\s+in\s+([A-Za-z][A-Za-z\s\-]*?)(?=\s+(?:tomorrow|tonight|later|today)\b|[?.!,]|$)",

    # --------------------------------------------------------
    # NATURAL-LANGUAGE FUTURE WEATHER
    # --------------------------------------------------------
    #
    # Examples:
    # will it rain tomorrow in Pune
    # will it rain in Pune tomorrow
    # is it going to rain tomorrow in Pune
    # temperature tomorrow in Pune
    # weather tomorrow in Pune
    # rain tomorrow in Pune
    #
    # --------------------------------------------------------

    r"\b(?:will\s+it|is\s+it\s+going\s+to)\s+(?:rain|raining|rainfall|drizzle|storm|thunderstorm)\s+(?:tomorrow|tonight|later|today)\s+in\s+([A-Za-z][A-Za-z\s\-]*?)(?:[?.!,]|$)",

    r"\b(?:will\s+it|is\s+it\s+going\s+to)\s+(?:rain|raining|rainfall|drizzle|storm|thunderstorm)\s+in\s+([A-Za-z][A-Za-z\s\-]*?)(?=\s+(?:tomorrow|tonight|later|today)\b|[?.!,]|$)",

    r"\b(?:weather|temperature|temp|humidity|wind|rain|rainfall|precipitation|heat|hot|cold)\s+(?:tomorrow|tonight|later|today)\s+in\s+([A-Za-z][A-Za-z\s\-]*?)(?:[?.!,]|$)",

    r"\b(?:weather|temperature|temp|humidity|wind|rain|rainfall|precipitation|heat|hot|cold)\s+in\s+([A-Za-z][A-Za-z\s\-]*?)(?=\s+(?:tomorrow|tonight|later|today)\b|[?.!,]|$)",

    # --------------------------------------------------------
    # GENERIC LOCATION FORMS
    # --------------------------------------------------------

    r"\bin\s+([A-Za-z][A-Za-z\s\-]*)\s+today\b",
    r"\bin\s+([A-Za-z][A-Za-z\s\-]*)\s+tomorrow\b",
    r"\bin\s+([A-Za-z][A-Za-z\s\-]*)\s+now\b",
]


BAD_CITY_WORDS = {
    "short",
    "meaning",
    "define",
    "definition",
    "what",
    "why",
    "how",
    "today",
    "tomorrow",
    "now",
    "current",
    "currently",
    "live",
    "hours",
    "hour",
    "next",
    "forecast",
    "prediction",
    "predict",
    "safe",
    "run",
    "jog",
    "walk",
    "gym",
    "exercise",
    "aqi",
    "air",
    "quality",
    "pollution",
    "pm25",
    "pm2",
    "pm2.5",
    "pm10",
    "o3",
    "no2",
    "so2",
    "co",
    "weather",
    "temperature",
    "temp",
    "rain",
    "rainfall",
    "precipitation",
    "outside",
    "outdoor",
    "humidity",
    "wind",
    "hot",
    "heat",
    "cold",
    "cloud",
    "cloudy",
    "visibility",
}


CITY_STOP_WORDS = {
    "today",
    "tomorrow",
    "now",
    "currently",
    "current",
    "live",
    "right",
    "forecast",
    "prediction",
    "expected",
    "later",
    "tonight",
    "morning",
    "evening",
    "afternoon",
    "next",
    "hours",
    "hour",
    "weather",
    "temperature",
    "temp",
    "rain",
    "rainfall",
    "precipitation",
    "humidity",
    "wind",
    "aqi",
    "air",
    "quality",
    "pollution",
    "safe",
    "outside",
    "outdoor",
    "should",
    "can",
    "will",
}


def clean_city_name(raw: str) -> str:
    """
    Clean a city extracted from natural language.
    """

    raw = raw.strip()

    # Remove punctuation.
    raw = re.sub(r"[^A-Za-z\s\-]", " ", raw)

    # Normalize whitespace.
    raw = re.sub(r"\s+", " ", raw).strip()

    if not raw:
        return ""

    # Remove trailing natural-language stop words.
    words = raw.split()

    while words and words[-1].lower() in CITY_STOP_WORDS:
        words.pop()

    raw = " ".join(words)

    return raw.title()


def looks_like_real_city(city: str) -> bool:
    """
    Basic sanity check only.

    IMPORTANT:
    This does NOT verify that the city actually exists.
    The live weather/AQI services perform the real validation.
    """

    if not city:
        return False

    c = city.strip().lower()

    if len(c) < 3:
        return False

    if len(c.split()) > 4:
        return False

    if c in BAD_CITY_WORDS:
        return False

    if all(word in BAD_CITY_WORDS for word in c.split()):
        return False

    return True


def extract_city(message: str) -> Optional[str]:
    """
    Extract a likely city from the user's message.

    This is intentionally conservative.
    Actual city validation is performed by the live services.
    """

    text = message.strip()

    for pattern in CITY_PATTERNS:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if not match:
            continue

        raw_city = match.group(1)

        city = clean_city_name(raw_city)

        if looks_like_real_city(city):
            return city

    return None


# ============================================================
# GENERAL HELPERS
# ============================================================

def contains_any(text: str, keywords: list) -> bool:
    """
    Case-insensitive keyword detection.
    """

    text_lower = text.lower()

    return any(
        keyword.lower() in text_lower
        for keyword in keywords
    )


def detect_time_query(msg_low: str) -> Optional[str]:
    """
    Detect requested time scope.

    Returns:
        now
        tomorrow
        next_hours
        tonight
        later
        None
    """

    if any(
        phrase in msg_low
        for phrase in [
            "next 2 hours",
            "next 3 hours",
            "next 6 hours",
            "next 12 hours",
            "next 24 hours",
            "next hours",
            "next hour",
            "next few hours",
            "next couple of hours",
            "coming hours",
        ]
    ):
        return "next_hours"

    if "tomorrow" in msg_low:
        return "tomorrow"

    if "tonight" in msg_low:
        return "tonight"

    if any(
        phrase in msg_low
        for phrase in [
            "later",
            "this evening",
            "this afternoon",
            "this morning",
        ]
    ):
        return "later"

    if any(
        phrase in msg_low
        for phrase in [
            "now",
            "right now",
            "currently",
            "live",
            "today",
            "current",
            "at the moment",
        ]
    ):
        return "now"

    return None


def is_weather_request(msg_low: str) -> bool:
    return contains_any(
        msg_low,
        WEATHER_KEYWORDS
    )


def is_aqi_request(msg_low: str) -> bool:
    return contains_any(
        msg_low,
        AQI_KEYWORDS
    )


def is_health_request(msg_low: str) -> bool:
    return contains_any(
        msg_low,
        HEALTH_KEYWORDS
    )


def is_environment_request(msg_low: str) -> bool:
    return contains_any(
        msg_low,
        ENVIRONMENT_KEYWORDS
    )


def is_decision_request(msg_low: str) -> bool:
    return contains_any(
        msg_low,
        DECISION_WORDS
    )



def is_explicit_live_environment_request(msg_low: str) -> bool:
    """
    Detect an explicit request for current/live AQI or pollution data.

    This is deliberately stricter than the general AQI keyword bank so
    health/knowledge questions such as "health tips for pollution" do not
    accidentally become CITY_REQUIRED.
    """
    return contains_any(
        msg_low,
        [
            "aqi",
            "air quality",
            "current pollution",
            "pollution level",
            "pollution levels",
            "current air pollution",
            "live pollution",
            "current air quality",
            "live air quality",
            "current aqi",
            "live aqi",
            "aqi now",
            "air quality now",
            "pollution now",
        ],
    )


def is_future_weather_request(
    msg_low: str,
    time_query: Optional[str]
) -> bool:
    """
    Detect future weather requests.

    This handles natural-language questions such as:
    - will it rain tomorrow
    - is it going to rain tomorrow
    - chance of rain tomorrow
    - weather tomorrow
    """

    if time_query in {
        "tomorrow",
        "tonight",
        "later",
        "next_hours",
    }:
        return True

    return any(
        phrase in msg_low
        for phrase in (
            "will it rain",
            "is it going to rain",
            "chance of rain",
            "rain probability",
            "weather forecast",
        )
    )


# ============================================================
# KNOWLEDGE PATTERNS
# ============================================================

PURE_KNOWLEDGE_PATTERNS = [
    "what is aqi",
    "what does aqi mean",
    "aqi meaning",
    "define aqi",
    "explain aqi",

    "what is pm",
    "what is pm2.5",
    "what is pm25",
    "what is pm10",
    "what is no2",
    "what is nitrogen dioxide",
    "what is ozone",
    "what is o3",
    "what is so2",
    "what is co",

    "how pollution affects",
    "effects of pollution",
    "health effects of pollution",
    "why air pollution",
    "why is air pollution dangerous",

    "what causes smog",
    "what causes pollution",
    "how to reduce pollution",

    "what is climate change",
    "global warming",
    "greenhouse gas",
    "what is environment",
    "what is ecosystem",
    "biodiversity",

    "home remedy",
    "home remedies",
    "natural remedy",
    "breathing exercise",
    "lung health",
    "how to protect",
    "how to prevent pollution",
]


# ============================================================
# MAIN ROUTER
# ============================================================

def route_intent(message: str) -> Dict[str, Any]:
    """
    Main deterministic VAYORA intent router.

    Priority:

    1. Small talk
    2. Pure knowledge
    3. Location-aware activity/decision
    4. Weather
    5. AQI
    6. Health
    7. Environment knowledge
    8. Missing-city handling
    9. General fallback
    """

    msg = message.strip()

    if not msg:
        return {
            "intent": "GENERAL_CHAT",
            "city": None,
            "time_query": None,
            "confidence": 1.0,
        }

    msg_low = msg.lower()

    # --------------------------------------------------------
    # CITY
    # --------------------------------------------------------

    city = extract_city(msg)

    # --------------------------------------------------------
    # TIME
    # --------------------------------------------------------

    time_query = detect_time_query(msg_low)

    # --------------------------------------------------------
    # FLAGS
    # --------------------------------------------------------

    is_aqi = is_aqi_request(msg_low)
    is_weather = is_weather_request(msg_low)
    is_health = is_health_request(msg_low)
    is_environment = is_environment_request(msg_low)

    is_realtime = contains_any(
        msg_low,
        REALTIME_WORDS
    )

    is_forecast = contains_any(
        msg_low,
        FORECAST_WORDS
    )

    is_decision = is_decision_request(
        msg_low
    )


    # Strict signal for genuine live/current environmental requests.
    is_explicit_live_environment = is_explicit_live_environment_request(
        msg_low
    )

    # --------------------------------------------------------
    # 1. SMALL TALK
    # --------------------------------------------------------

    if (
        contains_any(
            msg_low,
            SMALL_TALK_WORDS
        )
        and len(msg_low.split()) <= 7
    ):
        return {
            "intent": "GENERAL_CHAT",
            "city": None,
            "time_query": None,
            "confidence": 0.97,
        }

    # --------------------------------------------------------
    # 2. HEALTH ADVICE (EARLY PRIORITY)
    #
    # Health/remedy questions must be separated before generic
    # decision words ("should I", "can I") and before generic
    # pollution/AQI knowledge keywords.
    #
    # This fixes:
    #   "what should I do for cough?"
    #   "health tips for pollution"
    #   "home remedy for sore throat"
    #
    # Do not take this path when the user explicitly asks for
    # live/current AQI or pollution data.
    # --------------------------------------------------------

    if is_health and not is_explicit_live_environment:
        return {
            "intent": "HEALTH_ADVICE",
            "city": city,
            "time_query": time_query,
            "confidence": 0.94,
        }

    # --------------------------------------------------------
    # 3. PURE KNOWLEDGE
    # --------------------------------------------------------

    if any(
        pattern in msg_low
        for pattern in PURE_KNOWLEDGE_PATTERNS
    ):
        return {
            "intent": "ENVIRONMENT_KNOWLEDGE",
            "city": None,
            "time_query": None,
            "confidence": 0.96,
        }

    # --------------------------------------------------------
    # 4. OUTDOOR / ACTIVITY DECISION
    #
    # Examples:
    # "Can I run outside in Pune?"
    # "Can I run outside in Pune tomorrow?"
    # "Is it safe to walk in Pune?"
    #
    # These need live environmental data.
    # --------------------------------------------------------

    if is_decision:

        if city:

            return {
                "intent": "OUTDOOR_DECISION",
                "city": city,
                "time_query": time_query or "now",
                "confidence": 0.94,
            }

        return {
            "intent": "CITY_REQUIRED",
            "city": None,
            "time_query": time_query,
            "confidence": 0.88,
        }

    # --------------------------------------------------------
    # 5. WEATHER
    #
    # IMPORTANT:
    # Weather is checked BEFORE AQI.
    #
    # This prevents:
    # "weather in Pune"
    # from becoming CITY_AQI_FORECAST.
    #
    # It also handles:
    # "will it rain tomorrow in Pune?"
    # --------------------------------------------------------

    if is_weather:

        if city:

            # Future weather request
            if (
                is_forecast
                or is_future_weather_request(
                    msg_low,
                    time_query
                )
            ):
                return {
                    "intent": "WEATHER_FORECAST",
                    "city": city,
                    "time_query": time_query or "tomorrow",
                    "confidence": 0.95,
                }

            # Current weather request
            return {
                "intent": "WEATHER_QUERY",
                "city": city,
                "time_query": time_query or "now",
                "confidence": 0.96,
            }

        # Weather requested but no city.
        return {
            "intent": "CITY_REQUIRED",
            "city": None,
            "time_query": time_query,
            "confidence": 0.90,
        }

    # --------------------------------------------------------
    # 6. AQI / AIR QUALITY
    # --------------------------------------------------------

    if is_aqi:

        if city:

            # Future AQI request
            if (
                is_forecast
                or time_query in {
                    "tomorrow",
                    "tonight",
                    "later",
                    "next_hours",
                }
            ):
                return {
                    "intent": "CITY_AQI_FORECAST",
                    "city": city,
                    "time_query": time_query or "tomorrow",
                    "confidence": 0.95,
                }

            # Current AQI
            return {
                "intent": "CITY_AQI_NOW",
                "city": city,
                "time_query": time_query or "now",
                "confidence": 0.96,
            }

        # AQI requested without location.
        return {
            "intent": "CITY_REQUIRED",
            "city": None,
            "time_query": time_query,
            "confidence": 0.90,
        }

    # --------------------------------------------------------
    # 7. HEALTH ADVICE
    #
    # Health/remedy questions use the RAG knowledge path.
    # This is intentionally checked separately so:
    #   "what should I do for cough?"
    #   "health tips for pollution"
    #   "home remedy for sore throat"
    # do NOT become CITY_REQUIRED.
    #
    # Genuine live AQI questions such as:
    #   "current AQI in Pune"
    #   "air quality now in Pune"
    # are still handled by the AQI section above.
    # --------------------------------------------------------

    if is_health and not is_explicit_live_environment:

        return {
            "intent": "HEALTH_ADVICE",
            "city": city,
            "time_query": time_query,
            "confidence": 0.93,
        }

    # --------------------------------------------------------
    # 8. ENVIRONMENT KNOWLEDGE
    # --------------------------------------------------------

    if is_environment:

        return {
            "intent": "ENVIRONMENT_KNOWLEDGE",
            "city": city,
            "time_query": time_query,
            "confidence": 0.88,
        }

    # --------------------------------------------------------
    # 9. GENERIC LIVE REQUEST
    #
    # Example:
    # "How is pollution in Pune?"
    #
    # Normally caught by AQI keywords, but kept as a safe
    # fallback.
    # --------------------------------------------------------

    if city and is_realtime:

        if is_weather:

            return {
                "intent": "WEATHER_QUERY",
                "city": city,
                "time_query": "now",
                "confidence": 0.90,
            }

        if is_aqi:

            return {
                "intent": "CITY_AQI_NOW",
                "city": city,
                "time_query": "now",
                "confidence": 0.90,
            }

    # --------------------------------------------------------
    # 10. GENERIC KNOWLEDGE FALLBACK
    # --------------------------------------------------------

    if is_health:
        return {
            "intent": "HEALTH_ADVICE",
            "city": city,
            "time_query": time_query,
            "confidence": 0.86,
        }

    if (
        is_aqi
        or is_environment
    ):
        return {
            "intent": "ENVIRONMENT_KNOWLEDGE",
            "city": None,
            "time_query": None,
            "confidence": 0.78,
        }

    # --------------------------------------------------------
    # 11. FINAL GENERAL CHAT FALLBACK
    # --------------------------------------------------------

    return {
        "intent": "GENERAL_CHAT",
        "city": city,
        "time_query": time_query,
        "confidence": 0.70,
    }

# ============================================================
# OPTIONAL ROUTER REGRESSION TESTS
# ============================================================
def _router_regression_tests() -> None:
    """
    Manual smoke tests. Not executed automatically.
    """
    cases = [
        ("what should I do for cough?", "HEALTH_ADVICE"),
        ("health tips for pollution", "HEALTH_ADVICE"),
        ("home remedy for sore throat", "HEALTH_ADVICE"),
        ("what is climate change?", "ENVIRONMENT_KNOWLEDGE"),
        ("what is PM2.5?", "ENVIRONMENT_KNOWLEDGE"),
        ("AQI in Pune", "CITY_AQI_NOW"),
        ("weather in Pune", "WEATHER_QUERY"),
        ("rain in Pune", "WEATHER_QUERY"),
        ("weather tomorrow in Pune", "WEATHER_FORECAST"),
        ("will it rain tomorrow in Pune?", "WEATHER_FORECAST"),
        ("Can I run outside in Pune tomorrow?", "OUTDOOR_DECISION"),
    ]

    for query, expected in cases:
        result = route_intent(query)
        actual = result.get("intent")
        assert actual == expected, (
            f"Router regression failed: {query!r} -> "
            f"{actual!r}, expected {expected!r}"
        )

    print("VAYORA router regression tests passed.")