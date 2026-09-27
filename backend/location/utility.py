import pandas as pd


UTILITY_DATA = pd.read_csv(
    "data/utility/iou_zipcodes_2024.csv"
)


def get_utility(zip_code: str) -> str:
    """
    Return the electric utility associated with a ZIP code.

    Args:
        zip_code: Five-digit U.S. ZIP code.

    Returns:
        Electric utility name.

    Raises:
        ValueError: If ZIP code is invalid or not found.
    """

    # Convert to string and remove surrounding whitespace
    zip_code = str(zip_code).strip()

    # ZIP must contain only digits
    if not zip_code.isdigit():
        raise ValueError("ZIP code must contain only digits")

    # ZIP codes shorter than five digits are zero-padded
    zip_code = zip_code.zfill(5)

    # ZIP must be exactly five digits after padding
    if len(zip_code) != 5:
        raise ValueError("ZIP code must be exactly 5 digits")

    # Find ZIP code in utility dataset
    match = UTILITY_DATA[
        UTILITY_DATA["zip"] == int(zip_code)
    ]

    if match.empty:
        raise ValueError(f"ZIP code not found: {zip_code}")

    # Return utility name
    return match.iloc[0]["utility_name"]