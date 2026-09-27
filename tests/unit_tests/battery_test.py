import pytest
import pandas as pd

from backend.supporting_methods.battery_status import Battery
from backend.supporting_methods.price_thresholds import calculate_price_thresholds

# ============================================================
# Battery Initialization
# ============================================================

def test_battery_initializes_with_default_specs():
    battery = Battery()

    assert battery.capacity_kwh == 39.2
    assert battery.nominal_power_kw == 11
    assert battery.efficiency == 0.90
    assert battery.minimum_soc_kwh == pytest.approx(7.84)
    assert battery.maximum_soc_kwh == pytest.approx(39.2)
    assert battery.soc_kwh == pytest.approx(19.6)


# ============================================================
# Available Energy
# ============================================================

def test_get_available_discharge_kwh():
    battery = Battery()

    # Battery at 50% charge: can discharge down to minimum SOC
    # Accounts for efficiency: (19.6 - 7.84) * 0.90
    expected = (19.6 - 7.84) * 0.90

    assert battery.get_available_discharge_kwh() == pytest.approx(expected)


def test_get_available_charge_kwh():
    battery = Battery()

    # Battery at 50% charge: can charge up to maximum SOC
    expected = 39.2 - 19.6

    assert battery.get_available_charge_kwh() == pytest.approx(expected)


def test_available_energy_after_discharge():
    battery = Battery()

    battery.update_soc(
        energy_charged_kwh=0,
        energy_discharged_kwh=5,
        charge_efficiency=0.90,
    )

    expected_soc = 19.6 - (5 / 0.90)

    assert battery.soc_kwh == pytest.approx(expected_soc)

    assert battery.get_available_discharge_kwh() == pytest.approx(
        (expected_soc - 7.84) * 0.90
    )

    assert battery.get_available_charge_kwh() == pytest.approx(
        39.2 - expected_soc
    )


# ============================================================
# SOC Updates
# ============================================================

def test_update_soc_discharge():
    battery = Battery()

    battery.update_soc(
        energy_charged_kwh=0,
        energy_discharged_kwh=5,
        charge_efficiency=0.90,
    )

    expected_soc = 19.6 - (5 / 0.90)

    assert battery.soc_kwh == pytest.approx(expected_soc)


def test_update_soc_charge():
    battery = Battery()

    # Start with some room in the battery
    battery.soc_kwh = 20.0

    battery.update_soc(
        energy_charged_kwh=10,
        energy_discharged_kwh=0,
        charge_efficiency=0.90,
    )

    expected_soc = 20.0 + (10 * 0.90)

    assert battery.soc_kwh == pytest.approx(expected_soc)


def test_update_soc_charge_and_discharge():
    battery = Battery()

    battery.soc_kwh = 20.0

    battery.update_soc(
        energy_charged_kwh=10,
        energy_discharged_kwh=5,
        charge_efficiency=0.90,
    )

    expected_soc = (
        20.0
        + (10 * 0.90)
        - (5 / 0.90)
    )

    assert battery.soc_kwh == pytest.approx(expected_soc)


def test_update_soc_rejects_negative_charge():
    battery = Battery()

    with pytest.raises(ValueError):
        battery.update_soc(
            energy_charged_kwh=-1,
            energy_discharged_kwh=0,
            charge_efficiency=0.90,
        )


def test_update_soc_rejects_negative_discharge():
    battery = Battery()

    with pytest.raises(ValueError):
        battery.update_soc(
            energy_charged_kwh=0,
            energy_discharged_kwh=-1,
            charge_efficiency=0.90,
        )


def test_update_soc_rejects_zero_efficiency():
    battery = Battery()

    with pytest.raises(ValueError):
        battery.update_soc(
            energy_charged_kwh=1,
            energy_discharged_kwh=0,
            charge_efficiency=0,
        )


def test_update_soc_rejects_efficiency_above_one():
    battery = Battery()

    with pytest.raises(ValueError):
        battery.update_soc(
            energy_charged_kwh=1,
            energy_discharged_kwh=0,
            charge_efficiency=1.1,
        )


# ============================================================
# Home Electrical Service
# ============================================================

def test_get_home_service_limit_200_amps():
    battery = Battery()

    result = battery.get_home_service_limit(
        service_amps=200
    )

    # 200 A * 240 V / 1000 = 48 kW
    assert result == pytest.approx(48.0)


