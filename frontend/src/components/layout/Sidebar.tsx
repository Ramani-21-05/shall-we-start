// src/components/layout/Sidebar.tsx
import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import type { UserRole } from '@/context/AuthContext'
import { ChangePasswordModal } from '@/components/auth/ChangePasswordModal'
import {
  LayoutDashboard,
  PlayCircle,
  TrendingUp,
  History,
  Lightbulb,
  AlertTriangle,
  Target,
  LogOut,
  User,
  Shield,
  Sparkles,
  Key,
  Users,
  ScrollText,
  Menu,
  X,
} from 'lucide-react'

interface NavItem {
  to: string
  icon: any
  label: string
  roles: UserRole[]
}

interface NavSection {
  title: string
  items: NavItem[]
}

const NAV_SECTIONS: NavSection[] = [
  {
    title: 'Dashboard & Analytics',
    items: [
      { to: '/dashboard', icon: LayoutDashboard, label: 'Sales Dashboard', roles: ['ADMIN', 'MARKETING'] },
      { to: '/strategy', icon: Target, label: 'Strategy Intelligence', roles: ['MARKETING'] },
    ],
  },
  {
    title: 'Operations',
    items: [
      { to: '/simulation', icon: PlayCircle, label: 'Live 2019 Simulation', roles: ['ADMIN', 'STAFF'] },
    ],
  },
  {
    title: 'Intelligence & Forecasting',
    items: [
      { to: '/forecast', icon: TrendingUp, label: 'Demand Forecast', roles: ['ADMIN', 'MARKETING'] },
      { to: '/performance', icon: History, label: 'Past Performance', roles: ['ADMIN', 'MARKETING'] },
      { to: '/explainability', icon: Lightbulb, label: 'Explainability', roles: ['ADMIN'] },
    ],
  },
  {
    title: 'Administration',
    items: [
      { to: '/admin/users', icon: Users, label: 'User Provisioning', roles: ['ADMIN'] },
      { to: '/admin/logs',  icon: ScrollText, label: 'Logs', roles: ['ADMIN'] },
    ],
  },
]

const ROLE_BADGES: Record<UserRole, { label: string; color: string }> = {
  ADMIN:     { label: 'ADMIN', color: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' },
  STAFF:     { label: 'STAFF', color: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30' },
  MARKETING: { label: 'MARKETING', color: 'bg-amber-500/20 text-amber-300 border-amber-500/30' },
}

export function Sidebar() {
  const { user, logout } = useAuth()
  const userRole = user?.role || 'ADMIN'
  const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false)
  const [isMobileOpen, setIsMobileOpen] = useState(false)

  // Filter sections by role
  const visibleSections = NAV_SECTIONS.map(section => ({
    title: section.title,
    items: section.items.filter(item => item.roles.includes(userRole)),
  })).filter(section => section.items.length > 0)

  return (
    <>
      {/* Mobile Top Header Bar (< lg) */}
      <div className="lg:hidden fixed top-0 left-0 right-0 h-14 bg-[#0b1120] border-b border-white/10 px-4 flex items-center justify-between z-40 shadow-md">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsMobileOpen(!isMobileOpen)}
            className="p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
            aria-label="Toggle navigation menu"
          >
            {isMobileOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-cyan-400 flex items-center justify-center shadow">
              <span className="text-white font-black text-xs">Rx</span>
            </div>
            <span className="font-bold text-white text-sm">PharmaCast</span>
          </div>
        </div>
        {user && (
          <span className="text-[10px] font-bold text-indigo-300 bg-indigo-500/20 px-2.5 py-1 rounded-full border border-indigo-500/30">
            {user.role}
          </span>
        )}
      </div>

      {/* Mobile Drawer Backdrop Overlay */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-slate-950/70 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* Sidebar Container — Drawer on mobile, fixed on desktop */}
      <aside className={`sidebar flex flex-col justify-between transition-transform duration-300 ease-in-out z-50 ${isMobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}>
        <div>
          {/* Logo */}
          <div className="px-5 py-5 border-b border-white/5 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-cyan-400 flex items-center justify-center shadow-lg">
                <span className="text-white font-black text-sm">Rx</span>
              </div>
              <div>
                <p className="font-bold text-white text-sm leading-tight">PharmaCast</p>
                <p className="text-[10px] text-indigo-400 font-medium">Demand Intelligence</p>
              </div>
            </div>
            {/* Close button inside sidebar on mobile */}
            <button
              onClick={() => setIsMobileOpen(false)}
              className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10"
            >
              <X size={18} />
            </button>
          </div>

          {/* User Profile Badge & Change Password Trigger */}
          {user && (
            <div className="px-4 py-3 mx-3 mt-3 glass-card-sm border border-white/10 rounded-xl space-y-1.5">
              <div className="flex items-center justify-between">
                <p className="text-xs font-bold text-white truncate max-w-[120px]">{user.full_name}</p>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setIsPasswordModalOpen(true)}
                    title="Change Password"
                    className="p-1 rounded text-slate-400 hover:text-amber-300 hover:bg-white/5 transition-all cursor-pointer"
                  >
                    <Key size={13} />
                  </button>
                  <button
                    onClick={logout}
                    title="Sign Out"
                    className="p-1 rounded text-slate-400 hover:text-red-400 hover:bg-white/5 transition-all cursor-pointer"
                  >
                    <LogOut size={13} />
                  </button>
                </div>
              </div>
              <span className={`inline-block text-[10px] px-2 py-0.5 rounded-full font-bold border ${ROLE_BADGES[userRole].color}`}>
                {ROLE_BADGES[userRole].label}
              </span>
            </div>
          )}

          {/* Navigation */}
          <nav className="px-3 py-4 space-y-5">
            {visibleSections.map((section, idx) => (
              <div key={idx} className="space-y-1">
                <p className="px-3 mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
                  {section.title}
                </p>
                {section.items.map(({ to, icon: Icon, label }) => (
                  <NavLink
                    key={to}
                    to={to}
                    onClick={() => setIsMobileOpen(false)}
                    className={({ isActive }) =>
                      `sidebar-item ${isActive ? 'active' : ''}`
                    }
                  >
                    <Icon size={16} className="shrink-0" />
                    {label}
                  </NavLink>
                ))}
              </div>
            ))}
          </nav>
        </div>

        {/* Footer Data Integrity */}
        <div className="px-4 py-4 border-t border-white/5 space-y-3">
          <div className="glass-card-sm px-3 py-2 space-y-1">
            <div className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 pulse-dot" />
              <p className="text-[11px] text-emerald-400">Train: 2014–2018</p>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-amber-400" />
              <p className="text-[11px] text-amber-400">Anomaly: 2019 only</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Change Password Modal */}
      <ChangePasswordModal
        isOpen={isPasswordModalOpen}
        onClose={() => setIsPasswordModalOpen(false)}
      />
    </>
  )
}
