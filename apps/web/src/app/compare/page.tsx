'use client';

import { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ScatterChart, Scatter, ZAxis } from 'recharts';
import { StatCard, StatRow } from '../components/StatCard';

type Profile = { id: string; name: string; description?: string };

type EpResult = { run_id: string; episode: number; status: string; metrics: Record<string, number>; dr_realization: Record<string, number | boolean> };
type ProfileResult = { profile_id: string; episodes: EpResult[]; summary: { total_episodes: number; completed: number; failed: number; avg_step_time_ms: number; total_time_s: number } };
type CrossProfile = { num_profiles: number; step_time_mean_ms: number; step_time_std_ms: number; step_time_min_ms: number; step_time_max_ms: number };
type BatchReport = { batch_id: string; config: Record<string, unknown>; per_profile: ProfileResult[]; cross_profile: CrossProfile; total_time_s: number };
type PairDrop = { design_profile: string; eval_profile: string; performance_drop: { absolute_drop: number | null; relative_drop: number | null }; gap_width: { l2_distance?: number; cosine_similarity?: number } };
type BatchEval = { pairwise_drops: PairDrop[]; summary: { profiles_evaluated: number; pairwise_comparisons: number; mean_absolute_drop: number; max_absolute_drop: number } };

export default function ComparePage() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [steps, setSteps] = useState(50);
  const [drEp, setDrEp] = useState(3);
  const [running, setRunning] = useState(false);
  const [report, setReport] = useState<BatchReport | null>(null);
  const [evalData, setEvalData] = useState<BatchEval | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/reality-profiles').then(r => r.json()).then(d => {
      const p = d.profiles ?? [];
      setProfiles(p);
      setSelected(p.map((x: Profile) => x.id));
    }).catch(() => {});
  }, []);

  const toggle = (id: string) => setSelected(p => p.includes(id) ? p.filter(x => x !== id) : [...p, id]);

  const run = async () => {
    setRunning(true); setError(null); setReport(null); setEvalData(null);
    try {
      const res = await fetch('/api/sim/batch', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ urdf_path: 'examples/simple_robot.urdf', profiles: selected.length ? selected : undefined, steps, dt: 0.01, seed: 42, dr_episodes_per_profile: drEp }),
      });
      if (!res.ok) throw new Error(await res.text());
      const rpt: BatchReport = await res.json();
      setReport(rpt);
      const ev = await fetch(`/api/sim/batch/${rpt.batch_id}/evaluate`);
      if (ev.ok) setEvalData(await ev.json());
    } catch (e: unknown) { setError(e instanceof Error ? e.message : 'Failed'); }
    finally { setRunning(false); }
  };

  const barData = report?.per_profile.map(pp => ({ name: pp.profile_id, stepTime: parseFloat(pp.summary.avg_step_time_ms.toFixed(4)), episodes: pp.summary.completed })) || [];
  const scatterData = evalData?.pairwise_drops.map(pd => ({ x: pd.gap_width.l2_distance ?? 0, y: Math.abs(pd.performance_drop.absolute_drop ?? 0), label: `${pd.design_profile}→${pd.eval_profile}` })) || [];

  return (
    <div>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.3rem' }}>Multi-Profile Comparison</h1>
      <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '1.5rem' }}>
        Run the same scenario across multiple reality profiles to assess transfer robustness.
      </p>

      {/* Config */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
        <div className="card">
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.75rem' }}>Profiles</div>
          {profiles.map(p => (
            <label key={p.id} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.35rem 0', cursor: 'pointer', fontSize: '0.85rem' }}>
              <input type="checkbox" checked={selected.includes(p.id)} onChange={() => toggle(p.id)} />
              <span style={{ fontWeight: 500 }}>{p.name}</span>
            </label>
          ))}
        </div>
        <div className="card">
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.75rem' }}>Config</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
            <label style={{ fontSize: '0.85rem' }}>Steps: <input type="number" value={steps} onChange={e => setSteps(+e.target.value)} min={10} max={1000} style={{ width: 80, marginLeft: 4 }} /></label>
            <label style={{ fontSize: '0.85rem' }}>DR episodes/profile: <input type="number" value={drEp} onChange={e => setDrEp(+e.target.value)} min={1} max={20} style={{ width: 60, marginLeft: 4 }} /></label>
            <button className="btn-primary" onClick={run} disabled={running || !selected.length} style={{ marginTop: '0.5rem' }}>
              {running ? '⏳ Running batch...' : `▶ Run Batch (${selected.length} profiles)`}
            </button>
          </div>
        </div>
      </div>

      {error && <div style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid var(--error)', padding: '0.75rem', borderRadius: 'var(--radius)', marginBottom: '1rem', color: 'var(--error)' }}>{error}</div>}

      {report && (
        <>
          <StatRow>
            <StatCard label="Batch" value={report.batch_id.slice(0, 14)} />
            <StatCard label="Profiles" value={report.cross_profile.num_profiles} accent="var(--accent)" />
            <StatCard label="Total Time" value={`${report.total_time_s.toFixed(1)}s`} />
            <StatCard label="Mean Step" value={`${report.cross_profile.step_time_mean_ms.toFixed(3)} ms`} />
            <StatCard label="Std Dev" value={`${report.cross_profile.step_time_std_ms.toFixed(3)} ms`} />
          </StatRow>

          {/* Step time chart */}
          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.75rem' }}>Step Time by Profile</div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={barData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="name" tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
                <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 13 }} />
                <Bar dataKey="stepTime" fill="var(--accent)" radius={[4, 4, 0, 0]} name="Avg Step (ms)" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Cross-profile evaluation */}
          {evalData && (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
                {/* Gap width vs drop scatter */}
                <div className="card">
                  <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.75rem' }}>Gap Width vs Performance Drop</div>
                  {scatterData.length > 0 ? (
                    <ResponsiveContainer width="100%" height={200}>
                      <ScatterChart>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                        <XAxis type="number" dataKey="x" name="L2 Gap Width" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                        <YAxis type="number" dataKey="y" name="|Drop|" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                        <ZAxis range={[40, 40]} />
                        <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }} />
                        <Scatter data={scatterData} fill="var(--quantum)" />
                      </ScatterChart>
                    </ResponsiveContainer>
                  ) : <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Not enough data for scatter plot</p>}
                </div>

                {/* Summary stats */}
                <div className="card">
                  <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.75rem' }}>Evaluation Summary</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                    <StatMini label="Profiles evaluated" value={evalData.summary.profiles_evaluated} />
                    <StatMini label="Pairwise comparisons" value={evalData.summary.pairwise_comparisons} />
                    <StatMini label="Mean |drop|" value={evalData.summary.mean_absolute_drop.toFixed(4)} />
                    <StatMini label="Max |drop|" value={evalData.summary.max_absolute_drop.toFixed(4)} />
                  </div>
                </div>
              </div>

              {/* Pairwise table */}
              <div className="card">
                <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.75rem' }}>Pairwise Drops</div>
                <table>
                  <thead>
                    <tr><th>Design</th><th>Eval</th><th>Abs. Drop</th><th>Rel. Drop</th><th>L2 Gap</th><th>Cosine Sim</th></tr>
                  </thead>
                  <tbody>
                    {evalData.pairwise_drops.map((pd, i) => (
                      <tr key={i}>
                        <td className="mono">{pd.design_profile}</td>
                        <td className="mono">{pd.eval_profile}</td>
                        <td>{pd.performance_drop.absolute_drop?.toFixed(4) ?? '—'}</td>
                        <td>{pd.performance_drop.relative_drop != null ? `${(pd.performance_drop.relative_drop * 100).toFixed(1)}%` : '—'}</td>
                        <td>{pd.gap_width.l2_distance?.toFixed(4) ?? '—'}</td>
                        <td>{pd.gap_width.cosine_similarity?.toFixed(4) ?? '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {/* DR Realizations */}
          <details style={{ marginTop: '1.5rem' }}>
            <summary style={{ cursor: 'pointer', fontWeight: 600, fontSize: '0.9rem', marginBottom: '0.75rem' }}>DR Realizations</summary>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '0.75rem' }}>
              {report.per_profile.map(pp => (
                <div key={pp.profile_id} className="card" style={{ padding: '0.75rem' }}>
                  <div style={{ fontWeight: 600, fontSize: '0.85rem', marginBottom: '0.5rem' }}>{pp.profile_id}</div>
                  {pp.episodes.map(ep => (
                    <details key={ep.run_id} style={{ fontSize: '0.8rem', marginBottom: 2 }}>
                      <summary style={{ cursor: 'pointer', color: 'var(--text-secondary)' }}>Ep {ep.episode} — {ep.status}</summary>
                      <pre className="mono" style={{ margin: '0.25rem 0', whiteSpace: 'pre-wrap', color: 'var(--text-muted)' }}>{JSON.stringify(ep.dr_realization, null, 2)}</pre>
                    </details>
                  ))}
                </div>
              ))}
            </div>
          </details>
        </>
      )}
    </div>
  );
}

function StatMini({ label, value }: { label: string; value: string | number }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
      <span style={{ color: 'var(--text-muted)' }}>{label}</span>
      <span style={{ fontWeight: 600 }}>{value}</span>
    </div>
  );
}
