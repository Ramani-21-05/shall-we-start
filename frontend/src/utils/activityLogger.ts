// src/utils/activityLogger.ts
// Thin client-side logger. Sends events to /api/logs/write (fire-and-forget).

import api from '@/api/client'

export type LogEventType =
  | 'LOGIN'
  | 'LOGOUT'
  | 'API_CALL'
  | 'API_ERROR'
  | 'PAGE_VIEW'
  | 'ADMIN_ACTION'
  | 'SIM_ACTION'
  | 'ERROR'
  | 'INFO'

export type LogStatus = 'SUCCESS' | 'ERROR' | 'WARNING' | 'INFO'

interface LogPayload {
  event_type: LogEventType
  message: string
  detail?: string
  username?: string
  user_role?: string
  status?: LogStatus
}

/**
 * Fire-and-forget log write to backend.
 * Never throws — logging must never break the UX.
 */
export function writeLog(payload: LogPayload): void {
  const stored = localStorage.getItem('pharmacast_user')
  let username = payload.username
  let user_role = payload.user_role

  if (!username && stored) {
    try {
      const u = JSON.parse(stored)
      username = u.username
      user_role = u.role
    } catch {
      // ignore
    }
  }

  api.post('/logs/write', {
    ...payload,
    username: username || 'anonymous',
    user_role: user_role || 'UNKNOWN',
    status: payload.status || 'INFO',
    user_agent: navigator.userAgent,
  }).catch(() => {
    // Silent fail — do not disrupt main UX
  })
}
