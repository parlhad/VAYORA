from typing import List


def analyze_weather_impact(pollutants: dict) -> List[str]:
    # -------------------------------------------------------
    # 🔍 Extract values (V1 base)
    # -------------------------------------------------------
    temperature = pollutants.get("t", {}).get("v")
    wind_speed  = pollutants.get("w", {}).get("v")
    humidity    = pollutants.get("h", {}).get("v")
    pressure    = pollutants.get("p", {}).get("v")

    # 🔥 Added from V2/V3
    pm25 = pollutants.get("pm25", {}).get("v")
    pm10 = pollutants.get("pm10", {}).get("v")
    no2  = pollutants.get("no2", {}).get("v")
    o3   = pollutants.get("o3", {}).get("v")
    co   = pollutants.get("co", {}).get("v")

    insights = []

    # -------------------------------------------------------
    # 🌬️ WIND
    # -------------------------------------------------------
    if wind_speed is not None:
        if wind_speed < 0.5:
            insights.append("Very low wind speed — pollutants are trapped near ground level.")
        elif wind_speed < 2.0:
            insights.append("Low wind speed is reducing natural pollutant dispersal.")
        elif wind_speed > 7.0:
            insights.append("Strong winds are helping disperse pollutants — air may improve.")

    # -------------------------------------------------------
    # 💧 HUMIDITY
    # -------------------------------------------------------
    if humidity is not None:
        if humidity > 80:
            insights.append("High humidity increases particle size, worsening respiratory irritation.")
        elif humidity > 60:
            insights.append("Moderate humidity may slightly increase pollution concentration.")

    # -------------------------------------------------------
    # 🌡️ PRESSURE
    # -------------------------------------------------------
    if pressure is not None:
        if pressure > 1015:
            insights.append("High atmospheric pressure can trap pollutants near the surface (inversion effect).")
        elif pressure < 998:
            insights.append("Low pressure may help pollutants disperse more easily.")

    # -------------------------------------------------------
    # 🌡️ TEMPERATURE
    # -------------------------------------------------------
    if temperature is not None:
        if temperature < 12:
            insights.append(f"Low temperature ({temperature}°C) may trap pollution near ground.")
        elif temperature > 36:
            insights.append(f"High temperature ({temperature}°C) may increase ozone formation.")

    # -------------------------------------------------------
    # 🧪 POLLUTANTS (V2/V3 POWER)
    # -------------------------------------------------------
    if pm25 is not None and pm25 > 55:
        insights.append(f"PM2.5 at {pm25} µg/m³ — harmful fine particles affecting lungs and bloodstream.")

    if pm10 is not None and pm10 > 100:
        insights.append(f"PM10 at {pm10} µg/m³ — high dust levels likely from construction or roads.")

    if no2 is not None and no2 > 40:
        insights.append(f"NO2 at {no2} µg/m³ — indicates heavy traffic or industrial pollution.")

    if o3 is not None and o3 > 100:
        insights.append(f"Ozone at {o3} µg/m³ — may cause breathing discomfort during activity.")

    if co is not None and co > 4:
        insights.append(f"CO at {co} mg/m³ — elevated levels from combustion sources.")

    # -------------------------------------------------------
    # ✅ DEFAULT
    # -------------------------------------------------------
    if not insights:
        insights.append("Weather conditions do not indicate significant pollution buildup.")

    return insights