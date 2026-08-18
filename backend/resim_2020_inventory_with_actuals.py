"""
resim_2020_inventory_with_actuals.py
──────────────────────────────────────
Re-runs the 3-day sequential inventory simulation for 2020 using:
  - Jan-Mar: actual_sales from forecast_results (real synthetic data)
  - Apr-Dec: P50 forecast demand as fallback (no actuals yet)

Then updates inventory_recommendations in Supabase with:
  - recalculated simulated_inventory (purple line)
  - recalculated stockout_risk / overstock_risk / recommended_order_qty
  - actual_sales populated for Jan-Mar rows

Usage:
    cd backend
    python resim_2020_inventory_with_actuals.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import pandas as pd
from core.database import get_supabase

DRUGS = ['M01AB', 'M01AE', 'N02BA', 'N02BE', 'N05B', 'N05C', 'R03', 'R06']
LEAD_TIME_DAYS = 3


def fetch_2020_inventory_rows(drug: str) -> list:
    """Fetch the existing 2020 inventory_recommendations rows (has p50/p90/rop/tsl)."""
    supabase = get_supabase()
    res = supabase.table("inventory_recommendations") \
        .select("*") \
        .eq("drug_code", drug) \
        .gte("recommendation_date", "2020-01-01") \
        .lte("recommendation_date", "2020-12-31") \
        .order("recommendation_date") \
        .execute()
    return res.data or []


def fetch_jan_mar_actuals(drug: str) -> dict:
    """Fetch Jan-Mar 2020 actual_sales from forecast_results. Returns {date_str: sales}."""
    supabase = get_supabase()
    res = supabase.table("forecast_results") \
        .select("forecast_date,actual_sales") \
        .eq("drug_code", drug) \
        .gte("forecast_date", "2020-01-01") \
        .lte("forecast_date", "2020-03-31") \
        .not_.is_("actual_sales", "null") \
        .execute()
    return {str(r["forecast_date"])[:10]: float(r["actual_sales"]) for r in (res.data or [])}


def resimulate(rows: list, actuals: dict) -> list:
    """
    Re-run the 3-day sequential carryover inventory engine.
    Uses actual_sales for Jan-Mar, P50 for Apr-Dec.
    Returns list of updated dicts.
    """
    n_days = len(rows)
    if n_days == 0:
        return []

    p50     = np.array([float(r.get("p50_demand", 0)) for r in rows])
    p90     = np.array([float(r.get("p90_demand", 0)) for r in rows])
    rop     = np.array([float(r.get("reorder_point", 0)) for r in rows])
    tsl     = np.array([float(r.get("target_stock_lvl", 0)) for r in rows])
    dates   = [str(r["recommendation_date"])[:10] for r in rows]

    # Build actual_sales array: use real actuals where available, else NaN
    actual_arr = np.array([
        actuals.get(d, np.nan) for d in dates
    ])

    # ── Simulation (same logic as inventory_engine.py) ──────────────────────
    stock_on_hand      = np.zeros(n_days)
    pending_orders     = np.zeros(n_days + LEAD_TIME_DAYS + 10)
    recommended_orders = np.zeros(n_days)
    stockout_risks     = np.zeros(n_days, dtype=int)
    overstock_risks    = np.zeros(n_days, dtype=int)
    recommendations    = []

    current_stock = tsl[0]   # Day 1 starts at Target Stock Level

    for t in range(n_days):
        current_stock += pending_orders[t]
        stock_on_hand[t] = round(current_stock, 2)

        rop_t = rop[t]
        tsl_t = tsl[t]

        stockout_risks[t] = 1 if current_stock < rop_t else 0
        overstock_risks[t] = 1 if current_stock > tsl_t else 0

        rop_next1 = rop[t+1] if (t+1) < n_days else rop_t
        rop_next2 = rop[t+2] if (t+2) < n_days else rop_t
        remainder_2 = (current_stock - rop_next1) - rop_next2

        reactive_trigger  = current_stock < rop_t
        proactive_trigger = remainder_2 < 0
        pipeline          = np.sum(pending_orders[t+1 : t+1+LEAD_TIME_DAYS])
        effective_inv     = current_stock + pipeline

        order_qty = 0.0
        if reactive_trigger or proactive_trigger:
            if effective_inv < tsl_t:
                order_qty = max(0, np.ceil(tsl_t - effective_inv))
                pending_orders[t + LEAD_TIME_DAYS] += order_qty
                rec = "INCREASE REPLENISHMENT"
            else:
                rec = "MAINTAIN REPLENISHMENT"
        elif current_stock > tsl_t:
            rec = "REDUCE REPLENISHMENT"
        else:
            rec = "MAINTAIN REPLENISHMENT"

        recommended_orders[t] = order_qty
        recommendations.append(rec)

        # Deduct today's sales: actual if available, else P50 forecast
        sold = actual_arr[t] if not np.isnan(actual_arr[t]) else p50[t]
        current_stock = max(0, current_stock - sold)

    # ── Build updated records ────────────────────────────────────────────────
    updated = []
    for t, row in enumerate(rows):
        date = dates[t]
        has_actual = not np.isnan(actual_arr[t])
        updated.append({
            "recommendation_date":        date,
            "drug_code":                  row["drug_code"],
            "actual_sales":               float(actual_arr[t]) if has_actual else None,
            "simulated_inventory":        float(stock_on_hand[t]),
            "stockout_risk":              bool(stockout_risks[t]),
            "overstock_risk":             bool(overstock_risks[t]),
            "recommended_order_qty":      float(recommended_orders[t]),
            "replenishment_recommendation": recommendations[t],
        })
    return updated


def push_updates(updates: list, drug: str):
    """Update inventory_recommendations rows in Supabase."""
    supabase = get_supabase()
    for rec in updates:
        try:
            supabase.table("inventory_recommendations") \
                .update({
                    "actual_sales":               rec["actual_sales"],
                    "simulated_inventory":        rec["simulated_inventory"],
                    "stockout_risk":              rec["stockout_risk"],
                    "overstock_risk":             rec["overstock_risk"],
                    "recommended_order_qty":      rec["recommended_order_qty"],
                    "replenishment_recommendation": rec["replenishment_recommendation"],
                }) \
                .eq("recommendation_date", rec["recommendation_date"]) \
                .eq("drug_code", drug) \
                .execute()
        except Exception as e:
            print(f"  [ERROR] {drug} {rec['recommendation_date']}: {e}")


def main():
    print("=" * 60)
    print("  Re-Simulate 2020 Inventory with Jan-Mar Actuals")
    print("=" * 60)

    for drug in DRUGS:
        print(f"\n[{drug}]")

        rows = fetch_2020_inventory_rows(drug)
        if not rows:
            print(f"  No 2020 rows found in inventory_recommendations — skipping")
            continue
        print(f"  Fetched {len(rows)} rows from inventory_recommendations")

        actuals = fetch_jan_mar_actuals(drug)
        print(f"  Fetched {len(actuals)} Jan-Mar actual_sales from forecast_results")

        updates = resimulate(rows, actuals)

        # Stats
        actual_count  = sum(1 for u in updates if u["actual_sales"] is not None)
        stockout_days = sum(1 for u in updates if u["stockout_risk"])
        overstock_days = sum(1 for u in updates if u["overstock_risk"])
        inv_values    = [u["simulated_inventory"] for u in updates]
        print(f"  Days using real actuals : {actual_count} (Jan-Mar)")
        print(f"  Days using P50 fallback : {len(updates) - actual_count} (Apr-Dec)")
        print(f"  Stockout risk days      : {stockout_days}")
        print(f"  Overstock risk days     : {overstock_days}")
        print(f"  Inventory range         : {min(inv_values):.1f} — {max(inv_values):.1f}")

        print(f"  Pushing {len(updates)} updates to Supabase...")
        push_updates(updates, drug)
        print(f"  Done.")

    print("\n" + "=" * 60)
    print("  All drugs re-simulated with actual Jan-Mar 2020 sales.")
    print("  Inventory chart purple line now uses real consumption data.")
    print("=" * 60)


if __name__ == "__main__":
    main()
