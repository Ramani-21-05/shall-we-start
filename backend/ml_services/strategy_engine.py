"""
ml_services/strategy_engine.py
───────────────────────────────
Deterministic, Rule-Based Strategy & Intelligence Engine.

Architecture:
  ML / Statistics (Trend, Seasonality, Forecast, Stock Coverage, Co-demand)
        ↓
  Deterministic Rule Engine (Scenarios & Decision Matrices)
        ↓
  Structured Business Strategies (Sales, Marketing, Inventory, Rationale)
        ↓
  Human-Readable Explanations & Actionable UI Output
"""

import os
import pandas as pd
import numpy as np
from core.ml_paths import DRUGS, DRUG_NAMES, BASE_DIR

WEEKDAYS_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

# Association Rules / Co-purchasing knowledge base
ASSOCIATION_RULES = [
    {
        "antecedent": "N02BE",
        "consequent": "M01AE",
        "antecedent_name": "Paracetamol (Acetaminophen)",
        "consequent_name": "Ibuprofen (Propionic acid)",
        "support_pct": 28.4,
        "confidence_pct": 74.2,
        "lift": 1.82,
        "recommendation": "Customers purchasing Paracetamol frequently co-purchase Ibuprofen. Display pain-relief bundles and suggest dual-action therapy."
    },
    {
        "antecedent": "R03",
        "consequent": "R06",
        "antecedent_name": "Inhalers (Obstructive airway)",
        "consequent_name": "Antihistamines (Allergy)",
        "support_pct": 19.1,
        "confidence_pct": 68.5,
        "lift": 2.15,
        "recommendation": "Strong co-occurrence between respiratory inhalers and allergy medication. Position antihistamines next to asthma supplies."
    },
    {
        "antecedent": "N02BA",
        "consequent": "M01AB",
        "antecedent_name": "Aspirin (Salicylic acid)",
        "consequent_name": "Anti-inflammatory (Acetic acid)",
        "support_pct": 15.2,
        "confidence_pct": 61.0,
        "lift": 1.65,
        "recommendation": "Frequent co-purchasing of joint pain and anti-inflammatory remedies. Cross-promote topical gel additives."
    },
    {
        "antecedent": "N05B",
        "consequent": "N05C",
        "antecedent_name": "Anxiolytics (Sedatives)",
        "consequent_name": "Hypnotics (Sleep Aids)",
        "support_pct": 12.8,
        "confidence_pct": 78.5,
        "lift": 2.40,
        "recommendation": "High confidence co-demand between daytime anxiolytics and sleep aids. Offer calm & rest regimen bundles."
    }
]


from functools import lru_cache

@lru_cache(maxsize=1)
def load_dataset() -> pd.DataFrame:
    csv_path = os.path.join(BASE_DIR, "times_series", "dataset", "saleshourly.csv")
    if os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    return pd.DataFrame()


@lru_cache(maxsize=1)
def fetch_all_2020_forecasts() -> dict[str, dict[int, float]]:
    """Fetches 2020 forecast values for ALL drugs in ONE single Supabase query for maximum speed."""
    result: dict[str, dict[int, float]] = {}
    try:
        from core.database import get_supabase
        supabase = get_supabase()
        res = (
            supabase.table("forecast_results")
            .select("drug_code, forecast_date, p50_demand")
            .gte("forecast_date", "2020-01-01")
            .lte("forecast_date", "2020-12-31")
            .execute()
        )
        if res.data:
            for row in res.data:
                dc = row["drug_code"].upper()
                m = int(str(row["forecast_date"])[5:7])
                p50 = float(row.get("p50_demand", 0))
                if dc not in result:
                    result[dc] = {}
                result[dc][m] = round(result[dc].get(m, 0) + p50, 2)
    except Exception as e:
        print(f"Notice: Supabase bulk forecast query fallback: {e}")
    return result


