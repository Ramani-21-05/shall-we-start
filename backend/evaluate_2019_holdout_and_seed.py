"""
evaluate_2019_holdout_and_seed.py
──────────────────────────────────
1. Trains LightGBM Poisson & Quantile models strictly on 2014–2018 data
2. Generates 2019 holdout forecasts (P10, P50, P90)
3. Evaluates 2019 forecasts vs actuals on all 6 metrics:
   - MAE   (Mean Absolute Error)
   - MSE   (Mean Squared Error)
   - RMSE  (Root Mean Squared Error)
   - RMSLE (Root Mean Squared Logarithmic Error)
   - MAPE  (Mean Absolute Percentage Error %)
   - WAPE  (Weighted Absolute Percentage Error %)
4. Updates forecast_results in Supabase with 2019 forecasts + actuals
5. Generates/updates Jupyter notebook drug_models/model_evaluation_2019.ipynb
"""

import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import pandas as pd
import lightgbm as lgb
from datetime import datetime
from core.ml_paths import BASE_DIR, DRUG_MODELS_DIR
from core.database import get_supabase

DRUGS = ['M01AB', 'M01AE', 'N02BA', 'N02BE', 'N05B', 'N05C', 'R03', 'R06']

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

    for lag in [1, 2, 3, 7, 14, 21, 28, 60, 90]:
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


def run_2014_2018_training_and_2019_evaluation():
    print("=" * 70)
    print("  Training Models on 2014–2018 & Forecasting 2019 Holdout Data")
    print("=" * 70)

    train_df = pd.read_csv(os.path.join(BASE_DIR, "times_series/dataset/train_daily.csv"))
    val_df   = pd.read_csv(os.path.join(BASE_DIR, "times_series/dataset/val_daily.csv"))
    test_df  = pd.read_csv(os.path.join(BASE_DIR, "times_series/dataset/test_daily.csv"))

    for df in [train_df, val_df, test_df]:
        df['date'] = pd.to_datetime(df['date'])

    full_history = pd.concat([train_df, val_df, test_df]).sort_values('date').reset_index(drop=True)

    metrics_list = []
    supabase_records = []

    for drug in DRUGS:
        drug_upper = drug.upper()
        drug_lower = drug.lower()

        # Split train (2014-2018) and holdout test (2019)
        train_series = full_history[full_history['date'] <= '2018-12-31'].set_index('date')[drug_upper].asfreq('D')
        test_series  = full_history[(full_history['date'] >= '2019-01-01') & (full_history['date'] <= '2019-12-31')].set_index('date')[drug_upper].asfreq('D')

        # Fit LightGBM models strictly on 2014-2018
        feat_df, feature_cols = create_features_df(train_series)
        X_train = feat_df.dropna()
        y_train = X_train['sales'].values
        X_train_feats = X_train[feature_cols]

        m_p50 = lgb.LGBMRegressor(**LGB_PARAMS, objective='poisson')
        m_p50.fit(X_train_feats, y_train)

        m_p10 = lgb.LGBMRegressor(**LGB_PARAMS, objective='quantile', alpha=0.10)
        m_p10.fit(X_train_feats, y_train)

        m_p90 = lgb.LGBMRegressor(**LGB_PARAMS, objective='quantile', alpha=0.90)
        m_p90.fit(X_train_feats, y_train)

        # Build 2019 features for holdout prediction
        full_2019_df = full_history[full_history['date'] <= '2019-12-31'].set_index('date')[drug_upper].asfreq('D')
        feat_2019_df, _ = create_features_df(full_2019_df)
        eval_2019 = feat_2019_df.loc['2019-01-01':'2019-12-31'].dropna()

        y_true = eval_2019['sales'].values
        X_eval_feats = eval_2019[feature_cols]
        eval_dates = eval_2019.index.strftime('%Y-%m-%d').values

        p50_pred = np.round(np.clip(m_p50.predict(X_eval_feats), 0, None), 2)
        p10_pred = np.round(np.clip(m_p10.predict(X_eval_feats), 0, None), 2)
        p90_pred = np.round(np.clip(m_p90.predict(X_eval_feats), 0, None), 2)

        p90_pred = np.maximum(p50_pred * 1.15, p90_pred)
        p10_pred = np.minimum(p50_pred * 0.85, p10_pred)

        # ── Calculate 6 Evaluation Metrics for 2019 Holdout ──────────────────
        abs_err  = np.abs(y_true - p50_pred)
        sq_err   = (y_true - p50_pred) ** 2
        log_err  = (np.log1p(y_true) - np.log1p(p50_pred)) ** 2

        mae_val   = float(np.round(np.mean(abs_err), 3))
        mse_val   = float(np.round(np.mean(sq_err), 3))
        rmse_val  = float(np.round(np.sqrt(mse_val), 3))
        rmsle_val = float(np.round(np.sqrt(np.mean(log_err)), 4))

        denom = np.maximum(y_true, 1.0)
        mape_val  = float(np.round(np.mean(abs_err / denom) * 100.0, 2))
        wape_val  = float(np.round((np.sum(abs_err) / np.maximum(1.0, np.sum(y_true))) * 100.0, 2))

        metrics_list.append({
            'Drug Code': drug_upper,
            'MAE':   mae_val,
            'MSE':   mse_val,
            'RMSE':  rmse_val,
            'RMSLE': rmsle_val,
            'MAPE (%)': mape_val,
            'WAPE (%)': wape_val,
            'Evaluation Days': len(y_true),
        })

        print(f"  [{drug_upper}] MAE: {mae_val:.2f} | MSE: {mse_val:.2f} | RMSE: {rmse_val:.2f} | RMSLE: {rmsle_val:.4f} | MAPE: {mape_val:.1f}% | WAPE: {wape_val:.1f}%")

        # Collect rows to sync to Supabase forecast_results
        for dt, yt, p10, p50, p90 in zip(eval_dates, y_true, p10_pred, p50_pred, p90_pred):
            supabase_records.append({
                "forecast_date": dt,
                "drug_code": drug_upper,
                "actual_sales": float(yt),
                "p10_demand": float(p10),
                "p50_demand": float(p50),
                "p90_demand": float(p90),
                "uncertainty_band": float(round(p90 - p10, 4)),
            })

    # Summary Metrics DataFrame
    metrics_df = pd.DataFrame(metrics_list)
    avg_row = {
        'Drug Code': 'PORTFOLIO AVG',
        'MAE':   round(metrics_df['MAE'].mean(), 3),
        'MSE':   round(metrics_df['MSE'].mean(), 3),
        'RMSE':  round(metrics_df['RMSE'].mean(), 3),
        'RMSLE': round(metrics_df['RMSLE'].mean(), 4),
        'MAPE (%)': round(metrics_df['MAPE (%)'].mean(), 2),
        'WAPE (%)': round(metrics_df['WAPE (%)'].mean(), 2),
        'Evaluation Days': 281,
    }
    metrics_final_df = pd.concat([metrics_df, pd.DataFrame([avg_row])], ignore_index=True)

    print("\n" + "=" * 70)
    print("  2019 HOLDOUT EVALUATION SUMMARY REPORT (6 METRICS)")
    print("=" * 70)
    print(metrics_final_df.to_string(index=False))

    # Save summary report CSV inside drug_models/
    metrics_csv_path = os.path.join(DRUG_MODELS_DIR, "model_evaluation_2019_holdout.csv")
    metrics_final_df.to_csv(metrics_csv_path, index=False)
    print(f"\n✅ Saved 2019 evaluation metrics report to: {metrics_csv_path}")

    # ── Update Supabase forecast_results table ──────────────────────────────
    print("\nSyncing 2019 forecasted predictions + actuals to Supabase forecast_results...")
    try:
        supabase = get_supabase()
        batch_size = 500
        for i in range(0, len(supabase_records), batch_size):
            batch = supabase_records[i:i + batch_size]
            supabase.table("forecast_results").upsert(batch, on_conflict="forecast_date,drug_code").execute()
        print("✅ Successfully updated 2019 forecast_results in Supabase!")
    except Exception as e:
        print(f"Supabase update notice: {e}")

    # ── Create/Update Jupyter Notebook inside drug_models ────────────────────
    create_evaluation_jupyter_notebook(metrics_final_df)


