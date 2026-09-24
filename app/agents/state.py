from typing import TypedDict, List, Optional, Dict, Any


class VayoraState(TypedDict, total=False):
    """
    Shared state passed through the VAYORA agent pipeline.

    This remains a TypedDict so it is compatible with the current
    dictionary-based architecture.

    The state is intentionally data-focused:
    - live API data remains separate from AI-generated text
    - deterministic reasoning is stored separately
    - response decisions are stored separately
    - RAG knowledge is kept separate from live data
    """

    # ==========================================================
    # REQUEST / CONVERSATION CONTEXT
    # ==========================================================

    session_id: str
    user_message: str

    # Detected user intent
    intent: str

    # Response mode selected by the user/system
    # balanced | deep | emergency
    mode: str

    # Response language
    # en | hi | hinglish | mr
    language: str

    # Time requested by the user
    # now | tomorrow | next_hours | unknown
    time_scope: str

    # Whether the request requires live environmental data
    needs_live: bool


    # ==========================================================
    # LOCATION
    # ==========================================================

    # Human-readable city name
    city: Optional[str]

    # Resolved geographic coordinates
    latitude: Optional[float]
    longitude: Optional[float]

    # How the location was obtained/resolved
    # e.g. user_query | session_memory | geocoding
    location_source: Optional[str]


    # ==========================================================
    # LIVE AQI DATA
    # ==========================================================

    # Current AQI value from the live AQI source
    aqi: Optional[int]

    # Pollutant measurements returned by the AQI service
    pollutants: Optional[Dict[str, Any]]

    # Monitoring station name
    station: Optional[str]

    # Observation/update timestamp supplied by the data source
    observation_time: Optional[str]

    # Data source, e.g. WAQI
    aqi_source: Optional[str]

    # Whether the returned AQI came from cache
    from_cache: bool


    # ==========================================================
    # CURRENT WEATHER DATA
    # ==========================================================

    # Structured current-weather response.
    #
    # Kept separate from weather_insights because raw values are
    # live data while weather_insights are derived explanations.
    weather: Optional[Dict[str, Any]]

    # Weather data source, e.g. OpenWeather
    weather_source: Optional[str]

    # Weather observation/update timestamp
    weather_observation_time: Optional[str]

    # Human-readable weather/environment interpretation
    weather_insights: List[str]


    # ==========================================================
    # DATA QUALITY / AVAILABILITY
    # ==========================================================

    # Overall live-data state.
    # Examples:
    # live | recent | unavailable | partial
    data_status: Optional[str]

    # Optional detailed errors/warnings from services.
    #
    # These should describe missing/unavailable data and must not
    # be treated as factual environmental observations.
    data_warnings: List[str]


    # ==========================================================
    # DETERMINISTIC HEALTH / RISK REASONING
    # ==========================================================

    # Existing AQI health interpretation
    health_assessment: Optional[Dict[str, Any]]

    # Result produced by reasoning.py / assess_risk()
    risk_decision: Optional[Dict[str, Any]]


    # ==========================================================
    # RESPONSE DECISION
    # ==========================================================

    # Result produced by decision.py.
    #
    # Example:
    # {
    #     "tone": "urgent but calm",
    #     "detail_level": "high",
    #     "focus": "health protection",
    #     ...
    # }
    response_style: Optional[Dict[str, Any]]


    # ==========================================================
    # FORECAST
    # ==========================================================

    # Forecast data from the forecast service.
    #
    # This must contain real forecast information only.
    forecast: Optional[Dict[str, Any]]

    # Whether a reliable forecast is actually available
    forecast_available: bool


    # ==========================================================
    # RAG / KNOWLEDGE
    # ==========================================================

    # Query constructed for knowledge retrieval
    rag_query: Optional[str]

    # Retrieved knowledge from FAISS/RAG
    retrieved_knowledge: str


    # ==========================================================
    # SESSION MEMORY
    # ==========================================================

    # Context retrieved from session_memory.py
    session_context: str

    # Previous AQI information kept for conversational context
    last_aqi_context: str

    # Recent conversation history
    history: List[str]


    # ==========================================================
    # FINAL OUTPUT
    # ==========================================================

    # Final Gemini-generated response
    reply: str