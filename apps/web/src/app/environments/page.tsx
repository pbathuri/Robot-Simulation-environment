'use client';

import { useEffect, useState, useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { StatCard, StatRow } from '../components/StatCard';

type EnvMeta = { id: string; name: string; description: string; category: string };
type TrajectoryStep = { step: number; reward: number; render: Record<string, any>; terminated: boolean; truncated: boolean };
type EpisodeResult = { env_id: string; steps_run: number; total_reward: number; noise_type: string; trajectory: TrajectoryStep[] };
type Env3D = { id: string; filename: string; format: string; num_points?: number; bounds?: { min: number[]; max: number[] } };

const CATEGORY_COLORS: Record<string, string> = { classic: 'var(--info)', manipulation: 'var(--accent)', locomotion: 'var(--success)' };

export default function EnvironmentsPage() {
  const [envs, setEnvs] = useState<EnvMeta[]>([]);
  const [selectedEnv, setSelectedEnv] = useState<string>('cartpole');
  const [result, setResult] = useState<EpisodeResult | null>(null);
  const [running, setRunning] = useState(false);
  const [steps, setSteps] = useState(200);
  const [noiseScale, setNoiseScale] = useState(0.02);
  const [noiseType, setNoiseType] = useState('gaussian');
  const [env3ds, setEnv3ds] = useState<Env3D[]>([]);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    fetch('/api/envs/list').then(r => r.json()).then(d => setEnvs(d.environments ?? [])).catch(() => {});
    fetch('/api/environments/list').then(r => r.json()).then(d => setEnv3ds(d.environments ?? [])).catch(() => {});
  }, []);

  const runEnv = async () => {
    setRunning(true); setResult(null);
    try {
      const r = await fetch(`/api/envs/${selectedEnv}/run`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ steps, seed: Math.floor(Math.random() * 10000), noise_scale: noiseScale, noise_type: noiseType }),
      });
      if (r.ok) setResult(await r.json());
    } catch {} finally { setRunning(false); }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    const fd = new FormData();
    fd.append('file', file);
    try {
      const r = await fetch('/api/environments/upload', { method: 'POST', body: fd });
      if (r.ok) {
        const meta = await r.json();
        setEnv3ds(prev => [...prev, meta]);
      }
    } catch {} finally { setUploading(false); }
  };

  const rewardChart = useMemo(() => {
    if (!result) return [];
    const skip = Math.max(1, Math.floor(result.trajectory.length / 300));
    let cum = 0;
    return result.trajectory.filter((_, i) => i % skip === 0).map(t => {
      cum += t.reward;
      return { step: t.step, reward: t.reward, cumReward: cum };
    });
  }, [result]);

  const selected = envs.find(e => e.id === selectedEnv);

  return (
    <div>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.3rem' }}>Benchmark Environments</h1>
      <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '1.5rem' }}>
        Classical RL environments with quantum noise injection. Run, compare, and evaluate.
      </p>

      {/* Environment cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '0.75rem', marginBottom: '1.5rem' }}>
        {envs.map(env => (
          <div key={env.id} onClick={() => setSelectedEnv(env.id)}
            className="card card-hover" style={{
              cursor: 'pointer',
              borderColor: selectedEnv === env.id ? 'var(--accent)' : 'var(--border)',
              background: selectedEnv === env.id ? 'var(--accent-muted)' : undefined,
            }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
              <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>{env.name}</span>
              <span className="badge" style={{ background: `${CATEGORY_COLORS[env.category] || 'var(--text-muted)'}20`, color: CATEGORY_COLORS[env.category] || 'var(--text-muted)' }}>{env.category}</span>
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{env.description}</div>
          </div>
        ))}
      </div>

      {/* Run controls */}
      <div className="card" style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap', marginBottom: '1.5rem' }}>
        <span style={{ fontWeight: 600 }}>{selected?.name || selectedEnv}</span>
        <label style={{ fontSize: '0.85rem' }}>Steps: <input type="number" value={steps} onChange={e => setSteps(+e.target.value)} min={10} max={2000} style={{ width: 70, marginLeft: 4 }} /></label>
        <label style={{ fontSize: '0.85rem' }}>Noise: <input type="number" value={noiseScale} onChange={e => setNoiseScale(+e.target.value)} min={0} max={1} step={0.01} style={{ width: 60, marginLeft: 4 }} /></label>
        <label style={{ fontSize: '0.85rem' }}>Type:
          <select value={noiseType} onChange={e => setNoiseType(e.target.value)} style={{ marginLeft: 4 }}>
            <option value="gaussian">Gaussian</option>
            <option value="laplace">Laplace</option>
            <option value="cauchy">Cauchy</option>
            <option value="mixture">Mixture</option>
            <option value="quantum">Quantum</option>
          </select>
        </label>
        <button className="btn-primary" onClick={runEnv} disabled={running}>
          {running ? 'Running...' : 'Run Episode'}
        </button>
      </div>

      {/* Results */}
      {result && (
        <>
          <StatRow>
            <StatCard label="Environment" value={result.env_id} />
            <StatCard label="Steps" value={result.steps_run} />
            <StatCard label="Total Reward" value={result.total_reward.toFixed(1)} accent={result.total_reward > 0 ? 'var(--success)' : 'var(--error)'} />
            <StatCard label="Avg Reward" value={(result.total_reward / Math.max(result.steps_run, 1)).toFixed(3)} />
            <StatCard label="Noise" value={`${noiseScale} ${noiseType}`} accent={noiseType === 'quantum' ? 'var(--quantum)' : undefined} />
          </StatRow>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
            <div className="card">
              <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.5rem' }}>Cumulative Reward</div>
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={rewardChart}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="step" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                  <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                  <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 11 }} />
                  <Area type="monotone" dataKey="cumReward" stroke="var(--accent)" fill="var(--accent-muted)" strokeWidth={2} name="Cumulative" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className="card">
              <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.5rem' }}>Per-Step Reward</div>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={rewardChart}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="step" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                  <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                  <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 11 }} />
                  <Line type="monotone" dataKey="reward" stroke="var(--success)" strokeWidth={1.5} dot={false} name="Reward" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}

      {/* 3D Environment Upload */}
      <div className="card" style={{ marginTop: '1.5rem' }}>
        <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.75rem' }}>3D Environment Import</div>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
          Upload LiDAR point clouds (PCD, PLY) or meshes (OBJ, STL) to create realistic simulation environments.
        </p>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <label className="btn-primary" style={{ cursor: 'pointer' }}>
            {uploading ? 'Uploading...' : 'Upload File'}
            <input type="file" accept=".pcd,.ply,.obj,.stl" onChange={handleUpload} style={{ display: 'none' }} />
          </label>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>PCD, PLY, OBJ, STL supported</span>
        </div>
        {env3ds.length > 0 && (
          <div style={{ marginTop: '1rem' }}>
            <div style={{ fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.5rem' }}>Uploaded Environments</div>
            {env3ds.map(e => (
              <div key={e.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.4rem 0', borderBottom: '1px solid var(--border)', fontSize: '0.82rem' }}>
                <span>{e.filename}</span>
                <span style={{ color: 'var(--text-muted)' }}>{e.num_points ? `${e.num_points.toLocaleString()} pts` : e.format}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
