import sys
sys.path.insert(0, '.')
from core.database import get_supabase

supabase = get_supabase()

# Bulk UPDATE — no SELECT needed, just overwrite all Apr-Dec 2020 rows directly
print("Bulk clearing forecast_results.actual_sales for Apr-Dec 2020...")
res1 = supabase.table("forecast_results") \
    .update({"actual_sales": None}) \
    .gte("forecast_date", "2020-04-01") \
    .lte("forecast_date", "2020-12-31") \
    .execute()
print(f"  Rows updated: {len(res1.data)}")

print("Bulk clearing inventory_recommendations.actual_sales for Apr-Dec 2020...")
res2 = supabase.table("inventory_recommendations") \
    .update({"actual_sales": None}) \
    .gte("recommendation_date", "2020-04-01") \
    .lte("recommendation_date", "2020-12-31") \
    .execute()
print(f"  Rows updated: {len(res2.data)}")

# Verify using count
print()
print("=== Final Verification ===")

c1 = supabase.table("forecast_results").select("forecast_date", count="exact") \
    .gte("forecast_date", "2020-01-01").lte("forecast_date", "2020-03-31") \
    .not_.is_("actual_sales", "null").execute()
print(f"forecast_results  Jan-Mar with actual_sales : {c1.count}  (expected 728)")

c2 = supabase.table("forecast_results").select("forecast_date", count="exact") \
    .gte("forecast_date", "2020-04-01").lte("forecast_date", "2020-12-31") \
    .not_.is_("actual_sales", "null").execute()
print(f"forecast_results  Apr-Dec with actual_sales : {c2.count}  (expected 0)")

c3 = supabase.table("inventory_recommendations").select("recommendation_date", count="exact") \
    .gte("recommendation_date", "2020-01-01").lte("recommendation_date", "2020-03-31") \
    .not_.is_("actual_sales", "null").execute()
print(f"inventory_recs    Jan-Mar with actual_sales : {c3.count}")

c4 = supabase.table("inventory_recommendations").select("recommendation_date", count="exact") \
    .gte("recommendation_date", "2020-04-01").lte("recommendation_date", "2020-12-31") \
    .not_.is_("actual_sales", "null").execute()
print(f"inventory_recs    Apr-Dec with actual_sales : {c4.count}  (expected 0)")

if c2.count == 0 and c4.count == 0:
    print("\nAll clean! Only Jan-Mar 2020 has actual_sales. Apr-Dec is NULL.")
else:
    print(f"\nWARNING: {c2.count + c4.count} rows still have actual_sales in Apr-Dec.")
