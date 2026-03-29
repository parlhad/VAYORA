"""
VAYORA — Terminal Test Runner (FINAL)
══════════════════════════════════════
Run this to test VAYORA without frontend.

Usage:
    python main.py
"""

from app.services.aqi_service import get_city_aqi
from app.services.health_logic import interpret_aqi
from app.services.weather_logic import analyze_weather_impact
from app.services.aqi_forecast import get_aqi_forecast
from app.rag.ingest import build_vector_store, query_knowledge
from app.agents.vayora_agent import run_vayora_agent


def run_vayora_terminal():
    print("\n" + "═" * 60)
    print("🌍 VAYORA — Air Quality Intelligence (Terminal Mode)")
    print("═" * 60)

    # Load RAG once
    print("🔄 Loading knowledge base...")
    vector_db = build_vector_store("app/data/health_guidelines.txt")
    print("✅ Knowledge base ready.\n")

    # Mode selection
    mode = input("Select mode (balanced/deep/emergency) [default=balanced]: ").strip() or "balanced"
    language = input("Select language (en/hi/hinglish) [default=en]: ").strip() or "en"

    while True:
        print("\n" + "-" * 50)
        city = input("Enter city (or type 'exit'): ").strip()

        if city.lower() in ["exit", "quit"]:
            print("👋 Exiting VAYORA. Stay safe!")
            break

        if not city:
            city = "Delhi"

        print(f"\n🔄 Fetching AQI for {city}...")
        data = get_city_aqi(city)

        if "error" in data:
            print(f"❌ {data['error']}")
            continue

        print(f"✅ AQI: {data['aqi']} | Station: {data.get('station', city)}")

        # ── Processing ─────────────────────────────────────
        health_info      = interpret_aqi(data["aqi"])
        weather_insights = analyze_weather_impact(data.get("pollutants", {}))
        forecast         = get_aqi_forecast(city)

        retrieved = query_knowledge(
            vector_db,
            query=f"AQI {data['aqi']} health impact and precautions"
        )

        print("🤖 Generating response...\n")

        response = run_vayora_agent(
            city=city,
            aqi=data["aqi"],
            health_assessment=health_info,
            weather_insights=weather_insights,
            retrieved_knowledge=retrieved,
            forecast=forecast,
            mode=mode,
            language=language,
            user_query=f"What is the AQI in {city} and what should I do?"
        )

        # ── Output ─────────────────────────────────────────
        print("═" * 60)
        print("🧠 VAYORA RESPONSE")
        print("═" * 60)
        print(response)
        print("═" * 60)


if __name__ == "__main__":
    run_vayora_terminal()