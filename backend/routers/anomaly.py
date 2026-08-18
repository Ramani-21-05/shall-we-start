from fastapi import APIRouter, HTTPException
from ml_services.anomaly_service import get_anomalies, get_anomaly_summary

router = APIRouter(prefix="/api/anomaly", tags=["Anomaly Detection"])

@router.get("/summary")
def anomaly_portfolio_summary():
    return {"data": get_anomaly_summary()}

@router.get("/{drug_code}")
def drug_anomalies(drug_code: str):
    try:
        data = get_anomalies(drug_code.upper())
        return {
            "drug_code": drug_code.upper(),
            "data": data,
            "count": len(data),
            "note": "Anomalies detected on 2019 holdout data only (model NOT trained on 2019)."
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
