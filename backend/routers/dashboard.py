from fastapi import APIRouter, Query
import os, pandas as pd
from core.ml_paths import DRUGS, CHAMPION_MAP, DRUG_NAMES, BASE_DIR

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
WEEKDAYS_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

_hourly_df: pd.DataFrame | None = None

def _get_hourly_df() -> pd.DataFrame:
    global _hourly_df
    if _hourly_df is None:
        csv_path = os.path.join(BASE_DIR, "times_series", "dataset", "saleshourly.csv")
        if os.path.exists(csv_path):
            _hourly_df = pd.read_csv(csv_path)
        else:
            _hourly_df = pd.DataFrame()
    return _hourly_df


@router.get("/summary")
def dashboard_summary():
    # Portfolio champion metrics
    rankings_path = os.path.join(BASE_DIR, "drug_models", "drug_model_selection_rankings.csv")
    inv_eval_path = os.path.join(BASE_DIR, "inventory_recommendation", "inventory_recommendation_evaluation.csv")

    champions = []
    if os.path.exists(rankings_path):
        df = pd.read_csv(rankings_path)
        for drug in DRUGS:
            champion = CHAMPION_MAP[drug]
            row = df[(df["drug"] == drug) & (df["model_key"] == champion["model_key"])]
            if not row.empty:
                champions.append({
                    "drug_code": drug,
                    "drug_name": DRUG_NAMES[drug],
                    "champion_model": champion["model_name"],
                    "test_rmsle": float(row.iloc[0]["rmsle"]),
                    "test_rmse": float(row.iloc[0]["rmse"]) if ("rmse" in row.columns and pd.notna(row.iloc[0]["rmse"])) else None,
                    "test_mae": float(row.iloc[0]["mae"]),
                    "test_mape": float(row.iloc[0]["mape"]) if ("mape" in row.columns and pd.notna(row.iloc[0]["mape"])) else None,
                    "test_wape": float(row.iloc[0]["wape"]) if ("wape" in row.columns and pd.notna(row.iloc[0]["wape"])) else None,
                })

    portfolio_rmsle = sum(c["test_rmsle"] for c in champions) / len(champions) if champions else None
    valid_rmses = [c["test_rmse"] for c in champions if c.get("test_rmse") is not None]
    valid_mapes = [c["test_mape"] for c in champions if c.get("test_mape") is not None]
    valid_wapes = [c["test_wape"] for c in champions if c.get("test_wape") is not None]

    portfolio_rmse = sum(valid_rmses) / len(valid_rmses) if valid_rmses else None
    portfolio_mape = sum(valid_mapes) / len(valid_mapes) if valid_mapes else None
    portfolio_wape = sum(valid_wapes) / len(valid_wapes) if valid_wapes else None

    # Inventory summary
    inv_summary = {}
    if os.path.exists(inv_eval_path):
        df = pd.read_csv(inv_eval_path)
        avg_row = df[df["Drug Category"] == "PORTFOLIO AVG"]
        if not avg_row.empty:
            inv_summary = {
                "avg_service_level_pct": float(avg_row.iloc[0].get("Service Level (%)", 0)),
                "avg_demand_coverage_pct": float(avg_row.iloc[0].get("Demand Coverage Rate (%)", 0)),
                "avg_stockout_risk_pct": float(avg_row.iloc[0].get("Stockout Risk (%)", 0)),
                "avg_overstock_risk_pct": float(avg_row.iloc[0].get("Overstock Risk (%)", 0)),
            }

    return {
        "portfolio_avg_rmsle": round(portfolio_rmsle, 4) if portfolio_rmsle else None,
        "portfolio_avg_rmse": round(portfolio_rmse, 2) if portfolio_rmse else None,
        "portfolio_avg_mape": round(portfolio_mape, 1) if portfolio_mape else None,
        "portfolio_avg_wape": round(portfolio_wape, 1) if portfolio_wape else None,
        "total_drugs": len(DRUGS),
        "champions": champions,
        "inventory": inv_summary,
        "training_cutoff": "2018-12-31",
        "anomaly_detection_year": 2019,
    }


