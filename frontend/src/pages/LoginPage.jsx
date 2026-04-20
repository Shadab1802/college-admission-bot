// ── LoginPage.jsx ──────────────────────────────────────────
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'react-hot-toast'
import { authAPI } from '../services/api'
import { useAuth } from '../context/AuthContext'
import { GraduationCap, Mail, Lock, Loader2 } from 'lucide-react'

export default function LoginPage() {
  const [form, setForm]       = useState({ email: '', password: '' })
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate  = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      const { data } = await authAPI.login(form)
      login(data)
      toast.success(`Welcome back, ${data.name}!`)
      navigate(data.role === 'director' ? '/director/chat' : '/student/chat')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={styles.page}>
      <div style={styles.card} className="fade-up">
        {/* Logo */}
        <div style={styles.logo}>
          <div style={styles.logoIcon}><GraduationCap size={22} color="#0f0f0f" /></div>
          <span style={styles.logoText}>Aria</span>
        </div>

        <h1 style={styles.heading}>Welcome back</h1>
        <p style={styles.sub}>Sign in to your admissions portal</p>

        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.field}>
            <label className="label">Email</label>
            <div style={styles.inputWrap}>
              <Mail size={15} style={styles.inputIcon} />
              <input
                type="email"
                placeholder="you@example.com"
                value={form.email}
                onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                style={{ paddingLeft: '38px' }}
                required
              />
            </div>
          </div>

          <div style={styles.field}>
            <label className="label">Password</label>
            <div style={styles.inputWrap}>
              <Lock size={15} style={styles.inputIcon} />
              <input
                type="password"
                placeholder="••••••••"
                value={form.password}
                onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                style={{ paddingLeft: '38px' }}
                required
              />
            </div>
          </div>

          <button type="submit" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center', marginTop: '8px' }} disabled={loading}>
            {loading ? <Loader2 size={16} className="pulse" /> : null}
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>

        <p style={styles.footer}>
          New student? <Link to="/register">Create account</Link>
        </p>
      </div>
    </div>
  )
}

const styles = {
  page: {
    minHeight:      '100vh',
    display:        'flex',
    alignItems:     'center',
    justifyContent: 'center',
    background:     'radial-gradient(ellipse at 60% 20%, rgba(212,168,83,0.06) 0%, transparent 60%), var(--bg-base)',
    padding:        '24px',
  },
  card: {
    width:         '100%',
    maxWidth:      '400px',
    background:    'var(--bg-surface)',
    border:        '1px solid var(--border)',
    borderRadius:  'var(--radius-lg)',
    padding:       '40px',
    boxShadow:     'var(--shadow-lg)',
  },
  logo: {
    display:        'flex',
    alignItems:     'center',
    gap:            '10px',
    marginBottom:   '32px',
  },
  logoIcon: {
    width:          '36px',
    height:         '36px',
    borderRadius:   '10px',
    background:     'var(--accent)',
    display:        'flex',
    alignItems:     'center',
    justifyContent: 'center',
  },
  logoText: {
    fontFamily: 'var(--font-display)',
    fontSize:   '22px',
    color:      'var(--text-primary)',
  },
  heading: {
    fontFamily:   'var(--font-display)',
    fontSize:     '26px',
    marginBottom: '6px',
  },
  sub: {
    color:        'var(--text-secondary)',
    fontSize:     '14px',
    marginBottom: '28px',
  },
  form:     { display: 'flex', flexDirection: 'column', gap: '16px' },
  field:    { display: 'flex', flexDirection: 'column' },
  inputWrap:{ position: 'relative' },
  inputIcon:{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none' },
  footer:   { textAlign: 'center', fontSize: '13px', color: 'var(--text-secondary)', marginTop: '24px' },
}
