import { useState, useEffect } from 'react'
import { toast } from 'react-hot-toast'
import { adminAPI, emailAPI, chatAPI } from '../services/api'
import Layout from '../components/Layout'
import {
  MessageCircle, LayoutDashboard, Users, CheckCircle,
  XCircle, AlertCircle, Clock, Upload, Send, RefreshCw,
  Plus, Loader2, ChevronDown, ChevronUp, FileText
} from 'lucide-react'

const NAV = [
  { path: '/director/chat',      label: 'Aria Assistant', icon: MessageCircle },
  { path: '/director/dashboard', label: 'Dashboard',      icon: LayoutDashboard },
]

const BUCKET_CONFIG = {
  auto_selected: { label: 'Auto Selected',   color: 'var(--success)', icon: CheckCircle,  badge: 'badge-auto_selected' },
  borderline:    { label: 'Borderline',      color: 'var(--warning)', icon: AlertCircle,  badge: 'badge-borderline' },
  auto_rejected: { label: 'Auto Rejected',   color: 'var(--danger)',  icon: XCircle,      badge: 'badge-auto_rejected' },
  pending:       { label: 'Pending',         color: 'var(--text-muted)', icon: Clock,     badge: 'badge-pending' },
  selected:      { label: 'Finalized ✓',     color: 'var(--success)', icon: CheckCircle,  badge: 'badge-selected' },
  rejected:      { label: 'Rejected ✓',      color: 'var(--danger)',  icon: XCircle,      badge: 'badge-rejected' },
}

function StatCard({ label, value, color }) {
  return (
    <div className="card" style={{ textAlign: 'center', padding: '20px' }}>
      <div style={{ fontSize: '28px', fontFamily: 'var(--font-display)', color: color || 'var(--text-primary)' }}>{value}</div>
      <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>{label}</div>
    </div>
  )
}

function ApplicantRow({ app, onOverride }) {
  const [open,        setOpen]        = useState(false)
  const [note,        setNote]        = useState('')
  const [issuingCard, setIssuingCard] = useState(false)

  const statusCfg = BUCKET_CONFIG[app.status] || BUCKET_CONFIG['pending']
  const StatusIcon = statusCfg.icon

  const handleIssueAdmitCard = async () => {
    setIssuingCard(true)
    try {
      const { data } = await adminAPI.generateAdmitCard(app.application_id)
      toast.success(`Admit card issued for ${app.student_name}! Roll No: ${data.roll_no}`)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to generate admit card')
    } finally {
      setIssuingCard(false)
    }
  }

  return (
    <div style={styles.appRow}>
      <div style={styles.appRowMain} onClick={() => setOpen(o => !o)}>
        {/* Name + email */}
        <div style={{ flex: 1.5 }}>
          <div style={{ fontSize: '14px', fontWeight: '500' }}>{app.student_name}</div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{app.student_email}</div>
        </div>

        {/* Course */}
        <div style={{ fontSize: '12px', color: 'var(--text-muted)', flex: 1 }}>{app.course}</div>

        {/* Marks */}
        <div style={{ fontSize: '12px', minWidth: '80px' }}>
          {app.marks?.percentage != null
            ? <span style={{ color: 'var(--accent)', fontWeight: '600' }}>{app.marks.percentage}%</span>
            : <span style={{ color: 'var(--text-muted)' }}>No marks</span>
          }
        </div>

        {/* Status badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '12px', color: statusCfg.color, fontWeight: '500' }}>
          <StatusIcon size={13} />
          {statusCfg.label}
        </div>

        {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </div>

      {open && (
        <div style={styles.appRowExpanded}>
          {/* Screening notes */}
          {app.screening_notes && (
            <div style={styles.note}>🤖 {app.screening_notes}</div>
          )}

          {/* Document links */}
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', margin: '12px 0 4px' }}>
            {app.marksheet_url
              ? (
                <a
                  href={app.marksheet_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={styles.docLink}
                >
                  <FileText size={13} />
                  View Marksheet PDF
                </a>
              )
              : (
                <span style={{ ...styles.docLink, opacity: 0.45, cursor: 'default', pointerEvents: 'none' }}>
                  <FileText size={13} />
                  No marksheet uploaded
                </span>
              )
            }
          </div>

          {/* Extracted marks detail */}
          {app.marks && (app.marks.percentage != null || app.marks.cgpa != null) && (
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '12px', display: 'flex', gap: '12px' }}>
              {app.marks.percentage != null && <span>📊 Percentage: <strong>{app.marks.percentage}%</strong></span>}
              {app.marks.cgpa      != null && <span>CGPA: <strong>{app.marks.cgpa}</strong></span>}
            </div>
          )}

          {/* Issue Admit Card — only for passed students, on-demand */}
          {['auto_selected', 'selected'].includes(app.status) && (
            <div style={{ marginBottom: '12px' }}>
              <button
                className="btn btn-ghost"
                style={{ fontSize: '12px', color: 'var(--success)', borderColor: 'rgba(76,175,125,0.3)' }}
                onClick={handleIssueAdmitCard}
                disabled={issuingCard}
              >
                {issuingCard
                  ? <><Loader2 size={13} style={{ animation: 'spin 1s linear infinite' }} /> Generating…</>
                  : '🎫 Issue / Re-generate Admit Card'
                }
              </button>
            </div>
          )}

          {/* Override controls */}
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '4px' }}>
            <select style={{ flex: 1, minWidth: '160px' }}
              onChange={e => onOverride(app.application_id, e.target.value, note)}>
              <option value="">Override decision…</option>
              <option value="selected">✓ Select this student</option>
              <option value="rejected">✗ Reject this student</option>
              <option value="borderline">⚠ Mark as borderline</option>
            </select>
            <input placeholder="Optional note…" value={note} onChange={e => setNote(e.target.value)}
              style={{ flex: 2 }} />
          </div>
        </div>
      )}
    </div>
  )
}