def test_get_home_service_limit_400_amps():
    battery = Battery()

    result = battery.get_home_service_limit(
        service_amps=400
    )

    # 400 A * 240 V / 1000 = 96 kW
    assert result == pytest.approx(96.0)


def test_get_home_service_limit_custom_voltage():
    battery = Battery()

    result = battery.get_home_service_limit(
        service_amps=100,
        service_voltage=120,
    )

    assert result == pytest.approx(12.0)


# ============================================================
# Effective Discharge Power
# ============================================================

def test_effective_discharge_power_at_full_temperature():
    battery = Battery()

    assert battery.get_effective_discharge_power_kw(
        1.0
    ) == pytest.approx(11.0)


def test_effective_discharge_power_with_temperature_derating():
    battery = Battery()

    assert battery.get_effective_discharge_power_kw(
        0.8
    ) == pytest.approx(8.8)


def test_effective_discharge_power_rejects_zero_derating():
    battery = Battery()

    with pytest.raises(ValueError):
        battery.get_effective_discharge_power_kw(0.0)


def test_effective_discharge_power_rejects_derating_above_one():
    battery = Battery()

    with pytest.raises(ValueError):
        battery.get_effective_discharge_power_kw(1.1)


# ============================================================
# Effective Charge Power
# ============================================================

def test_effective_charge_power_limited_by_battery_temperature():
    battery = Battery()

    # 200A * 240V = 48kW service
    # 48 - 5 = 43kW available at the home
    # Battery temperature-limited power = 11kW
    # Therefore battery should be limited to 11kW.
    result = battery.get_effective_charge_power_kw(
        temperature_derating=1.0,
        service_limit_amps=200,
        household_load_kw=5.0,
    )

    assert result == pytest.approx(11.0)


def test_effective_charge_power_limited_by_home_load():
    battery = Battery()

    # 40A * 240V = 9.6kW service capacity
    # 9.6 - 5 = 4.6kW available for charging
    # Battery itself could provide 11kW
    # Therefore home capacity limits charging to 4.6kW.
    result = battery.get_effective_charge_power_kw(
        temperature_derating=1.0,
        service_limit_amps=40,
        household_load_kw=5.0,
    )

    assert result == pytest.approx(4.6)


def test_effective_charge_power_with_temperature_and_home_limit():
    battery = Battery()

    # Battery temperature limit = 11 * 0.8 = 8.8kW
    # Home available capacity = 48 - 5 = 43kW
    # Temperature is therefore the limiting factor.
    result = battery.get_effective_charge_power_kw(
        temperature_derating=0.8,
        service_limit_amps=200,
        household_load_kw=5.0,
    )

    assert result == pytest.approx(8.8)


def test_effective_charge_power_zero_home_capacity():
    battery = Battery()

    # 40A * 240V = 9.6kW
    # Household load = 9.6kW
    # No capacity remains for battery charging.
    result = battery.get_effective_charge_power_kw(
        temperature_derating=1.0,
        service_limit_amps=40,
        household_load_kw=9.6,
    )

    assert result == pytest.approx(0.0)


def test_effective_charge_power_cannot_be_negative():
    battery = Battery()

    # Household load exceeds total service capacity.
    # Function should floor available home power at zero.
    result = battery.get_effective_charge_power_kw(
        temperature_derating=1.0,
        service_limit_amps=40,
        household_load_kw=20.0,
    )

    assert result == pytest.approx(0.0)


def test_effective_charge_power_rejects_invalid_service_limit():
    battery = Battery()

    with pytest.raises(ValueError):
        battery.get_effective_charge_power_kw(
            temperature_derating=1.0,
            service_limit_amps=0,
            household_load_kw=5.0,
        )


def test_effective_charge_power_rejects_negative_household_load():
    battery = Battery()

    with pytest.raises(ValueError):
        battery.get_effective_charge_power_kw(
            temperature_derating=1.0,
            service_limit_amps=200,
            household_load_kw=-1.0,
        )


def test_effective_charge_power_rejects_invalid_voltage():
    battery = Battery()

    with pytest.raises(ValueError):
        battery.get_effective_charge_power_kw(
            temperature_derating=1.0,
            service_limit_amps=200,
            household_load_kw=5.0,
            voltage=0,
        )


