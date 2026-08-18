// src/api/inventory.ts
import api from './client'
import type { InventoryRecommendation } from '@/types'

export const fetchInventoryRecommendations = async (drug: string, year?: string): Promise<InventoryRecommendation[]> => {
  const params = year ? { year } : {}
  const res = await api.get(`/inventory/${drug}/recommendations`, { params })
  return res.data.data
}

export const fetchInventoryEvaluation = async (drug: string) => {
  const res = await api.get(`/inventory/${drug}/evaluation`)
  return res.data.data
}
