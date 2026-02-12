'use client';

import { useEffect, useState, useRef } from 'react';
import dynamic from 'next/dynamic';

// Dynamic import to avoid SSR issues with Monaco
const Editor = dynamic(() => import('@monaco-editor/react'), { ssr: false });

type Example = { id: string; name: string; description: string; code: string };
type RunResult = { success: boolean; stdout: string; stderr: string; error: string | null };

const DEFAULT_CODE = `# LABLAB Code Lab
# Write Python code using the simulator API.
# Available imports:
#   apps.sim.envs.registry - run_episode, make_env, list_envs
#   apps.sim.sim.quantum.q_plugin - QPlugin
#   apps.sim.runner.batch_runner - run_batch

from apps.sim.envs.registry import run_episode

ep = run_episode("cartpole", steps=100, seed=42)
print(f"Cartpole: {ep['total_reward']:.1f} reward in {ep['steps_run']} steps")
`;

export default function CodePage() {
  const [examples, setExamples] = useState<Example[]>([]);
  const [code, setCode] = useState(DEFAULT_CODE);
  const [result, setResult] = useState<RunResult | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    fetch('/api/code/examples').then(r => r.json()).then(d => setExamples(d.examples ?? [])).catch(() => {});
  }, []);

  const runCode = async () => {
    setRunning(true); setResult(null);
    try {
      const r = await fetch('/api/code/run', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, timeout: 30 }),
      });
      if (r.ok) setResult(await r.json());
    } catch (e: any) { setResult({ success: false, stdout: '', stderr: '', error: e.message }); }
    finally { setRunning(false); }
  };

  return (
    <div className="full-bleed">
      {/* Toolbar */}
      <div style={{ background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border)', padding: '0.4rem 1rem', display: 'flex', gap: '0.5rem', alignItems: 'center', minHeight: 44 }}>
        <span style={{ fontWeight: 700, fontSize: '0.95rem', marginRight: '0.5rem' }}>Code Lab</span>
        <button className="btn-primary" onClick={runCode} disabled={running}>
          {running ? 'Running...' : '▶ Run'}
        </button>
        <div style={{ width: 1, height: 22, background: 'var(--border)', margin: '0 0.5rem' }} />
        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Examples:</span>
        {examples.map(ex => (
          <button key={ex.id} onClick={() => setCode(ex.code)} style={{ fontSize: '0.78rem' }} title={ex.description}>
            {ex.name}
          </button>
        ))}
      </div>

      {/* Editor + Output */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Editor */}
        <div style={{ flex: 1, overflow: 'hidden' }}>
          <Editor
            height="100%"
            defaultLanguage="python"
            value={code}
            onChange={(val) => setCode(val || '')}
            theme="vs-dark"
            options={{
              fontSize: 14,
              minimap: { enabled: false },
              lineNumbers: 'on',
              renderLineHighlight: 'line',
              scrollBeyondLastLine: false,
              automaticLayout: true,
              padding: { top: 12 },
            }}
          />
        </div>

        {/* Output */}
        <div style={{ width: 420, minWidth: 420, background: 'var(--bg-secondary)', borderLeft: '1px solid var(--border)', display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '0.75rem 1rem', borderBottom: '1px solid var(--border)' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Output</div>
          </div>
          <div style={{ flex: 1, padding: '0.75rem 1rem', overflow: 'auto', fontFamily: 'var(--font-mono)', fontSize: '0.8rem', lineHeight: 1.7 }}>
            {result === null && !running && (
              <div style={{ color: 'var(--text-muted)' }}>Click Run to execute your code.</div>
            )}
            {running && <div style={{ color: 'var(--accent)' }}>Executing...</div>}
            {result && (
              <>
                {result.success && (
                  <div style={{ color: 'var(--success)', marginBottom: '0.5rem' }}>Execution successful</div>
                )}
                {!result.success && (
                  <div style={{ color: 'var(--error)', marginBottom: '0.5rem' }}>Execution failed</div>
                )}
                {result.stdout && (
                  <pre style={{ whiteSpace: 'pre-wrap', color: 'var(--text-primary)', margin: 0 }}>{result.stdout}</pre>
                )}
                {result.stderr && (
                  <pre style={{ whiteSpace: 'pre-wrap', color: 'var(--warning)', margin: '0.5rem 0 0' }}>{result.stderr}</pre>
                )}
                {result.error && (
                  <pre style={{ whiteSpace: 'pre-wrap', color: 'var(--error)', margin: '0.5rem 0 0', fontSize: '0.75rem' }}>{result.error}</pre>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
