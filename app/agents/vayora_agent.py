import os
from typing import Literal, Optional
from dotenv import load_dotenv
from google import genai

load_dotenv()

# ------------------------
# KEEP V1 SESSION MEMORY
# ------------------------
SESSION_MEMORY = {}

# ------------------------
# KEEP V1 MODE STYLE (IMPORTANT)
# ------------------------
MODE_INSTRUCTIONS = {
    "balanced": """
You are VAYORA, a calm, modern Air Quality & Health assistant.

- Start directly. No introduction.
- Show AQI + category first if available.
- 3–6 bullets max.
- No long paragraphs.
""",

    "deep": """
You are VAYORA, an expert-level Air Quality Intelligence system.

- Structured explanation allowed.
- Explain cause → effect → advice.
- Keep readable.
""",

    "emergency": """
You are VAYORA, an emergency health AI.

- Short, urgent, command-based.
"""
}

LANGUAGE_INSTRUCTIONS = {
    "en": "Respond in clear English.",
    "hi": "Respond in Hindi.",
    "hinglish": "Respond in Hinglish.",
    "mr": "Respond in Marathi."
}


# ------------------------
# FINAL MERGED AGENT
# ------------------------

def run_vayora_agent(
    intent: str,
    user_query: str,
    city: Optional[str] = None,
    aqi: Optional[int] = None,
    health_assessment: Optional[dict] = None,
    weather_insights: Optional[list] = None,
    retrieved_knowledge: Optional[str] = None,
    forecast: Optional[dict] = None,
    mode: Literal["balanced", "deep", "emergency"] = "balanced",
    language: Literal["en", "hi", "hinglish"] = "en"
) -> str:

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return "Configuration error: GOOGLE_API_KEY missing."

    client = genai.Client(api_key=api_key)

    mode_instruction = MODE_INSTRUCTIONS.get(mode)
    language_instruction = LANGUAGE_INSTRUCTIONS.get(language)

    memory_key = city if city else "CHAT_MODE"
    previous_context = SESSION_MEMORY.get(memory_key, "")

    # ==========================================================
    # 🟢 1. KNOWLEDGE / CHAT MODE (FROM V1, IMPROVED BY V2)
    # ==========================================================
    if intent in ["ENVIRONMENT_KNOWLEDGE", "GENERAL_CHAT", "HEALTH_ADVICE"]:

        prompt = f"""
You are VAYORA — an AI assistant for AQI, pollution, weather, and health.

{mode_instruction}
{language_instruction}

Conversation memory:
{previous_context}

User question:
{user_query}

Knowledge:
{retrieved_knowledge}

TASK:
- Answer directly.
- Do NOT ask for city unless needed.
- Include practical advice if relevant.
"""

        model = "gemini-3.1-flash-lite"

    # ==========================================================
    # 🔴 2. CITY REQUIRED (FROM V2)
    # ==========================================================
    elif intent == "CITY_REQUIRED":
        return "Please provide a city name to check AQI."

    # ==========================================================
    # 🔵 3. AQI ADVISORY MODE (V1 + V3 MERGE)
    # ==========================================================
    else:

        forecast_text = ""
        if forecast:
            forecast_text = f"Tomorrow: {forecast}"

        weather_text = "\n".join(weather_insights) if weather_insights else ""

        prompt = f"""
You are VAYORA — an Air Quality Intelligence Agent.

{mode_instruction}
{language_instruction}

Conversation memory:
{previous_context}

City: {city}
AQI: {aqi}
Category: {health_assessment.get('category', '')}

Weather:
{weather_text}

Forecast:
{forecast_text}

Knowledge:
{retrieved_knowledge}

TASK:
- Start with: "{city}'s AQI is {aqi} — {health_assessment.get('category', '')}"
- Then risk summary (1 line)
- Then 3–6 action bullets
- Include mask, outdoor advice
- Include forecast if exists
"""

        model = "gemini-3.1-flash-lite"

    # ==========================================================
    # CALL GEMINI
    # ==========================================================
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt
        )

        SESSION_MEMORY[memory_key] = response.text[:800]

        return response.text.strip()

    except Exception as e:
        return f"VAYORA error: {str(e)}"