import { useState, useEffect, useRef } from 'react'
import { toast } from 'react-hot-toast'
import { applicationAPI } from '../services/api'
import Layout from '../components/Layout'
import {
  MessageCircle, LayoutDashboard, Upload, CheckCircle, Clock, XCircle,
  AlertCircle, Loader2, FileText, Trash2, RefreshCw, ExternalLink, BookOpen
} from 'lucide-react'

const NAV = [
  { path: '/student/chat',      label: 'Chat with Aria', icon: MessageCircle },
  { path: '/student/dashboard', label: 'My Application', icon: LayoutDashboard },
]

// ── Status card ───────────────────────────────────────────
function StatusCard({ status, hasMarksheet }) {
  // Differentiate "pending" before and after marksheet upload
  const effectiveStatus =
    status === 'pending' && !hasMarksheet ? 'applied_no_sheet' : status

  const config = {
    not_applied:      { icon: Clock,        color: 'var(--text-muted)',  label: 'Not Applied Yet',          bg: 'var(--bg-elevated)' },
    applied_no_sheet: { icon: Clock,        color: 'var(--accent)',      label: 'Applied',          bg: 'rgba(138,116,249,0.08)' },
    pending:          { icon: Clock,        color: 'var(--warning)',     label: 'Under Screening',           bg: 'rgba(232,160,69,0.08)' },
    auto_selected:    { icon: CheckCircle,  color: 'var(--success)',     label: 'Screening Passed ✓',       bg: 'rgba(76,175,125,0.08)' },
    selected:         { icon: CheckCircle,  color: 'var(--success)',     label: 'Selected! 🎉',             bg: 'rgba(76,175,125,0.08)' },
    auto_rejected:    { icon: XCircle,      color: 'var(--danger)',      label: 'Not Eligible',             bg: 'rgba(224,92,92,0.08)' },
    rejected:         { icon: XCircle,      color: 'var(--danger)',      label: 'Not Selected',             bg: 'rgba(224,92,92,0.08)' },
    borderline:       { icon: AlertCircle,  color: 'var(--warning)',     label: 'Under Manual Review',      bg: 'rgba(232,160,69,0.08)' },
  }
  const c    = config[effectiveStatus] || config['pending']
  const Icon = c.icon

  return (
    <div style={{ ...styles.statusCard, background: c.bg, borderColor: c.color + '33' }}>
      <Icon size={28} color={c.color} />
      <div>
        <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '2px' }}>Application Status</div>
        <div style={{ fontSize: '18px', fontWeight: '600', color: c.color }}>{c.label}</div>
      </div>
    </div>
  )
}

