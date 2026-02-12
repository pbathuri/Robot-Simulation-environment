'use client';

import { useEffect, useState, useMemo } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { StatCard, StatRow } from '../../components/StatCard';

type TimelineStep = {
  step: number; t: number;
  state: { base_position: number[]; joint_positions: number[]; joint_velocities: number[]; link_positions: number[][]; end_effector: number[] };
  step_time_ms: number;
};

export default function RunDetailPage() {
  const params = useParams();
  const runId = params.runId as string;
  const [metrics, setMetrics] = useState<Record<string, any> | null>(null);
  const [config, setConfig] = useState<Record<string, any> | null>(null);
  const [timeline, setTimeline] = useState<TimelineStep[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch(`/api/v1/runs/${runId}/metrics`).then(r => r.ok ? r.json() : null).catch(() => null),
      fetch(`/api/sim/report/${runId}`).then(r => r.ok ? r.json() : null).catch(() => null),
      fetch(`/api/sim/timeline/${runId}?limit=2000`).then(r => r.ok ? r.json() : null).catch(() => null),
    ]).then(([m, rpt, tl]) => {
      setMetrics(m);
      setConfig(rpt?.config ?? null);
      setTimeline(tl?.timeline ?? rpt?.timeline ?? []);
    }).finally(() => setLoading(false));
  }, [runId]);

  const chartJoints = useMemo(() => {
    const skip = Math.max(1, Math.floor(timeline.length / 300));
    return timeline.filter((_, i) => i % skip === 0).map(s => ({
      step: s.step,
      j0: s.state.joint_positions?.[0] ?? 0,
      j1: s.state.joint_positions?.[1] ?? 0,
      j2: s.state.joint_positions?.[2] ?? 0,
      j3: s.state.joint_positions?.[3] ?? 0,
    }));
  }, [timeline]);

  const chartEE = useMemo(() => {
    const skip = Math.max(1, Math.floor(timeline.length / 300));
    return timeline.filter((_, i) => i % skip === 0).map(s => ({
      step: s.step,
      x: s.state.end_effector?.[0] ?? 0,
      z: s.state.end_effector?.[2] ?? 0,
    }));
  }, [timeline]);

  const chartStepTime = useMemo(() => {
    const skip = Math.max(1, Math.floor(timeline.length / 300));
    return timeline.filter((_, i) => i % skip === 0).map(s => ({
      step: s.step,
      ms: s.step_time_ms ?? 0,
    }));
  }, [timeline]);

  if (loading) return <p style={{ color: 'var(--text-muted)', padding: '2rem' }}>Loading run {runId.slice(0, 12)}...</p>;

  const m = metrics;

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
        <Link href="/runs" style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>← Runs</Link>
        <h1 style={{ fontSize: '1.3rem', fontWeight: 700 }}>Run Detail</h1>
        <span className="mono" style={{ color: 'var(--accent)', fontSize: '0.85rem' }}>{runId.slice(0, 18)}</span>
      </div>

      <StatRow>
        <StatCard label="Steps" value={m?.steps ?? '—'} />
        <StatCard label="Joints" value={m?.num_joints ?? '—'} />
        <StatCard label="Avg Step" value={m?.avg_step_time_ms != null ? `${Number(m.avg_step_time_ms).toFixed(3)} ms` : '—'} />
        <StatCard label="Total" value={m?.total_time_s != null ? `${Number(m.total_time_s).toFixed(3)} s` : '—'} />
        <StatCard label="Joint Travel" value={m?.total_joint_travel_rad != null ? `${m.total_joint_travel_rad} rad` : '—'} />
        <StatCard label="Engine" value={m?.physics_engine ?? '—'} />
        <StatCard label="Q-Plugin" value={m?.q_plugin_used ? 'Yes' : 'No'} accent={m?.q_plugin_used ? 'var(--quantum)' : undefined} />
        <StatCard label="Profile" value={m?.reality_profile ?? 'default'} />
      </StatRow>

      {/* Charts */}
      {chartJoints.length > 1 && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
          <div className="card">
            <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.5rem' }}>Joint Trajectories (rad)</div>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={chartJoints}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="step" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 11 }} />
                <Line type="monotone" dataKey="j0" stroke="#6366f1" strokeWidth={1.5} dot={false} name="J0" />
                <Line type="monotone" dataKey="j1" stroke="#22c55e" strokeWidth={1.5} dot={false} name="J1" />
                <Line type="monotone" dataKey="j2" stroke="#f59e0b" strokeWidth={1.5} dot={false} name="J2" />
                <Line type="monotone" dataKey="j3" stroke="#ef4444" strokeWidth={1.5} dot={false} name="J3" />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="card">
            <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.5rem' }}>End Effector Position</div>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={chartEE}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="step" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 11 }} />
                <Line type="monotone" dataKey="x" stroke="#3b82f6" strokeWidth={1.5} dot={false} name="X (m)" />
                <Line type="monotone" dataKey="z" stroke="#a855f7" strokeWidth={1.5} dot={false} name="Z (m)" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {chartStepTime.length > 1 && (
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.5rem' }}>Step Time (ms)</div>
          <ResponsiveContainer width="100%" height={120}>
            <AreaChart data={chartStepTime}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="step" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
              <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 11 }} />
              <Area type="monotone" dataKey="ms" stroke="var(--accent)" fill="var(--accent-muted)" strokeWidth={1.5} name="Step (ms)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Config */}
      {config && (
        <details>
          <summary style={{ cursor: 'pointer', fontWeight: 600, fontSize: '0.9rem', marginBottom: '0.5rem' }}>Configuration</summary>
          <div className="card">
            <pre className="mono" style={{ whiteSpace: 'pre-wrap', color: 'var(--text-secondary)', fontSize: '0.78rem' }}>
              {JSON.stringify(config, null, 2)}
            </pre>
          </div>
        </details>
      )}
    </div>
  );
}