def test_effective_charge_power_rejects_invalid_temperature_derating():
    battery = Battery()

    with pytest.raises(ValueError):
        battery.get_effective_charge_power_kw(
            temperature_derating=0.0,
            service_limit_amps=200,
            household_load_kw=5.0,
        )

    with pytest.raises(ValueError):
        battery.get_effective_charge_power_kw(
            temperature_derating=1.1,
            service_limit_amps=200,
            household_load_kw=5.0,
        )


# ============================================================
# Combined Effective Battery Power
# ============================================================

def test_effective_battery_power_all_limits_at_11kw():
    battery = Battery()

    result = battery.get_effective_battery_power(
        temperature_derating=1.0,
        service_limit_amps=200,
        household_load_kw=5.0,
        inverter_limit_kw=11.0,
    )

    assert result["max_charge_kw"] == pytest.approx(11.0)
    assert result["max_discharge_kw"] == pytest.approx(11.0)


def test_effective_battery_power_temperature_limits_both_directions():
    battery = Battery()

    result = battery.get_effective_battery_power(
        temperature_derating=0.8,
        service_limit_amps=200,
        household_load_kw=5.0,
        inverter_limit_kw=11.0,
    )

    # Temperature-limited battery power = 11 * 0.8 = 8.8kW
    assert result["max_charge_kw"] == pytest.approx(8.8)
    assert result["max_discharge_kw"] == pytest.approx(8.8)


def test_effective_battery_power_inverter_limits_both_directions():
    battery = Battery()

    result = battery.get_effective_battery_power(
        temperature_derating=1.0,
        service_limit_amps=200,
        household_load_kw=5.0,
        inverter_limit_kw=7.0,
    )

    assert result["max_charge_kw"] == pytest.approx(7.0)
    assert result["max_discharge_kw"] == pytest.approx(7.0)


def test_effective_battery_power_home_limits_charge_only():
    battery = Battery()

    result = battery.get_effective_battery_power(
        temperature_derating=1.0,
        service_limit_amps=40,
        household_load_kw=5.0,
        inverter_limit_kw=11.0,
    )

    # Home capacity:
    # 40A * 240V / 1000 = 9.6kW
    # 9.6 - 5 = 4.6kW available for charging
    #
    # Discharge is not constrained by household load.
    assert result["max_charge_kw"] == pytest.approx(4.6)
    assert result["max_discharge_kw"] == pytest.approx(11.0)


def test_effective_battery_power_inverter_limits_charge_and_discharge():
    battery = Battery()

    result = battery.get_effective_battery_power(
        temperature_derating=0.9,
        service_limit_amps=200,
        household_load_kw=10.0,
        inverter_limit_kw=5.0,
    )

    # Temperature-limited battery power = 11 * 0.9 = 9.9kW
    # Inverter limits both directions to 5kW.
    assert result["max_charge_kw"] == pytest.approx(5.0)
    assert result["max_discharge_kw"] == pytest.approx(5.0)


# ============================================================
# Economic Dispatch Decisions
# ============================================================

def test_should_charge_when_price_below_threshold():
    from datetime import datetime
    
    battery = Battery()
    
    price_thresholds = {
        1: {"charge": 0.05, "discharge": 0.12},
    }
    
    jan_time = datetime(2024, 1, 15, 12, 0)
    
    # Price below threshold, battery not full
    result = battery.should_charge(
        price_kwh=0.04,
        time=jan_time,
        price_thresholds=price_thresholds
    )
    
    assert result is True


def test_should_not_charge_when_price_above_threshold():
    from datetime import datetime
    
    battery = Battery()
    
    price_thresholds = {
        1: {"charge": 0.05, "discharge": 0.12},
    }
    
    jan_time = datetime(2024, 1, 15, 12, 0)
    
    # Price above threshold
    result = battery.should_charge(
        price_kwh=0.08,
        time=jan_time,
        price_thresholds=price_thresholds
    )
    
    assert result is False


def test_should_not_charge_when_battery_full():
    from datetime import datetime
    
    battery = Battery()
    battery.soc_kwh = battery.maximum_soc_kwh
    
    price_thresholds = {
        1: {"charge": 0.05, "discharge": 0.12},
    }
    
    jan_time = datetime(2024, 1, 15, 12, 0)
    
    # Price below threshold but battery is full
    result = battery.should_charge(
        price_kwh=0.04,
        time=jan_time,
        price_thresholds=price_thresholds
    )
    
    assert result is False


