import pytest
import pandas as pd

from backend.supporting_methods.cost_simulation import (
    get_customer_electricity_price,
    calculate_interval_electricity_cost,
    simulate_customer_savings,
)


# ============================================================
# get_customer_electricity_price()
# ============================================================

def test_customer_electricity_price_applies_multiplier():
    result = get_customer_electricity_price(0.10)

    assert result == pytest.approx(0.30)


def test_customer_electricity_price_zero():
    result = get_customer_electricity_price(0.0)

    assert result == pytest.approx(0.0)


def test_customer_electricity_price_negative_allowed():
    """ERCOT prices can be negative during oversupply periods."""
    result = get_customer_electricity_price(-0.10)
    
    # Negative wholesale price should result in negative retail price
    assert result == pytest.approx(-0.30)


# ============================================================
# calculate_interval_electricity_cost()
# ============================================================

def test_idle_cost():
    result = calculate_interval_electricity_cost(
        home_load_kw=4.0,
        action="idle",
        battery_energy_kwh=0.0,
        ercot_price_kwh=0.10,
    )

    # 4 kW × 0.25 hours = 1 kWh
    assert result["home_energy_kwh"] == pytest.approx(1.0)

    # Idle means all household energy comes from grid
    assert result["grid_energy_kwh"] == pytest.approx(1.0)

    # $0.10/kWh × 3 = $0.30/kWh
    assert result["customer_price_kwh"] == pytest.approx(0.30)

    # 1 kWh × $0.30 = $0.30
    assert result["electricity_cost"] == pytest.approx(0.30)


def test_charge_cost():
    result = calculate_interval_electricity_cost(
        home_load_kw=4.0,
        action="charge",
        battery_energy_kwh=2.0,
        ercot_price_kwh=0.10,
    )

    # Household uses 1 kWh
    assert result["home_energy_kwh"] == pytest.approx(1.0)

    # Grid supplies household + battery
    assert result["grid_energy_kwh"] == pytest.approx(3.0)

    # 3 kWh × $0.30/kWh
    assert result["electricity_cost"] == pytest.approx(0.90)


def test_discharge_cost():
    result = calculate_interval_electricity_cost(
        home_load_kw=4.0,
        action="discharge",
        battery_energy_kwh=0.5,
        ercot_price_kwh=0.10,
    )

    # Household uses 1 kWh
    assert result["home_energy_kwh"] == pytest.approx(1.0)

    # Battery supplies 0.5 kWh, grid supplies remaining 0.5
    assert result["grid_energy_kwh"] == pytest.approx(0.5)

    # 0.5 kWh × $0.30/kWh
    assert result["electricity_cost"] == pytest.approx(0.15)


def test_discharge_cannot_send_excess_energy_to_grid():
    result = calculate_interval_electricity_cost(
        home_load_kw=1.0,
        action="discharge",
        battery_energy_kwh=5.0,
        ercot_price_kwh=0.10,
    )

    # 1 kWh household demand is completely covered.
    # Excess battery energy is not exported.
    assert result["grid_energy_kwh"] == pytest.approx(0.0)

    assert result["electricity_cost"] == pytest.approx(0.0)


def test_custom_interval_length():
    result = calculate_interval_electricity_cost(
        home_load_kw=4.0,
        action="idle",
        battery_energy_kwh=0.0,
        ercot_price_kwh=0.10,
        interval_hours=0.5,
    )

    # 4 kW × 0.5 hours = 2 kWh
    assert result["home_energy_kwh"] == pytest.approx(2.0)

    assert result["grid_energy_kwh"] == pytest.approx(2.0)

    # 2 × $0.30
    assert result["electricity_cost"] == pytest.approx(0.60)


# ============================================================
# calculate_interval_electricity_cost() validation
# ============================================================

def test_negative_home_load_raises_error():
    with pytest.raises(
        ValueError,
        match="home_load_kw must be nonnegative"
    ):
        calculate_interval_electricity_cost(
            home_load_kw=-1.0,
            action="idle",
            battery_energy_kwh=0.0,
            ercot_price_kwh=0.10,
        )


def test_negative_battery_energy_raises_error():
    with pytest.raises(
        ValueError,
        match="battery_energy_kwh must be nonnegative"
    ):
        calculate_interval_electricity_cost(
            home_load_kw=4.0,
            action="charge",
            battery_energy_kwh=-1.0,
            ercot_price_kwh=0.10,
        )


