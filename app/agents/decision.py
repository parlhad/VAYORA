from typing import Any, Dict

from app.agents.state import VayoraState


def decide_response_style(state: VayoraState) -> Dict[str, Any]:
    """
    Decide how VAYORA should respond based on deterministic risk
    assessment and the user's requested mode.

    This function does NOT generate the response.
    It only decides the communication strategy that will later
    be given to Gemini.

    Priority:
        1. Environmental risk
        2. User-requested mode
        3. Intent
    """

    # ---------------------------------------------------------
    # Read state safely
    # ---------------------------------------------------------
    risk_decision = state.get("risk_decision") or {}

    urgency = str(
        risk_decision.get("urgency", "low")
    ).lower()

    risk = str(
        risk_decision.get("risk", "unknown")
    ).lower()

    category = str(
        risk_decision.get("category", "unknown")
    ).lower()

    mode = str(
        state.get("mode", "balanced")
    ).lower()

    intent = str(
        state.get("intent", "")
    ).lower()

    # ---------------------------------------------------------
    # Default response strategy
    # ---------------------------------------------------------
    style: Dict[str, Any] = {
        "tone": "clear and helpful",
        "detail_level": "medium",
        "focus": "answer the user's question",
        "priority": "normal",
        "include_live_data": bool(
            state.get("needs_live", False)
        ),
        "include_health_guidance": False,
        "include_weather_context": False,
        "include_uncertainty": False,
    }

    # ---------------------------------------------------------
    # Risk-based decisions
    # ---------------------------------------------------------
    #
    # Critical / very high risk:
    # Keep the answer direct, calm and safety-focused.
    #
    if urgency in {
        "critical",
        "emergency",
        "very_high",
        "high",
    }:
        style.update(
            {
                "tone": "calm, direct and safety-focused",
                "detail_level": "high",
                "focus": "health protection and immediate practical guidance",
                "priority": "high",
                "include_health_guidance": True,
            }
        )

    # Moderate risk:
    # Give useful context without sounding alarmist.
    elif urgency in {
        "moderate",
        "medium",
    }:
        style.update(
            {
                "tone": "clear, practical and informative",
                "detail_level": "medium",
                "focus": "risk awareness and practical guidance",
                "include_health_guidance": True,
            }
        )

    # Low / good conditions:
    # Avoid unnecessary alarm.
    else:
        style.update(
            {
                "tone": "clear, concise and reassuring",
                "detail_level": "medium",
                "focus": "answer the user's question with useful context",
                "priority": "normal",
            }
        )

    # ---------------------------------------------------------
    # User-requested response mode
    # ---------------------------------------------------------
    if mode == "deep":
        style["detail_level"] = "high"

    elif mode == "concise":
        style["detail_level"] = "low"

    elif mode == "balanced":
        # Keep risk-based detail level.
        pass

    # ---------------------------------------------------------
    # Intent-specific adjustments
    # ---------------------------------------------------------

    # Weather-related questions should make room for weather
    # context when weather data exists.
    if "weather" in intent:
        style["include_weather_context"] = True

    # Outdoor/activity/decision questions need practical guidance.
    if any(
        keyword in intent
        for keyword in (
            "activity",
            "outdoor",
            "decision",
            "running",
            "exercise",
            "walk",
            "travel",
        )
    ):
        style["include_health_guidance"] = True
        style["focus"] = (
            "give a practical decision using verified environmental data"
        )

    # Health-related questions should emphasize protection,
    # but VAYORA must not present itself as a diagnostic system.
    if "health" in intent:
        style["include_health_guidance"] = True

    # ---------------------------------------------------------
    # Data availability
    # ---------------------------------------------------------
    data_status = str(
        state.get("data_status", "")
    ).lower()

    if data_status in {
        "unavailable",
        "partial",
        "unknown",
    }:
        style["include_uncertainty"] = True

    # ---------------------------------------------------------
    # Return complete decision object
    # ---------------------------------------------------------
    return {
        **style,
        "urgency": urgency,
        "risk": risk,
        "aqi_category": category,
        "mode": mode,
        "intent": intent,
    }