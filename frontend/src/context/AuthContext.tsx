// src/context/AuthContext.tsx
import React, { createContext, useContext, useState, useEffect } from 'react'
import api from '@/api/client'
import { writeLog } from '@/utils/activityLogger'

export type UserRole = 'ADMIN' | 'STAFF' | 'MARKETING'

export interface UserProfile {
  id: number | string
  email: string
  username: string
  full_name: string
  role: UserRole
  is_active: number | boolean
}

interface AuthContextType {
  user: UserProfile | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (identifier: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const logout = () => {
    const stored = localStorage.getItem('pharmacast_user')
    let username = 'unknown'
    let role = 'UNKNOWN'
    if (stored) {
      try {
        const u = JSON.parse(stored)
        username = u.username
        role = u.role
      } catch {}
    }
    writeLog({
      event_type: 'LOGOUT',
      message: `User '${username}' logged out.`,
      username,
      user_role: role,
      status: 'INFO',
    })
    setUser(null)
    setToken(null)
    localStorage.removeItem('pharmacast_token')
    localStorage.removeItem('pharmacast_user')
    delete api.defaults.headers.common['Authorization']
  }

  useEffect(() => {
    const storedToken = localStorage.getItem('pharmacast_token')
    const storedUser  = localStorage.getItem('pharmacast_user')

    if (storedToken && storedUser) {
      try {
        const parsedUser = JSON.parse(storedUser)
        setToken(storedToken)
        setUser(parsedUser)
        api.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`
      } catch (e) {
        console.error('Failed to parse stored user auth state', e)
        logout()
      }
    } else {
      // Strictly unauthenticated when no token is present
      setUser(null)
      setToken(null)
    }
    setIsLoading(false)
  }, [])

  const saveAuthState = (newToken: string, newUser: UserProfile) => {
    setToken(newToken)
    setUser(newUser)
    localStorage.setItem('pharmacast_token', newToken)
    localStorage.setItem('pharmacast_user', JSON.stringify(newUser))
    api.defaults.headers.common['Authorization'] = `Bearer ${newToken}`
  }

  const login = async (identifier: string, password: string) => {
    const res = await api.post('/auth/login', {
      username_or_email: identifier,
      password,
    })
    const { access_token, user: userProfile } = res.data
    saveAuthState(access_token, userProfile)
    // Client-side login log (backend also logs this, belt-and-suspenders)
    writeLog({
      event_type: 'LOGIN',
      message: `User '${userProfile.username}' session started in browser.`,
      username: userProfile.username,
      user_role: userProfile.role,
      status: 'SUCCESS',
    })
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user && !!token,
        isLoading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
