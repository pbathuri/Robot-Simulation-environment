'use client';

import { useEffect, useState, useRef, useCallback, Suspense } from 'react';
import { Canvas, useLoader } from '@react-three/fiber';
import { OrbitControls, Grid, GizmoHelper, GizmoViewport, TransformControls, Line } from '@react-three/drei';
import { STLLoader } from 'three-stdlib';
import * as THREE from 'three';

// ── Types ────────────────────────────────────────────────────────────────────

type SceneObject = {
  id: string;
  name: string;
  type: 'link' | 'joint' | 'mesh' | 'frame' | 'target' | 'tool';
  position: [number, number, number];
  rotation: [number, number, number];
  scale: [number, number, number];
  color: string;
  geometry: 'box' | 'cylinder' | 'sphere' | 'file';
  dimensions: [number, number, number];
  meshUrl?: string;
  parentId: string | null;
  jointType?: 'fixed' | 'revolute' | 'prismatic' | 'continuous';
  robodkId?: string;
};

type RoboDKStatus = { connected: boolean; available?: boolean; station_name?: string; robots?: number; robot_names?: string[] };
type RoboDKRobot = { name: string; num_joints: number; joints: number[] };
type RoboDKItem = { name: string; type: string };

// ── Robot presets ────────────────────────────────────────────────────────────

const PRESETS: Record<string, SceneObject[]> = {
  '4dof-arm': [
    { id: 'base', name: 'Base', type: 'link', position: [0, 0.05, 0], rotation: [0, 0, 0], scale: [1, 1, 1], color: '#334155', geometry: 'cylinder', dimensions: [0.06, 0.10, 0], parentId: null },
    { id: 'link1', name: 'Link 1', type: 'link', position: [0, 0.175, 0], rotation: [0, 0, 0], scale: [1, 1, 1], color: '#4c6ef5', geometry: 'box', dimensions: [0.04, 0.15, 0.04], parentId: 'base', jointType: 'revolute' },
    { id: 'link2', name: 'Link 2', type: 'link', position: [0, 0.3, 0], rotation: [0, 0, 0], scale: [1, 1, 1], color: '#6366f1', geometry: 'box', dimensions: [0.035, 0.12, 0.035], parentId: 'link1', jointType: 'revolute' },
    { id: 'link3', name: 'Link 3', type: 'link', position: [0, 0.4, 0], rotation: [0, 0, 0], scale: [1, 1, 1], color: '#818cf8', geometry: 'box', dimensions: [0.03, 0.10, 0.03], parentId: 'link2', jointType: 'revolute' },
    { id: 'ee', name: 'End Effector', type: 'tool', position: [0, 0.47, 0], rotation: [0, 0, 0], scale: [1, 1, 1], color: '#22c55e', geometry: 'sphere', dimensions: [0.02, 0, 0], parentId: 'link3', jointType: 'fixed' },
  ],
  '6dof-arm': [
    { id: 'base', name: 'Base', type: 'link', position: [0, 0.04, 0], rotation: [0, 0, 0], scale: [1, 1, 1], color: '#334155', geometry: 'cylinder', dimensions: [0.07, 0.08, 0], parentId: null },
    { id: 'shoulder', name: 'Shoulder', type: 'link', position: [0, 0.12, 0], rotation: [0, 0, 0], scale: [1, 1, 1], color: '#3b82f6', geometry: 'box', dimensions: [0.05, 0.08, 0.05], parentId: 'base', jointType: 'revolute' },
    { id: 'upper', name: 'Upper Arm', type: 'link', position: [0, 0.24, 0], rotation: [0, 0, 0], scale: [1, 1, 1], color: '#4c6ef5', geometry: 'box', dimensions: [0.04, 0.16, 0.04], parentId: 'shoulder', jointType: 'revolute' },
    { id: 'elbow', name: 'Elbow', type: 'link', position: [0, 0.34, 0], rotation: [0, 0, 0], scale: [1, 1, 1], color: '#6366f1', geometry: 'cylinder', dimensions: [0.025, 0.04, 0], parentId: 'upper', jointType: 'revolute' },
    { id: 'forearm', name: 'Forearm', type: 'link', position: [0, 0.44, 0], rotation: [0, 0, 0], scale: [1, 1, 1], color: '#818cf8', geometry: 'box', dimensions: [0.03, 0.14, 0.03], parentId: 'elbow', jointType: 'revolute' },
    { id: 'wrist', name: 'Wrist', type: 'link', position: [0, 0.52, 0], rotation: [0, 0, 0], scale: [1, 1, 1], color: '#a5b4fc', geometry: 'cylinder', dimensions: [0.02, 0.03, 0], parentId: 'forearm', jointType: 'revolute' },
    { id: 'flange', name: 'Flange', type: 'tool', position: [0, 0.55, 0], rotation: [0, 0, 0], scale: [1, 1, 1], color: '#22c55e', geometry: 'sphere', dimensions: [0.015, 0, 0], parentId: 'wrist', jointType: 'revolute' },
  ],
  'mobile-base': [
    { id: 'chassis', name: 'Chassis', type: 'link', position: [0, 0.05, 0], rotation: [0, 0, 0], scale: [1, 1, 1], color: '#475569', geometry: 'box', dimensions: [0.3, 0.04, 0.2], parentId: null },
    { id: 'wl', name: 'Wheel L', type: 'link', position: [-0.12, 0.02, -0.04], rotation: [0, 0, Math.PI / 2], scale: [1, 1, 1], color: '#1e293b', geometry: 'cylinder', dimensions: [0.03, 0.02, 0], parentId: 'chassis', jointType: 'continuous' },
    { id: 'wr', name: 'Wheel R', type: 'link', position: [0.12, 0.02, -0.04], rotation: [0, 0, Math.PI / 2], scale: [1, 1, 1], color: '#1e293b', geometry: 'cylinder', dimensions: [0.03, 0.02, 0], parentId: 'chassis', jointType: 'continuous' },
    { id: 'lidar', name: 'LiDAR', type: 'link', position: [0, 0.09, -0.05], rotation: [0, 0, 0], scale: [1, 1, 1], color: '#ef4444', geometry: 'cylinder', dimensions: [0.03, 0.04, 0], parentId: 'chassis' },
  ],
};

