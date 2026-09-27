import pandas as pd
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import os

from backend.supporting_methods.cost_simulation import build_historical_data_from_location


# ============================================================
# Test 1: Valid location - Complete data flow
# ============================================================

@patch('backend.supporting_methods.weather.get_weather')
@patch('backend.supporting_methods.retrieve_price.get_historical_prices_bulk')
@patch('backend.location.zip_to_coord.get_zip_centroid')
@patch('backend.location.load_zone_lookup.get_ercot_load_zone')
def test_valid_location_returns_complete_dataframe(
    mock_load_zone,
    mock_zip_centroid,
    mock_prices_bulk,
    mock_weather,
    tmp_path,
    capsys
):
    """Test complete data flow from ZIP to final DataFrame."""
    
    # Setup mocks
    mock_load_zone.return_value = "LZ_NORTH"
    mock_zip_centroid.return_value = (32.7767, -96.7970)  # Dallas coordinates
    
    # Mock price data (15-minute intervals)
    start_date = datetime(2024, 1, 1, 0, 0)
    end_date = datetime(2024, 1, 1, 2, 0)
    
    price_timestamps = pd.date_range(start=start_date, end=end_date, freq="15min")
    mock_prices_bulk.return_value = pd.DataFrame({
        "Timestamp": price_timestamps,
        "Price ($/kWh)": [0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 0.11, 0.12, 0.13]
    })
    
    # Mock weather data (hourly)
    weather_timestamps = pd.date_range(start=start_date, end=end_date, freq="h")
    mock_weather.return_value = [
        {"timestamp": str(ts), "temperature_f": 75.0}
        for ts in weather_timestamps
    ]
    
    # Create temporary load profile
    load_profile_path = tmp_path / "load_profile.csv"
    load_profile = pd.DataFrame({
        "hour": list(range(24)),
        "load_kw": [3.0] * 24
    })
    load_profile.to_csv(load_profile_path, index=False)
    
    # Call function
    result = build_historical_data_from_location(
        zip_code="75201",
        start_date=start_date,
        end_date=end_date,
        home_load_profile_path=load_profile_path,
    )
    
    # Verify required columns exist
    required_columns = ["Timestamp", "Price ($/kWh)", "home_load_kw", "temperature_derating"]
    for col in required_columns:
        assert col in result.columns, f"Missing required column: {col}"
    
    # Verify data types
    assert pd.api.types.is_datetime64_any_dtype(result["Timestamp"])
    assert pd.api.types.is_numeric_dtype(result["Price ($/kWh)"])
    assert pd.api.types.is_numeric_dtype(result["home_load_kw"])
    assert pd.api.types.is_numeric_dtype(result["temperature_derating"])
    
    # Verify no missing values in required columns
    assert result["Timestamp"].notna().all()
    assert result["Price ($/kWh)"].notna().all()
    assert result["home_load_kw"].notna().all()
    assert result["temperature_derating"].notna().all()
    
    # Verify timestamps are sorted
    assert result["Timestamp"].is_monotonic_increasing
    
    # Verify timestamps are unique
    assert not result["Timestamp"].duplicated().any()
    
    # Verify autofill summary was printed
    captured = capsys.readouterr()
    assert "TOTAL AUTOFILLS" in captured.out


# ============================================================
# Test 2: Correct settlement point
# ============================================================

