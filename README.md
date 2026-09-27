# Base ROI Analysis

A comprehensive analysis tool for evaluating Base battery economics and reliability for Texas homeowners.

## Overview

This application helps Texas homeowners understand the economic value and reliability benefits of installing a Base battery system. It analyzes:

- **Economic Value**: Estimated annual savings, ROI, and payback period
- **Reliability**: Utility-level reliability metrics (SAIDI/SAIFI) and personalized backup duration
- **Grid Services**: Battery dispatch optimization based on ERCOT wholesale prices

## Architecture

```
React Frontend → FastAPI Backend → PostgreSQL/PostGIS Database
                      ↓
        Location Engine | Energy Model | Reliability Model
                      ↓
              Battery Value Model
                      ↓
           Personalized Results
```

## Project Structure

```
base-roi/
├── backend/           # FastAPI backend
│   ├── api/          # API routes
│   ├── location/     # Geocoding and utility mapping
│   ├── data/         # Data ingestion (ERCOT, weather, reliability)
│   ├── models/       # Load, battery, dispatch, ROI models
│   
├── frontend/         # React application
├── data/            # Data storage
│   ├── raw/         # Raw downloaded data
│   ├── processed/   # Cleaned/normalized data
│   └── reference/   # Reference datasets
└── tests/           # Test suite
```

## Data Sources

- **ERCOT**: Historical RTM load-zone prices and load profiles
- **NOAA**: Historical weather data
- **EIA-861**: Utility rates and service territories

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ with PostGIS extension
- Node.js 18+ (for frontend)

### Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and database credentials
```

3. Run the backend:
```bash
cd backend
python main.py
```

## Development Phases

### Phase 1 — Data Foundation
- [x] Create project structure
- [ ] Download utility territory data
- [ ] Build ZIP/location → utility function
- [ ] Build utility → ERCOT zone mapping

### Phase 2 — ERCOT
- [ ] Register for ERCOT API
- [ ] Download historical RTM load-zone prices
- [ ] Store normalized 15-minute prices
- [ ] Download historical ERCOT load profiles
- [ ] Store normalized load data

### Phase 3 — Home Model
- [ ] Build bill → kWh estimator
- [ ] Build synthetic 15-minute residential load model
- [ ] Add temperature dependence
- [ ] Validate monthly energy consumption

### Phase 4 — Battery
- [ ] Encode Base Core specifications
- [ ] Build charge/discharge constraints
- [ ] Build reserve constraint
- [ ] Build dispatch simulator
- [ ] Backtest against historical ERCOT data

### Phase 5 — Product
- [ ] Build /analyze-home API endpoint
- [ ] Build React input screen
- [ ] Add results screen
- [ ] Add methodology/assumptions
- [ ] Deploy

## API Endpoints

### POST /analyze-home

Analyze a home's Base battery economics and reliability.

**Request:**
```json
{
  "zip_code": "76201",
  "monthly_bill": 250
}
```

**Response:**
```json
{
  "location": {
    "zip": "76201",
    "utility": "Oncor",
    "ercot_zone": "LZ_NORTH"
  },
  "home": {
    "monthly_bill": 250,
    "estimated_monthly_kwh": 1667
  },
  "battery": {
    "capacity_kwh": 39.2,
    "backup_hours": 14.8
  }
}
```


