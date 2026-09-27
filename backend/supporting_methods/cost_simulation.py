RETAIL_PRICE_MULTIPLIER = 3.0

def get_customer_electricity_price(ercot_price_kwh: float) -> float:
    """
    Estimate residential customer electricity price from
    an ERCOT wholesale electricity price.

    Assumption:
        Customer electricity price ≈ 3 × ERCOT price.
        Can return to this function to refine the multiplier (add seasonality)

    The multiplier is a simplified estimate intended to
    account for the difference between wholesale ERCOT
    pricing and all-in residential electricity costs.
    """

    if ercot_price_kwh < 0:
        raise ValueError("ercot_price_kwh must be nonnegative.")

    return ercot_price_kwh * RETAIL_PRICE_MULTIPLIER


def calculate_interval_electricity_cost(
    home_load_kw: float,
    action: str,
    battery_energy_kwh: float,
    ercot_price_kwh: float,
    interval_hours: float = 0.25,
) -> dict:
    """
    Calculate the customer's electricity cost for one interval.

    The ERCOT price is converted into an estimated residential
    electricity price using get_customer_electricity_price().

    Args:
        home_load_kw: Household electricity demand during the interval.
        action: Battery action ("charge", "discharge", or "idle").
        battery_energy_kwh: Energy charged into or discharged from
            the battery during the interval.
        ercot_price_kwh: ERCOT electricity price in $/kWh.
        interval_hours: Length of the interval in hours.
            Defaults to 15 minutes.

    Returns:
        Dictionary containing grid energy, estimated customer price,
        and electricity cost for the interval.
    """

    if home_load_kw < 0:
        raise ValueError("home_load_kw must be nonnegative.")

    if battery_energy_kwh < 0:
        raise ValueError("battery_energy_kwh must be nonnegative.")

    if ercot_price_kwh < 0:
        raise ValueError("ercot_price_kwh must be nonnegative.")

    if interval_hours <= 0:
        raise ValueError("interval_hours must be positive.")

    if action not in {"charge", "discharge", "idle"}:
        raise ValueError(
            "action must be 'charge', 'discharge', or 'idle'."
        )

    # Household energy consumed during the interval
    home_energy_kwh = home_load_kw * interval_hours

    # Determine net energy drawn from the grid
    if action == "charge":
        grid_energy_kwh = home_energy_kwh + battery_energy_kwh

    elif action == "discharge":
        # Battery can offset household consumption,
        # but cannot send excess energy to the grid.
        grid_energy_kwh = max(
            0.0,
            home_energy_kwh - battery_energy_kwh
        )

    else:  # idle
        grid_energy_kwh = home_energy_kwh

    # Convert ERCOT wholesale price to estimated
    # residential customer electricity price.
    customer_price_kwh = get_customer_electricity_price(
        ercot_price_kwh
    )

    # Customer's electricity cost for the interval
    electricity_cost = grid_energy_kwh * customer_price_kwh

    return {
        "home_energy_kwh": home_energy_kwh,
        "grid_energy_kwh": grid_energy_kwh,
        "customer_price_kwh": customer_price_kwh,
        "electricity_cost": electricity_cost,
    }

import pandas as pd


