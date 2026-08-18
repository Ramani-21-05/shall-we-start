"""
Anomaly Service — reads 2019 anomaly detection results (READ ONLY).
2019 data is used ONLY for anomaly detection — NOT for model training.
"""
import os
import pandas as pd
from core.ml_paths import ANOMALY_DETECTION_DIR


def get_anomalies(drug: str) -> list[dict]:
    # 1. Try querying local SQLite / Supabase database
    try:
        from init_hackathon_db import DB_PATH
        import sqlite3
        if os.path.exists(DB_PATH):
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM anomaly_events WHERE drug_id = ? ORDER BY anomaly_date", (drug,))
            rows = cur.fetchall()
            conn.close()
            if rows:
                return [
                    {
                        "drug_code": r["drug_id"],
                        "anomaly_date": r["anomaly_date"],
                        "actual_demand": float(r["actual_demand"]),
                        "expected_demand": float(r["expected_demand"]),
                        "residual": float(r["residual"]),
                        "anomaly_score": float(r["anomaly_score"]),
                        "anomaly_type": r["anomaly_type"],
                        "severity": r["severity"],
                        "is_anomaly": bool(r["is_anomaly"]),
                        "detection_stage": "Stage 2 (Forecast-Aware)",
                    }
                    for r in rows
                ]
    except Exception:
        pass

    # 2. Fallback to reading pre-computed detail CSV
    detail_path = os.path.join(ANOMALY_DETECTION_DIR, "2019_detected_anomalies_detail.csv")
    if not os.path.exists(detail_path):
        raise FileNotFoundError("2019_detected_anomalies_detail.csv not found")

    df = pd.read_csv(detail_path)
    drug_col = next((c for c in df.columns if "drug" in c.lower()), "drug_category")
    sub = df[df[drug_col] == drug].copy()

    records = []
    for _, row in sub.iterrows():
        residual = float(row.get("residual", 0))
        records.append({
            "drug_code": drug,
            "anomaly_date": str(row.get("date", ""))[:10],
            "actual_demand": float(row.get("actual_sales", row.get("actual_demand", 0))),
            "expected_demand": float(row.get("p50_forecast", row.get("expected_demand", 0))),
            "residual": residual,
            "anomaly_score": float(row.get("anomaly_score", abs(residual))),
            "anomaly_type": str(row.get("anomaly_type", "Unknown")),
            "severity": _classify_severity(abs(residual)),
            "is_anomaly": bool(row.get("is_anomaly", True)),
            "detection_stage": "Stage 2 (Forecast-Aware)",
        })
    return records


def get_anomaly_summary() -> list[dict]:
    summary_path = os.path.join(ANOMALY_DETECTION_DIR, "2019_anomaly_detection_summary.csv")
    if not os.path.exists(summary_path):
        return []

    df = pd.read_csv(summary_path)
    return df.to_dict(orient="records")


def _classify_severity(abs_residual: float) -> str:
    if abs_residual >= 50:
        return "HIGH"
    elif abs_residual >= 20:
        return "MEDIUM"
    return "LOW"
