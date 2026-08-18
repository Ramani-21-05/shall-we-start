// src/api/explain.ts
import api from './client'
import type { ShapWeight } from '@/types'

export interface DomainBreakdownItem {
  domain: string
  total_shap: number
  percentage: number
}

export interface DrugNarrative {
  primary_driver: string
  summary: string
  key_insight: string
}

export interface ExplainabilitySummary {
  drug_code: string
  narrative: DrugNarrative
  domain_breakdown: DomainBreakdownItem[]
  top_features: ShapWeight[]
}

export const fetchShapWeights = async (drug: string, topN = 10): Promise<ShapWeight[]> => {
  const res = await api.get(`/explain/${drug}/weights`, { params: { top_n: topN } })
  return res.data.data
}

export const fetchExplainabilitySummary = async (drug: string): Promise<ExplainabilitySummary> => {
  const res = await api.get(`/explain/${drug}/summary`)
  return res.data.data
}

export const fetchShapBreakdown = async (drug: string) => {
  const res = await api.get(`/explain/${drug}/breakdown`)
  return res.data.data
}

