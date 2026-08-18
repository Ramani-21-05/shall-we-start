"""
Inventory Service — queries Supabase 'inventory_recommendations' table ONLY.
No local CSV fallback.
Supports year filtering (2019 vs 2020).
"""
import os
import pandas as pd
from core.ml_paths import INVENTORY_RECOMMENDATION_DIR
from core.database import get_supabase

def get_inventory_recommendations(drug: str, year: str = None) -> list[dict]:
    drug_upper = drug.upper()
    
    # Query Supabase 'inventory_recommendations' table ONLY (no CSV fallback)
    try:
        supabase = get_supabase()
        query = supabase.table("inventory_recommendations").select("*").eq("drug_code", drug_upper).order("recommendation_date")
        
        if year:
            query = query.gte("recommendation_date", f"{year}-01-01").lte("recommendation_date", f"{year}-12-31")
            
        res = query.execute()
        records = []
        if res.data and len(res.data) > 0:
            for row in res.data:
                act_raw = row.get("actual_sales")
                act_val = float(act_raw) if (act_raw is not None and pd.notna(act_raw) and str(act_raw).lower() != 'nan') else None
                records.append({
                    "drug_code": row["drug_code"],
                    "recommendation_date": str(row["recommendation_date"])[:10],
                    "actual_sales": act_val,
                    "p50_demand": float(row.get("p50_demand", 0)),
                    "p90_demand": float(row.get("p90_demand", 0)),
                    "reorder_point": float(row.get("reorder_point", 0)),
                    "target_stock_level": float(row.get("target_stock_lvl", 0)),
                    "simulated_inventory": float(row.get("simulated_inventory", 0)),
                    "recommended_order_qty": float(row.get("recommended_order_qty", 0)),
                    "replenishment_recommendation": str(row.get("replenishment_recommendation", "MAINTAIN REPLENISHMENT")),
                    "stockout_risk": bool(row.get("stockout_risk", False)),
                    "overstock_risk": bool(row.get("overstock_risk", False)),
                    "source": "supabase"
                })
        return records
    except Exception as e:
        print(f"Error fetching inventory recommendations from Supabase for {drug}: {e}")
        return []

def get_inventory_evaluation(drug: str) -> dict | None:
    tech_path = os.path.join(INVENTORY_RECOMMENDATION_DIR, "inventory_recommendation_evaluation.csv")
    biz_path  = os.path.join(INVENTORY_RECOMMENDATION_DIR, "inventory_business_level_evaluation.csv")

    result = {"drug_code": drug}

    if os.path.exists(tech_path):
        df = pd.read_csv(tech_path)
        drug_col = "Drug Category" if "Drug Category" in df.columns else "drug"
        row = df[df[drug_col] == drug]
        if not row.empty:
            result.update(row.iloc[0].to_dict())

    if os.path.exists(biz_path):
        df = pd.read_csv(biz_path)
        drug_col = "Drug Category" if "Drug Category" in df.columns else "drug"
        row = df[df[drug_col] == drug]
        if not row.empty:
            result.update(row.iloc[0].to_dict())

    return result
