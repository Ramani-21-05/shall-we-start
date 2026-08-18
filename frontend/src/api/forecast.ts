// src/api/forecast.ts
import api from './client'
import type { ForecastPoint } from '@/types'

export const fetchForecast = async (drug: string, year?: string): Promise<ForecastPoint[]> => {
  const params = year ? { year } : {}
  const res = await api.get(`/forecast/${drug}`, { params })
  return res.data.data
}

export const retrainModel = async (drug: string): Promise<{ status: string; message: string }> => {
  const res = await api.post(`/forecast/${drug}/retrain`)
  return res.data
}

export interface RetrainEligibility {
  eligible: boolean
  untrained_months: number
  months: string[]
  threshold: number
}

export const fetchRetrainEligibility = async (drug: string): Promise<RetrainEligibility> => {
  const res = await api.get(`/forecast/${drug}/retrain-eligibility`)
  return res.data
}
