"""
Seed Script: Ingest Forecast & Inventory CSV data and Raw Hourly Sales into Supabase tables:
  1. forecast_results
  2. inventory_recommendations
  3. sales_hourly
"""
import os
import glob
import numpy as np
import pandas as pd
from core.database import get_supabase
from core.ml_paths import BASE_DIR, DRUGS, DRUG_MODELS_DIR, INVENTORY_RECOMMENDATION_DIR

def seed_forecast_results():
    print("\n==================================================")
    print("Seeding Forecast Results into Supabase...")
    all_forecast_records = []
    
    for drug in DRUGS:
        drug_lower = drug.lower()
        csv_path = os.path.join(DRUG_MODELS_DIR, f"{drug_lower}_models", f"{drug_lower}_hybrid_supply_chain_plan.csv")
        
        if not os.path.exists(csv_path):
            print(f"Warning: Could not find forecast plan for {drug} at {csv_path}")
            continue
            
        df = pd.read_csv(csv_path)
        df.columns = [c.strip() for c in df.columns]
        
        date_col = next((c for c in df.columns if 'date' in c.lower()), 'Date')
        act_col  = next((c for c in df.columns if 'actual' in c.lower()), 'Actual Sales')
        p10_col  = next((c for c in df.columns if 'p10' in c.lower() and 'lean' in c.lower()), 'Lean Lower Bound (P10)')
        p50_col  = next((c for c in df.columns if 'p50' in c.lower() and 'expected' in c.lower()), 'Expected Demand Anchor (P50)')
        p90_col  = next((c for c in df.columns if 'p90' in c.lower() and 'upper' in c.lower()), 'Upper Target Stock (P90)')
        
        for _, row in df.iterrows():
            date_str = str(row[date_col])[:10]
            p10_val = float(row[p10_col]) if pd.notna(row[p10_col]) else 0.0
            p50_val = float(row[p50_col]) if pd.notna(row[p50_col]) else 0.0
            p90_val = float(row[p90_col]) if pd.notna(row[p90_col]) else 0.0
            act_val = float(row[act_col]) if (pd.notna(row[act_col]) and not np.isnan(float(row[act_col]))) else None
            
            all_forecast_records.append({
                "forecast_date": date_str,
                "drug_code": drug,
                "actual_sales": act_val,
                "p10_demand": p10_val,
                "p50_demand": p50_val,
                "p90_demand": p90_val,
                "uncertainty_band": round(p90_val - p10_val, 4),
            })
            
    print(f"  Total forecast records prepared: {len(all_forecast_records):,}")
    
    try:
        supabase = get_supabase()
        batch_size = 500
        for i in range(0, len(all_forecast_records), batch_size):
            batch = all_forecast_records[i:i + batch_size]
            supabase.table("forecast_results").upsert(batch, on_conflict="forecast_date,drug_code").execute()
            print(f"   [OK] Uploaded forecast records {i + 1} to {min(i + batch_size, len(all_forecast_records))}")
        print("Successfully seeded forecast_results table in Supabase!")
    except Exception as e:
        print(f"Supabase upload notice for forecast_results: {e}")

def seed_inventory_recommendations():
    print("\n==================================================")
    print("Seeding Inventory Recommendations into Supabase...")
    
    inv_csv_path = os.path.join(INVENTORY_RECOMMENDATION_DIR, "inventory_recommendations_all_drugs.csv")
    if not os.path.exists(inv_csv_path):
        print(f"❌ Error: Inventory CSV not found at {inv_csv_path}")
        return
        
    df = pd.read_csv(inv_csv_path)
    df.columns = [c.strip() for c in df.columns]
    
    records = []
    for _, row in df.iterrows():
        act_raw = row['actual_sales']
        act_val = float(act_raw) if (pd.notna(act_raw) and not np.isnan(float(act_raw))) else None
        records.append({
            "recommendation_date": str(row['date'])[:10],
            "drug_code": str(row['drug_category']),
            "actual_sales": act_val,
            "p10_demand": float(row['p10_demand']),
            "p50_demand": float(row['p50_demand']),
            "p90_demand": float(row['p90_demand']),
            "safety_stock": float(row['safety_stock']),
            "reorder_point": float(row['reorder_point']),
            "target_stock_lvl": float(row['target_stock_lvl']),
            "simulated_inventory": float(row['simulated_inventory']),
            "stockout_risk": bool(row['stockout_risk']),
            "overstock_risk": bool(row['overstock_risk']),
            "replenishment_recommendation": str(row['replenishment_recommendation']),
            "recommended_order_qty": float(row['recommended_order_qty']),
        })
        
    print(f"  Total inventory recommendation records prepared: {len(records):,}")
    
    try:
        supabase = get_supabase()
        batch_size = 500
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            supabase.table("inventory_recommendations").upsert(batch, on_conflict="recommendation_date,drug_code").execute()
            print(f"   [OK] Uploaded inventory records {i + 1} to {min(i + batch_size, len(records))}")
        print("Successfully seeded inventory_recommendations table in Supabase!")
    except Exception as e:
        print(f"Supabase upload notice for inventory_recommendations: {e}")

def seed_sales_hourly():
    print("\n==================================================")
    print("Seeding Raw Hourly Sales into Supabase (sales_hourly)...")
    
    hourly_path = os.path.join(BASE_DIR, "times_series", "dataset", "saleshourly.csv")
    if not os.path.exists(hourly_path):
        print(f"Warning: Could not find hourly CSV at {hourly_path}")
        return
        
    df = pd.read_csv(hourly_path)
    df['datum'] = pd.to_datetime(df['datum']).dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    records = []
    for _, row in df.iterrows():
        records.append({
            "datum": row['datum'],
            "M01AB": float(row['M01AB']),
            "M01AE": float(row['M01AE']),
            "N02BA": float(row['N02BA']),
            "N02BE": float(row['N02BE']),
            "N05B": float(row['N05B']),
            "N05C": float(row['N05C']),
            "R03": float(row['R03']),
            "R06": float(row['R06']),
            "Year": int(row['Year']),
            "Month": int(row['Month']),
            "Hour": int(row['Hour']),
            "Weekday Name": str(row['Weekday Name']),
            "is_trained": True,  # All 2014-2019 records are trained!
        })
        
    print(f"  Total sales_hourly records prepared: {len(records):,}")
    
    try:
        supabase = get_supabase()
        batch_size = 1000
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            supabase.table("sales_hourly").upsert(batch, on_conflict="datum").execute()
            if (i // batch_size) % 5 == 0 or (i + batch_size) >= len(records):
                print(f"   [OK] Uploaded sales_hourly records {i + 1} to {min(i + batch_size, len(records))}")
        print("Successfully seeded sales_hourly table in Supabase (is_trained = True)!")
    except Exception as e:
        print(f"Supabase upload notice for sales_hourly: {e}")

if __name__ == "__main__":
    seed_forecast_results()
    seed_inventory_recommendations()
    seed_sales_hourly()
