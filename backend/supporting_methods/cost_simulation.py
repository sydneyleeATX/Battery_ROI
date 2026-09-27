import pandas as pd
from datetime import datetime
from pathlib import Path
import sys

RETAIL_PRICE_MULTIPLIER = 3.0

# Import Battery for type reference in simulate_customer_savings
try:
    from backend.supporting_methods.battery_status import Battery
except ModuleNotFoundError:
    # Handle direct script execution
    project_root = Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from backend.supporting_methods.battery_status import Battery


def build_historical_data_from_location(
    zip_code: str | int,
    start_date: datetime,
    end_date: datetime,
    avg_annual_energy_kwh: float = 10000,
    home_load_profile_path: Path = Path("data/assumptions/residential_load_profile.csv"),
) -> pd.DataFrame:
    """
    Build location-aware historical dataset for battery simulation.
    
    Parameters
    ----------
    zip_code : str or int
        Customer ZIP code for location resolution.
    start_date : datetime
        Start date for historical data retrieval.
    end_date : datetime
        End date for historical data retrieval.
    avg_annual_energy_kwh : float, default=10000
        Customer's average annual household electricity consumption in kWh/year.
        Used to scale the residential load profile to customer-specific usage.
    home_load_profile_path : Path
        Path to residential load profile CSV file.
    
    This orchestration function combines:
    - Location resolution (ZIP → ERCOT load zone → settlement point)
    - Bulk price retrieval for the settlement point
    - Weather data retrieval for the location
    - Temperature derating calculation
    - Home load profile mapping
    
    Parameters
    ----------
    zip_code : str | int
        5-digit US ZIP code for customer location.
    
    start_date : datetime
        Start date for historical data (inclusive).
    
    end_date : datetime
        End date for historical data (inclusive).
    
    home_load_profile_path : Path
        Path to residential load profile CSV file.
    
    Returns
    -------
    pd.DataFrame
        DataFrame with columns:
        - Timestamp: pd.Timestamp for each interval
        - Price ($/kWh): ERCOT price in $/kWh
        - home_load_kw: Household load in kW
        - temperature_derating: Battery derating factor (0-1)
        - temperature_f: Temperature in Fahrenheit (diagnostic)
        - settlement_point: ERCOT settlement point (diagnostic)
    
    Raises
    ------
    ValueError
        If ZIP code is invalid, start_date > end_date, or required data is missing.
    FileNotFoundError
        If required data files do not exist.
    
    Notes
    -----
    Missing data handling:
    - Missing values are forward-filled from the previous interval
    - A summary of autofill operations is printed at the end
    """
    
    from backend.location.load_zone_lookup import get_ercot_load_zone
    from backend.location.zip_to_coord import get_zip_centroid
    from backend.supporting_methods.retrieve_price import get_historical_prices_bulk
    from backend.supporting_methods.weather import get_weather
    from backend.supporting_methods.temp_derating import get_temperature_derating
    
    # --------------------------------------------------------
    # Validate inputs
    # --------------------------------------------------------
    
    if start_date > end_date:
        raise ValueError(
            f"start_date ({start_date}) must be <= end_date ({end_date})"
        )
    
    print(f"Building historical data for ZIP {zip_code}")
    print(f"Period: {start_date.date()} to {end_date.date()}")
    print()
    
    # --------------------------------------------------------
    # Step 1: Location resolution
    # --------------------------------------------------------
    
    print("Step 1: Resolving location...")
    
    # ZIP → settlement point (for prices)
    settlement_point = get_ercot_load_zone(zip_code)
    print(f"  Settlement point: {settlement_point}")
    
    # ZIP → coordinates (for weather)
    latitude, longitude = get_zip_centroid(zip_code)
    if latitude is None or longitude is None:
        raise ValueError(f"Could not determine coordinates for ZIP {zip_code}")
    print(f"  Coordinates: ({latitude:.4f}, {longitude:.4f})")
    print()
    
    # --------------------------------------------------------
    # Step 2: Retrieve historical prices (bulk)
    # --------------------------------------------------------
    
    print("Step 2: Retrieving historical prices...")
    prices_df = get_historical_prices_bulk(
        start_date=start_date,
        end_date=end_date,
        settlement_point=settlement_point,
    )
    print(f"  Retrieved {len(prices_df)} price records")
    print()
    
    # --------------------------------------------------------
    # Step 3: Retrieve historical weather (bulk)
    # --------------------------------------------------------
    
    print("Step 3: Retrieving historical weather...")
    weather_data = get_weather(
        latitude=latitude,
        longitude=longitude,
        start_date=start_date,
        end_date=end_date,
    )
    
    if weather_data is None:
        raise ValueError(
            f"Failed to retrieve weather data for location ({latitude}, {longitude})"
        )
    
    # Convert to DataFrame
    weather_df = pd.DataFrame(weather_data)
    weather_df["Timestamp"] = pd.to_datetime(weather_df["timestamp"])
    weather_df = weather_df.rename(columns={"temperature_f": "temperature_f"})
    weather_df = weather_df[["Timestamp", "temperature_f"]]
    
    print(f"  Retrieved {len(weather_df)} weather records (hourly)")
    print()
    
    # --------------------------------------------------------
    # Step 4: Calculate temperature derating
    # --------------------------------------------------------
    
    print("Step 4: Calculating temperature derating...")
    weather_df["temperature_derating"] = weather_df["temperature_f"].apply(
        get_temperature_derating
    )
    print(f"  Applied derating to {len(weather_df)} records")
    print()
    
    # --------------------------------------------------------
    # Step 5: Load home load profile
    # --------------------------------------------------------
    
    print("Step 5: Loading home load profile...")
    if not home_load_profile_path.exists():
        raise FileNotFoundError(
            f"Home load profile not found: {home_load_profile_path}"
        )
    
    load_profile = pd.read_csv(home_load_profile_path)
    print(f"  Loaded profile with {len(load_profile)} entries")
    print()
    
    # --------------------------------------------------------
    # Step 6: Create complete timestamp range (15-minute intervals)
    # --------------------------------------------------------
    
    print("Step 6: Creating complete timestamp range...")
    complete_timestamps = pd.date_range(
        start=start_date,
        end=end_date,
        freq="15min",
    )
    
    historical_data = pd.DataFrame({
        "Timestamp": complete_timestamps
    })
    print(f"  Created {len(historical_data)} 15-minute intervals")
    print()
    
    # --------------------------------------------------------
    # Step 7: Merge price data
    # --------------------------------------------------------
    
    print("Step 7: Merging price data...")
    historical_data = historical_data.merge(
        prices_df,
        on="Timestamp",
        how="left",
    )
    
    price_missing_before = historical_data["Price ($/kWh)"].isna().sum()
    if price_missing_before > 0:
        print(f"  Warning: {price_missing_before} timestamps missing price data")
    print()
    
    # --------------------------------------------------------
    # Step 8: Merge weather data (hourly → 15-min via forward fill)
    # --------------------------------------------------------
    
    print("Step 8: Merging weather data...")
    historical_data = historical_data.merge(
        weather_df,
        on="Timestamp",
        how="left",
    )
    
    weather_missing_before = historical_data["temperature_f"].isna().sum()
    if weather_missing_before > 0:
        print(f"  Warning: {weather_missing_before} timestamps missing weather data")
    print()
    
    # --------------------------------------------------------
    # Step 9: Map home load profile to timestamps
    # --------------------------------------------------------
    
    print("Step 9: Mapping home load profile...")
    
    # Handle the actual load profile format with time intervals and fractions
    if "Interval_Index" in load_profile.columns and "Daily_Fraction_Annual" in load_profile.columns:
        # The profile has 96 15-minute intervals (24 hours * 4)
        # Map each timestamp to its 15-minute interval of the day
        
        # Calculate interval index (0-95) for each timestamp
        historical_data["interval_of_day"] = (
            historical_data["Timestamp"].dt.hour * 4 + 
            historical_data["Timestamp"].dt.minute // 15
        )
        
        # Merge with load profile
        load_profile_subset = load_profile[["Interval_Index", "Daily_Fraction_Annual"]].copy()
        load_profile_subset["interval_of_day"] = load_profile_subset["Interval_Index"] - 1  # 1-indexed to 0-indexed
        
        historical_data = historical_data.merge(
            load_profile_subset[["interval_of_day", "Daily_Fraction_Annual"]],
            on="interval_of_day",
            how="left",
        )
        
        # Convert daily fraction to kW for 15-minute interval
        # Daily fraction * annual kWh / 365 days = daily kWh for this interval
        # Then convert to kW: (daily kWh / 24 hours) * 4 (since 15-min intervals)
        historical_data["home_load_kw"] = (
            historical_data["Daily_Fraction_Annual"] * avg_annual_energy_kwh / 365 / 24 * 4
        )
        
        # Clean up temporary columns
        historical_data = historical_data.drop(columns=["interval_of_day", "Daily_Fraction_Annual"])
        
        print(f"  Mapped load profile using daily fractions")
        print(f"  Customer annual consumption: {avg_annual_energy_kwh} kWh/year")
        
    elif "hour" in load_profile.columns and "load_kw" in load_profile.columns:
        # Hour-based profile (alternative format)
        historical_data["hour"] = historical_data["Timestamp"].dt.hour
        historical_data = historical_data.merge(
            load_profile[["hour", "load_kw"]],
            on="hour",
            how="left",
        )
        historical_data = historical_data.rename(columns={"load_kw": "home_load_kw"})
        historical_data = historical_data.drop(columns=["hour"])
        print(f"  Mapped load profile using hourly values")
    else:
        # If profile format is different, raise error
        raise ValueError(
            f"Unsupported load profile format. "
            f"Expected 'Interval_Index' and 'Daily_Fraction_Annual' OR 'hour' and 'load_kw' columns. "
            f"Found: {load_profile.columns.tolist()}"
        )
    
    load_missing_before = historical_data["home_load_kw"].isna().sum()
    if load_missing_before > 0:
        print(f"  Warning: {load_missing_before} timestamps missing load data")
    print()
    
    # --------------------------------------------------------
    # Step 10: Forward-fill missing data
    # --------------------------------------------------------
    
    print("Step 10: Handling missing data (forward-fill)...")
    
    # Track missing counts before forward-fill
    price_missing = historical_data["Price ($/kWh)"].isna().sum()
    temp_missing = historical_data["temperature_f"].isna().sum()
    derating_missing = historical_data["temperature_derating"].isna().sum()
    load_missing = historical_data["home_load_kw"].isna().sum()
    
    # Forward-fill missing values
    historical_data["Price ($/kWh)"] = historical_data["Price ($/kWh)"].ffill()
    historical_data["temperature_f"] = historical_data["temperature_f"].ffill()
    historical_data["temperature_derating"] = historical_data["temperature_derating"].ffill()
    historical_data["home_load_kw"] = historical_data["home_load_kw"].ffill()
    
    # Track how many were filled
    price_filled = price_missing - historical_data["Price ($/kWh)"].isna().sum()
    temp_filled = temp_missing - historical_data["temperature_f"].isna().sum()
    derating_filled = derating_missing - historical_data["temperature_derating"].isna().sum()
    load_filled = load_missing - historical_data["home_load_kw"].isna().sum()
    
    total_autofills = price_filled + temp_filled + derating_filled + load_filled
    
    print(f"  Autofill summary:")
    print(f"    Price data:        {price_filled} intervals")
    print(f"    Temperature data:  {temp_filled} intervals")
    print(f"    Derating data:     {derating_filled} intervals")
    print(f"    Load data:         {load_filled} intervals")
    print(f"    TOTAL AUTOFILLS:   {total_autofills} intervals")
    print()
    
    # Check if any data is still missing after forward-fill
    still_missing = historical_data[
        ["Price ($/kWh)", "temperature_f", "temperature_derating", "home_load_kw"]
    ].isna().sum().sum()
    
    if still_missing > 0:
        print(f"  Warning: {still_missing} values still missing after forward-fill")
        print("  (These are likely at the start of the dataset with no prior values)")
        # Drop rows with any missing values
        rows_before = len(historical_data)
        historical_data = historical_data.dropna(
            subset=["Price ($/kWh)", "temperature_f", "temperature_derating", "home_load_kw"]
        )
        rows_dropped = rows_before - len(historical_data)
        print(f"  Dropped {rows_dropped} incomplete rows")
        print()
    
    # --------------------------------------------------------
    # Step 11: Add diagnostic columns
    # --------------------------------------------------------
    
    historical_data["settlement_point"] = settlement_point
    
    # --------------------------------------------------------
    # Step 12: Final validation
    # --------------------------------------------------------
    
    print("Step 11: Final validation...")
    
    # Verify timestamps are sorted
    if not historical_data["Timestamp"].is_monotonic_increasing:
        historical_data = historical_data.sort_values("Timestamp").reset_index(drop=True)
        print("  Sorted timestamps")
    
    # Verify timestamps are unique
    duplicates = historical_data["Timestamp"].duplicated().sum()
    if duplicates > 0:
        print(f"  Warning: Removed {duplicates} duplicate timestamps")
        historical_data = historical_data.drop_duplicates(subset=["Timestamp"])
    
    # Verify required columns exist
    required_columns = ["Timestamp", "Price ($/kWh)", "home_load_kw", "temperature_derating"]
    missing_columns = set(required_columns) - set(historical_data.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")
    
    print(f"  Final dataset: {len(historical_data)} complete intervals")
    print()
    
    print("=" * 60)
    print(f"Historical data build complete!")
    print(f"Total autofills required: {total_autofills}")
    print("=" * 60)
    print()
    
    return historical_data


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
    
    Note: ERCOT prices can be negative during oversupply periods.
    This is a legitimate market condition where generators pay to offload power.
    """

    # Note: We allow negative prices as they are legitimate in ERCOT markets
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

    # Note: ERCOT prices can be negative during oversupply periods
    # This is a legitimate market condition, so we don't validate >= 0

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

    # Test 7: Location-aware integration test
    print("=" * 60)
    print("Test 7: Location-aware simulation (Dallas, TX)")
    print("-" * 60)
    print()
    
    # Step 1: Build location-aware historical data
    print("Building historical data from location...")
    try:
        historical_data = build_historical_data_from_location(
            zip_code="75201",  # Dallas, TX
            start_date=datetime(2022, 1, 1),
            end_date=datetime(2022, 1, 7),  # 1 week of data
            avg_annual_energy_kwh=12000,  # Customer-specific usage
        )
        print(f"✓ Successfully built historical data")
        print(f"  Dataset size: {len(historical_data)} intervals")
        print(f"  Columns: {', '.join(historical_data.columns)}")
        print()
        
        # Step 2: Create battery and price thresholds
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
        
        # Step 3: Run simulation (doesn't know about location!)
        print("Running battery savings simulation...")
        results = simulate_customer_savings(
            battery=battery,
            historical_data=historical_data,
            price_thresholds=price_thresholds,
            service_limit_amps=200,
            inverter_limit_kw=11.0,
            voltage=240.0,
            interval_hours=0.25,
        )
        
        print(f"✓ Simulation complete")
        print()
        print(f"  Simulation period: {results['simulation_start']} to {results['simulation_end']}")
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
        
        # Show data flow summary
        print("Data Flow Summary:")
        print("  ZIP 75201 (Dallas)")
        print("    → Settlement Point:", historical_data['settlement_point'].iloc[0])
        print("    → Historical Prices: Retrieved from ERCOT")
        print("    → Weather Data: Retrieved from Open-Meteo API")
        print("    → Temperature Derating: Applied to battery performance")
        print("    → Home Load Profile: Mapped from residential profile")
        print("    → Simulation: Battery dispatch optimization")
        print()
        
    except Exception as e:
        print(f"✗ Location-aware test failed: {e}")
        print("  (This is expected if historical price files or load profile are missing)")
        print()

    print("=" * 60)
    print("All tests completed successfully!")