def test_zero_interval_hours_raises_error():
    with pytest.raises(
        ValueError,
        match="interval_hours must be positive"
    ):
        calculate_interval_electricity_cost(
            home_load_kw=4.0,
            action="idle",
            battery_energy_kwh=0.0,
            ercot_price_kwh=0.10,
            interval_hours=0.0,
        )


def test_negative_interval_hours_raises_error():
    with pytest.raises(
        ValueError,
        match="interval_hours must be positive"
    ):
        calculate_interval_electricity_cost(
            home_load_kw=4.0,
            action="idle",
            battery_energy_kwh=0.0,
            ercot_price_kwh=0.10,
            interval_hours=-0.25,
        )


def test_invalid_action_raises_error():
    with pytest.raises(
        ValueError,
        match="action must be 'charge', 'discharge', or 'idle'"
    ):
        calculate_interval_electricity_cost(
            home_load_kw=4.0,
            action="invalid",
            battery_energy_kwh=0.0,
            ercot_price_kwh=0.10,
        )


# ============================================================
# simulate_customer_savings()
# ============================================================

def test_simulate_customer_savings_missing_columns_raises_error():
    data = pd.DataFrame({
        "Timestamp": pd.date_range(
            "2025-01-01",
            periods=4,
            freq="15min"
        ),
        "Price ($/kWh)": [0.05, 0.06, 0.07, 0.08],
    })

    with pytest.raises(
        ValueError,
        match="Missing required columns"
    ):
        simulate_customer_savings(
            battery=None,
            historical_data=data,
            price_thresholds=None,
            service_limit_amps=200,
            inverter_limit_kw=11,
        )


def test_simulate_customer_savings_invalid_interval_raises_error():
    data = pd.DataFrame({
        "Timestamp": pd.date_range(
            "2025-01-01",
            periods=4,
            freq="15min"
        ),
        "Price ($/kWh)": [0.05, 0.06, 0.07, 0.08],
        "home_load_kw": [4.0, 4.0, 4.0, 4.0],
        "temperature_derating": [1.0, 1.0, 1.0, 1.0],
    })

    with pytest.raises(
        ValueError,
        match="interval_hours must be positive"
    ):
        simulate_customer_savings(
            battery=None,
            historical_data=data,
            price_thresholds=None,
            service_limit_amps=200,
            inverter_limit_kw=11,
            interval_hours=0,
        )


# ============================================================
# Negative price handling tests
# ============================================================

def test_negative_ercot_price_allowed():
    """Negative ERCOT prices are allowed (oversupply periods)."""
    result = calculate_interval_electricity_cost(
        home_load_kw=4.0,
        action="idle",
        battery_energy_kwh=0.0,
        ercot_price_kwh=-0.10,
    )
    
    # Negative wholesale price results in negative retail price
    assert result["customer_price_kwh"] == pytest.approx(-0.30)
    
    # Negative cost means customer is paid to consume
    assert result["electricity_cost"] == pytest.approx(-0.30)


def test_charging_during_negative_prices():
    """Charging during negative prices should result in negative cost (paid to charge)."""
    result = calculate_interval_electricity_cost(
        home_load_kw=2.0,
        action="charge",
        battery_energy_kwh=2.0,
        ercot_price_kwh=-0.05,
    )
    
    # Home uses 0.5 kWh, battery charges 2 kWh = 2.5 kWh total from grid
    assert result["grid_energy_kwh"] == pytest.approx(2.5)
    
    # Negative price means customer is paid
    assert result["customer_price_kwh"] == pytest.approx(-0.15)
    assert result["electricity_cost"] == pytest.approx(-0.375)


def test_discharging_during_negative_prices():
    """Discharging during negative prices reduces the benefit."""
    result = calculate_interval_electricity_cost(
        home_load_kw=4.0,
        action="discharge",
        battery_energy_kwh=0.5,
        ercot_price_kwh=-0.10,
    )
    
    # Battery supplies 0.5 kWh, grid supplies 0.5 kWh
    assert result["grid_energy_kwh"] == pytest.approx(0.5)
    
    # Still negative cost, but less negative than if we took more from grid
    assert result["electricity_cost"] == pytest.approx(-0.15)


# ============================================================
# Edge case tests
# ============================================================

