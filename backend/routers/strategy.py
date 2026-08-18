from fastapi import APIRouter, HTTPException, Query
from ml_services.strategy_engine import get_strategy_overview, generate_product_strategy
from core.ml_paths import DRUGS

router = APIRouter(prefix="/api/strategy", tags=["Strategy"])

@router.get("/overview")
def get_strategy_overview_route(month: int | None = Query(None, ge=1, le=12)):
    """
    Returns full portfolio strategy intelligence:
      - 4-Quadrant Opportunity Matrix
      - Deterministic Sales & Marketing Strategies per Product
      - Cross-Selling & Product Association Rules
      - Marketing Campaign Timing Recommendations
    """
    return get_strategy_overview(target_month=month)

@router.get("/{drug_code}")
def get_product_strategy_route(drug_code: str, month: int | None = Query(None, ge=1, le=12)):
    """Returns deep-dive strategy intelligence for a single drug category."""
    d_upper = drug_code.upper()
    if d_upper not in DRUGS:
        raise HTTPException(status_code=400, detail=f"Invalid drug code: {d_upper}. Valid: {DRUGS}")

    strat = generate_product_strategy(d_upper, target_month=month)
    if not strat:
        raise HTTPException(status_code=404, detail=f"Strategy not found for {d_upper}")

    return strat
