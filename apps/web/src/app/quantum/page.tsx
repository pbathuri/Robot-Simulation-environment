'use client';

import { useEffect, useState } from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { StatCard, StatRow } from '../components/StatCard';

type Distribution = { id: string; name: string; description: string; color: string };
type HistBin = { bin_start: number; bin_end: number; count: number };
type SampleResult = { distribution: string; stats: { mean: number; std: number; kurtosis: number; min: number; max: number }; histogram: HistBin[] };
type CompareResult = { label: string; color: string; total_reward: number; steps_run: number; rewards: number[]; cumulative_rewards: number[] };
type CircuitGate = { type: string; qubit?: number; control?: number; target?: number; param?: string; label: string };
type CircuitInfo = { num_qubits: number; gates: CircuitGate[]; ascii_diagram: string; advantage: string; output: string; description: string };

export default function QuantumPage() {
  const [distributions, setDistributions] = useState<Distribution[]>([]);
  const [circuit, setCircuit] = useState<CircuitInfo | null>(null);
  const [selectedDist, setSelectedDist] = useState('gaussian');
  const [sampleResult, setSampleResult] = useState<SampleResult | null>(null);
  const [allSamples, setAllSamples] = useState<Record<string, SampleResult>>({});
  const [compareResults, setCompareResults] = useState<CompareResult[]>([]);
  const [compareEnv, setCompareEnv] = useState('cartpole');
  const [sampling, setSampling] = useState(false);
  const [comparing, setComparing] = useState(false);

  useEffect(() => {
    fetch('/api/quantum/distributions').then(r => r.json()).then(d => setDistributions(d.distributions ?? [])).catch(() => {});
    fetch('/api/quantum/circuit').then(r => r.json()).then(setCircuit).catch(() => {});
  }, []);

  const sampleDist = async (dist: string) => {
    setSampling(true); setSelectedDist(dist);
    try {
      const r = await fetch('/api/quantum/sample', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ n: 5000, distribution: dist, noise_scale: 0.05 }) });
      if (r.ok) { const d = await r.json(); setSampleResult(d); setAllSamples(prev => ({ ...prev, [dist]: d })); }
    } catch {} finally { setSampling(false); }
  };

  const sampleAll = async () => {
    setSampling(true);
    for (const d of distributions) {
      try {
        const r = await fetch('/api/quantum/sample', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ n: 5000, distribution: d.id, noise_scale: 0.05 }) });
        if (r.ok) { const data = await r.json(); setAllSamples(prev => ({ ...prev, [d.id]: data })); }
      } catch {}
    }
    setSampling(false);
  };

  const runCompare = async () => {
    setComparing(true); setCompareResults([]);
    try {
      const r = await fetch('/api/quantum/compare', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ env_id: compareEnv, steps: 300, seed: 42, noise_scale: 0.05 }) });
      if (r.ok) { const d = await r.json(); setCompareResults(d.results ?? []); }
    } catch {} finally { setComparing(false); }
  };

  // Build comparison chart data
  const cmpChartData = compareResults.length > 0 ? compareResults[0].cumulative_rewards.map((_, i) => {
    const point: Record<string, number> = { step: i };
    compareResults.forEach(r => { point[r.label] = r.cumulative_rewards[i] ?? 0; });
    return point;
  }).filter((_, i) => i % Math.max(1, Math.floor(compareResults[0].cumulative_rewards.length / 200)) === 0) : [];

  // Distribution comparison bar chart
  const distBarData = Object.entries(allSamples).map(([id, s]) => ({
    name: id, std: parseFloat(s.stats.std.toFixed(4)), kurtosis: parseFloat(s.stats.kurtosis.toFixed(2)),
  }));

  return (
    <div>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.3rem' }}>Quantum Noise Engine</h1>
      <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '1.5rem' }}>
        Visualize the quantum circuit, compare noise distributions, and benchmark quantum vs classical domain randomization.
      </p>

      {/* Circuit Visualization */}
      {circuit && (
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
            <div>
              <div style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '0.3rem' }}>Quantum Circuit ({circuit.num_qubits} qubits)</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{circuit.description}</div>
            </div>
            <span className="badge badge-quantum">Entangled</span>
          </div>
          <pre style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', background: 'var(--bg-primary)', padding: '1rem', borderRadius: 'var(--radius)', border: '1px solid var(--border)', color: 'var(--quantum)', lineHeight: 1.8, overflow: 'auto' }}>
            {circuit.ascii_diagram}
          </pre>
          <div style={{ marginTop: '0.75rem' }}>
            <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.4rem' }}>Gate Sequence</div>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              {circuit.gates.map((g, i) => (
                <div key={i} style={{ padding: '0.3rem 0.6rem', background: 'var(--bg-hover)', borderRadius: 'var(--radius)', fontSize: '0.78rem', border: '1px solid var(--border)' }}>
                  <span style={{ color: 'var(--quantum)', fontWeight: 600 }}>{g.type}</span>
                  {g.qubit !== undefined && <span style={{ color: 'var(--text-muted)' }}> q{g.qubit}</span>}
                  {g.control !== undefined && <span style={{ color: 'var(--text-muted)' }}> q{g.control}→q{g.target}</span>}
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{g.label}</div>
                </div>
              ))}
            </div>
          </div>
          <div style={{ marginTop: '0.75rem', padding: '0.75rem', background: 'var(--quantum-muted)', borderRadius: 'var(--radius)', fontSize: '0.82rem', color: 'var(--quantum)' }}>
            <strong>Quantum Advantage:</strong> {circuit.advantage}
          </div>
        </div>
      )}

      {/* Distribution Sampling */}
      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
        <div className="card">
          <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.75rem' }}>Noise Distributions</div>
          <button onClick={sampleAll} disabled={sampling} style={{ marginBottom: '0.75rem', width: '100%' }} className="btn-primary">
            {sampling ? 'Sampling...' : 'Sample All (5000 pts each)'}
          </button>
          {distributions.map(d => (
            <div key={d.id} onClick={() => sampleDist(d.id)} style={{
              padding: '0.5rem 0.6rem', borderRadius: 'var(--radius)', cursor: 'pointer', marginBottom: '3px',
              background: selectedDist === d.id ? `${d.color}15` : 'transparent', border: `1px solid ${selectedDist === d.id ? d.color : 'transparent'}`,
            }}>
              <div style={{ fontWeight: 600, fontSize: '0.82rem', color: d.color }}>{d.name}</div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{d.description}</div>
            </div>
          ))}
        </div>
        <div className="card">
          <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.5rem' }}>
            {sampleResult ? `${sampleResult.distribution} Distribution` : 'Select a distribution to sample'}
          </div>
          {sampleResult && (
            <>
              <StatRow>
                <StatCard label="Mean" value={sampleResult.stats.mean.toFixed(4)} />
                <StatCard label="Std Dev" value={sampleResult.stats.std.toFixed(4)} />
                <StatCard label="Kurtosis" value={sampleResult.stats.kurtosis.toFixed(2)} accent={Math.abs(sampleResult.stats.kurtosis) > 1 ? 'var(--warning)' : undefined} />
                <StatCard label="Range" value={`[${sampleResult.stats.min.toFixed(3)}, ${sampleResult.stats.max.toFixed(3)}]`} />
              </StatRow>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={sampleResult.histogram}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="bin_start" tick={{ fill: 'var(--text-muted)', fontSize: 9 }} tickFormatter={v => v.toFixed(2)} />
                  <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                  <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 11 }} />
                  <Bar dataKey="count" fill={distributions.find(d => d.id === sampleResult.distribution)?.color || 'var(--accent)'} radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </>
          )}
        </div>
      </div>

      {/* Distribution comparison */}
      {distBarData.length > 1 && (
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.5rem' }}>Distribution Comparison</div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={distBarData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="name" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
              <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 11 }} />
              <Bar dataKey="std" fill="var(--accent)" name="Std Dev" radius={[3, 3, 0, 0]} />
              <Bar dataKey="kurtosis" fill="var(--quantum)" name="Kurtosis" radius={[3, 3, 0, 0]} />
              <Legend />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Quantum vs Classical Comparison */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
          <div style={{ fontSize: '0.95rem', fontWeight: 700 }}>Quantum vs Classical: Environment Benchmark</div>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <select value={compareEnv} onChange={e => setCompareEnv(e.target.value)}>
              <option value="cartpole">Cartpole</option>
              <option value="reach">Reach</option>
              <option value="walker2d">Walker 2D</option>
              <option value="push">Push</option>
            </select>
            <button className="btn-quantum" onClick={runCompare} disabled={comparing}>
              {comparing ? 'Running...' : 'Run Comparison'}
            </button>
          </div>
        </div>
        {compareResults.length > 0 && (
          <>
            <StatRow>
              {compareResults.map(r => (
                <StatCard key={r.label} label={r.label} value={r.total_reward.toFixed(1)} sublabel={`${r.steps_run} steps`} accent={r.color} />
              ))}
            </StatRow>
            <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.5rem' }}>Cumulative Reward Over Time</div>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={cmpChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="step" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 11 }} />
                {compareResults.map(r => (
                  <Line key={r.label} type="monotone" dataKey={r.label} stroke={r.color} strokeWidth={2} dot={false} />
                ))}
                <Legend />
              </LineChart>
            </ResponsiveContainer>
          </>
        )}
      </div>
    </div>
  );
}