export default function DirectorDashboard() {
  const [stats,     setStats]     = useState(null)
  const [applicants,setApplicants]= useState({})
  const [loading,   setLoading]   = useState(true)
  const [activeTab, setActiveTab] = useState('auto_selected')
  const [busy,      setBusy]      = useState('')

  // Course form
  const [showCourse, setShowCourse] = useState(false)
  const [courseForm, setCourseForm] = useState({ name: '', type: 'UG', seats: '', fees: '' })

  const load = async () => {
    try {
      const [s, a] = await Promise.all([adminAPI.getStats(), adminAPI.getApplicants()])
      setStats(s.data)
      setApplicants(a.data)
    } catch { toast.error('Failed to load dashboard') }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const handleOverride = async (appId, newStatus, note) => {
    if (!newStatus) return
    try {
      await adminAPI.override({ application_id: appId, new_status: newStatus, note })
      toast.success('Decision updated')
      load()
    } catch (err) { toast.error(err.response?.data?.detail || 'Override failed') }
  }

  const handleAction = async (action, label) => {
    setBusy(action)
    try {
      if (action === 'screen')   await adminAPI.screenAll()
      if (action === 'finalize') await adminAPI.finalize()
      if (action === 'send')     await emailAPI.sendResults()
      if (action === 'retry')    await emailAPI.retryFailed()
      toast.success(`${label} complete!`)
      load()
    } catch (err) { toast.error(err.response?.data?.detail || `${label} failed`) }
    finally { setBusy('') }
  }

  const handleDocUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setBusy('doc')
    try {
      const { data } = await chatAPI.uploadDoc(file)
      toast.success(`Document uploaded! ${data.chunks_stored} chunks indexed.`)
    } catch { toast.error('Upload failed') }
    finally { setBusy('') }
  }

  const handleTemplateUpload = async (type, e) => {
    const file = e.target.files[0]
    if (!file) return
    try {
      await emailAPI.uploadTemplate(type, file)
      toast.success(`${type} template uploaded!`)
    } catch { toast.error('Template upload failed') }
  }

  const handleCreateCourse = async () => {
    try {
      await adminAPI.createCourse({ ...courseForm, seats: +courseForm.seats, fees: +courseForm.fees })
      toast.success('Course created!')
      setShowCourse(false)
      setCourseForm({ name: '', type: 'UG', seats: '', fees: '' })
      load()
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed') }
  }

  if (loading) return (
    <Layout navItems={NAV}>
      <div style={styles.center}><Loader2 size={24} className="pulse" style={{ color: 'var(--accent)' }} /></div>
    </Layout>
  )

  const totalApps = stats?.total_applications || 0
  const byStatus  = stats?.by_status || {}

  return (
    <Layout navItems={NAV}>
      <div style={styles.page}>
        {/* Header */}
        <div style={styles.header}>
          <div>
            <h2 style={styles.title}>Director Dashboard</h2>
            <p style={styles.sub}>Manage admissions, review applicants, send results</p>
          </div>
          <button className="btn btn-ghost" onClick={load} style={{ fontSize: '13px' }}>
            <RefreshCw size={14} /> Refresh
          </button>
        </div>

        <div style={styles.content}>
          {/* Stats row */}
          <div style={styles.statsGrid}>
            <StatCard label="Total Applied"  value={totalApps} />
            <StatCard label="Auto Selected"  value={byStatus['auto_selected'] || 0} color="var(--success)" />
            <StatCard label="Borderline"     value={byStatus['borderline'] || 0}    color="var(--warning)" />
            <StatCard label="Auto Rejected"  value={byStatus['auto_rejected'] || 0} color="var(--danger)" />
            <StatCard label="Finalized"      value={(byStatus['selected'] || 0) + (byStatus['rejected'] || 0)} color="var(--info)" />
          </div>

          {/* Action buttons */}
          <div className="card">
            <h3 style={styles.sectionTitle}>⚡ Actions</h3>
            <div style={styles.actionRow}>
              {[
                { id: 'screen',   label: 'Run Screening',    icon: RefreshCw, cls: 'btn btn-ghost' },
                { id: 'finalize', label: 'Finalize Decisions',icon: CheckCircle, cls: 'btn btn-ghost' },
                { id: 'send',     label: 'Send Result Emails',icon: Send, cls: 'btn btn-primary' },
                { id: 'retry',    label: 'Retry Failed Emails',icon: RefreshCw, cls: 'btn btn-ghost' },
              ].map(a => (
                <button key={a.id} className={a.cls}
                  onClick={() => handleAction(a.id, a.label)}
                  disabled={!!busy}>
                  {busy === a.id ? <Loader2 size={14} className="pulse" /> : <a.icon size={14} />}
                  {a.label}
                </button>
              ))}
            </div>
          </div>

          {/* Upload section */}
          <div className="card">
            <h3 style={styles.sectionTitle}>📁 Upload Documents & Templates</h3>
            <div style={styles.uploadGrid}>
              <label style={styles.uploadBox}>
                <Upload size={18} color="var(--accent)" />
                <span style={{ fontSize: '13px' }}>College Brochure / Policy PDF</span>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Updates Aria's knowledge</span>
                <input type="file" accept=".pdf,.docx" style={{ display: 'none' }} onChange={handleDocUpload} disabled={busy === 'doc'} />
              </label>
              {['result_selected', 'result_rejected', 'admit_card'].map(t => (
                <label key={t} style={styles.uploadBox}>
                  <FileText size={18} color="var(--accent)" />
                  <span style={{ fontSize: '13px' }}>{t.replace(/_/g, ' ')} template</span>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>.docx with {'{{placeholders}}'}</span>
                  <input type="file" accept=".docx" style={{ display: 'none' }} onChange={e => handleTemplateUpload(t, e)} />
                </label>
              ))}
            </div>
          </div>

          {/* Course management */}
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={styles.sectionTitle}>🎓 Course Management</h3>
              <button className="btn btn-ghost" style={{ fontSize: '13px' }} onClick={() => setShowCourse(o => !o)}>
                <Plus size={14} /> Add Course
              </button>
            </div>
            {showCourse && (
              <div style={styles.courseForm}>
                <input placeholder="Course name" value={courseForm.name}
                  onChange={e => setCourseForm(f => ({ ...f, name: e.target.value }))} />
                <select value={courseForm.type} onChange={e => setCourseForm(f => ({ ...f, type: e.target.value }))}>
                  <option value="UG">UG</option>
                  <option value="PG">PG</option>
                </select>
                <input type="number" placeholder="Seats" value={courseForm.seats}
                  onChange={e => setCourseForm(f => ({ ...f, seats: e.target.value }))} />
                <input type="number" placeholder="Fees (₹)" value={courseForm.fees}
                  onChange={e => setCourseForm(f => ({ ...f, fees: e.target.value }))} />
                <button className="btn btn-primary" onClick={handleCreateCourse}>Create</button>
              </div>
            )}
          </div>

          {/* Applicant buckets */}
          <div className="card">
            <h3 style={styles.sectionTitle}>👥 Applicants</h3>

            {/* Tab bar */}
            <div style={styles.tabs}>
              {Object.entries(BUCKET_CONFIG).map(([key, cfg]) => {
                const count = (applicants[key] || []).length
                const Icon  = cfg.icon
                return (
                  <button key={key}
                    style={{ ...styles.tab, ...(activeTab === key ? { ...styles.tabActive, color: cfg.color, borderColor: cfg.color } : {}) }}
                    onClick={() => setActiveTab(key)}>
                    <Icon size={13} />
                    {cfg.label}
                    <span style={{ ...styles.tabBadge, background: activeTab === key ? cfg.color + '22' : 'var(--bg-elevated)', color: cfg.color }}>{count}</span>
                  </button>
                )
              })}
            </div>

            {/* Applicant list */}
            <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {(applicants[activeTab] || []).length === 0
                ? <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '14px', padding: '32px' }}>No applicants in this bucket</div>
                : (applicants[activeTab] || []).map(app => (
                    <ApplicantRow key={app.application_id} app={app} onOverride={handleOverride} />
                  ))
              }
            </div>
          </div>
        </div>
      </div>
    </Layout>
  )
}

