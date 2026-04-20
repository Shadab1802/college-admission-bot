import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import { chatAPI } from '../services/api'
import { useAuth } from '../context/AuthContext'
import { Send, Loader2, GraduationCap, User, Upload, CheckCircle } from 'lucide-react'
import { applicationAPI } from '../services/api'
import { toast } from 'react-hot-toast'

function InlineUpload() {
  const [uploading, setUploading] = useState(false)
  const [done, setDone]           = useState(false)
  const fileInputRef              = useRef(null)

  const handleUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setUploading(true)
    try {
      await applicationAPI.uploadMarksheet(file)
      toast.success('Marksheet uploaded successfully!')
      setDone(true)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  if (done) return (
    <div style={styles.inlineActionDone}>
      <CheckCircle size={16} color="var(--success)" />
      <span>Marksheet Uploaded</span>
    </div>
  )

  return (
    <div style={styles.inlineAction}>
      <label style={styles.inlineUploadLabel}>
        {uploading ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> : <Upload size={16} />}
        <span>{uploading ? 'Uploading…' : 'Upload Marksheet (PDF)'}</span>
        <input type="file" accept=".pdf" style={{ display: 'none' }} onChange={handleUpload} disabled={uploading} />
      </label>
    </div>
  )
}

function InlineApply({ courseId }) {
  const [applying, setApplying] = useState(false)
  const [done, setDone]         = useState(false)

  const handleApply = async () => {
    setApplying(true)
    try {
      await applicationAPI.apply(courseId)
      toast.success('Application submitted!')
      setDone(true)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Application failed')
    } finally {
      setApplying(false)
    }
  }

  if (done) return (
    <div style={styles.inlineActionDone}>
      <CheckCircle size={16} color="var(--success)" />
      <span>Applied successfully</span>
    </div>
  )

  return (
    <div style={styles.inlineAction}>
      <button style={styles.inlineApplyBtn} onClick={handleApply} disabled={applying}>
        {applying ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> : <GraduationCap size={16} />}
        <span>Apply for this Course</span>
      </button>
    </div>
  )
}

function MessageBubble({ msg }) {
  const isAria = msg.role === 'assistant'
  
  // Parse content for markers
  let content = msg.content
  const hasUploadMarker = content.includes('[UPLOAD_MARKSHEET]')
  const actionMatch     = content.match(/\[ACTION:apply_course:\s*(\d+)\]/)
  
  // Clean markers from display text
  content = content.replace(/\[UPLOAD_MARKSHEET\]/g, '')
  content = content.replace(/\[ACTION:apply_course:\s*\d+\]/g, '')

  return (
    <div style={{ ...styles.msgRow, flexDirection: 'column', alignItems: isAria ? 'flex-start' : 'flex-end' }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: '10px', width: '100%', justifyContent: isAria ? 'flex-start' : 'flex-end' }}>
        {isAria && (
          <div style={styles.ariaAvatar}>
            <GraduationCap size={14} color="var(--accent)" />
          </div>
        )}
        <div style={{ ...styles.bubble, ...(isAria ? styles.ariaBubble : styles.userBubble) }} className="markdown-body">
          {isAria ? (
            <ReactMarkdown>{content}</ReactMarkdown>
          ) : (
            content.split('\n').map((line, i) => (
              <span key={i}>{line}{i < content.split('\n').length - 1 && <br />}</span>
            ))
          )}
          {msg.streaming && <span style={styles.cursor}>▋</span>}
        </div>
        {!isAria && (
          <div style={styles.userAvatar}>
            <User size={14} color="var(--text-secondary)" />
          </div>
        )}
      </div>

      {/* Render Action Widgets if marker present and not streaming */}
      {isAria && !msg.streaming && (
        <div style={{ marginLeft: '40px', marginTop: '8px' }}>
          {hasUploadMarker && <InlineUpload />}
          {actionMatch && <InlineApply courseId={actionMatch[1]} />}
        </div>
      )}
    </div>
  )
}

