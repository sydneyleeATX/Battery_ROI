from sqlalchemy import Column, Integer, String, Float, DateTime, DECIMAL
from sqlalchemy.ext.declarative import declarative_base
from geoalchemy2 import Geometry

Base = declarative_base()

class Location(Base):
    __tablename__ = "locations"
    
    id = Column(Integer, primary_key=True)
    zip = Column(String(5), index=True)
    latitude = Column(Float)
    longitude = Column(Float)
    utility = Column(String(100))
    ercot_zone = Column(String(50))

class ERCOTPrice(Base):
    __tablename__ = "ercot_prices"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, index=True)
    zone = Column(String(50), index=True)
    price_mwh = Column(DECIMAL(10, 2))
    price_kwh = Column(DECIMAL(10, 6))

class ERCOTLoad(Base):
    __tablename__ = "ercot_load"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, index=True)
    weather_zone = Column(String(50), index=True)
    load_mw = Column(Float)

class Weather(Base):
    __tablename__ = "weather"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, index=True)
    location = Column(String(100))
    temperature_f = Column(Float)

class UtilityReliability(Base):
    __tablename__ = "utility_reliability"
    
    id = Column(Integer, primary_key=True)
    utility = Column(String(100), index=True)
    year = Column(Integer)
    saifi = Column(Float)
    saidi_hours = Column(Float)

class UtilityRate(Base):
    __tablename__ = "utility_rates"
    
    id = Column(Integer, primary_key=True)
    utility = Column(String(100), index=True)
    year = Column(Integer)
    residential_rate_kwh = Column(DECIMAL(10, 6))

class BasePlan(Base):
    __tablename__ = "base_plans"
    
    id = Column(Integer, primary_key=True)
    utility = Column(String(100), index=True)
    battery_count = Column(Integer)
    installation_fee = Column(DECIMAL(10, 2))
    monthly_fee = Column(DECIMAL(10, 2))
    energy_rate = Column(DECIMAL(10, 6))
    effective_date = Column(DateTime)
    expiration_date = Column(DateTime)

class UtilityTerritory(Base):
    __tablename__ = "utility_territories"
    
    id = Column(Integer, primary_key=True)
    geometry = Column(Geometry('MULTIPOLYGON'))
    utility_name = Column(String(100), index=True)
    eia_utility_id = Column(String(50))
    state = Column(String(2))
