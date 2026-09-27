import pytest

from backend.location.zip_to_coord import get_zip_centroid


def test_valid_zip_returns_coordinates():
    """A valid US ZIP code should return latitude and longitude."""

    lat, lon = get_zip_centroid("75001")

    assert lat is not None
    assert lon is not None
    assert isinstance(lat, float)
    assert isinstance(lon, float)


def test_valid_zip_returns_reasonable_coordinates():
    """Returned coordinates should fall within valid geographic ranges."""

    lat, lon = get_zip_centroid("75001")

    assert -90 <= lat <= 90
    assert -180 <= lon <= 180


def test_integer_zip_is_accepted():
    """An integer ZIP code should be accepted."""

    lat, lon = get_zip_centroid(75001)

    assert lat is not None
    assert lon is not None


def test_zip_with_whitespace_is_handled():
    """Whitespace surrounding a ZIP code should be ignored."""

    lat1, lon1 = get_zip_centroid("75001")
    lat2, lon2 = get_zip_centroid(" 75001 ")

    assert lat1 == lat2
    assert lon1 == lon2


def test_leading_zero_zip_is_preserved():
    """A ZIP code beginning with zero should be handled correctly."""

    lat1, lon1 = get_zip_centroid("02138")
    lat2, lon2 = get_zip_centroid(2138)

    assert lat1 == lat2
    assert lon1 == lon2


def test_unknown_zip_returns_none():
    """A ZIP code that does not exist should return (None, None)."""

    lat, lon = get_zip_centroid("00000")

    assert lat is None
    assert lon is None


def test_nonexistent_zip_returns_none():
    """A syntactically valid but nonexistent ZIP should return (None, None)."""

    lat, lon = get_zip_centroid("99999")

    assert lat is None
    assert lon is None