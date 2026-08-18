// src/api/strategy.ts
import api from './client'

export interface MonthlyTimelineItem {
  month: number
  month_name: string
  seasonal_index: number
  forecast_units: number
  season_status: 'PEAK' | 'NORMAL' | 'OFF_PEAK'
  is_selected: boolean
}

export interface StrategyMetrics {
  total_historical_sales: number
  historical_30d_avg: number
  forecast_30d: number
  forecast_growth_pct: number
  seasonal_index: number
  peak_month: string
  stock_coverage_days: number
  current_stock: number
  variability_cv: number
}

export interface SalesStrategyData {
  opportunity_level: string
  action: string
  stock_focus: string
  replenishment_urgency: string
}

export interface MarketingStrategyData {
  focus: string
  timing_recommendation: string
  action: string
  intensity: string
}

export interface InventoryStrategyData {
  status: string
  recommendation: string
  color: 'emerald' | 'amber' | 'red'
  coverage_days: number
}

export interface AssociationRuleData {
  antecedent: string
  consequent: string
  antecedent_name: string
  consequent_name: string
  support_pct: number
  confidence_pct: number
  lift: number
  recommendation: string
}

export interface ProductStrategyItem {
  drug_code: string
  drug_name: string
  selected_month?: number
  selected_month_name?: string
  metrics: StrategyMetrics
  quadrant: 'PRIORITY' | 'EMERGING' | 'STABLE' | 'LOW_PRIORITY'
  quadrant_label: string
  quadrant_badge: string
  sales_strategy: SalesStrategyData
  marketing_strategy: MarketingStrategyData
  inventory_strategy: InventoryStrategyData
  rationale: string
  monthly_timeline?: MonthlyTimelineItem[]
  association_rules: AssociationRuleData[]
}

export interface StrategySummary {
  total_products: number
  selected_month?: number
  selected_month_name?: string
  quadrant_counts: Record<string, number>
  priority_products_count: number
  emerging_products_count: number
  cross_sell_rules_count: number
}

export interface StrategyOverviewData {
  summary: StrategySummary
  products: ProductStrategyItem[]
  association_rules: AssociationRuleData[]
  urgent_sales_actions: { drug_code: string; drug_name: string; action: string }[]
  campaign_timings: { drug_code: string; drug_name: string; timing: string; focus: string }[]
}

export const fetchStrategyOverview = async (month?: number): Promise<StrategyOverviewData> => {
  const url = month ? `/strategy/overview?month=${month}` : '/strategy/overview'
  const res = await api.get(url)
  return res.data
}

export const fetchProductStrategy = async (drugCode: string, month?: number): Promise<ProductStrategyItem> => {
  const url = month ? `/strategy/${drugCode}?month=${month}` : `/strategy/${drugCode}`
  const res = await api.get(url)
  return res.data
}
