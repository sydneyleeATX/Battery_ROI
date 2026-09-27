"""
Home analysis helper function for battery savings calculation.

This module provides the core business logic for analyzing a customer's home
and calculating potential battery savings based on their location and energy usage.
"""

from datetime import datetime, timedelta
from pathlib import Path

from backend.location.load_zone_lookup import get_ercot_load_zone
from backend.location.zip_to_coord import get_zip_centroid
from backend.supporting_methods.cost_simulation import (
    build_historical_data_from_location,
    simulate_customer_savings,
)
from backend.supporting_methods.price_thresholds import calculate_price_thresholds
from backend.supporting_methods.retrieve_price import get_historical_prices_bulk
from backend.supporting_methods.battery_status import Battery


def analyze_home(
    zip_code: str,
    avg_annual_energy_kwh: float,
    start_date: datetime = None,
    end_date: datetime = None,
    service_limit_amps: float = 200,
    inverter_limit_kw: float = 11.0,
) -> dict:
    """
    Run the battery savings analysis for a customer's home.

    This function orchestrates the complete analysis workflow:
    1. Resolves customer location (ZIP → load zone → settlement point)
    2. Retrieves historical ERCOT prices and weather data
    3. Calculates location-specific price thresholds
    4. Simulates battery performance and economic savings

    Parameters
    ----------
    zip_code : str
        Customer ZIP code used to determine location-specific
        ERCOT pricing and weather data.
    avg_annual_energy_kwh : float
        Customer's average annual household electricity consumption in kWh/year.
        Used to scale the residential load profile to customer-specific usage.
    start_date : datetime, optional
        Start date for historical data. If None, uses 3 years ago.
    end_date : datetime, optional
        End date for historical data. If None, uses today.
    service_limit_amps : float, default=200
        Customer's electrical service panel amperage limit.
    inverter_limit_kw : float, default=11.0
        Battery inverter power limit in kW.

    Returns
    -------
    dict
        Complete analysis results containing:
        - location: ZIP code, load zone, settlement point, coordinates
        - customer: Annual energy usage
        - simulation: Battery performance and savings results
        - price_thresholds: Monthly charge/discharge thresholds

    Raises
    ------
    ValueError
        If ZIP code is invalid or location cannot be resolved.
    FileNotFoundError
        If required data files are missing.
    """

    # ---------------------------------------------------------
    # 1. Resolve customer location
    # ---------------------------------------------------------
    
    # Get ERCOT load zone and settlement point
    settlement_point = get_ercot_load_zone(zip_code)
    
    if settlement_point is None:
        raise ValueError(
            f"Unable to resolve ERCOT load zone for ZIP code {zip_code}. "
            "ZIP may be outside ERCOT territory or invalid."
        )
    
    # Get coordinates for weather data
    latitude, longitude = get_zip_centroid(zip_code)
    
    if latitude is None or longitude is None:
        raise ValueError(
            f"Unable to resolve coordinates for ZIP code {zip_code}. "
            "ZIP may be invalid."
        )
    
    # ---------------------------------------------------------
    # 2. Set date ranges
    # ---------------------------------------------------------
    
    # Default to most recent 1 year for simulation
    if end_date is None:
        end_date = datetime.now()
    
    if start_date is None:
        # modified for time considerations; ideally 3 years
        start_date = end_date - timedelta(days=1 * 365)
    
    # ---------------------------------------------------------
    # 3. Build historical data for this location
    # ---------------------------------------------------------
    
    historical_data = build_historical_data_from_location(
        zip_code=zip_code,
        start_date=start_date,
        end_date=end_date,
        avg_annual_energy_kwh=avg_annual_energy_kwh,
    )
    
    # ---------------------------------------------------------
    # 4. Calculate price thresholds from historical prices
    # ---------------------------------------------------------
    
    # Extract price data for threshold calculation
    # Use all 3 years of data to calculate monthly distributions
    historical_prices = historical_data[
        ["Timestamp", "Price ($/kWh)"]
    ].copy()
    
    price_thresholds = calculate_price_thresholds(
        historical_prices,
        low_percentile=0.25,
        high_percentile=0.75,
    )
    
    # ---------------------------------------------------------
    # 5. Create battery with default Tesla Powerwall 3 specs
    # ---------------------------------------------------------
    
    battery = Battery(
        capacity_kwh=39.2,
        nominal_power_kw=11,
        efficiency=0.90,
        minimum_soc=0.20,
        maximum_soc=1.00,
        initial_soc_kwh=39.2 * 0.5,  # Start at 50%
    )
    
    # ---------------------------------------------------------
    # 6. Run battery savings simulation
    # ---------------------------------------------------------
    
    simulation_result = simulate_customer_savings(
        battery=battery,
        historical_data=historical_data,
        price_thresholds=price_thresholds,
        service_limit_amps=service_limit_amps,
        inverter_limit_kw=inverter_limit_kw,
    )
    
    # ---------------------------------------------------------
    # 7. Return comprehensive analysis result
    # ---------------------------------------------------------
    
    return {
        "location": {
            "zip_code": str(zip_code),
            "settlement_point": settlement_point,
            "latitude": latitude,
            "longitude": longitude,
        },
        "customer": {
            "avg_annual_energy_kwh": avg_annual_energy_kwh,
            "service_limit_amps": service_limit_amps,
        },
        "battery": {
            "capacity_kwh": battery.capacity_kwh,
            "nominal_power_kw": battery.nominal_power_kw,
            "efficiency": battery.efficiency,
        },
        "price_thresholds": price_thresholds,
        "simulation": simulation_result,
        "metadata": {
            "analysis_date": datetime.now().isoformat(),
            "data_period_start": start_date.isoformat(),
            "data_period_end": end_date.isoformat(),
            "simulation_period_start": simulation_result["simulation_start"],
            "simulation_period_end": simulation_result["simulation_end"],
        },
    }
