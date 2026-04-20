import Layout from '../components/Layout'
import ChatWindow from '../components/ChatWindow'
import { MessageCircle, LayoutDashboard } from 'lucide-react'

const NAV = [
  { path: '/student/chat',      label: 'Chat with Aria',  icon: MessageCircle },
  { path: '/student/dashboard', label: 'My Application',  icon: LayoutDashboard },
]

export default function StudentChat() {
  return (
    <Layout navItems={NAV}>
      <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <div style={styles.header}>
          <div>
            <h2 style={styles.title}>Chat with Aria</h2>
            <p style={styles.sub}>Ask anything about admissions, courses, or your application</p>
          </div>
          <div style={styles.statusDot}>
            <span style={styles.dot} />
            <span style={{ fontSize: '12px', color: 'var(--success)' }}>Online</span>
          </div>
        </div>

        {/* Chat fills rest of height */}
        <div style={{ flex: 1, overflow: 'hidden' }}>
          <ChatWindow />
        </div>
      </div>
    </Layout>
  )
}

const styles = {
  header: {
    padding: '20px 24px', borderBottom: '1px solid var(--border)',
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    background: 'var(--bg-surface)',
  },
  title:  { fontFamily: 'var(--font-display)', fontSize: '20px', marginBottom: '2px' },
  sub:    { fontSize: '13px', color: 'var(--text-secondary)' },
  statusDot: { display: 'flex', alignItems: 'center', gap: '6px' },
  dot: {
    width: '8px', height: '8px', borderRadius: '50%',
    background: 'var(--success)',
    boxShadow: '0 0 6px var(--success)',
  },
}
