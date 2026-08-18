"""
SHAP Service — reads feature_weights_all_drugs.csv (READ ONLY).
"""
import os
import pandas as pd
from core.ml_paths import EXPLAINABLE_FORECASTING_DIR

DRUG_NARRATIVES = {
    "M01AB": {
        "primary_driver": "Day of Week (Prescription Writing Cycles)",
        "summary": "M01AB (Diclofenac / Acemetacin) demand is heavily governed by doctor visit schedules and Mon-Fri prescription issuance rather than seasonal climate shifts.",
        "key_insight": "Calendar features (sin_dayofweek) dominate because prescription renewals cluster on weekdays. Pharmacists should align inventory for Mon-Fri peaks.",
    },
    "M01AE": {
        "primary_driver": "28-Day Rolling Baseline + Weekly Cycle",
        "summary": "M01AE (Ibuprofen) demand combines a stable chronic arthritis patient base with strong weekly refill cadence.",
        "key_insight": "The 28-day rolling average provides the anchor demand level, while rolling std-28 flags monthly consumption volatility.",
    },
    "N02BA": {
        "primary_driver": "Chronic Daily Rolling Average (28-Day)",
        "summary": "N02BA (Aspirin) is dominated by daily cardiovascular prevention users, making its 28-day average nearly 5x more impactful than any other feature.",
        "key_insight": "Long-term consumption is extremely predictable from recent monthly averages. Spikes in cv_7 signal unexpected pharmacy stock adjustments.",
    },
    "N02BE": {
        "primary_driver": "Short-term Lags & Day of Week",
        "summary": "N02BE (Paracetamol) is an OTC analgesic for acute fever and pain, making short-term 7-day windows and weekend spikes key.",
        "key_insight": "Recent 7-day demand levels and day-of-week patterns drive predictions. Acute pain medication responds rapidly to short-term trends.",
    },
    "N05B": {
        "primary_driver": "7-Day Refill & 28-Day Baseline",
        "summary": "N05B (Anxiolytics) exhibits strict prescription refill schedules with strong weekly and monthly periodicities.",
        "key_insight": "Patients on anti-anxiety treatment renew prescriptions on fixed weekly/monthly schedules, driving high weight on lag_7 and rolling_mean_28.",
    },
    "N05C": {
        "primary_driver": "Chronic Monthly Baseline",
        "summary": "N05C (Hypnotics & Sedatives) maintains steady prescription patterns from chronic sleep treatment cohorts.",
        "key_insight": "Rolling 28-day mean anchors forecast stability, with minimal sensitivity to weather or day-to-day noise.",
    },
    "R03": {
        "primary_driver": "Annual Seasonality & 28-Day Peak Demand",
        "summary": "R03 (Asthma & COPD Inhalers) is strongly seasonal, driven by winter respiratory infections and allergy season triggers.",
        "key_insight": "Calendar day-of-year features and 28-day peak demand (rolling_max_28) dictate seasonal inventory buffering.",
    },
    "R06": {
        "primary_driver": "Annual Seasonality (Allergy Season)",
        "summary": "R06 (Antihistamines) features the strongest annual seasonal cycle across all 8 drugs due to spring/summer pollen triggers.",
        "key_insight": "Sin/cos day-of-year harmonic features account for over 50% of model weight during peak pollen months.",
    },
}


def get_shap_weights(drug: str) -> list[dict]:
    csv_path = os.path.join(EXPLAINABLE_FORECASTING_DIR, "feature_weights_all_drugs.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError("feature_weights_all_drugs.csv not found")

    df = pd.read_csv(csv_path)
    drug_col = "drug_category" if "drug_category" in df.columns else "drug"
    sub = df[df[drug_col] == drug].sort_values("mean_abs_shap", ascending=False).reset_index(drop=True)

    records = []
    for i, row in sub.iterrows():
        records.append({
            "drug_code": drug,
            "feature": row["feature"],
            "mean_abs_shap": float(row["mean_abs_shap"]),
            "lgb_gain": float(row["lgb_gain"]) if "lgb_gain" in row else None,
            "feature_domain": row.get("domain", "Unknown"),
            "feature_rank": i + 1,
        })
    return records


def get_drug_explanation(drug: str) -> dict:
    drug_upper = drug.upper()
    weights = get_shap_weights(drug_upper)
    
    # Calculate domain breakdown
    domain_totals = {}
    total_shap = sum(w["mean_abs_shap"] for w in weights) or 1.0
    for w in weights:
        dom = w["feature_domain"]
        domain_totals[dom] = domain_totals.get(dom, 0.0) + w["mean_abs_shap"]
    
    domain_breakdown = [
        {
            "domain": k,
            "total_shap": round(v, 4),
            "percentage": round((v / total_shap) * 100, 1),
        }
        for k, v in sorted(domain_totals.items(), key=lambda x: x[1], reverse=True)
    ]

    return {
        "drug_code": drug_upper,
        "narrative": DRUG_NARRATIVES.get(drug_upper, {
            "primary_driver": "Multi-Factor ML Model Signals",
            "summary": f"Demand for {drug_upper} is driven by a combination of lag, rolling average, and calendar seasonality features.",
            "key_insight": "Model uses automated SHAP feature weighting to prioritize top signals.",
        }),
        "domain_breakdown": domain_breakdown,
        "top_features": weights[:10],
    }



def get_shap_breakdown(drug: str) -> list[dict]:
    csv_path = os.path.join(EXPLAINABLE_FORECASTING_DIR, "explainable_shap_breakdown.csv")
    if not os.path.exists(csv_path):
        return []

    df = pd.read_csv(csv_path)
    drug_col = "drug_category" if "drug_category" in df.columns else "drug"
    sub = df[df[drug_col] == drug]

    records = []
    for _, row in sub.iterrows():
        records.append({
            "drug_code": drug,
            "date": str(row.get("date", ""))[:10],
            "feature": row.get("feature", ""),
            "shap_value": float(row.get("shap_value", 0)),
            "direction": "positive" if float(row.get("shap_value", 0)) > 0 else "negative",
        })
    return records

