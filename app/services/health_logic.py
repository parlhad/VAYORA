def interpret_aqi(aqi: int) -> dict:
    try:
        aqi = int(aqi)
    except (TypeError, ValueError):
        aqi = None

    if aqi is None:
        return {
            "category": "Unknown",
            "risk_level": "Unknown",
            "urgency": "low",
            "color": "gray",
            "advice": "AQI data unavailable.",
            "explanation": "Air quality data could not be retrieved.",
            "mask_needed": False,
            "outdoor_activity": "unknown",
            "sensitive_groups": []
        }

    # -------------------------------------------------------
    # GOOD
    # -------------------------------------------------------
    if aqi <= 50:
        return {
            "category": "Good",
            "risk_level": "Minimal",
            "urgency": "low",
            "color": "green",
            "advice": "Enjoy outdoor activities normally.",
            "explanation": "Air quality is considered satisfactory with little or no health risk.",
            "mask_needed": False,
            "outdoor_activity": "unrestricted",
            "sensitive_groups": []
        }

    # -------------------------------------------------------
    # MODERATE
    # -------------------------------------------------------
    elif aqi <= 100:
        return {
            "category": "Moderate",
            "risk_level": "Low",
            "urgency": "low",
            "color": "yellow",
            "advice": "Sensitive individuals should monitor symptoms.",
            "explanation": "Air quality is acceptable, but some pollutants may pose a mild risk to sensitive people.",
            "mask_needed": False,
            "outdoor_activity": "unrestricted for most",
            "sensitive_groups": ["asthma", "allergies"]
        }

    # -------------------------------------------------------
    # SENSITIVE GROUPS
    # -------------------------------------------------------
    elif aqi <= 150:
        return {
            "category": "Unhealthy for Sensitive Groups",
            "risk_level": "Medium",
            "urgency": "medium",
            "color": "orange",
            "advice": "Children, elderly, and people with respiratory issues should reduce prolonged outdoor exertion.",
            "explanation": "Sensitive groups may experience health effects, while the general public is less likely to be affected.",
            "mask_needed": False,
            "outdoor_activity": "limited for sensitive groups",
            "sensitive_groups": ["children", "elderly", "asthma", "heart disease"]
        }

    # -------------------------------------------------------
    # UNHEALTHY
    # -------------------------------------------------------
    elif aqi <= 200:
        return {
            "category": "Unhealthy",
            "risk_level": "High",
            "urgency": "high",
            "color": "red",
            "advice": "Avoid prolonged outdoor activity. Wear an N95 mask if going outside.",
            "explanation": "Everyone may begin to experience health effects, with sensitive groups at higher risk.",
            "mask_needed": True,
            "outdoor_activity": "minimize",
            "sensitive_groups": ["everyone"]
        }

    # -------------------------------------------------------
    # VERY UNHEALTHY
    # -------------------------------------------------------
    elif aqi <= 300:
        return {
            "category": "Very Unhealthy",
            "risk_level": "Very High",
            "urgency": "critical",
            "color": "purple",
            "advice": "Stay indoors as much as possible. Avoid outdoor activities completely.",
            "explanation": "Health alert: the risk of health effects is increased for everyone.",
            "mask_needed": True,
            "outdoor_activity": "avoid",
            "sensitive_groups": ["everyone"]
        }

    # -------------------------------------------------------
    # HAZARDOUS
    # -------------------------------------------------------
    else:
        return {
            "category": "Hazardous",
            "risk_level": "Severe",
            "urgency": "critical",
            "color": "maroon",
            "advice": "Remain indoors with air filtration. Follow health advisories strictly.",
            "explanation": "Serious health effects are likely for the entire population.",
            "mask_needed": True,
            "outdoor_activity": "prohibited",
            "sensitive_groups": ["everyone"]
        }