// ── Marksheet / Documents panel ──────────────────────────
function DocumentsPanel({ status, onRefresh }) {
  const [docs,      setDocs]      = useState([])
  const [uploading, setUploading] = useState(false)
  const [deleting,  setDeleting]  = useState(false)
  const fileInputRef = useRef(null)

  const loadDocs = async () => {
    try {
      const { data } = await applicationAPI.myDocuments()
      setDocs(data)
    } catch { /* silent */ }
  }

  useEffect(() => { if (status?.status !== 'not_applied') loadDocs() }, [status])

  if (!status || status.status === 'not_applied') return null

  const applicationStatus = status?.status
  const course      = status?.course
  const courseType  = course?.type           // "UG" or "PG"
  const docLabel    = courseType === 'UG' ? '12th Marksheet' : 'B.Tech Marksheet'
  const docTypeKey  = courseType === 'UG' ? 'marksheet_12th' : 'marksheet_btech'

  const uploadedDoc  = docs.find(d => d.type === docTypeKey)
  const admitCardDoc = docs.find(d => d.type === 'admit_card')
  const isFinalized  = ['selected', 'rejected'].includes(applicationStatus)

  const handleUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setUploading(true)
    try {
      const { data } = await applicationAPI.uploadMarksheet(file)
      const pct = data.extracted_marks?.percentage
      toast.success(
        pct
          ? `Marksheet uploaded! Extracted: ${pct}% — Screening: ${data.screening?.status}`
          : 'Marksheet uploaded! Screening triggered.'
      )
      await loadDocs()
      onRefresh()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Upload failed')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleDelete = async () => {
    if (!window.confirm('Delete your marksheet? Your application will return to pending and screening will reset.')) return
    setDeleting(true)
    try {
      await applicationAPI.deleteMarksheet()
      toast.success('Marksheet deleted. Upload a new one to continue.')
      await loadDocs()
      onRefresh()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Delete failed')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="card">
      {/* Section title */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
        <h3 style={styles.sectionTitle}>
          <BookOpen size={17} style={{ marginRight: '8px', verticalAlign: 'middle', color: 'var(--accent)' }} />
          {docLabel}
        </h3>
        {courseType && (
          <span style={styles.courseTypeBadge}>{courseType} Course</span>
        )}
      </div>

      {uploadedDoc ? (
        /* ── Uploaded state ─────────────────────────────── */
        <div>
          <div style={styles.docCard}>
            <FileText size={22} color="var(--accent)" style={{ flexShrink: 0 }} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: '14px', fontWeight: '500', marginBottom: '4px' }}>
                {docLabel}
                <span style={styles.uploadedBadge}>✓ Uploaded</span>
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                Uploaded {new Date(uploadedDoc.uploaded_at).toLocaleDateString('en-IN', {
                  day: 'numeric', month: 'short', year: 'numeric',
                  hour: '2-digit', minute: '2-digit'
                })}
              </div>

              {/* Extracted marks summary */}
              {uploadedDoc.extracted_marks && (
                <div style={styles.marksRow}>
                  {uploadedDoc.extracted_marks.percentage != null && (
                    <span style={styles.marksBadge}>
                      📊 {uploadedDoc.extracted_marks.percentage}%
                    </span>
                  )}
                  {uploadedDoc.extracted_marks.cgpa != null && (
                    <span style={styles.marksBadge}>
                      CGPA {uploadedDoc.extracted_marks.cgpa}
                    </span>
                  )}
                  {!uploadedDoc.extracted_marks.percentage && !uploadedDoc.extracted_marks.cgpa && (
                    <span style={{ ...styles.marksBadge, color: 'var(--warning)', background: 'rgba(232,160,69,0.12)' }}>
                      ⚠ Marks not auto-extracted
                    </span>
                  )}
                </div>
              )}
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', gap: '8px', flexShrink: 0 }}>
              <a
                href={uploadedDoc.file_url}
                target="_blank"
                rel="noopener noreferrer"
                style={styles.iconBtn}
                title="View PDF"
              >
                <ExternalLink size={15} />
              </a>

              {!isFinalized && (
                <>
                  <label style={styles.iconBtn} title="Re-upload marksheet">
                    {uploading
                      ? <Loader2 size={15} style={{ animation: 'spin 1s linear infinite' }} />
                      : <RefreshCw size={15} />
                    }
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".pdf"
                      style={{ display: 'none' }}
                      onChange={handleUpload}
                      disabled={uploading || deleting}
                    />
                  </label>

                  <button
                    style={{ ...styles.iconBtn, color: 'var(--danger)', borderColor: 'rgba(224,92,92,0.3)' }}
                    onClick={handleDelete}
                    disabled={deleting || uploading}
                    title="Delete marksheet"
                  >
                    {deleting
                      ? <Loader2 size={15} style={{ animation: 'spin 1s linear infinite' }} />
                      : <Trash2 size={15} />
                    }
                  </button>
                </>
              )}
            </div>
          </div>

          {isFinalized && (
            <div style={styles.finalizedNote}>
              🔒 Decision has been finalized — marksheet cannot be modified.
            </div>
          )}
        </div>
      ) : (
        /* ── Not yet uploaded ───────────────────────────── */
        <div>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
            Upload your <strong>{docLabel}</strong> (PDF) to trigger automatic eligibility screening.
            The director will review the result.
          </p>
          <label style={{
            ...styles.uploadZone,
            ...(uploading ? { opacity: 0.7, pointerEvents: 'none' } : {})
          }}>
            <Upload size={22} color="var(--accent)" />
            <span style={{ fontSize: '14px', fontWeight: '500', color: 'var(--text-primary)' }}>
              {uploading ? 'Uploading & screening…' : `Upload ${docLabel}`}
            </span>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>PDF only · Max 10 MB</span>
            {uploading && <Loader2 size={18} style={{ animation: 'spin 1s linear infinite', color: 'var(--accent)' }} />}
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              style={{ display: 'none' }}
              onChange={handleUpload}
              disabled={uploading}
            />
          </label>
        </div>
      )}

      {/* ── Admit Card (only for screened-in students) ──── */}
      {['auto_selected', 'selected'].includes(applicationStatus) && (
        <div style={{ marginTop: '20px', borderTop: '1px solid var(--border)', paddingTop: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <BookOpen size={16} color="var(--success)" />
            <span style={{ fontFamily: 'var(--font-display)', fontSize: '15px' }}>Admit Card</span>
            <span style={{ fontSize: '11px', color: 'var(--success)', background: 'rgba(76,175,125,0.12)', border: '1px solid rgba(76,175,125,0.25)', borderRadius: '99px', padding: '2px 8px', fontWeight: '600' }}>Screening Passed</span>
          </div>

          {admitCardDoc ? (
            <div style={styles.docCard}>
              <FileText size={20} color="var(--success)" style={{ flexShrink: 0 }} />
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: '14px', fontWeight: '500', marginBottom: '4px' }}>
                  Admit Card
                  <span style={{ ...styles.uploadedBadge, color: 'var(--success)', background: 'rgba(76,175,125,0.12)', border: '1px solid rgba(76,175,125,0.25)' }}>✓ Issued</span>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Issued {new Date(admitCardDoc.uploaded_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                </div>
              </div>
              <a href={admitCardDoc.file_url} target="_blank" rel="noopener noreferrer" style={styles.iconBtn} title="Download Admit Card">
                <ExternalLink size={15} />
              </a>
            </div>
          ) : (
            <div style={{ fontSize: '13px', color: 'var(--text-muted)', padding: '14px 16px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px dashed var(--border)' }}>
              🕐 Your admit card will be issued by the director shortly. Check back here soon.
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Main dashboard ────────────────────────────────────────
export default function StudentDashboard() {
  const [courses,  setCourses]  = useState([])
  const [status,   setStatus]   = useState(null)
  const [loading,  setLoading]  = useState(true)
  const [applying, setApplying] = useState(false)
  const [selected, setSelected] = useState(null)

  const load = async () => {
    try {
      const [c, s] = await Promise.all([
        applicationAPI.getCourses(),
        applicationAPI.myStatus()
      ])
      setCourses(c.data)
      setStatus(s.data)
    } catch { toast.error('Failed to load data') }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const handleApply = async () => {
    if (!selected) return toast.error('Please select a course first')
    setApplying(true)
    try {
      const { data } = await applicationAPI.apply(selected)
      toast.success(data.message)
      load()
    } catch (err) { toast.error(err.response?.data?.detail || 'Application failed') }
    finally { setApplying(false) }
  }

  const hasApplied = status && status.status !== 'not_applied'

  if (loading) return (
    <Layout navItems={NAV}>
      <div style={styles.center}><Loader2 size={24} style={{ animation: 'spin 1s linear infinite', color: 'var(--accent)' }} /></div>
    </Layout>
  )

  return (
    <Layout navItems={NAV}>
      <div style={styles.page}>
        <div style={styles.header}>
          <h2 style={styles.title}>My Application</h2>
          <p style={styles.sub}>Track your admission status and manage your documents</p>
        </div>

        <div style={styles.content}>
          {/* Status card */}
          <StatusCard status={status?.status || 'not_applied'} hasMarksheet={status?.has_marksheet} />

          {/* Exam details if selected */}
          {status?.exam_details && (
            <div className="card" style={{ borderColor: 'rgba(76,175,125,0.3)' }}>
              <h3 style={styles.sectionTitle}>📋 Exam Details</h3>
              <div style={styles.detailGrid}>
                <div><span className="label">Exam Date</span>{status.exam_details.exam_date || 'TBA'}</div>
                <div><span className="label">Venue</span>{status.exam_details.venue || 'TBA'}</div>
              </div>
            </div>
          )}

          {/* Applied course info */}
          {hasApplied && (
            <div className="card">
              <h3 style={styles.sectionTitle}>Your Application</h3>
              <div style={styles.detailGrid}>
                <div><span className="label">Course</span>{status.course?.name}</div>
                <div><span className="label">Type</span>{status.course?.type}</div>
                <div><span className="label">Applied On</span>{new Date(status.applied_on).toLocaleDateString('en-IN')}</div>
              </div>
              {status.screening_notes && (
                <div style={styles.note}>
                  <AlertCircle size={13} />
                  {status.screening_notes}
                </div>
              )}
            </div>
          )}

          {/* Documents / Marksheet panel */}
          {hasApplied && (
            <DocumentsPanel status={status} onRefresh={load} />
          )}

          {/* Course selection — only before applying */}
          {!hasApplied && (
            <div className="card">
              <h3 style={styles.sectionTitle}>Choose a Course</h3>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                Ask Aria for guidance, then select a course below to apply.
              </p>
              <div style={styles.courseGrid}>
                {courses.map(c => (
                  <div key={c.id}
                    style={{ ...styles.courseCard, ...(selected === c.id ? styles.courseSelected : {}) }}
                    onClick={() => setSelected(c.id)}>
                    <div style={styles.courseType}>{c.type}</div>
                    <div style={styles.courseName}>{c.name}</div>
                    <div style={styles.courseMeta}>
                      <span>{c.seats} seats</span>
                      <span style={{ color: 'var(--accent)' }}>₹{(c.fees / 100000).toFixed(1)}L</span>
                    </div>
                    {c.eligibility_summary && (
                      <div style={styles.courseElig}>{c.eligibility_summary}</div>
                    )}
                  </div>
                ))}
              </div>
              <button
                className="btn btn-primary"
                onClick={handleApply}
                disabled={applying || !selected}
                style={{ marginTop: '20px' }}
              >
                {applying && <Loader2 size={15} style={{ animation: 'spin 1s linear infinite' }} />}
                {applying ? 'Applying…' : 'Apply for Selected Course'}
              </button>
            </div>
          )}
        </div>
      </div>
    </Layout>
  )
}

const styles = {
  page:   { height: '100%', overflowY: 'auto', background: 'var(--bg-base)' },
  header: { padding: '24px 32px', borderBottom: '1px solid var(--border)', background: 'var(--bg-surface)' },
  title:  { fontFamily: 'var(--font-display)', fontSize: '22px', marginBottom: '4px' },
  sub:    { fontSize: '13px', color: 'var(--text-secondary)' },
  content:{ padding: '24px 32px', display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '760px' },
  center: { height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  statusCard: {
    display: 'flex', alignItems: 'center', gap: '16px',
    padding: '20px 24px', border: '1px solid', borderRadius: 'var(--radius-md)',
  },
  sectionTitle: { fontFamily: 'var(--font-display)', fontSize: '16px', marginBottom: '16px', display: 'flex', alignItems: 'center' },
  detailGrid:   { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', fontSize: '14px' },
  note: {
    display: 'flex', alignItems: 'flex-start', gap: '8px', marginTop: '16px',
    padding: '10px 14px', background: 'rgba(232,160,69,0.08)', borderRadius: 'var(--radius-sm)',
    fontSize: '13px', color: 'var(--warning)', border: '1px solid rgba(232,160,69,0.2)',
  },
  uploadZone: {
    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px',
    padding: '36px', border: '2px dashed var(--border)', borderRadius: 'var(--radius-md)',
    cursor: 'pointer', transition: 'var(--transition)',
  },

  // Documents panel
  courseTypeBadge: {
    fontSize: '11px', fontWeight: '600', fontFamily: 'var(--font-mono)',
    padding: '3px 10px', borderRadius: '99px', background: 'var(--accent-glow)',
    color: 'var(--accent)', border: '1px solid var(--accent)',
  },
  docCard: {
    display: 'flex', alignItems: 'flex-start', gap: '14px',
    padding: '16px', background: 'var(--bg-elevated)',
    border: '1px solid var(--border)', borderRadius: 'var(--radius-md)',
  },
  uploadedBadge: {
    fontSize: '11px', fontWeight: '600', color: 'var(--success)',
    background: 'rgba(76,175,125,0.12)', border: '1px solid rgba(76,175,125,0.25)',
    borderRadius: '99px', padding: '2px 8px', marginLeft: '10px',
    verticalAlign: 'middle',
  },
  marksRow: { display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '8px' },
  marksBadge: {
    fontSize: '12px', fontWeight: '600', padding: '3px 10px',
    borderRadius: '99px', background: 'rgba(138,116,249,0.12)',
    color: 'var(--accent)', border: '1px solid rgba(138,116,249,0.2)',
  },
  iconBtn: {
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
    width: '32px', height: '32px', borderRadius: 'var(--radius-sm)',
    border: '1px solid var(--border)', background: 'var(--bg-surface)',
    cursor: 'pointer', color: 'var(--text-secondary)', transition: 'var(--transition)',
    textDecoration: 'none',
  },
  finalizedNote: {
    marginTop: '12px', fontSize: '12px', color: 'var(--text-muted)',
    padding: '8px 12px', background: 'var(--bg-elevated)',
    borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)',
  },

  // Course selection
  courseGrid:    { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '12px' },
  courseCard: {
    padding: '16px', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)',
    cursor: 'pointer', transition: 'var(--transition)', background: 'var(--bg-elevated)',
  },
  courseSelected: { border: '1px solid var(--accent)', background: 'var(--accent-glow)' },
  courseType:     { fontSize: '11px', color: 'var(--accent)', fontWeight: '600', marginBottom: '6px', fontFamily: 'var(--font-mono)' },
  courseName:     { fontSize: '14px', fontWeight: '500', marginBottom: '10px', lineHeight: '1.4' },
  courseMeta:     { display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: 'var(--text-muted)' },
  courseElig:     { fontSize: '11px', color: 'var(--text-muted)', marginTop: '8px', lineHeight: '1.4', borderTop: '1px solid var(--border)', paddingTop: '8px' },
}
