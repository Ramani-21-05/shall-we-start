// src/api/dashboard.ts
import api from './client'
import type { DashboardSummary, Product } from '@/types'

export interface PeakHourInfo {
  hour: number
  label: string
  formatted: string
  avg_sales: number
  total_sales: number
}

export interface PeakWeekdayInfo {
  weekday: string
  avg_sales: number
  total_sales: number
}

export interface PeakMonthInfo {
  month: number
  month_name: string
  avg_sales: number
  total_sales: number
}

export interface DrugShareInfo {
  drug_code: string
  drug_name: string
  total_sales: number
  percentage_share: number
  avg_monthly_sales: number
}

export interface SalesAnalyticsSummary {
  selected_drug: string
  selected_year: string
  total_sales: number
  avg_daily_sales: number
  total_records: number
  peak_hour: PeakHourInfo
  peak_weekday: PeakWeekdayInfo
  peak_month: PeakMonthInfo
  top_drug: DrugShareInfo | null
  lowest_drug: DrugShareInfo | null
}

export interface MonthlyTrendPoint {
  label: string
  year: number
  month: number
  month_name: string
  total_sales: number
  [drug_code: string]: number | string
}

export interface SeasonalityPoint {
  month: number
  month_name: string
  avg_sales: number
  total_sales: number
  index: number
}

export interface HourlyPoint {
  hour: number
  label: string
  avg_sales: number
  total_sales: number
}

export interface WeekdayPoint {
  weekday: string
  short_name: string
  avg_sales: number
  total_sales: number
}

export interface YoYSeriesPoint {
  year: number
  total_sales: number
  growth_pct: number | null
}

export interface SalesAnalyticsData {
  summary: SalesAnalyticsSummary
  combined_trend: MonthlyTrendPoint[]
  seasonality: SeasonalityPoint[]
  hourly_pattern: HourlyPoint[]
  weekday_pattern: WeekdayPoint[]
  yoy_series: YoYSeriesPoint[]
  drug_shares: DrugShareInfo[]
}

export const fetchDashboardSummary = async (): Promise<DashboardSummary> => {
  const res = await api.get('/dashboard/summary')
  return res.data
}

export const fetchSalesAnalytics = async (
  drugCode: string = 'ALL',
  year: string = 'ALL'
): Promise<SalesAnalyticsData> => {
  const res = await api.get('/dashboard/sales-analytics', {
    params: { drug_code: drugCode, year },
  })
  return res.data
}

export const fetchProducts = async (): Promise<Product[]> => {
  const res = await api.get('/products')
  return res.data.data
}

