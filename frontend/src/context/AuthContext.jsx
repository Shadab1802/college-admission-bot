import { createContext, useContext, useState, useEffect } from 'react'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const token = localStorage.getItem('token')
    const role  = localStorage.getItem('role')
    if (token && role) {
      return {
        token, role,
        name: localStorage.getItem('name'),
        userId: localStorage.getItem('user_id')
      }
    }
    return null
  })

  const login = (data) => {
    localStorage.setItem('token',   data.access_token)
    localStorage.setItem('role',    data.role)
    localStorage.setItem('name',    data.name)
    localStorage.setItem('user_id', data.user_id)
    setUser({ token: data.access_token, role: data.role, name: data.name, userId: data.user_id })
  }

  const logout = () => {
    localStorage.clear()
    setUser(null)
    window.location.href = '/login'
  }

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