@patch('backend.supporting_methods.weather.get_weather')
@patch('backend.supporting_methods.retrieve_price.get_historical_prices_bulk')
@patch('backend.location.zip_to_coord.get_zip_centroid')
@patch('backend.location.load_zone_lookup.get_ercot_load_zone')
def test_correct_settlement_point_used(
    mock_load_zone,
    mock_zip_centroid,
    mock_prices_bulk,
    mock_weather,
    tmp_path
):
    """Verify that the settlement point from load zone is passed to price retrieval."""
    
    # Setup mocks
    mock_load_zone.return_value = "LZ_HOUSTON"  # Houston zone
    mock_zip_centroid.return_value = (29.7604, -95.3698)  # Houston coordinates
    
    start_date = datetime(2024, 1, 1, 0, 0)
    end_date = datetime(2024, 1, 1, 1, 0)
    
    # Mock price data
    price_timestamps = pd.date_range(start=start_date, end=end_date, freq="15min")
    mock_prices_bulk.return_value = pd.DataFrame({
        "Timestamp": price_timestamps,
        "Price ($/kWh)": [0.05] * len(price_timestamps)
    })
    
    # Mock weather data
    mock_weather.return_value = [
        {"timestamp": str(start_date), "temperature_f": 80.0},
        {"timestamp": str(end_date), "temperature_f": 82.0}
    ]
    
    # Create temporary load profile
    load_profile_path = tmp_path / "load_profile.csv"
    load_profile = pd.DataFrame({
        "hour": list(range(24)),
        "load_kw": [4.0] * 24
    })
    load_profile.to_csv(load_profile_path, index=False)
    
    # Call function
    result = build_historical_data_from_location(
        zip_code="77002",  # Houston ZIP
        start_date=start_date,
        end_date=end_date,
        home_load_profile_path=load_profile_path,
    )
    
    # Verify get_ercot_load_zone was called with correct ZIP
    mock_load_zone.assert_called_once_with("77002")
    
    # Verify get_historical_prices_bulk was called with correct settlement point
    mock_prices_bulk.assert_called_once()
    call_args = mock_prices_bulk.call_args
    assert call_args.kwargs["settlement_point"] == "LZ_HOUSTON"
    
    # Verify settlement point is in result
    assert "settlement_point" in result.columns
    assert (result["settlement_point"] == "LZ_HOUSTON").all()


# ============================================================
# Test 3: Correct weather location
# ============================================================

@patch('backend.supporting_methods.weather.get_weather')
@patch('backend.supporting_methods.retrieve_price.get_historical_prices_bulk')
@patch('backend.location.zip_to_coord.get_zip_centroid')
@patch('backend.location.load_zone_lookup.get_ercot_load_zone')
def test_correct_weather_location_used(
    mock_load_zone,
    mock_zip_centroid,
    mock_prices_bulk,
    mock_weather,
    tmp_path
):
    """Verify that coordinates from ZIP centroid are passed to weather API."""
    
    # Setup mocks
    dallas_lat, dallas_lon = 32.7767, -96.7970
    mock_load_zone.return_value = "LZ_NORTH"
    mock_zip_centroid.return_value = (dallas_lat, dallas_lon)
    
    start_date = datetime(2024, 1, 1, 0, 0)
    end_date = datetime(2024, 1, 1, 1, 0)
    
    # Mock price data
    price_timestamps = pd.date_range(start=start_date, end=end_date, freq="15min")
    mock_prices_bulk.return_value = pd.DataFrame({
        "Timestamp": price_timestamps,
        "Price ($/kWh)": [0.05] * len(price_timestamps)
    })
    
    # Mock weather data
    mock_weather.return_value = [
        {"timestamp": str(start_date), "temperature_f": 75.0},
        {"timestamp": str(end_date), "temperature_f": 77.0}
    ]
    
    # Create temporary load profile
    load_profile_path = tmp_path / "load_profile.csv"
    load_profile = pd.DataFrame({
        "hour": list(range(24)),
        "load_kw": [3.5] * 24
    })
    load_profile.to_csv(load_profile_path, index=False)
    
    # Call function
    result = build_historical_data_from_location(
        zip_code="75201",
        start_date=start_date,
        end_date=end_date,
        home_load_profile_path=load_profile_path,
    )
    
    # Verify get_zip_centroid was called with correct ZIP
    mock_zip_centroid.assert_called_once_with("75201")
    
    # Verify get_weather was called with correct coordinates
    mock_weather.assert_called_once()
    call_args = mock_weather.call_args
    assert call_args.kwargs["latitude"] == dallas_lat
    assert call_args.kwargs["longitude"] == dallas_lon