def test_zero_home_load():
    """Zero home load should result in zero cost for idle."""
    result = calculate_interval_electricity_cost(
        home_load_kw=0.0,
        action="idle",
        battery_energy_kwh=0.0,
        ercot_price_kwh=0.10,
    )
    
    assert result["home_energy_kwh"] == pytest.approx(0.0)
    assert result["grid_energy_kwh"] == pytest.approx(0.0)
    assert result["electricity_cost"] == pytest.approx(0.0)


def test_zero_battery_energy_charge_action():
    """Charging with zero battery energy should be same as idle."""
    result = calculate_interval_electricity_cost(
        home_load_kw=4.0,
        action="charge",
        battery_energy_kwh=0.0,
        ercot_price_kwh=0.10,
    )
    
    # Same as idle - only home load from grid
    assert result["grid_energy_kwh"] == pytest.approx(1.0)
    assert result["electricity_cost"] == pytest.approx(0.30)


def test_zero_battery_energy_discharge_action():
    """Discharging with zero battery energy should be same as idle."""
    result = calculate_interval_electricity_cost(
        home_load_kw=4.0,
        action="discharge",
        battery_energy_kwh=0.0,
        ercot_price_kwh=0.10,
    )
    
    # Same as idle - all home load from grid
    assert result["grid_energy_kwh"] == pytest.approx(1.0)
    assert result["electricity_cost"] == pytest.approx(0.30)


def test_very_high_ercot_price():
    """Very high ERCOT prices should be handled correctly."""
    result = calculate_interval_electricity_cost(
        home_load_kw=4.0,
        action="idle",
        battery_energy_kwh=0.0,
        ercot_price_kwh=9.00,  # $9000/MWh (ERCOT cap is $5000/MWh but testing edge case)
    )
    
    # Customer price = 9.00 * 3 = 27.00
    assert result["customer_price_kwh"] == pytest.approx(27.00)
    
    # 1 kWh * $27 = $27
    assert result["electricity_cost"] == pytest.approx(27.00)


# ============================================================
# Data validation tests
# ============================================================

def test_simulate_customer_savings_empty_data_raises_error():
    """Empty historical data should raise error."""
    data = pd.DataFrame({
        "Timestamp": pd.date_range("2025-01-01", periods=100, freq="15min"),
        "Price ($/kWh)": [0.05] * 100,
        "home_load_kw": [4.0] * 100,
        "temperature_derating": [1.0] * 100,
    })
    
    # Filter to empty dataset
    data = data[data["Timestamp"] > pd.Timestamp("2026-01-01")]
    
    from backend.supporting_methods.battery_status import Battery
    
    with pytest.raises(ValueError, match="No historical data available"):
        simulate_customer_savings(
            battery=Battery(),
            historical_data=data,
            price_thresholds={1: {"charge": 0.05, "discharge": 0.10}},
            service_limit_amps=200,
            inverter_limit_kw=11,
        )


def test_simulate_customer_savings_with_complete_data():
    """Verify simulation works with complete valid data."""
    from backend.supporting_methods.battery_status import Battery
    
    # Create one year of data
    data = pd.DataFrame({
        "Timestamp": pd.date_range("2024-01-01", periods=35040, freq="15min"),  # 1 year
        "Price ($/kWh)": [0.05] * 35040,
        "home_load_kw": [3.0] * 35040,
        "temperature_derating": [1.0] * 35040,
    })
    
    price_thresholds = {i: {"charge": 0.04, "discharge": 0.06} for i in range(1, 13)}
    
    results = simulate_customer_savings(
        battery=Battery(),
        historical_data=data,
        price_thresholds=price_thresholds,
        service_limit_amps=200,
        inverter_limit_kw=11,
    )
    
    # Verify result structure
    assert "total_savings" in results
    assert "charging_cost" in results
    assert "discharging_value" in results
    assert "net_economic_benefit" in results
    assert "charge_events" in results
    assert "discharge_events" in results
    assert "starting_soc_kwh" in results
    assert "ending_soc_kwh" in results
    assert "backup_reserve_violations" in results
    
    # Verify numeric results
    assert isinstance(results["total_savings"], (int, float))
    assert isinstance(results["charge_events"], int)
    assert isinstance(results["discharge_events"], int)
    assert results["charge_events"] >= 0
    assert results["discharge_events"] >= 0
    assert results["backup_reserve_violations"] >= 0