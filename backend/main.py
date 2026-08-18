"""
PharmaCast — Pharmaceutical Demand Forecasting & Decision-Support Platform
FastAPI Backend Entry Point
"""
import threading
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from routers import products, models, forecast, explain, inventory, dashboard, baselines, inventory_v2, vendor, simulation, history, strategy, auth, activity_logs

RPC_SQL = """
CREATE OR REPLACE FUNCTION get_drug_monthly_totals(p_drug_code TEXT)
RETURNS TABLE(year INTEGER, month INTEGER, total_sales FLOAT)
LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  RETURN QUERY EXECUTE format(
    'SELECT "Year"::INTEGER, "Month"::INTEGER,
            ROUND(SUM(%I)::NUMERIC, 2)::FLOAT AS total_sales
     FROM sales_hourly
     WHERE "Year" BETWEEN 2014 AND 2019
     GROUP BY "Year", "Month"
     ORDER BY "Year", "Month"',
    p_drug_code
  );
END;
$$;
GRANT EXECUTE ON FUNCTION get_drug_monthly_totals(TEXT) TO anon, authenticated;
"""

def _startup_warm():
    """
    Background thread: runs after server starts.
    1. Tries to create the fast Supabase RPC if not already deployed.
    2. Pre-loads all 8 drugs into the history in-memory cache IN PARALLEL.
       All 8 fetches run simultaneously, so total time ≈ slowest single drug.
    """
    try:
        from core.database import get_supabase
        sb = get_supabase()
        try:
            sb.rpc("query", {"query": RPC_SQL}).execute()
            print("✓ History RPC function deployed/refreshed in Supabase.")
        except Exception:
            pass  # Already exists or no exec rights — paginated fallback handles it
    except Exception as e:
        print(f"Notice: RPC deploy skipped: {e}")

    print("⏳ Warming history cache for all 8 drugs in parallel…")
    from routers.history import _load_raw_data, DRUGS
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _warm_one(drug):
        try:
            _load_raw_data(drug)
            return drug, None
        except Exception as e:
            return drug, str(e)

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_warm_one, d): d for d in DRUGS}
        for f in as_completed(futures):
            drug, err = f.result()
            if err:
                print(f"  ✗ {drug}: {err}")
            else:
                print(f"  ✓ Cached {drug}")

    print("✅ History cache warm complete — all drug switches now instant.")

    # Check activity_logs table exists
    try:
        from core.database import get_supabase as _sb
        sb2 = _sb()
        sb2.table("activity_logs").select("id").limit(1).execute()
        print("✓ activity_logs table found in Supabase.")
    except Exception as e:
        print(
            "\n⚠️  NOTICE: 'activity_logs' table not found in Supabase!\n"
            "   Please run: backend/database/setup/04_activity_logs.sql in Supabase > SQL Editor\n"
            f"   Error: {e}\n"
        )



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the cache-warming thread immediately (non-blocking)
    t = threading.Thread(target=_startup_warm, daemon=True)
    t.start()
    yield  # app runs here


app = FastAPI(
    title="PharmaCast API",
    description=(
        "Pharmaceutical Demand Forecasting, Explainability, Anomaly Detection "
        "& Forecast-Driven Inventory Management Platform.\n\n"
        "**Training cutoff**: All models trained on 2014–2018 data only.\n"
        "**2019 data**: Reserved exclusively for anomaly detection & holdout evaluation."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# ── Request Audit Logging Middleware ──────────────────────────────────────────
# Logs every API call to the activity_logs table in Supabase.
# Skips read-heavy GETs and noisy health/docs paths to keep logs meaningful.

SKIP_LOG_PATHS = {
    "/", "/health", "/docs", "/openapi.json", "/redoc",
    "/api/logs/write",  # Prevent recursive log-of-log
}

LOG_ONLY_MUTATIONS = True  # Set False to also log all GET requests

@app.middleware("http")
async def request_audit_logger(request: Request, call_next):
    path = request.url.path
    method = request.method

    # Skip noisy paths and (if configured) GET-only reads
    if path in SKIP_LOG_PATHS:
        return await call_next(request)
    if LOG_ONLY_MUTATIONS and method == "GET":
        return await call_next(request)

    start_time = time.time()
    try:
        response = await call_next(request)
    except Exception as exc:
        # If an unhandled error happens, let it be handled by standard handlers
        raise exc

    duration_ms = round((time.time() - start_time) * 1000)
    status_code = response.status_code
    log_status = "SUCCESS" if status_code < 400 else ("WARNING" if status_code < 500 else "ERROR")

    # Try to extract username from Authorization header
    username = "anonymous"
    user_role = "UNKNOWN"
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            from core.security import decode_access_token
            payload = decode_access_token(auth_header[7:])
            if payload:
                username = payload.get("username", "anonymous")
                user_role = payload.get("role", "UNKNOWN")
        except Exception:
            pass

    try:
        from routers.activity_logs import _write_log
        _write_log(
            event_type="API_CALL",
            message=f"{method} {path} → {status_code} ({duration_ms}ms)",
            username=username,
            user_role=user_role,
            status=log_status,
            detail=f"Method: {method} | Path: {path} | Status: {status_code} | Duration: {duration_ms}ms",
        )
    except Exception:
        pass  # Never break the request flow

    return response

# CORS — allow all origins including Vercel and local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register all routers
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(models.router)
app.include_router(forecast.router)
app.include_router(explain.router)
app.include_router(inventory.router)
app.include_router(inventory_v2.router)
app.include_router(vendor.router)
app.include_router(dashboard.router)
app.include_router(baselines.router)
app.include_router(simulation.router)
app.include_router(history.router)
app.include_router(strategy.router)
app.include_router(activity_logs.router)


@app.get("/", tags=["Health"])
def root():
    return {
        "service": "PharmaCast API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "drugs": ["M01AB", "M01AE", "N02BA", "N02BE", "N05B", "N05C", "R03", "R06"],
        "training_cutoff": "2018-12-31",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
