from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class HomeAnalysisRequest(BaseModel):
    zip_code: str
    monthly_bill: float

class HomeAnalysisResponse(BaseModel):
    location: dict
    home: dict
    battery: dict
    economics: dict
    reliability: dict

@router.post("/analyze-home", response_model=HomeAnalysisResponse)
async def analyze_home(request: HomeAnalysisRequest):
    raise HTTPException(status_code=501, detail="Not implemented yet")
