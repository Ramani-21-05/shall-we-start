"""
create_baseline_tables.py
──────────────────────────
Creates the two new Supabase tables needed for the Baseline Stock Alert system:
  1. stock_baselines  — one row per drug: baseline stock + alert threshold %
  2. stock_alerts     — one row per alert event (drug × date)

Run once:
    cd backend
    python create_baseline_tables.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from core.database import get_supabase

DRUGS = ['M01AB', 'M01AE', 'N02BA', 'N02BE', 'N05B', 'N05C', 'R03', 'R06']


def seed_default_baselines(supabase):
    """
    Seed an initial baseline for each drug based on the max TSL from 2020 inventory.
    Users can override these from the UI.
    """
    print("  Fetching TSL values from inventory_recommendations to seed baselines...")
    for drug in DRUGS:
        res = supabase.table("inventory_recommendations") \
            .select("target_stock_lvl") \
            .eq("drug_code", drug) \
            .gte("recommendation_date", "2020-01-01") \
            .lte("recommendation_date", "2020-12-31") \
            .execute()

        rows = res.data or []
        tsl_vals = [float(r.get("target_stock_lvl", 0)) for r in rows if r.get("target_stock_lvl")]

        if tsl_vals:
            tsl_vals.sort()
            # Use 90th percentile of TSL as initial baseline (conservative but realistic)
            idx = int(len(tsl_vals) * 0.90)
            suggested = round(tsl_vals[idx], 1)
        else:
            suggested = 50.0  # safe fallback

        record = {
            "drug_code":      drug,
            "baseline_stock": suggested,
            "threshold_pct":  70.0,  # alert at 70% of baseline
        }
        supabase.table("stock_baselines").upsert(record, on_conflict="drug_code").execute()
        print(f"    [{drug}] baseline_stock = {suggested}  threshold = 70%")


def main():
    print("=" * 60)
    print("  Creating Baseline Stock Alert Tables in Supabase")
    print("=" * 60)

    supabase = get_supabase()

    # ── stock_baselines ───────────────────────────────────────────
    print("\n[1] Checking stock_baselines table...")
    try:
        res = supabase.table("stock_baselines").select("drug_code").limit(1).execute()
        print("  Table exists. Skipping creation.")
    except Exception:
        print("  Table not found — please create it in Supabase SQL editor:")
        print("""
  CREATE TABLE IF NOT EXISTS stock_baselines (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    drug_code      TEXT NOT NULL UNIQUE,
    baseline_stock FLOAT NOT NULL,
    threshold_pct  FLOAT NOT NULL DEFAULT 70.0,
    updated_at     TIMESTAMPTZ DEFAULT NOW(),
    created_at     TIMESTAMPTZ DEFAULT NOW()
  );
        """)

    # ── stock_alerts ──────────────────────────────────────────────
    print("[2] Checking stock_alerts table...")
    try:
        res = supabase.table("stock_alerts").select("id").limit(1).execute()
        print("  Table exists. Skipping creation.")
    except Exception:
        print("  Table not found — please create it in Supabase SQL editor:")
        print("""
  CREATE TABLE IF NOT EXISTS stock_alerts (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    drug_code            TEXT NOT NULL,
    alert_date           DATE NOT NULL,
    simulated_inventory  FLOAT NOT NULL,
    baseline_stock       FLOAT NOT NULL,
    threshold_pct        FLOAT NOT NULL,
    stock_pct            FLOAT NOT NULL,
    is_read              BOOLEAN NOT NULL DEFAULT FALSE,
    created_at           TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (drug_code, alert_date)
  );
        """)

    # Seed default baselines from TSL
    print("\n[3] Seeding default baselines from 2020 TSL data...")
    try:
        seed_default_baselines(supabase)
        print("  Baselines seeded.")
    except Exception as e:
        print(f"  Seed error: {e}")

    # Run first alert check
    print("\n[4] Running initial alert check for all drugs (2020)...")
    try:
        import requests
        resp = requests.post("http://localhost:8000/api/alerts/check?year=2020")
        data = resp.json()
        print(f"  Alerts created: {data.get('created', 0)}")
        print(f"  Alerts skipped: {data.get('skipped', 0)}")
    except Exception as e:
        print(f"  Alert check via HTTP failed: {e}")
        print("  Run manually: POST http://localhost:8000/api/alerts/check")

    print("\nDone! Tables ready. Start the backend and visit /docs to explore the API.")


if __name__ == "__main__":
    main()