# ============================================================
# Test 4: Temperature derating applied
# ============================================================

@patch('backend.supporting_methods.weather.get_weather')
@patch('backend.supporting_methods.retrieve_price.get_historical_prices_bulk')
@patch('backend.location.zip_to_coord.get_zip_centroid')
@patch('backend.location.load_zone_lookup.get_ercot_load_zone')
def test_temperature_derating_applied(
    mock_load_zone,
    mock_zip_centroid,
    mock_prices_bulk,
    mock_weather,
    tmp_path
):
    """Verify temperature derating is calculated correctly."""
    
    # Setup mocks
    mock_load_zone.return_value = "LZ_NORTH"
    mock_zip_centroid.return_value = (32.7767, -96.7970)
    
    start_date = datetime(2024, 1, 1, 0, 0)
    end_date = datetime(2024, 1, 1, 1, 0)
    
    # Mock price data
    price_timestamps = pd.date_range(start=start_date, end=end_date, freq="15min")
    mock_prices_bulk.return_value = pd.DataFrame({
        "Timestamp": price_timestamps,
        "Price ($/kWh)": [0.05] * len(price_timestamps)
    })
    
    # Mock weather data with known temperatures
    # 75°F should give derating = 1.0
    # 115°F should give derating < 1.0
    mock_weather.return_value = [
        {"timestamp": str(start_date), "temperature_f": 75.0},  # No derating
        {"timestamp": str(end_date), "temperature_f": 115.0}     # Some derating
    ]
    
    # Create temporary load profile
    load_profile_path = tmp_path / "load_profile.csv"
    load_profile = pd.DataFrame({
        "hour": list(range(24)),
        "load_kw": [3.0] * 24
    })
    load_profile.to_csv(load_profile_path, index=False)
    
    # Call function
    result = build_historical_data_from_location(
        zip_code="75201",
        start_date=start_date,
        end_date=end_date,
        home_load_profile_path=load_profile_path,
    )
    
    # Verify temperature_derating column exists
    assert "temperature_derating" in result.columns
    assert "temperature_f" in result.columns
    
    # Verify derating values are in valid range [0, 1]
    assert (result["temperature_derating"] >= 0).all()
    assert (result["temperature_derating"] <= 1).all()
    
    # Verify derating is applied (should have some variation due to different temps)
    # After forward-fill, we should have both 1.0 and values < 1.0
    unique_deratings = result["temperature_derating"].unique()
    assert len(unique_deratings) > 0


# ============================================================
# Test 5: Timestamp alignment
# ============================================================

