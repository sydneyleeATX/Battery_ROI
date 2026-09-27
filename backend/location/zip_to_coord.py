from typing import Optional, Tuple
import numpy as np
import pgeocode

# Initialize the US geocoder once outside the function to avoid re-downloading/reloading
_nomi = pgeocode.Nominatim("us")


def get_zip_centroid(zipcode: str | int) -> Tuple[Optional[float], Optional[float]]:
    """Returns (latitude, longitude) for a given 5-digit US ZIP code.

    Returns (None, None) if the ZIP code is invalid or not found.
    """

    # Convert to string and remove surrounding whitespace
    zipcode = str(zipcode).strip()

    # ZIP must contain only digits
    if not zipcode.isdigit():
        raise ValueError("ZIP code must contain only digits")

    # ZIP codes shorter than five digits are zero-padded
    zipcode = zipcode.zfill(5)

    # ZIP must be exactly five digits after padding
    if len(zipcode) != 5:
        raise ValueError("ZIP code must be exactly 5 digits")

    # Ensure standard 5-digit string format (e.g. preserves leading zeroes like '02138')
    clean_zip = str(zipcode).strip().zfill(5)

    result = _nomi.query_postal_code(clean_zip)

    lat = result.latitude
    lon = result.longitude

    if np.isnan(lat) or np.isnan(lon):
        return None, None

    return float(lat), float(lon)
