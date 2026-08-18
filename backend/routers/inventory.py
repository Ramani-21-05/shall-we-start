from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ml_services.inventory_service import get_inventory_recommendations, get_inventory_evaluation

router = APIRouter(prefix="/api/inventory", tags=["Inventory"])

@router.get("/{drug_code}/recommendations")
def inventory_recommendations(drug_code: str, year: Optional[str] = Query(None, description="Year filter e.g. 2019 or 2020"), limit: int = 365):
    try:
        data = get_inventory_recommendations(drug_code.upper(), year=year)
        return {"drug_code": drug_code.upper(), "year_filter": year or "ALL", "data": data[:limit], "count": len(data)}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{drug_code}/evaluation")
def inventory_evaluation(drug_code: str):
    try:
        return {"drug_code": drug_code.upper(), "data": get_inventory_evaluation(drug_code.upper())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
