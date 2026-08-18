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
import sqlite3
import datetime
from typing import Dict, List, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "inventory_v2.db")

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


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # 1. Inventory table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            drug_code TEXT PRIMARY KEY,
            drug_name TEXT NOT NULL,
            category TEXT NOT NULL,
            current_stock REAL NOT NULL,
            baseline_stock REAL NOT NULL,
            safety_stock REAL NOT NULL,
            incoming_stock REAL NOT NULL DEFAULT 0.0,
            lead_time_days INTEGER NOT NULL DEFAULT 3,
            reorder_threshold REAL NOT NULL DEFAULT 70.0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Inventory Transactions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory_transactions (
            id TEXT PRIMARY KEY,
            drug_code TEXT NOT NULL,
            transaction_type TEXT NOT NULL, -- SALE, RESTOCK, RETURN, DAMAGE, EXPIRY, ADJUSTMENT
            quantity REAL NOT NULL,
            stock_before REAL NOT NULL,
            stock_after REAL NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_id TEXT NOT NULL,
            notes TEXT
        )
    """)

    # 3. Baseline History table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS baseline_history (
            id TEXT PRIMARY KEY,
            drug_code TEXT NOT NULL,
            old_baseline REAL NOT NULL,
            new_baseline REAL NOT NULL,
            source TEXT NOT NULL, -- MANUAL, FORECAST_RECOMMENDATION
            reason TEXT,
            changed_by TEXT NOT NULL,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL -- ACCEPTED, EDITED, REJECTED, MANUAL_UPDATE
        )
    """)

    # 4. Replenishment Orders table (Sent to Vendor Dashboard)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS replenishment_orders (
            id TEXT PRIMARY KEY,
            drug_code TEXT NOT NULL,
            quantity REAL NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expected_arrival DATE,
            status TEXT NOT NULL DEFAULT 'PENDING_VENDOR', -- PENDING_VENDOR, SHIPPED, DELIVERED, CANCELLED
            approved_by TEXT NOT NULL,
            reason TEXT,
            vendor_notes TEXT
        )
    """)

    # Seed default inventory if empty
    cursor.execute("SELECT COUNT(*) as cnt FROM inventory")
    row = cursor.fetchone()
    if row["cnt"] == 0:
        for code, meta in DRUG_METADATA.items():
            cursor.execute("""
                INSERT INTO inventory (drug_code, drug_name, category, current_stock, baseline_stock, safety_stock, incoming_stock, lead_time_days)
                VALUES (?, ?, ?, ?, ?, ?, 0.0, ?)
            """, (code, meta["name"], meta["category"], meta["default_stock"], meta["default_baseline"], meta["default_safety"], meta["lead_time_days"]))
            
            # Initial seed transaction
            tx_id = f"tx_init_{code}_{int(datetime.datetime.now().timestamp())}"
            cursor.execute("""
                INSERT INTO inventory_transactions (id, drug_code, transaction_type, quantity, stock_before, stock_after, user_id, notes)
                VALUES (?, ?, 'RESTOCK', ?, 0, ?, 'system', 'Initial Stock Setup')
            """, (tx_id, code, meta["default_stock"], meta["default_stock"]))
            
    conn.commit()
    conn.close()

# Initialize DB on module import
def reset_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS inventory")
    cursor.execute("DROP TABLE IF EXISTS inventory_transactions")
    cursor.execute("DROP TABLE IF EXISTS baseline_history")
    cursor.execute("DROP TABLE IF EXISTS replenishment_orders")
    conn.commit()
    conn.close()
    init_db()

init_db()


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
    Core Decision-Making Engine for a single drug.
    Computes inventory position, target stock, consumption %, risk level, and recommended order quantity.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inventory WHERE drug_code = ?", (drug_code,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        meta = DRUG_METADATA.get(drug_code, {"name": drug_code, "category": "General", "lead_time_days": 3, "default_baseline": 500, "default_safety": 75, "default_stock": 300})
        curr_stock = meta["default_stock"]
        base_stock = meta["default_baseline"]
        safety_stock = meta["default_safety"]
        incoming_stock = 0.0
        lead_time = meta["lead_time_days"]
    else:
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
    if quantity <= 0:
        raise ValueError("Sale quantity must be greater than 0")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT current_stock FROM inventory WHERE drug_code = ?", (drug_code,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Drug {drug_code} not found in inventory")

    stock_before = float(row["current_stock"])
    stock_after = max(0.0, stock_before - quantity)

    tx_id = f"tx_sale_{drug_code}_{int(datetime.datetime.now().timestamp())}"
    cursor.execute("""
        INSERT INTO inventory_transactions (id, drug_code, transaction_type, quantity, stock_before, stock_after, user_id, notes)
        VALUES (?, ?, 'SALE', ?, ?, ?, ?, ?)
    """, (tx_id, drug_code, quantity, stock_before, stock_after, user_id, notes or "Direct POS Sale"))

    cursor.execute("""
        UPDATE inventory SET current_stock = ?, updated_at = CURRENT_TIMESTAMP WHERE drug_code = ?
    """, (stock_after, drug_code))

    conn.commit()
    conn.close()

    return evaluate_drug_inventory(drug_code)


def record_inventory_transaction(
    drug_code: str,
    transaction_type: str, # SALE, RESTOCK, RETURN, DAMAGE, EXPIRY, ADJUSTMENT
    quantity: float,
    user_id: str = "pharmacist",
    notes: str = ""
) -> Dict[str, Any]:
    """
    Executes a formal inventory transaction:
    Current Stock = Opening Stock - Sales + Restocking + Returns - Damage - Expiry +- Adjustments
    """
    tx_type = transaction_type.upper()
    valid_types = ["SALE", "RESTOCK", "RETURN", "DAMAGE", "EXPIRY", "ADJUSTMENT"]
    if tx_type not in valid_types:
        raise ValueError(f"Invalid transaction type. Must be one of {valid_types}")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT current_stock, incoming_stock FROM inventory WHERE drug_code = ?", (drug_code,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Drug {drug_code} not found in inventory")

    stock_before = float(row["current_stock"])
    incoming = float(row["incoming_stock"])

    if tx_type in ["SALE", "DAMAGE", "EXPIRY"]:
        stock_after = max(0.0, stock_before - quantity)
    elif tx_type in ["RESTOCK", "RETURN"]:
        stock_after = stock_before + quantity
        # If restocking from incoming order, clear incoming stock
        if incoming > 0:
            incoming = max(0.0, incoming - quantity)
    elif tx_type == "ADJUSTMENT":
        stock_after = max(0.0, quantity) # Set absolute stock level
    else:
        stock_after = stock_before

    tx_id = f"tx_{tx_type.lower()}_{drug_code}_{int(datetime.datetime.now().timestamp())}"
    cursor.execute("""
        INSERT INTO inventory_transactions (id, drug_code, transaction_type, quantity, stock_before, stock_after, user_id, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (tx_id, drug_code, tx_type, quantity, stock_before, stock_after, user_id, notes))

    cursor.execute("""
        UPDATE inventory SET current_stock = ?, incoming_stock = ?, updated_at = CURRENT_TIMESTAMP WHERE drug_code = ?
    """, (stock_after, incoming, drug_code))

    conn.commit()
    conn.close()

    return evaluate_drug_inventory(drug_code)


