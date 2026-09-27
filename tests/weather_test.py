import pytest
import requests
from datetime import datetime
from backend.supporting_methods.weather import get_weather


def test_valid_request_returns_data():
    """Test that a valid request returns hourly weather data."""
    result = get_weather(
        latitude=30.2672,
        longitude=-97.7431,
        start_date=datetime(2022, 1, 1),
        end_date=datetime(2022, 1, 2)
    )

    assert result is not None
    assert len(result) > 0


def test_returns_correct_data_structure():
    """Test that each weather reading contains a timestamp and temperature."""
    result = get_weather(
        latitude=30.2672,
        longitude=-97.7431,
        start_date=datetime(2022, 1, 1),
        end_date=datetime(2022, 1, 2)
    )

    assert result is not None

    first_reading = result[0]

    assert "timestamp" in first_reading
    assert "temperature_f" in first_reading
    assert first_reading["timestamp"] is not None
    assert first_reading["temperature_f"] is not None


def test_one_day_request_returns_24_readings():
    """Test that one full day returns 24 hourly readings."""
    result = get_weather(
        latitude=30.2672,
        longitude=-97.7431,
        start_date=datetime(2022, 1, 1),
        end_date=datetime(2022, 1, 1)
    )

    assert result is not None
    assert len(result) == 24


def test_multiple_day_request_returns_expected_readings():
    """Test that multiple days return the expected number of hourly readings."""
    result = get_weather(
        latitude=30.2672,
        longitude=-97.7431,
        start_date=datetime(2022, 1, 1),
        end_date=datetime(2022, 1, 3)
    )

    assert result is not None
    assert len(result) == 72


def test_different_location_returns_data():
    """Test that the function works for a different location."""
    result = get_weather(
        latitude=40.7128,
        longitude=-74.0060,
        start_date=datetime(2022, 7, 1),
        end_date=datetime(2022, 7, 2)
    )

    assert result is not None
    assert len(result) > 0


def test_api_failure_returns_none(monkeypatch):
    """Test that an API failure returns None."""

    def mock_get(*args, **kwargs):
        raise requests.RequestException("API unavailable")

    monkeypatch.setattr(requests, "get", mock_get)

    result = get_weather(
        latitude=30.2672,
        longitude=-97.7431,
        start_date=datetime(2022, 1, 1),
        end_date=datetime(2022, 1, 2)
    )

    assert result is None