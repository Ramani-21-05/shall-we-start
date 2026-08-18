"""
routers/history.py
──────────────────
Historical Sales Analytics (2014–2019) — Supabase only.

Performance strategy (fastest → slowest):
  1. In-memory module cache   → instant on repeat requests (no network)
  2. Supabase RPC             → 1 HTTP call, returns 72 aggregated rows
  3. Supabase paginated fetch → fallback if RPC not yet deployed

Run supabase_history_rpc.sql once in Supabase SQL Editor to enable path 2.
"""

from fastapi import APIRouter, HTTPException
from core.database import get_supabase

router = APIRouter(prefix="/api/history", tags=["History"])

DRUGS = ['M01AB', 'M01AE', 'N02BA', 'N02BE', 'N05B', 'N05C', 'R03', 'R06']

DRUG_NAMES = {
    'M01AB': 'Anti-inflammatory (Acetic acid)',
    'M01AE': 'Anti-inflammatory (Propionic acid)',
    'N02BA': 'Analgesic & Antipyretic (Salicylic)',
    'N02BE': 'Analgesic & Antipyretic (Pyrazolones)',
    'N05B':  'Psycholeptics (Anxiolytics)',
    'N05C':  'Psycholeptics (Hypnotics & Sedatives)',
    'R03':   'Respiratory (Obstructive airway)',
    'R06':   'Respiratory (Antihistamines)',
}

MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
YEARS = [2014, 2015, 2016, 2017, 2018, 2019]

# ── In-memory cache: populated on first request, never expires (static data) ──
_cache: dict[str, list] = {}


def _fetch_via_rpc(drug_upper: str) -> list | None:
    """
    Fast path: call the Postgres RPC function that does GROUP BY server-side.
    Returns 72 rows in ONE HTTP request instead of 51+ paginated calls.
    Returns None if the function hasn't been deployed yet.
    """
    try:
        supabase = get_supabase()
        res = supabase.rpc(
            "get_drug_monthly_totals",
            {"p_drug_code": drug_upper}
        ).execute()

        rows = res.data or []
        if not rows:
            return None

        return [
            {
                "year": int(r["year"]),
                "month": int(r["month"]),
                "total_sales": float(r["total_sales"]),
            }
            for r in sorted(rows, key=lambda r: (r["year"], r["month"]))
        ]
    except Exception as e:
        print(f"History RPC not available for {drug_upper} ({e}), trying paginated fetch…")
        return None


def _fetch_paginated(drug_upper: str) -> list:
    """
    Fallback path: paginated SELECT if the RPC hasn't been deployed.
    Fetches Year, Month, and ALL 8 drug columns in one paginated scan.
    Populates _cache for all 8 drugs simultaneously.
    Note: Supabase PostgREST max row limit per request is 1000.
    """
    supabase = get_supabase()
    drugs_to_fetch = DRUGS if drug_upper in DRUGS else [drug_upper]
    
    # Store temporary aggregations per drug
    temp_cache: dict[str, dict[tuple, float]] = {d: {} for d in drugs_to_fetch}
    offset = 0
    PAGE = 1000  # PostgREST maximum limit is 1000 rows per request

    cols = '"Year","Month",' + ','.join([f'"{d}"' for d in drugs_to_fetch])

    while True:
        res = (
            supabase.table("sales_hourly")
            .select(cols)
            .gte("datum", "2014-01-01T00:00:00")
            .lte("datum", "2019-12-31T23:59:59")
            .range(offset, offset + PAGE - 1)
            .execute()
        )
        batch = res.data or []
        for row in batch:
            y = row.get("Year")
            m = row.get("Month")
            if y and m:
                key = (int(y), int(m))
                for d in drugs_to_fetch:
                    val = float(row.get(d, 0.0) or 0.0)
                    temp_cache[d][key] = temp_cache[d].get(key, 0.0) + val
        if len(batch) < PAGE:
            break
        offset += PAGE

    # Store aggregated rows in _cache for all drugs
    for d, monthly_map in temp_cache.items():
        _cache[d] = [
            {"year": k[0], "month": k[1], "total_sales": round(v, 2)}
            for k, v in sorted(monthly_map.items())
        ]

    return _cache.get(drug_upper, [])


def _fetch_from_dataset() -> dict[str, list]:
    """Load and aggregate monthly sales from dataset CSV to match Dashboard 100%."""
    import os, pandas as pd
    from core.ml_paths import BASE_DIR
    csv_path = os.path.join(BASE_DIR, "times_series", "dataset", "saleshourly.csv")
    if not os.path.exists(csv_path):
        return {}
    try:
        df = pd.read_csv(csv_path)
        df["datum_dt"] = pd.to_datetime(df["datum"])
        df["Year"] = df["datum_dt"].dt.year
        df["Month"] = df["datum_dt"].dt.month

        local_cache = {}
        for drug in DRUGS:
            if drug in df.columns:
                g = df.groupby(["Year", "Month"])[drug].sum()
                records = []
                for (y, m), val in g.items():
                    records.append({"year": int(y), "month": int(m), "total_sales": round(float(val), 2)})
                local_cache[drug] = sorted(records, key=lambda r: (r["year"], r["month"]))
        return local_cache
    except Exception as e:
        print(f"Notice: local dataset load fallback: {e}")
        return {}


