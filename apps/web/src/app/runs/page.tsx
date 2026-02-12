'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

type RunMeta = { run_id: string; status: string; scenario?: string; metrics_summary?: Record<string, unknown> };

export default function RunsPage() {
  const [runs, setRuns] = useState<RunMeta[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/v1/runs?limit=100')
      .then(r => r.json())
      .then(d => setRuns(d.runs ?? []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Simulation Runs</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>{runs.length} runs</p>
        </div>
        <Link href="/sim"><button className="btn-primary">▶ New Run</button></Link>
      </div>

      {loading ? (
        <p style={{ color: 'var(--text-muted)' }}>Loading...</p>
      ) : runs.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
          <p style={{ color: 'var(--text-muted)', marginBottom: '1rem' }}>No runs yet.</p>
          <Link href="/sim"><button className="btn-primary">Start your first simulation</button></Link>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table>
            <thead>
              <tr><th>Run ID</th><th>Status</th><th>Scenario</th><th>Step Time</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {runs.map(r => {
                const ms = r.metrics_summary as Record<string, number> | undefined;
                return (
                  <tr key={r.run_id}>
                    <td><Link href={`/runs/${r.run_id}`} className="mono" style={{ color: 'var(--accent-hover)' }}>{r.run_id.slice(0, 16)}</Link></td>
                    <td><span className={`badge ${r.status === 'completed' ? 'badge-success' : r.status === 'failed' ? 'badge-error' : 'badge-info'}`}>{r.status}</span></td>
                    <td style={{ color: 'var(--text-secondary)' }}>{r.scenario || 'sim'}</td>
                    <td className="mono">{ms?.avg_step_time_ms != null ? `${Number(ms.avg_step_time_ms).toFixed(3)} ms` : '—'}</td>
                    <td>
                      <Link href={`/runs/${r.run_id}`} style={{ fontSize: '0.8rem' }}>View →</Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
