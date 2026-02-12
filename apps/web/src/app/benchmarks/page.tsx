'use client';

import { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { StatCard, StatRow } from '../components/StatCard';

type BenchmarkReport = {
  success_rate?: number;
  g_perf_proxy?: number;
  g_dyn_proxy?: number;
  g_perc_proxy?: number;
  integrator?: string;
  total_runs?: number;
  results?: Array<Record<string, unknown>>;
};

export default function BenchmarksPage() {
  const [report, setReport] = useState<BenchmarkReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/benchmarks/latest')
      .then(r => { if (!r.ok) throw new Error('No benchmark report'); return r.json(); })
      .then(setReport)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const chartData = [
    { name: 'G_dyn', value: report?.g_dyn_proxy ?? 0 },
    { name: 'G_perc', value: report?.g_perc_proxy ?? 0 },
    { name: 'G_perf', value: report?.g_perf_proxy ?? 0 },
  ];

  return (
    <div>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.3rem' }}>Benchmarks</h1>
      <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '1.5rem' }}>
        Gap metrics (G_dyn, G_perc, G_perf) and benchmark results. Run <code className="mono">make benchmark</code> to generate.
      </p>

      {loading && <p style={{ color: 'var(--text-muted)' }}>Loading...</p>}
      {error && (
        <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
          <p style={{ color: 'var(--text-muted)', marginBottom: '1rem' }}>No benchmark report found.</p>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Run <code className="mono" style={{ background: 'var(--bg-hover)', padding: '0.2rem 0.5rem', borderRadius: 4 }}>make benchmark</code> from the repo root to generate one.</p>
        </div>
      )}

      {report && (
        <>
          <StatRow>
            <StatCard label="Success Rate" value={report.success_rate != null ? `${(report.success_rate * 100).toFixed(0)}%` : '—'} accent="var(--success)" />
            <StatCard label="G_perf" value={report.g_perf_proxy?.toFixed(4) ?? '—'} />
            <StatCard label="G_dyn" value={report.g_dyn_proxy?.toFixed(4) ?? '—'} accent="var(--info)" />
            <StatCard label="G_perc" value={report.g_perc_proxy?.toFixed(4) ?? '—'} accent="var(--quantum)" />
            <StatCard label="Integrator" value={report.integrator ?? 'euler'} />
            <StatCard label="Total Runs" value={report.total_runs ?? '—'} />
          </StatRow>

          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.75rem' }}>Gap Metrics</div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="name" tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
                <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8 }} />
                <Bar dataKey="value" fill="var(--accent)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {report.results && report.results.length > 0 && (
            <div className="card">
              <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.75rem' }}>Raw Results</div>
              <pre className="mono" style={{ whiteSpace: 'pre-wrap', color: 'var(--text-secondary)', fontSize: '0.8rem', maxHeight: 400, overflow: 'auto' }}>
                {JSON.stringify(report.results, null, 2)}
              </pre>
            </div>
          )}
        </>
      )}
    </div>
  );
}
