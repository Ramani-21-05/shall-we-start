// src/api/inventoryV2.ts
import { getErrorMessage } from '@/utils/errorUtils'

const API_BASE = 'http://localhost:8000/api/v2/inventory'

export interface ForecastDetails {
  tomorrow: number
  next_7_days: number
  next_14_days: number
  p90_7_days: number
  p10_7_days: number
}

export interface BaselineRecommendation {
  current_baseline: number
  suggested_baseline: number
  reason: string
}

export interface DrugInventoryEvaluation {
  drug_code: string
  drug_name: string
  category: string
  current_stock: number
  baseline_stock: number
  safety_stock: number
  incoming_stock: number
  lead_time_days: number
  consumed_qty: number
  consumed_pct: number
  inventory_position: number
  forecast_demand: number
  forecast_details: ForecastDetails
  target_stock: number
  recommended_order_qty: number
  status: 'HEALTHY' | 'WATCH' | 'REPLENISHMENT_RECOMMENDED' | 'STOCKOUT_RISK' | 'EMERGENCY_REPLENISHMENT' | 'OUT_OF_STOCK'
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  reason: string
  baseline_recommendation?: BaselineRecommendation | null
}

export interface SundayReviewItem {
  drug_code: string
  drug_name: string
  baseline_stock: number
  current_stock: number
  incoming_stock: number
  consumed_pct: number
  forecast_risk: string
  status: string
  recommendation_action: string
  recommended_order_qty: number
  target_stock: number
}

export interface InventoryTransactionItem {
  id: string
  drug_code: string
  transaction_type: 'SALE' | 'RESTOCK' | 'RETURN' | 'DAMAGE' | 'EXPIRY' | 'ADJUSTMENT'
  quantity: number
  stock_before: number
  stock_after: number
  timestamp: string
  user_id: string
  notes: string
}

export interface BaselineHistoryItem {
  id: string
  drug_code: string
  old_baseline: number
  new_baseline: number
  source: string
  reason: string
  changed_by: string
  changed_at: string
  status: string
}

export async function fetchInventoryOverview(): Promise<DrugInventoryEvaluation[]> {
  const res = await fetch(`${API_BASE}/overview`)
  if (!res.ok) throw new Error('Failed to fetch inventory overview')
  const json = await res.json()
  return json.data || []
}

export async function fetchDrugInventory(drugCode: string): Promise<DrugInventoryEvaluation> {
  const res = await fetch(`${API_BASE}/${drugCode.toUpperCase()}`)
  if (!res.ok) throw new Error(`Failed to fetch inventory for ${drugCode}`)
  const json = await res.json()
  return json.data
}

export async function fetchInventoryAlerts(): Promise<DrugInventoryEvaluation[]> {
  const res = await fetch(`${API_BASE}/alerts`)
  if (!res.ok) throw new Error('Failed to fetch inventory alerts')
  const json = await res.json()
  return json.data || []
}

export async function fetchSundayReview(): Promise<SundayReviewItem[]> {
  const res = await fetch(`${API_BASE}/sunday-review`)
  if (!res.ok) throw new Error('Failed to fetch Sunday review')
  const json = await res.json()
  return json.data || []
}

export async function fetchTransactions(drugCode?: string): Promise<InventoryTransactionItem[]> {
  const url = drugCode ? `${API_BASE}/transactions?drug=${drugCode.toUpperCase()}` : `${API_BASE}/transactions`
  const res = await fetch(url)
  if (!res.ok) throw new Error('Failed to fetch transactions')
  const json = await res.json()
  return json.data || []
}

export async function fetchBaselineHistory(drugCode?: string): Promise<BaselineHistoryItem[]> {
  const url = drugCode ? `${API_BASE}/baseline-history?drug=${drugCode.toUpperCase()}` : `${API_BASE}/baseline-history`
  const res = await fetch(url)
  if (!res.ok) throw new Error('Failed to fetch baseline history')
  const json = await res.json()
  return json.data || []
}

export async function recordSale(drugCode: string, quantity: number, userId = 'pharmacist', notes = 'Direct POS sale') {
  const res = await fetch(`${API_BASE}/sale`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ drug_code: drugCode, quantity, user_id: userId, notes })
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(getErrorMessage(err, 'Failed to record sale'))
  }
  return res.json()
}

export async function recordTransaction(
  drugCode: string,
  transactionType: string,
  quantity: number,
  userId = 'pharmacist',
  notes = ''
) {
  const res = await fetch(`${API_BASE}/transaction`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ drug_code: drugCode, transaction_type: transactionType, quantity, user_id: userId, notes })
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(getErrorMessage(err, 'Failed to execute transaction'))
  }
  return res.json()
}

export async function updateBaselineStock(
  drugCode: string,
  newBaseline: number,
  source = 'MANUAL',
  reason = 'Pharmacist review',
  changedBy = 'pharmacist',
  status = 'ACCEPTED'
) {
  const res = await fetch(`${API_BASE}/baseline`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      drug_code: drugCode,
      new_baseline: newBaseline,
      source,
      reason,
      changed_by: changedBy,
      status
    })
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(getErrorMessage(err, 'Failed to update baseline'))
  }
  return res.json()
}

export async function approveReplenishmentOrder(
  drugCode: string,
  quantity: number,
  approvedBy = 'pharmacist',
  reason = 'Approved recommendation'
) {
  const res = await fetch(`${API_BASE}/order/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      drug_code: drugCode,
      quantity,
      approved_by: approvedBy,
      reason
    })
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(getErrorMessage(err, 'Failed to approve replenishment order'))
  }
  return res.json()
}

export async function resetInventory() {
  const res = await fetch(`${API_BASE}/reset`, { method: 'POST' })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(getErrorMessage(err, 'Failed to reset inventory'))
  }
  return res.json()
}
