from typing import TypedDict, List, Optional, Dict, Any


class VayoraState(TypedDict, total=False):
    # ── Request context ─────────────────────────
    session_id: str
    user_message: str
    intent: str
    mode: str                 # balanced | deep | emergency
    language: str             # en | hi | hinglish
    time_scope: str           # now | tomorrow | next_hours
    needs_live: bool

    # ── City ───────────────────────────────────
    city: Optional[str]

    # ── AQI data ───────────────────────────────
    aqi: Optional[int]
    pollutants: Optional[Dict[str, Any]]
    station: Optional[str]
    from_cache: bool

    # ── Derived data ───────────────────────────
    health_assessment: Optional[Dict]
    risk_decision: Optional[Dict]
    weather_insights: List[str]

    # ── Forecast ───────────────────────────────
    forecast: Optional[Dict]

    # ── Knowledge (RAG) ────────────────────────
    retrieved_knowledge: str

    # ── Session memory ─────────────────────────
    session_context: str
    last_aqi_context: str

    # ── Output ────────────────────────────────
    reply: str
    history: List[str]