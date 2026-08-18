// src/api/anomaly.ts
import api from './client'
import type { AnomalyResult } from '@/types'

export const fetchAnomalies = async (drug: string): Promise<AnomalyResult[]> => {
  const res = await api.get(`/anomaly/${drug}`)
  return res.data.data
}

export const fetchAnomalySummary = async () => {
  const res = await api.get('/anomaly/summary')
  return res.data.data
}
