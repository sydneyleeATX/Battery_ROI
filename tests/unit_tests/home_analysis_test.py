"""
Unit tests for the home analysis API helper function.
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from backend.api.home_analysis import analyze_home


# ============================================================
# Test analyze_home function
# ============================================================

@patch('backend.api.home_analysis.simulate_customer_savings')
@patch('backend.api.home_analysis.calculate_price_thresholds')
@patch('backend.api.home_analysis.build_historical_data_from_location')
@patch('backend.api.home_analysis.get_zip_centroid')
@patch('backend.api.home_analysis.get_ercot_load_zone')
def test_analyze_home_complete_flow(
    mock_load_zone,
    mock_zip_centroid,
    mock_build_data,
    mock_calc_thresholds,
    mock_simulate,
):
    """Test complete analyze_home flow with mocked dependencies."""
    
    # Setup mocks
    mock_load_zone.return_value = "LZ_NORTH"
    mock_zip_centroid.return_value = (32.7904, -96.8044)
    
    mock_build_data.return_value = MagicMock(
        __getitem__=lambda self, key: MagicMock()
    )
    
    mock_calc_thresholds.return_value = {
        1: {"charge": 0.05, "discharge": 0.10},
        2: {"charge": 0.05, "discharge": 0.10},
    }
    
    mock_simulate.return_value = {
        "total_savings": 500.0,
        "baseline_cost": 1500.0,
        "battery_cost": 1000.0,
        "charge_events": 100,
        "discharge_events": 50,
        "simulation_start": "2024-01-01",
        "simulation_end": "2024-12-31",
    }
    
    # Run analysis
    result = analyze_home(
        zip_code="75201",
        avg_annual_energy_kwh=12000,
    )
    
    # Verify result structure
    assert "location" in result
    assert "customer" in result
    assert "battery" in result
    assert "price_thresholds" in result
    assert "simulation" in result
    assert "metadata" in result
    
    # Verify location data
    assert result["location"]["zip_code"] == "75201"
    assert result["location"]["settlement_point"] == "LZ_NORTH"
    assert result["location"]["latitude"] == 32.7904
    assert result["location"]["longitude"] == -96.8044
    
    # Verify customer data
    assert result["customer"]["avg_annual_energy_kwh"] == 12000
    assert result["customer"]["service_limit_amps"] == 200
    
    # Verify battery data
    assert result["battery"]["capacity_kwh"] == 39.2
    assert result["battery"]["nominal_power_kw"] == 11
    assert result["battery"]["efficiency"] == 0.90
    
    # Verify simulation results
    assert result["simulation"]["total_savings"] == 500.0
    
    # Verify function calls
    mock_load_zone.assert_called_once_with("75201")
    mock_zip_centroid.assert_called_once_with("75201")
    mock_build_data.assert_called_once()
    mock_calc_thresholds.assert_called_once()
    mock_simulate.assert_called_once()


@patch('backend.api.home_analysis.get_ercot_load_zone')
def test_analyze_home_invalid_zip_raises_error(mock_load_zone):
    """Test that invalid ZIP code raises ValueError."""
    
    mock_load_zone.return_value = None
    
    with pytest.raises(ValueError, match="Unable to resolve ERCOT load zone"):
        analyze_home(
            zip_code="00000",
            avg_annual_energy_kwh=10000,
        )


@patch('backend.api.home_analysis.get_zip_centroid')
@patch('backend.api.home_analysis.get_ercot_load_zone')
def test_analyze_home_invalid_coordinates_raises_error(
    mock_load_zone,
    mock_zip_centroid,
):
    """Test that invalid coordinates raise ValueError."""
    
    mock_load_zone.return_value = "LZ_NORTH"
    mock_zip_centroid.return_value = (None, None)
    
    with pytest.raises(ValueError, match="Unable to resolve coordinates"):
        analyze_home(
            zip_code="75201",
            avg_annual_energy_kwh=10000,
        )


@patch('backend.api.home_analysis.simulate_customer_savings')
@patch('backend.api.home_analysis.calculate_price_thresholds')
@patch('backend.api.home_analysis.build_historical_data_from_location')
@patch('backend.api.home_analysis.get_zip_centroid')
@patch('backend.api.home_analysis.get_ercot_load_zone')
def test_analyze_home_uses_custom_parameters(
    mock_load_zone,
    mock_zip_centroid,
    mock_build_data,
    mock_calc_thresholds,
    mock_simulate,
):
    """Test that custom service limits are passed through correctly."""
    
    # Setup mocks
    mock_load_zone.return_value = "LZ_HOUSTON"
    mock_zip_centroid.return_value = (29.7604, -95.3698)
    mock_build_data.return_value = MagicMock(__getitem__=lambda self, key: MagicMock())
    mock_calc_thresholds.return_value = {}
    mock_simulate.return_value = {
        "total_savings": 0,
        "simulation_start": "2024-01-01",
        "simulation_end": "2024-12-31",
    }
    
    # Run with custom parameters
    result = analyze_home(
        zip_code="77001",
        avg_annual_energy_kwh=15000,
        service_limit_amps=400,
        inverter_limit_kw=15.0,
    )
    
    # Verify custom parameters are in result
    assert result["customer"]["avg_annual_energy_kwh"] == 15000
    assert result["customer"]["service_limit_amps"] == 400
    
    # Verify they were passed to simulation
    call_kwargs = mock_simulate.call_args.kwargs
    assert call_kwargs["service_limit_amps"] == 400
    assert call_kwargs["inverter_limit_kw"] == 15.0


@patch('backend.api.home_analysis.simulate_customer_savings')
@patch('backend.api.home_analysis.calculate_price_thresholds')
@patch('backend.api.home_analysis.build_historical_data_from_location')
@patch('backend.api.home_analysis.get_zip_centroid')
@patch('backend.api.home_analysis.get_ercot_load_zone')
def test_analyze_home_passes_annual_energy_to_builder(
    mock_load_zone,
    mock_zip_centroid,
    mock_build_data,
    mock_calc_thresholds,
    mock_simulate,
):
    """Test that avg_annual_energy_kwh is passed to build_historical_data_from_location."""
    
    # Setup mocks
    mock_load_zone.return_value = "LZ_NORTH"
    mock_zip_centroid.return_value = (32.7904, -96.8044)
    mock_build_data.return_value = MagicMock(__getitem__=lambda self, key: MagicMock())
    mock_calc_thresholds.return_value = {}
    mock_simulate.return_value = {
        "total_savings": 0,
        "simulation_start": "2024-01-01",
        "simulation_end": "2024-12-31",
    }
    
    # Run with specific annual energy
    analyze_home(
        zip_code="75201",
        avg_annual_energy_kwh=8500,
    )
    
    # Verify avg_annual_energy_kwh was passed to builder
    call_kwargs = mock_build_data.call_args.kwargs
    assert call_kwargs["avg_annual_energy_kwh"] == 8500
