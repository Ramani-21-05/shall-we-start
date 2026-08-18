// src/components/auth/ProtectedRoute.tsx
import React from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import type { UserRole } from '@/context/AuthContext'
import { ShieldAlert, ArrowLeft } from 'lucide-react'

interface ProtectedRouteProps {
  children: React.ReactNode
  allowedRoles?: UserRole[]
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles }) => {
  const { user, isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-10 h-10 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return (
      <div className="flex items-center justify-center min-h-[70vh] p-4">
        <div className="glass-card p-8 max-w-md text-center space-y-4 border border-red-500/30">
          <ShieldAlert size={48} className="text-red-400 mx-auto" />
          <h2 className="text-xl font-bold text-white">Access Denied</h2>
          <p className="text-xs text-slate-400 leading-relaxed">
            Your current role <span className="font-bold text-red-400">({user.role})</span> does not have permission to view this section.
          </p>
          <div className="pt-2">
            <Navigate to={user.role === 'STAFF' ? '/simulation' : '/dashboard'} replace />
          </div>
        </div>
      </div>
    )
  }

  return <>{children}</>
}
