"""
routers/vendor.py
─────────────────
Vendor Portal API Router — Handles replenishment orders placed by the pharmacy.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from ml_services.inventory_engine import (
    get_vendor_orders,
    update_vendor_order_status,
)

router = APIRouter(prefix="/api/v2/vendor", tags=["Vendor Operations"])


class VendorStatusUpdateRequest(BaseModel):
    status: str = Field(..., example="SHIPPED") # SHIPPED, DELIVERED, CANCELLED
    vendor_notes: Optional[str] = "Dispatched via standard cold-chain logistics."


@router.get("/orders")
def get_orders(status: Optional[str] = Query(None, description="Filter by status: PENDING_VENDOR, SHIPPED, DELIVERED, CANCELLED")):
    """Get all incoming pharmacy replenishment orders."""
    try:
        orders = get_vendor_orders(status_filter=status)
        return {"data": orders, "count": len(orders)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/orders/{order_id}/status")
def update_order_status(order_id: str, req: VendorStatusUpdateRequest):
    """
    Vendor updates order status.
    Transitioning to DELIVERED automatically triggers restocking of current stock in the pharmacy inventory.
    """
    try:
        res = update_vendor_order_status(
            order_id=order_id,
            new_status=req.status,
            vendor_notes=req.vendor_notes or ""
        )
        return {"status": "ok", "data": res}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
