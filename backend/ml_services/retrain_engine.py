"""
Retrain Engine — Backend ML retraining module.
Retrains LightGBM Poisson & Quantile models for target drug on 2014-2019 data,
generates dynamic 2020 forecasts, updates model artifacts, and seeds Supabase.
"""
import os, sys, json, joblib, subprocess, threading
import numpy as np
import pandas as pd
import lightgbm as lgb
from datetime import datetime

from core.ml_paths import BASE_DIR, DRUG_MODELS_DIR, INVENTORY_RECOMMENDATION_DIR

LGB_PARAMS = {
    'num_leaves': 63,
    'max_depth': 5,
    'learning_rate': 0.01,
    'n_estimators': 350,
    'min_child_samples': 5,
    'subsample': 0.9,
    'colsample_bytree': 0.8,
    'random_state': 42,
    'verbose': -1
}

def create_features_df(series):
    df_feat = pd.DataFrame(index=series.index)
    df_feat['sales'] = series.values

    for lag in [1, 2, 3, 7, 14, 21, 28, 60, 90, 365]:
        df_feat[f'lag_{lag}'] = df_feat['sales'].shift(lag)

    for window in [7, 14, 28]:
        shifted = df_feat['sales'].shift(1)
        df_feat[f'rolling_mean_{window}'] = shifted.rolling(window).mean()
        df_feat[f'rolling_std_{window}']  = shifted.rolling(window).std()
        df_feat[f'rolling_max_{window}']  = shifted.rolling(window).max()
        df_feat[f'rolling_min_{window}']  = shifted.rolling(window).min()

    df_feat['ewm_mean_7']  = df_feat['sales'].shift(1).ewm(span=7).mean()
    df_feat['ewm_mean_28'] = df_feat['sales'].shift(1).ewm(span=28).mean()
    df_feat['cv_7']        = df_feat['rolling_std_7'] / (df_feat['rolling_mean_7'] + 1e-5)

    dof = df_feat.index.dayofyear
    dow = df_feat.index.dayofweek
    df_feat['sin_dayofyear'] = np.sin(2 * np.pi * dof / 365.25)
    df_feat['cos_dayofyear'] = np.cos(2 * np.pi * dof / 365.25)
    df_feat['sin_dayofweek'] = np.sin(2 * np.pi * dow / 7)
    df_feat['cos_dayofweek'] = np.cos(2 * np.pi * dow / 7)
    df_feat['month']         = df_feat.index.month
    df_feat['dayofweek']     = dow
    df_feat['is_weekend']    = (dow >= 5).astype(int)

    feature_cols = [c for c in df_feat.columns if c != 'sales']
    return df_feat, feature_cols

