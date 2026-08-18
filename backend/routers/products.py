from fastapi import APIRouter
from core.ml_paths import DRUGS, DRUG_NAMES, CHAMPION_MAP

router = APIRouter(prefix="/api/products", tags=["Products"])

@router.get("")
def list_products():
    products = []
    for drug in DRUGS:
        champion = CHAMPION_MAP[drug]
        products.append({
            "drug_code": drug,
            "drug_name": DRUG_NAMES[drug],
            "champion_model_name": champion["model_name"],
            "algorithm_family": champion["algorithm_family"],
            "training_cutoff_date": "2018-12-31",
            "anomaly_detection_year": 2019,
        })
    return {"data": products, "count": len(products)}

@router.get("/{drug_code}")
def get_product(drug_code: str):
    drug = drug_code.upper()
    if drug not in DRUGS:
        return {"error": f"Drug {drug} not found"}
    champion = CHAMPION_MAP[drug]
    return {
        "drug_code": drug,
        "drug_name": DRUG_NAMES[drug],
        "champion_model_name": champion["model_name"],
        "algorithm_family": champion["algorithm_family"],
        "training_cutoff_date": "2018-12-31",
        "anomaly_detection_year": 2019,
    }
