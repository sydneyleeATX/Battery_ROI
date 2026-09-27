from datetime import datetime
from typing import Optional
import requests


OPENMETEO_HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/archive"


def get_weather(
    latitude: float,
    longitude: float,
    start_date: datetime,
    end_date: datetime
) -> Optional[list]:
    """
    Get hourly historical temperature data for a location.

    Args:
        latitude: Latitude of the location.
        longitude: Longitude of the location.
        start_date: Start date for historical weather data.
        end_date: End date for historical weather data.

    Returns:
        List of hourly timestamps and temperatures, or None if
        the API request fails.
    """

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "hourly": "temperature_2m",
        "temperature_unit": "fahrenheit",
        "timezone": "auto",
    }

    try:
        response = requests.get(
            OPENMETEO_HISTORICAL_URL,
            params=params,
            timeout=10
        )
        response.raise_for_status()

        data = response.json()

        hourly_data = data.get("hourly", {})

        return [
            {
                "timestamp": timestamp,
                "temperature_f": temperature
            }
            for timestamp, temperature in zip(
                hourly_data.get("time", []),
                hourly_data.get("temperature_2m", [])
            )
        ]

    except Exception as e:
        print(f"Error fetching historical weather: {e}")
        return None


