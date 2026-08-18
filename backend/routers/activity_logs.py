"""
routers/activity_logs.py
────────────────────────
Activity Audit Log Router.

Logs every significant system event:
  - LOGIN / LOGOUT
  - API calls (page loads, data fetches)
  - Errors / failed auth
  - Admin provisioning actions
  - Simulation actions (step, approve order, reset)

Stores in Supabase ctivity_logs table.
ADMIN-only read access via GET /api/logs endpoint.
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from core.database import get_supabase
from core.auth_middleware import get_current_user, require_roles

router = APIRouter(prefix="/api/logs", tags=["Activity Logs"])

SUPABASE_TABLE = "activity_logs"


class ActivityLogEntry(BaseModel):
    event_type: str
    username: Optional[str] = None
    user_role: Optional[str] = None
    message: str
    detail: Optional[str] = None
    status: str = "SUCCESS"
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


def _write_log(
    event_type: str,
    message: str,
    username: Optional[str] = None,
    user_role: Optional[str] = None,
    detail: Optional[str] = None,
    status: str = "SUCCESS",
):
    try:
        sb = get_supabase()
        sb.table(SUPABASE_TABLE).insert({
            "event_type": event_type,
            "username": username or "system",
            "user_role": user_role or "SYSTEM",
            "message": message,
            "detail": detail or "",
            "status": status,
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception:
        pass


@router.post("/write")
def write_log(entry: ActivityLogEntry):
    try:
        sb = get_supabase()
        sb.table(SUPABASE_TABLE).insert({
            "event_type": entry.event_type,
            "username": entry.username or "anonymous",
            "user_role": entry.user_role or "UNKNOWN",
            "message": entry.message,
            "detail": entry.detail or "",
            "status": entry.status,
            "ip_address": entry.ip_address or "",
            "user_agent": entry.user_agent or "",
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception:
        pass
    return {"ok": True}


@router.get("/")
def get_activity_logs(
    limit: int = Query(200, ge=1, le=1000),
    event_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    username: Optional[str] = Query(None),
    current_user: dict = Depends(require_roles(["ADMIN"])),
):
    sb = get_supabase()
    query = sb.table(SUPABASE_TABLE).select("*").order("created_at", desc=True).limit(limit)
    if event_type:
        query = query.eq("event_type", event_type)
    if status:
        query = query.eq("status", status)
    if username:
        query = query.ilike("username", f"%{username}%")
    res = query.execute()
    return {
        "logs": res.data or [],
        "total": len(res.data or []),
        "filters": {"event_type": event_type, "status": status, "username": username},
    }


@router.get("/summary")
def get_log_summary(current_user: dict = Depends(require_roles(["ADMIN"]))):
    sb = get_supabase()
    res = sb.table(SUPABASE_TABLE).select("event_type, status").execute()
    rows = res.data or []
    summary: dict = {}
    for row in rows:
        et = row.get("event_type", "UNKNOWN")
        st = row.get("status", "UNKNOWN")
        summary.setdefault(et, {"SUCCESS": 0, "ERROR": 0, "WARNING": 0, "INFO": 0, "total": 0})
        summary[et][st] = summary[et].get(st, 0) + 1
        summary[et]["total"] += 1
    return {"summary": summary, "total_events": len(rows)}
