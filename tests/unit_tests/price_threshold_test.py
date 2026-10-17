import numpy as np
import pandas as pd
from pathlib import Path
import sys

project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.supporting_methods.price_thresholds import calculate_price_thresholds


if __name__ == "__main__":
    print("Testing calculate_price_thresholds function...")
    print("=" * 60)

    sample_data = {
        "Timestamp": pd.date_range(
            start="2022-01-01",
            end="2024-12-31",
            freq="h",
        ),
    }

    np.random.seed(42)

    timestamps = sample_data["Timestamp"]
    n_hours = len(timestamps)

    months = timestamps.month
    seasonal_factor = 1 + 0.3 * np.sin(2 * np.pi * (months - 1) / 12)
    base_prices = 0.08 * seasonal_factor
    noise = np.random.normal(0, 0.02, n_hours)
    prices = np.maximum(0.01, base_prices + noise)

    sample_data["Price ($/kWh)"] = prices
    df = pd.DataFrame(sample_data)

    print("\nSample data created:")
    print(f"  Date range: {df['Timestamp'].min()} to {df['Timestamp'].max()}")
    print(f"  Total records: {len(df):,}")
    print(
        f"  Price range: ${df['Price ($/kWh)'].min():.4f} - "
        f"${df['Price ($/kWh)'].max():.4f}"
    )

    print("\nCalculating monthly thresholds (25th/75th percentiles)...")
    thresholds = calculate_price_thresholds(
        df,
        low_percentile=0.25,
        high_percentile=0.75,
    )

    print("\nMonthly Price Thresholds:")
    print("-" * 60)
    print(f"{'Month':<10} {'Charge (25th)':<20} {'Discharge (75th)':<20}")
    print("-" * 60)

    month_names = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]

    for month in range(1, 13):
        if month in thresholds:
            charge_threshold = thresholds[month]["charge"]
            discharge_threshold = thresholds[month]["discharge"]
            print(
                f"{month_names[month - 1]:<10} "
                f"${charge_threshold:.4f}           ${discharge_threshold:.4f}"
            )

    print("\n" + "=" * 60)
    print("Testing with custom percentiles (10th/90th)...")

    custom_thresholds = calculate_price_thresholds(
        df,
        low_percentile=0.10,
        high_percentile=0.90,
    )

    print("\nJanuary thresholds:")
    print(f"  Charge (10th): ${custom_thresholds[1]['charge']:.4f}")
    print(f"  Discharge (90th): ${custom_thresholds[1]['discharge']:.4f}")

    print("\n" + "=" * 60)
    print("All tests completed successfully!")