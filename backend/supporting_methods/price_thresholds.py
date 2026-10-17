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