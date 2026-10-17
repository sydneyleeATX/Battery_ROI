# Base Power Home Battery Analysis

## Objective

- Estimate how a home battery could affect a Texas household's electricity costs using its ZIP code and annual usage.
- Results are illustrative; the model does not yet calculate retail-plan bills, ROI, or outage reliability.

## Data Sources

| Data | Source / granularity | Use |
|---|---|---|
| ERCOT load profiles | ERCOT, 15-minute by zone | Available, but not used in the home simulation. |
| ERCOT load zones | Local GeoJSON polygons | Map ZIP centroid to a pricing area. |
| ERCOT wholesale prices | [ERCOT market prices](https://www.ercot.com/mktinfo/prices), 15-minute by settlement point | Build monthly dispatch thresholds and interval costs. |
| Temperature | [Open-Meteo Archive API](https://archive-api.open-meteo.com/v1/archive), hourly | Estimate battery power derating. |
| Home load shape | Local CSV, 96 intervals per typical day | Approximate household usage, scaled to annual kWh. |
| Battery specs | Fixed model assumptions | Set capacity, efficiency, power, and state-of-charge limits. |

The price loader expects annual Excel workbooks with monthly sheets. The repository contains a CSV instead, so the live analysis needs compatible workbooks or a loader update.

## Data Preparation

- Build one row per 15-minute interval with price, home load, temperature, derating, and settlement point.
- Scale and repeat a typical daily load profile; it is not household meter data.
- Forward-fill missing values; drop rows still incomplete and report fill counts.
- Calculate monthly charge/discharge thresholds at the 25th and 75th price percentiles.

## Simulation

- Battery model: 39.2 kWh, 11 kW, 90% efficiency, 20% reserve; starts at 50% state of charge.
- Each interval calculates baseline cost, then charges below the monthly 25th percentile or discharges above the 75th, subject to battery, temperature, service-panel, and inverter limits.
- Estimated residential price is ERCOT wholesale price multiplied by 3.
- Savings = baseline cost without battery - modeled cost with battery. Discharge offsets home use; surplus is not exported.

## Challenges

- Wholesale prices times a fixed multiplier may not match a customer's retail plan.
- A standardized load shape may not represent an individual home's interval usage.
- Weather retrieval, data preparation, and sequential processing of about 35,000 intervals can make a one-year run slow; runtime is not benchmarked.
- The price loader expects Excel workbooks, while the repository contains a CSV.

## Future Work

- Benchmark and optimize data loading and simulation; cache reusable inputs.
- Evaluate PostgreSQL for indexed, consistent data storage. It may speed up data retrieval, but not necessarily the CPU-bound simulation.
- Reconcile price formats and build repeatable data ingestion and validation.
- Use ERCOT load data to improve regional and seasonal household load shapes.
- Add PUCT SAIFI/SAIDI reliability scoring and personalized backup-duration simulation.
- Incorporate retail plans and validate assumptions against historical outcomes.

## Tech Stack

- **Frontend:** React, TypeScript, Vite, React Router, Tailwind CSS.
- **Backend:** Python, FastAPI, Pydantic, Uvicorn, pandas, NumPy, GeoPandas, Shapely, `pgeocode`, Requests.
- **Data:** Local CSV, GeoJSON, and expected Excel workbooks; PostgreSQL/PostGIS dependencies are present but unused by the current analysis path.
- **Tests:** pytest; frontend TypeScript and ESLint checks.

## Quickstart

**Requirements:** Python 3.10+, Node.js/npm, geospatial dependencies, network access for weather, and compatible ERCOT price workbooks.

1. Install Python dependencies from the repository root:

```bash
python -m pip install -r requirements.txt geopandas shapely pgeocode openpyxl
```

2. Start the backend from the repository root:

```bash
python -m uvicorn backend.main:app --reload --port 8000
```

3. In a second terminal, install and start the frontend:

```bash
cd frontend
npm install
npm run dev
```

4. Open the Vite URL shown in the terminal. Set `VITE_API_URL` if the backend is not at `http://localhost:8000`.

> Live analysis requires annual `prices_<year>.xlsx` workbooks; the checked-in price CSV is not compatible with the current loader. Add compatible workbooks or update the loader. For a frontend-only demo, add `?demo=true`.

## API Example

**Request:** `POST http://localhost:8000/analyze-home`

```json
{
	"zip_code": "75201",
	"avg_annual_energy_kwh": 12000,
	"service_limit_amps": 200,
	"inverter_limit_kw": 11.0
}
```

**Response (selected fields; values illustrative):**

```json
{
	"location": {
		"zip_code": "75201",
		"settlement_point": "LZ_NORTH",
		"latitude": 32.78,
		"longitude": -96.80
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
	"simulation": {
		"total_savings": 420.5,
		"baseline_cost": 1500.0,
		"battery_cost": 1079.5,
		"charge_events": 100,
		"discharge_events": 98
	},
	"metadata": {
		"simulation_period_start": "2025-09-27T00:00:00",
		"simulation_period_end": "2026-09-26T23:45:00"
	}
}
```


