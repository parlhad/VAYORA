from typing import Any, Dict, Optional

from app.services.health_logic import interpret_aqi


def assess_risk(aqi: Optional[int]) -> Dict[str, Any]:
    """
    Assess the health risk associated with the current AQI.

    This is a deterministic reasoning layer.

    Responsibilities:
    - Validate the AQI value.
    - Use health_logic.py as the authoritative AQI
      interpretation layer.
    - Convert that interpretation into a compact risk
      decision for the VAYORA agent.

    This function does NOT:
    - call Gemini
    - invent environmental data
    - estimate missing AQI
    - replace the authoritative AQI classification
    """

    # =========================================================
    # 1. Validate AQI
    # =========================================================

    try:
        if aqi is None:
            normalized_aqi = None
        else:
            normalized_aqi = int(aqi)

    except (TypeError, ValueError):
        normalized_aqi = None

    # =========================================================
    # 2. Use existing authoritative AQI interpretation
    # =========================================================

    assessment = interpret_aqi(normalized_aqi)

    # Protect against an unexpected response from health_logic.
    if not isinstance(assessment, dict):
        assessment = {}

    # =========================================================
    # 3. AQI unavailable
    # =========================================================

    if normalized_aqi is None:

        return {
            "aqi": None,

            "category": assessment.get(
                "category",
                "Unknown"
            ),

            "risk": assessment.get(
                "risk_level",
                "Unknown"
            ),

            "urgency": assessment.get(
                "urgency",
                "low"
            ),

            "color": assessment.get(
                "color",
                "gray"
            ),

            "outdoor_ok": False,

            "mask_needed": False,

            "outdoor_activity": assessment.get(
                "outdoor_activity",
                "unknown"
            ),

            "sensitive_groups": assessment.get(
                "sensitive_groups",
                []
            ),

            "reason": (
                "Current AQI data is unavailable."
            ),

            "data_available": False,
        }

    # =========================================================
    # 4. Valid AQI
    # =========================================================

    outdoor_activity = assessment.get(
        "outdoor_activity",
        "unknown"
    )

    return {

        # -----------------------------------------------------
        # AQI
        # -----------------------------------------------------

        "aqi": normalized_aqi,

        # -----------------------------------------------------
        # Authoritative health interpretation
        # -----------------------------------------------------

        "category": assessment.get(
            "category",
            "Unknown"
        ),

        "risk": assessment.get(
            "risk_level",
            "Unknown"
        ),

        "urgency": assessment.get(
            "urgency",
            "low"
        ),

        "color": assessment.get(
            "color",
            "gray"
        ),

        # -----------------------------------------------------
        # Outdoor guidance
        # -----------------------------------------------------

        "outdoor_ok": outdoor_activity in {
            "unrestricted",
            "unrestricted for most",
        },

        "mask_needed": assessment.get(
            "mask_needed",
            False
        ),

        "outdoor_activity": outdoor_activity,

        # -----------------------------------------------------
        # Sensitive groups
        # -----------------------------------------------------

        "sensitive_groups": assessment.get(
            "sensitive_groups",
            []
        ),

        # -----------------------------------------------------
        # Deterministic explanation
        # -----------------------------------------------------

        "reason": assessment.get(
            "explanation",
            ""
        ),

        "data_available": True,
    }