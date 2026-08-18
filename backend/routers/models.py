from fastapi import APIRouter, HTTPException
from ml_services.model_registry_service import get_champion_model

router = APIRouter(prefix="/api/models", tags=["Models"])

@router.get("/{drug_code}/champion")
def drug_champion_model(drug_code: str):
    try:
        return {"drug_code": drug_code.upper(), "data": get_champion_model(drug_code.upper())}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

