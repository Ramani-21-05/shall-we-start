"""
Seed Script: Ingest original saleshourly.csv into Supabase database.
Dataset: times_series/dataset/saleshourly.csv (50,532 records)
"""
import os
import pandas as pd
from core.database import get_supabase
from core.ml_paths import BASE_DIR

CSV_PATH = os.path.join(BASE_DIR, "times_series", "dataset", "saleshourly.csv")

def assign_split(year: int) -> str:
    if year <= 2017:
        return "train"
    elif year == 2018:
        return "val"
    else:
        return "test"

def seed_sales_hourly():
    if not os.path.exists(CSV_PATH):
        print(f"❌ Error: CSV file not found at {CSV_PATH}")
        return

    print(f"📖 Reading original dataset from: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)
    print(f"📊 Loaded {len(df):,} rows from saleshourly.csv")

    # Clean datum timestamp
    df['datum'] = pd.to_datetime(df['datum'], format='%m/%d/%Y %H:%M')
    df['dataset_split'] = df['Year'].apply(assign_split)

    records = []
    for _, row in df.iterrows():
        records.append({
            "datum": row['datum'].isoformat(),
            "m01ab": float(row['M01AB']),
            "m01ae": float(row['M01AE']),
            "n02ba": float(row['N02BA']),
            "n02be": float(row['N02BE']),
            "n05b": float(row['N05B']),
            "n05c": float(row['N05C']),
            "r03": float(row['R03']),
            "r06": float(row['R06']),
            "year": int(row['Year']),
            "month": int(row['Month']),
            "hour": int(row['Hour']),
            "weekday_name": str(row['Weekday Name']),
            "dataset_split": str(row['dataset_split']),
        })

    try:
        supabase = get_supabase()
        batch_size = 1000
        total = len(records)
        print(f"🚀 Uploading {total:,} rows to Supabase in batches of {batch_size}...")

        for i in range(0, total, batch_size):
            batch = records[i:i + batch_size]
            res = supabase.table("sales_hourly_raw").upsert(batch, on_conflict="datum").execute()
            print(f"  ✓ Uploaded rows {i + 1} to {min(i + batch_size, total)}")

        print("✅ Successfully seeded saleshourly.csv into Supabase!")
    except Exception as e:
        print(f"⚠️ Supabase upload skipped or failed: {e}")
        print("💡 Ensure SUPABASE_URL and SUPABASE_KEY are configured in .env and supabase_schema.sql is executed.")

if __name__ == "__main__":
    seed_sales_hourly()