@router.get("/sales-analytics")
def get_sales_analytics(
    drug_code: str = Query("ALL", description="Drug code filter, or ALL for portfolio combined"),
    year: str = Query("ALL", description="Year filter (2014-2019), or ALL for full period"),
):
    """
    Computes comprehensive sales analytics from raw hourly sales history:
      - All drugs combined trend (72-month time series with individual drug stack)
      - Monthly Seasonality & Seasonal Index
      - Peak Hour (24-hour distribution)
      - Peak Weekday (Monday-Sunday distribution)
      - Peak Selling Month
      - YoY Sales & Growth
      - Drug Category Distribution & Share
    """
    df = _get_hourly_df().copy()
    if df.empty:
        return {"error": "Hourly dataset not available"}

    # Year filter
    if year != "ALL":
        try:
            yr_val = int(year)
            df = df[df["Year"] == yr_val]
        except ValueError:
            pass

    # Target drugs
    d_upper = drug_code.upper()
    if d_upper != "ALL" and d_upper in DRUGS:
        active_drugs = [d_upper]
    else:
        active_drugs = DRUGS
        d_upper = "ALL"

    df["selected_sales"] = df[active_drugs].sum(axis=1)

    total_units = float(df["selected_sales"].sum())
    total_records = len(df)
    unique_days = len(df["datum"].str.split(" ").str[0].unique()) if "datum" in df.columns else total_records // 24
    avg_daily_sales = total_units / unique_days if unique_days > 0 else 0.0

    # 1. PEAK HOUR ANALYSIS
    hour_grp = df.groupby("Hour")["selected_sales"].agg(["mean", "sum"]).reset_index()
    hourly_pattern = []
    for _, row in hour_grp.iterrows():
        h = int(row["Hour"])
        hourly_pattern.append({
            "hour": h,
            "label": f"{h:02d}:00",
            "avg_sales": round(float(row["mean"]), 2),
            "total_sales": round(float(row["sum"]), 2),
        })

    peak_h_row = hour_grp.sort_values(by="mean", ascending=False).iloc[0] if not hour_grp.empty else None
    peak_hour = {
        "hour": int(peak_h_row["Hour"]) if peak_h_row is not None else 19,
        "label": f"{int(peak_h_row['Hour']):02d}:00" if peak_h_row is not None else "19:00",
        "formatted": f"{int(peak_h_row['Hour']):02d}:00 ({'12 AM' if int(peak_h_row['Hour'])==0 else '12 PM' if int(peak_h_row['Hour'])==12 else str(int(peak_h_row['Hour'])%12) + (' AM' if int(peak_h_row['Hour'])<12 else ' PM')})" if peak_h_row is not None else "19:00 (7:00 PM)",
        "avg_sales": round(float(peak_h_row["mean"]), 2) if peak_h_row is not None else 0.0,
        "total_sales": round(float(peak_h_row["sum"]), 2) if peak_h_row is not None else 0.0,
    }

    # 2. PEAK WEEKDAY ANALYSIS
    wd_grp = df.groupby("Weekday Name")["selected_sales"].agg(["mean", "sum"]).to_dict(orient="index")
    weekday_pattern = []
    max_wd_mean = -1.0
    peak_wd_name = "Saturday"

    for wd in WEEKDAYS_ORDER:
        val = wd_grp.get(wd, {"mean": 0.0, "sum": 0.0})
        avg_v = float(val["mean"])
        tot_v = float(val["sum"])
        if avg_v > max_wd_mean:
            max_wd_mean = avg_v
            peak_wd_name = wd
        weekday_pattern.append({
            "weekday": wd,
            "short_name": wd[:3],
            "avg_sales": round(avg_v, 2),
            "total_sales": round(tot_v, 2),
        })

    peak_weekday = {
        "weekday": peak_wd_name,
        "avg_sales": round(max_wd_mean, 2),
        "total_sales": round(float(wd_grp.get(peak_wd_name, {}).get("sum", 0.0)), 2),
    }

    # 3. PEAK MONTH & SEASONALITY
    mo_grp = df.groupby("Month")["selected_sales"].agg(["mean", "sum"]).reset_index()
    month_avg_map = {int(r["Month"]): float(r["mean"]) for _, r in mo_grp.iterrows()}
    month_sum_map = {int(r["Month"]): float(r["sum"]) for _, r in mo_grp.iterrows()}

    grand_mo_avg = sum(month_avg_map.values()) / 12 if month_avg_map else 1.0
    seasonality = []
    peak_m_num = 1
    max_m_avg = -1.0

    for m in range(1, 13):
        avg_v = month_avg_map.get(m, 0.0)
        tot_v = month_sum_map.get(m, 0.0)
        idx_v = avg_v / grand_mo_avg if grand_mo_avg > 0 else 1.0
        if avg_v > max_m_avg:
            max_m_avg = avg_v
            peak_m_num = m

        seasonality.append({
            "month": m,
            "month_name": MONTH_NAMES[m - 1],
            "avg_sales": round(avg_v, 2),
            "total_sales": round(tot_v, 2),
            "index": round(idx_v, 4),
        })

    peak_month = {
        "month": peak_m_num,
        "month_name": MONTH_NAMES[peak_m_num - 1],
        "avg_sales": round(max_m_avg, 2),
        "total_sales": round(month_sum_map.get(peak_m_num, 0.0), 2),
    }

    # 4. COMBINED TREND (Monthly Time Series 2014-2019)
    # Group by Year, Month and calculate total + breakdown for each drug
    monthly_grp = df.groupby(["Year", "Month"])
    monthly_series = []

    for (y, m), group in monthly_grp:
        tot = float(group["selected_sales"].sum())
        item = {
            "label": f"{y}-{str(m).zfill(2)}",
            "year": int(y),
            "month": int(m),
            "month_name": MONTH_NAMES[int(m) - 1],
            "total_sales": round(tot, 2),
        }
        for d in DRUGS:
            item[d] = round(float(group[d].sum()), 2)
        monthly_series.append(item)

    monthly_series.sort(key=lambda x: (x["year"], x["month"]))

    # 5. ANNUAL TOTALS & YOY GROWTH
    year_grp = df.groupby("Year")["selected_sales"].sum().to_dict()
    yoy_series = []
    sorted_years = sorted(year_grp.keys())
    for i, y in enumerate(sorted_years):
        tot_v = float(year_grp[y])
        prev_v = float(year_grp[sorted_years[i - 1]]) if i > 0 else None
        growth = round((tot_v - prev_v) / prev_v * 100, 2) if (prev_v and prev_v > 0) else None
        yoy_series.append({
            "year": int(y),
            "total_sales": round(tot_v, 2),
            "growth_pct": growth,
        })

    # 6. DRUG SHARES
    drug_shares = []
    grand_portfolio_total = float(df[DRUGS].sum().sum()) or 1.0
    for d in DRUGS:
        d_tot = float(df[d].sum())
        drug_shares.append({
            "drug_code": d,
            "drug_name": DRUG_NAMES.get(d, d),
            "total_sales": round(d_tot, 2),
            "percentage_share": round((d_tot / grand_portfolio_total) * 100, 1),
            "avg_monthly_sales": round(d_tot / (len(monthly_series) or 1), 2),
        })

    drug_shares.sort(key=lambda x: x["total_sales"], reverse=True)
    top_drug = drug_shares[0] if drug_shares else None
    lowest_drug = drug_shares[-1] if drug_shares else None

    return {
        "summary": {
            "selected_drug": d_upper,
            "selected_year": year,
            "total_sales": round(total_units, 2),
            "avg_daily_sales": round(avg_daily_sales, 2),
            "total_records": total_records,
            "peak_hour": peak_hour,
            "peak_weekday": peak_weekday,
            "peak_month": peak_month,
            "top_drug": top_drug,
            "lowest_drug": lowest_drug,
        },
        "combined_trend": monthly_series,
        "seasonality": seasonality,
        "hourly_pattern": hourly_pattern,
        "weekday_pattern": weekday_pattern,
        "yoy_series": yoy_series,
        "drug_shares": drug_shares,
    }

