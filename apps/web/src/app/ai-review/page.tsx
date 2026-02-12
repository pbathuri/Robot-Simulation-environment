'use client';

import { useState } from 'react';
import Link from 'next/link';

export default function AIReviewPage() {
  const [goal, setGoal] = useState('Move to target position');
  const [plan, setPlan] = useState<Record<string, unknown> | null>(null);
  const [approved, setApproved] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/ai/plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal, task_type: 'custom' }),
      });
      const data = await res.json();
      setPlan(data);
      setApproved(false);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '700px' }}>
      <h1>AI Plan Review</h1>
      <p><Link href="/">← Home</Link></p>
      <p>Generate a plan from a task goal. Review and Approve only; no code execution.</p>

      <div style={{ marginTop: '1rem' }}>
        <label>Goal:</label>
        <input
          type="text"
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          style={{ width: '100%', padding: '0.5rem', marginTop: '0.25rem' }}
        />
        <button onClick={handleGenerate} disabled={loading} style={{ marginTop: '0.5rem', padding: '0.5rem 1rem' }}>
          {loading ? 'Generating...' : 'Generate Plan'}
        </button>
      </div>

      {plan && (
        <div style={{ marginTop: '1.5rem', border: '1px solid #333', padding: '1rem' }}>
          <h2>Generated Plan (review only)</h2>
          <pre style={{ background: '#1a1a1a', padding: '1rem', overflow: 'auto', fontSize: '0.85rem' }}>
            {JSON.stringify(plan, null, 2)}
          </pre>
          <div style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem' }}>
            <button onClick={() => setApproved(true)} style={{ padding: '0.5rem 1rem' }}>Approve</button>
            <button onClick={() => setApproved(false)} style={{ padding: '0.5rem 1rem' }}>Reject</button>
          </div>
          {approved && <p style={{ marginTop: '0.5rem', color: '#6a6' }}>Approved. No execution (safety).</p>}
        </div>
      )}
    </div>
  );
}
