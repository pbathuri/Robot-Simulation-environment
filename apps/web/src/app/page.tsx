'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { StatCard, StatRow } from './components/StatCard';

type SystemInfo = {
  physics_engine: string;
  qiskit: string | null;
  profiles_count: number;
  runs_count: number;
  python_version: string;
  redis_connected: boolean;
};

type RunMeta = {
  run_id: string;
  status: string;
  metrics?: Record<string, unknown>;
};

type Profile = { id: string; name: string; description?: string };

export default function Dashboard() {
  const [sys, setSys] = useState<SystemInfo | null>(null);
  const [runs, setRuns] = useState<RunMeta[]>([]);
  const [profiles, setProfiles] = useState<Profile[]>([]);

  useEffect(() => {
    fetch('/api/system/info').then(r => r.json()).then(setSys).catch(() => {});
    fetch('/api/runs?limit=8').then(r => r.json()).then(d => setRuns(d.runs ?? [])).catch(() => {});
    fetch('/api/reality-profiles').then(r => r.json()).then(d => setProfiles(d.profiles ?? [])).catch(() => {});
  }, []);

  return (
    <div>
      {/* Hero */}
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: '0.4rem' }}>
          LABLAB Dashboard
        </h1>
        <p style={{ color: 'var(--text-secondary)', maxWidth: 600, fontSize: '0.9rem' }}>
          Quantum-enhanced robotics simulator. Reduce the sim-to-real gap through
          domain randomization, residual learning, and standardized evaluation.
        </p>
      </div>

      {/* Stats */}
      <StatRow>
        <StatCard label="Total Runs" value={sys?.runs_count ?? '—'} />
        <StatCard label="Reality Profiles" value={sys?.profiles_count ?? '—'} accent="var(--accent)" />
        <StatCard label="Physics Engine" value={sys?.physics_engine === 'pybullet' ? 'PyBullet' : 'Stub'} />
        <StatCard
          label="Quantum"
          value={sys?.qiskit ? 'Qiskit' : 'Classical'}
          accent={sys?.qiskit ? 'var(--quantum)' : undefined}
        />
        <StatCard label="Job Queue" value={sys?.redis_connected ? 'Redis' : 'Sync'} sublabel={sys?.redis_connected ? 'Connected' : 'No Redis'} trend={sys?.redis_connected ? 'up' : 'neutral'} />
      </StatRow>

      {/* Quick Actions */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
        <ActionCard href="/sim" icon="▶" title="Run Simulation" description="Launch physics sim with 3D viewport" />
        <ActionCard href="/compare" icon="⇄" title="Multi-Profile Compare" description="Pseudo-reality evaluation across profiles" accent="var(--accent)" />
        <ActionCard href="/design" icon="✦" title="Robot Design" description="Import mesh → segment → URDF export" />
        <ActionCard href="/ai-review" icon="✧" title="AI Planner" description="Text → algorithm generation" accent="var(--quantum)" />
      </div>

      {/* Two-column: Recent Runs + Profiles */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
        {/* Recent Runs */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>Recent Runs</h3>
            <Link href="/runs" style={{ fontSize: '0.8rem' }}>View all →</Link>
          </div>
          {runs.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No runs yet. Start a simulation!</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              {runs.slice(0, 6).map(r => (
                <Link
                  key={r.run_id}
                  href={`/runs/${r.run_id}`}
                  style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '0.5rem 0.75rem', borderRadius: 'var(--radius)',
                    transition: 'background 0.12s', textDecoration: 'none',
                  }}
                  className="card-hover"
                >
                  <span className="mono" style={{ color: 'var(--text-primary)' }}>{r.run_id.slice(0, 12)}</span>
                  <span className={`badge ${r.status === 'completed' ? 'badge-success' : r.status === 'failed' ? 'badge-error' : 'badge-info'}`}>
                    {r.status}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Profiles */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>Reality Profiles</h3>
            <Link href="/compare" style={{ fontSize: '0.8rem' }}>Compare →</Link>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {profiles.map(p => (
              <div key={p.id} style={{
                padding: '0.6rem 0.75rem',
                borderRadius: 'var(--radius)',
                border: '1px solid var(--border)',
                background: 'var(--bg-secondary)',
              }}>
                <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>{p.name}</div>
                {p.description && (
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>
                    {p.description.slice(0, 80)}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function ActionCard({ href, icon, title, description, accent }: {
  href: string; icon: string; title: string; description: string; accent?: string;
}) {
  return (
    <Link href={href} style={{ textDecoration: 'none' }}>
      <div className="card card-hover" style={{ cursor: 'pointer', height: '100%' }}>
        <div style={{
          width: 36, height: 36,
          background: accent ? `${accent}20` : 'var(--bg-hover)',
          borderRadius: 'var(--radius)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '1.1rem', marginBottom: '0.75rem',
          color: accent || 'var(--text-secondary)',
        }}>
          {icon}
        </div>
        <div style={{ fontWeight: 600, fontSize: '0.9rem', marginBottom: '0.25rem', color: 'var(--text-primary)' }}>
          {title}
        </div>
        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{description}</div>
      </div>
    </Link>
  );
}