def _load_raw_data(drug_upper: str) -> list:
    """
    Returns monthly totals for 2014-2019 for the given drug.
    Order of preference:
      1. Module-level in-memory cache (instant, no network)
      2. Local hourly dataset aggregation (instant, 100% match with Dashboard)
      3. Supabase RPC / Paginated query fallback
    """
    if drug_upper in _cache and _cache[drug_upper]:
        return _cache[drug_upper]

    # Try fast dataset aggregation first to match Dashboard 100%
    dataset_cache = _fetch_from_dataset()
    if dataset_cache:
        for d, recs in dataset_cache.items():
            _cache[d] = recs
        if drug_upper in _cache:
            return _cache[drug_upper]

    # Try RPC next
    raw = _fetch_via_rpc(drug_upper)

    # Fallback to paginated if RPC not available
    if raw is None or not raw:
        raw = _fetch_paginated(drug_upper)

    return raw


def _build_analytics(drug_upper: str, raw: list) -> dict:
    """Compute trend, seasonality, YoY, and summary from monthly totals."""
    # Monthly time series
    monthly_series = [
        {
            "label": f"{r['year']}-{str(r['month']).zfill(2)}",
            "year": r["year"],
            "month": r["month"],
            "total_sales": r["total_sales"],
            "month_name": MONTH_NAMES[r["month"] - 1],
        }
        for r in raw
    ]

    # Year-over-year annual totals
    yoy: dict[int, float] = {}
    for r in raw:
        yoy[r["year"]] = yoy.get(r["year"], 0.0) + r["total_sales"]
    yoy_series = [
        {"year": y, "total_sales": round(v, 2), "growth_pct": None}
        for y, v in sorted(yoy.items())
    ]
    for i in range(1, len(yoy_series)):
        prev = yoy_series[i - 1]["total_sales"]
        curr = yoy_series[i]["total_sales"]
        yoy_series[i]["growth_pct"] = round((curr - prev) / prev * 100, 2) if prev else None

    # Seasonality: avg per calendar month across all years
    month_totals: dict[int, list] = {m: [] for m in range(1, 13)}
    for r in raw:
        month_totals[r["month"]].append(r["total_sales"])

    season_avg = {m: (sum(v) / len(v) if v else 0.0) for m, v in month_totals.items()}
    grand_avg = sum(season_avg.values()) / 12 if season_avg else 1.0
    seasonality = [
        {
            "month": m,
            "month_name": MONTH_NAMES[m - 1],
            "avg_sales": round(season_avg[m], 2),
            "index": round(season_avg[m] / grand_avg, 4) if grand_avg else 1.0,
        }
        for m in range(1, 13)
    ]

    # Year breakdown per month for grouped bar chart
    year_breakdown: dict[int, dict[int, float]] = {}
    for r in raw:
        yr, mo = r["year"], r["month"]
        if yr not in year_breakdown:
            year_breakdown[yr] = {}
        year_breakdown[yr][mo] = r["total_sales"]

    yoy_monthly = [
        {
            "month": m,
            "month_name": MONTH_NAMES[m - 1],
            **{str(y): round(year_breakdown.get(y, {}).get(m, 0.0), 2) for y in YEARS}
        }
        for m in range(1, 13)
    ]

    # Summary stats
    all_vals = [r["total_sales"] for r in raw]
    peak_idx = all_vals.index(max(all_vals)) if all_vals else 0
    summary = {
        "drug_code": drug_upper,
        "drug_name": DRUG_NAMES.get(drug_upper, drug_upper),
        "years_covered": sorted(list({r["year"] for r in raw})),
        "total_records": len(raw),
        "overall_total": round(sum(all_vals), 2),
        "overall_avg_monthly": round(sum(all_vals) / len(all_vals), 2) if all_vals else 0,
        "overall_max_monthly": round(max(all_vals), 2) if all_vals else 0,
        "overall_min_monthly": round(min(all_vals), 2) if all_vals else 0,
        "peak_month": monthly_series[peak_idx]["label"] if all_vals else None,
        "annual_totals": {str(k): round(v, 2) for k, v in sorted(yoy.items())},
        "fetched_from_cache": drug_upper in _cache,
    }

    return {
        "summary": summary,
        "monthly_series": monthly_series,
        "yoy_series": yoy_series,
        "seasonality": seasonality,
        "yoy_monthly": yoy_monthly,
    }


# ── Portfolio Analytics ────────────────────────────────────────────────────────