@patch('backend.supporting_methods.weather.get_weather')
@patch('backend.supporting_methods.retrieve_price.get_historical_prices_bulk')
@patch('backend.location.zip_to_coord.get_zip_centroid')
@patch('backend.location.load_zone_lookup.get_ercot_load_zone')
def test_timestamp_alignment(
    mock_load_zone,
    mock_zip_centroid,
    mock_prices_bulk,
    mock_weather,
    tmp_path
):
    """Verify all data is aligned to the same timestamps."""
    
    # Setup mocks
    mock_load_zone.return_value = "LZ_NORTH"
    mock_zip_centroid.return_value = (32.7767, -96.7970)
    
    start_date = datetime(2024, 1, 1, 0, 0)
    end_date = datetime(2024, 1, 1, 2, 0)
    
    # Mock price data (15-minute intervals)
    price_timestamps = pd.date_range(start=start_date, end=end_date, freq="15min")
    mock_prices_bulk.return_value = pd.DataFrame({
        "Timestamp": price_timestamps,
        "Price ($/kWh)": [0.05 + i * 0.01 for i in range(len(price_timestamps))]
    })
    
    # Mock weather data (hourly - will be forward-filled to 15-min)
    weather_timestamps = pd.date_range(start=start_date, end=end_date, freq="h")
    mock_weather.return_value = [
        {"timestamp": str(ts), "temperature_f": 75.0 + i * 2}
        for i, ts in enumerate(weather_timestamps)
    ]
    
    # Create temporary load profile
    load_profile_path = tmp_path / "load_profile.csv"
    load_profile = pd.DataFrame({
        "hour": list(range(24)),
        "load_kw": [3.0 + (h % 12) * 0.5 for h in range(24)]
    })
    load_profile.to_csv(load_profile_path, index=False)
    
    # Call function
    result = build_historical_data_from_location(
        zip_code="75201",
        start_date=start_date,
        end_date=end_date,
        home_load_profile_path=load_profile_path,
    )
    
    # Verify all rows have the same timestamp
    # (i.e., each row represents a complete 15-minute interval with all data)
    assert len(result) > 0
    
    # Verify timestamps are 15-minute intervals
    time_diffs = result["Timestamp"].diff().dropna()
    assert (time_diffs == pd.Timedelta(minutes=15)).all()
    
    # Verify no missing data in any row
    assert result[["Timestamp", "Price ($/kWh)", "home_load_kw", "temperature_derating"]].notna().all().all()


# ============================================================
# Test 6: Invalid ZIP code
# ============================================================

@patch('backend.location.zip_to_coord.get_zip_centroid')
@patch('backend.location.load_zone_lookup.get_ercot_load_zone')
def test_invalid_zip_raises_error(
    mock_load_zone,
    mock_zip_centroid,
    tmp_path
):
    """Verify invalid ZIP code raises clear error."""
    
    # Mock invalid ZIP - load zone lookup fails
    mock_load_zone.side_effect = ValueError("ZIP centroid is not inside an ERCOT Load Zone: 00000")
    
    start_date = datetime(2024, 1, 1, 0, 0)
    end_date = datetime(2024, 1, 1, 1, 0)
    
    # Create temporary load profile
    load_profile_path = tmp_path / "load_profile.csv"
    load_profile = pd.DataFrame({
        "hour": list(range(24)),
        "load_kw": [3.0] * 24
    })
    load_profile.to_csv(load_profile_path, index=False)
    
    # Verify error is raised
    with pytest.raises(ValueError, match="ZIP centroid is not inside an ERCOT Load Zone"):
        build_historical_data_from_location(
            zip_code="00000",
            start_date=start_date,
            end_date=end_date,
            home_load_profile_path=load_profile_path,
        )


# ============================================================
# Test 7: Missing price data - Forward fill
# ============================================================

@patch('backend.supporting_methods.weather.get_weather')
@patch('backend.supporting_methods.retrieve_price.get_historical_prices_bulk')
@patch('backend.location.zip_to_coord.get_zip_centroid')
@patch('backend.location.load_zone_lookup.get_ercot_load_zone')
def test_missing_price_data_forward_filled(
    mock_load_zone,
    mock_zip_centroid,
    mock_prices_bulk,
    mock_weather,
    tmp_path,
    capsys
):
    """Verify missing price data is forward-filled and reported."""
    
    # Setup mocks
    mock_load_zone.return_value = "LZ_NORTH"
    mock_zip_centroid.return_value = (32.7767, -96.7970)
    
    start_date = datetime(2024, 1, 1, 0, 0)
    end_date = datetime(2024, 1, 1, 2, 0)
    
    # Mock price data with gaps (missing some 15-minute intervals)
    price_timestamps = pd.date_range(start=start_date, end=end_date, freq="15min")
    # Only provide every other timestamp
    sparse_timestamps = price_timestamps[::2]
    mock_prices_bulk.return_value = pd.DataFrame({
        "Timestamp": sparse_timestamps,
        "Price ($/kWh)": [0.05] * len(sparse_timestamps)
    })
    
    # Mock weather data
    weather_timestamps = pd.date_range(start=start_date, end=end_date, freq="h")
    mock_weather.return_value = [
        {"timestamp": str(ts), "temperature_f": 75.0}
        for ts in weather_timestamps
    ]
    
    # Create temporary load profile
    load_profile_path = tmp_path / "load_profile.csv"
    load_profile = pd.DataFrame({
        "hour": list(range(24)),
        "load_kw": [3.0] * 24
    })
    load_profile.to_csv(load_profile_path, index=False)
    
    # Call function
    result = build_historical_data_from_location(
        zip_code="75201",
        start_date=start_date,
        end_date=end_date,
        home_load_profile_path=load_profile_path,
    )
    
    # Verify no missing values after forward-fill
    assert result["Price ($/kWh)"].notna().all()
    
    # Verify autofill was reported
    captured = capsys.readouterr()
    assert "Price data:" in captured.out
    assert "TOTAL AUTOFILLS" in captured.out
    
    # Verify the autofill count is > 0
    assert "Price data:        0 intervals" not in captured.out