const styles = {
  page:    { height: '100%', overflowY: 'auto', background: 'var(--bg-base)' },
  header:  { padding: '20px 32px', borderBottom: '1px solid var(--border)', background: 'var(--bg-surface)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  title:   { fontFamily: 'var(--font-display)', fontSize: '22px', marginBottom: '4px' },
  sub:     { fontSize: '13px', color: 'var(--text-secondary)' },
  content: { padding: '24px 32px', display: 'flex', flexDirection: 'column', gap: '20px' },
  center:  { height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  statsGrid:   { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))', gap: '12px' },
  sectionTitle:{ fontFamily: 'var(--font-display)', fontSize: '17px', marginBottom: '0' },
  actionRow:   { display: 'flex', gap: '10px', flexWrap: 'wrap', marginTop: '16px' },
  uploadGrid:  { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '12px', marginTop: '16px' },
  uploadBox: {
    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px', padding: '20px 16px',
    border: '1px dashed var(--border)', borderRadius: 'var(--radius-md)', cursor: 'pointer',
    transition: 'var(--transition)', textAlign: 'center',
  },
  courseForm:  { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: '10px', marginBottom: '16px' },
  tabs:        { display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '16px' },
  tab: {
    display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px',
    borderRadius: '99px', fontSize: '12px', fontWeight: '500', cursor: 'pointer',
    background: 'var(--bg-elevated)', border: '1px solid var(--border)',
    color: 'var(--text-secondary)', transition: 'var(--transition)',
  },
  tabActive:   { background: 'var(--accent-glow)' },
  tabBadge:    { padding: '1px 7px', borderRadius: '99px', fontSize: '11px', fontWeight: '600' },
  appRow:      { border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', overflow: 'hidden' },
  appRowMain:  { display: 'flex', alignItems: 'center', gap: '16px', padding: '12px 16px', cursor: 'pointer', transition: 'var(--transition)' },
  appRowExpanded: { padding: '12px 16px', borderTop: '1px solid var(--border)', background: 'var(--bg-elevated)' },
  note: { fontSize: '12px', color: 'var(--text-secondary)', padding: '8px 12px', background: 'var(--bg-surface)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' },
  docLink: {
    display: 'inline-flex', alignItems: 'center', gap: '5px',
    fontSize: '12px', fontWeight: '500', color: 'var(--accent)',
    background: 'var(--accent-glow)', border: '1px solid rgba(138,116,249,0.3)',
    borderRadius: 'var(--radius-sm)', padding: '4px 10px',
    textDecoration: 'none', transition: 'var(--transition)',
  },
}
