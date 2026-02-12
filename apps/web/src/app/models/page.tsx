'use client';

import Link from 'next/link';

export default function ModelsPage() {
  return (
    <div style={{ padding: '2rem' }}>
      <h1>Model Registry (Placeholder)</h1>
      <p><Link href="/">← Home</Link></p>
      <p>Model registry will support:</p>
      <ul>
        <li>Hugging Face models (VLA, policies, perception, planners)</li>
        <li>Uniform interface: predict_action, plan, perceive</li>
        <li>Local/remote weights, caching, device selection</li>
      </ul>
    </div>
  );
}
