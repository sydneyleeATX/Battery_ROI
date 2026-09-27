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


def test_customer_electricity_price_negative_raises_error():
    with pytest.raises(
        ValueError,
        match="ercot_price_kwh must be nonnegative"
    ):
        get_customer_electricity_price(-0.10)


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


def test_negative_ercot_price_raises_error():
    with pytest.raises(
        ValueError,
        match="ercot_price_kwh must be nonnegative"
    ):
        calculate_interval_electricity_cost(
            home_load_kw=4.0,
            action="idle",
            battery_energy_kwh=0.0,
            ercot_price_kwh=-0.10,
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