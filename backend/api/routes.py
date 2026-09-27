from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from backend.api.home_analysis import analyze_home as analyze_home_helper

router = APIRouter()


class HomeAnalysisRequest(BaseModel):
    """Request model for home battery analysis."""
    zip_code: str
    avg_annual_energy_kwh: float
    service_limit_amps: Optional[float] = 200
    inverter_limit_kw: Optional[float] = 11.0


class HomeAnalysisResponse(BaseModel):
    """Response model for home battery analysis."""
    location: dict
    customer: dict
    battery: dict
    price_thresholds: dict
    simulation: dict
    metadata: dict


@router.post("/analyze-home", response_model=HomeAnalysisResponse)
async def analyze_home_endpoint(request: HomeAnalysisRequest):
    """
    Analyze a customer's home for battery savings potential.
    
    This endpoint calculates potential battery savings based on:
    - Customer location (ZIP code)
    - Annual energy consumption
    - Location-specific ERCOT pricing
    - Local weather conditions
    
    Returns comprehensive analysis including:
    - Location information (load zone, settlement point)
    - Battery performance simulation
    - Economic savings calculations
    - Monthly price thresholds
    """
    try:
        result = analyze_home_helper(
            zip_code=request.zip_code,
            avg_annual_energy_kwh=request.avg_annual_energy_kwh,
            service_limit_amps=request.service_limit_amps,
            inverter_limit_kw=request.inverter_limit_kw,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=f"Required data file missing: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