def simulate_customer_savings(
    battery,
    historical_data,
    price_thresholds,
    service_limit_amps,
    inverter_limit_kw,
    voltage=240.0,
    interval_hours=0.25,
):
    """
    Simulate customer battery savings over the most recent year
    of available historical data.

    Needs to account for customer's location (for pricing and weather)

    The simulation runs sequentially through 15-minute intervals,
    calling dispatch_battery() at each interval and updating the
    battery SOC.

    Returns:
        dict containing total savings, charging cost, discharging
        value, net economic benefit, event counts, SOC information,
        and backup reserve violations.
    """

    required_columns = {
        "Timestamp",
        "Price ($/kWh)",
        "home_load_kw",
        "temperature_derating",
    }

    missing_columns = required_columns - set(historical_data.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    if interval_hours <= 0:
        raise ValueError("interval_hours must be positive.")

    # --------------------------------------------------
    # Prepare historical data
    # --------------------------------------------------

    historical_data = historical_data.copy()

    historical_data["Timestamp"] = pd.to_datetime(
        historical_data["Timestamp"]
    )

    historical_data = historical_data.sort_values("Timestamp")

    # --------------------------------------------------
    # Select most recent year of data
    # --------------------------------------------------

    end_time = historical_data["Timestamp"].max()
    start_time = end_time - pd.DateOffset(years=1)

    historical_data = historical_data[
        (historical_data["Timestamp"] >= start_time)
        & (historical_data["Timestamp"] <= end_time)
    ].copy()

    if historical_data.empty:
        raise ValueError(
            "No historical data available for the most recent year."
        )

    # --------------------------------------------------
    # Initialize simulation
    # --------------------------------------------------

    starting_soc_kwh = battery.soc_kwh

    total_baseline_cost = 0.0
    total_battery_cost = 0.0
    total_charging_cost = 0.0
    total_discharging_value = 0.0

    charge_events = 0
    discharge_events = 0
    backup_reserve_violations = 0

    # --------------------------------------------------
    # Run battery simulation
    # --------------------------------------------------

    for _, row in historical_data.iterrows():

        timestamp = row["Timestamp"]
        ercot_price_kwh = row["Price ($/kWh)"]
        home_load_kw = row["home_load_kw"]
        temperature_derating = row["temperature_derating"]

        # ----------------------------------------------
        # Baseline: no battery
        # ----------------------------------------------

        baseline_cost_result = calculate_interval_electricity_cost(
            home_load_kw=home_load_kw,
            action="idle",
            battery_energy_kwh=0.0,
            ercot_price_kwh=ercot_price_kwh,
            interval_hours=interval_hours,
        )

        baseline_cost = baseline_cost_result["electricity_cost"]

        # ----------------------------------------------
        # Battery dispatch
        # ----------------------------------------------

        dispatch_result = Battery.dispatch_battery(
            battery=battery,
            home_load_kw=home_load_kw,
            price_kwh=ercot_price_kwh,
            price_thresholds=price_thresholds,
            timestamp=timestamp,
            temperature_derating=temperature_derating,
            service_limit_amps=service_limit_amps,
            inverter_limit_kw=inverter_limit_kw,
            voltage=voltage,
        )

        action = dispatch_result["action"]
        battery_energy_kwh = dispatch_result["energy_kwh"]

        # ----------------------------------------------
        # Cost with battery
        # ----------------------------------------------

        battery_cost_result = calculate_interval_electricity_cost(
            home_load_kw=home_load_kw,
            action=action,
            battery_energy_kwh=battery_energy_kwh,
            ercot_price_kwh=ercot_price_kwh,
            interval_hours=interval_hours,
        )

        battery_cost = battery_cost_result["electricity_cost"]

        total_baseline_cost += baseline_cost
        total_battery_cost += battery_cost

        # ----------------------------------------------
        # Track charging/discharging economics
        # ----------------------------------------------

        if action == "charge":
            charge_events += 1

            charging_cost = (
                battery_energy_kwh
                * battery_cost_result["customer_price_kwh"]
            )

            total_charging_cost += charging_cost

        elif action == "discharge":
            discharge_events += 1

            discharging_value = (
                battery_energy_kwh
                * battery_cost_result["customer_price_kwh"]
            )

            total_discharging_value += discharging_value

        # ----------------------------------------------
        # Check backup reserve
        # ----------------------------------------------

        if battery.soc_kwh < battery.minimum_soc_kwh:
            backup_reserve_violations += 1

    # --------------------------------------------------
    # Aggregate results
    # --------------------------------------------------

    total_savings = total_baseline_cost - total_battery_cost

    net_economic_benefit = (
        total_discharging_value - total_charging_cost
    )

    return {
        "simulation_start": historical_data["Timestamp"].min(),
        "simulation_end": historical_data["Timestamp"].max(),

        "total_savings": total_savings,
        "charging_cost": total_charging_cost,
        "discharging_value": total_discharging_value,
        "net_economic_benefit": net_economic_benefit,

        "charge_events": charge_events,
        "discharge_events": discharge_events,

        "starting_soc_kwh": starting_soc_kwh,
        "ending_soc_kwh": battery.soc_kwh,

        "backup_reserve_violations": backup_reserve_violations,

        "baseline_cost": total_baseline_cost,
        "battery_cost": total_battery_cost,
    }










if __name__ == "__main__":
    from datetime import datetime, timedelta
    import sys
    from pathlib import Path
    
    # Add project root to path for imports
    project_root = Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    from backend.supporting_methods.battery_status import Battery
    
    print("Testing cost simulation functions...")
    print("=" * 60)
    print()

    # Test 1: Customer price conversion
    print("Test 1: Customer electricity price conversion")
    ercot_price = 0.05  # $0.05/kWh wholesale
    customer_price = get_customer_electricity_price(ercot_price)
    print(f"  ERCOT price: ${ercot_price:.3f}/kWh")
    print(f"  Customer price: ${customer_price:.3f}/kWh")
    print(f"  Multiplier: {customer_price / ercot_price:.1f}x")
    print()

    # Test 2: Idle scenario (no battery action)
    print("Test 2: Idle scenario (no battery)")
    result = calculate_interval_electricity_cost(
        home_load_kw=5.0,
        action="idle",
        battery_energy_kwh=0.0,
        ercot_price_kwh=0.08,
        interval_hours=0.25,
    )
    print(f"  Home load: 5.0 kW")
    print(f"  Action: idle")
    print(f"  Home energy: {result['home_energy_kwh']:.3f} kWh")
    print(f"  Grid energy: {result['grid_energy_kwh']:.3f} kWh")
    print(f"  Customer price: ${result['customer_price_kwh']:.3f}/kWh")
    print(f"  Electricity cost: ${result['electricity_cost']:.3f}")
    print()

    # Test 3: Charging scenario
    print("Test 3: Charging scenario (low price)")
    result = calculate_interval_electricity_cost(
        home_load_kw=5.0,
        action="charge",
        battery_energy_kwh=2.75,  # Charging 11 kW * 0.25 hr
        ercot_price_kwh=0.04,
        interval_hours=0.25,
    )
    print(f"  Home load: 5.0 kW")
    print(f"  Action: charge")
    print(f"  Battery energy: {result['home_energy_kwh']:.3f} kWh (home)")
    print(f"  Battery charging: 2.75 kWh")
    print(f"  Grid energy: {result['grid_energy_kwh']:.3f} kWh")
    print(f"  Customer price: ${result['customer_price_kwh']:.3f}/kWh")
    print(f"  Electricity cost: ${result['electricity_cost']:.3f}")
    print()

    # Test 4: Discharging scenario (partial offset)
    print("Test 4: Discharging scenario (partial offset)")
    result = calculate_interval_electricity_cost(
        home_load_kw=5.0,
        action="discharge",
        battery_energy_kwh=1.5,  # Battery provides 1.5 kWh
        ercot_price_kwh=0.15,
        interval_hours=0.25,
    )
    print(f"  Home load: 5.0 kW")
    print(f"  Action: discharge")
    print(f"  Home energy: {result['home_energy_kwh']:.3f} kWh")
    print(f"  Battery discharge: 1.5 kWh")
    print(f"  Grid energy: {result['grid_energy_kwh']:.3f} kWh")
    print(f"  Customer price: ${result['customer_price_kwh']:.3f}/kWh")
    print(f"  Electricity cost: ${result['electricity_cost']:.3f}")
    print()

    # Test 5: Discharging scenario (full offset)
    print("Test 5: Discharging scenario (full offset)")
    result = calculate_interval_electricity_cost(
        home_load_kw=5.0,
        action="discharge",
        battery_energy_kwh=2.0,  # Battery provides more than home needs
        ercot_price_kwh=0.15,
        interval_hours=0.25,
    )
    print(f"  Home load: 5.0 kW")
    print(f"  Action: discharge")
    print(f"  Home energy: {result['home_energy_kwh']:.3f} kWh")
    print(f"  Battery discharge: 2.0 kWh")
    print(f"  Grid energy: {result['grid_energy_kwh']:.3f} kWh (fully offset!)")
    print(f"  Customer price: ${result['customer_price_kwh']:.3f}/kWh")
    print(f"  Electricity cost: ${result['electricity_cost']:.3f}")
    print()

    # Test 6: Cost comparison
    print("Test 6: Cost comparison (with vs without battery)")
    print("-" * 60)
    
    # High price scenario - no battery
    no_battery = calculate_interval_electricity_cost(
        home_load_kw=5.0,
        action="idle",
        battery_energy_kwh=0.0,
        ercot_price_kwh=0.15,
        interval_hours=0.25,
    )
    
    # High price scenario - with battery discharge
    with_battery = calculate_interval_electricity_cost(
        home_load_kw=5.0,
        action="discharge",
        battery_energy_kwh=1.25,
        ercot_price_kwh=0.15,
        interval_hours=0.25,
    )
    
    savings = no_battery['electricity_cost'] - with_battery['electricity_cost']
    
    print(f"  Without battery: ${no_battery['electricity_cost']:.3f}")
    print(f"  With battery:    ${with_battery['electricity_cost']:.3f}")
    print(f"  Savings:         ${savings:.3f}")
    print()

    # Test 7: simulate_customer_savings with sample data
    print("=" * 60)
    print("Test 7: simulate_customer_savings (sample data)")
    print("-" * 60)
    
    # Create sample historical data for one week
    start_date = datetime(2024, 1, 1)
    num_intervals = 4 * 24 * 7  # 7 days of 15-minute intervals
    
    timestamps = [start_date + timedelta(hours=0.25 * i) for i in range(num_intervals)]
    
    # Create realistic price pattern (low at night, high during day)
    import numpy as np
    np.random.seed(42)
    
    prices = []
    home_loads = []
    temp_deratings = []
    
    for ts in timestamps:
        hour = ts.hour
        
        # Price pattern: low at night (2-6am), high during day (2-8pm)
        if 2 <= hour < 6:
            base_price = 0.03  # Low overnight
        elif 14 <= hour < 20:
            base_price = 0.12  # High during peak
        else:
            base_price = 0.06  # Medium
        
        price = base_price + np.random.normal(0, 0.01)
        prices.append(max(0.01, price))
        
        # Home load pattern: low at night, high during day
        if 0 <= hour < 6:
            base_load = 2.0
        elif 6 <= hour < 9:
            base_load = 4.0
        elif 9 <= hour < 17:
            base_load = 3.0
        elif 17 <= hour < 22:
            base_load = 6.0
        else:
            base_load = 3.0
        
        load = base_load + np.random.normal(0, 0.5)
        home_loads.append(max(1.0, load))
        
        # Temperature derating (assume good conditions)
        temp_deratings.append(1.0)
    
    historical_data = pd.DataFrame({
        'Timestamp': timestamps,
        'Price ($/kWh)': prices,
        'home_load_kw': home_loads,
        'temperature_derating': temp_deratings,
    })
    
    # Create battery and price thresholds
    battery = Battery()
    
    price_thresholds = {
        1: {"charge": 0.05, "discharge": 0.10},
        2: {"charge": 0.05, "discharge": 0.10},
        3: {"charge": 0.05, "discharge": 0.10},
        4: {"charge": 0.05, "discharge": 0.10},
        5: {"charge": 0.05, "discharge": 0.10},
        6: {"charge": 0.05, "discharge": 0.10},
        7: {"charge": 0.05, "discharge": 0.10},
        8: {"charge": 0.05, "discharge": 0.10},
        9: {"charge": 0.05, "discharge": 0.10},
        10: {"charge": 0.05, "discharge": 0.10},
        11: {"charge": 0.05, "discharge": 0.10},
        12: {"charge": 0.05, "discharge": 0.10},
    }
    
    # Run simulation
    results = simulate_customer_savings(
        battery=battery,
        historical_data=historical_data,
        price_thresholds=price_thresholds,
        service_limit_amps=200,
        inverter_limit_kw=11.0,
        voltage=240.0,
        interval_hours=0.25,
    )
    
    print(f"  Simulation period: {results['simulation_start']} to {results['simulation_end']}")
    print(f"  Duration: 7 days")
    print()
    print(f"  Starting SOC: {results['starting_soc_kwh']:.2f} kWh")
    print(f"  Ending SOC: {results['ending_soc_kwh']:.2f} kWh")
    print()
    print(f"  Baseline cost (no battery): ${results['baseline_cost']:.2f}")
    print(f"  Battery cost:                ${results['battery_cost']:.2f}")
    print(f"  Total savings:               ${results['total_savings']:.2f}")
    print()
    print(f"  Charging cost:               ${results['charging_cost']:.2f}")
    print(f"  Discharging value:           ${results['discharging_value']:.2f}")
    print(f"  Net economic benefit:        ${results['net_economic_benefit']:.2f}")
    print()
    print(f"  Charge events: {results['charge_events']}")
    print(f"  Discharge events: {results['discharge_events']}")
    print(f"  Backup reserve violations: {results['backup_reserve_violations']}")
    print()

    print("=" * 60)
    print("All tests completed successfully!")
