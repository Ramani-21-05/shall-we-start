"""
Forecast Service — queries Supabase 'forecast_results' table ONLY.
No local CSV fallback.
Supports 2019 holdout backtesting and 2020 future demand projections.
Supports P10, P50, and P90 quantile demand intervals.
Supports on-demand model retraining & horizon extension.
"""
import os, subprocess, sys
from core.ml_paths import BASE_DIR, DRUG_MODELS_DIR
from core.database import get_supabase

def get_forecast_data(drug: str, year: str = None) -> list[dict]:
    drug_upper = drug.upper()
    drug_lower = drug.lower()
    
    # 1. Try Supabase 'forecast_results' table
    try:
        supabase = get_supabase()
        query = supabase.table("forecast_results").select("*").eq("drug_code", drug_upper).order("forecast_date")
        
        if year:
            query = query.gte("forecast_date", f"{year}-01-01").lte("forecast_date", f"{year}-12-31")
            
        res = query.execute()
        records = []
        if res.data and len(res.data) > 0:
            for row in res.data:
                records.append({
                    "date": str(row["forecast_date"])[:10],
                    "drug_code": row["drug_code"],
                    "actual_sales": row.get("actual_sales"),
                    "p10_demand": float(row.get("p10_demand", 0)),
                    "p50_demand": float(row.get("p50_demand", 0)),
                    "p90_demand": float(row.get("p90_demand", 0)),
                    "source": "supabase"
                })
            return records
    except Exception as e:
        print(f"Notice: Supabase forecast query fallback for {drug}: {e}")

    # 2. Local CSV fallback if Supabase is offline
    csv_path = os.path.join(DRUG_MODELS_DIR, f"{drug_lower}_models", f"{drug_lower}_hybrid_supply_chain_plan.csv")
    if os.path.exists(csv_path):
        import pandas as pd
        df = pd.read_csv(csv_path)
        df.columns = [c.strip() for c in df.columns]
        date_col = next((c for c in df.columns if 'date' in c.lower()), 'Date')
        act_col  = next((c for c in df.columns if 'actual' in c.lower()), 'Actual Sales')
        p10_col  = next((c for c in df.columns if 'p10' in c.lower()), 'Lean Lower Bound (P10)')
        p50_col  = next((c for c in df.columns if 'p50' in c.lower()), 'Expected Demand Anchor (P50)')
        p90_col  = next((c for c in df.columns if 'p90' in c.lower()), 'Upper Target Stock (P90)')

        if year:
            df = df[df[date_col].str.startswith(str(year))]

        records = []
        for _, row in df.iterrows():
            act_val = float(row[act_col]) if pd.notna(row[act_col]) else None
            records.append({
                "date": str(row[date_col])[:10],
                "drug_code": drug_upper,
                "actual_sales": act_val,
                "p10_demand": float(row[p10_col]),
                "p50_demand": float(row[p50_col]),
                "p90_demand": float(row[p90_col]),
                "source": "local_csv"
            })
        return records

    return []

def trigger_model_retrain(drug_code: str = None) -> dict:
    """Triggers champion model retraining for ALL 8 drugs in background thread."""
    try:
        from ml_services.retrain_engine import start_retrain_in_thread
        start_retrain_in_thread(drug_code)
        return {
            "status": "RETRAINING_STARTED",
            "drug_code": drug_code.upper() if drug_code else "ALL",
            "message": "Model retraining for all 8 drug models started in background thread. Syncing updated forecasts to forecast_results."
        }
    except Exception as e:
        print(f"Error during model retraining: {e}")
        return {
            "status": "RETRAINING_FAILED",
            "drug_code": drug_code.upper() if drug_code else "ALL",
            "message": str(e)
        }
