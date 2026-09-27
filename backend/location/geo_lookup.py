import geopandas as gpd


# Load Census ZCTA data
zcta = gpd.read_file("data/zcta/tl_2020_us_zcta520.shp")


def lookup_zip(zip_code: str) -> dict:
    """
    Look up the representative latitude/longitude for a ZIP code
    using the Census ZCTA dataset.
    """

    zip_code = str(zip_code).zfill(5)

    match = zcta[zcta["ZCTA5CE20"] == zip_code]

    if match.empty:
        raise ValueError(f"ZIP code not found: {zip_code}")

    row = match.iloc[0]

    return {
        "zip": zip_code,
        "latitude": float(row["INTPTLAT20"]),
        "longitude": float(row["INTPTLON20"]),
    }



