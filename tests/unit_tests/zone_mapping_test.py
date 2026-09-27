import pytest

from backend.location.load_zone_lookup import get_ercot_load_zone


def test_valid_dallas_zip_returns_load_zone():
    result = get_ercot_load_zone("75001")

    assert result == "North"


def test_valid_houston_zip_returns_load_zone():
    result = get_ercot_load_zone("77001")

    assert result == "Houston"


def test_valid_austin_zip_returns_load_zone():
    result = get_ercot_load_zone("78701")

    assert result == "South"


def test_integer_zip_is_accepted():
    result = get_ercot_load_zone(75001)

    assert result == "North"


def test_zip_with_whitespace_is_accepted():
    result = get_ercot_load_zone(" 75001 ")

    assert result == "North"


def test_unknown_zip_raises_value_error():
    with pytest.raises(ValueError):
        get_ercot_load_zone("00000")


def test_nonexistent_zip_raises_value_error():
    with pytest.raises(ValueError):
        get_ercot_load_zone("99999")