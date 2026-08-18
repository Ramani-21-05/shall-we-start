// src/pages/AuthPage.tsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { User, Key, Eye, EyeOff, ArrowRight, Lock } from 'lucide-react'
import { getErrorMessage } from '@/utils/errorUtils'

export function AuthPage() {
  const { login } = useAuth()
  const navigate = useNavigate()

  const [showPassword, setShowPassword] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMsg('')
    setIsSubmitting(true)
    try {
      await login(identifier, password)
      navigate('/dashboard')
    } catch (err: any) {
      setErrorMsg(getErrorMessage(err, 'Invalid username/email or password.'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen w-full bg-slate-950 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background glow effects */}
      <div className="absolute top-1/4 left-1/3 w-96 h-96 bg-indigo-600/15 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/3 w-96 h-96 bg-cyan-600/15 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md glass-card p-8 border border-indigo-500/20 shadow-2xl relative z-10 space-y-6 animate-fade-in-up">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-indigo-500 to-cyan-400 flex items-center justify-center shadow-lg mx-auto">
            <span className="text-white font-black text-xl">Rx</span>
          </div>
          <h1 className="text-2xl font-bold gradient-text">PharmaCast Portal</h1>
          <p className="text-slate-400 text-xs">Enterprise Secure Authentication &amp; RBAC</p>
        </div>

        <div className="flex items-center justify-center gap-2 py-1.5 px-3 bg-indigo-500/10 border border-indigo-500/20 rounded-lg text-indigo-300 text-xs">
          <Lock size={14} className="text-indigo-400" />
          <span>Admin-Provisioned Account Access Only</span>
        </div>

        {errorMsg && (
          <div className="glass-card-sm p-3 border-l-2 border-red-400 text-red-300 text-xs bg-red-950/20">
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
              Username or Email ID
            </label>
            <div className="relative">
              <User size={16} className="absolute left-3 top-3 text-slate-500" />
              <input
                type="text"
                required
                value={identifier}
                onChange={e => setIdentifier(e.target.value)}
                placeholder="ranjeet or 727823tuad122@skct.edu.in"
                className="w-full bg-white border border-white/10 rounded-lg pl-9 pr-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <div>
            <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
              Password
            </label>
            <div className="relative">
              <Key size={16} className="absolute left-3 top-3 text-slate-500" />
              <input
                type={showPassword ? 'text' : 'password'}
                required
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-white border border-white/10 rounded-lg pl-9 pr-9 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-3 text-slate-500 hover:text-slate-300"
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 font-semibold text-xs text-white rounded-lg transition-all shadow-md flex items-center justify-center gap-2 cursor-pointer"
          >
            {isSubmitting ? 'Authenticating…' : 'Sign In to Dashboard'}
            <ArrowRight size={14} />
          </button>
        </form>
      </div>
    </div>
  )
}
