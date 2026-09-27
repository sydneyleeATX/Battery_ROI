import pandas as pd
from pathlib import Path
from datetime import datetime


PRICES_FOLDER = Path("data/historical_prices")


def get_historical_price(
    timestamp: pd.Timestamp,
    settlement_point: str,
    prices_folder: Path = PRICES_FOLDER
) -> float:
    """
    Retrieve the ERCOT historical price for a specific timestamp and settlement point.

    Parameters
    ----------
    timestamp : pd.Timestamp
        Timestamp for which to retrieve the price.
        Must correspond to a 15-minute ERCOT interval.

    settlement_point : str
        ERCOT settlement point, e.g. "LZ_NORTH".

    prices_folder : Path
        Folder containing prices_2022.xlsx through prices_2026.xlsx.

    Returns
    -------
    float
        ERCOT price in $/kWh.

    Raises
    ------
    ValueError
        If the timestamp or settlement point cannot be found.
    FileNotFoundError
        If the relevant yearly Excel file does not exist.
    """

    # --------------------------------------------------------
    # Normalize timestamp
    # --------------------------------------------------------

    timestamp = pd.Timestamp(timestamp)

    year = timestamp.year
    month = timestamp.strftime("%b")

    # --------------------------------------------------------
    # Select the appropriate yearly workbook
    # --------------------------------------------------------

    file_path = prices_folder / f"prices_{year}.xlsx"

    if not file_path.exists():
        raise FileNotFoundError(
            f"Historical price file not found: {file_path}"
        )

    # --------------------------------------------------------
    # Read the relevant month
    # --------------------------------------------------------

    try:
        prices = pd.read_excel(
            file_path,
            sheet_name=month
        )

    except ValueError:
        raise ValueError(
            f"Month sheet '{month}' was not found in {file_path}."
        )

    # --------------------------------------------------------
    # Clean column names
    # --------------------------------------------------------

    prices.columns = (
        prices.columns
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
    )

    # --------------------------------------------------------
    # Convert delivery date
    # --------------------------------------------------------

    prices["Delivery Date"] = pd.to_datetime(
        prices["Delivery Date"],
        errors="coerce"
    )

    prices["Delivery Hour"] = pd.to_numeric(
        prices["Delivery Hour"],
        errors="coerce"
    )

    prices["Delivery Interval"] = pd.to_numeric(
        prices["Delivery Interval"],
        errors="coerce"
    )

    # --------------------------------------------------------
    # Create timestamp
    # --------------------------------------------------------

    prices["Timestamp"] = (
        prices["Delivery Date"]
        + pd.to_timedelta(
            prices["Delivery Hour"] - 1,
            unit="h"
        )
        + pd.to_timedelta(
            (prices["Delivery Interval"] - 1) * 15,
            unit="m"
        )
    )

    # --------------------------------------------------------
    # Find matching price
    # --------------------------------------------------------

    match = prices[
        (prices["Timestamp"] == timestamp)
        & (
            prices["Settlement Point Name"]
            == settlement_point
        )
    ]

    if match.empty:
        raise ValueError(
            f"No ERCOT price found for "
            f"{settlement_point} at {timestamp}."
        )

    # --------------------------------------------------------
    # Get price in $/MWh
    # --------------------------------------------------------

    price_mwh = pd.to_numeric(
        match.iloc[0]["Settlement Point Price"],
        errors="coerce"
    )

    if pd.isna(price_mwh):
        raise ValueError(
            f"Invalid price for "
            f"{settlement_point} at {timestamp}."
        )

    # --------------------------------------------------------
    # Convert $/MWh -> $/kWh
    # --------------------------------------------------------

    price_kwh = price_mwh / 1000

    return float(price_kwh)


