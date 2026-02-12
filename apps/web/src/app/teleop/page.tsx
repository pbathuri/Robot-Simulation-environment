import Link from 'next/link';

export default function TeleopPage() {
  return (
    <div>
      <h1>Teleop (placeholder)</h1>
      <p><Link href="/">← Home</Link></p>
      <p>Control panel will call API endpoints to start/stop runs and send commands.</p>
    </div>
  );
}
