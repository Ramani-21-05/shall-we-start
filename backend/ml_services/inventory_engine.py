"""
ml_services/inventory_engine.py
─────────────────────────────────
Forecast-Driven Pharmacy Demand & Inventory Management Engine

Implements live inventory decision logic:
- Current Stock, Baseline Stock, Safety Stock, Incoming Stock, Lead Time
- Consumed %, Target Stock, Recommended Order Quantity
- 60% WATCH, 70% REPLENISHMENT_RECOMMENDED, STOCKOUT_RISK, EMERGENCY_REPLENISHMENT
- Baseline Review & Recommendations
- Sales & Inventory Audit Transactions (SALE, RESTOCK, RETURN, DAMAGE, EXPIRY, ADJUSTMENT)
- Replenishment Orders sent to Vendor Dashboard
"""

import os
import datetime
from typing import Dict, List, Any, Optional
from core.database import get_supabase

DRUG_METADATA = {
    "M01AB": {"name": "Acemetacin / Anti-inflammatory", "category": "Anti-inflammatory", "lead_time_days": 2, "default_baseline": 500.0, "default_safety": 75.0, "default_stock": 400.0},
    "M01AE": {"name": "Ibuprofen", "category": "Anti-inflammatory", "lead_time_days": 3, "default_baseline": 300.0, "default_safety": 45.0, "default_stock": 110.0},
    "N02BA": {"name": "Aspirin", "category": "Analgesic", "lead_time_days": 3, "default_baseline": 400.0, "default_safety": 60.0, "default_stock": 120.0},
    "N02BE": {"name": "Paracetamol", "category": "Analgesic / Antipyretic", "lead_time_days": 4, "default_baseline": 1000.0, "default_safety": 150.0, "default_stock": 280.0},
    "N05B":  {"name": "Anxiolytics", "category": "Psycholeptics", "lead_time_days": 2, "default_baseline": 250.0, "default_safety": 35.0, "default_stock": 210.0},
    "N05C":  {"name": "Hypnotics & Sedatives", "category": "Psycholeptics", "lead_time_days": 3, "default_baseline": 150.0, "default_safety": 25.0, "default_stock": 80.0},
    "R03":   {"name": "Asthma Treatments", "category": "Respiratory", "lead_time_days": 5, "default_baseline": 600.0, "default_safety": 90.0, "default_stock": 180.0},
    "R06":   {"name": "Antihistamines", "category": "Antihistamine", "lead_time_days": 3, "default_baseline": 450.0, "default_safety": 65.0, "default_stock": 300.0},
}

# In-Memory Cache Store for high performance & fallback
IN_MEMORY_INVENTORY: Dict[str, Dict[str, Any]] = {}
IN_MEMORY_TRANSACTIONS: List[Dict[str, Any]] = []
IN_MEMORY_BASELINE_HISTORY: List[Dict[str, Any]] = []
IN_MEMORY_ORDERS: List[Dict[str, Any]] = []


def _init_in_memory_inventory():
    """Initializes in-memory defaults."""
    for code, meta in DRUG_METADATA.items():
        if code not in IN_MEMORY_INVENTORY:
            IN_MEMORY_INVENTORY[code] = {
                "drug_code": code,
                "drug_name": meta["name"],
                "category": meta["category"],
                "current_stock": meta["default_stock"],
                "baseline_stock": meta["default_baseline"],
                "safety_stock": meta["default_safety"],
                "incoming_stock": 0.0,
                "lead_time_days": meta["lead_time_days"],
                "reorder_threshold": 70.0,
            }


_init_in_memory_inventory()