def get_portfolio_analytics() -> dict:
    """
    Computes portfolio-level analytics aggregated across ALL 8 drugs:
      - monthly_series: combined monthly sales totals (2014-2019)
      - seasonality: average combined monthly sales & index per calendar month
      - highest_sales_drug: top selling drug metadata & totals
      - lowest_sales_drug: lowest selling drug metadata & totals
      - drug_shares: list of drugs with totals, avg monthly, % share of portfolio
    """
    drug_totals = {}
    combined_monthly = {}
    month_calendar_totals = {m: [] for m in range(1, 13)}

    for drug in DRUGS:
        try:
            raw = _load_raw_data(drug)
        except Exception as e:
            print(f"Portfolio analytics load note for {drug}: {e}")
            continue

        d_total = sum(r["total_sales"] for r in raw)
        drug_totals[drug] = round(d_total, 2)

        for r in raw:
            yr, mo, val = r["year"], r["month"], r["total_sales"]
            key = (yr, mo)
            combined_monthly[key] = combined_monthly.get(key, 0.0) + val

    monthly_series = [
        {
            "label": f"{k[0]}-{str(k[1]).zfill(2)}",
            "year": k[0],
            "month": k[1],
            "total_sales": round(v, 2),
            "month_name": MONTH_NAMES[k[1] - 1],
        }
        for k, v in sorted(combined_monthly.items())
    ]

    for r in monthly_series:
        month_calendar_totals[r["month"]].append(r["total_sales"])

    season_avg = {m: (sum(v) / len(v) if v else 0.0) for m, v in month_calendar_totals.items()}
    grand_avg = sum(season_avg.values()) / 12 if season_avg else 1.0
    seasonality = [
        {
            "month": m,
            "month_name": MONTH_NAMES[m - 1],
            "avg_sales": round(season_avg[m], 2),
            "index": round(season_avg[m] / grand_avg, 4) if grand_avg else 1.0,
        }
        for m in range(1, 13)
    ]

    grand_total = sum(drug_totals.values()) or 1.0
    sorted_drugs = sorted(drug_totals.items(), key=lambda x: x[1], reverse=True)

    drug_shares = [
        {
            "drug_code": code,
            "drug_name": DRUG_NAMES.get(code, code),
            "total_sales": total,
            "avg_monthly_sales": round(total / 72, 2),
            "percentage_share": round((total / grand_total) * 100, 1),
        }
        for code, total in sorted_drugs
    ]

    highest = drug_shares[0] if drug_shares else None
    lowest = drug_shares[-1] if drug_shares else None

    return {
        "summary": {
            "portfolio_total_sales": round(grand_total, 2),
            "portfolio_avg_monthly_sales": round(grand_total / 72, 2),
            "total_drugs": len(DRUGS),
            "highest_sales_drug": highest,
            "lowest_sales_drug": lowest,
        },
        "monthly_series": monthly_series,
        "seasonality": seasonality,
        "drug_shares": drug_shares,
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/portfolio-overview")
def get_portfolio_overview():
    """Returns combined trend, seasonality, top/bottom drug, and share breakdown for all drugs."""
    return get_portfolio_analytics()


@router.get("/{drug_code}")
def get_historical_analytics(drug_code: str):
    """
    Returns full 2014-2019 historical analytics for a given drug.
    First call loads from Supabase (RPC if available, else paginated).
    All subsequent calls for the same drug are served from memory cache (instant).
    """
    drug_upper = drug_code.upper()
    if drug_upper not in DRUGS:
        raise HTTPException(status_code=400, detail=f"Unknown drug: {drug_upper}. Valid: {DRUGS}")

    raw = _load_raw_data(drug_upper)
    if not raw:
        raise HTTPException(status_code=404, detail=f"No historical data found for {drug_upper}")

    return _build_analytics(drug_upper, raw)


@router.post("/cache/warm")
def warm_cache():
    """
    Pre-loads all 8 drugs into memory cache in one call.
    Call this once after server startup to make all drug switches instant.
    """
    loaded = []
    failed = []
    for drug in DRUGS:
        try:
            if drug not in _cache:
                _load_raw_data(drug)
            loaded.append(drug)
        except Exception as e:
            failed.append({"drug": drug, "error": str(e)})

    return {
        "status": "ok",
        "cached": loaded,
        "failed": failed,
        "total_cached": len(_cache),
    }


@router.delete("/cache")
def clear_cache():
    """Clears the in-memory cache (forces re-fetch from Supabase on next request)."""
    _cache.clear()
    return {"status": "ok", "message": "Cache cleared"}


@router.get("/")
def get_all_drugs_summary():
    """Returns annual totals for ALL 8 drugs. Uses cache where available."""
    results = []
    for drug in DRUGS:
        try:
            raw = _load_raw_data(drug)
        except Exception:
            continue
        if not raw:
            continue
        yoy: dict[int, float] = {}
        for r in raw:
            yoy[r["year"]] = yoy.get(r["year"], 0.0) + r["total_sales"]
        results.append({
            "drug_code": drug,
            "drug_name": DRUG_NAMES.get(drug, drug),
            "annual_totals": {str(y): round(v, 2) for y, v in sorted(yoy.items())},
            "total_2014_2019": round(sum(yoy.values()), 2),
        })
    return {"drugs": results}