def create_evaluation_jupyter_notebook(metrics_df):
    """Generates drug_models/model_evaluation_2019.ipynb with rich table display of all 6 metrics."""
    nb_path = os.path.join(DRUG_MODELS_DIR, "model_evaluation_2019.ipynb")

    cells = [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# 📊 2019 Holdout Model Evaluation Report\n",
                "\n",
                "**Training Period**: 2014-01-02 to 2018-12-31 (5 full years)\n",
                "**Evaluation Holdout**: 2019-01-01 to 2019-10-08 (281 days)\n",
                "\n",
                "### Evaluated Metrics (6 Core Demand Metrics):\n",
                "1. **MAE**: Mean Absolute Error ($\\|y - \\hat{y}\\|$)\n",
                "2. **MSE**: Mean Squared Error ($(y - \\hat{y})^2$)\n",
                "3. **RMSE**: Root Mean Squared Error ($\\sqrt{\\text{MSE}}$)\n",
                "4. **RMSLE**: Root Mean Squared Logarithmic Error\n",
                "5. **MAPE (%)**: Mean Absolute Percentage Error\n",
                "6. **WAPE (%)**: Weighted Absolute Percentage Error\n"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import pandas as pd\n",
                "import os\n",
                "\n",
                "# Load evaluation report\n",
                "csv_path = 'model_evaluation_2019_holdout.csv'\n",
                "df = pd.read_csv(csv_path)\n",
                "\n",
                "print('========================================================================')\n",
                "print('  2019 HOLDOUT PERFORMANCE METRICS (2014-2018 TRAINED CHAMPION MODELS)')\n",
                "print('========================================================================')\n",
                "display(df.style.highlight_max(subset=['RMSLE', 'MAPE (%)'], color='#f87171')\\\n",
                "                .highlight_min(subset=['RMSLE', 'MAPE (%)'], color='#34d399'))\n"
            ]
        }
    ]

    notebook_content = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.10.0"}
        },
        "nbformat": 4,
        "nbformat_minor": 2
    }

    with open(nb_path, "w", encoding="utf-8") as f:
        json.dump(notebook_content, f, indent=2)

    print(f"✅ Created Jupyter Notebook at: {nb_path}")


if __name__ == "__main__":
    run_2014_2018_training_and_2019_evaluation()
