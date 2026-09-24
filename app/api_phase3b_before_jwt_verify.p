"""
VAYORA API
================================================================

Main responsibilities:

    User request
        ↓
    Intent Router
        ↓
    Session Memory
        ↓
    Live Data Services
        ↓
    Deterministic AQI Reasoning
        ↓
    Response Decision
        ↓
    RAG
        ↓
    Gemini Agent
        ↓
    Structured API Response

Important design rules:

    • WAQI remains the source of live AQI data.
    • OpenWeather remains the source of live weather data.
    • RAG remains the source of stored health/environment knowledge.
    • Gemini interprets the verified information.
    • Gemini does NOT create live environmental measurements.
    • Session memory is per-session, not global.
    • Live data and AI-generated text remain separate.
"""

from typing import Optional, Dict, Any
from uuid import uuid4

from fastapi import FastAPI, Query
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi import HTTPException

# ============================================================
# DATABASE / AUTHENTICATION
# ============================================================

from sqlalchemy import select

from app.database import SessionLocal
from app.models import User

from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
)
# ============================================================
# VAYORA AGENT COMPONENTS
# ============================================================

from app.agents.intent_router import route_intent
from app.agents.vayora_agent import run_vayora_agent
from app.agents.reasoning import assess_risk
from app.agents.decision import decide_response_style

from app.agents.session_memory import (
    get_session_city,
    get_last_aqi,
    get_context,
    get_history,
    update_session,
)


# ============================================================
# LIVE SERVICES
# ============================================================

from app.services.aqi_service import get_city_aqi
from app.services.health_logic import interpret_aqi
from app.services.weather_logic import analyze_weather_impact
from app.services.aqi_forecast import get_aqi_forecast
from app.services.weather_service import get_weather

# Optional future-weather service.
# It is imported lazily in the forecast handler so VAYORA can still
# start safely if the service file is not installed yet.


# ============================================================
# RAG
# ============================================================

from app.rag.ingest import (
    build_vector_store,
    query_knowledge,
)


# ============================================================
# REQUEST MODEL
# ============================================================

class ChatRequest(BaseModel):
    """
    Request sent by the VAYORA frontend.

    session_id:
        Identifies one conversation.

        The frontend will normally provide one using:
            crypto.randomUUID()

        A fallback is generated here so the API remains
        compatible before the frontend is updated.
    """

    message: str
    mode: str = "balanced"
    language: str = "en"
    session_id: Optional[str] = None
# ============================================================
# AUTHENTICATION REQUEST MODELS
# ============================================================

class RegisterRequest(BaseModel):

    name: str
    email: str
    password: str


class LoginRequest(BaseModel):

    email: str
    password: str

# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="VAYORA – Environmental Intelligence API",
    version="2.0",
)


# ============================================================
# STATIC FRONTEND
# ============================================================

app.mount(
    "/static",
    StaticFiles(directory="frontend"),
    name="static",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# LOAD RAG KNOWLEDGE BASE
# ============================================================

print("🔄 Loading VAYORA knowledge base...")

vector_db = build_vector_store(
    "app/data/health_guidelines.txt"
)

print("✅ Knowledge base ready.")


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return FileResponse(
        "frontend/index.html"
    )
# ============================================================
# AUTHENTICATION — REGISTER
# ============================================================

@app.post("/auth/register")
def register_user(
    payload: RegisterRequest,
):

    db = SessionLocal()

    try:

        existing_user = db.execute(
            select(User).where(
                User.email == payload.email.lower().strip()
            )
        ).scalar_one_or_none()

        if existing_user:

            raise HTTPException(
                status_code=409,
                detail="An account with this email already exists.",
            )

        user = User(
            name=payload.name.strip(),
            email=payload.email.lower().strip(),
            password_hash=hash_password(
                payload.password
            ),
        )

        db.add(user)

        db.commit()

        db.refresh(user)

        return {
            "message": "Account created successfully.",
            "user": {
                "id": str(user.id),
                "name": user.name,
                "email": user.email,
            },
        }

    finally:

        db.close()


# ============================================================
# AUTHENTICATION — LOGIN
# ============================================================

@app.post("/auth/login")
def login_user(
    payload: LoginRequest,
):

    db = SessionLocal()

    try:

        user = db.execute(
            select(User).where(
                User.email == payload.email.lower().strip()
            )
        ).scalar_one_or_none()

        if not user:

            raise HTTPException(
                status_code=401,
                detail="Invalid email or password.",
            )

        if not verify_password(
            payload.password,
            user.password_hash,
        ):

            raise HTTPException(
                status_code=401,
                detail="Invalid email or password.",
            )

        access_token = create_access_token(
            user.id
        )

        return {
            "message": "Login successful.",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "name": user.name,
                "email": user.email,
            },
        }

    finally:

        db.close()

# ============================================================
# HELPER — NORMALIZE SESSION
# ============================================================

def _get_session_id(
    requested_session_id: Optional[str],
) -> str:
    """
    Return a valid session ID.

    The frontend will normally provide one.

    If it does not, generate one so the API does not fall back
    to global shared application state.
    """

    if requested_session_id:
        return requested_session_id.strip()

    return str(uuid4())


# ============================================================
# HELPER — NORMALIZE MODE
# ============================================================

def _normalize_mode(mode: str) -> str:

    allowed = {
        "balanced",
        "deep",
        "emergency",
        "concise",
    }

    mode = (mode or "balanced").lower().strip()

    if mode not in allowed:
        return "balanced"

    return mode


# ============================================================
# HELPER — NORMALIZE LANGUAGE
# ============================================================

