import pytest

from backend.location.utility import get_utility


def test_valid_coordinates_return_utility():
    """Zipcode inside a utility territory should return a utility name."""

    result = get_utility(14263)

    assert result == "Niagara Mohawk Power Corp."
    assert result != ""


def test_another_valid_zip_returns_expected_utility():
    """Another ZIP code should return its associated utility."""

    result = get_utility(93199)

    assert result == "Southern California Edison Co"


def test_unknown_zip_raises_error():
    """An unknown ZIP code should raise a ValueError."""

    with pytest.raises(ValueError, match="ZIP code not found"):
        get_utility(00000)


def test_short_zip_is_zero_padded():
    """A ZIP code shorter than five digits should be zero-padded."""

    result = get_utility(1201)

    assert result == get_utility("01201")


def test_zip_with_whitespace_is_handled():
    """Whitespace around a ZIP code should be ignored."""

    result = get_utility(" 14263 ")

    assert result == "Niagara Mohawk Power Corp."



 