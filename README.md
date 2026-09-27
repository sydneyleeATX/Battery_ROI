# Base ROI Analysis

A comprehensive analysis tool for evaluating Base battery economics and reliability for Texas homeowners.

## Overview

This application helps Texas homeowners understand the economic value and reliability benefits of installing a Base battery system. It analyzes:

- **Economic Value**: Estimated annual savings, ROI, and payback period
- **Grid Services**: Battery dispatch optimization based on ERCOT wholesale prices

## Architecture

```
React Frontend → FastAPI Backend 
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
- [] Create project structure
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
```

**Request:**
```json
{
  "zip_code": "76201",
  "monthly_bill": 250
}
**Response:**
```json
{
  "location": {
    "zip_code": "76201",
    "settlement_point": "LZ_NORTH",
    "latitude": 33.2148,
    "longitude": -97.1331
  },
  "customer": {
    "avg_annual_energy_kwh": 12000,
    "service_limit_amps": 200
  },
  "battery": {
    "capacity_kwh": 39.2,
    "nominal_power_kw": 11,
    "efficiency": 0.9
  },
  "price_thresholds": {
    "1": { "charge": 0.035, "discharge": 0.075 },
    "2": { "charge": 0.034, "discharge": 0.073 },
    "3": { "charge": 0.032, "discharge": 0.071 },
    "4": { "charge": 0.031, "discharge": 0.070 },
    "5": { "charge": 0.033, "discharge": 0.074 },
    "6": { "charge": 0.036, "discharge": 0.080 },
    "7": { "charge": 0.038, "discharge": 0.085 },
    "8": { "charge": 0.037, "discharge": 0.082 },
    "9": { "charge": 0.034, "discharge": 0.076 },
    "10": { "charge": 0.032, "discharge": 0.071 },
    "11": { "charge": 0.033, "discharge": 0.072 },
    "12": { "charge": 0.034, "discharge": 0.074 }
  },
  "simulation": {
    "simulation_start": "2025-09-27T00:00:00",
    "simulation_end": "2026-09-26T23:45:00",
    "total_savings": 420.5,
    "charging_cost": 180.0,
    "discharging_value": 600.0,
    "net_economic_benefit": 420.0,
    "charge_events": 100,
    "discharge_events": 98,
    "starting_soc_kwh": 19.6,
    "ending_soc_kwh": 20.0,
    "backup_reserve_violations": 0,
    "baseline_cost": 1500.0,
    "battery_cost": 1079.5
  },
  "metadata": {
    "analysis_date": "2026-09-27T12:00:00",
    "data_period_start": "2025-09-27T12:00:00",
    "data_period_end": "2026-09-27T12:00:00",
    "simulation_period_start": "2025-09-27T00:00:00",
    "simulation_period_end": "2026-09-26T23:45:00"
  }
}
```





