from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ml_services.forecast_service import get_forecast_data, trigger_model_retrain
from core.database import get_supabase

router = APIRouter(prefix="/api/forecast", tags=["Forecast"])

@router.get("/{drug_code}/retrain-eligibility")
def check_retrain_eligibility(drug_code: str):
    """
    Returns whether the model is eligible for retraining.
    Eligible = 3+ distinct calendar months of new actual sales data exist in
    sales_hourly where is_trained (or is_training) is False.
    """
    try:
        supabase = get_supabase()
        months = set()
        offset = 0
        page_size = 1000

        while True:
            res = supabase.table("sales_hourly") \
                .select("Year, Month, datum") \
                .eq("is_trained", False) \
                .range(offset, offset + page_size - 1) \
                .execute()
            batch = res.data or []
            for row in batch:
                y = row.get("Year")
                m = row.get("Month")
                if y and m:
                    months.add(f"{y}-{str(m).zfill(2)}")
                else:
                    datum_str = str(row.get("datum", ""))
                    if len(datum_str) >= 7:
                        months.add(datum_str[:7])
            if len(batch) < page_size:
                break
            offset += page_size

        untrained_months = len(months)
        return {
            "eligible": untrained_months >= 3,
            "untrained_months": untrained_months,
            "months": sorted(list(months)),
            "threshold": 3
        }
    except Exception as e:
        return {"eligible": False, "untrained_months": 0, "months": [], "threshold": 3, "error": str(e)}

@router.get("/{drug_code}")
def get_forecast(drug_code: str, year: Optional[str] = Query(None, description="Year filter e.g. 2019 or 2020"), limit: int = 400):
    try:
        data = get_forecast_data(drug_code.upper(), year=year)
        return {
            "drug_code": drug_code.upper(),
            "year_filter": year or "ALL",
            "data": data[:limit],
            "count": len(data),
            "note": f"Forecast dataset for {drug_code.upper()} (Year: {year or 'ALL'})."
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{drug_code}/retrain")
def retrain_forecast_model(drug_code: str):
    try:
        res = trigger_model_retrain(drug_code.upper())
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset-demo-state")
def reset_demo_state():
    """Resets 2020 sales_hourly to 3 months with is_trained=False and clears forecast_results.actual_sales."""
    try:
        import reset_2020_to_3months
        import clear_2020_forecast_actuals
        reset_2020_to_3months.delete_all_2020()
        df = reset_2020_to_3months.generate_3months()
        reset_2020_to_3months.upload(df)
        clear_2020_forecast_actuals.clear_2020_actuals()
        return {
            "status": "RESET_COMPLETE",
            "message": "Successfully reset 2020 data to 3 untrained months (is_training = False) and cleared forecast_results.actual_sales."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
