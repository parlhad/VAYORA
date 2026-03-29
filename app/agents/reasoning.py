def assess_risk(aqi: int) -> dict:
    if aqi is None:
        return {
            "category": "Unknown",
            "risk": "Unknown",
            "urgency": "low",
            "color": "gray",
            "outdoor_ok": True,
            "mask_needed": False
        }

    elif aqi <= 50:
        return {
            "category": "Good",
            "risk": "Low",
            "urgency": "low",
            "color": "green",
            "outdoor_ok": True,
            "mask_needed": False
        }

    elif aqi <= 100:
        return {
            "category": "Moderate",
            "risk": "Low",
            "urgency": "low",
            "color": "yellow",
            "outdoor_ok": True,
            "mask_needed": False
        }

    elif aqi <= 150:
        return {
            "category": "Unhealthy for Sensitive Groups",
            "risk": "Medium",
            "urgency": "medium",
            "color": "orange",
            "outdoor_ok": True,
            "mask_needed": False
        }

    elif aqi <= 200:
        return {
            "category": "Unhealthy",
            "risk": "High",
            "urgency": "high",
            "color": "red",
            "outdoor_ok": False,
            "mask_needed": True
        }

    elif aqi <= 300:
        return {
            "category": "Very Unhealthy",
            "risk": "Very High",
            "urgency": "critical",
            "color": "purple",
            "outdoor_ok": False,
            "mask_needed": True
        }

    else:
        return {
            "category": "Hazardous",
            "risk": "Severe",
            "urgency": "critical",
            "color": "maroon",
            "outdoor_ok": False,
            "mask_needed": True
        }