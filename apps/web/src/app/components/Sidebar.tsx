'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const NAV_ITEMS = [
  { href: '/', label: 'Dashboard', icon: '◆' },
  { href: '/sim', label: 'Simulator', icon: '▶' },
  { href: '/environments', label: 'Environments', icon: '◫' },
  { href: '/quantum', label: 'Quantum', icon: '⚛' },
  { href: '/compare', label: 'Compare', icon: '⇄' },
  { href: '/runs', label: 'Runs', icon: '≡' },
  { href: '/code', label: 'Code Lab', icon: '⌨' },
  { href: '/design', label: 'Design', icon: '✦' },
  { href: '/benchmarks', label: 'Benchmarks', icon: '◎' },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <nav className="sidebar">
      {/* Logo */}
      <div style={{
        padding: '1.25rem 1.25rem 1rem',
        borderBottom: '1px solid var(--border)',
      }}>
        <Link href="/" style={{ textDecoration: 'none' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <div style={{
              width: 28, height: 28,
              background: 'linear-gradient(135deg, var(--accent), var(--quantum))',
              borderRadius: 6,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '0.8rem', fontWeight: 'bold', color: '#fff',
            }}>
              L
            </div>
            <div>
              <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '0.02em' }}>
                LABLAB
              </div>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: -2 }}>
                Robot Simulator
              </div>
            </div>
          </div>
        </Link>
      </div>

      {/* Nav */}
      <div style={{ flex: 1, padding: '0.75rem 0.75rem', overflow: 'auto' }}>
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href ||
            (item.href !== '/' && pathname.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.6rem',
                padding: '0.55rem 0.75rem',
                borderRadius: 'var(--radius)',
                fontSize: '0.875rem',
                fontWeight: isActive ? 600 : 400,
                color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                background: isActive ? 'var(--accent-muted)' : 'transparent',
                textDecoration: 'none',
                transition: 'all 0.12s',
                marginBottom: '2px',
              }}
            >
              <span style={{
                width: 20, textAlign: 'center',
                color: isActive ? 'var(--accent)' : 'var(--text-muted)',
                fontSize: '0.85rem',
              }}>
                {item.icon}
              </span>
              {item.label}
            </Link>
          );
        })}
      </div>

      {/* Footer */}
      <div style={{
        padding: '0.75rem 1rem',
        borderTop: '1px solid var(--border)',
        fontSize: '0.7rem',
        color: 'var(--text-muted)',
      }}>
        <div>Quantum-Enhanced</div>
        <div style={{ marginTop: 2 }}>Sim-to-Real Platform</div>
      </div>
    </nav>
  );
}