def fetch_drug_from_supabase(drug_code: str) -> Dict[str, Any]:
    """Fetches single drug inventory from Supabase or returns in-memory cache."""
    try:
        sb = get_supabase()
        res = sb.table("inventory").select("*").eq("drug_code", drug_code).execute()
        if res.data and len(res.data) > 0:
            row = res.data[0]
            item = {
                "drug_code": row["drug_code"],
                "drug_name": row.get("drug_name", DRUG_METADATA.get(drug_code, {}).get("name", drug_code)),
                "category": row.get("category", DRUG_METADATA.get(drug_code, {}).get("category", "General")),
                "current_stock": float(row.get("current_stock", 0.0)),
                "baseline_stock": float(row.get("baseline_stock", 500.0)),
                "safety_stock": float(row.get("safety_stock", 75.0)),
                "incoming_stock": float(row.get("incoming_stock", 0.0)),
                "lead_time_days": int(row.get("lead_time_days", 3)),
                "reorder_threshold": float(row.get("reorder_threshold", 70.0)),
            }
            IN_MEMORY_INVENTORY[drug_code] = item
            return item
    except Exception as e:
        print(f"Notice: Supabase inventory fetch fallback for {drug_code}: {e}")

    return IN_MEMORY_INVENTORY.get(
        drug_code,
        {
            "drug_code": drug_code,
            "drug_name": DRUG_METADATA.get(drug_code, {}).get("name", drug_code),
            "category": DRUG_METADATA.get(drug_code, {}).get("category", "General"),
            "current_stock": DRUG_METADATA.get(drug_code, {}).get("default_stock", 300.0),
            "baseline_stock": DRUG_METADATA.get(drug_code, {}).get("default_baseline", 500.0),
            "safety_stock": DRUG_METADATA.get(drug_code, {}).get("default_safety", 75.0),
            "incoming_stock": 0.0,
            "lead_time_days": DRUG_METADATA.get(drug_code, {}).get("lead_time_days", 3),
            "reorder_threshold": 70.0,
        },
    )


def save_drug_to_supabase(item: Dict[str, Any]):
    """Saves/upserts drug inventory record to Supabase."""
    IN_MEMORY_INVENTORY[item["drug_code"]] = item
    try:
        sb = get_supabase()
        sb.table("inventory").upsert(item, on_conflict="drug_code").execute()
    except Exception as e:
        print(f"Notice: Supabase inventory save notice: {e}")


def reset_db():
    _init_in_memory_inventory()
    IN_MEMORY_TRANSACTIONS.clear()
    IN_MEMORY_BASELINE_HISTORY.clear()
    IN_MEMORY_ORDERS.clear()


def _get_forecast_demand(drug_code: str) -> Dict[str, float]:
    """
    Fetch forecast demand projections for 1 day, 7 days, 14 days, and lead time.
    Integrates with forecast_results or fallback calculations.
    """
    try:
        from ml_services.forecast_service import get_forecast_data
        recs = get_forecast_data(drug_code, year="2020")
        if recs and len(recs) >= 14:
            f1 = float(recs[0].get("p50_demand", 25.0))
            f7 = sum(float(r.get("p50_demand", 25.0)) for r in recs[:7])
            f14 = sum(float(r.get("p50_demand", 25.0)) for r in recs[:14])
            p90_7 = sum(float(r.get("p90_demand", 30.0)) for r in recs[:7])
            p10_7 = sum(float(r.get("p10_demand", 20.0)) for r in recs[:7])
            return {
                "tomorrow": round(f1, 1),
                "next_7_days": round(f7, 1),
                "next_14_days": round(f14, 1),
                "p90_7_days": round(p90_7, 1),
                "p10_7_days": round(p10_7, 1),
            }
    except Exception as e:
        print(f"Notice: forecast engine fallback for {drug_code}: {e}")
    
    # Fallback estimations based on drug baseline
    meta = DRUG_METADATA.get(drug_code, {})
    base = meta.get("default_baseline", 500.0)
    f7 = round(base * 0.70, 1)
    return {
        "tomorrow": round(f7 / 7.0, 1),
        "next_7_days": f7,
        "next_14_days": round(f7 * 1.9, 1),
        "p90_7_days": round(f7 * 1.15, 1),
        "p10_7_days": round(f7 * 0.85, 1),
    }


