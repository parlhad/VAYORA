from typing import Any, Dict, List, Optional


def _get_value(data: Dict[str, Any], key: str) -> Optional[float]:
    """
    Safely extract a numeric value.

    Supports the existing WAQI structure:

        {"t": {"v": 29}}

    and also allows future structured values such as:

        {"temperature": 29}
    """

    value = data.get(key)

    # Existing WAQI IAQI format:
    if isinstance(value, dict):
        value = value.get("v")

    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def analyze_weather_impact(
    pollutants: Dict[str, Any],
    weather: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """
    Analyze environmental conditions and produce cautious,
    human-readable insights.

    IMPORTANT:
    - Existing callers can continue using:
          analyze_weather_impact(pollutants)
    - A richer OpenWeather dictionary can optionally be supplied:
          analyze_weather_impact(pollutants, weather)

    This function does NOT determine the AQI category.
    AQI interpretation remains the responsibility of health_logic.py.

    It also avoids claiming that a single weather variable
    definitively caused the observed pollution.
    """

    pollutants = pollutants or {}
    weather = weather or {}

    # =========================================================
    # CURRENT WEATHER
    #
    # Prefer the real OpenWeather values when available.
    # Otherwise fall back to the existing WAQI IAQI values.
    # =========================================================

    temperature = weather.get("temperature")

    if temperature is None:
        temperature = _get_value(pollutants, "t")

    wind_speed = weather.get("wind_speed")

    if wind_speed is None:
        wind_speed = _get_value(pollutants, "w")

    humidity = weather.get("humidity")

    if humidity is None:
        humidity = _get_value(pollutants, "h")

    pressure = weather.get("pressure")

    if pressure is None:
        pressure = _get_value(pollutants, "p")

    # Additional real-weather fields available from OpenWeather.
    visibility = weather.get("visibility")
    cloudiness = weather.get("cloudiness")
    rain_1h = weather.get("rain_1h")

    description = weather.get("description")

    # =========================================================
    # POLLUTANTS
    # =========================================================

    pm25 = _get_value(pollutants, "pm25")
    pm10 = _get_value(pollutants, "pm10")
    no2 = _get_value(pollutants, "no2")
    o3 = _get_value(pollutants, "o3")
    co = _get_value(pollutants, "co")

    insights: List[str] = []

    # =========================================================
    # WIND
    # =========================================================

    if wind_speed is not None:

        if wind_speed < 0.5:
            insights.append(
                "Very low wind speed may reduce pollutant dispersion "
                "near the surface."
            )

        elif wind_speed < 2.0:
            insights.append(
                "Low wind speed may limit natural pollutant dispersion."
            )

        elif wind_speed > 7.0:
            insights.append(
                "Strong winds can increase atmospheric mixing and "
                "help disperse pollutants."
            )

    # =========================================================
    # HUMIDITY
    # =========================================================

    if humidity is not None:

        if humidity > 80:
            insights.append(
                f"Humidity is high ({humidity:.0f}%), which can affect "
                "particle behavior and may increase discomfort for "
                "some people."
            )

        elif humidity > 60:
            insights.append(
                f"Humidity is moderately high ({humidity:.0f}%)."
            )

    # =========================================================
    # PRESSURE
    #
    # Do NOT claim pressure alone proves an inversion.
    # =========================================================

    if pressure is not None:

        if pressure > 1015:
            insights.append(
                f"Atmospheric pressure is relatively high "
                f"({pressure:.0f} hPa). Pressure can influence "
                "weather and atmospheric mixing, but pressure alone "
                "does not establish a pollution inversion."
            )

        elif pressure < 998:
            insights.append(
                f"Atmospheric pressure is relatively low "
                f"({pressure:.0f} hPa). Its effect on pollution "
                "dispersion depends on the wider weather pattern."
            )

    # =========================================================
    # TEMPERATURE
    # =========================================================

    if temperature is not None:

        if temperature < 12:
            insights.append(
                f"Current temperature is {temperature:.1f}°C. "
                "Cool conditions can sometimes be associated with "
                "reduced vertical mixing, depending on the atmosphere."
            )

        elif temperature > 36:
            insights.append(
                f"Current temperature is {temperature:.1f}°C. "
                "High temperatures can contribute to ozone formation "
                "under suitable sunlight and atmospheric conditions."
            )

    # =========================================================
    # VISIBILITY
    # =========================================================

    if visibility is not None:

        try:
            visibility_km = float(visibility) / 1000.0

            if visibility_km < 2:
                insights.append(
                    f"Visibility is low at about {visibility_km:.1f} km. "
                    "Reduced visibility can occur with haze, particles, "
                    "fog, rain, or other atmospheric conditions."
                )

        except (TypeError, ValueError):
            pass

    # =========================================================
    # RAIN
    # =========================================================

    if rain_1h is not None:

        try:
            rain_amount = float(rain_1h)

            if rain_amount > 0:
                insights.append(
                    f"OpenWeather reports approximately "
                    f"{rain_amount:.1f} mm of rain in the last hour."
                )

        except (TypeError, ValueError):
            pass

    # =========================================================
    # GENERAL WEATHER DESCRIPTION
    # =========================================================

    if description:
        insights.append(
            f"Current weather: {str(description).capitalize()}."
        )

    # =========================================================
    # PM2.5
    # =========================================================

    if pm25 is not None and pm25 > 55:
        insights.append(
            f"PM2.5 is {pm25:.1f} µg/m³, indicating elevated "
            "fine-particle pollution that can be harmful to health."
        )

    # =========================================================
    # PM10
    # =========================================================

    if pm10 is not None and pm10 > 100:
        insights.append(
            f"PM10 is {pm10:.1f} µg/m³, indicating elevated "
            "coarse-particle pollution."
        )

    # =========================================================
    # NO2
    # =========================================================

    if no2 is not None and no2 > 40:
        insights.append(
            f"NO₂ is {no2:.1f} µg/m³, indicating elevated "
            "nitrogen-dioxide levels."
        )

    # =========================================================
    # OZONE
    # =========================================================

    if o3 is not None and o3 > 100:
        insights.append(
            f"Ozone is {o3:.1f} µg/m³, which may contribute to "
            "airway irritation, particularly during outdoor activity."
        )

    # =========================================================
    # CARBON MONOXIDE
    # =========================================================

    if co is not None and co > 4:
        insights.append(
            f"CO is {co:.1f} mg/m³, indicating an elevated "
            "carbon-monoxide concentration."
        )

    # =========================================================
    # DEFAULT
    # =========================================================

    if not insights:
        insights.append(
            "No additional weather or pollutant insight could be "
            "derived from the available data."
        )

    return insights