def test_should_discharge_when_price_above_threshold():
    from datetime import datetime
    
    battery = Battery()
    
    price_thresholds = {
        1: {"charge": 0.05, "discharge": 0.12},
    }
    
    jan_time = datetime(2024, 1, 15, 12, 0)
    
    # Price above threshold, battery has energy above minimum
    result = battery.should_discharge(
        price_kwh=0.15,
        time=jan_time,
        price_thresholds=price_thresholds
    )
    
    assert result is True


def test_should_not_discharge_when_price_below_threshold():
    from datetime import datetime
    
    battery = Battery()
    
    price_thresholds = {
        1: {"charge": 0.05, "discharge": 0.12},
    }
    
    jan_time = datetime(2024, 1, 15, 12, 0)
    
    # Price below threshold
    result = battery.should_discharge(
        price_kwh=0.08,
        time=jan_time,
        price_thresholds=price_thresholds
    )
    
    assert result is False


def test_should_not_discharge_when_battery_at_minimum():
    from datetime import datetime
    
    battery = Battery()
    battery.soc_kwh = battery.minimum_soc_kwh
    
    price_thresholds = {
        1: {"charge": 0.05, "discharge": 0.12},
    }
    
    jan_time = datetime(2024, 1, 15, 12, 0)
    
    # Price above threshold but battery at minimum SOC
    result = battery.should_discharge(
        price_kwh=0.15,
        time=jan_time,
        price_thresholds=price_thresholds
    )
    
    assert result is False


def test_economic_dispatch_uses_correct_month():
    from datetime import datetime
    
    battery = Battery()
    
    price_thresholds = {
        1: {"charge": 0.05, "discharge": 0.12},
        6: {"charge": 0.06, "discharge": 0.15},
    }
    
    # Test January thresholds
    jan_time = datetime(2024, 1, 15, 12, 0)
    jan_charge = battery.should_charge(
        price_kwh=0.055,
        time=jan_time,
        price_thresholds=price_thresholds
    )
    
    # Test June thresholds
    june_time = datetime(2024, 6, 15, 12, 0)
    june_charge = battery.should_charge(
        price_kwh=0.055,
        time=june_time,
        price_thresholds=price_thresholds
    )
    
    # Same price: should charge in January (0.055 > 0.05) but not in June (0.055 < 0.06)
    assert jan_charge is False
    assert june_charge is True


def test_get_economic_soc_limit():
    battery = Battery()
    
    # Economic SOC limit should equal minimum SOC
    result = battery.get_economic_soc_limit()
    
    assert result == pytest.approx(battery.minimum_soc_kwh)
    assert result == pytest.approx(7.84)


# ============================================================
# Battery Dispatch
# ============================================================

def test_dispatch_battery_charges_at_low_price():
    from datetime import datetime
    
    battery = Battery()
    battery.soc_kwh = 19.6  # 50% SOC
    
    price_thresholds = {
        1: {"charge": 0.05, "discharge": 0.12},
    }
    
    jan_time = datetime(2024, 1, 15, 12, 0)
    
    result = Battery.dispatch_battery(
        battery=battery,
        home_load_kw=5.0,
        price_kwh=0.04,  # Below charge threshold
        price_thresholds=price_thresholds,
        timestamp=jan_time,
        temperature_derating=1.0,
        service_limit_amps=200,
        inverter_limit_kw=11.0,
    )
    
    assert result["action"] == "charge"
    assert result["power_kw"] == pytest.approx(11.0)
    assert result["energy_kwh"] == pytest.approx(2.75)  # 11 kW * 0.25 hours
    assert result["soc_before_kwh"] == pytest.approx(19.6)
    assert result["soc_after_kwh"] > result["soc_before_kwh"]


def test_dispatch_battery_discharges_at_high_price():
    from datetime import datetime
    
    battery = Battery()
    battery.soc_kwh = 19.6  # 50% SOC
    
    price_thresholds = {
        1: {"charge": 0.05, "discharge": 0.12},
    }
    
    jan_time = datetime(2024, 1, 15, 12, 0)
    
    result = Battery.dispatch_battery(
        battery=battery,
        home_load_kw=5.0,
        price_kwh=0.15,  # Above discharge threshold
        price_thresholds=price_thresholds,
        timestamp=jan_time,
        temperature_derating=1.0,
        service_limit_amps=200,
        inverter_limit_kw=11.0,
    )
    
    assert result["action"] == "discharge"
    assert result["power_kw"] == pytest.approx(11.0)
    assert result["energy_kwh"] == pytest.approx(2.75)  # 11 kW * 0.25 hours
    assert result["soc_before_kwh"] == pytest.approx(19.6)
    assert result["soc_after_kwh"] < result["soc_before_kwh"]


