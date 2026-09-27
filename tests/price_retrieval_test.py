import pandas as pd
import pytest

from backend.supporting_methods.retrieve_price import get_historical_price


def test_valid_price_lookup():
    """A valid timestamp and settlement point should return a price."""

    timestamp = pd.Timestamp("2022-01-01 12:00:00")
    settlement_point = "LZ_NORTH"

    price = get_historical_price(
        timestamp=timestamp,
        settlement_point=settlement_point
    )

    assert isinstance(price, float)
    assert price >= 0


def test_price_is_returned_in_kwh():
    """The returned price should be in $/kWh, not $/MWh."""

    timestamp = pd.Timestamp("2022-01-01 12:00:00")
    settlement_point = "LZ_NORTH"

    price_kwh = get_historical_price(
        timestamp=timestamp,
        settlement_point=settlement_point
    )

    # ERCOT prices should be much smaller when expressed in $/kWh.
    assert price_kwh < 10


def test_different_settlement_points_return_prices():
    """Different settlement points should be independently retrievable."""

    timestamp = pd.Timestamp("2022-01-01 12:00:00")

    north_price = get_historical_price(
        timestamp=timestamp,
        settlement_point="LZ_NORTH"
    )

    houston_price = get_historical_price(
        timestamp=timestamp,
        settlement_point="LZ_HOUSTON"
    )

    assert isinstance(north_price, float)
    assert isinstance(houston_price, float)


def test_different_years_are_supported():
    """The function should select the correct yearly workbook."""

    test_cases = [
        pd.Timestamp("2022-01-01 12:00:00"),
        pd.Timestamp("2023-01-01 12:00:00"),
        pd.Timestamp("2024-01-01 12:00:00"),
        pd.Timestamp("2025-01-01 12:00:00"),
        pd.Timestamp("2026-01-01 12:00:00"),
    ]

    for timestamp in test_cases:
        price = get_historical_price(
            timestamp=timestamp,
            settlement_point="LZ_NORTH"
        )

        assert isinstance(price, float)
        assert price >= 0


def test_different_intervals_are_supported():
    """The function should correctly retrieve different 15-minute intervals."""

    timestamp_1 = pd.Timestamp("2022-01-01 12:00:00")
    timestamp_2 = pd.Timestamp("2022-01-01 12:15:00")
    timestamp_3 = pd.Timestamp("2022-01-01 12:30:00")
    timestamp_4 = pd.Timestamp("2022-01-01 12:45:00")

    prices = [
        get_historical_price(timestamp_1, "LZ_NORTH"),
        get_historical_price(timestamp_2, "LZ_NORTH"),
        get_historical_price(timestamp_3, "LZ_NORTH"),
        get_historical_price(timestamp_4, "LZ_NORTH"),
    ]

    assert all(isinstance(price, float) for price in prices)


def test_invalid_settlement_point_raises_error():
    """An unknown settlement point should raise ValueError."""

    timestamp = pd.Timestamp("2022-01-01 12:00:00")

    with pytest.raises(ValueError, match="No ERCOT price found"):
        get_historical_price(
            timestamp=timestamp,
            settlement_point="NOT_A_REAL_SETTLEMENT_POINT"
        )


def test_timestamp_not_in_dataset_raises_error():
    """A timestamp that does not exist should raise ValueError."""

    timestamp = pd.Timestamp("2022-01-01 12:07:00")

    with pytest.raises(ValueError, match="No ERCOT price found"):
        get_historical_price(
            timestamp=timestamp,
            settlement_point="LZ_NORTH"
        )


def test_missing_year_file_raises_error():
    """A year without a corresponding pricing file should raise FileNotFoundError."""

    timestamp = pd.Timestamp("2030-01-01 12:00:00")

    with pytest.raises(FileNotFoundError):
        get_historical_price(
            timestamp=timestamp,
            settlement_point="LZ_NORTH"
        )


def test_missing_month_sheet_raises_error():
    """A month without a corresponding sheet should raise ValueError."""
    
    timestamp = pd.Timestamp("2026-12-01 00:00:00")

    with pytest.raises(
        ValueError,
        match=r"Month sheet 'Dec' was not found"
    ):
        get_historical_price(
            timestamp=timestamp,
            settlement_point="LZ_NORTH"
        )