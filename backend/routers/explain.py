from fastapi import APIRouter, HTTPException
from ml_services.shap_service import get_shap_weights, get_shap_breakdown, get_drug_explanation

router = APIRouter(prefix="/api/explain", tags=["Explainability"])

@router.get("/{drug_code}/summary")
def shap_drug_summary(drug_code: str):
    try:
        data = get_drug_explanation(drug_code.upper())
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{drug_code}/weights")
def shap_feature_weights(drug_code: str, top_n: int = 10):
    try:
        data = get_shap_weights(drug_code.upper())
        return {"drug_code": drug_code.upper(), "data": data[:top_n]}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{drug_code}/breakdown")
def shap_daily_breakdown(drug_code: str, limit: int = 50):
    try:
        data = get_shap_breakdown(drug_code.upper())
        return {"drug_code": drug_code.upper(), "data": data[:limit]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

