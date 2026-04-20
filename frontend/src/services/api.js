import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({ baseURL: BASE_URL })

// ── Inject JWT token on every request ─────────────────────
api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ── Auto-logout on 401 ────────────────────────────────────
api.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      localStorage.clear()
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// ── Auth ───────────────────────────────────────────────────
export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login:    (data) => {
    const formData = new URLSearchParams()
    formData.append('username', data.email)
    formData.append('password', data.password)
    return api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
  },
}

// ── Chat ───────────────────────────────────────────────────
export const chatAPI = {
  // Returns a fetch Response (SSE stream) — not axios
  streamMessage: async (content, history) => {
    const token = localStorage.getItem('token')
    return fetch(`${BASE_URL}/chat/message`, {
      method:  'POST',
      headers: {
        'Content-Type':  'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ content, history })
    })
  },
  uploadDoc:    (file) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/chat/upload-doc', form)
  },
  listDocs: () => api.get('/chat/docs'),
}

// ── Applications ───────────────────────────────────────────
export const applicationAPI = {
  getCourses:      () => api.get('/applications/courses'),
  apply:           (course_id) => api.post('/applications/apply', { course_id }),
  uploadMarksheet: (file) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/applications/upload-marksheet', form)
  },
  deleteMarksheet: () => api.delete('/applications/delete-marksheet'),
  myDocuments:     () => api.get('/applications/my-documents'),
  myStatus:        () => api.get('/applications/my-status'),
}

// ── Admin ──────────────────────────────────────────────────
export const adminAPI = {
  getApplicants:      () => api.get('/admin/applicants'),
  getStats:           () => api.get('/admin/stats'),
  override:           (data) => api.post('/admin/override', data),
  screenAll:          () => api.post('/admin/screen-all'),
  finalize:           () => api.post('/admin/finalize'),
  setExamSchedule:    (data) => api.post('/admin/exam-schedule', data),
  createCourse:       (data) => api.post('/admin/courses', data),
  updateCourse:       (id, data) => api.put(`/admin/courses/${id}`, data),
  deleteCourse:       (id) => api.delete(`/admin/courses/${id}`),
  generateAdmitCard:  (applicationId) => api.post(`/admin/generate-admit-card/${applicationId}`),
}

// ── Email ──────────────────────────────────────────────────
export const emailAPI = {
  sendResults:    () => api.post('/email/send-results'),
  retryFailed:    () => api.post('/email/retry-failed'),
  uploadTemplate: (templateType, file) => {
    const form = new FormData()
    form.append('file', file)
    return api.post(`/email/upload-template?template_type=${templateType}`, form)
  },
  listTemplates:  () => api.get('/email/templates'),
  getLogs:        () => api.get('/email/logs'),
}

export default api
