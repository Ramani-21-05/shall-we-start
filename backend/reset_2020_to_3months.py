"""
reset_2020_to_3months.py
─────────────────────────
1. Deletes ALL 2020 rows from sales_hourly
2. Inserts only Jan-Feb-Mar 2020 synthetic hourly data (3 months = 2,184 rows)
   with is_trained=False

Usage:
    cd backend
    python reset_2020_to_3months.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import pandas as pd
from datetime import timezone

from core.database import get_supabase

DRUGS = ['M01AB', 'M01AE', 'N02BA', 'N02BE', 'N05B', 'N05C', 'R03', 'R06']

DRUG_STATS = {
    'M01AB': {'mean': 0.2098, 'std': 0.5560, 'max': 7.0},
    'M01AE': {'mean': 0.1624, 'std': 0.4161, 'max': 6.0},
    'N02BA': {'mean': 0.1617, 'std': 0.4532, 'max': 6.5},
    'N02BE': {'mean': 1.2468, 'std': 2.3874, 'max': 29.0},
    'N05B':  {'mean': 0.3690, 'std': 0.9309, 'max': 15.0},
    'N05C':  {'mean': 0.0247, 'std': 0.2179, 'max': 6.0},
    'R03':   {'mean': 0.2297, 'std': 1.2405, 'max': 25.0},
    'R06':   {'mean': 0.1209, 'std': 0.3920, 'max': 5.0},
}

HOUR_MULTIPLIERS = {
    0: 0.00, 1: 0.00, 2: 0.00, 3: 0.00, 4: 0.00, 5: 0.00,
    6: 0.00, 7: 0.06,
    8: 1.27, 9: 1.68, 10: 1.96, 11: 2.19,
    12: 2.13, 13: 1.81, 14: 1.94, 15: 1.48,
    16: 1.31, 17: 1.40, 18: 1.67, 19: 2.01,
    20: 1.84, 21: 1.22,
    22: 0.02, 23: 0.00,
}

WEEKDAY_MULTIPLIERS = {
    'Monday': 1.00, 'Tuesday': 1.00, 'Wednesday': 0.95,
    'Thursday': 0.90, 'Friday': 0.95,
    'Saturday': 1.14, 'Sunday': 1.05,
}

MONTH_MULTIPLIERS = {1: 1.00, 2: 0.99, 3: 0.97}

rng = np.random.default_rng(42)


def generate_drug_value(drug, hour, weekday, month):
    stats = DRUG_STATS[drug]
    h_mult = HOUR_MULTIPLIERS.get(hour, 0.0)
    d_mult = WEEKDAY_MULTIPLIERS.get(weekday, 1.0)
    m_mult = MONTH_MULTIPLIERS.get(month, 1.0)
    expected = stats['mean'] * h_mult * d_mult * m_mult
    if expected <= 0.001:
        return 0.0
    if rng.random() < 0.45:
        return 0.0
    val = abs(rng.normal(loc=expected * 1.4, scale=stats['std'] * 0.6))
    return float(round(min(val, stats['max']), 4))


# ── Step 1: Delete all 2020 rows ─────────────────────────────────────────────
def delete_all_2020():
    print("Step 1: Deleting all 2020 rows from sales_hourly...")
    supabase = get_supabase()
    try:
        res = supabase.table("sales_hourly") \
            .delete() \
            .gte("datum", "2020-01-01T00:00:00Z") \
            .lte("datum", "2020-12-31T23:59:59Z") \
            .execute()
        deleted = len(res.data) if res.data else 0
        print(f"  Deleted {deleted} rows (2020-01-01 to 2020-12-31)")
    except Exception as e:
        print(f"  Error during delete: {e}")


# ── Step 2: Generate Jan-Feb-Mar 2020 (3 months) ────────────────────────────
def generate_3months():
    print("\nStep 2: Generating Jan-Mar 2020 hourly data (3 months)...")
    # Jan=31 days, Feb=29 days (2020 is leap year), Mar=31 days = 91 days x 24h = 2,184 rows
    timestamps = pd.date_range(
        start='2020-01-01 00:00:00',
        end='2020-03-31 23:00:00',
        freq='h',
        tz=timezone.utc
    )

    rows = []
    for ts in timestamps:
        weekday = ts.strftime('%A')
        hour    = ts.hour
        month   = ts.month

        row = {
            'datum':        ts.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'Year':         2020,
            'Month':        month,
            'Hour':         hour,
            'Weekday Name': weekday,
            'is_trained':   False,
        }
        for drug in DRUGS:
            row[drug] = generate_drug_value(drug, hour, weekday, month)
        rows.append(row)

    df = pd.DataFrame(rows)
    print(f"  Generated {len(df):,} rows  ({df['datum'].iloc[0]} to {df['datum'].iloc[-1]})")
    print(f"  Months covered: Jan ({(df['Month']==1).sum()}h), Feb ({(df['Month']==2).sum()}h), Mar ({(df['Month']==3).sum()}h)")
    return df


# ── Step 3: Upload to Supabase ───────────────────────────────────────────────
def upload(df):
    print(f"\nStep 3: Uploading {len(df):,} rows to Supabase...")
    supabase = get_supabase()
    records = df.to_dict(orient='records')
    batch_size = 500
    total_batches = (len(records) + batch_size - 1) // batch_size

    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        batch_num = i // batch_size + 1
        try:
            supabase.table("sales_hourly").upsert(batch, on_conflict="datum").execute()
            print(f"  [OK] Batch {batch_num}/{total_batches}")
        except Exception as e:
            print(f"  [ERROR] Batch {batch_num}: {e}")

    print(f"  Done! {len(df):,} rows uploaded (is_trained=False).")


def restore_baseline_forecasts():
    """Restores original baseline CSV plan files and re-seeds forecast_results."""
    import shutil
    from core.ml_paths import DRUGS, DRUG_MODELS_DIR
    from seed_forecast_and_inventory import seed_forecast_results

    print("\nRestoring baseline pre-trained forecast predictions...")
    for drug in DRUGS:
        dl = drug.lower()
        plan_path = os.path.join(DRUG_MODELS_DIR, f"{dl}_models", f"{dl}_hybrid_supply_chain_plan.csv")
        backup_path = os.path.join(DRUG_MODELS_DIR, f"{dl}_models", f"{dl}_hybrid_supply_chain_plan_baseline.csv")
        if os.path.exists(backup_path):
            shutil.copyfile(backup_path, plan_path)

    seed_forecast_results()

    # Clear actual_sales in forecast_results for 2020
    try:
        from clear_2020_forecast_actuals import clear_2020_actuals
        clear_2020_actuals()
    except Exception as e:
        print(f"Notice clearing 2020 actuals: {e}")

# ── Step 4: Verify ───────────────────────────────────────────────────────────
def verify():
    print("\nStep 4: Verifying...")
    supabase = get_supabase()
    try:
        # Total 2020 rows
        res = supabase.table("sales_hourly") \
            .select("datum", count="exact") \
            .gte("datum", "2020-01-01") \
            .lte("datum", "2020-12-31T23:59:59Z") \
            .execute()
        total = res.count if hasattr(res, 'count') else len(res.data)
        print(f"  2020 rows in sales_hourly : {total:,}  (expected 2,184)")

        # is_trained=False count
        res2 = supabase.table("sales_hourly") \
            .select("datum", count="exact") \
            .gte("datum", "2020-01-01") \
            .eq("is_trained", False) \
            .execute()
        untrained = res2.count if hasattr(res2, 'count') else len(res2.data)
        print(f"  Rows with is_trained=False: {untrained:,}")
        print(f"\n  3 months of untrained actual data ready. Baseline forecasts restored!")
    except Exception as e:
        print(f"  Verification error: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("  Reset 2020 sales_hourly to 3 Months (Jan-Mar) & Restore Baseline Forecasts")
    print("=" * 60)
    delete_all_2020()
    df = generate_3months()
    upload(df)
    restore_baseline_forecasts()
    verify()
