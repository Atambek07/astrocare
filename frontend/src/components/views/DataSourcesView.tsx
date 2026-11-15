'use client';

import { useEffect, useMemo, useState } from 'react';
import { Database, ExternalLink, ShieldCheck, AlertTriangle } from 'lucide-react';
import { useHealthStore } from '@/store/useHealthStore';

type ProvenanceClass = 'NASA_REAL' | 'NASA_DERIVED' | 'SYNTHETIC';

interface StudyRow {
  study_id: string;
  title?: string | null;
  mission?: string | null;
  study_category?: string | null;
  verification_status?: string | null;
  relevance_score?: number | null;
  rejection_reason?: string | null;
  source_url?: string | null;
}

interface BundleManifest {
  bundle_id?: string;
  generated_at_utc?: string;
  fallback_status?: string;
  counts?: Record<string, number>;
  artifacts?: { artifact_path: string; artifact_class: string; size_bytes: number }[];
}

interface QualityReport {
  status?: string;
  continuous_telemetry_available?: boolean;
  laboratory_quality?: Record<string, number>;
  warnings?: string[];
}

const CLASS_STYLE: Record<ProvenanceClass, string> = {
  NASA_REAL: 'bg-emerald-500/15 text-emerald-300',
  NASA_DERIVED: 'bg-sky-500/15 text-sky-300',
  SYNTHETIC: 'bg-amber-500/15 text-amber-300',
};

const PIPELINE_STAGES = [
  'NASA Discovery',
  'Metadata Inspection',
  'File Download',
  'Checksum Verification',
  'Parsing',
  'Normalization',
  'Quality Control',
  'Feature Extraction',
  'Evidence Registry',
  'Simulation Calibration',
];

function ProvenanceBadge({ value }: { value: ProvenanceClass }) {
  return (
    <span className={`rounded-full px-2 py-1 text-xs font-semibold ${CLASS_STYLE[value]}`}>
      {value.replace('_', ' ')}
    </span>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl bg-card p-3 ring-1 ring-white/10">
      <div className="text-xs uppercase tracking-wide text-muted">{label}</div>
      <div className="mt-1 text-lg font-semibold text-ink">{value}</div>
    </div>
  );
}

