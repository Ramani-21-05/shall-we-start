"""
clear_2020_forecast_actuals.py
-------------------------------
Clears actual_sales (sets to NULL) for all 2020 records in forecast_results
and inventory_recommendations tables in Supabase.

Usage:
    cd backend
    python clear_2020_forecast_actuals.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from core.database import get_supabase

def clear_2020_actuals():
    supabase = get_supabase()
    print("Clearing actual_sales for 2020 in forecast_results...")
    res1 = supabase.table("forecast_results") \
        .update({"actual_sales": None}) \
        .gte("forecast_date", "2020-01-01") \
        .lte("forecast_date", "2020-12-31") \
        .execute()
    print(f"  forecast_results rows updated: {len(res1.data) if res1.data else 0}")

    try:
        print("Clearing actual_sales for 2020 in inventory_recommendations...")
        res2 = supabase.table("inventory_recommendations") \
            .update({"actual_sales": None}) \
            .gte("recommendation_date", "2020-01-01") \
            .lte("recommendation_date", "2020-12-31") \
            .execute()
        print(f"  inventory_recommendations rows updated: {len(res2.data) if res2.data else 0}")
    except Exception as e:
        print(f"  Notice updating inventory_recommendations: {e}")

    print("\nVerification:")
    c1 = supabase.table("forecast_results").select("forecast_date", count="exact") \
        .gte("forecast_date", "2020-01-01").lte("forecast_date", "2020-12-31") \
        .not_.is_("actual_sales", "null").execute()
    print(f"  2020 forecast_results with non-null actual_sales: {c1.count}")

if __name__ == "__main__":
    clear_2020_actuals()