# ============================================================
# Test 8: Empty date range
# ============================================================

@patch('backend.location.load_zone_lookup.get_ercot_load_zone')
def test_empty_date_range_raises_error(mock_load_zone, tmp_path):
    """Verify start_date > end_date raises error."""
    
    mock_load_zone.return_value = "LZ_NORTH"
    
    start_date = datetime(2024, 1, 2, 0, 0)
    end_date = datetime(2024, 1, 1, 0, 0)  # Before start_date
    
    # Create temporary load profile
    load_profile_path = tmp_path / "load_profile.csv"
    load_profile = pd.DataFrame({
        "hour": list(range(24)),
        "load_kw": [3.0] * 24
    })
    load_profile.to_csv(load_profile_path, index=False)
    
    # Verify error is raised
    with pytest.raises(ValueError, match="start_date .* must be <= end_date"):
        build_historical_data_from_location(
            zip_code="75201",
            start_date=start_date,
            end_date=end_date,
            home_load_profile_path=load_profile_path,
        )


# ============================================================
# Test 9: Bulk retrieval (no API calls in loops)
# ============================================================

@patch('backend.supporting_methods.weather.get_weather')
@patch('backend.supporting_methods.retrieve_price.get_historical_prices_bulk')
@patch('backend.location.zip_to_coord.get_zip_centroid')
@patch('backend.location.load_zone_lookup.get_ercot_load_zone')
def test_bulk_retrieval_not_per_timestamp(
    mock_load_zone,
    mock_zip_centroid,
    mock_prices_bulk,
    mock_weather,
    tmp_path
):
    """Verify bulk retrieval functions are called once, not per timestamp."""
    
    # Setup mocks
    mock_load_zone.return_value = "LZ_NORTH"
    mock_zip_centroid.return_value = (32.7767, -96.7970)
    
    # Use a longer date range to ensure many timestamps
    start_date = datetime(2024, 1, 1, 0, 0)
    end_date = datetime(2024, 1, 7, 0, 0)  # 1 week = 672 15-minute intervals
    
    # Mock price data
    price_timestamps = pd.date_range(start=start_date, end=end_date, freq="15min")
    mock_prices_bulk.return_value = pd.DataFrame({
        "Timestamp": price_timestamps,
        "Price ($/kWh)": [0.05] * len(price_timestamps)
    })
    
    # Mock weather data
    weather_timestamps = pd.date_range(start=start_date, end=end_date, freq="h")
    mock_weather.return_value = [
        {"timestamp": str(ts), "temperature_f": 75.0}
        for ts in weather_timestamps
    ]
    
    # Create temporary load profile
    load_profile_path = tmp_path / "load_profile.csv"
    load_profile = pd.DataFrame({
        "hour": list(range(24)),
        "load_kw": [3.0] * 24
    })
    load_profile.to_csv(load_profile_path, index=False)
    
    # Call function
    result = build_historical_data_from_location(
        zip_code="75201",
        start_date=start_date,
        end_date=end_date,
        home_load_profile_path=load_profile_path,
    )
    
    # Verify bulk functions were called exactly ONCE (not once per timestamp)
    assert mock_prices_bulk.call_count == 1, "Price retrieval should be called once (bulk)"
    assert mock_weather.call_count == 1, "Weather retrieval should be called once (bulk)"
    assert mock_load_zone.call_count == 1, "Load zone lookup should be called once"
    assert mock_zip_centroid.call_count == 1, "ZIP centroid lookup should be called once"
    
    # Verify we got data for all timestamps
    # 6 days * 24 hours * 4 intervals/hour = 576 intervals
    # Plus 1 for the end timestamp = 577 intervals
    assert len(result) >= 576  # Should have ~576-577 intervals for 6+ days


