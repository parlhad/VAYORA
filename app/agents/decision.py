def decide_response_style(state):
    urgency = state.urgency
    mode = getattr(state, "mode", "balanced")  # safe fallback

    if urgency == "critical":
        return {
            "tone": "urgent and direct",
            "detail_level": "high",
            "focus": "immediate health protection",
            "use_headers": False,
            "bullet_count": "3-5 commands only",
            "include_forecast": True,
            "include_pollutants": False,
            "include_science": False,
            "lead_with_aqi": True,
            "user_groups_to_flag": ["everyone"],
        }

    elif urgency == "high":
        return {
            "tone": "urgent but calm",  # ✅ from V1 (IMPORTANT)
            "detail_level": "high",
            "focus": "health protection",
            "use_headers": mode == "deep",
            "bullet_count": "4-6",
            "include_forecast": True,
            "include_pollutants": True,
            "include_science": mode == "deep",
            "lead_with_aqi": True,
            "user_groups_to_flag": ["children", "elderly", "asthma"],
        }

    elif urgency == "medium":
        return {
            "tone": "advisory",  # ✅ V1 tone preserved
            "detail_level": "medium",
            "focus": "precaution",
            "use_headers": mode == "deep",
            "bullet_count": "3-5",
            "include_forecast": True,
        }

    else:
        return {
            "tone": "informative",  # ✅ V1 tone preserved
            "detail_level": "low",
            "focus": "awareness",
            "use_headers": False,
            "bullet_count": "2-4",
            "include_forecast": True,
        }