def get_historical_prices_bulk(
    start_date: datetime,
    end_date: datetime,
    settlement_point: str,
    prices_folder: Path = PRICES_FOLDER
) -> pd.DataFrame:
    """
    Retrieve ERCOT historical prices for a date range.
    
    This function efficiently retrieves all prices for the requested period
    by reading the relevant Excel files once rather than making individual
    calls for each timestamp.
    
    Parameters
    ----------
    start_date : datetime
        Start date for price retrieval (inclusive).
    
    end_date : datetime
        End date for price retrieval (inclusive).
    
    settlement_point : str
        ERCOT settlement point, e.g. "LZ_NORTH".
    
    prices_folder : Path
        Folder containing prices_2022.xlsx through prices_2026.xlsx.
    
    Returns
    -------
    pd.DataFrame
        DataFrame with columns:
        - Timestamp: pd.Timestamp for each 15-minute interval
        - Price ($/kWh): ERCOT price in $/kWh
    
    Raises
    ------
    ValueError
        If start_date > end_date or if settlement point is invalid.
    FileNotFoundError
        If required yearly Excel files do not exist.
    """
    
    if start_date > end_date:
        raise ValueError(
            f"start_date ({start_date}) must be <= end_date ({end_date})"
        )
    
    # Determine which years and months we need
    years = range(start_date.year, end_date.year + 1)
    
    all_prices = []
    
    for year in years:
        file_path = prices_folder / f"prices_{year}.xlsx"
        
        if not file_path.exists():
            raise FileNotFoundError(
                f"Historical price file not found: {file_path}"
            )
        
        # Determine which months to read for this year
        if year == start_date.year and year == end_date.year:
            # Same year - only read months in range
            start_month = start_date.month
            end_month = end_date.month
        elif year == start_date.year:
            # First year - read from start_month to December
            start_month = start_date.month
            end_month = 12
        elif year == end_date.year:
            # Last year - read from January to end_month
            start_month = 1
            end_month = end_date.month
        else:
            # Middle year - read all months
            start_month = 1
            end_month = 12
        
        # Read each month's data
        for month_num in range(start_month, end_month + 1):
            month_name = pd.Timestamp(year=year, month=month_num, day=1).strftime("%b")
            
            try:
                month_prices = pd.read_excel(
                    file_path,
                    sheet_name=month_name
                )
            except ValueError:
                # Month sheet doesn't exist - skip it
                continue
            
            # Clean column names
            month_prices.columns = (
                month_prices.columns
                .str.strip()
                .str.replace(r"\s+", " ", regex=True)
            )
            
            # Convert delivery date and time columns
            month_prices["Delivery Date"] = pd.to_datetime(
                month_prices["Delivery Date"],
                errors="coerce"
            )
            
            month_prices["Delivery Hour"] = pd.to_numeric(
                month_prices["Delivery Hour"],
                errors="coerce"
            )
            
            month_prices["Delivery Interval"] = pd.to_numeric(
                month_prices["Delivery Interval"],
                errors="coerce"
            )
            
            # Create timestamp
            month_prices["Timestamp"] = (
                month_prices["Delivery Date"]
                + pd.to_timedelta(
                    month_prices["Delivery Hour"] - 1,
                    unit="h"
                )
                + pd.to_timedelta(
                    (month_prices["Delivery Interval"] - 1) * 15,
                    unit="m"
                )
            )
            
            # Filter by settlement point
            month_prices = month_prices[
                month_prices["Settlement Point Name"] == settlement_point
            ].copy()
            
            # Convert price to $/kWh
            month_prices["Price ($/kWh)"] = pd.to_numeric(
                month_prices["Settlement Point Price"],
                errors="coerce"
            ) / 1000
            
            # Keep only needed columns
            month_prices = month_prices[["Timestamp", "Price ($/kWh)"]]
            
            all_prices.append(month_prices)
    
    if not all_prices:
        raise ValueError(
            f"No price data found for {settlement_point} "
            f"between {start_date} and {end_date}"
        )
    
    # Combine all months
    prices_df = pd.concat(all_prices, ignore_index=True)
    
    # Filter to exact date range
    prices_df = prices_df[
        (prices_df["Timestamp"] >= pd.Timestamp(start_date))
        & (prices_df["Timestamp"] <= pd.Timestamp(end_date))
    ].copy()
    
    # Sort by timestamp
    prices_df = prices_df.sort_values("Timestamp").reset_index(drop=True)
    
    # Remove any duplicates
    prices_df = prices_df.drop_duplicates(subset=["Timestamp"])
    
    return prices_df
