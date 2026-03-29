from fastapi import FastAPI, Query
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os

# ── Imports ─────────────────────────────────────────
from app.agents.intent_router import route_intent
from app.agents.vayora_agent import run_vayora_agent

from app.services.aqi_service import get_city_aqi
from app.services.health_logic import interpret_aqi
from app.services.weather_logic import analyze_weather_impact
from app.services.aqi_forecast import get_aqi_forecast
from app.services.weather_service import get_weather
from app.rag.ingest import build_vector_store, query_knowledge


# ---------------------------------------------------
# ✅ REQUEST MODEL
# ---------------------------------------------------
class ChatRequest(BaseModel):
    message: str
    mode: str = "balanced"
    language: str = "en"   # 🔥 ADDED


# ---------------------------------------------------
# ✅ FASTAPI APP
# ---------------------------------------------------
app = FastAPI(
    title="VAYORA – Air Quality Intelligence API",
    version="FINAL"
)

# 🔥 STATIC FILES (UI FIX)
app.mount("/static", StaticFiles(directory="frontend"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------
# ✅ LOAD RAG ON STARTUP
# ---------------------------------------------------
print("🔄 Loading VAYORA knowledge base...")
vector_db = build_vector_store("app/data/health_guidelines.txt")
print("✅ Knowledge base ready.")


# ---------------------------------------------------
# ✅ ROOT (SERVE UI)
# ---------------------------------------------------
@app.get("/")
def root():
    return FileResponse("frontend/index.html")


# ---------------------------------------------------
# ✅ HELPER FUNCTION
# ---------------------------------------------------
def _generate_advisory(city: str, mode: str, user_query: str, language: str):

    aqi_data = get_city_aqi(city)

    if "aqi" not in aqi_data:
        return {"reply": f"Sorry, AQI data for {city} is unavailable."}

    health_info = interpret_aqi(aqi_data["aqi"])
    weather_insights = analyze_weather_impact(aqi_data.get("pollutants", {}))
    forecast = get_aqi_forecast(city)

    retrieved_knowledge = query_knowledge(
        vector_db,
        query=f"AQI {aqi_data['aqi']} health impact and precautions"
    )

    reply = run_vayora_agent(
        intent="CITY_AQI_NOW",
        city=city,
        aqi=aqi_data["aqi"],
        health_assessment=health_info,
        weather_insights=weather_insights,
        retrieved_knowledge=retrieved_knowledge,
        forecast=forecast,
        mode=mode,
        language=language,
        user_query=user_query
    )

    return {
        "reply": reply,
        "aqi": aqi_data["aqi"],
        "category": health_info.get("category"),
        "city": city
    }


# ---------------------------------------------------
# ✅ ADVISORY ENDPOINT
# ---------------------------------------------------
@app.get("/vayora/advisory")
def get_advisory(city: str = Query(...), mode: str = Query("balanced")):
    return _generate_advisory(city, mode, f"AQI advisory for {city}", "en")


# ---------------------------------------------------
# ✅ MAIN CHAT ENDPOINT
# ---------------------------------------------------
@app.post("/vayora/chat")
def chat_vayora(payload: ChatRequest):

    user_message = payload.message.strip()
    mode = payload.mode
    language = payload.language

    intent_data = route_intent(user_message)
    intent = intent_data.get("intent", "")
    city = intent_data.get("city")

    # 🔥 SESSION MEMORY FIX
    if not city and intent in ["CITY_AQI_NOW", "CITY_AQI_FORECAST", "WEATHER_QUERY"]:
        if hasattr(app.state, "last_city"):
            city = app.state.last_city

    # 🔥 GREETING FIX
    if intent == "GENERAL_CHAT" and not city:
        return {
            "reply": "Hello! I'm VAYORA 🌍\n\nI can help with:\n• AQI\n• Weather\n• Health tips\n\nAsk me anything!"
        }

    # SAVE CITY
    if city:
        app.state.last_city = city

    # ---------------------------------------------------
    # CITY REQUIRED
    # ---------------------------------------------------
    if intent == "CITY_REQUIRED":
        return {
            "reply": "Please provide a city name (e.g., AQI in Delhi)"
        }

    # ---------------------------------------------------
    # AQI
    # ---------------------------------------------------
    if intent in ["CITY_AQI_NOW", "CITY_AQI_FORECAST"] and city:
        return _generate_advisory(city, mode, user_message, language)

    # ---------------------------------------------------
    # WEATHER (FIXED)
    # ---------------------------------------------------
    if intent == "WEATHER_QUERY" and city:

        weather = get_weather(city)

        if "error" in weather:
            return {"reply": f"Weather data unavailable for {city}"}

        reply = f"""
Weather in {city}:

🌡 Temperature: {weather['temperature']}°C
💧 Humidity: {weather['humidity']}%
🌬 Wind Speed: {weather['wind_speed']} m/s
🌤 Condition: {weather['description']}
"""

        return {"reply": reply}

    # ---------------------------------------------------
    # KNOWLEDGE / CHAT
    # ---------------------------------------------------
    retrieved_knowledge = query_knowledge(vector_db, query=user_message)

    reply = run_vayora_agent(
        intent="GENERAL_CHAT",
        city=None,
        aqi=None,
        health_assessment=None,
        weather_insights=[],
        retrieved_knowledge=retrieved_knowledge,
        forecast=None,
        mode=mode,
        language=language,
        user_query=user_message
    )

    return {"reply": reply}