'use client';

import { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import Link from 'next/link';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Grid, GizmoHelper, GizmoViewport } from '@react-three/drei';
import * as THREE from 'three';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

type Profile = { id: string; name: string };
type TimelineStep = {
  step: number; t: number;
  state: { base_position: number[]; joint_positions: number[]; joint_velocities: number[]; link_positions: number[][]; end_effector: number[] };
  observation: { imu_acc: number; camera_val: number };
  step_time_ms: number;
};
type RunResult = { run_id: string; status: string; metrics: Record<string, any> };

export default function SimPage() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [profile, setProfile] = useState('');
  const [steps, setSteps] = useState(200);
  const [useQ, setUseQ] = useState(false);
  const [useRes, setUseRes] = useState(false);

  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<RunResult | null>(null);
  const [timeline, setTimeline] = useState<TimelineStep[]>([]);
  const [playIdx, setPlayIdx] = useState(0);
  const [playing, setPlaying] = useState(false);
  const playRef = useRef(false);
  const [consoleLines, setConsoleLines] = useState<string[]>(['System ready.']);

  useEffect(() => {
    fetch('/api/reality-profiles').then(r => r.json()).then(d => setProfiles(d.profiles ?? [])).catch(() => {});
  }, []);

  const log = useCallback((msg: string) => {
    setConsoleLines(prev => [...prev.slice(-80), `[${new Date().toLocaleTimeString()}] ${msg}`]);
  }, []);

  // Run simulation
  const handleRun = async () => {
    setRunning(true); setTimeline([]); setPlayIdx(0); setPlaying(false); setResult(null);
    log(`Starting: profile=${profile || 'default'} steps=${steps} Q=${useQ} R=${useRes}`);
    try {
      const res = await fetch('/api/sim/run', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: 'sim', urdf_path: 'examples/simple_robot.urdf', steps, dt: 0.01, seed: Math.floor(Math.random() * 10000), use_q_plugin: useQ, use_residual: useRes, reality_profile: profile || undefined }),
      });
      const data = await res.json();
      setResult(data);
      log(`Run ${data.run_id?.slice(0, 10)} completed — ${data.metrics?.avg_step_time_ms?.toFixed(3)} ms/step, ${data.metrics?.num_joints} joints`);

      // Fetch full timeline
      const tlRes = await fetch(`/api/sim/timeline/${data.run_id}?limit=5000`);
      if (tlRes.ok) {
        const tl = await tlRes.json();
        setTimeline(tl.timeline ?? []);
        log(`Loaded ${tl.timeline?.length ?? 0} steps for playback`);
        setPlayIdx(0);
        setPlaying(true);
        playRef.current = true;
      }
    } catch (e: any) { log(`Error: ${e.message}`); }
    finally { setRunning(false); }
  };

  // Playback timer
  useEffect(() => {
    if (!playing || timeline.length === 0) return;
    playRef.current = true;
    const interval = setInterval(() => {
      if (!playRef.current) { clearInterval(interval); return; }
      setPlayIdx(prev => {
        if (prev >= timeline.length - 1) { playRef.current = false; setPlaying(false); return prev; }
        return prev + 1;
      });
    }, 30); // ~33fps playback
    return () => clearInterval(interval);
  }, [playing, timeline.length]);

  const togglePlay = () => { if (playing) { playRef.current = false; setPlaying(false); } else if (timeline.length > 0) { if (playIdx >= timeline.length - 1) setPlayIdx(0); setPlaying(true); } };
  const currentFrame = timeline[playIdx] || null;
  const m = result?.metrics;

  // Chart data (downsample for perf)
  const chartData = useMemo(() => {
    if (timeline.length === 0) return [];
    const skip = Math.max(1, Math.floor(timeline.length / 200));
    return timeline.filter((_, i) => i % skip === 0).map(s => ({
      step: s.step,
      j0: s.state.joint_positions?.[0] ?? 0,
      j1: s.state.joint_positions?.[1] ?? 0,
      j2: s.state.joint_positions?.[2] ?? 0,
      ee_x: s.state.end_effector?.[0] ?? 0,
      ee_z: s.state.end_effector?.[2] ?? 0,
    }));
  }, [timeline]);

  return (
    <div className="full-bleed">
      {/* ── Toolbar ── */}
      <div style={{ background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border)', padding: '0.4rem 1rem', display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap', minHeight: 44 }}>
        <button className="btn-primary" onClick={handleRun} disabled={running} style={{ minWidth: 90 }}>
          {running ? '⏳ Sim...' : '▶ Run'}
        </button>
        <button onClick={togglePlay} disabled={timeline.length === 0} style={{ minWidth: 70 }}>
          {playing ? '⏸ Pause' : '▶ Play'}
        </button>
        <button onClick={() => { setPlayIdx(0); playRef.current = false; setPlaying(false); }} disabled={timeline.length === 0}>
          ⏮ Reset
        </button>

        <div style={{ width: 1, height: 22, background: 'var(--border)', margin: '0 0.25rem' }} />

        <label style={{ display: 'flex', alignItems: 'center', gap: 3, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
          Steps: <input type="number" value={steps} onChange={e => setSteps(+e.target.value)} min={20} max={2000} style={{ width: 65 }} />
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: 3, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
          Profile: <select value={profile} onChange={e => setProfile(e.target.value)} style={{ minWidth: 120 }}>
            <option value="">default</option>
            {profiles.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </label>

        <div style={{ width: 1, height: 22, background: 'var(--border)', margin: '0 0.25rem' }} />

        <label style={{ display: 'flex', alignItems: 'center', gap: 3, fontSize: '0.8rem', cursor: 'pointer' }}>
          <input type="checkbox" checked={useQ} onChange={e => setUseQ(e.target.checked)} />
          <span style={{ color: useQ ? 'var(--quantum)' : 'var(--text-muted)' }}>Quantum</span>
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: 3, fontSize: '0.8rem', cursor: 'pointer' }}>
          <input type="checkbox" checked={useRes} onChange={e => setUseRes(e.target.checked)} />
          <span style={{ color: useRes ? 'var(--success)' : 'var(--text-muted)' }}>Residual</span>
        </label>

        {/* Scrubber */}
        {timeline.length > 0 && (
          <>
            <div style={{ width: 1, height: 22, background: 'var(--border)', margin: '0 0.25rem' }} />
            <input type="range" min={0} max={timeline.length - 1} value={playIdx} onChange={e => { playRef.current = false; setPlaying(false); setPlayIdx(+e.target.value); }} style={{ width: 140, accentColor: 'var(--accent)' }} />
            <span className="mono" style={{ fontSize: '0.75rem', color: 'var(--text-muted)', minWidth: 50 }}>
              {playIdx}/{timeline.length - 1}
            </span>
          </>
        )}
      </div>

      {/* ── Main area ── */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* 3D Viewport */}
        <div style={{ flex: 1, background: '#080810', position: 'relative' }}>
          <Canvas camera={{ position: [0.6, 0.5, 0.6], fov: 50 }} shadows>
            <ambientLight intensity={0.25} />
            <directionalLight position={[3, 6, 3]} intensity={1.2} castShadow shadow-mapSize={[2048, 2048]} />
            <pointLight position={[-2, 3, -2]} intensity={0.3} color="#818cf8" />
            <OrbitControls enableDamping dampingFactor={0.08} target={[0, 0.15, 0]} />
            <Grid args={[10, 10]} cellColor="#14142a" sectionColor="#222248" fadeDistance={12} position={[0, 0, 0]} />
            <GizmoHelper alignment="bottom-right" margin={[60, 60]}><GizmoViewport /></GizmoHelper>
            {/* Ground */}
            <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow position={[0, -0.001, 0]}>
              <planeGeometry args={[10, 10]} />
              <meshStandardMaterial color="#0a0a14" />
            </mesh>
            {/* Robot */}
            <RobotArm frame={currentFrame} useQ={useQ} />
          </Canvas>
          {/* HUD */}
          <div style={{ position: 'absolute', top: 10, left: 10, background: 'rgba(12,12,16,0.88)', borderRadius: 8, padding: '6px 12px', fontSize: '0.75rem', color: 'var(--text-muted)', backdropFilter: 'blur(10px)', border: '1px solid var(--border)', display: 'flex', gap: 8, alignItems: 'center' }}>
            {useQ && <span className="badge badge-quantum">Quantum</span>}
            {useRes && <span className="badge badge-success">Residual</span>}
            <span>{profile || 'default'}</span>
            {currentFrame && <span className="mono">t={currentFrame.t.toFixed(3)}s</span>}
          </div>
          {currentFrame && (
            <div style={{ position: 'absolute', bottom: 10, left: 10, background: 'rgba(12,12,16,0.88)', borderRadius: 8, padding: '6px 12px', fontSize: '0.72rem', color: 'var(--text-muted)', backdropFilter: 'blur(10px)', border: '1px solid var(--border)', fontFamily: 'var(--font-mono)' }}>
              EE: [{currentFrame.state.end_effector.map(v => v.toFixed(3)).join(', ')}]
            </div>
          )}
        </div>

        {/* Right panel: inspector + charts */}
        <div style={{ width: 340, minWidth: 340, background: 'var(--bg-secondary)', borderLeft: '1px solid var(--border)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {/* Inspector */}
          <div style={{ padding: '0.75rem 1rem', borderBottom: '1px solid var(--border)', overflow: 'auto', flex: '0 0 auto', maxHeight: 240 }}>
            <SectionLabel>Run Info</SectionLabel>
            {m ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <Row label="Run ID" value={result!.run_id.slice(0, 14)} accent="var(--accent)" />
                <Row label="Steps" value={String(m.steps)} />
                <Row label="Joints" value={String(m.num_joints)} />
                <Row label="Step time" value={`${Number(m.avg_step_time_ms).toFixed(3)} ms`} />
                <Row label="Joint travel" value={`${m.total_joint_travel_rad} rad`} />
                <Row label="Engine" value={m.physics_engine} />
                <Row label="Profile" value={m.reality_profile || 'default'} />
                <Row label="EE pos" value={m.end_effector_position?.map((v: number) => v.toFixed(3)).join(', ') ?? '—'} />
              </div>
            ) : (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>Run a simulation to see results.</div>
            )}
          </div>

          {/* Charts */}
          <div style={{ flex: 1, overflow: 'auto', padding: '0.75rem 1rem' }}>
            {chartData.length > 1 && (
              <>
                <SectionLabel>Joint Trajectories</SectionLabel>
                <div style={{ height: 150, marginBottom: '1rem' }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                      <XAxis dataKey="step" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                      <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} domain={['auto', 'auto']} />
                      <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 11 }} />
                      <Line type="monotone" dataKey="j0" stroke="#6366f1" strokeWidth={1.5} dot={false} name="Joint 0" />
                      <Line type="monotone" dataKey="j1" stroke="#22c55e" strokeWidth={1.5} dot={false} name="Joint 1" />
                      <Line type="monotone" dataKey="j2" stroke="#f59e0b" strokeWidth={1.5} dot={false} name="Joint 2" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                <SectionLabel>End Effector Path</SectionLabel>
                <div style={{ height: 150 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                      <XAxis dataKey="step" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                      <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} domain={['auto', 'auto']} />
                      <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 11 }} />
                      <Line type="monotone" dataKey="ee_x" stroke="#3b82f6" strokeWidth={1.5} dot={false} name="EE X" />
                      <Line type="monotone" dataKey="ee_z" stroke="#a855f7" strokeWidth={1.5} dot={false} name="EE Z" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* ── Bottom: Console ── */}
      <div style={{ height: 120, background: 'var(--bg-secondary)', borderTop: '1px solid var(--border)', padding: '0.5rem 1rem', overflow: 'auto' }}>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', lineHeight: 1.7 }}>
          {consoleLines.map((line, i) => (
            <div key={i} style={{ color: line.includes('Error') ? 'var(--error)' : line.includes('completed') ? 'var(--success)' : 'var(--text-muted)' }}>{line}</div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── 3D Robot Component ──────────────────────────────────────────────────────

const LINK_LENGTHS = [0.15, 0.12, 0.10, 0.08];
const LINK_COLORS = ['#4c6ef5', '#6366f1', '#818cf8', '#a5b4fc'];

function RobotArm({ frame, useQ }: { frame: TimelineStep | null; useQ: boolean }) {
  const groupRef = useRef<THREE.Group>(null);
  const trailRef = useRef<THREE.Vector3[]>([]);
  const trailLineRef = useRef<THREE.Line | null>(null);

  // Animate smoothly towards target
  const targetPositions = useRef<number[]>([0, 0, 0, 0]);
  const currentPositions = useRef<number[]>([0, 0, 0, 0]);

  useEffect(() => {
    if (frame?.state.joint_positions) {
      targetPositions.current = [...frame.state.joint_positions];
    }
  }, [frame]);

  useFrame(() => {
    // Lerp
    for (let i = 0; i < 4; i++) {
      currentPositions.current[i] += (targetPositions.current[i] - currentPositions.current[i]) * 0.15;
    }

    if (!groupRef.current) return;
    const children = groupRef.current.children;
    let cumAngle = 0;
    let x = 0, z = 0.15;

    for (let j = 0; j < 4; j++) {
      cumAngle += currentPositions.current[j];
      const len = LINK_LENGTHS[j];
      const midX = x + (len / 2) * Math.cos(cumAngle);
      const midZ = z + (len / 2) * Math.sin(cumAngle);
      x += len * Math.cos(cumAngle);
      z += len * Math.sin(cumAngle);

      const link = children[j] as THREE.Mesh;
      if (link) {
        link.position.set(midX, 0, midZ);
        link.rotation.set(0, 0, -cumAngle);
        link.scale.set(len, 0.02, 0.02);
      }
    }

    // End effector sphere
    const ee = children[4] as THREE.Mesh;
    if (ee) {
      ee.position.set(x, 0, Math.max(z, 0));
    }

    // Trail
    if (frame) {
      trailRef.current.push(new THREE.Vector3(x, 0, Math.max(z, 0)));
      if (trailRef.current.length > 300) trailRef.current.shift();
    }
  });

  return (
    <group>
      {/* Base */}
      <mesh position={[0, 0, 0.075]} castShadow>
        <cylinderGeometry args={[0.04, 0.05, 0.15, 16]} />
        <meshStandardMaterial color="#333340" metalness={0.7} roughness={0.3} />
      </mesh>

      {/* Arm links */}
      <group ref={groupRef}>
        {LINK_LENGTHS.map((_, j) => (
          <mesh key={j} castShadow>
            <boxGeometry args={[1, 1, 1]} />
            <meshStandardMaterial
              color={LINK_COLORS[j]}
              metalness={0.5}
              roughness={0.35}
              emissive={useQ ? '#2a1050' : '#000'}
              emissiveIntensity={useQ ? 0.3 : 0}
            />
          </mesh>
        ))}
        {/* End effector */}
        <mesh>
          <sphereGeometry args={[0.015, 16, 16]} />
          <meshStandardMaterial
            color={useQ ? '#a855f7' : '#22c55e'}
            emissive={useQ ? '#a855f7' : '#22c55e'}
            emissiveIntensity={0.8}
          />
        </mesh>
      </group>
    </group>
  );
}

// ── Small components ────────────────────────────────────────────────────────

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.4rem' }}>{children}</div>;
}

function Row({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', padding: '1px 0' }}>
      <span style={{ color: 'var(--text-muted)' }}>{label}</span>
      <span style={{ color: accent || 'var(--text-primary)', fontWeight: 500, fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }}>{value}</span>
    </div>
  );
}
