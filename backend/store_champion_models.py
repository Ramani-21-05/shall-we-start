"""
Store Per-Drug Dual Models Script (Forecast Anchor + Inventory Quantile Models)
Creates a dedicated directory for each drug inside backend/saved_models/{drug}/:
  1. anchor_model.pkl   (P50 Expected Demand Anchor)
  2. quantile_model.pkl (P10 & P90 Risk Bounds & Inventory Safety Stock)
  3. config.json         (Metadata, features, and 2014-2018 training cutoff)
"""
import os
import json
import joblib
import pandas as pd
import numpy as np
import lightgbm as lgb
import xgboost as xgb
from statsmodels.tsa.arima.model import ARIMA
from prophet import Prophet

BASE_DIR = r"c:\Users\ranje\sales forcasting"
SAVED_MODELS_DIR = os.path.join(BASE_DIR, "backend", "saved_models")
os.makedirs(SAVED_MODELS_DIR, exist_ok=True)

# 8 Drug Categories with their assigned Anchor ($P_50$) and Quantile ($P_10, P_90$) models
DRUG_MODEL_CONFIG = {
    "M01AB": {"anchor_family": "lightgbm", "anchor_name": "LightGBM + SHAP",    "quantile_family": "xgboost", "quantile_name": "XGBoost Quantile"},
    "M01AE": {"anchor_family": "prophet",  "anchor_name": "Meta Prophet",        "quantile_family": "xgboost", "quantile_name": "XGBoost Quantile"},
    "N02BA": {"anchor_family": "lightgbm", "anchor_name": "LightGBM + SHAP",    "quantile_family": "xgboost", "quantile_name": "XGBoost Quantile"},
    "N02BE": {"anchor_family": "lightgbm", "anchor_name": "LightGBM + SHAP",    "quantile_family": "xgboost", "quantile_name": "XGBoost Quantile"},
    "N05B":  {"anchor_family": "lightgbm", "anchor_name": "LightGBM + SHAP",    "quantile_family": "xgboost", "quantile_name": "XGBoost Quantile"},
    "N05C":  {"anchor_family": "arima",    "anchor_name": "ARIMA",              "quantile_family": "xgboost", "quantile_name": "XGBoost Quantile"},
    "R03":   {"anchor_family": "xgboost",  "anchor_name": "XGBoost Quantile",  "quantile_family": "xgboost", "quantile_name": "XGBoost Quantile"},
    "R06":   {"anchor_family": "lightgbm", "anchor_name": "LightGBM + SHAP",    "quantile_family": "xgboost", "quantile_name": "XGBoost Quantile"},
}

def load_training_data():
    train_path = os.path.join(BASE_DIR, "times_series", "dataset", "train_daily.csv")
    val_path   = os.path.join(BASE_DIR, "times_series", "dataset", "val_daily.csv")
    
    df_train = pd.read_csv(train_path)
    df_val   = pd.read_csv(val_path)
    
    full_train = pd.concat([df_train, df_val], ignore_index=True)
    full_train['date'] = pd.to_datetime(full_train['date'])
    full_train = full_train.sort_values('date').reset_index(drop=True)
    
    # Enforce strict cutoff date: 2018-12-31 (2014-2018 data only)
    full_train = full_train[full_train['date'] <= '2018-12-31'].copy()
    return full_train

def create_features(df, target_col):
    data = df[['date', target_col]].copy()
    data.columns = ['date', 'y']
    for lag in [1, 2, 3, 7, 14, 21, 28]:
        data[f'lag_{lag}'] = data['y'].shift(lag)
    for rw in [7, 14, 30]:
        data[f'rolling_mean_{rw}'] = data['y'].shift(1).rolling(rw).mean()
        data[f'rolling_std_{rw}']  = data['y'].shift(1).rolling(rw).std()
    
    data['dayofweek'] = data['date'].dt.dayofweek
    data['month']     = data['date'].dt.month
    data['day']       = data['date'].dt.day
    data['year']      = data['date'].dt.year
    
    data = data.dropna().reset_index(drop=True)
    features = [c for c in data.columns if c not in ['date', 'y']]
    return data[features], data['y'], features

