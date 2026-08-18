-- ============================================================
-- Run this ONCE in your Supabase SQL Editor (Dashboard → SQL Editor)
-- This creates a PostgreSQL function that aggregates sales_hourly
-- data server-side, returning 72 rows (6 years × 12 months) in
-- a single RPC call instead of 51+ paginated HTTP requests.
-- ============================================================

CREATE OR REPLACE FUNCTION get_drug_monthly_totals(p_drug_code TEXT)
RETURNS TABLE(year INTEGER, month INTEGER, total_sales FLOAT)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  -- Use dynamic SQL so the drug column name is injected safely
  RETURN QUERY EXECUTE format(
    'SELECT "Year"::INTEGER,
            "Month"::INTEGER,
            ROUND(SUM(%I)::NUMERIC, 2)::FLOAT AS total_sales
     FROM sales_hourly
     WHERE "Year" BETWEEN 2014 AND 2019
     GROUP BY "Year", "Month"
     ORDER BY "Year", "Month"',
    p_drug_code   -- e.g. 'M01AB', 'N02BE', etc.
  );
END;
$$;

-- Grant public access so the API key can call it
GRANT EXECUTE ON FUNCTION get_drug_monthly_totals(TEXT) TO anon, authenticated;
