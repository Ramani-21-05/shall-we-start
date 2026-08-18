// src/pages/AdminUsersPage.tsx
import { useState, useEffect } from 'react'
import api from '@/api/client'
import { useAuth } from '@/context/AuthContext'
import type { UserRole } from '@/context/AuthContext'
import { UserPlus, Shield, Copy, Check, Users, RefreshCw, Mail, User, Key, Lock, Trash2, AlertTriangle } from 'lucide-react'
import { getErrorMessage } from '@/utils/errorUtils'

interface UserItem {
  id: number | string
  email: string
  username: string
  full_name: string
  role: UserRole
  is_active: number | boolean
  created_at: string
}

export function AdminUsersPage() {
  const { user: currentUser } = useAuth()
  const [users, setUsers] = useState<UserItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorMsg, setErrorMsg] = useState('')

  // Form State
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [role, setRole] = useState<UserRole>('STAFF')
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Generated Result Banner
  const [createdResult, setCreatedResult] = useState<{
    user: UserItem
    initialPassword: string
  } | null>(null)
  const [copied, setCopied] = useState(false)

  // Email Action Sending States
  const [sendingEmailUserId, setSendingEmailUserId] = useState<string | number | null>(null)
  const [sentEmailUserIds, setSentEmailUserIds] = useState<Record<string | number, boolean>>({})

  // Delete Action Loading State
  const [deletingUserId, setDeletingUserId] = useState<string | number | null>(null)

  const fetchUsers = async () => {
    setIsLoading(true)
    try {
      const res = await api.get('/auth/admin/users')
      setUsers(res.data.users || [])
      setErrorMsg('')
    } catch (err: any) {
      setErrorMsg('Failed to load user list. Verify Admin permissions.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchUsers()
  }, [])

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMsg('')
    setCreatedResult(null)
    setIsSubmitting(true)

    try {
      const res = await api.post('/auth/admin/create-user', {
        full_name: fullName,
        email,
        username,
        role,
      })

      setCreatedResult({
        user: res.data.user,
        initialPassword: res.data.initial_password,
      })

      setFullName('')
      setEmail('')
      setUsername('')
      fetchUsers()
    } catch (err: any) {
      setErrorMsg(getErrorMessage(err, 'Failed to provision user account.'))
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleCopyPassword = () => {
    if (createdResult?.initialPassword) {
      navigator.clipboard.writeText(createdResult.initialPassword)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleToggleStatus = async (userId: number | string, currentStatus: boolean | number) => {
    const newStatus = !currentStatus
    try {
      await api.post('/auth/admin/toggle-user-status', {
        user_id: userId,
        is_active: newStatus,
      })
      fetchUsers()
    } catch (err: any) {
      setErrorMsg('Failed to update user status.')
    }
  }

  const handleSendCredentialsEmail = async (targetUser: UserItem) => {
    const confirmed = window.confirm(`Send login credentials email to ${targetUser.full_name} (${targetUser.email})?`)
    if (!confirmed) return

    setSendingEmailUserId(targetUser.id)
    try {
      const res = await api.post('/auth/send-credentials-email', { identifier: targetUser.email })
      setSentEmailUserIds(prev => ({ ...prev, [targetUser.id]: true }))
      alert(`✓ Success! Credentials email dispatched to ${res.data.email_id}.\nTemporary Password: ${res.data.temporary_password}`)
    } catch (err: any) {
      alert(getErrorMessage(err, 'Failed to dispatch email.'))
    } finally {
      setSendingEmailUserId(null)
    }
  }

  const handleDeleteUser = async (targetUser: UserItem) => {
    if (String(targetUser.id) === String(currentUser?.id) || targetUser.username === currentUser?.username) {
      alert('🔒 Protection Error: You cannot delete your own active Admin account.')
      return
    }

    const confirmed = window.confirm(
      `⚠️ PERMANENT DELETION CONFIRMATION:\n\nAre you sure you want to permanently delete user account '${targetUser.username}' (${targetUser.email})?\n\nThis action cannot be undone.`
    )
    if (!confirmed) return

    setDeletingUserId(targetUser.id)
    try {
      await api.delete(`/auth/admin/delete-user/${targetUser.id}`)
      alert(`User '${targetUser.username}' permanently deleted.`)
      fetchUsers()
    } catch (err: any) {
      alert(getErrorMessage(err, 'Failed to delete user account.'))
    } finally {
      setDeletingUserId(null)
    }
  }

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Page Title */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Shield className="text-indigo-400" size={24} />
            <h1 className="text-2xl font-bold gradient-text">User Provisioning & Access Control</h1>
          </div>
          <p className="text-xs text-slate-400">
            Admin console for provisioning, managing, emailing credentials, toggling active status, and deleting user accounts
          </p>
        </div>
        <button
          onClick={fetchUsers}
          className="px-3 py-1.5 glass-card-sm text-xs font-semibold text-slate-300 hover:text-white flex items-center gap-1.5 border border-white/10 rounded-lg cursor-pointer"
        >
          <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} /> Refresh List
        </button>
      </div>

      {errorMsg && (
        <div className="p-4 glass-card border-l-4 border-red-400 text-red-300 text-xs bg-red-950/20">
          {errorMsg}
        </div>
      )}

      {/* Grid: Create User Form + Provisioning Result */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Provision Form */}
        <div className="lg:col-span-5 glass-card p-6 border border-indigo-500/20 space-y-4">
          <div className="flex items-center gap-2 pb-2 border-b border-white/5">
            <UserPlus size={18} className="text-indigo-400" />
            <h2 className="font-bold text-white text-sm">Provision New User Account</h2>
          </div>

          <form onSubmit={handleCreateUser} className="space-y-3.5">
            <div>
              <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                Full Name
              </label>
              <div className="relative">
                <User size={15} className="absolute left-3 top-2.5 text-slate-500" />
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={e => setFullName(e.target.value)}
                  placeholder="e.g. Sarah Jenkins"
                  className="w-full bg-slate-900/80 border border-white/10 rounded-lg pl-9 pr-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <div>
              <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                Email Address (Receives Credentials)
              </label>
              <div className="relative">
                <Mail size={15} className="absolute left-3 top-2.5 text-slate-500" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="sarah@pharmacast.com"
                  className="w-full bg-slate-900/80 border border-white/10 rounded-lg pl-9 pr-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <div>
              <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                Username
              </label>
              <input
                type="text"
                required
                value={username}
                onChange={e => setUsername(e.target.value.toLowerCase())}
                placeholder="sarah_j"
                className="w-full bg-slate-900/80 border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                Assign System Role
              </label>
              <select
                value={role}
                onChange={e => setRole(e.target.value as UserRole)}
                className="w-full bg-slate-900/80 border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500 cursor-pointer"
              >
                <option value="STAFF" className="bg-slate-900">STAFF — Inventory & Replenishment Only</option>
                <option value="MARKETING" className="bg-slate-900">MARKETING — Dashboard, Forecast & Strategy</option>
                <option value="ADMIN" className="bg-slate-900">ADMIN — Full System Superuser</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 font-semibold text-xs text-white rounded-lg transition-all shadow-md flex items-center justify-center gap-2 cursor-pointer mt-2 disabled:opacity-50"
            >
              <UserPlus size={14} />
              {isSubmitting ? 'Provisioning & Emailing…' : 'Generate, Provision & Email Credentials'}
            </button>
          </form>
        </div>

        {/* Provisioning Result & Info */}
        <div className="lg:col-span-7 space-y-4">
          {createdResult ? (
            <div className="glass-card p-6 border-2 border-emerald-500/40 bg-emerald-950/10 space-y-4 animate-fade-in">
              <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm">
                <Check size={18} />
                <span>Account Provisioned & Email Dispatched!</span>
              </div>

              <div className="grid grid-cols-2 gap-4 text-xs">
                <div>
                  <p className="text-slate-400 font-semibold uppercase text-[10px]">User Name</p>
                  <p className="text-white font-medium">{createdResult.user.full_name}</p>
                </div>
                <div>
                  <p className="text-slate-400 font-semibold uppercase text-[10px]">Username</p>
                  <p className="text-indigo-300 font-mono font-medium">{createdResult.user.username}</p>
                </div>
                <div>
                  <p className="text-slate-400 font-semibold uppercase text-[10px]">Email ID (Sent To)</p>
                  <p className="text-emerald-300 font-mono">{createdResult.user.email}</p>
                </div>
                <div>
                  <p className="text-slate-400 font-semibold uppercase text-[10px]">Role</p>
                  <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                    {createdResult.user.role}
                  </span>
                </div>
              </div>

              {/* Initial Password Display Strip */}
              <div className="p-3 bg-slate-950 border border-amber-500/30 rounded-xl space-y-1.5">
                <p className="text-[10px] font-semibold text-amber-400 uppercase tracking-wider flex items-center gap-1">
                  <Key size={12} /> Generated Initial Temporary Password (Sent via Email):
                </p>
                <div className="flex items-center justify-between gap-3">
                  <span className="font-mono text-base font-bold text-emerald-300 bg-slate-900 px-3 py-1 rounded border border-emerald-500/30 select-all">
                    {createdResult.initialPassword}
                  </span>
                  <button
                    onClick={handleCopyPassword}
                    className="px-3 py-1.5 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 text-xs font-semibold rounded-lg border border-amber-500/40 flex items-center gap-1.5 cursor-pointer transition-all"
                  >
                    {copied ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
                    {copied ? 'Copied!' : 'Copy Password'}
                  </button>
                </div>
              </div>

              <p className="text-[11px] text-emerald-400/90 italic">
                ✓ Credentials containing Email ID, Username, and Password have been dispatched to {createdResult.user.email}.
              </p>
            </div>
          ) : (
            <div className="glass-card p-6 border border-white/5 space-y-3">
              <div className="flex items-center gap-2 text-indigo-300 font-semibold text-xs">
                <Lock size={14} />
                <span>Automated Email Dispatch Service</span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                When you provision a new account, the platform automatically generates a temporary password and dispatches an HTML email to the user containing their <strong>Email ID</strong>, <strong>Username</strong>, <strong>Password</strong>, and system login link.
              </p>
            </div>
          )}

          {/* User Count Summary */}
          <div className="grid grid-cols-3 gap-4">
            <div className="glass-card p-4 text-center space-y-1">
              <p className="text-[10px] font-semibold uppercase text-slate-400">Total System Users</p>
              <p className="text-2xl font-bold text-white">{users.length}</p>
            </div>
            <div className="glass-card p-4 text-center space-y-1">
              <p className="text-[10px] font-semibold uppercase text-cyan-400">Staff Members</p>
              <p className="text-2xl font-bold text-cyan-300">{users.filter(u => u.role === 'STAFF').length}</p>
            </div>
            <div className="glass-card p-4 text-center space-y-1">
              <p className="text-[10px] font-semibold uppercase text-amber-400">Marketing Members</p>
              <p className="text-2xl font-bold text-amber-300">{users.filter(u => u.role === 'MARKETING').length}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Users Table */}
      <div className="glass-card p-6 border border-white/5 space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-white/5">
          <div className="flex items-center gap-2">
            <Users size={18} className="text-indigo-400" />
            <h2 className="font-bold text-white text-sm">Provisioned System Users ({users.length})</h2>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-white/10 text-slate-400 uppercase text-[10px] tracking-wider">
                <th className="pb-3 px-3">Full Name</th>
                <th className="pb-3 px-3">Username</th>
                <th className="pb-3 px-3">Email ID</th>
                <th className="pb-3 px-3">Role</th>
                <th className="pb-3 px-3">Status</th>
                <th className="pb-3 px-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-slate-200">
              {users.map(u => {
                const isSelf = String(u.id) === String(currentUser?.id) || u.username === currentUser?.username
                const isSendingThis = sendingEmailUserId === u.id
                const isSentThis = !!sentEmailUserIds[u.id]
                const isDeletingThis = deletingUserId === u.id

                return (
                  <tr key={u.id} className="hover:bg-white/5 transition-colors">
                    <td className="py-3 px-3 font-medium text-white flex items-center gap-2">
                      <span>{u.full_name}</span>
                      {isSelf && (
                        <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                          YOU
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-3 font-mono text-indigo-300">{u.username}</td>
                    <td className="py-3 px-3 text-slate-300 font-mono">{u.email}</td>
                    <td className="py-3 px-3">
                      <span
                        className={`inline-block px-2.5 py-0.5 rounded text-[10px] font-bold border ${
                          u.role === 'ADMIN'
                            ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                            : u.role === 'STAFF'
                            ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30'
                            : 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                        }`}
                      >
                        {u.role}
                      </span>
                    </td>
                    <td className="py-3 px-3">
                      <button
                        onClick={() => handleToggleStatus(u.id, u.is_active)}
                        className={`px-2 py-0.5 rounded text-[11px] font-semibold transition-all cursor-pointer flex items-center gap-1 border ${
                          u.is_active
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30 hover:bg-red-500/20 hover:text-red-300 hover:border-red-500/40'
                            : 'bg-red-500/10 text-red-400 border-red-500/30 hover:bg-emerald-500/20 hover:text-emerald-300 hover:border-emerald-500/40'
                        }`}
                      >
                        <span className={`w-1.5 h-1.5 rounded-full ${u.is_active ? 'bg-emerald-400' : 'bg-red-400'}`} />
                        {u.is_active ? 'Active' : 'Deactivated'}
                      </button>
                    </td>
                    <td className="py-3 px-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {/* Send Email Button (Only for STAFF and MARKETING roles, not ADMIN) */}
                        {u.role !== 'ADMIN' && (
                          <button
                            onClick={() => handleSendCredentialsEmail(u)}
                            disabled={isSendingThis}
                            className={`px-2.5 py-1 text-[11px] font-semibold rounded-md transition-all cursor-pointer flex items-center gap-1 border ${
                              isSendingThis
                                ? 'bg-slate-800 text-slate-400 border-slate-700 cursor-not-allowed opacity-75'
                                : isSentThis
                                ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 hover:bg-emerald-500/30'
                                : 'glass-card-sm text-indigo-300 hover:text-white border-indigo-500/30 hover:bg-indigo-500/20'
                            }`}
                          >
                            {isSendingThis ? (
                              <>
                                <RefreshCw size={12} className="animate-spin text-slate-400" />
                                <span>Sending…</span>
                              </>
                            ) : isSentThis ? (
                              <>
                                <Check size={12} className="text-emerald-400" />
                                <span>Sent ✓</span>
                              </>
                            ) : (
                              <>
                                <Mail size={12} />
                                <span>Send Email</span>
                              </>
                            )}
                          </button>
                        )}

                        {/* Delete User Button */}
                        <button
                          onClick={() => handleDeleteUser(u)}
                          disabled={isSelf || isDeletingThis}
                          title={isSelf ? 'Cannot delete your own logged-in Admin account' : `Delete ${u.username}`}
                          className={`px-2 py-1 text-[11px] font-semibold rounded-md transition-all flex items-center gap-1 border ${
                            isSelf
                              ? 'bg-slate-900/50 text-slate-600 border-slate-800 cursor-not-allowed opacity-40'
                              : isDeletingThis
                              ? 'bg-red-950/80 text-red-400 border-red-800 cursor-wait'
                              : 'bg-red-500/10 text-red-400 border-red-500/30 hover:bg-red-500/25 hover:text-red-200 cursor-pointer'
                          }`}
                        >
                          <Trash2 size={12} className={isDeletingThis ? 'animate-bounce' : ''} />
                          <span>{isDeletingThis ? 'Deleting…' : 'Delete'}</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