// ── Main Component ───────────────────────────────────────────────────────────

export default function DesignPage() {
  const [objects, setObjects] = useState<SceneObject[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [transformMode, setTransformMode] = useState<'translate' | 'rotate' | 'scale'>('translate');
  const [exporting, setExporting] = useState(false);
  const [exportResult, setExportResult] = useState<string | null>(null);
  // RoboDK
  const [rdk, setRdk] = useState<RoboDKStatus>({ connected: false, available: false });
  const [rdkRobots, setRdkRobots] = useState<RoboDKRobot[]>([]);
  const [rdkItems, setRdkItems] = useState<RoboDKItem[]>([]);
  const [rdkLoading, setRdkLoading] = useState(false);
  const [rdkMsg, setRdkMsg] = useState<string | null>(null);

  const refreshRDK = useCallback(async () => {
    try {
      const [s, r, it] = await Promise.all([
        fetch('/api/robodk/status').then(x => x.json()),
        fetch('/api/robodk/robots').then(x => x.json()),
        fetch('/api/robodk/items').then(x => x.json()),
      ]);
      setRdk(s); setRdkRobots(r.robots ?? []); setRdkItems(it.items ?? []);
    } catch {}
  }, []);

  useEffect(() => { refreshRDK(); }, [refreshRDK]);

  const rdkConnect = async () => {
    setRdkLoading(true); setRdkMsg(null);
    const r = await fetch('/api/robodk/reconnect', { method: 'POST' }).then(x => x.json()).catch(() => ({ connected: false }));
    setRdk(r); setRdkMsg(r.connected ? 'Connected!' : 'Could not connect. Is RoboDK running?');
    if (r.connected) refreshRDK();
    setRdkLoading(false);
  };

  const rdkLoadRobot = async () => {
    setRdkLoading(true); setRdkMsg(null);
    const r = await fetch('/api/robodk/load-robot', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{"robot_filter":""}' }).then(x => x.json()).catch(() => ({ success: false }));
    setRdkMsg(r.success ? (r.name ? `Loaded ${r.name}` : 'Opened RoboDK. Click the "Online Library" (Globe icon) there.') : 'Failed');
    setTimeout(refreshRDK, 2000);
    setRdkLoading(false);
  };

  const rdkImportItem = async (name: string) => {
    setRdkLoading(true); setRdkMsg(`Importing ${name}...`);
    try {
      const r = await fetch(`/api/robodk/import/${encodeURIComponent(name)}`).then(x => x.json());
      if (r.object) {
        // Fetch geometry
        let meshUrl: string | undefined;
        try {
          const res = await fetch(`/api/robodk/export/${encodeURIComponent(name)}`);
          if (res.ok) {
            const blob = await res.blob();
            if (blob.size > 0) {
              meshUrl = URL.createObjectURL(blob);
            } else {
              console.warn("Exported STL is empty");
            }
          } else {
            console.warn("Failed to export geometry:", res.statusText);
          }
        } catch (e) {
          console.error("Failed to load geometry", e);
        }

        const m = new THREE.Matrix4();
        // Check if pose is flat or nested
        let p: number[] = [];
        if (Array.isArray(r.object.pose) && Array.isArray(r.object.pose[0])) {
             // Nested [[...], ...]
             p = r.object.pose.flat();
        } else {
             // Already flat or something else
             p = r.object.pose;
        }

        m.set(
          p[0], p[1], p[2], p[3],
          p[4], p[5], p[6], p[7],
          p[8], p[9], p[10], p[11],
          p[12], p[13], p[14], p[15]
        );
        
        const pos = new THREE.Vector3();
        const quat = new THREE.Quaternion();
        const scale = new THREE.Vector3();
        m.decompose(pos, quat, scale);
        const rot = new THREE.Euler().setFromQuaternion(quat);

        setObjects(prev => {
          const parentName = r.object.metadata?.robodk_parent;
          let parentId: string | null = null;
          if (parentName) {
             const p = prev.find(o => o.name === parentName);
             if (p) parentId = p.id;
          }

          const newObj: SceneObject = {
            id: r.object.id || `imported_${Date.now()}`,
            name: r.object.name,
            type: 'mesh',
            position: [pos.x, pos.y, pos.z],
            rotation: [rot.x, rot.y, rot.z],
            scale: [0.001, 0.001, 0.001], // Assume mm to m conversion for imported STLs
            color: '#a855f7',
            geometry: meshUrl ? 'file' : 'box',
            meshUrl,
            dimensions: [0.1, 0.1, 0.1],
            parentId: parentId,
            robodkId: r.object.robodk_id
          };
          return [...prev, newObj];
        });
        setRdkMsg(`Imported ${name}`);
      } else {
        setRdkMsg(r.error || 'Import failed');
      }
    } catch (e: any) { setRdkMsg(`Import failed: ${e.message}`); }
    setRdkLoading(false);
  };

  const rdkQuantumDemo = async (name: string) => {
    setRdkLoading(true); setRdkMsg(`Running quantum demo on ${name}...`);
    const r = await fetch('/api/robodk/quantum-demo', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ robot_name: name, steps: 80, noise_scale: 0.05 }) }).then(x => x.json()).catch(() => ({ success: false }));
    setRdkMsg(r.success ? 'Quantum demo complete!' : (r.error || 'Failed'));
    setRdkLoading(false);
  };

  const loadPreset = (key: string) => { setObjects(PRESETS[key] || []); setSelected(null); setExportResult(null); };
  const addPrimitive = (geo: SceneObject['geometry']) => {
    setObjects(prev => [...prev, {
      id: `obj_${Date.now()}`, name: `${geo}_${objects.length}`, type: 'link' as const,
      position: [0, 0.1 + objects.length * 0.1, 0] as [number, number, number], rotation: [0, 0, 0] as [number, number, number], scale: [1, 1, 1] as [number, number, number],
      color: '#64748b', geometry: geo,
      dimensions: (geo === 'box' ? [0.05, 0.05, 0.05] : geo === 'cylinder' ? [0.03, 0.06, 0] : [0.03, 0, 0]) as [number, number, number],
      parentId: null,
    }]);
  };
  const updateObject = (id: string, u: Partial<SceneObject>) => {
    setObjects(prev => prev.map(o => o.id === id ? { ...o, ...u } : o));
    // Optional: if needed, trigger sync to backend immediately or debounced.
    // For now, the user manually moves it. 
    // If they want RoboDK sync, they should use the 'sync-to-robodk' endpoint or we add a button.
  };
  const deleteObject = (id: string) => { setObjects(prev => prev.filter(o => o.id !== id)); if (selected === id) setSelected(null); };

  const syncToRoboDK = async (id: string) => {
    setRdkLoading(true);
    try {
      const res = await fetch(`/api/design/objects/${id}/sync-to-robodk`, { method: 'POST' }).then(r => r.json());
      if (res.success) setRdkMsg('Synced to RoboDK');
      else setRdkMsg('Sync failed');
    } catch (e) { setRdkMsg('Sync failed'); }
    setRdkLoading(false);
  };

  const exportURDF = async () => {
    setExporting(true);
    const parts = objects.map(o => ({ id: o.id, name: o.name, mesh_path: null }));
    const edges = objects.filter(o => o.parentId).map(o => ({ parent_id: o.parentId!, child_id: o.id, joint_type: o.jointType || 'fixed' }));
    const data = await fetch('/api/design/linkage', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ parts, edges, export_urdf: true, output_filename: 'design_export.urdf' }) }).then(r => r.json()).catch(() => ({}));
    setExportResult(data.exported_path || 'Exported');
    setExporting(false);
  };

  const sel = objects.find(o => o.id === selected);

  return (
    <div className="full-bleed">
      {/* ── Toolbar ── */}
      <div style={{ background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border)', padding: '0.4rem 0.75rem', display: 'flex', gap: '0.4rem', alignItems: 'center', flexShrink: 0, minHeight: 42, flexWrap: 'wrap' }}>
        <span style={{ fontWeight: 700, fontSize: '0.9rem', marginRight: '0.3rem' }}>Designer</span>
        {(['translate', 'rotate', 'scale'] as const).map(m => (
          <button key={m} onClick={() => setTransformMode(m)} style={{ background: transformMode === m ? 'var(--accent-muted)' : undefined, color: transformMode === m ? 'var(--accent)' : undefined, fontSize: '0.75rem', padding: '0.3rem 0.6rem' }}>
            {m === 'translate' ? '↔ Move' : m === 'rotate' ? '↻ Rotate' : '⇲ Scale'}
          </button>
        ))}
        <Sep />
        <button onClick={() => loadPreset('4dof-arm')} style={{ fontSize: '0.75rem', padding: '0.3rem 0.5rem' }}>4-DOF</button>
        <button onClick={() => loadPreset('6dof-arm')} style={{ fontSize: '0.75rem', padding: '0.3rem 0.5rem' }}>6-DOF</button>
        <button onClick={() => loadPreset('mobile-base')} style={{ fontSize: '0.75rem', padding: '0.3rem 0.5rem' }}>Mobile</button>
        <Sep />
        <button onClick={() => addPrimitive('box')} style={{ fontSize: '0.75rem', padding: '0.3rem 0.5rem' }}>+ Box</button>
        <button onClick={() => addPrimitive('cylinder')} style={{ fontSize: '0.75rem', padding: '0.3rem 0.5rem' }}>+ Cyl</button>
        <button onClick={() => addPrimitive('sphere')} style={{ fontSize: '0.75rem', padding: '0.3rem 0.5rem' }}>+ Sph</button>
        <div style={{ flex: 1 }} />
        <button className="btn-primary" onClick={exportURDF} disabled={exporting || !objects.length} style={{ fontSize: '0.75rem', padding: '0.3rem 0.7rem' }}>
          {exporting ? '...' : 'Export URDF'}
        </button>
        {exportResult && <span style={{ fontSize: '0.7rem', color: 'var(--success)' }}>Saved</span>}
      </div>

      {/* ── Main 3-column ── */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Left: Scene Tree */}
        <div style={{ width: 200, minWidth: 200, background: 'var(--bg-secondary)', borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '0.5rem 0.75rem', borderBottom: '1px solid var(--border)' }}>
            <Lbl>Scene Tree</Lbl>
          </div>
          <div style={{ flex: 1, overflow: 'auto', padding: '0.4rem' }}>
            {!objects.length && <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', padding: '0.5rem' }}>Load a preset or add shapes.</div>}
            {objects.filter(o => !o.parentId).map(root => (
              <TreeNode key={root.id} obj={root} objects={objects} selected={selected} onSelect={setSelected} depth={0} />
            ))}
          </div>
        </div>

        {/* Center: 3D Viewport */}
        <div style={{ flex: 1, background: '#101018', position: 'relative' }}>
          <Canvas camera={{ position: [0.5, 0.5, 0.7], fov: 45 }} shadows>
            <color attach="background" args={['#101018']} />
            <ambientLight intensity={0.5} />
            <directionalLight position={[4, 8, 4]} intensity={1.5} castShadow />
            <pointLight position={[-3, 4, -3]} intensity={0.4} color="#6366f1" />
            <OrbitControls makeDefault enableDamping dampingFactor={0.08} target={[0, 0.2, 0]} enableZoom={true} zoomSpeed={1.2} minDistance={0.1} maxDistance={10} />
            <Grid args={[8, 8]} cellColor="#1e1e36" sectionColor="#2e2e56" fadeDistance={6} position={[0, 0, 0]} />
            <GizmoHelper alignment="bottom-right" margin={[50, 50]}><GizmoViewport /></GizmoHelper>
            <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow position={[0, -0.001, 0]}>
              <planeGeometry args={[8, 8]} />
              <meshStandardMaterial color="#12121e" />
            </mesh>
            <Suspense fallback={null}>
              {objects.map(obj => (
                <ObjMesh key={obj.id} obj={obj} isSel={selected === obj.id} onSelect={() => setSelected(obj.id)} tMode={transformMode} onTx={(p, r) => updateObject(obj.id, { position: [p.x, p.y, p.z], rotation: [r.x, r.y, r.z] })} />
              ))}
            </Suspense>
            {objects.filter(o => o.parentId).map(c => {
              const p = objects.find(o => o.id === c.parentId);
              return p ? <Line key={`jl_${c.id}`} points={[p.position, c.position]} color={c.jointType === 'revolute' ? '#f59e0b' : c.jointType === 'continuous' ? '#22c55e' : '#6b7280'} lineWidth={2} /> : null;
            })}
          </Canvas>
          <div style={{ position: 'absolute', top: 8, left: 8, background: 'rgba(16,16,24,0.85)', borderRadius: 6, padding: '4px 10px', fontSize: '0.72rem', color: 'var(--text-muted)', backdropFilter: 'blur(8px)', border: '1px solid var(--border)' }}>
            {objects.length} objects | {transformMode}
          </div>
        </div>

        {/* Right: Properties + RoboDK */}
        <div style={{ width: 260, minWidth: 260, background: 'var(--bg-secondary)', borderLeft: '1px solid var(--border)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ flex: 1, overflow: 'auto', padding: '0.75rem' }}>
            <Lbl>Properties</Lbl>
            {sel ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.4rem' }}>
                <div><div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Name</div><input value={sel.name} onChange={e => updateObject(sel.id, { name: e.target.value })} style={{ width: '100%' }} /></div>
                <Row label="Type" value={sel.type} />
                <Lbl>Position</Lbl>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.25rem' }}>
                  {['X', 'Y', 'Z'].map((a, i) => (
                    <div key={a}>
                      <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>{a}</div>
                      <input 
                        type="number" 
                        step={0.01} 
                        value={sel.position && sel.position[i] != null ? sel.position[i].toFixed(3) : '0.000'} 
                        onChange={e => { 
                          const p = sel.position ? [...sel.position] as [number, number, number] : [0,0,0]; 
                          p[i] = +e.target.value; 
                          updateObject(sel.id, { position: p }); 
                        }} 
                        style={{ width: '100%' }} 
                      />
                    </div>
                  ))}
                </div>
                <Lbl>Dimensions</Lbl>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.25rem' }}>
                  {['W', 'H', 'D'].map((a, i) => (
                    <div key={a}>
                      <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>{a}</div>
                      <input 
                        type="number" 
                        step={0.01} 
                        value={sel.dimensions && sel.dimensions[i] != null ? sel.dimensions[i].toFixed(3) : '0.000'} 
                        onChange={e => { 
                          const d = sel.dimensions ? [...sel.dimensions] as [number, number, number] : [0,0,0]; 
                          d[i] = +e.target.value; 
                          updateObject(sel.id, { dimensions: d }); 
                        }} 
                        style={{ width: '100%' }} 
                      />
                    </div>
                  ))}
                </div>
                <Lbl>Color</Lbl>
                <input type="color" value={sel.color} onChange={e => updateObject(sel.id, { color: e.target.value })} style={{ width: '100%', height: 28, padding: 1 }} />
                {sel.parentId !== undefined && (
                  <>
                    <Lbl>Joint Type</Lbl>
                    <select value={sel.jointType || 'fixed'} onChange={e => updateObject(sel.id, { jointType: e.target.value as any })} style={{ width: '100%' }}>
                      <option value="fixed">Fixed</option><option value="revolute">Revolute</option><option value="prismatic">Prismatic</option><option value="continuous">Continuous</option>
                    </select>
                    <Lbl>Parent</Lbl>
                    <select value={sel.parentId || ''} onChange={e => updateObject(sel.id, { parentId: e.target.value || null })} style={{ width: '100%' }}>
                      <option value="">None</option>
                      {objects.filter(o => o.id !== sel.id).map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
                    </select>
                  </>
                )}
                <button onClick={() => deleteObject(sel.id)} style={{ marginTop: '0.3rem', color: 'var(--error)', borderColor: 'var(--error)', fontSize: '0.75rem' }}>Delete</button>
                {sel.robodkId && rdk.connected && (
                  <button onClick={() => syncToRoboDK(sel.id)} disabled={rdkLoading} style={{ marginTop: '0.3rem', fontSize: '0.75rem', background: 'var(--accent-muted)', color: 'var(--accent)', border: '1px solid var(--accent)' }}>Sync to RoboDK</button>
                )}
              </div>
            ) : (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.78rem', marginTop: '0.4rem' }}>Select an object to edit.</div>
            )}

            {/* ── RoboDK Bridge ── */}
            <div style={{ marginTop: '1.25rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border)' }}>
              <Lbl>RoboDK Bridge</Lbl>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', marginTop: '0.3rem', marginBottom: '0.4rem' }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: rdk.connected ? 'var(--success)' : '#ef4444', flexShrink: 0 }} />
                <span style={{ fontSize: '0.75rem', color: rdk.connected ? 'var(--success)' : 'var(--text-muted)' }}>
                  {rdk.connected ? `Connected${rdk.robot_names?.length ? ` (${rdk.robot_names.length} robots)` : ''}` : 'Disconnected'}
                </span>
              </div>

              <button onClick={rdkConnect} disabled={rdkLoading} style={{ width: '100%', fontSize: '0.75rem', marginBottom: '0.3rem' }}>
                {rdkLoading ? '...' : rdk.connected ? 'Refresh Connection' : 'Connect to RoboDK'}
              </button>

              {rdk.connected && (
                <>
                  <button onClick={rdkLoadRobot} disabled={rdkLoading} style={{ width: '100%', fontSize: '0.75rem', marginBottom: '0.5rem' }}>
                    Load Robot from Library
                  </button>

                  {rdkRobots.length > 0 && (
                    <div style={{ marginBottom: '0.5rem' }}>
                      <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.25rem' }}>Robots</div>
                      {rdkRobots.map((r, i) => (
                        <div key={`${r.name}-${i}`} style={{ padding: '0.35rem 0.4rem', background: 'var(--bg-primary)', borderRadius: 'var(--radius)', marginBottom: '0.2rem' }}>
                          <div style={{ fontWeight: 600, fontSize: '0.78rem' }}>{r.name}</div>
                          <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>{r.num_joints} joints</div>
                        </div>
                      ))}
                    </div>
                  )}

                  {rdkItems.length > 0 && (
                    <div>
                      <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.25rem' }}>Station Items</div>
                      {rdkItems.map((item, i) => (
                        <div key={`${item.name}-${i}`} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.72rem', padding: '0.15rem 0', color: 'var(--text-secondary)' }}>
                          <div style={{ display: 'flex', flexDirection: 'column' }}>
                            <span>{item.name}</span>
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.65rem' }}>{item.type}</span>
                          </div>
                          <button onClick={() => rdkImportItem(item.name)} disabled={rdkLoading} style={{ fontSize: '0.65rem', padding: '0.1rem 0.3rem', background: 'transparent', border: '1px solid var(--border)', color: 'var(--accent)' }}>
                            Import
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}

              {rdkMsg && (
                <div style={{ fontSize: '0.7rem', padding: '0.25rem 0.4rem', borderRadius: 'var(--radius)', marginTop: '0.3rem', background: rdkMsg.includes('fail') || rdkMsg.includes('Could not') ? 'rgba(239,68,68,0.1)' : 'rgba(34,197,94,0.1)', color: rdkMsg.includes('fail') || rdkMsg.includes('Could not') ? 'var(--error)' : 'var(--success)' }}>
                  {rdkMsg}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── 3D Object ────────────────────────────────────────────────────────────────

function ObjMesh({ obj, isSel, onSelect, tMode, onTx }: {
  obj: SceneObject; isSel: boolean; onSelect: () => void; tMode: 'translate' | 'rotate' | 'scale';
  onTx: (p: THREE.Vector3, r: THREE.Euler) => void;
}) {
  const ref = useRef<THREE.Mesh>(null);
  
  // If it's a file, delegate to STLObject which handles useLoader
  if (obj.geometry === 'file' && obj.meshUrl) {
     return <STLObject obj={obj} isSel={isSel} onSelect={onSelect} tMode={tMode} onTx={onTx} />;
  }

  // Primitive logic
  const geo = obj.geometry === 'box'
    ? <boxGeometry args={obj.dimensions} />
    : obj.geometry === 'cylinder'
    ? <cylinderGeometry args={[obj.dimensions[0], obj.dimensions[0], obj.dimensions[1], 16]} />
    : <sphereGeometry args={[obj.dimensions[0], 16, 16]} />;

  const primitiveMesh = (
    <mesh ref={ref} position={obj.position} rotation={obj.rotation} scale={obj.scale} onClick={e => { e.stopPropagation(); onSelect(); }} castShadow>
      {geo}
      <meshStandardMaterial color={obj.color} metalness={0.5} roughness={0.35} emissive={isSel ? '#2a2a6a' : '#000'} emissiveIntensity={isSel ? 0.4 : 0} />
    </mesh>
  );

  if (isSel) {
    return (
      <TransformControls
        mode={tMode}
        onMouseUp={() => { if (ref.current) onTx(ref.current.position, ref.current.rotation); }}
      >
        {primitiveMesh}
      </TransformControls>
    );
  }
  return primitiveMesh;
}

function STLObject({ obj, isSel, onSelect, tMode, onTx }: {
  obj: SceneObject; isSel: boolean; onSelect: () => void; tMode: 'translate' | 'rotate' | 'scale';
  onTx: (p: THREE.Vector3, r: THREE.Euler) => void;
}) {
  const geom = useLoader(STLLoader, obj.meshUrl!);
  const ref = useRef<THREE.Mesh>(null);
  
  const mesh = (
    <mesh ref={ref} geometry={geom} position={obj.position} rotation={obj.rotation} scale={obj.scale} onClick={e => { e.stopPropagation(); onSelect(); }} castShadow receiveShadow>
       <meshStandardMaterial color={obj.color} metalness={0.5} roughness={0.35} emissive={isSel ? '#2a2a6a' : '#000'} emissiveIntensity={isSel ? 0.4 : 0} />
    </mesh>
  );

  if (isSel) {
    return (
      <TransformControls mode={tMode} onMouseUp={() => { if (ref.current) onTx(ref.current.position, ref.current.rotation); }}>
        {mesh}
      </TransformControls>
    );
  }
  return mesh;
}


// ── Tree node ────────────────────────────────────────────────────────────────

function TreeNode({ obj, objects, selected, onSelect, depth }: { obj: SceneObject; objects: SceneObject[]; selected: string | null; onSelect: (id: string) => void; depth: number }) {
  const children = objects.filter(o => o.parentId === obj.id);
  const active = selected === obj.id;
  const jColor = obj.jointType === 'revolute' ? '#f59e0b' : obj.jointType === 'continuous' ? '#22c55e' : undefined;
  return (
    <div>
      <div onClick={() => onSelect(obj.id)} style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', padding: '0.25rem 0.35rem', paddingLeft: `${0.35 + depth * 0.6}rem`, borderRadius: 'var(--radius)', cursor: 'pointer', fontSize: '0.75rem', background: active ? 'var(--accent-muted)' : 'transparent', color: active ? 'var(--text-primary)' : 'var(--text-secondary)', marginBottom: 1 }}>
        <span style={{ color: jColor || 'var(--text-muted)', fontSize: '0.65rem' }}>{obj.type === 'tool' ? '◆' : '◻'}</span>
        <span>{obj.name}</span>
        {obj.jointType && obj.jointType !== 'fixed' && <span style={{ fontSize: '0.6rem', color: jColor, marginLeft: 'auto' }}>{obj.jointType[0].toUpperCase()}</span>}
      </div>
      {children.map(c => <TreeNode key={c.id} obj={c} objects={objects} selected={selected} onSelect={onSelect} depth={depth + 1} />)}
    </div>
  );
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function Lbl({ children }: { children: React.ReactNode }) {
  return <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>{children}</div>;
}
function Row({ label, value }: { label: string; value: string }) {
  return <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem' }}><span style={{ color: 'var(--text-muted)' }}>{label}</span><span style={{ fontWeight: 500 }}>{value}</span></div>;
}
function Sep() {
  return <div style={{ width: 1, height: 20, background: 'var(--border)', margin: '0 0.15rem', flexShrink: 0 }} />;
}
