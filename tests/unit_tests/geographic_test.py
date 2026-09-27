import pytest

from backend.location.geo_lookup import lookup_zip


def test_valid_zip_returns_coordinates():
    """A valid ZIP code should return ZIP, latitude, and longitude."""

    result = lookup_zip("75001")

    assert result["zip"] == "75001"
    assert isinstance(result["latitude"], float)
    assert isinstance(result["longitude"], float)


def test_valid_zip_coordinates_are_reasonable():
    """Returned coordinates should be valid latitude/longitude values."""

    result = lookup_zip("75001")

    assert -90 <= result["latitude"] <= 90
    assert -180 <= result["longitude"] <= 180


def test_invalid_zip_raises_error():
    """An unknown ZIP code should raise ValueError."""

    with pytest.raises(ValueError):
        lookup_zip("00000")


def test_short_zip_is_zero_padded():
    """A numeric ZIP shorter than 5 digits should be zero-padded."""

    result = lookup_zip("1001")

    assert result["zip"] == "01001"