def generate_product_strategy(
    drug_code: str,
    df: pd.DataFrame | None = None,
    target_month: int | None = None,
    forecast_dict: dict[int, float] | None = None,
) -> dict:
    if df is None or df.empty:
        df = load_dataset()

    d_upper = drug_code.upper()
    if d_upper not in DRUGS or df.empty:
        return {}

    # Basic stats
    sales_col = df[d_upper]
    total_sales = float(sales_col.sum())
    mean_hourly = float(sales_col.mean())
    std_hourly = float(sales_col.std())
    cv = std_hourly / mean_hourly if mean_hourly > 0 else 0.0

    # 30-day projected vs historical baseline
    df_2019 = df[df["Year"] == 2019]
    df_2018 = df[df["Year"] == 2018]

    if not df_2019.empty:
        total_2019_months = len(df_2019["Month"].unique()) or 10
        historical_30d_avg = float(df_2019[d_upper].sum()) / total_2019_months
    elif not df_2018.empty:
        historical_30d_avg = float(df_2018[d_upper].sum()) / 12.0
    else:
        historical_30d_avg = total_sales / 72.0

    # Seasonality for selected month / Jan-Dec timeline
    mo_grp = df.groupby("Month")[d_upper].mean()
    grand_mo_mean = mo_grp.mean()
    
    selected_month_num = target_month if (target_month and 1 <= target_month <= 12) else 9  # default Sep
    selected_month_name = MONTH_NAMES[selected_month_num - 1]
    peak_month_num = int(mo_grp.idxmax())
    peak_month_name = MONTH_NAMES[peak_month_num - 1]

    # YoY Growth component (2019 vs 2018 monthly avg)
    if not df_2019.empty and not df_2018.empty:
        avg_18 = float(df_2018[d_upper].sum()) / 12.0
        avg_19 = historical_30d_avg
        yoy_growth = (avg_19 - avg_18) / avg_18 if avg_18 > 0 else 0.0
    else:
        yoy_growth = 0.02

    yoy_growth_pct = round(yoy_growth * 100, 1)

    # Fetch real 2020 AI model P50 forecast predictions from pre-fetched bulk cache or single lookup
    if forecast_dict is not None:
        supabase_monthly_forecast = forecast_dict
    else:
        all_fc = fetch_all_2020_forecasts()
        supabase_monthly_forecast = all_fc.get(d_upper, {})

    # 12-Month Timeline Array (Jan to Dec)
    monthly_timeline = []
    for m in range(1, 13):
        m_avg = float(mo_grp.get(m, grand_mo_mean))
        m_idx = round(m_avg / grand_mo_mean, 2) if grand_mo_mean > 0 else 1.0
        m_growth_factor = (1.0 + yoy_growth) * (0.85 + 0.3 * m_idx) - 1.0
        if m in supabase_monthly_forecast:
            m_forecast = supabase_monthly_forecast[m]
        else:
            m_forecast = round(historical_30d_avg * (1.0 + m_growth_factor), 1)
        m_status = "PEAK" if m_idx >= 1.15 else ("OFF_PEAK" if m_idx < 0.85 else "NORMAL")
        monthly_timeline.append({
            "month": m,
            "month_name": MONTH_NAMES[m - 1],
            "seasonal_index": m_idx,
            "forecast_units": m_forecast,
            "season_status": m_status,
            "is_selected": (m == selected_month_num),
        })

    # Combined 30-day forecast demand & growth for selected month
    # Calculate historical same-month average across 2014-2019 for true YoY month growth comparison
    df_target_month = df[df["Month"] == selected_month_num]
    num_years = len(df_target_month["Year"].unique()) if not df_target_month.empty else 6
    historical_same_month_avg = float(df_target_month[d_upper].sum()) / num_years if num_years > 0 else historical_30d_avg

    sel_mo_avg = float(mo_grp.get(selected_month_num, grand_mo_mean))
    seasonal_index = round(sel_mo_avg / grand_mo_mean, 2) if grand_mo_mean > 0 else 1.0
    combined_growth_factor = (1.0 + yoy_growth) * (0.85 + 0.3 * seasonal_index) - 1.0

    if selected_month_num in supabase_monthly_forecast:
        forecast_30d = supabase_monthly_forecast[selected_month_num]
        if historical_same_month_avg > 0:
            combined_growth_factor = (forecast_30d - historical_same_month_avg) / historical_same_month_avg
        forecast_growth_pct = round(combined_growth_factor * 100.0, 1)
    else:
        forecast_30d = round(historical_30d_avg * (1.0 + combined_growth_factor), 2)
        forecast_growth_pct = round(combined_growth_factor * 100.0, 1)

    # Dynamic Inventory Retrieval from Live Inventory Engine (no hardcoded fixed dictionary)
    try:
        from ml_services.inventory_engine import evaluate_drug_inventory
        inv_eval = evaluate_drug_inventory(d_upper)
        current_stock = round(float(inv_eval.get("current_stock", 100.0)), 1)
        lead_time_days = float(inv_eval.get("lead_time_days", 3))
    except Exception as e:
        print(f"Notice: Live inventory engine query fallback for {d_upper}: {e}")
        current_stock = round(historical_30d_avg * 0.5, 1)
        lead_time_days = 3.0

    daily_demand = max(forecast_30d / 30.0, 0.1)
    stock_coverage_days = round(current_stock / daily_demand, 1)

    # Dynamic Reorder Point (ROP) & Order Quantity calculations
    safety_days = 5.0 if seasonal_index >= 1.15 else 3.0
    reorder_point = round(daily_demand * (lead_time_days + safety_days), 1)
    target_stock = round(daily_demand * 30.0, 1)
    recommended_order_qty = round(max(0.0, target_stock - current_stock), 1)

    # Dynamic Portfolio Median Demand threshold (statistically robust against extreme outliers)
    all_monthly_avgs = [float(df[d].sum() / 72.0) for d in DRUGS if d in df.columns]
    portfolio_median_demand = float(pd.Series(all_monthly_avgs).median()) if all_monthly_avgs else 134.33

    # Volume threshold: forecast_30d >= portfolio_median_demand = High Demand in target month
    # Growth threshold: forecast_growth_pct >= 0.0% = High Growth in target month
    is_high_volume = forecast_30d >= portfolio_median_demand
    is_high_growth = forecast_growth_pct >= 0.0

    if is_high_growth and is_high_volume:
        quadrant = "PRIORITY"
        quadrant_label = "🟢 Priority Product"
        quadrant_badge = "High Growth + High Demand"
    elif is_high_growth and not is_high_volume:
        quadrant = "EMERGING"
        quadrant_label = "🔵 Emerging Product"
        quadrant_badge = "High Growth + Low Demand"
    elif not is_high_growth and is_high_volume:
        quadrant = "STABLE"
        quadrant_label = "🟡 Stable Product"
        quadrant_badge = "Low Growth + High Demand"
    else:
        quadrant = "LOW_PRIORITY"
        quadrant_label = "🔴 Low Priority"
        quadrant_badge = "Low Growth + Low Demand"

    # 2. DETERMINISTIC SALES STRATEGY RULES (Month-aware & Quadrant-aligned)
    if quadrant == "PRIORITY" or seasonal_index >= 1.15:
        sales_strategy = {
            "opportunity_level": f"High Demand Growth in {selected_month_name}",
            "action": f"Strong demand projected for {selected_month_name} ({forecast_30d} units). Increase replenishment orders 2 weeks in advance to prevent stockouts.",
            "stock_focus": "Priority Inventory Buffer",
            "replenishment_urgency": "Urgent",
        }
    elif quadrant == "EMERGING":
        sales_strategy = {
            "opportunity_level": f"Emerging Demand in {selected_month_name}",
            "action": f"Positive demand growth momentum in {selected_month_name} ({forecast_30d} units). Build growth inventory buffer to capture expanding market share.",
            "stock_focus": "Growth Expansion Buffer",
            "replenishment_urgency": "High",
        }
    elif quadrant == "STABLE":
        sales_strategy = {
            "opportunity_level": f"Steady High Volume in {selected_month_name}",
            "action": f"Steady sales velocity expected for {selected_month_name} ({forecast_30d} units). Maintain regular automated replenishment.",
            "stock_focus": "Standard Steady Buffer",
            "replenishment_urgency": "Normal",
        }
    else:
        sales_strategy = {
            "opportunity_level": f"Low Velocity Demand in {selected_month_name}",
            "action": f"Slow seasonal period in {selected_month_name} ({forecast_30d} units). Reduce purchase order quantities and maintain lean holding stock.",
            "stock_focus": "Controlled Lean Stock",
            "replenishment_urgency": "Low",
        }

    # 3. DETERMINISTIC MARKETING STRATEGY RULES (Month-aware)
    if seasonal_index >= 1.15:
        marketing_strategy = {
            "focus": f"{selected_month_name} Seasonal Surge Campaign",
            "timing_recommendation": f"High seasonal index ({seasonal_index}x) in {selected_month_name}. Launch promotional campaign during the first week of {selected_month_name}.",
            "action": f"Run prime pharmacy banner placements, featured bundle ads, and doctor recommendation drives.",
            "intensity": "High",
        }
    elif seasonal_index < 0.85:
        marketing_strategy = {
            "focus": "Off-Season Clearance & Loyalty Retention",
            "timing_recommendation": f"Low seasonal demand in {selected_month_name}. Focus on loyalty point multipliers or multi-pack bundles rather than heavy ad spend.",
            "action": "Implement targeted digital coupons and reward points to maintain baseline velocity.",
            "intensity": "Low",
        }
    elif quadrant == "PRIORITY":
        marketing_strategy = {
            "focus": "Aggressive Promotion & Feature Placement",
            "timing_recommendation": f"Increase promotional visibility during {selected_month_name} to capture growth momentum.",
            "action": "Run feature banner placement, hero pharmacy co-op ads, and prime shelf placement.",
            "intensity": "High",
        }
    elif quadrant == "EMERGING":
        marketing_strategy = {
            "focus": "Category Adoption & Targeted Promotion",
            "timing_recommendation": f"Product shows positive growth momentum in {selected_month_name}. Run targeted trial promotions.",
            "action": "Test targeted digital coupons, pharmacist sampling recommendations, and cross-category intro packs.",
            "intensity": "Medium",
        }
    else:
        marketing_strategy = {
            "focus": "Standard Promotional Baseline",
            "timing_recommendation": f"Maintain standard marketing presence for {selected_month_name}.",
            "action": "Keep standard product listing and monitor weekly customer conversion.",
            "intensity": "Low-Moderate",
        }

    # 4. DYNAMIC INVENTORY ALIGNMENT RULES
    if stock_coverage_days < 7.0 or current_stock <= reorder_point:
        inv_status = "CRITICAL STOCKOUT RISK"
        inv_recommendation = f"Current stock ({current_stock} units / {stock_coverage_days} days) is at or below Reorder Point ({reorder_point} units). Expedite purchase order of {recommended_order_qty} units immediately."
        inv_color = "red"
    elif stock_coverage_days < 14.0:
        inv_status = "REORDER REQUIRED"
        inv_recommendation = f"Current stock ({current_stock} units / {stock_coverage_days} days) is approaching safety limit. Place purchase order for {recommended_order_qty} units."
        inv_color = "amber"
    elif stock_coverage_days > 30.0:
        inv_status = "EXCESS OVERSTOCK"
        inv_recommendation = f"Current stock ({current_stock} units / {stock_coverage_days} days) exceeds 30-day requirement ({forecast_30d} units). Hold further purchase orders."
        inv_color = "amber"
    else:
        inv_status = "OPTIMAL COVERAGE"
        inv_recommendation = f"Current stock ({current_stock} units / {stock_coverage_days} days) matches target 30-day demand ({forecast_30d} units)."
        inv_color = "emerald"

    # 5. DETERMINISTIC RATIONALE EXPLANATION
    rationale = (
        f"Historical 30-day average for {d_upper} is {round(historical_30d_avg, 1)} units. "
        f"Forecast for {selected_month_name} projects {forecast_30d} units ({'+' if forecast_growth_pct>=0 else ''}{forecast_growth_pct}% YoY growth). "
        f"Seasonal index for {selected_month_name} is {seasonal_index}x (annual peak month: {peak_month_name}). "
        f"Classified as {quadrant_label} based on volume and growth trajectory."
    )

    # Relevant association rule for this drug
    assoc = [r for r in ASSOCIATION_RULES if r["antecedent"] == d_upper or r["consequent"] == d_upper]

    return {
        "drug_code": d_upper,
        "drug_name": DRUG_NAMES.get(d_upper, "Pharmaceutical Category"),
        "quadrant": quadrant,
        "quadrant_label": quadrant_label,
        "quadrant_badge": quadrant_badge,
        "metrics": {
            "total_historical_sales": round(float(df[d_upper].sum()), 1),
            "historical_30d_avg": round(historical_30d_avg, 1),
            "forecast_30d": forecast_30d,
            "forecast_growth_pct": forecast_growth_pct,
            "seasonal_index": seasonal_index,
            "peak_month": peak_month_name,
            "stock_coverage_days": stock_coverage_days,
            "current_stock": current_stock,
            "variability_cv": round(cv, 2),
        },
        "quadrant": quadrant,
        "quadrant_label": quadrant_label,
        "quadrant_badge": quadrant_badge,
        "sales_strategy": sales_strategy,
        "marketing_strategy": marketing_strategy,
        "inventory_strategy": {
            "status": inv_status,
            "recommendation": inv_recommendation,
            "color": inv_color,
            "coverage_days": stock_coverage_days,
        },
        "rationale": rationale,
        "monthly_timeline": monthly_timeline,
        "association_rules": assoc,
    }


