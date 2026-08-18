// src/types/index.ts
export interface Product {
  drug_code: string
  drug_name: string
  champion_model_name: string
  algorithm_family: string
  training_cutoff_date: string
  anomaly_detection_year: number
}

export interface ChampionSummary {
  drug_code: string
  drug_name: string
  champion_model: string
  test_rmsle: number
  test_rmse?: number
  test_mae: number
  test_mape?: number
  test_wape?: number
}

export interface DashboardSummary {
  portfolio_avg_rmsle: number
  portfolio_avg_rmse?: number
  portfolio_avg_mape?: number
  portfolio_avg_wape?: number
  total_drugs: number
  champions: ChampionSummary[]
  inventory: {
    avg_service_level_pct: number
    avg_demand_coverage_pct: number
    avg_stockout_risk_pct: number
    avg_overstock_risk_pct: number
  }
  training_cutoff: string
  anomaly_detection_year: number
}

export interface ModelRanking {
  drug_code: string
  drug_name: string
  model_key: string
  model_name: string
  rmsle: number
  rmse?: number
  mae: number
  mape?: number
  wape?: number
  n_days: number
  is_champion: boolean
  rank?: number
  model_status?: string
  last_retrained?: string
  training_cutoff_date?: string
}

export interface ForecastPoint {
  date: string
  drug_code: string
  actual_sales: number | null
  p10_demand: number | null
  p50_demand: number | null
  p90_demand: number | null
}

export interface ShapWeight {
  drug_code: string
  feature: string
  mean_abs_shap: number
  lgb_gain: number | null
  feature_domain: string
  feature_rank: number
}

export interface AnomalyResult {
  drug_code: string
  anomaly_date: string
  actual_demand: number
  expected_demand: number
  residual: number
  anomaly_score: number
  anomaly_type: string
  severity: 'HIGH' | 'MEDIUM' | 'LOW'
  is_anomaly: boolean
  detection_stage: string
}

export interface InventoryRecommendation {
  drug_code: string
  recommendation_date: string
  actual_sales: number | null
  p50_demand: number
  p90_demand: number
  reorder_point: number
  target_stock_level: number
  simulated_inventory: number
  recommended_order_qty: number
  replenishment_recommendation: string
  stockout_risk: boolean
  overstock_risk: boolean
}

export const DRUGS = ['M01AB', 'M01AE', 'N02BA', 'N02BE', 'N05B', 'N05C', 'R03', 'R06'] as const
export type DrugCode = typeof DRUGS[number]