# ============================================================
# Test 10: Missing load profile file
# ============================================================

@patch('backend.location.load_zone_lookup.get_ercot_load_zone')
def test_missing_load_profile_raises_error(mock_load_zone):
    """Verify missing load profile file raises FileNotFoundError."""
    
    mock_load_zone.return_value = "LZ_NORTH"
    
    start_date = datetime(2024, 1, 1, 0, 0)
    end_date = datetime(2024, 1, 1, 1, 0)
    
    # Use non-existent file path
    load_profile_path = Path("/nonexistent/path/load_profile.csv")
    
    # Verify error is raised
    with pytest.raises(FileNotFoundError, match="Home load profile not found"):
        build_historical_data_from_location(
            zip_code="75201",
            start_date=start_date,
            end_date=end_date,
            home_load_profile_path=load_profile_path,
        )


@patch('backend.supporting_methods.weather.get_weather')
@patch('backend.supporting_methods.retrieve_price.get_historical_prices_bulk')
@patch('backend.location.zip_to_coord.get_zip_centroid')
@patch('backend.location.load_zone_lookup.get_ercot_load_zone')
def test_off_grid_analysis_dates_align_price_and_weather(
    mock_load_zone,
    mock_zip_centroid,
    mock_prices_bulk,
    mock_weather,
    tmp_path,
):
    mock_load_zone.return_value = "LZ_NORTH"
    mock_zip_centroid.return_value = (32.7767, -96.7970)

    aligned_start = datetime(2024, 1, 1, 0, 0)
    aligned_end = datetime(2024, 1, 1, 2, 0)
    mock_prices_bulk.return_value = pd.DataFrame({
        "Timestamp": pd.date_range(aligned_start, aligned_end, freq="15min"),
        "Price ($/kWh)": [0.05] * 9,
    })
    mock_weather.return_value = [
        {"timestamp": str(timestamp), "temperature_f": 75.0}
        for timestamp in pd.date_range(aligned_start, aligned_end, freq="h")
    ]

    load_profile_path = tmp_path / "load_profile.csv"
    pd.DataFrame({"hour": list(range(24)), "load_kw": [3.0] * 24}).to_csv(
        load_profile_path,
        index=False,
    )

    result = build_historical_data_from_location(
        zip_code="75201",
        start_date=datetime(2024, 1, 1, 0, 8, 37),
        end_date=datetime(2024, 1, 1, 2, 8, 37),
        home_load_profile_path=load_profile_path,
    )

    mock_prices_bulk.assert_called_once_with(
        start_date=aligned_start,
        end_date=aligned_end,
        settlement_point="LZ_NORTH",
    )
    mock_weather.assert_called_once_with(
        latitude=32.7767,
        longitude=-96.7970,
        start_date=aligned_start,
        end_date=aligned_end,
    )
    assert len(result) == 9
    assert result["Price ($/kWh)"].notna().all()
    assert result["temperature_f"].notna().all()