@lru_cache(maxsize=16)
def get_strategy_overview(target_month: int | None = None) -> dict:
    df = load_dataset()
    products = []
    quadrant_counts = {"PRIORITY": 0, "EMERGING": 0, "STABLE": 0, "LOW_PRIORITY": 0}

    selected_month_num = target_month if (target_month and 1 <= target_month <= 12) else 9
    selected_month_name = MONTH_NAMES[selected_month_num - 1]

    # Bulk fetch 2020 forecasts once for all 8 drugs
    all_fc = fetch_all_2020_forecasts()

    for d in DRUGS:
        strat = generate_product_strategy(d, df, target_month=selected_month_num, forecast_dict=all_fc.get(d, {}))
        if strat:
            products.append(strat)
            quadrant_counts[strat["quadrant"]] = quadrant_counts.get(strat["quadrant"], 0) + 1

    # Urgent actions summary
    urgent_sales_actions = [
        {"drug_code": p["drug_code"], "drug_name": p["drug_name"], "action": p["sales_strategy"]["action"]}
        for p in products if p["sales_strategy"].get("replenishment_urgency") in ["Urgent", "Moderate-High"]
    ]

    campaign_timings = [
        {"drug_code": p["drug_code"], "drug_name": p["drug_name"], "timing": p["marketing_strategy"]["timing_recommendation"], "focus": p["marketing_strategy"]["focus"]}
        for p in products if p["marketing_strategy"].get("intensity") in ["High", "Medium"]
    ]

    return {
        "summary": {
            "total_products": len(DRUGS),
            "selected_month": selected_month_num,
            "selected_month_name": selected_month_name,
            "quadrant_counts": quadrant_counts,
            "priority_products_count": quadrant_counts["PRIORITY"],
            "emerging_products_count": quadrant_counts["EMERGING"],
            "cross_sell_rules_count": len(ASSOCIATION_RULES),
        },
        "products": products,
        "association_rules": ASSOCIATION_RULES,
        "urgent_sales_actions": urgent_sales_actions,
        "campaign_timings": campaign_timings,
    }

