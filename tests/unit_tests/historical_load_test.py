from datetime import datetime
import pandas as pd
import pytest
from backend.supporting_methods.ercot_load import get_historical_load


# Validates schema, date filtering, ordering, and interval cadence in 1 query
def test_valid_request_schema_cadence_and_bounds():
    start_date = datetime(2022, 1, 1)
    end_date = datetime(2022, 1, 2)

    result = get_historical_load(
        weather_zone="BUSHIDG_COAST",
        start_date=start_date,
        end_date=end_date,
    )

    # Output structure & column checks
    assert not result.empty
    assert list(result.columns) == ["timestamp", "weather_zone", "load_mw"]
    assert (result["weather_zone"] == "BUSHIDG_COAST").all()

    # Boundary and monotonicity checks
    assert result["timestamp"].min() >= start_date
    assert result["timestamp"].max() < end_date
    assert result["timestamp"].is_monotonic_increasing

    # 15-minute interval check
    time_differences = result["timestamp"].diff().dropna()
    assert (time_differences == pd.Timedelta(minutes=15)).all()


@pytest.mark.parametrize(
    "weather_zone",
    [
        "RESLOWR_EAST",
        "RESLOWR_NORTH",
    ],
)
def test_multiple_weather_zones_return_data(weather_zone):
    result = get_historical_load(
        weather_zone=weather_zone,
        start_date=datetime(2022, 1, 1),
        end_date=datetime(2022, 1, 2),
    )

    assert not result.empty
    assert result["weather_zone"].nunique() == 1
    assert result["weather_zone"].iloc[0] == weather_zone


# --- Interval Edge Cases (Kept minimal boundaries, removed redundant hour/day tests) ---

def test_exact_15_minute_interval_and_exclusive_end():
    start_date = datetime(2022, 1, 1, 12, 0)
    end_date = datetime(2022, 1, 1, 12, 15)

    result = get_historical_load(
        weather_zone="BUSHIDG_COAST",
        start_date=start_date,
        end_date=end_date,
    )

    assert len(result) == 1
    assert result["timestamp"].iloc[0] == start_date
    assert end_date not in result["timestamp"].values


def test_interval_crossing_month_boundary():
    start_date = datetime(2022, 1, 31, 23, 0)
    end_date = datetime(2022, 2, 1, 1, 0)

    result = get_historical_load(
        weather_zone="BUSHIDG_COAST",
        start_date=start_date,
        end_date=end_date,
    )

    assert len(result) == 8
    assert result["timestamp"].min() == start_date
    assert result["timestamp"].max() == datetime(2022, 2, 1, 0, 45)


# --- Error Handling & Unknown Input ---

@pytest.mark.parametrize(
    "start,end",
    [
        (datetime(2022, 1, 2), datetime(2022, 1, 1)),  # Inverted range
        (datetime(2022, 1, 1), datetime(2022, 1, 1)),  # Same start and end
    ],
)
def test_invalid_date_ranges_raise_error(start, end):
    with pytest.raises(ValueError):
        get_historical_load(
            weather_zone="BUSHIDG_COAST",
            start_date=start,
            end_date=end,
        )


def test_empty_weather_zone_raises_error():
    with pytest.raises(ValueError):
        get_historical_load(
            weather_zone="",
            start_date=datetime(2022, 1, 1),
            end_date=datetime(2022, 1, 2),
        )


def test_unknown_weather_zone_returns_empty_dataframe():
    result = get_historical_load(
        weather_zone="NOT_A_REAL_ZONE",
        start_date=datetime(2022, 1, 1),
        end_date=datetime(2022, 1, 2),
    )

    assert result.empty
    assert list(result.columns) == ["timestamp", "weather_zone", "load_mw"]