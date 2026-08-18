-- ============================================================
-- Forecast-Driven Pharmacy Demand and Inventory Management System
-- Hackathon Supabase Schema
-- ============================================================

-- 1. Drugs Table
CREATE TABLE IF NOT EXISTS drugs (
  drug_id TEXT PRIMARY KEY,       -- e.g. 'M01AB', 'M01AE', 'N02BA', 'N02BE', 'N05B', 'N05C', 'R03', 'R06'
  drug_code TEXT UNIQUE NOT NULL,
  drug_name TEXT NOT NULL,
  category TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Inventory Table (Simulated State)
CREATE TABLE IF NOT EXISTS inventory (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  drug_id TEXT REFERENCES drugs(drug_id) ON DELETE CASCADE UNIQUE NOT NULL,
  baseline_stock FLOAT NOT NULL DEFAULT 500,
  current_stock FLOAT NOT NULL DEFAULT 500,
  safety_stock FLOAT NOT NULL DEFAULT 75,
  lead_time_days INT NOT NULL DEFAULT 4,
  incoming_stock FLOAT NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Inventory Transactions Audit Trail
CREATE TABLE IF NOT EXISTS inventory_transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  drug_id TEXT REFERENCES drugs(drug_id) ON DELETE CASCADE NOT NULL,
  transaction_type TEXT NOT NULL, -- 'SALE', 'RESTOCK', 'RETURN', 'DAMAGE', 'EXPIRY', 'ADJUSTMENT'
  quantity FLOAT NOT NULL,
  stock_before FLOAT NOT NULL,
  stock_after FLOAT NOT NULL,
  simulation_date DATE NOT NULL,
  user_name TEXT DEFAULT 'System',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Forecasts Table (Next 7-day Demand Predictions)
CREATE TABLE IF NOT EXISTS forecasts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  drug_id TEXT REFERENCES drugs(drug_id) ON DELETE CASCADE NOT NULL,
  forecast_date DATE NOT NULL,
  forecast_quantity FLOAT NOT NULL, -- 7-day predicted demand
  lower_bound FLOAT DEFAULT 0,
  upper_bound FLOAT DEFAULT 0,
  model_version TEXT DEFAULT 'xgboost_v1',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(drug_id, forecast_date)
);

-- 5. Replenishment Orders Table
CREATE TABLE IF NOT EXISTS replenishment_orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  drug_id TEXT REFERENCES drugs(drug_id) ON DELETE CASCADE NOT NULL,
  quantity FLOAT NOT NULL,
  order_date DATE NOT NULL,
  expected_arrival DATE NOT NULL,
  status TEXT NOT NULL DEFAULT 'PENDING_APPROVAL', -- 'PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'EDITED', 'DELIVERED'
  approved_by TEXT DEFAULT 'Pharmacy Member',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Alerts Table
CREATE TABLE IF NOT EXISTS alerts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  drug_id TEXT REFERENCES drugs(drug_id) ON DELETE CASCADE NOT NULL,
  alert_type TEXT NOT NULL, -- 'WATCH', 'REPLENISHMENT_RECOMMENDED', 'STOCKOUT_RISK', 'EMERGENCY_REPLENISHMENT', 'OUT_OF_STOCK'
  severity TEXT NOT NULL,   -- 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
  message TEXT NOT NULL,
  alert_date DATE NOT NULL,
  status TEXT NOT NULL DEFAULT 'ACTIVE', -- 'ACTIVE', 'DISMISSED', 'RESOLVED'
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Baseline History Table
CREATE TABLE IF NOT EXISTS baseline_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  drug_id TEXT REFERENCES drugs(drug_id) ON DELETE CASCADE NOT NULL,
  old_baseline FLOAT NOT NULL,
  new_baseline FLOAT NOT NULL,
  reason TEXT NOT NULL,
  changed_by TEXT DEFAULT 'Pharmacy Member',
  changed_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. Simulation State Clock
CREATE TABLE IF NOT EXISTS simulation_state (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9. Anomaly Events Table (2019 Holdout Anomaly Detection)
CREATE TABLE IF NOT EXISTS anomaly_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  drug_id TEXT REFERENCES drugs(drug_id) ON DELETE CASCADE NOT NULL,
  anomaly_date DATE NOT NULL,
  actual_demand FLOAT NOT NULL,
  expected_demand FLOAT NOT NULL,
  residual FLOAT NOT NULL,
  anomaly_score FLOAT NOT NULL,
  anomaly_type TEXT NOT NULL,
  severity TEXT NOT NULL,
  is_anomaly BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(drug_id, anomaly_date)
);

-- 10. Monthly Simulation Records Table (Stored Monthly Batch Summary)
CREATE TABLE IF NOT EXISTS monthly_simulation_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  year INT NOT NULL,
  month INT NOT NULL,
  month_name TEXT NOT NULL,
  month_start_date DATE NOT NULL,
  month_end_date DATE NOT NULL,
  drug_id TEXT REFERENCES drugs(drug_id) ON DELETE CASCADE NOT NULL,
  starting_stock FLOAT NOT NULL,
  ending_stock FLOAT NOT NULL,
  total_monthly_sales FLOAT NOT NULL,
  baseline_stock FLOAT NOT NULL,
  safety_stock FLOAT NOT NULL,
  total_orders_placed INT DEFAULT 0,
  total_units_restocked FLOAT DEFAULT 0,
  stockout_risk_events INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(year, month, drug_id)
);

-- RLS Policies
ALTER TABLE drugs ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE forecasts ENABLE ROW LEVEL SECURITY;
ALTER TABLE replenishment_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE baseline_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE simulation_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE anomaly_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE monthly_simulation_records ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read drugs" ON drugs FOR SELECT USING (true);
CREATE POLICY "Public read/write inventory" ON inventory FOR ALL USING (true);
CREATE POLICY "Public read/write inventory_transactions" ON inventory_transactions FOR ALL USING (true);
CREATE POLICY "Public read/write forecasts" ON forecasts FOR ALL USING (true);
CREATE POLICY "Public read/write replenishment_orders" ON replenishment_orders FOR ALL USING (true);
CREATE POLICY "Public read/write alerts" ON alerts FOR ALL USING (true);
CREATE POLICY "Public read/write baseline_history" ON baseline_history FOR ALL USING (true);
CREATE POLICY "Public read/write simulation_state" ON simulation_state FOR ALL USING (true);
CREATE POLICY "Public read/write anomaly_events" ON anomaly_events FOR ALL USING (true);
CREATE POLICY "Public read/write monthly_simulation_records" ON monthly_simulation_records FOR ALL USING (true);
