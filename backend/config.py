import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/base_roi"
    )
    
    ERCOT_API_KEY: str = os.getenv("ERCOT_API_KEY", "")
    ERCOT_API_URL: str = "https://api.ercot.com"
    
    CENSUS_GEOCODER_URL: str = "https://geocoding.geo.census.gov/geocoder"
    NOAA_API_URL: str = "https://www.ncdc.noaa.gov/cdo-web/api/v2"
    NOAA_API_KEY: str = os.getenv("NOAA_API_KEY", "")
    
    class Config:
        env_file = ".env"

settings = Settings()
