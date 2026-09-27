import pandas as pd
from pathlib import Path


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

