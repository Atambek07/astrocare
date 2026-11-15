'use client';

import { useEffect, useState } from 'react';
import { Activity, FlaskConical, Pause, Play, RotateCcw, ShieldCheck, Zap } from 'lucide-react';
import { useHealthStore } from '@/store/useHealthStore';
import { fetchBackendJson } from '@/lib/backend';

interface SimulationStatus {
  mission_status: string;
  mission_time_seconds: number;
  mission_day: number;
  mission_phase: string;
  simulation_speed: number;
  active_scenarios: string[];
  active_astronauts: string[];
}

interface SimulationStatusResponse {
  status: SimulationStatus;
  astronauts: string[];
  environment: Record<string, unknown>;
  mode: string;
}

const SCENARIOS = [
  'HYPERCAPNIC_CABIN',
  'NEUROCOGNITIVE_FATIGUE',
  'SANS_FLUID_SHIFT',
  'SOLAR_PARTICLE_EVENT',
  'MISSED_ARED',
  'ENVIRONMENTAL_EQUIPMENT_MALFUNCTION',
];

const COUNTERMEASURES = [
  'ARED',
  'AEROBIC_EXERCISE',
  'SLEEP_INTERVENTION',
  'ENVIRONMENTAL_CORRECTION',
];

async function postJson<T>(url: string, body: unknown): Promise<T> {
  return fetchBackendJson<T>(url, { method: 'POST', body });
}

