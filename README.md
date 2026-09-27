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
│   └── database/     # Database models and connection
├── frontend/         # React application
├── data/            # Data storage
│   ├── raw/         # Raw downloaded data
│   ├── processed/   # Cleaned/normalized data
│   └── reference/   # Reference datasets
└── tests/           # Test suite
```

## Data Sources

- **ERCOT**: Historical RTM load-zone prices and load profiles
- **HIFLD**: Electric retail service territories
- **PUCT**: Utility reliability data (SAIDI/SAIFI)
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

2. Set up PostgreSQL database:
```bash
createdb base_roi
psql base_roi -c "CREATE EXTENSION postgis;"
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and database credentials
```

4. Run the backend:
```bash
cd backend
python main.py
```

## Development Phases

### Phase 1 — Data Foundation
- [x] Create project structure
- [ ] Set up PostgreSQL/PostGIS
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
- [ ] Build SOC model
- [ ] Build charge/discharge constraints
- [ ] Build reserve constraint
- [ ] Build dispatch simulator
- [ ] Backtest against historical ERCOT data

### Phase 5 — Economics
- [ ] Add Base pricing by utility
- [ ] Calculate annual value
- [ ] Calculate annual net cost
- [ ] Calculate payback
- [ ] Calculate 5-year value

### Phase 6 — Reliability
- [ ] Collect PUCT SAIDI/SAIFI data
- [ ] Build utility reliability table
- [ ] Normalize reliability
- [ ] Calculate reliability score
- [ ] Calculate personalized backup duration

### Phase 7 — Product
- [ ] Build /analyze-home API endpoint
- [ ] Build React input screen
- [ ] Add Texas map
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
  },
  "economics": {
    "annual_value": 843,
    "installation_cost": 695,
    "monthly_fee": 19,
    "five_year_net_value": 3270,
    "payback_years": 1.34
  },
  "reliability": {
    "saifi": 1.2,
    "saidi_hours": 145,
    "score": 74
  }
}
```

## License

MIT
