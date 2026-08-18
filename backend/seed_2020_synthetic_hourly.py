"""
seed_2020_synthetic_hourly.py
─────────────────────────────
Generates realistic synthetic 2020 hourly pharmaceutical sales data that
mirrors the real 2015-2019 distribution (hour-of-day, weekday, monthly
seasonality, per-drug mean/std) and uploads it to the Supabase
`sales_hourly` table with is_trained=False.

Usage:
    cd backend
    python seed_2020_synthetic_hourly.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import pandas as pd
from datetime import timezone

from core.database import get_supabase

DRUGS = ['M01AB', 'M01AE', 'N02BA', 'N02BE', 'N05B', 'N05C', 'R03', 'R06']

# Real per-drug mean & std from 2015-2019 hourly data
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

# Hour-of-day multipliers (derived from real 2015-2019 averages)
HOUR_MULTIPLIERS = {
    0: 0.00, 1: 0.00, 2: 0.00, 3: 0.00, 4: 0.00, 5: 0.00,
    6: 0.00, 7: 0.06,
    8: 1.27, 9: 1.68, 10: 1.96, 11: 2.19,
    12: 2.13, 13: 1.81, 14: 1.94, 15: 1.48,
    16: 1.31, 17: 1.40, 18: 1.67, 19: 2.01,
    20: 1.84, 21: 1.22,
    22: 0.02, 23: 0.00,
}

# Weekday multipliers
WEEKDAY_MULTIPLIERS = {
    'Monday': 1.00, 'Tuesday': 1.00, 'Wednesday': 0.95,
    'Thursday': 0.90, 'Friday': 0.95,
    'Saturday': 1.14, 'Sunday': 1.05,
}

# Monthly seasonality multipliers
MONTH_MULTIPLIERS = {
    1: 1.00, 2: 0.99, 3: 0.97, 4: 1.02,
    5: 0.96, 6: 0.94, 7: 1.03, 8: 1.08,
    9: 0.99, 10: 0.99, 11: 1.04, 12: 0.98,
}

rng = np.random.default_rng(42)


def generate_drug_value(drug: str, hour: int, weekday: str, month: int) -> float:
    stats = DRUG_STATS[drug]
    h_mult = HOUR_MULTIPLIERS.get(hour, 0.0)
    d_mult = WEEKDAY_MULTIPLIERS.get(weekday, 1.0)
    m_mult = MONTH_MULTIPLIERS.get(month, 1.0)

    expected = stats['mean'] * h_mult * d_mult * m_mult

    if expected <= 0.001:
        return 0.0

    # ~45% of business hours have zero sales (real data is sparse)
    if rng.random() < 0.45:
        return 0.0

    val = abs(rng.normal(loc=expected * 1.4, scale=stats['std'] * 0.6))
    return float(round(min(val, stats['max']), 4))


def generate_2020_hourly() -> pd.DataFrame:
    print("Generating 2020 synthetic hourly sales data...")
    timestamps = pd.date_range(
        start='2020-01-01 00:00:00',
        end='2020-12-31 23:00:00',
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

    print("\n  Drug sanity check (synthetic vs real mean):")
    print(f"  {'Drug':<8} {'Synth Mean':>12} {'Real Mean':>12} {'Synth Max':>12} {'Real Max':>12}")
    for drug in DRUGS:
        s = DRUG_STATS[drug]
        print(f"  {drug:<8} {df[drug].mean():>12.4f} {s['mean']:>12.4f} {df[drug].max():>12.4f} {s['max']:>12.4f}")

    return df


def upload_to_supabase(df: pd.DataFrame):
    print(f"\nUploading {len(df):,} rows to Supabase sales_hourly...")
    supabase = get_supabase()
    records = df.to_dict(orient='records')
    batch_size = 500
    total_batches = (len(records) + batch_size - 1) // batch_size

    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        batch_num = i // batch_size + 1
        try:
            supabase.table("sales_hourly").upsert(batch, on_conflict="datum").execute()
            if batch_num % 4 == 0 or batch_num == total_batches:
                print(f"  [OK] Batch {batch_num}/{total_batches} — rows {i+1}–{min(i+batch_size, len(records))}")
        except Exception as e:
            print(f"  [ERROR] Batch {batch_num}: {e}")

    print(f"\nDone! {len(df):,} synthetic 2020 rows uploaded (is_trained=False).")


def verify_upload():
    print("\nVerifying upload...")
    supabase = get_supabase()
    try:
        res = supabase.table("sales_hourly") \
            .select("datum", count="exact") \
            .gte("datum", "2020-01-01") \
            .lte("datum", "2020-12-31T23:59:59Z") \
            .execute()
        count = res.count if hasattr(res, 'count') else len(res.data)
        print(f"  2020 rows in sales_hourly: {count:,}  (expected 8,784)")

        res2 = supabase.table("sales_hourly") \
            .select("datum", count="exact") \
            .gte("datum", "2020-01-01") \
            .eq("is_trained", False) \
            .execute()
        untrained = res2.count if hasattr(res2, 'count') else len(res2.data)
        print(f"  Rows with is_trained=False: {untrained:,}")
        print("\nNext steps:")
        print("  1. Forecast page -> 2020 tab: actual_sales line should now appear")
        print("  2. Inventory page -> 2020 tab: Stockout/Overstock columns show Yes/No")
        print("  3. Note: Retrain eligibility uses forecast_results (not sales_hourly),")
        print("     so run seed_forecast_and_inventory.py to populate 2020 actual_sales there too.")
    except Exception as e:
        print(f"  Verification error: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("  2020 Synthetic Hourly Sales Seeder")
    print("=" * 60)
    df = generate_2020_hourly()
    upload_to_supabase(df)
    verify_upload()
