"""
routers/inventory_v2.py
───────────────────────
API Endpoints for Forecast-Driven Inventory Decision Engine
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from routers.activity_logs import _write_log
from ml_services.inventory_engine import (
    get_all_inventory_overview,
    evaluate_drug_inventory,
    record_sale,
    record_inventory_transaction,
    update_baseline_stock,
    create_replenishment_order,
    get_transaction_history,
    get_baseline_history,
    get_sunday_replenishment_review,
    reset_db,
)

router = APIRouter(prefix="/api/v2/inventory", tags=["Inventory Engine v2"])


@router.post("/reset")
def reset_inventory():
    """Reset inventory database to fresh initial state."""
    try:
        reset_db()
        return {"status": "ok", "message": "Inventory database reset to fresh default state."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Pydantic Request Models ──────────────────────────────────────────────────

class SaleRequest(BaseModel):
    drug_code: str = Field(..., example="N02BE")
    quantity: float = Field(..., gt=0, example=25.0)
    user_id: Optional[str] = "pharmacist"
    notes: Optional[str] = "Direct POS sale"


class TransactionRequest(BaseModel):
    drug_code: str = Field(..., example="N02BE")
    transaction_type: str = Field(..., example="RESTOCK") # SALE, RESTOCK, RETURN, DAMAGE, EXPIRY, ADJUSTMENT
    quantity: float = Field(..., gt=0, example=100.0)
    user_id: Optional[str] = "pharmacist"
    notes: Optional[str] = ""


class BaselineUpdateRequest(BaseModel):
    drug_code: str = Field(..., example="N02BE")
    new_baseline: float = Field(..., gt=0, example=1100.0)
    source: Optional[str] = "MANUAL" # MANUAL or FORECAST_RECOMMENDATION
    reason: Optional[str] = "Pharmacist review"
    changed_by: Optional[str] = "pharmacist"
    status: Optional[str] = "ACCEPTED"


class ApproveOrderRequest(BaseModel):
    drug_code: str = Field(..., example="N02BE")
    quantity: float = Field(..., gt=0, example=700.0)
    approved_by: Optional[str] = "pharmacist"
    reason: Optional[str] = "Approved 70% replenishment recommendation"


# ── Router Endpoints ─────────────────────────────────────────────────────────

@router.get("/overview")
def get_overview():
    """Get live inventory decision matrix for all 8 drugs."""
    try:
        return {"data": get_all_inventory_overview(), "count": 8}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sunday-review")
def sunday_review():
    """Get Sunday full replenishment review matrix."""
    try:
        return {"data": get_sunday_replenishment_review()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
def get_alerts():
    """Get actionable alerts (drugs in WATCH, REPLENISHMENT_RECOMMENDED, STOCKOUT_RISK, EMERGENCY)."""
    try:
        overview = get_all_inventory_overview()
        alerts = [item for item in overview if item["status"] != "HEALTHY"]
        return {"data": alerts, "count": len(alerts)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transactions")
def get_transactions(drug: Optional[str] = None, limit: int = 100):
    """Get audit logs of all inventory transactions."""
    try:
        return {"data": get_transaction_history(drug_code=drug, limit=limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/baseline-history")
def baseline_history(drug: Optional[str] = None):
    """Get baseline change history logs."""
    try:
        return {"data": get_baseline_history(drug_code=drug)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{drug_code}")
def get_drug_details(drug_code: str):
    """Get full decision metrics and forecast projections for a single drug."""
    try:
        data = evaluate_drug_inventory(drug_code.upper())
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sale")
def record_drug_sale(req: SaleRequest):
    """Record a sale, decrease stock, log transaction audit, and update alert state."""
    try:
        res = record_sale(
            drug_code=req.drug_code.upper(),
            quantity=req.quantity,
            user_id=req.user_id or "pharmacist",
            notes=req.notes or ""
        )
        _write_log(
            event_type="STOCK_UPDATED",
            message=f"Sale recorded: {req.quantity} units of '{req.drug_code.upper()}' by '{req.user_id}'.",
            username=req.user_id or "pharmacist",
            user_role="STAFF",
            status="SUCCESS",
            detail=f"Drug: {req.drug_code.upper()} | Qty: {req.quantity} | Notes: {req.notes}",
        )
        return {"status": "ok", "message": f"Sale of {req.quantity} units recorded.", "evaluation": res}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transaction")
def execute_transaction(req: TransactionRequest):
    """Log an inventory transaction (SALE, RESTOCK, RETURN, DAMAGE, EXPIRY, ADJUSTMENT)."""
    try:
        res = record_inventory_transaction(
            drug_code=req.drug_code.upper(),
            transaction_type=req.transaction_type,
            quantity=req.quantity,
            user_id=req.user_id or "pharmacist",
            notes=req.notes or ""
        )
        _write_log(
            event_type="STOCK_UPDATED",
            message=f"Inventory transaction '{req.transaction_type}': {req.quantity} units of '{req.drug_code.upper()}'.",
            username=req.user_id or "pharmacist",
            user_role="STAFF",
            status="SUCCESS",
            detail=f"Drug: {req.drug_code.upper()} | Type: {req.transaction_type} | Qty: {req.quantity} | Notes: {req.notes}",
        )
        return {"status": "ok", "message": f"Transaction {req.transaction_type} executed.", "evaluation": res}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/baseline")
def set_baseline(req: BaselineUpdateRequest):
    """Manually set baseline stock or accept/edit forecast recommendation."""
    try:
        res = update_baseline_stock(
            drug_code=req.drug_code.upper(),
            new_baseline=req.new_baseline,
            source=req.source or "MANUAL",
            reason=req.reason or "Pharmacist decision",
            changed_by=req.changed_by or "pharmacist",
            status=req.status or "ACCEPTED"
        )
        _write_log(
            event_type="BASELINE_STOCK_CHANGED",
            message=f"Baseline for '{req.drug_code.upper()}' updated to {req.new_baseline} units by '{req.changed_by}'.",
            username=req.changed_by or "pharmacist",
            user_role="STAFF",
            status="SUCCESS",
            detail=f"Drug: {req.drug_code.upper()} | New baseline: {req.new_baseline} | Source: {req.source} | Reason: {req.reason}",
        )
        return {"status": "ok", "message": f"Baseline for {req.drug_code} updated to {req.new_baseline}.", "evaluation": res}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/order/approve")
def approve_order(req: ApproveOrderRequest):
    """Pharmacy member approves replenishment recommendation, sending order to Vendor Dashboard."""
    try:
        res = create_replenishment_order(
            drug_code=req.drug_code.upper(),
            quantity=req.quantity,
            approved_by=req.approved_by or "pharmacist",
            reason=req.reason or "Recommendation approved"
        )
        _write_log(
            event_type="STOCK_UPDATED",
            message=f"Replenishment order approved: {req.quantity} units of '{req.drug_code.upper()}' by '{req.approved_by}'.",
            username=req.approved_by or "pharmacist",
            user_role="STAFF",
            status="SUCCESS",
            detail=f"Drug: {req.drug_code.upper()} | Order qty: {req.quantity} | Reason: {req.reason}",
        )
        return {"status": "ok", "data": res}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