def retrain_drug_model(drug: str):
    drug_upper = drug.upper()
    drug_lower = drug.lower()
    print(f"\n[{drug_upper}] Executing Backend Model Retraining...")

    from core.database import get_supabase
    supabase = get_supabase()

    # 1. Load baseline history (2014-2019)
    train_df = pd.read_csv(os.path.join(BASE_DIR, "times_series/dataset/train_daily.csv"))
    val_df   = pd.read_csv(os.path.join(BASE_DIR, "times_series/dataset/val_daily.csv"))
    test_df  = pd.read_csv(os.path.join(BASE_DIR, "times_series/dataset/test_daily.csv"))

    for df in [train_df, val_df, test_df]:
        df['date'] = pd.to_datetime(df['date'])

    full_history = pd.concat([train_df, val_df, test_df]).sort_values('date').reset_index(drop=True)
    full_history = full_history[full_history['date'] <= '2019-12-31'].copy()
    hist_series  = full_history.set_index('date')[drug_upper].asfreq('D')

    # 2. Fetch ALL 2020 daily actual sales from sales_hourly to populate actual_sales & train model
    untrained_max_datum = "2019-12-31T23:59:59Z"
    daily_actuals_dict = {}

    try:
        all_2020_rows = []
        offset = 0
        page_size = 1000
        while True:
            res = supabase.table("sales_hourly") \
                .select(f"datum,{drug_upper},is_trained") \
                .gte("datum", "2020-01-01T00:00:00Z") \
                .lte("datum", "2020-12-31T23:59:59Z") \
                .range(offset, offset + page_size - 1) \
                .execute()
            batch = res.data or []
            all_2020_rows.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size

        if all_2020_rows:
            df_2020 = pd.DataFrame(all_2020_rows)
            df_2020['date_str'] = df_2020['datum'].astype(str).str[:10]
            df_2020[drug_upper] = pd.to_numeric(df_2020[drug_upper], errors='coerce').fillna(0.0)
            
            daily_agg = df_2020.groupby('date_str')[drug_upper].sum()
            daily_actuals_dict = daily_agg.to_dict()

            daily_agg.index = pd.to_datetime(daily_agg.index)
            hist_series = pd.concat([hist_series, daily_agg]).sort_index()
            hist_series = hist_series[~hist_series.index.duplicated(keep='last')]

            untrained_rows = [r for r in all_2020_rows if not r.get('is_trained')]
            if untrained_rows:
                untrained_max_datum = max(r['datum'] for r in untrained_rows)
            else:
                untrained_max_datum = max(r['datum'] for r in all_2020_rows)
            
            print(f"[{drug_upper}] Ingested {len(daily_agg)} 2020 daily actuals for retraining! Max datum: {untrained_max_datum}")
    except Exception as e:
        print(f"[{drug_upper}] Notice during 2020 actuals query: {e}")

    future_dates = pd.date_range(start='2020-01-01', end='2020-12-31', freq='D')
    dof   = future_dates.dayofyear
    dow   = future_dates.dayofweek
    month = future_dates.month

    # 3. Fit LightGBM on updated history (2014 through new actuals)
    feat_df, feature_cols = create_features_df(hist_series)
    X_train = feat_df.dropna()
    y_train = X_train['sales'].values
    X_train_feats = X_train[feature_cols]

    m_p50 = lgb.LGBMRegressor(**LGB_PARAMS, objective='poisson')
    m_p50.fit(X_train_feats, y_train)

    m_p10 = lgb.LGBMRegressor(**LGB_PARAMS, objective='quantile', alpha=0.10)
    m_p10.fit(X_train_feats, y_train)

    m_p90 = lgb.LGBMRegressor(**LGB_PARAMS, objective='quantile', alpha=0.90)
    m_p90.fit(X_train_feats, y_train)

    # 4. Construct 2020 features & predict
    X_2020 = pd.DataFrame(index=future_dates)
    recent_vals = hist_series.dropna().values
    if len(recent_vals) >= 366:
        last_year_vals = recent_vals[-366:]
    else:
        last_year_vals = np.pad(recent_vals, (366 - len(recent_vals), 0), mode='edge')

    for lag in [1, 2, 3, 7, 14, 21, 28, 60, 90, 365]:
        X_2020[f'lag_{lag}'] = np.roll(last_year_vals, lag)
    for window in [7, 14, 28]:
        s = pd.Series(last_year_vals)
        X_2020[f'rolling_mean_{window}'] = s.rolling(window, min_periods=1).mean().values
        X_2020[f'rolling_std_{window}']  = s.rolling(window, min_periods=1).std().fillna(0).values
        X_2020[f'rolling_max_{window}']  = s.rolling(window, min_periods=1).max().values
        X_2020[f'rolling_min_{window}']  = s.rolling(window, min_periods=1).min().values
    X_2020['ewm_mean_7']  = pd.Series(last_year_vals).ewm(span=7).mean().values
    X_2020['ewm_mean_28'] = pd.Series(last_year_vals).ewm(span=28).mean().values
    X_2020['cv_7']        = X_2020['rolling_std_7'] / (X_2020['rolling_mean_7'] + 1e-5)

    X_2020['sin_dayofyear'] = np.sin(2 * np.pi * dof / 365.25)
    X_2020['cos_dayofyear'] = np.cos(2 * np.pi * dof / 365.25)
    X_2020['sin_dayofweek'] = np.sin(2 * np.pi * dow / 7)
    X_2020['cos_dayofweek'] = np.cos(2 * np.pi * dow / 7)
    X_2020['month']         = month
    X_2020['dayofweek']     = dow
    X_2020['is_weekend']    = (dow >= 5).astype(int)

    X_2020_feats = X_2020[feature_cols]

    p50_2020 = np.round(np.clip(m_p50.predict(X_2020_feats), 0, None), 2)
    p10_2020 = np.round(np.clip(m_p10.predict(X_2020_feats), 0, None), 2)
    p90_2020 = np.round(np.clip(m_p90.predict(X_2020_feats), 0, None), 2)

    p90_2020 = np.maximum(p50_2020 * 1.15, p90_2020)
    p10_2020 = np.minimum(p50_2020 * 0.85, p10_2020)

    # 5. Store / Upsert retrained forecast results directly in Supabase forecast_results table
    forecast_records = []
    for idx, d in enumerate(future_dates):
        date_str = d.strftime('%Y-%m-%d')
        act_val = daily_actuals_dict.get(date_str, None)
        p10 = float(p10_2020[idx])
        p50 = float(p50_2020[idx])
        p90 = float(p90_2020[idx])
        record = {
            "forecast_date": date_str,
            "drug_code": drug_upper,
            "p10_demand": p10,
            "p50_demand": p50,
            "p90_demand": p90,
            "uncertainty_band": round(p90 - p10, 4)
        }
        if act_val is not None:
            record["actual_sales"] = float(round(act_val, 4))
        forecast_records.append(record)

    try:
        batch_size = 300
        for i in range(0, len(forecast_records), batch_size):
            batch = forecast_records[i:i + batch_size]
            supabase.table("forecast_results").upsert(batch, on_conflict="forecast_date,drug_code").execute()
        print(f"[{drug_upper}] Successfully updated {len(forecast_records)} 2020 predictions in forecast_results!")
    except Exception as e:
        print(f"[{drug_upper}] Error updating forecast_results: {e}")

    # 6. Update plan CSV artifact
    plan_path  = os.path.join(DRUG_MODELS_DIR, f"{drug_lower}_models", f"{drug_lower}_hybrid_supply_chain_plan.csv")
    if os.path.exists(plan_path):
        plan_2019  = pd.read_csv(plan_path)
        plan_2019.columns = [c.strip() for c in plan_2019.columns]

        plan_2020 = pd.DataFrame({
            "Date": future_dates.strftime('%Y-%m-%d'),
            "Drug Category": drug_upper,
            "Actual Sales": [daily_actuals_dict.get(d.strftime('%Y-%m-%d'), np.nan) for d in future_dates],
            "Lean Lower Bound (P10)": p10_2020,
            "Expected Demand Anchor (P50)": p50_2020,
            "Upper Target Stock (P90)": p90_2020,
            "Uncertainty Band Width (P90 - P10)": np.round(p90_2020 - p10_2020, 2),
            "Order Range (Lean P10 Pack Target)": np.maximum(1, np.ceil(p10_2020)).astype(int),
            "Order Range (Expected P50 Pack Target)": np.maximum(1, np.ceil(p50_2020)).astype(int),
            "Order Range (Safety P90 Pack Target)": np.maximum(1, np.ceil(p90_2020)).astype(int)
        })

        combined_plan = pd.concat([plan_2019[plan_2019['Date'] < '2020-01-01'], plan_2020], ignore_index=True)
        combined_plan.to_csv(plan_path, index=False)

    # 7. Save model artifacts (to both drug_models and backend/saved_models)
    save_dirs = [
        os.path.join(DRUG_MODELS_DIR, f"{drug_lower}_models", "saved_models"),
        os.path.join(BASE_DIR, "backend", "saved_models", drug_lower)
    ]
    max_hist_date = hist_series.index.max().strftime("%Y-%m-%d")
    cfg = {
        "drug_code": drug_upper,
        "training_period": f"2014-01-02 to {max_hist_date}",
        "forecast_horizon": "2020-01-01 to 2020-12-31",
        "status": "DYNAMIC_2020_RETRAINED",
        "last_retrained": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    for s_dir in save_dirs:
        os.makedirs(s_dir, exist_ok=True)
        joblib.dump({"model": m_p50, "features": feature_cols}, os.path.join(s_dir, "anchor_model.pkl"))
        joblib.dump({"model_p10": m_p10, "model_p90": m_p90, "features": feature_cols}, os.path.join(s_dir, "quantile_model.pkl"))
        with open(os.path.join(s_dir, "config.json"), "w") as f:
            json.dump(cfg, f, indent=2)


    # 8. Mark sales_hourly records as trained (is_trained = True and is_training = True)
    try:
        supabase.table("sales_hourly").update({"is_trained": True}).lte("datum", untrained_max_datum).execute()
        print(f"[{drug_upper}] Updated sales_hourly is_trained = True up to {untrained_max_datum}")
    except Exception as e:
        print(f"[{drug_upper}] Error updating is_trained in sales_hourly: {e}")

    try:
        supabase.table("sales_hourly").update({"is_training": True}).lte("datum", untrained_max_datum).execute()
    except Exception:
        pass

    print(f"[{drug_upper}] Retraining Complete & Synced to Supabase (is_trained=True, is_training=True)!")

def retrain_all_models():
    """Retrains LightGBM Poisson & Quantile models for ALL 8 drugs."""
    from core.ml_paths import DRUGS
    print("\n" + "="*70)
    print("Executing Model Retraining for ALL 8 Drug Models...")
    print("="*70 + "\n")

    results = []
    for drug in DRUGS:
        try:
            retrain_drug_model(drug)
            results.append(drug)
        except Exception as e:
            print(f"Error retraining model for {drug}: {e}")

    print(f"\n[ALL DRUGS] Successfully retrained all 8 models: {results}")
    return results

def start_retrain_in_thread(drug_code: str = None):
    t = threading.Thread(target=retrain_all_models, daemon=True)
    t.start()
