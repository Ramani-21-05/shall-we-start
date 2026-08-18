// src/api/baselines.ts
import api from './client'

export interface StockBaseline {
  id: string
  drug_code: string
  baseline_stock: number
  threshold_pct: number
  updated_at: string
}

export interface StockAlert {
  id: string
  drug_code: string
  alert_date: string
  simulated_inventory: number
  baseline_stock: number
  threshold_pct: number
  stock_pct: number
  is_read: boolean
  created_at: string
}

export interface BaselineSuggest {
  drug_code: string
  suggested: number
  smoothed: number
  existing: number | null
  method: string
}

// ── Baselines ────────────────────────────────────────────────────────────────

export const fetchBaselines = async (): Promise<StockBaseline[]> => {
  const res = await api.get('/baselines')
  return res.data
}

export const setBaseline = async (
  drug: string,
  baseline_stock: number,
  threshold_pct = 70
): Promise<void> => {
  await api.post(`/baselines/${drug}`, { baseline_stock, threshold_pct })
}

export const fetchBaselineSuggest = async (drug: string): Promise<BaselineSuggest> => {
  const res = await api.get(`/baselines/${drug}/suggest`)
  return res.data
}

// ── Alerts ───────────────────────────────────────────────────────────────────

export const fetchAlerts = async (drug?: string, unreadOnly = false): Promise<StockAlert[]> => {
  const params: Record<string, string> = {}
  if (drug) params.drug = drug
  if (unreadOnly) params.unread_only = 'true'
  const res = await api.get('/alerts', { params })
  return res.data
}

export const fetchUnreadCount = async (): Promise<number> => {
  const res = await api.get('/alerts/unread-count')
  return res.data.count ?? 0
}

export const checkAlerts = async (year = '2020'): Promise<{ created: number; skipped: number }> => {
  const res = await api.post(`/alerts/check?year=${year}`)
  return res.data
}

export const markAlertRead = async (alertId: string): Promise<void> => {
  await api.patch(`/alerts/${alertId}/read`)
}

export const markAllAlertsRead = async (): Promise<void> => {
  await api.patch('/alerts/read-all')
}