def evaluate_drug_inventory(drug_code: str) -> Dict[str, Any]:
    """
    Core Decision-Making Engine for a single drug using Supabase storage.
    Computes inventory position, target stock, consumption %, risk level, and recommended order quantity.
    """
    row = fetch_drug_from_supabase(drug_code)
    curr_stock = float(row["current_stock"])
    base_stock = float(row["baseline_stock"])
    safety_stock = float(row["safety_stock"])
    incoming_stock = float(row["incoming_stock"])
    lead_time = int(row["lead_time_days"])

    # 1. Consumption %
    consumed_qty = max(0.0, base_stock - curr_stock)
    consumed_pct = round((consumed_qty / base_stock * 100.0), 1) if base_stock > 0 else 0.0

    # 2. Inventory Position = Current Stock + Incoming Stock
    inventory_position = curr_stock + incoming_stock

    # 3. Forecast Projections
    fc = _get_forecast_demand(drug_code)
    forecast_7d = fc["next_7_days"]
    forecast_lead_time = round((fc["next_7_days"] / 7.0) * lead_time, 1)

    # 4. Target Stock Calculation
    # Target Stock = Baseline Stock + max(0, Forecast requirement beyond normal buffer) + Safety Stock
    forecast_adj = max(0.0, forecast_7d - (base_stock - safety_stock))
    target_stock = round(base_stock + forecast_adj + (safety_stock * 0.2), 1)

    # 5. Recommended Order Quantity = max(0, Target Stock - Inventory Position)
    recommended_order_qty = max(0.0, round(target_stock - inventory_position, 0))

    # 6. Risk Level & Status Determination
    reason = []
    if curr_stock <= 0:
        status = "OUT_OF_STOCK"
        risk_level = "CRITICAL"
        reason.append("Current stock is 0 units.")
    elif curr_stock < forecast_lead_time and incoming_stock == 0:
        status = "EMERGENCY_REPLENISHMENT"
        risk_level = "CRITICAL"
        reason.append(f"Current stock ({curr_stock}) cannot sustain expected lead-time demand ({forecast_lead_time} units over {lead_time} days). Emergency order needed before normal replenishment.")
    elif inventory_position < forecast_7d:
        status = "STOCKOUT_RISK"
        risk_level = "HIGH"
        reason.append(f"Forecast demand ({forecast_7d} units) exceeds total inventory position ({inventory_position} units).")
    elif consumed_pct >= 70.0:
        status = "REPLENISHMENT_RECOMMENDED"
        risk_level = "HIGH" if consumed_pct >= 80 else "MEDIUM"
        reason.append(f"{consumed_pct}% of baseline stock consumed (threshold 70%). Replenishment recommended.")
    elif consumed_pct >= 60.0:
        status = "WATCH"
        risk_level = "MEDIUM"
        reason.append(f"{consumed_pct}% of baseline stock consumed (threshold 60%). Watch closely and evaluate replenishment.")
    else:
        status = "HEALTHY"
        risk_level = "LOW"
        reason.append("Stock is sufficient to meet forecasted demand.")

    # 7. Baseline Recommendation Check
    # If 14-day forecast consistently exceeds 80% of baseline, suggest an updated baseline
    forecast_suggested_baseline = None
    if fc["next_14_days"] > (base_stock * 1.25):
        suggested_val = round(base_stock * 1.15, -1)
        forecast_suggested_baseline = {
            "current_baseline": base_stock,
            "suggested_baseline": suggested_val,
            "reason": f"Forecast demand for next 14 days ({fc['next_14_days']} units) is significantly higher than current baseline capacity ({base_stock})."
        }

    return {
        "drug_code": drug_code,
        "drug_name": DRUG_METADATA.get(drug_code, {}).get("name", drug_code),
        "category": DRUG_METADATA.get(drug_code, {}).get("category", "General"),
        "current_stock": curr_stock,
        "baseline_stock": base_stock,
        "safety_stock": safety_stock,
        "incoming_stock": incoming_stock,
        "lead_time_days": lead_time,
        "consumed_qty": round(consumed_qty, 1),
        "consumed_pct": consumed_pct,
        "inventory_position": round(inventory_position, 1),
        "forecast_demand": forecast_7d,
        "forecast_details": fc,
        "target_stock": target_stock,
        "recommended_order_qty": int(recommended_order_qty),
        "status": status,
        "risk_level": risk_level,
        "reason": " ".join(reason),
        "baseline_recommendation": forecast_suggested_baseline
    }


def get_all_inventory_overview() -> List[Dict[str, Any]]:
    """Returns inventory status and decision analysis for all 8 drugs."""
    return [evaluate_drug_inventory(code) for code in DRUG_METADATA.keys()]


def record_sale(drug_code: str, quantity: float, user_id: str = "pharmacist", notes: str = "") -> Dict[str, Any]:
    """Records a sale transaction, decreases current stock, and returns updated evaluation."""
    return record_inventory_transaction(drug_code, "SALE", quantity, user_id, notes)