/** Simulation controls backed by the unified AstroCare service. */
export function SimulationView() {
  const set = useHealthStore((s) => s.set);
  const [status, setStatus] = useState<SimulationStatus | null>(null);
  const [environment, setEnvironment] = useState<Record<string, unknown> | null>(null);
  const [astronauts, setAstronauts] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const payload = await fetchBackendJson<SimulationStatusResponse>('/simulation/status');
        if (cancelled) return;
        setStatus(payload.status);
        setEnvironment(payload.environment);
        setAstronauts(payload.astronauts);
        setError(null);
      } catch (exc) {
        if (!cancelled) setError(exc instanceof Error ? exc.message : 'simulation service unavailable');
      }
    };
    load();
    const timer = setInterval(load, 2000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  const sendControl = async (body: Record<string, unknown>) => {
    setBusy(true);
    try {
      await postJson('/simulation/control', body);
      setError(null);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : 'control failed');
    } finally {
      setBusy(false);
    }
  };

  const sendScenario = async (scenario_id: string, action: 'start' | 'terminate') => {
    setBusy(true);
    try {
      await postJson('/simulation/scenario', { scenario_id, action });
      setError(null);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : 'scenario control failed');
    } finally {
      setBusy(false);
    }
  };

  const sendCountermeasure = async (type: string) => {
    setBusy(true);
    try {
      await postJson('/simulation/countermeasure', { type });
      setError(null);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : 'countermeasure failed');
    } finally {
      setBusy(false);
    }
  };

  const sendWhatIf = async (body: Record<string, unknown>) => {
    setBusy(true);
    try {
      const result = await postJson<Record<string, unknown>>('/simulation/what-if', body);
      console.info('What-If result', result);
      setError(null);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : 'What-If failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="mx-auto max-w-6xl space-y-6 px-4 py-6">
      <header className="space-y-2">
        <div className="flex items-center gap-2 text-sky-300"><Activity size={20} /><h1 className="text-2xl font-semibold text-ink">Simulation Control</h1></div>
        <p className="text-sm text-muted">
          Controls operate the unified backend service and Advanced Hybrid Simulation Engine. All generated telemetry is
          <span className="mx-1 font-semibold text-amber-300">SYNTHETIC</span>.
        </p>
      </header>

      {error && <div className="rounded-lg bg-warn/15 px-3 py-2 text-sm text-warn">{error}</div>}

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl bg-card p-4 ring-1 ring-white/10">
          <h2 className="text-sm font-semibold text-ink">Mission state</h2>
          <dl className="mt-3 space-y-2 text-sm text-muted">
            <div className="flex justify-between"><dt>Status</dt><dd className="text-ink">{status?.mission_status ?? 'unavailable'}</dd></div>
            <div className="flex justify-between"><dt>Mission day</dt><dd className="text-ink">{status?.mission_day ?? '—'}</dd></div>
            <div className="flex justify-between"><dt>Phase</dt><dd className="text-ink">{status?.mission_phase ?? '—'}</dd></div>
            <div className="flex justify-between"><dt>Speed</dt><dd className="text-ink">{status?.simulation_speed ?? '—'}×</dd></div>
            <div className="flex justify-between"><dt>Astronauts</dt><dd className="text-ink">{astronauts.join(', ') || '—'}</dd></div>
            <div className="flex justify-between"><dt>Active scenarios</dt><dd className="text-ink">{status?.active_scenarios.join(', ') || 'none'}</dd></div>
          </dl>
        </div>

        <div className="rounded-xl bg-card p-4 ring-1 ring-white/10">
          <h2 className="text-sm font-semibold text-ink">Environment</h2>
          <dl className="mt-3 space-y-2 text-sm text-muted">
            <div className="flex justify-between"><dt>Cabin ppCO2</dt><dd className="text-ink">{formatNumber(environment?.cabin_ppco2_mmhg)} mmHg</dd></div>
            <div className="flex justify-between"><dt>Radiation dose rate</dt><dd className="text-ink">{formatNumber(environment?.radiation_dose_rate_msv_h)} mSv/h</dd></div>
            <div className="flex justify-between"><dt>Daily radiation</dt><dd className="text-ink">{formatNumber(environment?.daily_radiation_msv)} mSv</dd></div>
            <div className="flex justify-between"><dt>Cumulative radiation</dt><dd className="text-ink">{formatNumber(environment?.cumulative_radiation_msv)} mSv</dd></div>
          </dl>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-xl bg-card p-4 ring-1 ring-white/10">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-ink"><Play size={16} /> Lifecycle</h2>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <button className="rounded-lg bg-info px-3 py-2 text-sm font-semibold text-canvas hover:bg-sky-300" disabled={busy} onClick={() => sendControl({ action: 'start' })}>Start</button>
            <button className="rounded-lg bg-card px-3 py-2 text-sm text-ink ring-1 ring-white/10 hover:bg-raised" disabled={busy} onClick={() => sendControl({ action: 'pause' })}><Pause size={14} className="mr-1 inline" />Pause</button>
            <button className="rounded-lg bg-card px-3 py-2 text-sm text-ink ring-1 ring-white/10 hover:bg-raised" disabled={busy} onClick={() => sendControl({ action: 'resume' })}>Resume</button>
            <button className="rounded-lg bg-card px-3 py-2 text-sm text-ink ring-1 ring-white/10 hover:bg-raised" disabled={busy} onClick={() => sendControl({ action: 'reset' })}><RotateCcw size={14} className="mr-1 inline" />Reset</button>
          </div>
          <div className="mt-3 flex gap-2">
            {[1, 10, 60, 300].map((speed) => (
              <button key={speed} className="rounded-lg bg-card px-2 py-1 text-xs text-ink ring-1 ring-white/10 hover:bg-raised" disabled={busy} onClick={() => sendControl({ action: 'set_speed', speed })}>{speed}×</button>
            ))}
          </div>
        </div>

        <div className="rounded-xl bg-card p-4 ring-1 ring-white/10">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-ink"><FlaskConical size={16} /> Scenarios</h2>
          <div className="mt-3 space-y-2">
            {SCENARIOS.map((scenario) => (
              <div key={scenario} className="flex items-center gap-2">
                <span className="flex-1 truncate text-xs text-muted">{scenario}</span>
                <button className="rounded-md bg-info/20 px-2 py-1 text-xs font-semibold text-info" disabled={busy} onClick={() => sendScenario(scenario, 'start')}>Start</button>
                <button className="rounded-md bg-card px-2 py-1 text-xs text-muted ring-1 ring-white/10" disabled={busy} onClick={() => sendScenario(scenario, 'terminate')}>Stop</button>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-xl bg-card p-4 ring-1 ring-white/10">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-ink"><ShieldCheck size={16} /> Countermeasures</h2>
          <div className="mt-3 grid gap-2">
            {COUNTERMEASURES.map((type) => (
              <button key={type} className="rounded-lg bg-card px-3 py-2 text-left text-sm text-ink ring-1 ring-white/10 hover:bg-raised" disabled={busy} onClick={() => sendCountermeasure(type)}>{type}</button>
            ))}
          </div>
        </div>
      </div>

      <div className="rounded-xl bg-card p-4 ring-1 ring-white/10">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-ink"><Zap size={16} /> What-If experiments</h2>
        <div className="mt-3 grid gap-2 sm:grid-cols-3">
          <button className="rounded-lg bg-card px-3 py-2 text-sm text-ink ring-1 ring-white/10 hover:bg-raised" disabled={busy} onClick={() => sendWhatIf({ missed_ared_days: 7, duration_seconds: 604800 })}>Missed ARED 7 days</button>
          <button className="rounded-lg bg-card px-3 py-2 text-sm text-ink ring-1 ring-white/10 hover:bg-raised" disabled={busy} onClick={() => sendWhatIf({ sleep_duration_delta_h: -2, duration_seconds: 86400 })}>Sleep −2 h/day</button>
          <button className="rounded-lg bg-card px-3 py-2 text-sm text-ink ring-1 ring-white/10 hover:bg-raised" disabled={busy} onClick={() => sendWhatIf({ ppco2_target_mmhg: 5.0, duration_seconds: 1800 })}>CO2 5 mmHg</button>
        </div>
      </div>
    </section>
  );
}

function formatNumber(value: unknown): string {
  return typeof value === 'number' ? value.toFixed(3) : '—';
}
