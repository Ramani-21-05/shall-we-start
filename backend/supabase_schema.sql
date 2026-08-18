-- ============================================================
-- PharmaCast Supabase Schema
-- ============================================================

-- 0. Table for Raw Hourly Pharmaceutical Sales (50,532 records: 2014 - 2019)
CREATE TABLE IF NOT EXISTS sales_hourly (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  "datum" TIMESTAMPTZ NOT NULL UNIQUE,
  "M01AB" FLOAT NOT NULL DEFAULT 0.0,
  "M01AE" FLOAT NOT NULL DEFAULT 0.0,
  "N02BA" FLOAT NOT NULL DEFAULT 0.0,
  "N02BE" FLOAT NOT NULL DEFAULT 0.0,
  "N05B" FLOAT NOT NULL DEFAULT 0.0,
  "N05C" FLOAT NOT NULL DEFAULT 0.0,
  "R03" FLOAT NOT NULL DEFAULT 0.0,
  "R06" FLOAT NOT NULL DEFAULT 0.0,
  "Year" INTEGER NOT NULL,
  "Month" INTEGER NOT NULL,
  "Hour" INTEGER NOT NULL,
  "Weekday Name" TEXT NOT NULL,
  is_trained BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sales_hourly_datum ON sales_hourly(datum);

ALTER TABLE sales_hourly ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public read sales_hourly" ON sales_hourly FOR SELECT USING (true);
CREATE POLICY "Allow public insert sales_hourly" ON sales_hourly FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public update sales_hourly" ON sales_hourly FOR UPDATE USING (true) WITH CHECK (true);


-- 1. Forecast Results Table (P10 / P50 / P90 Demand Range Forecasts for all 8 drugs)
CREATE TABLE IF NOT EXISTS forecast_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  forecast_date DATE NOT NULL,
  drug_code TEXT NOT NULL,          -- 'M01AB', 'M01AE', 'N02BA', 'N02BE', 'N05B', 'N05C', 'R03', 'R06'
  actual_sales FLOAT,
  p10_demand FLOAT NOT NULL,        -- Lean Lower Bound (P10)
  p50_demand FLOAT NOT NULL,        -- Expected Demand Anchor (P50)
  p90_demand FLOAT NOT NULL,        -- Upper Target Stock (P90)
  uncertainty_band FLOAT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (forecast_date, drug_code)
);

CREATE INDEX IF NOT EXISTS idx_forecast_date_drug ON forecast_results(forecast_date, drug_code);

ALTER TABLE forecast_results ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public read forecast_results" ON forecast_results FOR SELECT USING (true);


-- 2. Inventory Recommendations Table (Demand-Aware Replenishment Directives)
CREATE TABLE IF NOT EXISTS inventory_recommendations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  recommendation_date DATE NOT NULL,
  drug_code TEXT NOT NULL,
  actual_sales FLOAT,
  p10_demand FLOAT NOT NULL,
  p50_demand FLOAT NOT NULL,
  p90_demand FLOAT NOT NULL,
  safety_stock FLOAT NOT NULL,
  reorder_point FLOAT NOT NULL,
  target_stock_lvl FLOAT NOT NULL,
  simulated_inventory FLOAT NOT NULL,
  stockout_risk BOOLEAN NOT NULL DEFAULT FALSE,
  overstock_risk BOOLEAN NOT NULL DEFAULT FALSE,
  replenishment_recommendation TEXT NOT NULL, -- 'INCREASE REPLENISHMENT', 'MAINTAIN REPLENISHMENT', 'REDUCE REPLENISHMENT'
  recommended_order_qty FLOAT NOT NULL DEFAULT 0.0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (recommendation_date, drug_code)
);

CREATE INDEX IF NOT EXISTS idx_inventory_date_drug ON inventory_recommendations(recommendation_date, drug_code);

ALTER TABLE inventory_recommendations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public read inventory_recommendations" ON inventory_recommendations FOR SELECT USING (true);


