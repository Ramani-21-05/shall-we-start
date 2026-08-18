// src/api/history.ts
import api from './client'

export interface MonthlyPoint {
  label: string
  year: number
  month: number
  total_sales: number
  month_name: string
}

export interface YoYPoint {
  year: number
  total_sales: number
  growth_pct: number | null
}

export interface SeasonPoint {
  month: number
  month_name: string
  avg_sales: number
  index: number
}

export interface YoYMonthlyPoint {
  month: number
  month_name: string
  [year: string]: number | string
}

export interface HistorySummary {
  drug_code: string
  drug_name: string
  years_covered: number[]
  total_records: number
  overall_total: number
  overall_avg_monthly: number
  overall_max_monthly: number
  overall_min_monthly: number
  peak_month: string
  annual_totals: Record<string, number>
}

export interface HistoricalAnalytics {
  summary: HistorySummary
  monthly_series: MonthlyPoint[]
  yoy_series: YoYPoint[]
  seasonality: SeasonPoint[]
  yoy_monthly: YoYMonthlyPoint[]
}

export interface DrugShareItem {
  drug_code: string
  drug_name: string
  total_sales: number
  avg_monthly_sales: number
  percentage_share: number
}

export interface PortfolioSummary {
  portfolio_total_sales: number
  portfolio_avg_monthly_sales: number
  total_drugs: number
  highest_sales_drug: DrugShareItem | null
  lowest_sales_drug: DrugShareItem | null
}

export interface PortfolioOverview {
  summary: PortfolioSummary
  monthly_series: MonthlyPoint[]
  seasonality: SeasonPoint[]
  drug_shares: DrugShareItem[]
}

export const fetchHistoricalAnalytics = async (drug: string): Promise<HistoricalAnalytics> => {
  const res = await api.get(`/history/${drug}`)
  return res.data
}

export const fetchPortfolioOverview = async (): Promise<PortfolioOverview> => {
  const res = await api.get('/history/portfolio-overview')
  return res.data
}

export const fetchAllDrugsSummary = async () => {
  const res = await api.get('/history/')
  return res.data
}

