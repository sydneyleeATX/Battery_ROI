from shapely.geometry import Point
import geopandas as gpd
from backend.location.zip_to_coord import get_zip_centroid

LOAD_ZONES = gpd.read_file(
    "data/load_zones/ercot_load_zones.geojson"
)

def get_ercot_load_zone(zip_code: str | int) -> str:
    """
    Determine ERCOT load zone based on ZIP Centroid
    
    Args: Zip code
        
    Returns:
        ERCOT zone (LZ_NORTH, LZ_SOUTH, LZ_WEST, LZ_HOUSTON)
    """

    # Get ZIP centroid
    latitude, longitude = get_zip_centroid(zip_code)

    if latitude is None or longitude is None:
        raise ValueError(
            f"ZIP code could not be located: {zip_code}"
        )

    # Create point.
    # IMPORTANT: Shapely uses (longitude, latitude).
    point = Point(longitude, latitude)

    # Put point into GeoDataFrame using same CRS as GeoJSON.
    point_gdf = gpd.GeoDataFrame(
        {"zip": [str(zip_code)]},
        geometry=[point],
        crs="EPSG:4326",
    )

    # Match CRS if necessary.
    if LOAD_ZONES.crs != point_gdf.crs:
        point_gdf = point_gdf.to_crs(LOAD_ZONES.crs)

    # Find polygon containing point.
    match = gpd.sjoin(
        point_gdf,
        LOAD_ZONES,
        how="inner",
        predicate="within",
    )

    if match.empty:
        raise ValueError(
            f"ZIP centroid is not inside an ERCOT Load Zone: {zip_code}"
        )

    if len(match) > 1:
        raise ValueError(
            f"ZIP centroid matched multiple ERCOT Load Zones: {zip_code}"
        )

    return match.iloc[0]["NAME"]


