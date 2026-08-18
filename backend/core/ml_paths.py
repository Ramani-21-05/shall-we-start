import os

CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_FILE_DIR)
BASE_DIR = os.getenv("APP_BASE_DIR", os.path.dirname(BACKEND_DIR))

# ============================================================
# READ-ONLY paths to research/ML artifact directories.
# These are NEVER modified by the backend — only read from.
# ============================================================

DRUG_MODELS_DIR              = os.path.join(BASE_DIR, "drug_models")
ANOMALY_DETECTION_DIR        = os.path.join(BASE_DIR, "anomaly_detection")
EXPLAINABLE_FORECASTING_DIR  = os.path.join(BASE_DIR, "explainable_forecasting")
INVENTORY_RECOMMENDATION_DIR = os.path.join(BASE_DIR, "inventory_recommendation")
TIMES_SERIES_DIR             = os.path.join(BASE_DIR, "times_series")

DRUGS = ["M01AB", "M01AE", "N02BA", "N02BE", "N05B", "N05C", "R03", "R06"]

# Champion model mapping
CHAMPION_MAP = {
    "M01AB": {"model_key": "m6_lightgbm",     "model_name": "LightGBM + SHAP",   "algorithm_family": "Tree-Based ML"},
    "M01AE": {"model_key": "m4_prophet",       "model_name": "Meta Prophet",       "algorithm_family": "Statistical Trend"},
    "N02BA": {"model_key": "m6_lightgbm",      "model_name": "LightGBM + SHAP",   "algorithm_family": "Tree-Based ML"},
    "N02BE": {"model_key": "m6_lightgbm",      "model_name": "LightGBM + SHAP",   "algorithm_family": "Tree-Based ML"},
    "N05B":  {"model_key": "m6_lightgbm",      "model_name": "LightGBM + SHAP",   "algorithm_family": "Tree-Based ML"},
    "N05C":  {"model_key": "m1_arima",         "model_name": "ARIMA",              "algorithm_family": "Classical Time-Series"},
    "R03":   {"model_key": "m7_xgb_quantile",  "model_name": "XGBoost Quantile",  "algorithm_family": "Tree-Based ML"},
    "R06":   {"model_key": "m6_lightgbm",      "model_name": "LightGBM + SHAP",   "algorithm_family": "Tree-Based ML"},
}

DRUG_NAMES = {
    "M01AB": "Anti-inflammatory (Acetic Acid Derivatives)",
    "M01AE": "Anti-inflammatory (Propionic Acid — Ibuprofen)",
    "N02BA": "Salicylic Acid (Aspirin)",
    "N02BE": "Paracetamol (Acetaminophen)",
    "N05B":  "Anxiolytics (Sedatives / Anti-Anxiety)",
    "N05C":  "Hypnotics (Sleeping Pills)",
    "R03":   "Inhalers (Asthma & COPD)",
    "R06":   "Antihistamines (Allergy)",
}

# Training cutoff — models ONLY trained on data up to this date
TRAINING_CUTOFF_DATE = "2018-12-31"

# 2019 test set is reserved EXCLUSIVELY for anomaly detection
ANOMALY_DETECTION_YEAR = 2019
