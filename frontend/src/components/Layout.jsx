import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { GraduationCap, LogOut } from 'lucide-react'

export default function Layout({ navItems, children }) {
  const { user, logout } = useAuth()
  const location         = useLocation()

  return (
    <div style={styles.shell}>
      {/* Sidebar */}
      <aside style={styles.sidebar}>
        {/* Logo */}
        <div style={styles.logoWrap}>
          <div style={styles.logoIcon}><GraduationCap size={18} color="#0f0f0f" /></div>
          <div>
            <div style={styles.logoName}>Aria</div>
            <div style={styles.logoSub}>IEM Kolkata</div>
          </div>
        </div>

        <div className="divider" />

        {/* User info */}
        <div style={styles.userInfo}>
          <div style={styles.userAvatar}>{user?.name?.[0]?.toUpperCase()}</div>
          <div>
            <div style={styles.userName}>{user?.name}</div>
            <div style={styles.userRole}>{user?.role}</div>
          </div>
        </div>

        <div className="divider" />

        {/* Nav */}
        <nav style={styles.nav}>
          {navItems.map(item => {
            const active = location.pathname === item.path
            return (
              <Link key={item.path} to={item.path}
                style={{ ...styles.navItem, ...(active ? styles.navActive : {}) }}>
                <item.icon size={16} />
                {item.label}
              </Link>
            )
          })}
        </nav>

        {/* Logout */}
        <button onClick={logout} style={styles.logout} className="btn btn-ghost">
          <LogOut size={15} /> Sign out
        </button>
      </aside>

      {/* Main content */}
      <main style={styles.main}>
        {children}
      </main>
    </div>
  )
}

const styles = {
  shell:    { display: 'flex', height: '100vh', overflow: 'hidden' },
  sidebar: {
    width: '220px', flexShrink: 0,
    background: 'var(--bg-surface)', borderRight: '1px solid var(--border)',
    display: 'flex', flexDirection: 'column', padding: '20px 12px',
  },
  logoWrap: { display: 'flex', alignItems: 'center', gap: '10px', padding: '4px 8px', marginBottom: '4px' },
  logoIcon: { width: '32px', height: '32px', borderRadius: '8px', background: 'var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  logoName: { fontFamily: 'var(--font-display)', fontSize: '18px', lineHeight: 1.2 },
  logoSub:  { fontSize: '11px', color: 'var(--text-muted)' },
  userInfo: { display: 'flex', alignItems: 'center', gap: '10px', padding: '4px 8px' },
  userAvatar: {
    width: '32px', height: '32px', borderRadius: '50%',
    background: 'var(--accent-glow)', border: '1px solid var(--accent)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: '14px', fontWeight: '600', color: 'var(--accent)', flexShrink: 0,
  },
  userName: { fontSize: '13px', fontWeight: '500', color: 'var(--text-primary)' },
  userRole: { fontSize: '11px', color: 'var(--text-muted)', textTransform: 'capitalize' },
  nav:      { flex: 1, display: 'flex', flexDirection: 'column', gap: '2px' },
  navItem: {
    display: 'flex', alignItems: 'center', gap: '10px',
    padding: '9px 12px', borderRadius: 'var(--radius-sm)',
    color: 'var(--text-secondary)', fontSize: '13px', fontWeight: '500',
    transition: 'var(--transition)', textDecoration: 'none',
  },
  navActive: { background: 'var(--accent-glow)', color: 'var(--accent)', border: '1px solid rgba(212,168,83,0.2)' },
  logout:   { width: '100%', justifyContent: 'center', fontSize: '13px', marginTop: '4px' },
  main:     { flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' },
}
