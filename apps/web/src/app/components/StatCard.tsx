'use client';

interface StatCardProps {
  label: string;
  value: string | number;
  sublabel?: string;
  trend?: 'up' | 'down' | 'neutral';
  accent?: string;
}

export function StatCard({ label, value, sublabel, trend, accent }: StatCardProps) {
  const trendColor = trend === 'up' ? 'var(--success)' : trend === 'down' ? 'var(--error)' : 'var(--text-muted)';
  return (
    <div className="card" style={{ minWidth: 140 }}>
      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.35rem' }}>
        {label}
      </div>
      <div style={{ fontSize: '1.5rem', fontWeight: 700, color: accent || 'var(--text-primary)', lineHeight: 1.2 }}>
        {value}
      </div>
      {sublabel && (
        <div style={{ fontSize: '0.75rem', color: trendColor, marginTop: '0.2rem' }}>
          {sublabel}
        </div>
      )}
    </div>
  );
}

export function StatRow({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '1.5rem' }}>
      {children}
    </div>
  );
}
