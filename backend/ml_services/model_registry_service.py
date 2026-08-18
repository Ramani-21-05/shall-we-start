"""
Model Registry Service — reads drug_model_selection_rankings.csv (READ ONLY).
"""
import os
import pandas as pd
from core.ml_paths import DRUG_MODELS_DIR, CHAMPION_MAP, DRUG_NAMES, DRUGS, TRAINING_CUTOFF_DATE


import json

def get_all_models() -> list[dict]:
    rankings_path = os.path.join(DRUG_MODELS_DIR, "drug_model_selection_rankings.csv")
    if not os.path.exists(rankings_path):
        raise FileNotFoundError("drug_model_selection_rankings.csv not found")

    df = pd.read_csv(rankings_path)
    records = []
    for _, row in df.iterrows():
        drug = row["drug"]
        champion = CHAMPION_MAP.get(drug, {})
        cfg_path = os.path.join(DRUG_MODELS_DIR, f"{drug.lower()}_models", "saved_models", "config.json")
        cfg_info = {}
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path) as f:
                    cfg_info = json.load(f)
            except Exception:
                pass
        records.append({
            "drug_code": drug,
            "drug_name": DRUG_NAMES.get(drug, drug),
            "model_key": row["model_key"],
            "model_name": row["model_name"],
            "rmsle": float(row["rmsle"]),
            "rmse": float(row["rmse"]) if ("rmse" in row and pd.notna(row["rmse"])) else None,
            "mae": float(row["mae"]),
            "mape": float(row["mape"]) if ("mape" in row and pd.notna(row["mape"])) else None,
            "wape": float(row["wape"]) if ("wape" in row and pd.notna(row["wape"])) else None,
            "n_days": int(row["n"]),
            "is_champion": row["model_key"] == champion.get("model_key"),
            "training_cutoff_date": cfg_info.get("training_period", TRAINING_CUTOFF_DATE),
            "model_status": cfg_info.get("status", "PRE_TRAINED_AND_READY"),
            "last_retrained": cfg_info.get("last_retrained"),
            "evaluation_set": "2019 Holdout",
        })
    return records



def get_drug_rankings(drug: str) -> list[dict]:
    all_models = get_all_models()
    drug_models = [m for m in all_models if m["drug_code"] == drug]
    drug_models.sort(key=lambda x: x["rmsle"])
    for i, m in enumerate(drug_models):
        m["rank"] = i + 1
    return drug_models


def get_champion_model(drug: str) -> dict | None:
    drug_upper = drug.upper()
    holdout_path = os.path.join(DRUG_MODELS_DIR, "model_evaluation_2019_holdout.csv")
    
    cfg_path = os.path.join(DRUG_MODELS_DIR, f"{drug_upper.lower()}_models", "saved_models", "config.json")
    cfg_info = {}
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path) as f:
                cfg_info = json.load(f)
        except Exception:
            pass

    if os.path.exists(holdout_path):
        try:
            df = pd.read_csv(holdout_path)
            row = df[df["Drug Code"] == drug_upper]
            if not row.empty:
                r = row.iloc[0]
                return {
                    "drug_code": drug_upper,
                    "drug_name": DRUG_NAMES.get(drug_upper, drug_upper),
                    "model_key": "champion_model",
                    "model_name": str(r["Best Champion Model"]),
                    "rmsle": float(r["RMSLE"]),
                    "rmse": float(r["RMSE"]),
                    "mae": float(r["MAE"]),
                    "mape": float(r["MAPE (%)"]),
                    "wape": float(r["WAPE (%)"]),
                    "n_days": int(r["Evaluation Days"]),
                    "is_champion": True,
                    "training_cutoff_date": cfg_info.get("training_period", TRAINING_CUTOFF_DATE),
                    "model_status": cfg_info.get("status", "PRE_TRAINED_AND_READY"),
                    "last_retrained": cfg_info.get("last_retrained"),
                    "evaluation_set": "2019 Holdout",
                    "rank": 1,
                }
        except Exception as e:
            print(f"Error loading holdout champion for {drug_upper}: {e}")

    rankings = get_drug_rankings(drug_upper)
    for m in rankings:
        if m["is_champion"]:
            return m
    return rankings[0] if rankings else None