def test_dispatch_battery_idles_at_mid_price():
    from datetime import datetime
    
    battery = Battery()
    battery.soc_kwh = 19.6  # 50% SOC
    
    price_thresholds = {
        1: {"charge": 0.05, "discharge": 0.12},
    }
    
    jan_time = datetime(2024, 1, 15, 12, 0)
    
    result = Battery.dispatch_battery(
        battery=battery,
        home_load_kw=5.0,
        price_kwh=0.08,  # Between thresholds
        price_thresholds=price_thresholds,
        timestamp=jan_time,
        temperature_derating=1.0,
        service_limit_amps=200,
        inverter_limit_kw=11.0,
    )
    
    assert result["action"] == "idle"
    assert result["power_kw"] == pytest.approx(0.0)
    assert result["energy_kwh"] == pytest.approx(0.0)
    assert result["soc_before_kwh"] == pytest.approx(19.6)
    assert result["soc_after_kwh"] == pytest.approx(19.6)


def test_dispatch_battery_respects_available_charge_energy():
    from datetime import datetime
    
    battery = Battery()
    battery.soc_kwh = 38.0  # Nearly full
    
    price_thresholds = {
        1: {"charge": 0.05, "discharge": 0.12},
    }
    
    jan_time = datetime(2024, 1, 15, 12, 0)
    
    result = Battery.dispatch_battery(
        battery=battery,
        home_load_kw=5.0,
        price_kwh=0.04,  # Should charge
        price_thresholds=price_thresholds,
        timestamp=jan_time,
        temperature_derating=1.0,
        service_limit_amps=200,
        inverter_limit_kw=11.0,
    )
    
    assert result["action"] == "charge"
    # Available charge energy is limited by SOC, not power
    assert result["energy_kwh"] <= result["available_charge_kwh"]
    assert result["soc_after_kwh"] <= battery.maximum_soc_kwh


def test_dispatch_battery_respects_available_discharge_energy():
    from datetime import datetime
    
    battery = Battery()
    battery.soc_kwh = 9.0  # Close to minimum
    
    price_thresholds = {
        1: {"charge": 0.05, "discharge": 0.12},
    }
    
    jan_time = datetime(2024, 1, 15, 12, 0)
    
    result = Battery.dispatch_battery(
        battery=battery,
        home_load_kw=5.0,
        price_kwh=0.15,  # Should discharge
        price_thresholds=price_thresholds,
        timestamp=jan_time,
        temperature_derating=1.0,
        service_limit_amps=200,
        inverter_limit_kw=11.0,
    )
    
    assert result["action"] == "discharge"
    # Available discharge energy is limited by SOC, not power
    assert result["energy_kwh"] <= result["available_discharge_kwh"]
    assert result["soc_after_kwh"] >= battery.minimum_soc_kwh


def test_dispatch_battery_respects_temperature_derating():
    from datetime import datetime
    
    battery = Battery()
    battery.soc_kwh = 19.6
    
    price_thresholds = {
        1: {"charge": 0.05, "discharge": 0.12},
    }
    
    jan_time = datetime(2024, 1, 15, 12, 0)
    
    result = Battery.dispatch_battery(
        battery=battery,
        home_load_kw=5.0,
        price_kwh=0.04,  # Should charge
        price_thresholds=price_thresholds,
        timestamp=jan_time,
        temperature_derating=0.8,  # 80% derating
        service_limit_amps=200,
        inverter_limit_kw=11.0,
    )
    
    assert result["action"] == "charge"
    # Power should be limited by temperature derating
    assert result["power_kw"] == pytest.approx(8.8)  # 11 * 0.8
    assert result["max_charge_kw"] == pytest.approx(8.8)


