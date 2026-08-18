"""
backfill_2020_actuals_to_forecast_results.py
─────────────────────────────────────────────
Reads the 2020 synthetic hourly sales from the Supabase `sales_hourly`
table, aggregates to daily totals per drug, then updates `actual_sales`
in `forecast_results` for 2020 dates.

This makes the Retrain Eligibility endpoint detect 12 months of real
(synthetic) actuals → unlocks the ⚡ Retrain & Extend button.

Usage:
    cd backend
    python backfill_2020_actuals_to_forecast_results.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from collections import defaultdict
from core.database import get_supabase

DRUGS = ['M01AB', 'M01AE', 'N02BA', 'N02BE', 'N05B', 'N05C', 'R03', 'R06']


def fetch_2020_hourly_from_supabase():
    """Fetch all 2020 rows from sales_hourly (8,784 rows)."""
    print("Fetching 2020 hourly rows from Supabase sales_hourly...")
    supabase = get_supabase()
    all_rows = []
    page_size = 1000
    offset = 0

    while True:
        res = supabase.table("sales_hourly") \
            .select("datum," + ",".join(DRUGS)) \
            .gte("datum", "2020-01-01") \
            .lte("datum", "2020-12-31T23:59:59Z") \
            .range(offset, offset + page_size - 1) \
            .execute()
        batch = res.data or []
        all_rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    print(f"  Fetched {len(all_rows):,} hourly rows")
    return all_rows


def aggregate_to_daily(rows: list) -> dict:
    """
    Aggregate hourly → daily totals per drug.
    Returns: {drug: {date_str: daily_total}}
    """
    print("Aggregating hourly → daily totals...")
    # drug -> date -> total
    daily = {drug: defaultdict(float) for drug in DRUGS}

    for row in rows:
        datum = str(row.get("datum", ""))
        date_key = datum[:10]   # "2020-01-01"
        for drug in DRUGS:
            val = row.get(drug, 0.0) or 0.0
            daily[drug][date_key] += val

    # Round to 4 decimal places
    for drug in DRUGS:
        daily[drug] = {k: round(v, 4) for k, v in daily[drug].items()}

    # Quick sanity
    sample_drug = 'M01AB'
    sample_dates = sorted(daily[sample_drug].keys())[:5]
    print(f"\n  Sample daily totals (M01AB):")
    for d in sample_dates:
        print(f"    {d}: {daily[sample_drug][d]:.4f}")

    return daily


def update_forecast_results(daily: dict):
    """
    UPDATE actual_sales on existing forecast_results rows for 2020.
    Uses per-drug batched updates instead of upsert (which would try to
    INSERT and violate NOT NULL constraints on p10/p50/p90 columns).
    """
    print("\nUpdating forecast_results.actual_sales for 2020...")
    supabase = get_supabase()

    total_updates = 0
    for drug in DRUGS:
        updated = 0
        for date_str, total_sales in daily[drug].items():
            try:
                supabase.table("forecast_results") \
                    .update({"actual_sales": total_sales}) \
                    .eq("forecast_date", date_str) \
                    .eq("drug_code", drug) \
                    .execute()
                updated += 1
            except Exception as e:
                print(f"  [ERROR] {drug} {date_str}: {e}")

        total_updates += updated
        print(f"  [{drug}] Updated {updated} rows")

    print(f"\n  Total rows updated: {total_updates:,}")


def verify_retrain_eligibility():
    """
    Simulate what the retrain eligibility endpoint checks:
    3+ months of 2020 actual_sales IS NOT NULL in forecast_results.
    """
    print("\nVerifying retrain eligibility for each drug...")
    supabase = get_supabase()

    for drug in DRUGS:
        res = supabase.table("forecast_results") \
            .select("forecast_date") \
            .eq("drug_code", drug) \
            .gt("forecast_date", "2019-12-31") \
            .not_.is_("actual_sales", "null") \
            .execute()

        rows = res.data or []
        months = set()
        for row in rows:
            fd = str(row.get("forecast_date", ""))
            if len(fd) >= 7:
                months.add(fd[:7])

        eligible = len(months) >= 3
        status = "ELIGIBLE" if eligible else "NOT YET"
        print(f"  [{drug}] {len(months)} months with actuals → {status} {'✅' if eligible else '❌'}")


if __name__ == "__main__":
    print("=" * 60)
    print("  Backfill 2020 Actuals → forecast_results")
    print("=" * 60)

    rows = fetch_2020_hourly_from_supabase()
    daily = aggregate_to_daily(rows)
    update_forecast_results(daily)
    verify_retrain_eligibility()

    print("\nDone! The ⚡ Retrain & Extend button should now be active")
    print("for all drugs when viewing the 2020 Forecast tab.")
