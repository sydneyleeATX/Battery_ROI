import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, ArrowRight, BatteryCharging, CalendarDays, ChartNoAxesCombined, Zap } from 'lucide-react';

interface AnalysisResults {
  location: { zip_code: string; settlement_point: string; latitude: number; longitude: number };
  customer: { avg_annual_energy_kwh: number; service_limit_amps: number };
  battery: { capacity_kwh: number; nominal_power_kw: number; efficiency: number };
  simulation: { total_savings: number; baseline_cost: number; battery_cost: number; charging_cost: number; discharging_value: number; charge_events: number; discharge_events: number; starting_soc_kwh: number; ending_soc_kwh: number };
  metadata: { simulation_period_start: string; simulation_period_end: string };
}

const money = (value: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value);

export default function AnalysisResultsScreen() {
  const navigate = useNavigate();
  const [results] = useState<AnalysisResults | null>(() => {
    const storedResults = sessionStorage.getItem('analysisResults');
    return storedResults ? JSON.parse(storedResults) as AnalysisResults : null;
  });
  useEffect(() => { if (!results) navigate('/', { replace: true }); }, [navigate, results]);
  if (!results) return null;
  const savings = results.simulation.total_savings;
  const savingsPercent = results.simulation.baseline_cost ? savings / results.simulation.baseline_cost * 100 : 0;
  const periodStart = new Date(results.metadata.simulation_period_start).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  const periodEnd = new Date(results.metadata.simulation_period_end).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

  return (
    <div className="site-shell results-shell">
      <header className="site-header">
        <a className="brand" href="/" aria-label="Base Power home energy analysis"><span className="brand-mark"><Zap size={17} fill="currentColor" /></span><span className="brand-name">BASE<span>POWER</span></span></a>
        <button className="text-link" onClick={() => navigate('/')}><ArrowLeft size={16} /> New analysis</button>
      </header>
      <main className="results-main">
        <div className="results-heading"><div><p className="eyebrow"><span className="eyebrow-line" /> YOUR HOME ENERGY SNAPSHOT</p><h1>More insight.<br /><span>More power.</span></h1></div><div className="location-tag"><span className="location-dot" /> ZIP {results.location.zip_code}<span className="location-divider">/</span>{results.location.settlement_point}</div></div>
        <section className="savings-band" aria-label="Estimated annual savings">
          <div className="savings-copy"><p className="form-kicker">ESTIMATED ANNUAL {savings >= 0 ? 'SAVINGS' : 'COST CHANGE'}</p><p className={`savings-value ${savings < 0 ? 'negative-value' : ''}`}>{savings < 0 ? '−' : ''}{money(Math.abs(savings))}</p><p className="savings-caption">{savings >= 0 ? `${Math.abs(savingsPercent).toFixed(1)}% lower modeled electricity costs` : `${Math.abs(savingsPercent).toFixed(1)}% higher modeled electricity costs`}</p></div>
          <div className="savings-mark" aria-hidden="true"><ChartNoAxesCombined size={38} strokeWidth={1.4} /></div>
          <div className="monthly-note"><span>AVERAGE PER MONTH</span><strong>{savings < 0 ? '−' : ''}{money(Math.abs(savings / 12))}</strong></div>
        </section>
        <section className="metrics-grid" aria-label="Analysis summary">
          <article className="metric-item"><span className="metric-icon"><Zap size={18} /></span><p className="metric-label">ANNUAL ENERGY USE</p><p className="metric-value">{results.customer.avg_annual_energy_kwh.toLocaleString()} <span>kWh</span></p></article>
          <article className="metric-item"><span className="metric-icon"><BatteryCharging size={18} /></span><p className="metric-label">BATTERY ACTIVITY</p><p className="metric-value">{results.simulation.charge_events + results.simulation.discharge_events} <span>events</span></p><p className="metric-detail">{results.simulation.charge_events} charges · {results.simulation.discharge_events} discharges</p></article>
          <article className="metric-item"><span className="metric-icon"><CalendarDays size={18} /></span><p className="metric-label">SIMULATION PERIOD</p><p className="metric-value metric-period">{periodStart} – {periodEnd}</p></article>
        </section>
        <section className="details-section">
          <div className="section-heading"><div><p className="form-kicker">THE BREAKDOWN</p><h2>How the estimate adds up</h2></div><span className="market-label">{results.location.settlement_point} MARKET</span></div>
          <div className="details-grid">
            <article className="detail-column"><h3>Electricity costs</h3><div className="detail-row"><span>Without battery</span><strong>{money(results.simulation.baseline_cost)}</strong></div><div className="detail-row"><span>With battery</span><strong>{money(results.simulation.battery_cost)}</strong></div><div className="detail-row detail-total"><span>{savings >= 0 ? 'Estimated savings' : 'Estimated added cost'}</span><strong>{savings < 0 ? '−' : ''}{money(Math.abs(savings))}</strong></div></article>
            <article className="detail-column"><h3>Battery system</h3><div className="detail-row"><span>Energy capacity</span><strong>{results.battery.capacity_kwh} kWh</strong></div><div className="detail-row"><span>Power output</span><strong>{results.battery.nominal_power_kw} kW</strong></div><div className="detail-row"><span>Round-trip efficiency</span><strong>{(results.battery.efficiency * 100).toFixed(0)}%</strong></div><div className="detail-row"><span>Charging / discharge value</span><strong>{money(results.simulation.charging_cost)} / {money(results.simulation.discharging_value)}</strong></div></article>
          </div>
        </section>
        <div className="data-note">Historical estimate based on ERCOT pricing and local weather from {periodStart} to {periodEnd}.</div>
        <button className="submit-button results-cta" onClick={() => navigate('/')}>Analyze another home <ArrowRight size={18} /></button>
      </main>
      <footer className="site-footer"><span>BASE POWER <span className="footer-divider">/</span> HOME ENERGY ANALYSIS</span><span>Estimates are illustrative and based on historical data.</span></footer>
    </div>
  );
}