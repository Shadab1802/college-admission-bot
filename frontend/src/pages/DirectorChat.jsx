import Layout from '../components/Layout'
import ChatWindow from '../components/ChatWindow'
import { MessageCircle, LayoutDashboard, Mail } from 'lucide-react'

const NAV = [
  { path: '/director/chat',      label: 'Aria Assistant',  icon: MessageCircle },
  { path: '/director/dashboard', label: 'Dashboard',       icon: LayoutDashboard },
]

export default function DirectorChat() {
  return (
    <Layout navItems={NAV}>
      <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        <div style={styles.header}>
          <div>
            <h2 style={styles.title}>Director Assistant</h2>
            <p style={styles.sub}>Ask Aria for admission insights, stats, or document queries</p>
          </div>
          <div style={styles.tips}>
            <span style={styles.tip}>Try: "How many students applied for BTech?"</span>
            <span style={styles.tip}>Try: "Show PG applicants above 75%"</span>
          </div>
        </div>
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
    background: 'var(--bg-surface)',
    display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px',
  },
  title:  { fontFamily: 'var(--font-display)', fontSize: '20px', marginBottom: '2px' },
  sub:    { fontSize: '13px', color: 'var(--text-secondary)' },
  tips:   { display: 'flex', flexDirection: 'column', gap: '6px', alignItems: 'flex-end' },
  tip: {
    fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)',
    background: 'var(--bg-elevated)', padding: '4px 10px', borderRadius: '99px',
    border: '1px solid var(--border)',
  },
}