def test_dispatch_battery_respects_home_electrical_limit():
    from datetime import datetime
    
    battery = Battery()
    battery.soc_kwh = 19.6
    
    price_thresholds = {
        1: {"charge": 0.05, "discharge": 0.12},
    }
    
    jan_time = datetime(2024, 1, 15, 12, 0)
    
    result = Battery.dispatch_battery(
        battery=battery,
        home_load_kw=5.0,
        price_kwh=0.04,  # Should charge
        price_thresholds=price_thresholds,
        timestamp=jan_time,
        temperature_derating=1.0,
        service_limit_amps=40,  # Small service
        inverter_limit_kw=11.0,
    )
    
    assert result["action"] == "charge"
    # 40A * 240V / 1000 = 9.6 kW
    # 9.6 - 5 = 4.6 kW available
    assert result["power_kw"] == pytest.approx(4.6)
    assert result["max_charge_kw"] == pytest.approx(4.6)


def test_dispatch_battery_respects_inverter_limit():
    from datetime import datetime
    
    battery = Battery()
    battery.soc_kwh = 19.6
    
    price_thresholds = {
        1: {"charge": 0.05, "discharge": 0.12},
    }
    
    jan_time = datetime(2024, 1, 15, 12, 0)
    
    result = Battery.dispatch_battery(
        battery=battery,
        home_load_kw=5.0,
        price_kwh=0.04,  # Should charge
        price_thresholds=price_thresholds,
        timestamp=jan_time,
        temperature_derating=1.0,
        service_limit_amps=200,
        inverter_limit_kw=7.0,  # Limited inverter
    )
    
    assert result["action"] == "charge"
    assert result["power_kw"] == pytest.approx(7.0)
    assert result["max_charge_kw"] == pytest.approx(7.0)


def test_dispatch_battery_returns_complete_result():
    from datetime import datetime
    
    battery = Battery()
    battery.soc_kwh = 19.6
    
    price_thresholds = {
        1: {"charge": 0.05, "discharge": 0.12},
    }
    
    jan_time = datetime(2024, 1, 15, 12, 0)
    
    result = Battery.dispatch_battery(
        battery=battery,
        home_load_kw=5.0,
        price_kwh=0.04,
        price_thresholds=price_thresholds,
        timestamp=jan_time,
        temperature_derating=1.0,
        service_limit_amps=200,
        inverter_limit_kw=11.0,
    )
    
    # Verify all expected keys are present
    assert "action" in result
    assert "power_kw" in result
    assert "energy_kwh" in result
    assert "soc_before_kwh" in result
    assert "soc_after_kwh" in result
    assert "price_kwh" in result
    assert "low_price_threshold" in result
    assert "high_price_threshold" in result
    assert "max_charge_kw" in result
    assert "max_discharge_kw" in result
    assert "available_charge_kwh" in result
    assert "available_discharge_kwh" in result
    assert "timestamp" in result
    
    # Verify values are correct
    assert result["price_kwh"] == pytest.approx(0.04)
    assert result["low_price_threshold"] == pytest.approx(0.05)
    assert result["high_price_threshold"] == pytest.approx(0.12)
    assert result["timestamp"] == jan_time


def test_dispatch_battery_uses_correct_monthly_thresholds():
    from datetime import datetime
    
    battery = Battery()
    battery.soc_kwh = 19.6
    
    price_thresholds = {
        1: {"charge": 0.05, "discharge": 0.12},
        6: {"charge": 0.06, "discharge": 0.15},
    }
    
    # Test January
    jan_time = datetime(2024, 1, 15, 12, 0)
    jan_result = Battery.dispatch_battery(
        battery=battery,
        home_load_kw=5.0,
        price_kwh=0.055,
        price_thresholds=price_thresholds,
        timestamp=jan_time,
        temperature_derating=1.0,
        service_limit_amps=200,
        inverter_limit_kw=11.0,
    )
    
    # Reset battery
    battery.soc_kwh = 19.6
    
    # Test June
    june_time = datetime(2024, 6, 15, 12, 0)
    june_result = Battery.dispatch_battery(
        battery=battery,
        home_load_kw=5.0,
        price_kwh=0.055,
        price_thresholds=price_thresholds,
        timestamp=june_time,
        temperature_derating=1.0,
        service_limit_amps=200,
        inverter_limit_kw=11.0,
    )
    
    # Same price: should idle in January (0.055 > 0.05) but charge in June (0.055 < 0.06)
    assert jan_result["action"] == "idle"
    assert june_result["action"] == "charge"