import pandas as pd


def calculate_price_thresholds(
    historical_prices,
    low_percentile=0.25,
    high_percentile=0.75,
):
    """
    Calculate monthly ERCOT price thresholds from historical data.

    For each calendar month, the price distribution consists of
    observations from the three-year historical period represented
    in the input data.

    The low percentile defines the charging threshold.
    The high percentile defines the discharging threshold.

    Parameters
    ----------
    historical_prices : pandas.DataFrame
        Historical ERCOT price data. Must contain:
            - Timestamp
            - Price ($/kWh)

    low_percentile : float, default=0.25
        Percentile used to define the low-price charging threshold.

    high_percentile : float, default=0.75
        Percentile used to define the high-price discharging threshold.

    Returns
    -------
    dict
        Dictionary keyed by calendar month number.

        Example:
        {
            1: {
                "charge": 0.045,
                "discharge": 0.120
            },
            2: {
                "charge": 0.048,
                "discharge": 0.115
            },
            ...
        }
    """

    if not 0 <= low_percentile <= 1:
        raise ValueError("low_percentile must be between 0 and 1.")

    if not 0 <= high_percentile <= 1:
        raise ValueError("high_percentile must be between 0 and 1.")

    if low_percentile >= high_percentile:
        raise ValueError(
            "low_percentile must be less than high_percentile."
        )

    required_columns = {"Timestamp", "Price ($/kWh)"}

    missing_columns = required_columns - set(historical_prices.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    prices = historical_prices.copy()

    prices["Timestamp"] = pd.to_datetime(prices["Timestamp"])

    prices["Price ($/kWh)"] = pd.to_numeric(
        prices["Price ($/kWh)"],
        errors="coerce",
    )

    prices = prices.dropna(
        subset=["Timestamp", "Price ($/kWh)"]
    )

    prices["Month"] = prices["Timestamp"].dt.month

    monthly_thresholds = {}

    for month in range(1, 13):

        month_prices = prices.loc[
            prices["Month"] == month,
            "Price ($/kWh)"
        ]

        if month_prices.empty:
            continue

        monthly_thresholds[month] = {
            "charge": month_prices.quantile(low_percentile),
            "discharge": month_prices.quantile(high_percentile),
        }

    return monthly_thresholds


if __name__ == "__main__":
    print("Testing calculate_price_thresholds function...")
    print("=" * 60)
    
    # Create sample historical price data
    sample_data = {
        "Timestamp": pd.date_range(
            start="2022-01-01",
            end="2024-12-31",
            freq="H"
        ),
    }
    
    # Generate sample prices with seasonal variation
    import numpy as np
    np.random.seed(42)
    
    timestamps = sample_data["Timestamp"]
    n_hours = len(timestamps)
    
    # Base price with monthly variation
    months = timestamps.month
    seasonal_factor = 1 + 0.3 * np.sin(2 * np.pi * (months - 1) / 12)
    
    # Add random variation
    base_prices = 0.08 * seasonal_factor
    noise = np.random.normal(0, 0.02, n_hours)
    prices = np.maximum(0.01, base_prices + noise)
    
    sample_data["Price ($/kWh)"] = prices
    
    df = pd.DataFrame(sample_data)
    
    print(f"\nSample data created:")
    print(f"  Date range: {df['Timestamp'].min()} to {df['Timestamp'].max()}")
    print(f"  Total records: {len(df):,}")
    print(f"  Price range: ${df['Price ($/kWh)'].min():.4f} - ${df['Price ($/kWh)'].max():.4f}")
    
    # Calculate thresholds
    print("\nCalculating monthly thresholds (25th/75th percentiles)...")
    thresholds = calculate_price_thresholds(
        df,
        low_percentile=0.25,
        high_percentile=0.75
    )
    
    print("\nMonthly Price Thresholds:")
    print("-" * 60)
    print(f"{'Month':<10} {'Charge (25th)':<20} {'Discharge (75th)':<20}")
    print("-" * 60)
    
    month_names = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    
    for month in range(1, 13):
        if month in thresholds:
            charge_threshold = thresholds[month]["charge"]
            discharge_threshold = thresholds[month]["discharge"]
            print(f"{month_names[month-1]:<10} ${charge_threshold:.4f}           ${discharge_threshold:.4f}")
    
    # Test with custom percentiles
    print("\n" + "=" * 60)
    print("Testing with custom percentiles (10th/90th)...")
    
    custom_thresholds = calculate_price_thresholds(
        df,
        low_percentile=0.10,
        high_percentile=0.90
    )
    
    print(f"\nJanuary thresholds:")
    print(f"  Charge (10th): ${custom_thresholds[1]['charge']:.4f}")
    print(f"  Discharge (90th): ${custom_thresholds[1]['discharge']:.4f}")
    
    print("\n" + "=" * 60)
    print("All tests completed successfully!")