def record_inventory_transaction(
    drug_code: str,
    transaction_type: str,
    quantity: float,
    user_id: str = "pharmacist",
    notes: str = ""
) -> Dict[str, Any]:
    """Executes an inventory transaction using Supabase storage."""
    tx_type = transaction_type.upper()
    inv = fetch_drug_from_supabase(drug_code)
    stock_before = float(inv["current_stock"])
    incoming = float(inv["incoming_stock"])

    if tx_type in ["SALE", "DAMAGE", "EXPIRY"]:
        stock_after = max(0.0, stock_before - quantity)
    elif tx_type in ["RESTOCK", "RETURN"]:
        stock_after = stock_before + quantity
        if incoming > 0:
            incoming = max(0.0, incoming - quantity)
    elif tx_type == "ADJUSTMENT":
        stock_after = max(0.0, quantity)
    else:
        stock_after = stock_before

    tx_id = f"tx_{tx_type.lower()}_{drug_code}_{int(datetime.datetime.now().timestamp())}"
    tx_record = {
        "id": tx_id,
        "drug_code": drug_code,
        "transaction_type": tx_type,
        "quantity": quantity,
        "stock_before": stock_before,
        "stock_after": stock_after,
        "timestamp": datetime.datetime.now().isoformat(),
        "user_id": user_id,
        "notes": notes,
    }

    IN_MEMORY_TRANSACTIONS.insert(0, tx_record)
    inv["current_stock"] = stock_after
    inv["incoming_stock"] = incoming
    save_drug_to_supabase(inv)

    try:
        sb = get_supabase()
        sb.table("inventory_transactions").upsert(tx_record, on_conflict="id").execute()
    except Exception as e:
        print(f"Notice: Supabase transaction log notice: {e}")

    return evaluate_drug_inventory(drug_code)


def update_baseline_stock(
    drug_code: str,
    new_baseline: float,
    source: str = "MANUAL",
    reason: str = "Manual adjustment",
    changed_by: str = "pharmacist",
    status: str = "MANUAL_UPDATE"
) -> Dict[str, Any]:
    """Updates drug baseline stock in Supabase."""
    inv = fetch_drug_from_supabase(drug_code)
    old_baseline = float(inv["baseline_stock"])
    hist_id = f"hist_{drug_code}_{int(datetime.datetime.now().timestamp())}"
    hist_record = {
        "id": hist_id,
        "drug_code": drug_code,
        "old_baseline": old_baseline,
        "new_baseline": new_baseline,
        "source": source,
        "reason": reason,
        "changed_by": changed_by,
        "status": status,
        "changed_at": datetime.datetime.now().isoformat(),
    }

    IN_MEMORY_BASELINE_HISTORY.insert(0, hist_record)
    inv["baseline_stock"] = new_baseline
    save_drug_to_supabase(inv)

    try:
        sb = get_supabase()
        sb.table("baseline_history").upsert(hist_record, on_conflict="id").execute()
    except Exception as e:
        print(f"Notice: Supabase baseline history notice: {e}")

    return evaluate_drug_inventory(drug_code)


def create_replenishment_order(
    drug_code: str,
    quantity: float,
    approved_by: str = "pharmacist",
    reason: str = "Replenishment Recommendation Approved"
) -> Dict[str, Any]:
    """Generates a Replenishment Order stored in Supabase."""
    order_id = f"ORD-{drug_code}-{int(datetime.datetime.now().timestamp())}"
    lead_time = DRUG_METADATA.get(drug_code, {}).get("lead_time_days", 3)
    expected_arrival = (datetime.date.today() + datetime.timedelta(days=lead_time)).isoformat()

    order_record = {
        "id": order_id,
        "drug_code": drug_code,
        "quantity": quantity,
        "order_date": datetime.datetime.now().isoformat(),
        "expected_arrival": expected_arrival,
        "status": "PENDING_VENDOR",
        "approved_by": approved_by,
        "reason": reason,
        "vendor_notes": "",
    }

    IN_MEMORY_ORDERS.insert(0, order_record)
    inv = fetch_drug_from_supabase(drug_code)
    inv["incoming_stock"] = float(inv["incoming_stock"]) + quantity
    save_drug_to_supabase(inv)

    try:
        sb = get_supabase()
        sb.table("replenishment_orders").upsert(order_record, on_conflict="id").execute()
    except Exception as e:
        print(f"Notice: Supabase replenishment order notice: {e}")

    return {
        "order_id": order_id,
        "drug_code": drug_code,
        "quantity": quantity,
        "status": "PENDING_VENDOR",
        "expected_arrival": expected_arrival,
        "approved_by": approved_by,
        "message": f"Replenishment order for {quantity} units of {drug_code} dispatched."
    }