def _normalize_language(language: str) -> str:

    allowed = {
        "en",
        "hi",
        "hinglish",
        "mr",
    }

    language = (language or "en").lower().strip()

    if language not in allowed:
        return "en"

    return language


# ============================================================
# HELPER — SAFE NUMBER
# ============================================================

def _safe_number(value):
    """
    Keep numeric API values numeric.

    No environmental value is generated here.
    """

    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return value


# ============================================================
# HELPER — BUILD WEATHER LIVE DATA
# ============================================================

def _build_weather_live_data(
    weather: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Convert the current OpenWeather response into a clean
    structured block for the frontend.

    IMPORTANT:
        These values are passed through from OpenWeather.

        No values are estimated by VAYORA.
    """

    return {
        "temperature": weather.get("temperature"),
        "feels_like": weather.get("feels_like"),

        "humidity": weather.get("humidity"),

        "wind_speed": weather.get("wind_speed"),
        "wind_direction": weather.get("wind_direction"),
        "wind_gust": weather.get("wind_gust"),

        "pressure": weather.get("pressure"),

        "visibility": weather.get("visibility"),

        "cloudiness": weather.get("cloudiness"),

        "rain_1h": weather.get("rain_1h"),
        "snow_1h": weather.get("snow_1h"),

        "description": weather.get("description"),
        "weather_main": weather.get("weather_main"),
        "weather_icon": weather.get("weather_icon"),

        "latitude": weather.get("latitude"),
        "longitude": weather.get("longitude"),

        "city": weather.get("city"),
        "country": weather.get("country"),

        "observation_timestamp": weather.get(
            "observation_timestamp"
        ),

        "observation_time": weather.get(
            "observation_time"
        ),

        "source": weather.get(
            "source",
            "OpenWeather"
        ),
    }


# ============================================================
# HELPER — BUILD WEATHER-SPECIFIC RESPONSE
# ============================================================

def _build_weather_reply(
    user_query: str,
    city: str,
    weather: Dict[str, Any],
) -> str:
    """
    Create a deterministic answer for the user's specific
    current-weather question.

    IMPORTANT:

        OpenWeather is the source of the measurements.

        VAYORA must not guess whether rain is occurring when
        the API has not supplied precipitation information.

        This function only selects and presents verified fields.
    """

    query = (user_query or "").lower().strip()

    temperature = weather.get("temperature")
    feels_like = weather.get("feels_like")
    humidity = weather.get("humidity")
    wind_speed = weather.get("wind_speed")
    wind_direction = weather.get("wind_direction")
    wind_gust = weather.get("wind_gust")
    cloudiness = weather.get("cloudiness")
    visibility = weather.get("visibility")
    description = weather.get("description")

    rain_1h = weather.get("rain_1h")
    snow_1h = weather.get("snow_1h")

    # ========================================================
    # RAIN / PRECIPITATION
    # ========================================================

    if any(
        word in query
        for word in (
            "rain",
            "raining",
            "rainfall",
            "precipitation",
            "drizzle",
            "showers",
        )
    ):

        if rain_1h is not None:

            reply = (
                f"🌧 Rain information for {city}:\n\n"
                f"Rain reported in the last hour: "
                f"{rain_1h} mm"
            )

        else:

            reply = (
                f"🌧 Rain information for {city}:\n\n"
                f"OpenWeather is not currently reporting a "
                f"precipitation amount for the last hour.\n\n"
                f"This does not by itself prove that it is not "
                f"raining right now."
            )

        if description:
            reply += (
                f"\n🌤 Current condition: {description}"
            )

        if cloudiness is not None:
            reply += (
                f"\n☁️ Cloudiness: {cloudiness}%"
            )

        return reply


    # ========================================================
    # TEMPERATURE / HEAT / COLD
    # ========================================================

    if any(
        word in query
        for word in (
            "temperature",
            "temp",
            "hot",
            "cold",
            "heat",
            "feels like",
        )
    ):

        reply = (
            f"🌡 Current temperature in {city}: "
            f"{temperature}°C"
        )

        if feels_like is not None:
            reply += (
                f"\n🤗 Feels like: {feels_like}°C"
            )

        if description:
            reply += (
                f"\n🌤 Condition: {description}"
            )

        return reply


    # ========================================================
    # HUMIDITY
    # ========================================================

    if any(
        word in query
        for word in (
            "humidity",
            "humid",
            "moisture",
        )
    ):

        reply = (
            f"💧 Current humidity in {city}: "
            f"{humidity}%"
        )

        if temperature is not None:
            reply += (
                f"\n🌡 Temperature: {temperature}°C"
            )

        if feels_like is not None:
            reply += (
                f"\n🤗 Feels like: {feels_like}°C"
            )

        return reply


    # ========================================================
    # WIND
    # ========================================================

    if any(
        word in query
        for word in (
            "wind",
            "windy",
            "breeze",
            "gust",
        )
    ):

        reply = (
            f"🌬 Current wind in {city}:\n\n"
            f"Wind speed: {wind_speed} m/s"
        )

        if wind_direction is not None:
            reply += (
                f"\n🧭 Direction: "
                f"{wind_direction}°"
            )

        if wind_gust is not None:
            reply += (
                f"\n💨 Gust: "
                f"{wind_gust} m/s"
            )

        return reply


    # ========================================================
    # VISIBILITY
    # ========================================================

    if any(
        word in query
        for word in (
            "visibility",
            "visible",
            "fog",
        )
    ):

        reply = (
            f"👁 Current visibility in {city}: "
            f"{visibility} m"
        )

        if description:
            reply += (
                f"\n🌤 Condition: {description}"
            )

        return reply


    # ========================================================
    # CLOUDS / CLOUDINESS
    # ========================================================

    if any(
        word in query
        for word in (
            "cloud",
            "clouds",
            "cloudy",
            "cloudiness",
        )
    ):

        reply = (
            f"☁️ Current cloudiness in {city}: "
            f"{cloudiness}%"
        )

        if description:
            reply += (
                f"\n🌤 Condition: {description}"
            )

        return reply


    # ========================================================
    # GENERAL CURRENT WEATHER
    # ========================================================

    reply = (
        f"Current weather in {city}:\n\n"
        f"🌡 Temperature: "
        f"{temperature}°C\n"
        f"🤗 Feels like: "
        f"{feels_like}°C\n"
        f"💧 Humidity: "
        f"{humidity}%\n"
        f"🌬 Wind Speed: "
        f"{wind_speed} m/s\n"
        f"🧭 Wind Direction: "
        f"{wind_direction}°\n"
        f"☁️ Cloudiness: "
        f"{cloudiness}%\n"
        f"👁 Visibility: "
        f"{visibility} m\n"
        f"🌤 Condition: "
        f"{description}"
    )

    if rain_1h is not None:
        reply += (
            f"\n🌧 Rain in last hour: "
            f"{rain_1h} mm"
        )

    if snow_1h is not None:
        reply += (
            f"\n❄️ Snow in last hour: "
            f"{snow_1h} mm"
        )

    return reply


# ============================================================
# HELPER — GET WEATHER FORECAST
# ============================================================

def _get_weather_forecast(city: str, days: int = 3) -> Dict[str, Any]:
    """
    Retrieve real future weather data from the dedicated
    weather-forecast service.

    This is intentionally separate from get_weather(), because
    current weather values must never be presented as future data.

    The forecast service is expected to expose get_forecast(city, days).
    If the service is unavailable, return a safe structured error
    instead of crashing the whole VAYORA API.
    """

    try:
        from app.services.weather_forecast import get_forecast
    except ImportError:
        return {
            "available": False,
            "source": "OpenWeather",
            "forecast": [],
            "warnings": [
                "Weather forecast service is not installed/configured."
            ],
        }

    try:
        result = get_forecast(city, days=days)

        if not isinstance(result, dict):
            return {
                "available": False,
                "source": "OpenWeather",
                "forecast": [],
                "warnings": [
                    "Weather forecast service returned invalid data."
                ],
            }

        return result

    except Exception as exc:
        return {
            "available": False,
            "source": "OpenWeather",
            "forecast": [],
            "warnings": [
                f"Weather forecast request failed: {exc}"
            ],
        }


def _build_weather_forecast_reply(
    city: str,
    forecast_data: Dict[str, Any],
    user_query: str,
) -> str:
    """
    Present real forecast entries without inventing rainfall,
    temperature, or other future values.

    The exact forecast payload remains available in live_data for
    the frontend and future agent/tool integration.
    """

    if not forecast_data.get("available"):
        warnings = forecast_data.get("warnings") or []
        reason = warnings[0] if warnings else "Forecast data is unavailable."
        return (
            f"Sorry, I couldn't retrieve the requested weather forecast "
            f"for {city}.\n\n"
            f"Source status: {reason}"
        )

    entries = forecast_data.get("forecast") or []
    query = (user_query or "").lower()

    if not entries:
        return f"No reliable future weather data is available for {city}."

    # Keep the answer compact while preserving the real hourly entries.
    # Weather-forecast services may return many hourly observations.
    selected = entries[:8]

    lines = [f"🌤 Weather forecast for {city}:\n"]

    wants_rain = any(
        word in query
        for word in ("rain", "raining", "rainfall", "precipitation", "showers", "drizzle")
    )
    wants_temperature = any(
        word in query
        for word in ("temperature", "temp", "hot", "heat", "cold", "feels like")
    )

    for item in selected:
        timestamp = item.get("timestamp")
        weather = item.get("weather") or {}
        temperature = item.get("temperature")
        feels_like = item.get("feels_like")
        humidity = item.get("humidity")
        wind_speed = item.get("wind_speed")
        rain = item.get("rain_3h")
        description = item.get("description")

        # Support both the normalized forecast schema and a direct
        # OpenWeather-style entry if the service returns one.
        if timestamp is None:
            timestamp = item.get("dt")

        if not isinstance(weather, dict):
            weather = {}

        if temperature is None:
            main = item.get("main") or {}
            temperature = main.get("temp")
            feels_like = feels_like if feels_like is not None else main.get("feels_like")
            humidity = humidity if humidity is not None else main.get("humidity")

        if description is None:
            description = weather.get("description")

        if wind_speed is None:
            wind = item.get("wind") or {}
            wind_speed = wind.get("speed")

        if rain is None:
            rain_obj = item.get("rain") or {}
            rain = rain_obj.get("3h")

        if timestamp is not None:
            try:
                from datetime import datetime, timezone
                dt_text = datetime.fromtimestamp(
                    float(timestamp), tz=timezone.utc
                ).strftime("%d %b %H:%M UTC")
            except (TypeError, ValueError, OSError):
                dt_text = str(timestamp)
        else:
            dt_text = "Forecast period"

        line = f"• {dt_text}"

        if wants_rain:
            if rain is not None:
                line += f" — 🌧 Rain: {rain} mm"
            elif description:
                line += f" — 🌤 {description}"
            else:
                line += " — precipitation amount not reported"

        elif wants_temperature:
            if temperature is not None:
                line += f" — 🌡 {temperature}°C"
            if feels_like is not None:
                line += f" (feels {feels_like}°C)"
            if description:
                line += f" — {description}"

        else:
            if temperature is not None:
                line += f" — 🌡 {temperature}°C"
            if description:
                line += f" — {description}"
            if rain is not None:
                line += f" — 🌧 {rain} mm"
            if humidity is not None:
                line += f" — 💧 {humidity}%"
            if wind_speed is not None:
                line += f" — 🌬 {wind_speed} m/s"

        lines.append(line)

    lines.append("\nSource: OpenWeather forecast data.")
    return "\n".join(lines)


# ============================================================
# HELPER — BUILD AQI LIVE DATA
# ============================================================

def _build_aqi_live_data(
    aqi_data: Dict[str, Any],
    health_info: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build a structured AQI block.

    IMPORTANT:

        WAQI's IAQI pollutant values are NOT automatically
        treated as µg/m³ concentrations.

        We therefore preserve the raw pollutant data exactly
        as returned by WAQI.

        This prevents Gemini from being encouraged to invent
        units that the API did not provide.
    """

    return {
        "aqi": aqi_data.get("aqi"),

        "category": health_info.get(
            "category"
        ),

        "risk_level": health_info.get(
            "risk_level"
        ),

        "color": health_info.get(
            "color"
        ),

        "pollutants": aqi_data.get(
            "pollutants",
            {}
        ),

        "station": aqi_data.get(
            "station"
        ),

        "observation_time": aqi_data.get(
            "time"
        ),

        "source": "WAQI",

        "from_cache": bool(
            aqi_data.get(
                "_from_cache",
                False
            )
        ),

        "data_status": aqi_data.get(
            "data_status",
            "live"
        ),
    }


# ============================================================
# HELPER — BUILD AQI ADVISORY
# ============================================================

def _generate_advisory(
    city: str,
    mode: str,
    user_query: str,
    language: str,
    session_id: str,
    intent: str = "CITY_AQI_NOW",
):

    # ========================================================
    # 1. GET LIVE AQI
    # ========================================================

    aqi_data = get_city_aqi(city)

    if not aqi_data or "aqi" not in aqi_data:

        error_message = (
            aqi_data.get(
                "error",
                f"AQI data for {city} is unavailable."
            )
            if isinstance(aqi_data, dict)
            else f"AQI data for {city} is unavailable."
        )

        return {
            "reply": (
                f"Sorry, {error_message}"
            ),

            "session_id": session_id,

            "live_data": {
                "aqi": None,
                "city": city,
                "source": "WAQI",
            },

            "data_status": "unavailable",
        }

    # ========================================================
    # 2. DETERMINISTIC HEALTH INTERPRETATION
    # ========================================================

    aqi_value = aqi_data.get("aqi")

    health_info = interpret_aqi(
        aqi_value
    )

    # ========================================================
    # 3. DETERMINISTIC RISK REASONING
    # ========================================================

    risk_decision = assess_risk(
        aqi_value
    )

    # ========================================================
    # 4. WEATHER IMPACT FROM AQI POLLUTANTS
    # ========================================================

    weather_insights = analyze_weather_impact(
        aqi_data.get(
            "pollutants",
            {}
        )
    )

    # ========================================================
    # 5. FORECAST
    # ========================================================

    forecast = get_aqi_forecast(
        city
    )

    forecast_available = bool(
        forecast
        and not (
            isinstance(forecast, dict)
            and forecast.get("error")
        )
    )

    # ========================================================
    # 6. BUILD RESPONSE DECISION STATE
    # ========================================================

    decision_state = {
        "session_id": session_id,
        "user_message": user_query,

        "intent": intent,

        "mode": mode,
        "language": language,

        "needs_live": True,

        "city": city,

        "aqi": aqi_value,

        "health_assessment": health_info,

        "risk_decision": risk_decision,

        "data_status": (
            "recent"
            if aqi_data.get(
                "_from_cache",
                False
            )
            else "live"
        ),
    }

    response_style = decide_response_style(
        decision_state
    )

    # ========================================================
    # 7. SESSION CONTEXT
    # ========================================================

    session_context = get_context(
        session_id
    )

    # ========================================================
    # 8. RAG QUERY
    # ========================================================

    rag_query = (
        f"AQI category {health_info.get('category', '')}; "
        f"risk {risk_decision.get('risk', '')}; "
        f"urgency {risk_decision.get('urgency', '')}; "
        f"health protection; precautions; outdoor activity"
    )

    retrieved_knowledge = query_knowledge(
        vector_db,
        query=rag_query,
    )

    # ========================================================
    # 9. KEEP VERIFIED FACTS CLEARLY SEPARATED
    # ========================================================

    verified_context = f"""
VERIFIED VAYORA DATA — DO NOT INVENT OR ALTER:

City:
{city}

Current WAQI AQI:
{aqi_value}

AQI Category:
{health_info.get('category', '')}

AQI Risk:
{risk_decision.get('risk', '')}

AQI Urgency:
{risk_decision.get('urgency', '')}

WAQI Station:
{aqi_data.get('station', '')}

WAQI Observation Time:
{aqi_data.get('time', '')}

WAQI Pollutant IAQI Data:
{aqi_data.get('pollutants', {})}

IMPORTANT:
The pollutant values above are raw WAQI IAQI values.
Do NOT invent µg/m³ or other concentration units unless
the source explicitly provides those units.

Deterministic Health Interpretation:
{health_info}

Deterministic Risk Decision:
{risk_decision}

Response Decision:
{response_style}

Session Context:
{session_context}

Retrieved Knowledge:
{retrieved_knowledge}
"""

    # ========================================================
    # 10. CALL GEMINI
    # ========================================================

    reply = run_vayora_agent(
        intent=intent,
        city=city,
        aqi=aqi_value,
        health_assessment=health_info,

        weather_insights=(
            weather_insights
            + [
                verified_context
            ]
        ),

        retrieved_knowledge=retrieved_knowledge,

        forecast=forecast,

        mode=mode,
        language=language,

        user_query=user_query,
    )

        # ========================================================
    # 11. STRUCTURED LIVE DATA
    # ========================================================

    # Attach current OpenWeather data to the same verified city
    # response so the map Weather control can use it directly.
    #
    # This is an OpenWeather service call only.
    # It does NOT call Gemini.

    weather_map_data = None

    try:
        weather_map_data = get_weather(city)

    except Exception as weather_error:

        print(
            f"VAYORA map weather warning for {city}: {weather_error}"
        )

        weather_map_data = None

    live_data = {
        "aqi": _build_aqi_live_data(
            aqi_data,
            health_info,
        ),

        "weather": (
            _build_weather_live_data(
                weather_map_data
            )
            if isinstance(
                weather_map_data,
                dict
            )
            and weather_map_data.get(
                "available",
                True
            )
            else None
        ),

        "forecast": (
            forecast
            if forecast_available
            else None
        ),

        "coordinates": {
            "latitude": None,
            "longitude": None,
        },
    }

    # ========================================================
    # 12. COORDINATES
    # ========================================================

    if isinstance(forecast, dict):

        latitude = forecast.get(
            "latitude"
        )

        longitude = forecast.get(
            "longitude"
        )

        if latitude is not None:
            live_data["coordinates"][
                "latitude"
            ] = latitude

        if longitude is not None:
            live_data["coordinates"][
                "longitude"
            ] = longitude
        # OpenWeather coordinates are a safe fallback
    # when the AQI forecast service did not attach coordinates.

    if (
        live_data["coordinates"]["latitude"] is None
        or
        live_data["coordinates"]["longitude"] is None
    ) and isinstance(
        weather_map_data,
        dict
    ):

        weather_latitude = weather_map_data.get(
            "latitude"
        )

        weather_longitude = weather_map_data.get(
            "longitude"
        )

        if weather_latitude is not None:

            live_data["coordinates"][
                "latitude"
            ] = weather_latitude

        if weather_longitude is not None:

            live_data["coordinates"][
                "longitude"
            ] = weather_longitude
    # ========================================================
    # 13. SESSION MEMORY UPDATE
    # ========================================================

    update_session(
        session_id=session_id,

        user_message=user_query,

        bot_reply=reply,

        city=city,

        aqi_data={
            "city": city,
            "aqi": aqi_value,
            "category": health_info.get(
                "category",
                ""
            ),
        },
    )

    # ========================================================
    # 14. FINAL RESPONSE
    # ========================================================

    return {
        "reply": reply,

        "session_id": session_id,

        "live_data": live_data,

        "data_status": (
            "recent"
            if aqi_data.get(
                "_from_cache",
                False
            )
            else "live"
        ),

        "city": city,

        "aqi": aqi_value,

        "category": health_info.get(
            "category"
        ),
    }


# ============================================================
# AQI ADVISORY ENDPOINT
# ============================================================

@app.get("/vayora/advisory")
def get_advisory(
    city: str = Query(...),
    mode: str = Query("balanced"),
):

    mode = _normalize_mode(
        mode
    )

    session_id = str(
        uuid4()
    )

    return _generate_advisory(
        city=city,

        mode=mode,

        user_query=(
            f"AQI advisory for {city}"
        ),

        language="en",

        session_id=session_id,

        intent="CITY_AQI_NOW",
    )
# ============================================================
# HELPER — CONTEXTUAL FOLLOW-UP ROUTING
# ============================================================

def _apply_contextual_followup(
    intent: str,
    user_message: str,
    session_id: str,
) -> str:
    """
    Preserve VAYORA's existing router while allowing short
    follow-up questions to use the previous conversation.

    IMPORTANT:
        This does NOT replace the intent router.

        It only helps when the current message is clearly
        contextual and the router could not determine the
        correct live-data path by itself.

    Examples:

        AQI in Mumbai
        -> What about tomorrow?
        -> CITY_AQI_FORECAST

        Weather in Pune
        -> What about tomorrow?
        -> WEATHER_FORECAST

        Temperature in Pune
        -> What about tomorrow?
        -> WEATHER_FORECAST

    Unrelated questions remain on their original path.
    """

    query = (user_message or "").lower().strip()

    if not query:
        return intent

    # --------------------------------------------------------
    # Only intervene for short/contextual follow-ups.
    # --------------------------------------------------------

    contextual_words = (
        "tomorrow",
        "today",
        "tonight",
        "later",
        "next",
        "morning",
        "afternoon",
        "evening",
        "what about",
        "how about",
        "and tomorrow",
        "then",
    )

    is_contextual = any(
        phrase in query
        for phrase in contextual_words
    )

    if not is_contextual:
        return intent

    # --------------------------------------------------------
    # Read recent session history.
    # --------------------------------------------------------

    try:
        history = get_history(session_id)
    except Exception:
        history = []

    if not history:
        return intent

    # --------------------------------------------------------
    # Find the most recent meaningful USER message.
    # --------------------------------------------------------

    previous_user_message = ""

    for turn in reversed(history):
        if (
            isinstance(turn, dict)
            and turn.get("role") == "user"
            and turn.get("content")
        ):
            previous_user_message = (
                str(turn["content"])
                .lower()
                .strip()
            )
            break

    if not previous_user_message:
        return intent

    # --------------------------------------------------------
    # Detect previous AQI topic.
    # --------------------------------------------------------

    previous_aqi = any(
        phrase in previous_user_message
        for phrase in (
            "aqi",
            "air quality",
            "pm2.5",
            "pm25",
            "pm10",
            "no2",
            "so2",
            "ozone",
        )
    )

    # --------------------------------------------------------
    # Detect previous weather topic.
    # --------------------------------------------------------

    previous_weather = any(
        phrase in previous_user_message
        for phrase in (
            "weather",
            "temperature",
            "temp",
            "rain",
            "raining",
            "rainfall",
            "precipitation",
            "drizzle",
            "showers",
            "humidity",
            "humid",
            "wind",
            "windy",
            "breeze",
            "gust",
            "cloud",
            "cloudy",
            "visibility",
            "fog",
            "hot",
            "cold",
            "heat",
            "feels like",
        )
    )

    # --------------------------------------------------------
    # Future/contextual question.
    # --------------------------------------------------------

    future_question = any(
        phrase in query
        for phrase in (
            "tomorrow",
            "next",
            "later",
            "tonight",
            "morning",
            "afternoon",
            "evening",
            "forecast",
            "will it",
            "expected",
            "what about",
            "how about",
        )
    )

    if not future_question:
        return intent

    # --------------------------------------------------------
    # AQI context → AQI forecast
    # --------------------------------------------------------

    if previous_aqi and not previous_weather:
        return "CITY_AQI_FORECAST"

    # --------------------------------------------------------
    # Weather context → Weather forecast
    # --------------------------------------------------------

    if previous_weather and not previous_aqi:
        return "WEATHER_FORECAST"

    # --------------------------------------------------------
    # If both were discussed, preserve the router's decision.
    # Do NOT guess.
    # --------------------------------------------------------

    return intent

# ============================================================
# MAIN CHAT ENDPOINT
# ============================================================

@app.post("/vayora/chat")
def chat_vayora(
    payload: ChatRequest
):

    # ========================================================
    # 1. NORMALIZE REQUEST
    # ========================================================

    user_message = (
        payload.message
        or ""
    ).strip()

    mode = _normalize_mode(
        payload.mode
    )

    language = _normalize_language(
        payload.language
    )

    session_id = _get_session_id(
        payload.session_id
    )

    # --------------------------------------------------------
    # Empty message
    # --------------------------------------------------------

    if not user_message:

        return {
            "reply": (
                "Ask me about AQI, weather, "
                "pollution, or environmental health."
            ),

            "session_id": session_id,

            "live_data": None,

            "data_status": "none",
        }

    # ========================================================
    # 2. ROUTE INTENT
    # ========================================================

    intent_data = route_intent(
        user_message
    )

    intent = intent_data.get(
        "intent",
        ""
    )

    city = intent_data.get(
        "city"
    )

    time_query = intent_data.get(
        "time_query"
    )
    # Apply contextual follow-up routing without replacing
    # the existing intent router.
    intent = _apply_contextual_followup(
        intent=intent,
        user_message=user_message,
        session_id=session_id,
    )
    # ========================================================
    # 3. DEFENSIVE WEATHER INTENT CHECK
    # ========================================================
    #
    # The router is the primary intent detector.
    #
    # This small compatibility check protects the API if a
    # weather-specific request is accidentally classified as
    # an AQI forecast because it contains words such as
    # "forecast" or "weather".
    #
    # Explicit AQI requests remain AQI requests.
    # ========================================================

    query_lower = user_message.lower()

    explicit_aqi_request = any(
        phrase in query_lower
        for phrase in (
            "aqi",
            "air quality",
            "pollution",
            "pm2.5",
            "pm25",
            "pm10",
            "no2",
            "so2",
            "ozone",
        )
    )

    weather_request_words = (
        "weather",
        "temperature",
        "temp",
        "humidity",
        "humid",
        "rain",
        "raining",
        "rainfall",
        "precipitation",
        "drizzle",
        "showers",
        "wind",
        "windy",
        "breeze",
        "gust",
        "cloud",
        "clouds",
        "cloudy",
        "visibility",
        "fog",
        "hot",
        "cold",
        "heat",
        "feels like",
    )

    has_weather_request = any(
        word in query_lower
        for word in weather_request_words
    )

    if (
        intent == "CITY_AQI_FORECAST"
        and has_weather_request
        and not explicit_aqi_request
    ):
        # If the user is asking for future weather, keep it as a
        # forecast request. Only current-weather questions become
        # WEATHER_QUERY.
        future_weather_words = (
            "tomorrow", "next", "later", "tonight", "morning",
            "evening", "forecast", "will it", "expected",
        )

        if any(word in query_lower for word in future_weather_words):
            intent = "WEATHER_FORECAST"
        else:
            intent = "WEATHER_QUERY"

    # ========================================================
    # 4. SESSION MEMORY — CITY FALLBACK
    # ========================================================
    #
    # IMPORTANT:
    #
    # We no longer use:
    #
    #     app.state.last_city
    #
    # because that would be shared by every user.
    #
    # Instead:
    #
    #     session_id → session_memory → last_city
    #
    # ========================================================

    if (
        not city
        and intent in {
            "CITY_AQI_NOW",
            "CITY_AQI_FORECAST",
            "WEATHER_QUERY",
            "WEATHER_FORECAST",
            "OUTDOOR_DECISION",
        }
    ):

        city = get_session_city(
            session_id
        )

    # ========================================================
    # 5. GENERAL CHAT
    # ========================================================

    if (
        intent == "GENERAL_CHAT"
        and not city
    ):

        reply = (
            "Hello! I'm VAYORA 🌍\n\n"
            "I can help with:\n"
            "• Live AQI\n"
            "• Current weather\n"
            "• Pollution and health guidance\n"
            "• Environmental questions\n"
            "• AQI forecasts\n\n"
            "Ask me anything!"
        )

        update_session(
            session_id=session_id,

            user_message=user_message,

            bot_reply=reply,

            city=None,

            aqi_data=None,
        )

        return {
            "reply": reply,

            "session_id": session_id,

            "live_data": None,

            "data_status": "none",
        }

    # ========================================================
    # 6. CITY REQUIRED
    # ========================================================

    if intent == "CITY_REQUIRED":

        reply = (
            "Please provide a city name "
            "(for example: AQI in Delhi "
            "or weather in Pune)."
        )

        update_session(
            session_id=session_id,

            user_message=user_message,

            bot_reply=reply,

            city=None,

            aqi_data=None,
        )

        return {
            "reply": reply,

            "session_id": session_id,

            "live_data": None,

            "data_status": "location_required",
        }

    # ========================================================
    # 7. AQI CURRENT / FORECAST
    # ========================================================

    if (
        intent in {
            "CITY_AQI_NOW",
            "CITY_AQI_FORECAST",
        }
        and city
    ):

        return _generate_advisory(
            city=city,

            mode=mode,

            user_query=user_message,

            language=language,

            session_id=session_id,

            intent=intent,
        )

    # ========================================================
    # 8. WEATHER FORECAST / OUTDOOR DECISION
    # ========================================================

    if (
        intent in {
            "WEATHER_FORECAST",
            "OUTDOOR_DECISION",
        }
        and city
    ):

        forecast_data = _get_weather_forecast(city, days=3)

        if not forecast_data.get("available"):
            warnings = forecast_data.get("warnings") or []
            reason = warnings[0] if warnings else "Forecast data is unavailable."

            reply = (
                f"Sorry, I couldn't retrieve the requested forecast for {city}.\n\n"
                f"Source status: {reason}"
            )

            update_session(
                session_id=session_id,
                user_message=user_message,
                bot_reply=reply,
                city=city,
                aqi_data=None,
            )

            return {
                "reply": reply,
                "session_id": session_id,
                "live_data": {
                    "weather": None,
                    "aqi": None,
                    "forecast": forecast_data,
                    "coordinates": forecast_data.get("coordinates"),
                },
                "data_status": "unavailable",
                "city": city,
                "intent": intent,
                "time_query": time_query,
            }

        # For OUTDOOR_DECISION we also fetch current AQI so the
        # final decision can consider both verified air quality and
        # verified future weather. No environmental value is guessed.
        aqi_data = get_city_aqi(city)
        health_info = {}
        risk_decision = {}

        if isinstance(aqi_data, dict) and "aqi" in aqi_data:
            health_info = interpret_aqi(aqi_data.get("aqi"))
            risk_decision = assess_risk(aqi_data.get("aqi"))

        session_context = get_context(session_id)

        rag_query = (
            f"weather forecast for {city}; outdoor activity; rain; heat; "
            f"AQI health protection; safe outdoor activity"
        )

        retrieved_knowledge = query_knowledge(
            vector_db,
            query=rag_query,
        )

        response_style = decide_response_style({
            "session_id": session_id,
            "user_message": user_message,
            "intent": intent,
            "mode": mode,
            "language": language,
            "needs_live": True,
            "city": city,
            "aqi": aqi_data.get("aqi") if isinstance(aqi_data, dict) else None,
            "health_assessment": health_info,
            "risk_decision": risk_decision,
            "data_status": "live",
        })

        verified_context = f"""
VERIFIED WEATHER FORECAST DATA — DO NOT INVENT OR ALTER:
City: {city}
Forecast source: {forecast_data.get('source', 'OpenWeather')}
Forecast data: {forecast_data.get('forecast', [])}
Coordinates: {forecast_data.get('coordinates')}

VERIFIED CURRENT AQI DATA IF AVAILABLE:
AQI: {aqi_data.get('aqi') if isinstance(aqi_data, dict) else None}
Health assessment: {health_info}
Risk decision: {risk_decision}

Response decision: {response_style}
Session context: {session_context}
Retrieved knowledge: {retrieved_knowledge}

RULES:
- Never invent future weather values.
- Never convert OpenWeather forecast data into a fake WAQI AQI.
- If a requested forecast field is absent, say it is not reported.
- For outdoor decisions, use verified AQI and forecast information only.
"""

        # Gemini can explain the verified forecast, but the raw data
        # remains in live_data and is not replaced by generated text.
        reply = run_vayora_agent(
            intent="CITY_AQI_NOW" if intent == "OUTDOOR_DECISION" else "GENERAL_CHAT",
            city=city,
            aqi=(aqi_data.get("aqi") if isinstance(aqi_data, dict) else None),
            health_assessment=health_info or None,
            weather_insights=[verified_context],
            retrieved_knowledge=retrieved_knowledge,
            forecast=forecast_data,
            mode=mode,
            language=language,
            user_query=user_message,
        )

        # If Gemini fails, retain a deterministic forecast answer rather
        # than losing access to the verified live data.
        if not reply or reply.startswith("VAYORA error:"):
            reply = _build_weather_forecast_reply(
                city=city,
                forecast_data=forecast_data,
                user_query=user_message,
            )

        update_session(
            session_id=session_id,
            user_message=user_message,
            bot_reply=reply,
            city=city,
            aqi_data=(
                {
                    "city": city,
                    "aqi": aqi_data.get("aqi"),
                    "category": health_info.get("category", ""),
                }
                if isinstance(aqi_data, dict) and "aqi" in aqi_data
                else None
            ),
        )

        return {
            "reply": reply,
            "session_id": session_id,
            "live_data": {
                "weather": None,
                "aqi": (
                    _build_aqi_live_data(aqi_data, health_info)
                    if isinstance(aqi_data, dict) and "aqi" in aqi_data
                    else None
                ),
                "forecast": forecast_data,
                "coordinates": forecast_data.get("coordinates"),
            },
            "data_status": "live",
            "city": city,
            "intent": intent,
            "time_query": time_query,
        }


    # ========================================================
    # 9. WEATHER
    # ========================================================

    if (
        intent == "WEATHER_QUERY"
        and city
    ):

        weather = get_weather(
            city
        )

        # ----------------------------------------------------
        # Weather unavailable
        # ----------------------------------------------------

        if (
            not weather
            or weather.get(
                "available"
            ) is False
            or weather.get(
                "error"
            )
        ):

            error = (
                weather.get(
                    "error",
                    f"Weather data for {city} is unavailable."
                )
                if isinstance(
                    weather,
                    dict
                )
                else f"Weather data for {city} is unavailable."
            )

            reply = (
                f"Sorry, I couldn't retrieve current "
                f"weather for {city}.\n\n"
                f"Source status: {error}"
            )

            update_session(
                session_id=session_id,

                user_message=user_message,

                bot_reply=reply,

                city=city,

                aqi_data=None,
            )

            return {
                "reply": reply,

                "session_id": session_id,

                "live_data": {
                    "weather": None,
                    "coordinates": None,
                },

                "data_status": "unavailable",

                "city": city,
            }

        # ----------------------------------------------------
        # Structured weather data
        # ----------------------------------------------------

        weather_live_data = (
            _build_weather_live_data(
                weather
            )
        )

        # ----------------------------------------------------
        # Forecast protection
        # ----------------------------------------------------
        #
        # IMPORTANT:
        #
        # Current weather endpoint is not a forecast endpoint.
        #
        # We therefore never present current values as
        # tomorrow's or future values.
        # ----------------------------------------------------

        if time_query in {
            "tomorrow",
            "next_hours",
            "forecast",
        }:

            reply = (
                f"I can access current weather for "
                f"{city}, but the current OpenWeather "
                f"integration does not yet provide the "
                f"requested forecast period.\n\n"
                f"Current conditions are:\n\n"
                f"🌡 Temperature: "
                f"{weather.get('temperature')}°C\n"
                f"🤗 Feels like: "
                f"{weather.get('feels_like')}°C\n"
                f"💧 Humidity: "
                f"{weather.get('humidity')}%\n"
                f"🌬 Wind: "
                f"{weather.get('wind_speed')} m/s\n"
                f"🌤 Condition: "
                f"{weather.get('description')}"
            )

        else:

            # ------------------------------------------------
            # Specific weather-question intelligence
            # ------------------------------------------------
            #
            # Instead of always dumping every field, VAYORA
            # now answers according to what the user actually
            # asked.
            #
            # Example:
            #
            # rain in Pune
            #     → rain-focused answer
            #
            # temperature in Pune
            #     → temperature-focused answer
            #
            # humidity in Pune
            #     → humidity-focused answer
            #
            # weather in Pune
            #     → complete current-weather answer
            # ------------------------------------------------

            reply = _build_weather_reply(
                user_query=user_message,
                city=city,
                weather=weather,
            )

        # ----------------------------------------------------
        # Save weather conversation
        # ----------------------------------------------------

        update_session(
            session_id=session_id,

            user_message=user_message,

            bot_reply=reply,

            city=city,

            aqi_data=None,
        )

        return {
            "reply": reply,

            "session_id": session_id,

            "live_data": {
                "weather": weather_live_data,

                "aqi": None,

                "forecast": None,

                "coordinates": {
                    "latitude": weather.get(
                        "latitude"
                    ),

                    "longitude": weather.get(
                        "longitude"
                    ),
                },
            },

            "data_status": "live",

            "city": city,

            "time_query": time_query,
        }

    # ========================================================
    # 10. KNOWLEDGE / GENERAL ENVIRONMENT / HEALTH
    # ========================================================

    session_context = get_context(
        session_id
    )

    retrieved_knowledge = query_knowledge(
        vector_db,
        query=user_message,
    )

    # --------------------------------------------------------
    # Deterministic state for decision layer
    # --------------------------------------------------------

    knowledge_state = {
        "session_id": session_id,

        "user_message": user_message,

        "intent": intent,

        "mode": mode,

        "language": language,

        "needs_live": False,

        "city": city,

        "data_status": "none",

        "session_context": session_context,
    }

    response_style = decide_response_style(
        knowledge_state
    )

    # --------------------------------------------------------
    # Give Gemini the retrieved knowledge.
    #
    # Session context is included explicitly so the current
    # agent can use it without requiring a breaking change to
    # run_vayora_agent().
    # --------------------------------------------------------

    combined_knowledge = f"""
VAYORA RESPONSE DECISION:
{response_style}

SESSION CONTEXT:
{session_context}

RETRIEVED KNOWLEDGE:
{retrieved_knowledge}
"""

    reply = run_vayora_agent(
        intent=(
            "HEALTH_ADVICE"
            if intent == "HEALTH_ADVICE"
            else "GENERAL_CHAT"
        ),

        city=city,

        aqi=None,

        health_assessment=None,

        weather_insights=[],

        retrieved_knowledge=combined_knowledge,

        forecast=None,

        mode=mode,

        language=language,

        user_query=user_message,
    )

    # ========================================================
    # SAVE SESSION
    # ========================================================

    update_session(
        session_id=session_id,

        user_message=user_message,

        bot_reply=reply,

        city=city,

        aqi_data=None,
    )

    # ========================================================
    # FINAL KNOWLEDGE RESPONSE
    # ========================================================

    return {
        "reply": reply,

        "session_id": session_id,

        "live_data": None,

        "data_status": "none",

        "city": city,

        "intent": intent,
    }