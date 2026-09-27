export function createDemoAnalysisResults(zipCode: string, annualUsage: number) {
  const endDate = new Date();
  endDate.setMinutes(Math.floor(endDate.getMinutes() / 15) * 15, 0, 0);

  const startDate = new Date(endDate);
  startDate.setDate(startDate.getDate() - 365);
  startDate.setMinutes(0, 0, 0);

  const baselineCost = Number((annualUsage * 0.12).toFixed(2));
  const totalSavings = Number((baselineCost * 0.28).toFixed(2));
  const chargingCost = Number((baselineCost * 0.12).toFixed(2));

  return {
    location: {
      zip_code: zipCode,
      settlement_point: 'SIMULATED',
      latitude: 0,
      longitude: 0,
    },
    customer: {
      avg_annual_energy_kwh: annualUsage,
      service_limit_amps: 200,
    },
    battery: {
      capacity_kwh: 39.2,
      nominal_power_kw: 11,
      efficiency: 0.9,
    },
    simulation: {
      total_savings: totalSavings,
      baseline_cost: baselineCost,
      battery_cost: Number((baselineCost - totalSavings).toFixed(2)),
      charging_cost: chargingCost,
      discharging_value: Number((chargingCost + totalSavings).toFixed(2)),
      charge_events: Math.round(annualUsage / 120),
      discharge_events: Math.round(annualUsage / 125),
      starting_soc_kwh: 19.6,
      ending_soc_kwh: 20,
    },
    metadata: {
      simulation_period_start: startDate.toISOString(),
      simulation_period_end: endDate.toISOString(),
      demo_mode: true,
    },
  };
}