def get_vendor_orders(status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns replenishment orders from Supabase or memory."""
    try:
        sb = get_supabase()
        q = sb.table("replenishment_orders").select("*")
        if status_filter:
            q = q.eq("status", status_filter.upper())
        res = q.execute()
        if res.data:
            orders = []
            for r in res.data:
                meta = DRUG_METADATA.get(r["drug_code"], {})
                orders.append({
                    "order_id": r["id"],
                    "drug_code": r["drug_code"],
                    "drug_name": meta.get("name", r["drug_code"]),
                    "category": meta.get("category", "General"),
                    "quantity": float(r["quantity"]),
                    "order_date": r.get("order_date", ""),
                    "expected_arrival": r.get("expected_arrival", ""),
                    "status": r["status"],
                    "approved_by": r.get("approved_by", "pharmacist"),
                    "reason": r.get("reason", ""),
                    "vendor_notes": r.get("vendor_notes", "")
                })
            return orders
    except Exception as e:
        print(f"Notice: Supabase vendor orders fetch notice: {e}")

    filtered = IN_MEMORY_ORDERS
    if status_filter:
        filtered = [o for o in IN_MEMORY_ORDERS if o["status"] == status_filter.upper()]
    return filtered


def update_vendor_order_status(order_id: str, new_status: str, vendor_notes: str = "") -> Dict[str, Any]:
    """Vendor updates order status in Supabase."""
    status_upper = new_status.upper()
    try:
        sb = get_supabase()
        sb.table("replenishment_orders").update({"status": status_upper, "vendor_notes": vendor_notes}).eq("id", order_id).execute()
    except Exception as e:
        print(f"Notice: Supabase order status update notice: {e}")

    for o in IN_MEMORY_ORDERS:
        if o["id"] == order_id:
            old_status = o["status"]
            o["status"] = status_upper
            o["vendor_notes"] = vendor_notes
            drug_code = o["drug_code"]
            qty = float(o["quantity"])

            if status_upper == "DELIVERED" and old_status != "DELIVERED":
                inv = fetch_drug_from_supabase(drug_code)
                inv["current_stock"] = float(inv["current_stock"]) + qty
                inv["incoming_stock"] = max(0.0, float(inv["incoming_stock"]) - qty)
                save_drug_to_supabase(inv)

            return {
                "order_id": order_id,
                "drug_code": drug_code,
                "quantity": qty,
                "old_status": old_status,
                "new_status": status_upper,
                "vendor_notes": vendor_notes,
            }

    return {"order_id": order_id, "new_status": status_upper}


def get_transaction_history(drug_code: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Fetches transaction logs from Supabase."""
    try:
        sb = get_supabase()
        q = sb.table("inventory_transactions").select("*")
        if drug_code:
            q = q.eq("drug_code", drug_code.upper())
        res = q.order("timestamp", desc=True).limit(limit).execute()
        if res.data:
            return res.data
    except Exception as e:
        print(f"Notice: Supabase transaction log fetch notice: {e}")

    if drug_code:
        return [t for t in IN_MEMORY_TRANSACTIONS if t["drug_code"].upper() == drug_code.upper()][:limit]
    return IN_MEMORY_TRANSACTIONS[:limit]


def get_baseline_history(drug_code: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetches baseline history from Supabase."""
    try:
        sb = get_supabase()
        q = sb.table("baseline_history").select("*")
        if drug_code:
            q = q.eq("drug_code", drug_code.upper())
        res = q.order("changed_at", desc=True).execute()
        if res.data:
            return res.data
    except Exception as e:
        print(f"Notice: Supabase baseline history fetch notice: {e}")

    if drug_code:
        return [b for b in IN_MEMORY_BASELINE_HISTORY if b["drug_code"].upper() == drug_code.upper()]
    return IN_MEMORY_BASELINE_HISTORY


def get_sunday_replenishment_review() -> List[Dict[str, Any]]:
    """Sunday Replenishment Review matrix."""
    overview = get_all_inventory_overview()
    review_list = []
    for item in overview:
        recommendation_action = "Maintain"
        if item["status"] in ["EMERGENCY_REPLENISHMENT", "OUT_OF_STOCK"]:
            recommendation_action = "Emergency Reorder"
        elif item["status"] in ["REPLENISHMENT_RECOMMENDED", "STOCKOUT_RISK"]:
            recommendation_action = "Reorder"
        elif item["status"] == "WATCH":
            recommendation_action = "Review & Monitor"

        review_list.append({
            "drug_code": item["drug_code"],
            "drug_name": item["drug_name"],
            "baseline_stock": item["baseline_stock"],
            "current_stock": item["current_stock"],
            "incoming_stock": item["incoming_stock"],
            "consumed_pct": item["consumed_pct"],
            "forecast_risk": item["risk_level"],
            "status": item["status"],
            "recommendation_action": recommendation_action,
            "recommended_order_qty": item["recommended_order_qty"],
            "target_stock": item["target_stock"]
        })
    return review_list