def train_and_store_per_drug():
    df = load_training_data()
    min_date = str(df['date'].min())[:10]
    max_date = str(df['date'].max())[:10]
    print(f"Loaded Training Data strictly from {min_date} to {max_date} ({len(df):,} days)")
    
    for drug, cfg in DRUG_MODEL_CONFIG.items():
        drug_folder = os.path.join(SAVED_MODELS_DIR, drug.lower())
        os.makedirs(drug_folder, exist_ok=True)
        print(f"\n==================================================")
        print(f"Processing Drug Category: [{drug}]")
        print(f"Directory: backend/saved_models/{drug.lower()}/")
        print(f"  Anchor Model (P50): {cfg['anchor_name']}")
        print(f"  Quantile Model (P10/P90): {cfg['quantile_name']}")
        
        anchor_path = os.path.join(drug_folder, "anchor_model.pkl")
        quantile_path = os.path.join(drug_folder, "quantile_model.pkl")
        config_path = os.path.join(drug_folder, "config.json")
        
        # 1. Train & Store Anchor Model (P50 Forecast)
        anchor_fam = cfg["anchor_family"]
        if anchor_fam == "lightgbm":
            X, y, feats = create_features(df, drug)
            m_anchor = lgb.LGBMRegressor(n_estimators=100, learning_rate=0.05, random_state=42, verbose=-1)
            m_anchor.fit(X, y)
            joblib.dump({"model": m_anchor, "features": feats}, anchor_path)
            
        elif anchor_fam == "prophet":
            pdf = df[['date', drug]].rename(columns={'date': 'ds', drug: 'y'})
            m_anchor = Prophet(yearly_seasonality=True, weekly_seasonality=True)
            m_anchor.fit(pdf)
            joblib.dump({"model": m_anchor}, anchor_path)
            
        elif anchor_fam == "arima":
            series = df[drug].values
            m_anchor = ARIMA(series, order=(2, 1, 2)).fit()
            joblib.dump({"model": m_anchor}, anchor_path)
            
        elif anchor_fam == "xgboost":
            X, y, feats = create_features(df, drug)
            m_anchor = xgb.XGBRegressor(n_estimators=100, learning_rate=0.05, random_state=42)
            m_anchor.fit(X, y)
            joblib.dump({"model": m_anchor, "features": feats}, anchor_path)
            
        print(f"   [OK] Saved Anchor Model: {drug.lower()}/anchor_model.pkl")
        
        # 2. Train & Store Quantile Model (P10 & P90 Risk & Safety Stock Bounds)
        X, y, feats = create_features(df, drug)
        m_quantile_10 = xgb.XGBRegressor(n_estimators=100, learning_rate=0.05, objective='reg:quantileerror', quantile_alpha=0.1, random_state=42)
        m_quantile_90 = xgb.XGBRegressor(n_estimators=100, learning_rate=0.05, objective='reg:quantileerror', quantile_alpha=0.9, random_state=42)
        m_quantile_10.fit(X, y)
        m_quantile_90.fit(X, y)
        joblib.dump({"model_p10": m_quantile_10, "model_p90": m_quantile_90, "features": feats}, quantile_path)
        print(f"   [OK] Saved Quantile Model: {drug.lower()}/quantile_model.pkl")
        
        # 3. Save Drug-Specific Config Metadata
        drug_config = {
            "drug_code": drug,
            "training_period": f"{min_date} to {max_date}",
            "training_cutoff_date": max_date,
            "training_data_days": len(df),
            "anchor_model": {
                "purpose": "P50 Expected Daily Sales Forecast",
                "model_name": cfg["anchor_name"],
                "algorithm_family": cfg["anchor_family"],
                "file": "anchor_model.pkl"
            },
            "quantile_model": {
                "purpose": "P10 & P90 Risk Bounds, Safety Stock, and ROP Calculation",
                "model_name": cfg["quantile_name"],
                "algorithm_family": "xgboost_quantile",
                "file": "quantile_model.pkl"
            },
            "status": "PRE_TRAINED_AND_READY"
        }
        with open(config_path, "w") as f:
            json.dump(drug_config, f, indent=2)
            
        print(f"   [OK] Saved Config: {drug.lower()}/config.json")
        
    print("\nSUCCESS: All 8 drug folders created in backend/saved_models/ with pre-trained models!")

if __name__ == "__main__":
    train_and_store_per_drug()
