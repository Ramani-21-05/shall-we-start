"""
routers/baselines.py
─────────────────────
Baseline Stock Alert System

Route ordering rules (FastAPI matches top-to-bottom):
  - Static paths (/alerts/unread-count, /alerts/read-all, /alerts/check)
    MUST come BEFORE dynamic paths (/alerts/{alert_id}/read)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.database import get_supabase
from typing import Optional
from routers.activity_logs import _write_log

router = APIRouter(prefix="/api", tags=["Baselines & Alerts"])

DRUGS = ['M01AB', 'M01AE', 'N02BA', 'N02BE', 'N05B', 'N05C', 'R03', 'R06']
DEFAULT_THRESHOLD_PCT = 70.0


# ── Pydantic models ───────────────────────────────────────────────────────────

class BaselineSet(BaseModel):
    baseline_stock: float
    threshold_pct: Optional[float] = DEFAULT_THRESHOLD_PCT


# ─────────────────────────────────────────────────────────────────────────────
# BASELINE ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/baselines")
def get_all_baselines():
    """Fetch all drug baselines."""
    try:
        supabase = get_supabase()
        res = supabase.table("stock_baselines").select("*").order("drug_code").execute()
        return res.data or []
    except Exception as e:
        print(f"Notice: Fetching stock_baselines: {e}")
        return []


@router.post("/baselines/{drug}")
def set_baseline(drug: str, body: BaselineSet):
    """Set or update the baseline stock for a drug."""
    drug_upper = drug.upper()
    if drug_upper not in DRUGS:
        raise HTTPException(status_code=400, detail=f"Unknown drug: {drug_upper}")
    if body.baseline_stock <= 0:
        raise HTTPException(status_code=400, detail="baseline_stock must be > 0")
    thr = body.threshold_pct or DEFAULT_THRESHOLD_PCT
    if not (1 <= thr <= 100):
        raise HTTPException(status_code=400, detail="threshold_pct must be 1-100")

    supabase = get_supabase()
    record = {
        "drug_code":      drug_upper,
        "baseline_stock": round(body.baseline_stock, 2),
        "threshold_pct":  thr,
    }
    supabase.table("stock_baselines").upsert(record, on_conflict="drug_code").execute()

    _write_log(
        event_type="BASELINE_STOCK_CHANGED",
        message=f"Baseline stock for '{drug_upper}' set to {round(body.baseline_stock, 2)} units (threshold: {thr}%).",
        username="system",
        user_role="SYSTEM",
        status="SUCCESS",
        detail=f"Drug: {drug_upper} | Baseline: {round(body.baseline_stock, 2)} | Threshold: {thr}%",
    )

    return {"status": "ok", "drug_code": drug_upper,
            "baseline_stock": body.baseline_stock, "threshold_pct": thr}


@router.get("/baselines/{drug}/suggest")
def suggest_baseline(drug: str, year: str = "2020"):
    """Auto-suggest a baseline from P90 TSL inventory data (smoothed)."""
    drug_upper = drug.upper()
    supabase = get_supabase()

    res = supabase.table("inventory_recommendations") \
        .select("target_stock_lvl") \
        .eq("drug_code", drug_upper) \
        .gte("recommendation_date", f"{year}-01-01") \
        .lte("recommendation_date", f"{year}-12-31") \
        .execute()

    rows = res.data or []
    tsl_values = sorted([float(r["target_stock_lvl"]) for r in rows if r.get("target_stock_lvl")])
    if not tsl_values:
        raise HTTPException(status_code=404, detail="No TSL data found")

    idx = int(len(tsl_values) * 0.90)
    suggested = round(tsl_values[idx], 1)

    existing_res = supabase.table("stock_baselines").select("baseline_stock") \
        .eq("drug_code", drug_upper).execute()
    existing = (existing_res.data or [{}])[0].get("baseline_stock")

    if existing:
        smoothed = round(0.8 * float(existing) + 0.2 * suggested, 1)
        return {"drug_code": drug_upper, "suggested": suggested, "smoothed": smoothed,
                "existing": existing, "method": "smoothed (80% existing + 20% forecast P90 TSL)"}

    return {"drug_code": drug_upper, "suggested": suggested, "smoothed": suggested,
            "existing": None, "method": "forecast P90 TSL (no prior baseline)"}


# ─────────────────────────────────────────────────────────────────────────────
# ALERT ENDPOINTS — static routes FIRST, then dynamic {alert_id} routes
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/alerts/unread-count")
def get_unread_count():
    """Fast unread alert count for the notification badge."""
    try:
        supabase = get_supabase()
        res = supabase.table("stock_alerts").select("id", count="exact") \
            .eq("is_read", False).execute()
        return {"count": res.count if hasattr(res, 'count') else len(res.data)}
    except Exception as e:
        return {"count": 0}


@router.patch("/alerts/read-all")
def mark_all_read():
    """Mark all alerts as read."""
    try:
        supabase = get_supabase()
        supabase.table("stock_alerts").update({"is_read": True}).eq("is_read", False).execute()
    except Exception:
        pass
    return {"status": "ok"}


@router.post("/alerts/check")
def check_all_alerts(year: str = "2020"):
    """
    Batch alert check: compare simulated_inventory vs each drug baseline.
    Efficiently fetches existing alert dates in one query per drug to avoid N+1.
    """
    try:
        supabase = get_supabase()

        baselines_res = supabase.table("stock_baselines").select("*").execute()
        baselines = {r["drug_code"]: r for r in (baselines_res.data or [])}
        if not baselines:
            return {"status": "no_baselines", "message": "Set at least one baseline first"}

        created_count = 0
        skipped_count = 0
        new_alerts = []

        for drug_code, bl in baselines.items():
            baseline     = float(bl["baseline_stock"])
            threshold_pct = float(bl.get("threshold_pct", DEFAULT_THRESHOLD_PCT))
            alert_level  = baseline * (threshold_pct / 100.0)

            # Fetch all 2020 inventory rows
            inv_res = supabase.table("inventory_recommendations") \
                .select("recommendation_date,simulated_inventory") \
                .eq("drug_code", drug_code) \
                .gte("recommendation_date", f"{year}-01-01") \
                .lte("recommendation_date", f"{year}-12-31") \
                .execute()
            inv_rows = inv_res.data or []

            # Collect dates that breach threshold
            breach_rows = [
                r for r in inv_rows
                if float(r.get("simulated_inventory", 0)) < alert_level
            ]
            if not breach_rows:
                continue

            # Fetch already-alerted dates in ONE query (batch dedup)
            existing_res = supabase.table("stock_alerts") \
                .select("alert_date") \
                .eq("drug_code", drug_code) \
                .gte("alert_date", f"{year}-01-01") \
                .lte("alert_date", f"{year}-12-31") \
                .execute()
            existing_dates = {str(r["alert_date"])[:10] for r in (existing_res.data or [])}

            # Build new alert records (skip existing)
            to_insert = []
            for row in breach_rows:
                alert_date = str(row["recommendation_date"])[:10]
                if alert_date in existing_dates:
                    skipped_count += 1
                    continue
                inv = float(row["simulated_inventory"])
                stock_pct = round((inv / baseline) * 100, 1) if baseline > 0 else 0
                to_insert.append({
                    "drug_code":           drug_code,
                    "alert_date":          alert_date,
                    "simulated_inventory": round(inv, 2),
                    "baseline_stock":      baseline,
                    "threshold_pct":       threshold_pct,
                    "stock_pct":           stock_pct,
                    "is_read":             False,
                })

            # Batch insert in chunks of 100
            if to_insert:
                batch_size = 100
                for i in range(0, len(to_insert), batch_size):
                    chunk = to_insert[i:i + batch_size]
                    supabase.table("stock_alerts").insert(chunk).execute()
                created_count += len(to_insert)
                new_alerts += [f"{drug_code}:{r['alert_date']} ({r['stock_pct']}%)" for r in to_insert]

        return {
            "status":  "ok",
            "created": created_count,
            "skipped": skipped_count,
            "sample_alerts": new_alerts[:20],
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/alerts")
def get_alerts(drug: Optional[str] = None, unread_only: bool = False, limit: int = 200):
    """Get all stock alerts, newest first."""
    try:
        supabase = get_supabase()
        query = supabase.table("stock_alerts").select("*") \
            .order("alert_date", desc=True).limit(limit)
        if drug:
            query = query.eq("drug_code", drug.upper())
        if unread_only:
            query = query.eq("is_read", False)
        res = query.execute()
        return res.data or []
    except Exception as e:
        return []


@router.patch("/alerts/{alert_id}/read")
def mark_read(alert_id: str):
    """Mark a single alert as read."""
    supabase = get_supabase()
    supabase.table("stock_alerts").update({"is_read": True}).eq("id", alert_id).execute()
    return {"status": "ok"}
