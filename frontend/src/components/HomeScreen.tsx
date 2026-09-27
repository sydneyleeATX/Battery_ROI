import { useState } from 'react';
import type { FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Check, LoaderCircle, Zap } from 'lucide-react';

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '');

interface AnalysisResults {
  location: { zip_code: string; settlement_point: string };
  customer: { avg_annual_energy_kwh: number };
  battery: { capacity_kwh: number; nominal_power_kw: number; efficiency: number };
  simulation: { total_savings: number; baseline_cost: number; battery_cost: number; charging_cost: number; discharging_value: number; charge_events: number; discharge_events: number; starting_soc_kwh: number; ending_soc_kwh: number };
  metadata: { simulation_period_start: string; simulation_period_end: string };
}

export default function HomeScreen() {
  const navigate = useNavigate();
  const [annualUsage, setAnnualUsage] = useState('');
  const [zipCode, setZipCode] = useState('');
  const [errors, setErrors] = useState<{ usage?: string; zip?: string }>({});
  const [requestError, setRequestError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleAnalyze = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const usage = Number(annualUsage);
    const nextErrors: { usage?: string; zip?: string } = {};
    if (!Number.isFinite(usage) || usage < 1000 || usage > 50000) nextErrors.usage = 'Enter annual usage between 1,000 and 50,000 kWh.';
    if (!/^\d{5}$/.test(zipCode)) nextErrors.zip = 'Enter a valid 5-digit ZIP code.';
    setErrors(nextErrors);
    setRequestError('');
    if (Object.keys(nextErrors).length) return;

    setIsSubmitting(true);
    sessionStorage.removeItem('analysisResults');
    try {
      const response = await fetch(`${API_BASE_URL}/analyze-home`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ zip_code: zipCode, avg_annual_energy_kwh: usage }),
      });
      if (!response.ok) {
        let message = `Analysis request failed (${response.status}).`;
        const errorBody = await response.json().catch(() => null);
        if (typeof errorBody?.detail === 'string') message = errorBody.detail;
        throw new Error(message);
      }
      const results = (await response.json()) as AnalysisResults;
      sessionStorage.setItem('analysisResults', JSON.stringify(results));
      navigate('/results');
    } catch (error) {
      setRequestError(error instanceof TypeError
        ? `Could not connect to the analysis API at ${API_BASE_URL}. Check VITE_API_URL and make sure the backend is running.`
        : error instanceof Error ? error.message : 'Unable to complete the analysis. Try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="site-shell">
      <header className="site-header">
        <a className="brand" href="/" aria-label="Base Power home energy analysis">
          <span className="brand-mark"><Zap size={17} fill="currentColor" /></span><span className="brand-name">BASE<span>POWER</span></span>
        </a>
        <span className="header-label">HOME BATTERY ANALYSIS</span>
      </header>
      <main className="input-main">
        <section className="intro-panel" aria-labelledby="page-title">
          <div className="eyebrow"><span className="eyebrow-line" /> ENERGY THAT WORKS HARDER</div>
          <h1 id="page-title">Your home.<br /><span>Your power.</span></h1>
          <p className="intro-copy">See how a home battery could work with your energy use and local electricity market.</p>
          <div className="promise-list" aria-label="Analysis details">
            <div className="promise-item"><span><Check size={14} /></span> Local ERCOT pricing</div>
            <div className="promise-item"><span><Check size={14} /></span> Your annual energy use</div>
            <div className="promise-item"><span><Check size={14} /></span> Historical weather patterns</div>
          </div>
          <div className="intro-footnote">A personalized estimate, built from real market history.</div>
        </section>
        <section className="form-panel" aria-labelledby="form-title">
          <div className="form-heading"><p className="form-kicker">LET'S GET STARTED</p><h2 id="form-title">Tell us about your home</h2><p>We’ll use these details to shape your estimate.</p></div>
          <form className="analysis-form" onSubmit={handleAnalyze} noValidate>
            <div className="field-group">
              <label htmlFor="annual-usage">Annual electricity use</label>
              <div className={`field-wrap ${errors.usage ? 'field-invalid' : ''}`}>
                <input id="annual-usage" type="number" min="1000" max="50000" step="1" inputMode="numeric" value={annualUsage} onChange={(event) => setAnnualUsage(event.target.value)} placeholder="12,000" aria-invalid={Boolean(errors.usage)} aria-describedby={errors.usage ? 'usage-error usage-hint' : 'usage-hint'} />
                <span className="field-unit">kWh / year</span>
              </div>
              {errors.usage && <p className="field-error" id="usage-error">{errors.usage}</p>}
              <p className="field-hint" id="usage-hint">Find this on your electricity bill. Typical homes use 5,000–20,000 kWh.</p>
            </div>
            <div className="field-group">
              <label htmlFor="zip-code">Home ZIP code</label>
              <div className={`field-wrap ${errors.zip ? 'field-invalid' : ''}`}>
                <input id="zip-code" type="text" inputMode="numeric" autoComplete="postal-code" maxLength={5} value={zipCode} onChange={(event) => setZipCode(event.target.value.replace(/\D/g, '').slice(0, 5))} placeholder="75201" aria-invalid={Boolean(errors.zip)} aria-describedby={errors.zip ? 'zip-error zip-hint' : 'zip-hint'} />
                <span className="zip-state">TEXAS</span>
              </div>
              {errors.zip && <p className="field-error" id="zip-error">{errors.zip}</p>}
              <p className="field-hint" id="zip-hint">Used to find your ERCOT region and local weather history.</p>
            </div>
            {requestError && <div className="request-error" role="alert">{requestError}</div>}
            <button className="submit-button" type="submit" disabled={isSubmitting}>
              {isSubmitting ? <><LoaderCircle size={18} className="spin-icon" /> Building your estimate</> : <>See my estimate <ArrowRight size={18} /></>}
            </button>
            <p className="privacy-note">Your information is used only to calculate this estimate.</p>
          </form>
        </section>
      </main>
      <footer className="site-footer"><span>BASE POWER <span className="footer-divider">/</span> HOME ENERGY ANALYSIS</span><span>Estimate based on historical ERCOT data</span></footer>
    </div>
  );
}