export default function ChatWindow({ systemContext = '' }) {
  const { user }                = useAuth()

  const [messages, setMessages] = useState(() => {
    const saved = user ? sessionStorage.getItem(`aria_chat_${user.userId}`) : null
    if (saved) return JSON.parse(saved)
    return [
      {
        role: 'assistant',
        content: "Hi! I'm Aria, your admissions assistant at IEM Kolkata 🎓\nHow can I help you today? Ask me anything about courses, fees, eligibility, or your application.",
      }
    ]
  })
  
  const [input, setInput]       = useState('')
  const [loading, setLoading]   = useState(false)
  const bottomRef               = useRef(null)
  const inputRef                = useRef(null)

  useEffect(() => {
    if (user) sessionStorage.setItem(`aria_chat_${user.userId}`, JSON.stringify(messages))
  }, [messages, user])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async () => {
    if (!input.trim() || loading) return

    const userMsg = { role: 'user', content: input.trim() }
    const history = messages.filter(m => !m.streaming).map(m => ({
      role: m.role, content: m.content
    }))

    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    // Add empty Aria bubble that will stream into
    setMessages(prev => [...prev, { role: 'assistant', content: '', streaming: true }])

    try {
      const response = await chatAPI.streamMessage(userMsg.content, history)
      if (!response.ok) throw new Error('Stream failed')

      const reader  = response.body.getReader()
      const decoder = new TextDecoder()
      let   buffer  = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()  // keep incomplete line

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const rawToken = line.slice(6)
          if (rawToken === '[DONE]') break

          let token = ''
          try {
            token = JSON.parse(rawToken)
          } catch (e) {
            token = rawToken
          }

          setMessages(prev => {
            const updated = [...prev]
            // Deep copy to prevent React StrictMode from mutating the state twice
            const last    = { ...updated[updated.length - 1] } 
            if (last.streaming) {
              last.content += token
              updated[updated.length - 1] = last
            }
            return updated
          })
        }
      }

      // Mark streaming done
      setMessages(prev => {
        const updated = [...prev]
        const last    = updated[updated.length - 1]
        if (last.streaming) delete last.streaming
        return updated
      })

    } catch (err) {
      setMessages(prev => {
        const updated = [...prev]
        updated[updated.length - 1] = {
          role: 'assistant',
          content: 'Sorry, I had trouble responding. Please try again.'
        }
        return updated
      })
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
  }

  const suggestions = [
    'What are the BTech eligibility criteria?',
    'What are the fees for BCA?',
    'What documents do I need?',
    'When is the last date to apply?',
  ]

  return (
    <div style={styles.container}>
      {/* Messages */}
      <div style={styles.messages}>
        {messages.length === 1 && (
          <div style={styles.suggestions}>
            <p style={styles.suggestLabel}>Suggested questions</p>
            <div style={styles.suggestGrid}>
              {suggestions.map(s => (
                <button key={s} style={styles.suggestBtn}
                  onClick={() => { setInput(s); inputRef.current?.focus() }}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((msg, i) => <MessageBubble key={i} msg={msg} />)}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div style={styles.inputBar}>
        <textarea
          ref={inputRef}
          rows={1}
          placeholder="Ask Aria anything about admissions…"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          style={styles.textarea}
        />
        <button
          onClick={sendMessage}
          disabled={!input.trim() || loading}
          style={styles.sendBtn}
          className="btn btn-primary"
        >
          {loading
            ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
            : <Send size={16} />
          }
        </button>
      </div>
    </div>
  )
}

const styles = {
  container: { display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' },
  messages: {
    flex: 1, overflowY: 'auto', padding: '24px',
    display: 'flex', flexDirection: 'column', gap: '16px',
  },
  msgRow:     { display: 'flex', alignItems: 'flex-end', gap: '10px' },
  ariaAvatar: {
    width: '30px', height: '30px', borderRadius: '50%',
    background: 'var(--accent-glow)', border: '1px solid var(--accent)',
    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
  },
  userAvatar: {
    width: '30px', height: '30px', borderRadius: '50%',
    background: 'var(--bg-elevated)', border: '1px solid var(--border)',
    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
  },
  bubble: {
    maxWidth: '72%', padding: '12px 16px', borderRadius: '16px',
    fontSize: '14px', lineHeight: '1.65',
  },
  ariaBubble: {
    background: 'var(--bg-elevated)', border: '1px solid var(--border)',
    borderBottomLeftRadius: '4px', color: 'var(--text-primary)',
  },
  userBubble: {
    background: 'var(--accent)', color: '#0f0f0f', fontWeight: '500',
    borderBottomRightRadius: '4px',
  },
  cursor: { display: 'inline-block', animation: 'pulse 0.8s ease-in-out infinite', marginLeft: '2px' },
  suggestions: { marginBottom: '8px' },
  suggestLabel: { fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px', fontWeight: '500' },
  suggestGrid:  { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' },
  suggestBtn: {
    padding: '10px 12px', background: 'var(--bg-elevated)',
    border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)',
    color: 'var(--text-secondary)', fontSize: '12px', textAlign: 'left',
    cursor: 'pointer', transition: 'var(--transition)', lineHeight: '1.4',
  },
  inputBar: {
    padding: '16px 24px', borderTop: '1px solid var(--border)',
    display: 'flex', gap: '10px', alignItems: 'flex-end',
    background: 'var(--bg-surface)',
  },
  textarea: {
    flex: 1, resize: 'none', minHeight: '42px', maxHeight: '120px',
    padding: '10px 14px', borderRadius: 'var(--radius-sm)',
    fontSize: '14px', lineHeight: '1.5', background: 'var(--bg-elevated)',
    border: '1px solid var(--border)', color: 'var(--text-primary)',
    fontFamily: 'var(--font-body)',
  },
  sendBtn: { height: '42px', width: '42px', padding: '0', justifyContent: 'center', borderRadius: 'var(--radius-sm)', flexShrink: 0 },
  
  // Inline Actions
  inlineAction: {
    marginTop: '4px', background: 'var(--bg-elevated)', border: '1px solid var(--border)',
    borderRadius: '12px', padding: '10px 16px', display: 'inline-flex', alignItems: 'center',
  },
  inlineActionDone: {
    marginTop: '4px', display: 'inline-flex', alignItems: 'center', gap: '8px',
    fontSize: '12px', color: 'var(--success)', padding: '6px 12px',
    background: 'rgba(76,175,125,0.08)', borderRadius: '99px', border: '1px solid rgba(76,175,125,0.2)'
  },
  inlineUploadLabel: {
    display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer',
    fontSize: '13px', fontWeight: '500', color: 'var(--accent)',
  },
  inlineApplyBtn: {
    background: 'none', border: 'none', padding: '0', cursor: 'pointer',
    display: 'flex', alignItems: 'center', gap: '10px',
    fontSize: '13px', fontWeight: '500', color: 'var(--accent)',
    fontFamily: 'inherit',
  }
}
