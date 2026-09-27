# Base Power Battery Simulator - Setup Instructions

This project consists of a Python FastAPI backend and a React TypeScript frontend.

## Prerequisites

- Python 3.9+
- Node.js 18+
- npm or yarn

---

## Backend Setup

### 1. Install Python Dependencies

```bash
cd Base_Hackathon2
pip install -r requirements.txt
```

If `requirements.txt` doesn't exist, install these packages:

```bash
pip install fastapi uvicorn pandas geopandas shapely pgeocode requests python-dotenv pydantic
```

### 2. Start the Backend Server

```bash
# From the Base_Hackathon2 directory
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The backend API will be available at: `http://localhost:8000`

**API Endpoint:**
- `POST /analyze-home` - Analyze a home's battery savings potential

**Request Body:**
```json
{
  "zip_code": "75201",
  "avg_annual_energy_kwh": 12000,
  "service_limit_amps": 200,
  "inverter_limit_kw": 11.0
}
```

---

## Frontend Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Start the Development Server

```bash
npm run dev
```

The frontend will be available at: `http://localhost:5173`

---

## Running the Complete Application

### Terminal 1 - Backend:
```bash
cd Base_Hackathon2
python -m uvicorn backend.main:app --reload --port 8000
```

### Terminal 2 - Frontend:
```bash
cd Base_Hackathon2/frontend
npm run dev
```

Then open your browser to `http://localhost:5173`

---

## Application Flow

1. **Input Screen** (`/`)
   - Enter annual electricity usage (kWh/year)
   - Enter Texas ZIP code
   - Click "Analyze My Home"

2. **Map Screen** (`/map`)
   - Confirm location on interactive Texas map
   - Search by ZIP or click on map
   - Click "Confirm & Analyze" to run analysis

3. **Results Screen** (`/results`)
   - View annual savings estimate
   - See battery performance metrics
   - Review cost comparison
   - Analyze charge/discharge patterns

---

## Data Requirements

The backend requires the following data files:

- `data/historical_prices/*.xlsx` - ERCOT historical price data
- `data/assumptions/residential_load_profile.csv` - Residential load profile
- `data/ercot_load_zones.geojson` - ERCOT load zone boundaries
- `data/tl_2019_us_zcta510/` - ZIP code boundary shapefiles

---

## Deployment

### Backend (Railway/Render/Heroku)

1. Create a `Procfile`:
```
web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

2. Deploy to your platform of choice

### Frontend (Vercel)

1. Update API URL in `frontend/src/components/MapScreen.tsx`:
```typescript
const response = await fetch('YOUR_BACKEND_URL/analyze-home', {
```

2. Deploy to Vercel:
```bash
cd frontend
npm run build
vercel --prod
```

Or connect your GitHub repo to Vercel for automatic deployments.

---

## Environment Variables

### Backend
Create `.env` file in `Base_Hackathon2/`:
```
# Add any API keys or configuration here
```

### Frontend
Create `.env` file in `frontend/`:
```
VITE_API_URL=http://localhost:8000
```

Then update the fetch call to use:
```typescript
const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
```

---

## Troubleshooting

### Backend Issues

**"Module not found" errors:**
- Ensure you're running from the `Base_Hackathon2` directory
- Check that all dependencies are installed: `pip install -r requirements.txt`

**"File not found" errors:**
- Verify all data files are in the correct locations
- Check file paths in the code match your directory structure

### Frontend Issues

**Tailwind CSS not working:**
- The `@tailwind` warnings in CSS are normal - Tailwind processes them at build time
- Ensure `tailwind.config.js` and `postcss.config.js` exist

**Map not displaying:**
- Check that Leaflet CSS is imported: `import 'leaflet/dist/leaflet.css'`
- Verify internet connection (map tiles load from OpenStreetMap)

**API connection failed:**
- Ensure backend is running on port 8000
- Check CORS settings in FastAPI (should allow localhost:5173)
- Verify the API URL in MapScreen.tsx matches your backend

---

## Tech Stack

**Backend:**
- FastAPI - Web framework
- Pandas - Data processing
- GeoPandas - Geospatial analysis
- Pgeocode - ZIP code geocoding

**Frontend:**
- React 19 + TypeScript
- Vite - Build tool
- TailwindCSS - Styling
- React Router - Navigation
- Leaflet - Interactive maps
- Lucide React - Icons

---

## Next Steps

1. ✅ Backend API is complete
2. ✅ Frontend screens are built
3. ⏳ Test the complete flow
4. ⏳ Deploy to production
5. ⏳ Add error handling improvements
6. ⏳ Add loading states and animations
7. ⏳ Implement proper geocoding for all Texas ZIP codes
