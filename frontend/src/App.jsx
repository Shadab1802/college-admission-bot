import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { AuthProvider, useAuth } from './context/AuthContext'

import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import StudentChat from './pages/StudentChat'
import StudentDashboard from './pages/StudentDashboard'
import DirectorChat from './pages/DirectorChat'
import DirectorDashboard from './pages/DirectorDashboard'

function ProtectedRoute({ children, requiredRole }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (requiredRole && user.role !== requiredRole) return <Navigate to="/login" replace />
  return children
}

function RootRedirect() {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  return user.role === 'director'
    ? <Navigate to="/director/chat" replace />
    : <Navigate to="/student/chat" replace />
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: '#1e1e1e',
              color: '#f0ece4',
              border: '1px solid #2a2a2a',
              fontFamily: 'DM Sans, sans-serif',
              fontSize: '14px',
            },
            success: { iconTheme: { primary: '#4caf7d', secondary: '#0f0f0f' } },
            error: { iconTheme: { primary: '#e05c5c', secondary: '#0f0f0f' } },
          }}
        />
        <Routes>
          <Route path="/" element={<RootRedirect />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* Student routes */}
          <Route path="/student/chat" element={
            <ProtectedRoute requiredRole="student"><StudentChat /></ProtectedRoute>
          } />
          <Route path="/student/dashboard" element={
            <ProtectedRoute requiredRole="student"><StudentDashboard /></ProtectedRoute>
          } />

          {/* Director routes */}
          <Route path="/director/chat" element={
            <ProtectedRoute requiredRole="director"><DirectorChat /></ProtectedRoute>
          } />
          <Route path="/director/dashboard" element={
            <ProtectedRoute requiredRole="director"><DirectorDashboard /></ProtectedRoute>
          } />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}