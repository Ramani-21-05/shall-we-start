import os
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, average_precision_score
import warnings
warnings.filterwarnings('ignore')

DATA_DIR = r'c:\Users\ranje\sales forcasting\times_series\dataset'
ANOMALY_DIR = r'c:\Users\ranje\sales forcasting\anomaly_detection'

train_df = pd.read_csv(os.path.join(DATA_DIR, 'train_daily.csv'))
val_df   = pd.read_csv(os.path.join(DATA_DIR, 'val_daily.csv'))
synthetic_df = pd.read_csv(os.path.join(ANOMALY_DIR, 'data', 'synthetic_2019_labeled_anomalies.csv'))

for df in [train_df, val_df]:
    df['date'] = pd.to_datetime(df['date'])
synthetic_df['date'] = pd.to_datetime(synthetic_df['date'])

def build_standalone_features(df, drug_col):
    """
    Stage 1 Feature Engineering (Standalone):
    Uses raw sales, lags, rolling stats, and calendar indicators.
    NO forecast information used.
    """
    feat = pd.DataFrame(index=df.index)
    series = df[drug_col]
    
    feat['sales'] = series
    feat['lag_1'] = series.shift(1)
    feat['lag_7'] = series.shift(7)
    feat['roll_mean_7'] = series.shift(1).rolling(7).mean()
    feat['roll_std_7']  = series.shift(1).rolling(7).std()
    feat['roll_mean_14'] = series.shift(1).rolling(14).mean()
    
    dof = df['date'].dt.dayofyear
    dow = df['date'].dt.dayofweek
    feat['dayofweek']  = dow
    feat['is_weekend'] = (dow >= 5).astype(float)
    feat['sin_month']  = np.sin(2 * np.pi * df['date'].dt.month / 12.0)
    
    return feat.fillna(0)

def run_stage1_standalone_detection(drug):
    """
    Trains Stage 1 Standalone Isolation Forest on 2014-2017 normal data,
    tunes contamination threshold on 2018 validation data,
    and evaluates on 2019 synthetic labeled anomalies.
    """
    # 1. Build training features (2014-2017)
    X_train = build_standalone_features(train_df, drug)
    
    # 2. Build validation features (2018)
    X_val   = build_standalone_features(val_df, drug)
    
    # 3. Build synthetic test features (2019)
    synth_drug_df = synthetic_df[synthetic_df['drug_category'] == drug].copy().reset_index(drop=True)
    synth_drug_df.rename(columns={'synthetic_sales': drug}, inplace=True)
    X_test  = build_standalone_features(synth_drug_df, drug)
    y_test  = synth_drug_df['is_anomaly'].values
    
    # Fit Isolation Forest on historical normal data (2014-2017)
    clf = IsolationForest(n_estimators=150, contamination='auto', random_state=42, n_jobs=-1)
    clf.fit(X_train)
    
    # Score validation to calibrate threshold
    val_scores = -clf.score_samples(X_val) # Higher score = more anomalous
    threshold  = np.percentile(val_scores, 95) # 95th percentile as anomaly threshold
    
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
        'Stage': 'Stage 1 (Standalone)',
        'Precision': round(prec, 4),
        'Recall': round(rec, 4),
        'F1-Score': round(f1, 4),
        'ROC-AUC': round(auc, 4),
        'PR-AUC': round(pr_auc, 4),
        'Detected Anomalies': y_pred.sum(),
        'Actual Anomalies': y_test.sum()
    }, test_scores, y_pred

if __name__ == '__main__':
    print("=== TESTING STAGE 1 STANDALONE ANOMALY DETECTOR FOR M01AB ===")
    res, _, _ = run_stage1_standalone_detection('M01AB')
    print(res)