def update_baseline_stock(
    drug_code: str,
    new_baseline: float,
    source: str = "MANUAL",
    reason: str = "Manual adjustment",
    changed_by: str = "pharmacist",
    status: str = "MANUAL_UPDATE"
) -> Dict[str, Any]:
    """Updates drug baseline stock and logs history."""
    if new_baseline <= 0:
        raise ValueError("Baseline stock must be greater than 0")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT baseline_stock FROM inventory WHERE drug_code = ?", (drug_code,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Drug {drug_code} not found")

    old_baseline = float(row["baseline_stock"])
    hist_id = f"hist_{drug_code}_{int(datetime.datetime.now().timestamp())}"

    cursor.execute("""
        INSERT INTO baseline_history (id, drug_code, old_baseline, new_baseline, source, reason, changed_by, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (hist_id, drug_code, old_baseline, new_baseline, source, reason, changed_by, status))

    cursor.execute("""
        UPDATE inventory SET baseline_stock = ?, updated_at = CURRENT_TIMESTAMP WHERE drug_code = ?
    """, (new_baseline, drug_code))

    conn.commit()
    conn.close()

    return evaluate_drug_inventory(drug_code)


def create_replenishment_order(
    drug_code: str,
    quantity: float,
    approved_by: str = "pharmacist",
    reason: str = "Replenishment Recommendation Approved"
) -> Dict[str, Any]:
    """
    Pharmacy member approves/edits replenishment recommendation.
    Generates a Replenishment Order sent to the Vendor Dashboard and increases incoming_stock.
    """
    if quantity <= 0:
        raise ValueError("Replenishment quantity must be > 0")

    conn = get_db()
    cursor = conn.cursor()
    
    order_id = f"ORD-{drug_code}-{int(datetime.datetime.now().timestamp())}"
    lead_time = DRUG_METADATA.get(drug_code, {}).get("lead_time_days", 3)
    expected_arrival = (datetime.date.today() + datetime.timedelta(days=lead_time)).isoformat()

    cursor.execute("""
        INSERT INTO replenishment_orders (id, drug_code, quantity, expected_arrival, status, approved_by, reason)
        VALUES (?, ?, ?, ?, 'PENDING_VENDOR', ?, ?)
    """, (order_id, drug_code, quantity, expected_arrival, approved_by, reason))

    # Increase incoming stock on order approval
    cursor.execute("""
        UPDATE inventory SET incoming_stock = incoming_stock + ?, updated_at = CURRENT_TIMESTAMP WHERE drug_code = ?
    """, (quantity, drug_code))

    conn.commit()
    conn.close()

    return {
        "order_id": order_id,
        "drug_code": drug_code,
        "quantity": quantity,
        "status": "PENDING_VENDOR",
        "expected_arrival": expected_arrival,
        "approved_by": approved_by,
        "message": f"Replenishment order for {quantity} units of {drug_code} dispatched to Vendor Dashboard."
    }


def get_vendor_orders(status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """Vendor Dashboard query: Returns all incoming replenishment orders placed by the pharmacy."""
    conn = get_db()
    cursor = conn.cursor()
    query = "SELECT * FROM replenishment_orders"
    params = []
    if status_filter:
        query += " WHERE status = ?"
        params.append(status_filter.upper())
    query += " ORDER BY order_date DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    orders = []
    for r in rows:
        d_code = r["drug_code"]
        meta = DRUG_METADATA.get(d_code, {})
        orders.append({
            "order_id": r["id"],
            "drug_code": d_code,
            "drug_name": meta.get("name", d_code),
            "category": meta.get("category", "General"),
            "quantity": float(r["quantity"]),
            "order_date": r["order_date"],
            "expected_arrival": r["expected_arrival"],
            "status": r["status"],
            "approved_by": r["approved_by"],
            "reason": r["reason"],
            "vendor_notes": r["vendor_notes"] or ""
        })
    return orders


def update_vendor_order_status(
    order_id: str,
    new_status: str, # SHIPPED, DELIVERED, CANCELLED
    vendor_notes: str = ""
) -> Dict[str, Any]:
    """
    Vendor updates order status.
    If DELIVERED: Triggers automatic restocking of current inventory and clears incoming stock.
    """
    status_upper = new_status.upper()
    valid_statuses = ["SHIPPED", "DELIVERED", "CANCELLED"]
    if status_upper not in valid_statuses:
        raise ValueError(f"Invalid vendor status. Must be one of {valid_statuses}")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM replenishment_orders WHERE id = ?", (order_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Order {order_id} not found")

    old_status = row["status"]
    drug_code = row["drug_code"]
    qty = float(row["quantity"])

    cursor.execute("""
        UPDATE replenishment_orders SET status = ?, vendor_notes = ? WHERE id = ?
    """, (status_upper, vendor_notes, order_id))

    # If order is now DELIVERED and wasn't already delivered
    if status_upper == "DELIVERED" and old_status != "DELIVERED":
        # Get current stock & incoming stock
        cursor.execute("SELECT current_stock, incoming_stock FROM inventory WHERE drug_code = ?", (drug_code,))
        inv_row = cursor.fetchone()
        if inv_row:
            curr_stock = float(inv_row["current_stock"])
            inc_stock = float(inv_row["incoming_stock"])
            new_curr = curr_stock + qty
            new_inc = max(0.0, inc_stock - qty)

            tx_id = f"tx_restock_{drug_code}_{int(datetime.datetime.now().timestamp())}"
            cursor.execute("""
                INSERT INTO inventory_transactions (id, drug_code, transaction_type, quantity, stock_before, stock_after, user_id, notes)
                VALUES (?, ?, 'RESTOCK', ?, ?, ?, 'vendor', ?)
            """, (tx_id, drug_code, qty, curr_stock, new_curr, f"Shipment Delivered for Order {order_id}"))

            cursor.execute("""
                UPDATE inventory SET current_stock = ?, incoming_stock = ?, updated_at = CURRENT_TIMESTAMP WHERE drug_code = ?
            """, (new_curr, new_inc, drug_code))

    conn.commit()
    conn.close()

    return {
        "order_id": order_id,
        "drug_code": drug_code,
        "quantity": qty,
        "old_status": old_status,
        "new_status": status_upper,
        "vendor_notes": vendor_notes
    }


def get_transaction_history(drug_code: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Fetches inventory audit transaction logs."""
    conn = get_db()
    cursor = conn.cursor()
    query = "SELECT * FROM inventory_transactions"
    params = []
    if drug_code:
        query += " WHERE drug_code = ?"
        params.append(drug_code.upper())
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_baseline_history(drug_code: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetches baseline change audit history."""
    conn = get_db()
    cursor = conn.cursor()
    query = "SELECT * FROM baseline_history"
    params = []
    if drug_code:
        query += " WHERE drug_code = ?"
        params.append(drug_code.upper())
    query += " ORDER BY changed_at DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_sunday_replenishment_review() -> List[Dict[str, Any]]:
    """
    Sunday Replenishment Cycle:
    Scans ALL 8 drugs regardless of stock levels and generates a full replenishment review matrix.
    """
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
