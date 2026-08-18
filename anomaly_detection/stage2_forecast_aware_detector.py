import os, glob
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, average_precision_score
import warnings
warnings.filterwarnings('ignore')

DATA_DIR = r'c:\Users\ranje\sales forcasting\times_series\dataset'
ANOMALY_DIR = r'c:\Users\ranje\sales forcasting\anomaly_detection'
DRUG_MODELS_DIR = r'c:\Users\ranje\sales forcasting\drug_models'

train_df = pd.read_csv(os.path.join(DATA_DIR, 'train_daily.csv'))
val_df   = pd.read_csv(os.path.join(DATA_DIR, 'val_daily.csv'))
synthetic_df = pd.read_csv(os.path.join(ANOMALY_DIR, 'data', 'synthetic_2019_labeled_anomalies.csv'))

for df in [train_df, val_df]:
    df['date'] = pd.to_datetime(df['date'])
synthetic_df['date'] = pd.to_datetime(synthetic_df['date'])

def load_champion_forecasts(drug):
    """
    Loads the Champion Model predictions for the given drug category.
    """
    folder = os.path.join(DRUG_MODELS_DIR, f"{drug.lower()}_models")
    plan_csvs = glob.glob(os.path.join(folder, '*_supply_chain_plan.csv'))
    
    if plan_csvs:
        plan_df = pd.read_csv(plan_csvs[0])
        plan_df['date'] = pd.to_datetime(plan_df['Date'])
        return plan_df[['date', 'Expected Demand Anchor (P50)']].rename(
            columns={'Expected Demand Anchor (P50)': 'champion_p50'}
        )
    else:
        raise FileNotFoundError(f"Champion forecast plan CSV not found for {drug}")

def build_forecast_aware_features(df, drug_col, champion_p50_series):
    """
    Stage 2 Feature Engineering (Forecast-Aware):
    Combines raw sales, lags, rolling stats, AND champion forecast + residual dynamics.
    """
    feat = pd.DataFrame(index=df.index)
    sales = df[drug_col]
    
    # 1. Standalone Base Features
    feat['sales'] = sales
    feat['lag_1'] = sales.shift(1)
    feat['lag_7'] = sales.shift(7)
    feat['roll_mean_7'] = sales.shift(1).rolling(7).mean()
    feat['roll_std_7']  = sales.shift(1).rolling(7).std()
    feat['roll_mean_14'] = sales.shift(1).rolling(14).mean()
    
    dof = df['date'].dt.dayofyear
    dow = df['date'].dt.dayofweek
    feat['dayofweek']  = dow
    feat['is_weekend'] = (dow >= 5).astype(float)
    feat['sin_month']  = np.sin(2 * np.pi * df['date'].dt.month / 12.0)
    
    # 2. FORECAST-AWARE FEATURES
    feat['champion_p50'] = champion_p50_series.values
    feat['raw_residual'] = sales.values - feat['champion_p50'].values
    feat['abs_residual'] = np.abs(feat['raw_residual'])
    
    # Relative Residual Ratio
    feat['relative_error_ratio'] = feat['raw_residual'] / (feat['champion_p50'] + 1.0)
    
    # Rolling Residual Z-Score
    roll_res_mean = feat['abs_residual'].shift(1).rolling(14).mean()
    roll_res_std  = feat['abs_residual'].shift(1).rolling(14).std().replace(0, 1.0)
    feat['residual_zscore'] = (feat['abs_residual'] - roll_res_mean) / roll_res_std
    
    return feat.fillna(0)

def run_stage2_forecast_aware_detection(drug):
    """
    Trains Stage 2 Forecast-Aware Isolation Forest on 2014-2017 historical data,
    tunes contamination threshold on 2018 validation data,
    and evaluates on 2019 synthetic labeled anomalies.
    """
    # Load 2019 test set champion forecast
    champ_df = load_champion_forecasts(drug)
    
    # Generate standard baseline forecast approximations for historical train/val
    train_champ_p50 = train_df[drug].shift(1).rolling(7).mean().fillna(train_df[drug].mean())
    val_champ_p50   = val_df[drug].shift(1).rolling(7).mean().fillna(val_df[drug].mean())
    
    # Build feature matrices
    X_train = build_forecast_aware_features(train_df, drug, train_champ_p50)
    X_val   = build_forecast_aware_features(val_df, drug, val_champ_p50)
    
    synth_drug_df = synthetic_df[synthetic_df['drug_category'] == drug].copy().reset_index(drop=True)
    synth_drug_df.rename(columns={'synthetic_sales': drug}, inplace=True)
    
    # Merge synthetic test set with exact 2019 Champion P50 forecasts
    synth_drug_df = pd.merge(synth_drug_df, champ_df, on='date', how='left')
    synth_drug_df['champion_p50'] = synth_drug_df['champion_p50'].fillna(synth_drug_df[drug].mean())
    
    X_test = build_forecast_aware_features(synth_drug_df, drug, synth_drug_df['champion_p50'])
    y_test = synth_drug_df['is_anomaly'].values
    
    # Fit Forecast-Aware Isolation Forest on historical data
    clf = IsolationForest(n_estimators=150, contamination='auto', random_state=42, n_jobs=-1)
    clf.fit(X_train)
    
    # Score validation to calibrate threshold
    val_scores = -clf.score_samples(X_val)
    threshold  = np.percentile(val_scores, 95)
    
    # Score synthetic test set
    test_scores = -clf.score_samples(X_test)
    y_pred = (test_scores >= threshold).astype(int)
    
    # Metrics
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec  = recall_score(y_test, y_pred, zero_division=0)
    f1   = f1_score(y_test, y_pred, zero_division=0)
    auc  = roc_auc_score(y_test, test_scores)
    pr_auc = average_precision_score(y_test, test_scores)
    
    return {
        'Drug Category': drug,
        'Stage': 'Stage 2 (Forecast-Aware)',
        'Precision': round(prec, 4),
        'Recall': round(rec, 4),
        'F1-Score': round(f1, 4),
        'ROC-AUC': round(auc, 4),
        'PR-AUC': round(pr_auc, 4),
        'Detected Anomalies': y_pred.sum(),
        'Actual Anomalies': y_test.sum()
    }, test_scores, y_pred

if __name__ == '__main__':
    print("=== TESTING STAGE 2 FORECAST-AWARE ANOMALY DETECTOR FOR M01AB ===")
    res, _, _ = run_stage2_forecast_aware_detection('M01AB')
    print(res)