/** NASA data provenance and evidence registry view. */
export function DataSourcesView() {
  const mode = useHealthStore((s) => s.mode);
  const [manifest, setManifest] = useState<BundleManifest | null>(null);
  const [quality, setQuality] = useState<QualityReport | null>(null);
  const [studies, setStudies] = useState<StudyRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function loadJson<T>(path: string): Promise<T | null> {
      try {
        const response = await fetch(path, { cache: 'no-store' });
        if (!response.ok) return null;
        return (await response.json()) as T;
      } catch {
        return null;
      }
    }
    (async () => {
      const [m, q, s] = await Promise.all([
        loadJson<BundleManifest>('/data/manifests/bundle_manifest.json'),
        loadJson<QualityReport>('/data/manifests/data_quality_report.json'),
        loadJson<StudyRow[]>('/data/reference/study_catalog.json'),
      ]);
      if (cancelled) return;
      setManifest(m);
      setQuality(q);
      setStudies(s ?? []);
      if (!m && !q && !s?.length) setError('NASA data manifests are not available in the offline bundle.');
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const accepted = useMemo(() => studies.filter((s) => !s.rejection_reason), [studies]);
  const rejected = useMemo(() => studies.filter((s) => s.rejection_reason), [studies]);
  const verified = useMemo(() => accepted.filter((s) => s.verification_status === 'VERIFIED_METADATA'), [accepted]);

  return (
    <section className="mx-auto max-w-7xl space-y-6 px-4 py-6">
      <header className="space-y-2">
        <div className="flex items-center gap-2 text-sky-300"><Database size={20} /><h1 className="text-2xl font-semibold text-ink">Data Sources &amp; Scientific Evidence</h1></div>
        <p className="max-w-4xl text-sm text-muted">
          This view shows the provenance chain from NASA OSDR to normalized evidence and synthetic simulation outputs.
          NASA data is never presented as continuous astronaut telemetry.
        </p>
      </header>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Studies catalogued" value={studies.length} />
        <StatCard label="Accepted studies" value={accepted.length} />
        <StatCard label="Rejected with reason" value={rejected.length} />
        <StatCard label="Verified by metadata" value={verified.length} />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-xl bg-card p-4 ring-1 ring-white/10">
          <h2 className="text-sm font-semibold text-ink">Pipeline stages</h2>
          <ol className="mt-3 space-y-2 text-sm text-muted">
            {PIPELINE_STAGES.map((stage, index) => (
              <li key={stage} className="flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-info/15 text-xs font-semibold text-info">{index + 1}</span>
                {stage}
              </li>
            ))}
          </ol>
        </div>

        <div className="rounded-xl bg-card p-4 ring-1 ring-white/10">
          <h2 className="text-sm font-semibold text-ink">Processing status</h2>
          <dl className="mt-3 space-y-2 text-sm text-muted">
            <div className="flex justify-between gap-3"><dt>Bundle</dt><dd className="text-ink">{manifest?.bundle_id ?? 'unavailable'}</dd></div>
            <div className="flex justify-between gap-3"><dt>Generated</dt><dd className="text-ink">{manifest?.generated_at_utc ?? 'unknown'}</dd></div>
            <div className="flex justify-between gap-3"><dt>Fallback</dt><dd className="text-ink">{manifest?.fallback_status ?? 'unknown'}</dd></div>
            <div className="flex justify-between gap-3"><dt>Quality</dt><dd className="text-ink">{quality?.status ?? 'unknown'}</dd></div>
            <div className="flex justify-between gap-3"><dt>Continuous NASA telemetry</dt><dd className="text-ink">{quality?.continuous_telemetry_available === false ? 'not available' : 'unknown'}</dd></div>
          </dl>
          {error && (
            <p className="mt-3 flex items-center gap-2 text-xs text-warn"><AlertTriangle size={14} />{error}</p>
          )}
        </div>

        <div className="rounded-xl bg-card p-4 ring-1 ring-white/10">
          <h2 className="text-sm font-semibold text-ink">Provenance classes</h2>
          <div className="mt-3 space-y-2 text-sm text-muted">
            <p className="flex items-center gap-2"><ProvenanceBadge value="NASA_REAL" /> measured NASA/OSDR values</p>
            <p className="flex items-center gap-2"><ProvenanceBadge value="NASA_DERIVED" /> derived from NASA records</p>
            <p className="flex items-center gap-2"><ProvenanceBadge value="SYNTHETIC" /> generated by this engine</p>
            <p className="pt-2 text-xs">Active frontend mode: <span className="font-semibold text-ink">{mode === 'mock' ? 'DEMO MOCK' : 'LIVE BACKEND'}</span></p>
          </div>
        </div>
      </div>

      <div className="rounded-xl bg-card p-4 ring-1 ring-white/10">
        <h2 className="text-sm font-semibold text-ink">NASA OSDR study catalog</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[900px] text-left text-sm">
            <thead className="text-xs uppercase tracking-wide text-muted">
              <tr>
                <th className="px-3 py-2">Study</th>
                <th className="px-3 py-2">Title</th>
                <th className="px-3 py-2">Category</th>
                <th className="px-3 py-2">Verification</th>
                <th className="px-3 py-2">Relevance</th>
                <th className="px-3 py-2">Source</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {studies.slice(0, 40).map((study) => (
                <tr key={study.study_id} className={study.rejection_reason ? 'opacity-60' : ''}>
                  <td className="px-3 py-2 font-semibold text-ink">{study.study_id}</td>
                  <td className="max-w-[420px] px-3 py-2 text-muted">{study.title ?? '—'}</td>
                  <td className="px-3 py-2 text-muted">{study.study_category ?? '—'}</td>
                  <td className="px-3 py-2 text-muted">{study.verification_status ?? '—'}</td>
                  <td className="px-3 py-2 text-muted">{study.relevance_score ?? '—'}</td>
                  <td className="px-3 py-2">
                    {study.source_url && (
                      <a className="inline-flex items-center gap-1 text-sky-300 hover:underline" href={study.source_url} target="_blank" rel="noreferrer">
                        OSDR <ExternalLink size={12} />
                      </a>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="rounded-xl bg-card p-4 ring-1 ring-white/10">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-ink"><ShieldCheck size={16} className="text-emerald-300" /> Transparency notes</h2>
        <ul className="mt-3 space-y-2 text-sm text-muted">
          {quality?.warnings?.map((warning) => (<li key={warning}>• {warning}</li>))}
          <li>• NASA laboratory measurements are not converted into continuous vital-sign telemetry.</li>
          <li>• Rejected studies remain visible with explicit rejection reasons.</li>
          <li>• Simulation telemetry is always labeled <span className="font-semibold text-amber-300">SYNTHETIC</span>.</li>
        </ul>
      </div>
    </section>
  );
}
